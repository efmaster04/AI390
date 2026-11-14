import json
from pathlib import Path

import pytest

from eval import run_e2e
from eval.judge import load_prompt
from src.baseline.providers import ProviderError

ROOT = Path(__file__).resolve().parents[1]
HANDBOOK_KEYS = ["week", "test_set_size", "e2e_accuracy", "abstention_correct", "unsupported_claims",
                 "hit_at_5", "mrr", "task_success", "pass_k", "injection_success", "cost_per_task_usd",
                 "latency_p50_s", "spend_week_usd", "spend_total_usd"]
CLASSIFIER_OUT = {
    "intent": "field_complaint", "secondary_intents": [], "lang": "tr", "ticket_id": None,
    "missing_fields": [], "issues": [{
        "category": "street_lighting", "urgency": "P3", "urgency_status": "classified",
        "location": None, "scope": "single_point", "onset_text": None, "sensitive_use": None,
        "referral_needed": "no", "urgency_reason": "One failed streetlight."}]}


def make_cases(tmp_path, n=6):
    cases = []
    for i in range(n):
        cases.append({"id": f"T-{i:03d}", "lang": "tr", "type": ["normal", "unanswerable", "edge"][i % 3],
                      "text": f"case text {i}",
                      "expected": {"intent": "field_complaint" if i % 2 else "faq", "secondary_intents": [],
                                   "issues": [{k: v for k, v in CLASSIFIER_OUT["issues"][0].items()
                                               if k != "urgency_reason"}] if i % 2 else [],
                                   "ticket_id": None, "missing_fields": []},
                      "expected_behavior": "Do the right thing.", "answerable": i % 3 != 1})
    path = tmp_path / "cases.jsonl"
    path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    return path, cases


class FakeProvider:
    """Stage-aware fake: classifier JSON, versioned answers, judge verdicts from a table."""

    def __init__(self, passes=None, fail_answer=None):
        self.calls = []
        self.versions = {load_prompt(ROOT / f"prompts/main/{v}.md")[0]: v for v in ("v1", "v2", "v3")}
        self.passes = passes or {}
        self.fail_answer = fail_answer or set()

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        self.calls.append((system[:30], user[:30]))
        if json_mode and "independent evaluator" in system:
            answer = user.split("<assistant_answer>\n", 1)[1].split("\n</assistant_answer>", 1)[0]
            version, text = answer.split("|", 1)
            ok = self.passes.get((version, text), False)
            out = {"label": "pass" if ok else "fail", "abstained": "<answerable>\nfalse" in user,
                   "fabrication": not ok, "claims_unperformed_action": False, "reason": "fake verdict"}
            return {"output": json.dumps(out), "input_tokens": 100, "output_tokens": 20}
        if json_mode:
            return {"output": json.dumps(CLASSIFIER_OUT), "input_tokens": 50, "output_tokens": 30}
        version = self.versions[system]
        if (version, user) in self.fail_answer:
            raise ProviderError("HTTP 400", retryable=False)
        return {"output": f"{version}|{user}", "input_tokens": 40, "output_tokens": 60}


def run(tmp_path, provider, cases_path, out="out"):
    return run_e2e.run(provider_name="fake", model="fake-model", versions=["v1", "v2", "v3"],
                       out_dir=tmp_path / out, providers={s: provider for s in ("classifier", "answer", "judge")},
                       rpm=1000, cases_path=cases_path, sleep=lambda s: None)


