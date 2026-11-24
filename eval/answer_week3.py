"""Bounded Week 3 retrieval -> cited answer -> claim-judge pipeline.

Real run (explicitly uses the configured model API):
  python -m eval.answer_week3 --provider gemini --model gemini-3.1-flash-lite
Offline recompute/replay of saved records:
  python -m eval.answer_week3 --out-dir eval/results/week3/answers --recompute-only

Every completed stage is cached by provider/model, source context, prompt, code
and config. Failed stages are checkpointed but not reused as successful cache.
No human label is ever generated automatically. Actual billing is unknown.
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import os
from pathlib import Path
import random
import re
import statistics
import time
from urllib.parse import quote

from src.baseline.providers import GeminiProvider, ProviderError, make_provider
from src.rag.corpus import ROOT, digest
from .faithfulness_week3 import (PROMPT, calibrate_human, flattened_claims,
                                 judge_claims, summarize_faithfulness, write_human_sheet)

DEFAULT_OUT = ROOT/"eval/results/week3/answers"
DEFAULT_CASES = ROOT/"eval/testsets/week3_retrieval.jsonl"


class BudgetExceeded(ProviderError):
    pass


DIAGNOSTIC_CODES = {"INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND",
                    "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION", "ABORTED", "OUT_OF_RANGE",
                    "UNIMPLEMENTED", "INTERNAL", "UNAVAILABLE", "DATA_LOSS", "DEADLINE_EXCEEDED",
                    "CANCELLED", "UNKNOWN", "PROVIDER_ERROR", "NETWORK_TIMEOUT", "NETWORK_CONNECTION",
                    "NETWORK_ERROR", "INVALID_PROVIDER_JSON", "BAD_GATEWAY"}


class DiagnosticProviderError(ProviderError):
    """Safe structured diagnostics; raw response bodies/URLs are never retained."""
    def __init__(self, *, http_status=None, diagnostic_code="PROVIDER_ERROR", retryable=False,
                 retry_after_s=None):
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        self.diagnostic_code = diagnostic_code if diagnostic_code in DIAGNOSTIC_CODES else "PROVIDER_ERROR"
        self.retry_after_s = (float(retry_after_s) if isinstance(retry_after_s, (int, float))
                              and math.isfinite(retry_after_s) and retry_after_s >= 0 else None)
        super().__init__(f"HTTP {self.http_status}" if self.http_status else self.diagnostic_code,
                         retryable=retryable)


def parse_retry_after(value, *, now=None):
    """Parse seconds or an HTTP date. Invalid/untrusted header text is discarded."""
    if not isinstance(value, str):
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            seconds = when.timestamp()-(time.time() if now is None else now)
        except (TypeError, ValueError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


class TimedGeminiProvider(GeminiProvider):
    """Week 3's isolated transport; never mutates historical Week 2 adapters."""
    def __init__(self, model, api_key, timeout_s=30):
        super().__init__(model, api_key)
        self.timeout_s = timeout_s

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        import requests
        payload = {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"role": "user", "parts": [{"text": user}]}],
                   "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens,
                                        "seed": seed, **({"responseMimeType": "application/json"} if json_mode else {})}}
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent",
                headers={"x-goog-api-key": self.api_key}, json=payload,
                timeout=(min(10, self.timeout_s), self.timeout_s))
        except requests.RequestException as exc:
            code = ("NETWORK_TIMEOUT" if isinstance(exc, requests.Timeout) else
                    "NETWORK_CONNECTION" if isinstance(exc, requests.ConnectionError) else "NETWORK_ERROR")
            raise DiagnosticProviderError(diagnostic_code=code, retryable=True) from exc
        if not response.ok:
            fallback = {400: "INVALID_ARGUMENT", 401: "UNAUTHENTICATED", 403: "PERMISSION_DENIED",
                        404: "NOT_FOUND", 408: "DEADLINE_EXCEEDED", 429: "RESOURCE_EXHAUSTED",
                        500: "INTERNAL", 502: "BAD_GATEWAY", 503: "UNAVAILABLE", 504: "DEADLINE_EXCEEDED"}
            code = fallback.get(response.status_code, "PROVIDER_ERROR")
            try:
                body = response.json()
                candidate_code = body.get("error", {}).get("status") if isinstance(body, dict) else None
                if candidate_code in DIAGNOSTIC_CODES:
                    code = candidate_code
            except (TypeError, ValueError, AttributeError):
                pass
            raise DiagnosticProviderError(http_status=response.status_code, diagnostic_code=code,
                                          retryable=response.status_code in (408, 429) or response.status_code >= 500,
                                          retry_after_s=parse_retry_after(response.headers.get("Retry-After")))
        try:
            data = response.json()
        except ValueError as exc:
            raise DiagnosticProviderError(diagnostic_code="INVALID_PROVIDER_JSON", retryable=True) from exc
        candidate = (data.get("candidates") or [{}])[0]
        usage = data.get("usageMetadata") or {}
        count = usage.get("candidatesTokenCount")
        return {"output": "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought")),
                "input_tokens": usage.get("promptTokenCount"),
                "output_tokens": count+(usage.get("thoughtsTokenCount") or 0) if count is not None else None,
                "finish_reason": candidate.get("finishReason")}