def test_dry_end_to_end_writes_every_file_and_key(tmp_path):
    out = tmp_path / "week2"
    assert run_e2e.main(["--provider", "dry", "--model", "dry", "--out-dir", str(out)]) == 0
    for name in ["classifier.jsonl", "run_meta.json", "scoreboard.json", "comparison.md", "comparison.json",
                 "results_for_labeling.jsonl"] + [f"{k}_v{i}.jsonl" for k in ("answers", "judged") for i in (1, 2, 3)]:
        assert (out / name).exists(), name
    board = json.loads((out / "scoreboard.json").read_text())
    assert list(board)[:len(HANDBOOK_KEYS)] == HANDBOOK_KEYS
    assert board["week"] == 2 and board["test_set_size"] == 42
    assert board["e2e_accuracy"]["n"] == 42 and len(board["e2e_accuracy"]["ci95"]) == 2
    for key in ("unsupported_claims", "hit_at_5", "mrr", "task_success", "pass_k", "injection_success"):
        assert board[key]["value"] is None
    assert board["spend_week_usd"] == 0.0 and board["best_version"] in ("v1", "v2", "v3")
    assert {"intent", "issues_match", "urgency", "category", "scope", "missing_fields",
            "json_valid", "mean_attempts"} <= set(board["classifier"])
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["git_dirty"] is not None and len(meta["testset_sha256"]) == 64
    assert set(meta["prompts"]) == {"classifier", "judge", "v1", "v2", "v3"}
    labeling = [json.loads(l) for l in (out / "results_for_labeling.jsonl").read_text().splitlines()]
    assert len(labeling) == 126 and set(labeling[0]) == {"case_id", "prompt_version", "answer"}


def test_cache_hit_avoids_second_provider_call(tmp_path):
    cases_path, cases = make_cases(tmp_path)
    first = FakeProvider()
    meta = run(tmp_path, first, cases_path)
    # 6 classifier + 18 answers + 6 judge (identical answers across versions differ by prefix -> 18)
    assert len(first.calls) == meta["counts"]["provider_calls_this_run"] == 6 + 18 + 18
    second = FakeProvider()
    meta2 = run(tmp_path, second, cases_path)
    assert second.calls == [] and meta2["counts"]["provider_calls_this_run"] == 0
    assert meta2["counts"]["cache_hits"] == 42
    rows = [json.loads(l) for l in (tmp_path / "out/judged_v1.jsonl").read_text().splitlines()]
    assert all(r["cached"] for r in rows)


def test_provider_error_counted_and_scored_incorrect_then_retried(tmp_path):
    cases_path, cases = make_cases(tmp_path)
    passes = {(v, c["text"]): True for v in ("v1", "v2", "v3") for c in cases}
    bad = ("v2", cases[0]["text"])
    run(tmp_path, FakeProvider(passes=passes, fail_answer={bad}), cases_path)
    out = tmp_path / "out"
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["errors"]["answer_v2"] == 1 and meta["errors"]["judge_v2"] == 1
    assert meta["errors"]["answer_v1"] == 0
    judged = [json.loads(l) for l in (out / "judged_v2.jsonl").read_text().splitlines()]
    assert judged[0]["status"] == "skipped_answer_error" and judged[0]["label"] is None
    comp = json.loads((out / "comparison.json").read_text())
    assert comp["versions"]["v2"]["accuracy"]["k"] == 5 and comp["versions"]["v2"]["accuracy"]["n"] == 6
    assert comp["versions"]["v2"]["errors"]["answer"] == 1
    assert comp["versions"]["v1"]["accuracy"]["k"] == 6
    # Errors are not cached: a rerun retries exactly the failed answer (+ its judge call).
    retry = FakeProvider(passes=passes)
    run(tmp_path, retry, cases_path)
    assert len(retry.calls) == 2
    assert json.loads((out / "run_meta.json").read_text())["errors"]["answer_v2"] == 0


def test_retryable_error_backs_off_with_pacing_excluded_from_latency(tmp_path):
    waits = []
    pacer = run_e2e.Pacer(60, sleep=waits.append)

    class Flaky:
        n = 0

        def generate(self, *args, **kwargs):
            self.n += 1
            if self.n == 1:
                raise ProviderError("HTTP 429", retryable=True)
            return {"output": "ok"}

    assert run_e2e.Paced(Flaky(), pacer).generate("s", "u", 0, 10, 42) == {"output": "ok"}
    assert pacer.calls == 2 and 10 in waits and pacer.wait_s >= 10