class BoundedProvider:
    """Shared pacing/deadline, bounded exponential backoff and server Retry-After."""
    def __init__(self, provider, *, max_calls=110, rpm=9, deadline_s=1500, sleep=time.sleep,
                 transport_retries=1, backoff_s=5.0, clock=time.monotonic, jitter_ratio=0.2):
        if max_calls < 1 or rpm <= 0 or deadline_s <= 0:
            raise ValueError("Call budget, rpm and deadline must be positive")
        self.provider, self.max_calls, self.interval = provider, max_calls, 60/rpm
        if type(transport_retries) is not int or transport_retries not in range(4):
            raise ValueError("transport_retries must be 0, 1, 2 or 3")
        if not isinstance(backoff_s, (int, float)) or not math.isfinite(backoff_s) or backoff_s < 0:
            raise ValueError("backoff_s must be finite and nonnegative")
        if not isinstance(jitter_ratio, (int, float)) or not math.isfinite(jitter_ratio) or not 0 <= jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between zero and one")
        self.transport_retries = transport_retries
        self.jitter_ratio, self.random = jitter_ratio, random.Random(42)
        self.clock, self.backoff_s = clock, backoff_s
        self.deadline, self.sleep = clock()+deadline_s, sleep
        self.last, self.calls, self.errors, self.wait_s = None, 0, 0, 0.0
        self.next_allowed_at, self.blocked_by_deadline = 0.0, False
        self.stop_reason = None
        self.events = []
        self.case_id, self.stage = None, None

    @property
    def exhausted(self):
        return self.calls >= self.max_calls or self.clock() >= self.deadline or self.blocked_by_deadline

    def generate(self, *args, **kwargs):
        for attempt in range(self.transport_retries+1):
            if self.exhausted:
                raise BudgetExceeded("Week 3 call or wall-clock budget exhausted", retryable=False)
            now = self.clock()
            pacing_due = self.last+self.interval if self.last is not None else now
            wait = max(0.0, pacing_due-now, self.next_allowed_at-now)
            if now+wait >= self.deadline:
                self.blocked_by_deadline = True
                self.stop_reason = "retry_after_or_pacing_exceeds_deadline"
                raise BudgetExceeded("Required provider wait exceeds remaining Week 3 deadline", retryable=False)
            remaining = wait
            while remaining > 0:
                # Small waits keep the desktop task responsive, even for large headers.
                chunk = min(remaining, 30.0)
                self.sleep(chunk)
                self.wait_s += chunk
                remaining -= chunk
            self.calls += 1
            self.last = self.clock()
            event = {"call_number": self.calls, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                     "case_id": self.case_id, "stage": self.stage, "transport_attempt": attempt+1,
                     "status": "started", "http_status": None, "diagnostic_code": None,
                     "wait_before_call_s": wait}
            self.events.append(event)
            try:
                value = self.provider.generate(*args, **kwargs)
                event["status"] = "ok"
                self.next_allowed_at = 0.0
                return value
            except ProviderError as exc:
                self.errors += 1
                match = re.fullmatch(r"HTTP (\d{3})", str(exc))
                event.update(status="provider_error", http_status=int(match[1]) if match else None,
                             exception_type=type(exc).__name__, retryable=bool(exc.retryable))
                code = getattr(exc, "diagnostic_code", None)
                event["diagnostic_code"] = code if code in DIAGNOSTIC_CODES else "PROVIDER_ERROR"
                retry_after = getattr(exc, "retry_after_s", None)
                if not isinstance(retry_after, (int, float)) or not math.isfinite(retry_after) or retry_after < 0:
                    retry_after = None
                # Exponential backoff belongs to retries of this generate call.
                # Once its attempt budget is spent, an independent next request
                # starts with normal RPM pacing. Server Retry-After is global.
                will_retry = exc.retryable and attempt < self.transport_retries
                exponential = self.backoff_s*(2**attempt) if will_retry else 0.0
                jitter = self.random.uniform(0, exponential*self.jitter_ratio)
                delay = max(exponential+jitter, retry_after or 0.0)
                event.update(retry_after_s=retry_after, backoff_s=exponential,
                             jitter_s=jitter, required_wait_s=delay)
                if exc.retryable:
                    self.next_allowed_at = max(self.next_allowed_at, self.clock()+delay)
                    if self.next_allowed_at >= self.deadline:
                        self.blocked_by_deadline = True
                        self.stop_reason = "provider_retry_after_or_backoff_exceeds_deadline"
                if not exc.retryable or attempt == self.transport_retries:
                    raise
            except Exception as exc:
                self.errors += 1
                event.update(status="provider_error", exception_type=type(exc).__name__, retryable=False)
                raise


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temp.replace(path)


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows), encoding="utf-8")
    tmp.replace(path)


def read_jsonl(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]


def _stage_cache(cache, key, function):
    identity = digest(json.dumps(key, sort_keys=True, ensure_ascii=False))
    path = Path(cache)/(identity+".json")
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("key") == key and saved["result"].get("valid"):
            return saved["result"], True
    value = function()
    if value.get("valid"):
        atomic_json(path, {"key": key, "result": value})
    return value, False


def _unknown_sum(values):
    values = list(values)
    return None if any(type(v) is not int or v < 0 for v in values) else sum(values)


def _without_pacing(provider, function):
    before = provider.wait_s
    result = function()
    if result.get("latency_s") is not None:
        result["wall_latency_including_pacing_s"] = result["latency_s"]
        result["latency_s"] = max(0.0, result["latency_s"]-(provider.wait_s-before))
    return result


def summarize_answers(rows, meta):
    n = len(rows)
    valid = [r for r in rows if (r.get("generation") or {}).get("valid")]
    judged = [r for r in rows if (r.get("judgement") or {}).get("valid")]
    abstention_rows = [r for r in rows if not r["expected_answerable"]]
    honest = sum(r["generation"].get("valid") and r["generation"].get("abstained") is True for r in abstention_rows)
    answerability = sum(bool(r["generation"].get("valid")) and
                        (not r["generation"].get("abstained")) == r["expected_answerable"] for r in rows)
    faith = summarize_faithfulness(rows)
    def measured_count(row, stage, key):
        report = row.get(stage) or {}
        if not report.get("valid") and report.get("error") != "skipped_generation_error":
            return None  # Failed/provider-lost consumption cannot be inferred as 0.
        return report.get(key)
    tokens = {stage: {key: _unknown_sum(measured_count(r, stage, key) for r in rows)
                      for key in ("input_tokens", "output_tokens")}
              for stage in ("generation", "judgement")}
    price = meta.get("prices_snapshot")
    costs = {}
    for stage, values in tokens.items():
        costs[stage] = ((values["input_tokens"]*price["price_in_per_1m_usd"]+
                         values["output_tokens"]*price["price_out_per_1m_usd"])/1e6
                        if price and all(v is not None for v in values.values()) else None)
    answer_latencies = [r["generation"]["latency_s"] for r in valid]
    rag_latencies = [r["generation"]["latency_s"]+r["retrieval"]["timings_s"]["total"] for r in valid]
    current_calls = meta.get("provider_calls_this_invocation", 0)
    deferred = sum((r.get("judgement") or {}).get("error") == "deferred_judgement" for r in rows)
    skipped = sum((r.get("judgement") or {}).get("error") == "skipped_generation_error" for r in rows)
    return {"week": 3, "stage": "rag_answer_and_claim_judge", "planned_cases": meta["planned_cases"],
            "processed_cases": n, "run_complete": n == meta["planned_cases"] and deferred == 0,
            "generation_pass_complete": n == meta["planned_cases"], "judging_pass_complete": deferred == 0,
            "valid_generated_answers": len(valid), "valid_claim_judgements": len(judged),
            "judgements_deferred_or_not_attempted": deferred,
            "judgements_skipped_generation_error": skipped,
            "judgements_failed_or_invalid": n-len(judged)-deferred-skipped,
            "answerability_accuracy": {"value": answerability/n if n else None, "n": n,
                                       "definition": "valid answer abstains iff fixed test flag says unanswerable; not semantic answer accuracy"},
            "abstention_correct": {"value": honest/len(abstention_rows) if abstention_rows else None,
                                   "n": len(abstention_rows), "numerator": honest,
                                   "definition": "valid fixed-fallback response on unavailable-information controls"},
            "unsupported_claims": faith["unsupported_claims"], "faithfulness": faith,
            "generation_latency_p50_s": statistics.median(answer_latencies) if answer_latencies else None,
            "latency_p50_s": statistics.median(rag_latencies) if rag_latencies else None,
            "latency_note": "retrieval plus generation service time; judge and scheduler/backoff waits excluded, not end-user wall time; cached rows retain historical generation timings",
            "e2e_accuracy": {"value": None, "n": None, "reason": "No independent answer-adequacy rubric measured; claim faithfulness is not question completion"},
            "tokens": tokens,
            "tokens_scope": "Known usage in saved stage results, including historical cache hits; failed transport-attempt usage may be unavailable",
            "list_price_equivalent_usd": costs,
            "list_price_scope": "Equivalent price of known saved-stage tokens, not current-invocation API consumption or actual billed spend",
            "transport_attempt_usage_complete": meta.get("transport_errors", 0) == 0,
            "historical_cache_attempt_usage_unknown": meta.get("cache_hits", 0) > 0,
            "cost_incomplete": (any(v is None for v in costs.values()) or meta.get("transport_errors", 0) > 0 or meta.get("cache_hits", 0) > 0),
            "actual_spend_usd": None, "billing_note": "No billing evidence collected; list prices are dated assumptions, not actual spend",
            "provider_calls_this_invocation": current_calls,
            "valid_answers_from_cache": sum(r.get("generation_from_cache", False) for r in valid),
            "valid_answers_fresh": sum(not r.get("generation_from_cache", False) for r in valid),
            "valid_judgements_from_cache": sum(r.get("judgement_from_cache", False) for r in judged),
            "valid_judgements_fresh": sum(not r.get("judgement_from_cache", False) for r in judged),
            "provisional": True, "provisional_reason": "Synthetic draft corpus/test labels and human judge calibration pending or limited"}