def test_classifier_errors_do_not_hit_cache(tmp_path):
    cases_path, _ = make_cases(tmp_path, n=1)

    class Down(FakeProvider):
        def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
            if json_mode and "independent evaluator" not in system:
                raise ProviderError("HTTP 400")
            return super().generate(system, user, temperature, max_tokens, seed, json_mode=json_mode)

    meta = run(tmp_path, Down(), cases_path)
    assert meta["errors"]["classifier"] == 1
    assert not (tmp_path / "out/cache/classifier").exists()
    board = json.loads((tmp_path / "out/scoreboard.json").read_text())
    assert board["classifier"]["json_valid"]["k"] == 0 and board["latency_p50_s"] is None


def test_cache_key_format_unchanged_and_judge_input_hash_recorded(tmp_path):
    cases_path, cases = make_cases(tmp_path, n=1)
    run(tmp_path, FakeProvider(), cases_path)
    case = cases[0]
    answer = f"v1|{case['text']}"
    judged_input = json.dumps([case["text"], case["expected_behavior"], case["answerable"], answer],
                              ensure_ascii=False)
    key = {"stage": "judge", "case_id": case["id"], "prompt_sha256": load_prompt(ROOT / run_e2e.JUDGE_PROMPT)[1],
           "model": "fake-model", "text_sha256": run_e2e.sha256_text(judged_input)}
    path = tmp_path / "out/cache/judge" / (run_e2e.sha256_text(json.dumps(key, sort_keys=True)) + ".json")
    assert json.loads(path.read_text())["key"] == key
    row = json.loads((tmp_path / "out/judged_v1.jsonl").read_text().splitlines()[0])
    assert row["judge_input_sha256"] == key["text_sha256"]


def test_cache_is_bound_to_provider(tmp_path):
    cases_path, _ = make_cases(tmp_path, n=2)
    out = tmp_path / "out"
    base = ["--model", "dry", "--out-dir", str(out), "--cases", str(cases_path), "--versions", "v1"]
    assert run_e2e.main(["--provider", "dry", *base]) == 0
    assert (out / "cache/PROVIDER").read_text() == "dry|dry|"
    # Same out-dir, different provider identity: abort before any call, cache untouched.
    other = ["--provider", "dry", "--model", "other", "--out-dir", str(out), "--cases", str(cases_path),
             "--versions", "v1"]
    assert run_e2e.main(other) == 2
    assert (out / "cache/PROVIDER").read_text() == "dry|dry|"
    with pytest.raises(run_e2e.CacheProviderMismatch):
        run_e2e.run(provider_name="dry", model="dry", versions=["v1"], out_dir=out, providers={},
                    cases_path=cases_path, base_url="http://elsewhere")
    assert run_e2e.main([*other, "--reset-cache"]) == 0
    assert (out / "cache/PROVIDER").read_text() == "dry|other|"
    meta = json.loads((out / "run_meta.json").read_text())
    assert meta["counts"]["cache_hits"] == 0


def test_existing_cache_without_marker_is_adopted(tmp_path):
    cases_path, _ = make_cases(tmp_path, n=2)
    run(tmp_path, FakeProvider(), cases_path)
    (tmp_path / "out/cache/PROVIDER").unlink()
    second = FakeProvider()
    meta = run(tmp_path, second, cases_path)
    assert second.calls == [] and meta["counts"]["cache_hits"] == 2 * 7
    assert (tmp_path / "out/cache/PROVIDER").read_text() == "fake|fake-model|"


def test_run_meta_snapshots_cost_inputs(tmp_path):
    cases_path, _ = make_cases(tmp_path, n=1)
    meta = run(tmp_path, FakeProvider(), cases_path)
    snap = meta["cost_inputs"]
    assert snap["price"] is None and len(snap["prices_sha256"]) == 64
    assert snap["prices_path"] == "config/prices.json" and "week1_spend_usd" in snap
    assert json.loads((tmp_path / "out/run_meta.json").read_text())["cost_inputs"] == snap