def failure_analysis(rows):
    output = []
    for row in rows:
        if not row["generation"].get("valid"):
            output.append({"case_id": row["case_id"], "stage": "generation", "kind": "generation_or_provider_error",
                           "error": row["generation"].get("error")})
            continue
        results = row["retrieval"]["results"]
        gold = [g for group in row.get("gold_groups", [[g] for g in row.get("gold", [])]) for g in group]
        gold_found = any(g["passage_id"] == r["passage_id"] and g["quote"] in r["text"] for g in gold for r in results)
        if row["expected_answerable"] and not gold_found:
            output.append({"case_id": row["case_id"], "stage": "retrieval", "kind": "designated_gold_missing_from_context",
                           "note": "Alternative valid evidence may exist; draft gold needs human review"})
        if row["expected_answerable"] and row["generation"].get("abstained"):
            output.append({"case_id": row["case_id"], "stage": "generation" if gold_found else "retrieval",
                           "kind": "abstained_on_answerable_question", "gold_found": gold_found})
        if not row["expected_answerable"] and not row["generation"].get("abstained"):
            output.append({"case_id": row["case_id"], "stage": "generation", "kind": "answered_unavailable_information_control"})
        judge = row.get("judgement") or {}
        if not judge.get("valid"):
            output.append({"case_id": row["case_id"], "stage": "evaluation", "kind": "judge_error_or_invalid"})
        elif any(c["label"] != "supported" for c in [*judge["claims"], *judge["unlisted_claims"]]):
            output.append({"case_id": row["case_id"], "stage": "generation", "kind": "unsupported_or_insufficient_claim",
                           "note": "According to provisional automatic claim judge; inspect cited evidence"})
    return output


def recompute(out_dir):
    out = Path(out_dir)
    rows = read_jsonl(out/"records.jsonl")
    meta = json.loads((out/"run_meta.json").read_text())
    summary = summarize_answers(rows, meta)
    atomic_json(out/"summary.json", summary)
    atomic_json(out/"automatic_claim_labels.json", flattened_claims(rows))
    write_human_sheet(rows, out/"human_sheet.csv", n=20)
    atomic_json(out/"human_calibration.json", calibrate_human(out/"human_sheet.csv", rows))
    atomic_json(out/"failures.json", failure_analysis(rows))
    # Separate preliminary scoreboard; root combines report-wide metrics without
    # overwriting the committed Week 2 scoreboard or pretending RAG is validated.
    atomic_json(out/"scoreboard.json", summary)
    return summary


def run(*, provider_name, model, out_dir=DEFAULT_OUT, cases_path=DEFAULT_CASES,
        max_cases=None, max_calls=110, rpm=9, timeout_s=30, deadline_s=1500,
        provider=None, retriever=None, transport_retries=1, validation_retries=1, backoff_s=5.0,
        defer_judge=False):
    from src.rag.answer import answer_with_sources
    from src.rag.retrieval import Retriever, source_context
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases = read_jsonl(cases_path)
    if max_cases is not None:
        if max_cases < 1:
            raise ValueError("max_cases must be positive")
        cases = cases[:max_cases]
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    if type(validation_retries) is not int or validation_retries not in (0, 1):
        raise ValueError("validation_retries must be 0 or 1")
    code_files = [ROOT/"src/rag/answer.py", ROOT/"eval/faithfulness_week3.py", Path(__file__)]
    code_hashes = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in code_files}
    config_path = ROOT/"config/rag_answer.json"
    config = json.loads(config_path.read_text())
    prompt_path = ROOT/config["prompt_path"]
    hashes = {"generation_prompt": digest(prompt_path.read_bytes()), "judge_prompt": digest(PROMPT.read_bytes()),
              "answer_config": digest(config_path.read_bytes()), "cases": digest(Path(cases_path).read_bytes())}
    if provider is None:
        if provider_name == "gemini":
            key = os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("GEMINI_API_KEY is not set")
            provider = TimedGeminiProvider(model, key, timeout_s=timeout_s)
        else:
            provider = make_provider(provider_name, model)
    bounded = BoundedProvider(provider, max_calls=max_calls, rpm=rpm, deadline_s=deadline_s,
                              transport_retries=transport_retries, backoff_s=backoff_s)
    retriever = retriever or Retriever()
    prices = json.loads((ROOT/"config/prices.json").read_text())
    price = next((p for p in prices if p["provider"] == provider_name and p["model"] == model), None)
    identity = {"provider": provider_name, "model": model, "temperature": 0, "seed": 42,
                "hashes": hashes, "code": code_hashes, "corpus_sha256": retriever.corpus_sha256,
                "index_sha256": retriever.index_sha256}
    meta = {"started_utc": datetime.now(timezone.utc).isoformat(), "planned_cases": len(cases),
            "identity": identity, "max_calls": max_calls, "rpm": rpm, "timeout_s": timeout_s,
            "transport_retries": transport_retries, "validation_retries": validation_retries,
            "transport_backoff_s": backoff_s, "transport_jitter_ratio": bounded.jitter_ratio,
            "transport_jitter_seed": 42, "retry_after_respected": True,
            "deadline_s": deadline_s, "prices_snapshot": price,
            "actual_spend_usd": None, "provider_calls_this_invocation": 0,
            "defer_judge": bool(defer_judge), "phase": "generation" if defer_judge else "interleaved",
            "cache_hits": 0, "provider_events": [], "cached_results_are_historical_model_calls": True}
    atomic_json(out/"run_meta.json", meta)
    records, pending_judges = [], []

    def obtain_judgement(case, generation, sources, common):
        bounded.case_id, bounded.stage = case["id"], "judge"
        judge_key = {**common, "stage": "judge", "prompt_sha256": hashes["judge_prompt"],
                     "answer_sha256": digest(json.dumps({"answer": generation["answer"], "claims": generation["claims"]}, ensure_ascii=False)),
                     "code_sha256": code_hashes["eval/faithfulness_week3.py"]}
        return _stage_cache(out/"cache", judge_key, lambda: _without_pacing(bounded, lambda: judge_claims(
            generation, sources, bounded, question=case["text"], language=case["lang"], max_retries=validation_retries)))

    def checkpoint():
        write_jsonl(out/"records.jsonl", records)
        meta.update(provider_calls_this_invocation=bounded.calls, transport_errors=bounded.errors,
                    provider_events=bounded.events, pacing_wait_s=bounded.wait_s, processed_cases=len(records))
        atomic_json(out/"run_meta.json", meta)

    for i, case in enumerate(cases, 1):
        if bounded.exhausted:
            meta["stop_reason"] = bounded.stop_reason or "call_or_wall_clock_budget"
            break
        retrieval = retriever.search(case["text"], role=case.get("role", "public"), k=5)
        sources = source_context(retrieval)
        bounded.case_id = case["id"]
        bounded.stage = "answer"
        common = {"provider": provider_name, "model": model, "corpus": retriever.corpus_sha256,
                  "index": retriever.index_sha256, "question": case["text"], "language": case["lang"],
                  "sources_sha256": digest(json.dumps(sources, ensure_ascii=False, sort_keys=True)),
                  "config_sha256": hashes["answer_config"], "temperature": 0, "seed": 42,
                  "validation_retries": validation_retries}
        key = {**common, "stage": "answer", "prompt_sha256": hashes["generation_prompt"],
               "code_sha256": code_hashes["src/rag/answer.py"]}
        generation, hit = _stage_cache(out/"cache", key, lambda: _without_pacing(bounded, lambda: answer_with_sources(
            case["text"], bounded, sources, language=case["lang"], max_retries=validation_retries)))
        generation_from_cache = bool(hit)
        meta["cache_hits"] += hit
        if generation.get("valid") and not defer_judge:
            judgement, hit = obtain_judgement(case, generation, sources, common)
            judgement_from_cache = bool(hit)
            meta["cache_hits"] += hit
        elif generation.get("valid"):
            judgement_from_cache = False
            judgement = {"valid": False, "error": "deferred_judgement", "claims": [], "unlisted_claims": [],
                         "input_tokens": 0, "output_tokens": 0, "attempts": 0}
            pending_judges.append((len(records), case, sources, common))
        else:
            judgement_from_cache = False
            judgement = {"valid": False, "error": "skipped_generation_error", "claims": [], "unlisted_claims": [],
                         "input_tokens": 0, "output_tokens": 0, "attempts": 0}
        row = {"case_id": case["id"], "question": case["text"], "lang": case["lang"],
               "expected_answerable": case["answerable"], "review_status": case.get("review_status", "draft"),
               "gold": case.get("gold", []), "gold_groups": case.get("gold_groups", [[g] for g in case.get("gold", [])]), "retrieval": retrieval, "sources": sources,
               "generation": generation, "judgement": judgement,
               "generation_from_cache": generation_from_cache, "judgement_from_cache": judgement_from_cache}
        records.append(row)
        checkpoint()
        print(f"[{i}/{len(cases)}] {case['id']} answer={'ok' if generation.get('valid') else 'error'} "
              f"judge={'ok' if judgement.get('valid') else 'error/skipped'} calls={bounded.calls} "
              f"http_statuses={[e['http_status'] for e in bounded.events if e['case_id'] == case['id'] and e['http_status']]}", flush=True)
    if defer_judge:
        meta["phase"] = "judging"
        checkpoint()
        for index, case, sources, common in pending_judges:
            if bounded.exhausted:
                meta["stop_reason"] = bounded.stop_reason or "call_or_wall_clock_budget"
                break
            judgement, hit = obtain_judgement(case, records[index]["generation"], sources, common)
            records[index]["judgement"], records[index]["judgement_from_cache"] = judgement, bool(hit)
            meta["cache_hits"] += hit
            checkpoint()
            print(f"[judge {index+1}/{len(records)}] {case['id']} "
                  f"judge={'ok' if judgement.get('valid') else 'error'} calls={bounded.calls}", flush=True)
    meta["phase"] = "finished"
    meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_json(out/"run_meta.json", meta)
    if not (out/"records.jsonl").exists():
        write_jsonl(out/"records.jsonl", [])
    return recompute(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=["gemini", "ollama", "openai_compat"], default="gemini")
    p.add_argument("--model", default="gemini-3.1-flash-lite")
    p.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--max-cases", type=int)
    p.add_argument("--max-calls", type=int, default=110)
    p.add_argument("--rpm", type=float, default=9)
    p.add_argument("--timeout-s", type=float, default=30)
    p.add_argument("--deadline-s", type=float, default=1500)
    p.add_argument("--transport-retries", type=int, choices=[0, 1, 2, 3], default=1)
    p.add_argument("--backoff-s", type=float, default=5.0,
                   help="Exponential transport delay base; server Retry-After and pacing may require longer waits")
    p.add_argument("--validation-retries", "--stage-retries", dest="validation_retries", type=int, choices=[0, 1], default=1)
    p.add_argument("--recompute-only", action="store_true")
    p.add_argument("--defer-judge", action="store_true", help="Checkpoint every generation first, then judge using the remaining shared budget")
    args = p.parse_args(argv)
    if args.recompute_only:
        value = recompute(args.out_dir)
    else:
        value = run(provider_name=args.provider, model=args.model, cases_path=args.cases,
                    out_dir=args.out_dir, max_cases=args.max_cases, max_calls=args.max_calls,
                    rpm=args.rpm, timeout_s=args.timeout_s, deadline_s=args.deadline_s,
                    transport_retries=args.transport_retries, validation_retries=args.validation_retries,
                    backoff_s=args.backoff_s, defer_judge=args.defer_judge)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
