"""W2.4 eval harness: classifier -> main answer (v1..vN) -> LLM judge for every Week 2 case.

One command runs every case and writes the scoreboard:
    python -m eval.run_e2e --provider gemini --model gemini-3.1-flash-lite --versions v1 v2 v3

Every model call result is cached under <out-dir>/cache keyed by
(stage, case_id, prompt sha256, model, text sha256), so a rerun resumes instead of
repaying calls. Provider errors are not cached (a rerun retries them); they mark that
case's stage as error, the run continues, and an errored case counts as incorrect.

Cache keys do not name the provider, so <out-dir>/cache/PROVIDER records
"<provider>|<model>|<base_url>" on first use; a later run with a different provider in the
same out-dir aborts (exit 2) unless --reset-cache deletes the cache first.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from eval import compare_versions
from eval.answer import answer as main_answer, resolve
from eval.judge import judge, load_prompt
from src.baseline.providers import ProviderError, make_provider
from src.classifier.classify import classify


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = "eval/testsets/week2_cases.jsonl"
CLASSIFIER_PROMPT = "prompts/classifier/v1.md"
JUDGE_PROMPT = "prompts/judge/v2.md"
SEED = 42
ANSWER_MAX_TOKENS = 1024


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return sha256_bytes(text.encode("utf-8"))


def _git(*args):
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def commit_hash():
    out = _git("rev-parse", "HEAD")
    return (out.strip() or None) if out is not None else None


def git_dirty():
    out = _git("status", "--porcelain")
    return None if out is None else bool(out.strip())


def rel(path):
    path = resolve(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_cases(path):
    with resolve(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class Pacer:
    """Shared request clock: at most `rpm` requests per minute across all stages."""

    def __init__(self, rpm, sleep=time.sleep, enabled=True):
        self.interval = 60 / rpm if enabled and rpm else 0
        self.sleep, self.last, self.wait_s, self.calls = sleep, None, 0.0, 0

    def wait(self, seconds):
        if seconds > 0:
            self.sleep(seconds)
            self.wait_s += seconds

    def before_call(self):
        if self.interval and self.last is not None:
            self.wait(self.interval - (time.monotonic() - self.last))
        self.last = time.monotonic()
        self.calls += 1


class Paced:
    """Provider wrapper: pacing plus backoff on retryable errors (429/5xx/network)."""

    def __init__(self, provider, pacer, retries=3, backoff_s=10):
        self.provider, self.pacer, self.retries, self.backoff_s = provider, pacer, retries, backoff_s

    def generate(self, *args, **kwargs):
        for attempt in range(self.retries + 1):
            self.pacer.before_call()
            try:
                return self.provider.generate(*args, **kwargs)
            except ProviderError as exc:
                if not exc.retryable or attempt == self.retries:
                    raise
                self.pacer.wait(self.backoff_s * 2 ** attempt)


class DryJudgeProvider:
    """Offline judge stand-in: deterministic, schema-valid verdicts (synthetic, not a measurement)."""

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        unanswerable = "<answerable>\nfalse\n</answerable>" in user
        verdict = {"label": "pass" if int(sha256_text(user), 16) % 2 else "fail",
                   "abstained": unanswerable, "fabrication": False,
                   "claims_unperformed_action": False, "reason": "dry-run synthetic verdict"}
        output = json.dumps(verdict)
        return {"output": output, "input_tokens": len(user) // 4, "output_tokens": len(output) // 4}


class CacheProviderMismatch(RuntimeError):
    pass


def provider_identity(provider_name, model, base_url=None):
    return f"{provider_name}|{model}|{base_url or ''}"


def check_cache_provider(cache_dir, identity, reset=False):
    """Bind the cache dir to one provider; keys stay unchanged (the marker lives beside them).

    A cache dir without a marker (written before markers existed) is adopted for the
    current provider. A different recorded provider aborts unless reset deletes the cache.
    """
    cache_dir = Path(cache_dir)
    if reset and cache_dir.exists():
        shutil.rmtree(cache_dir)
    marker = cache_dir / "PROVIDER"
    if marker.exists():
        recorded = marker.read_text(encoding="utf-8").strip()
        if recorded != identity:
            raise CacheProviderMismatch(
                f"Cache {cache_dir} was filled by provider '{recorded}', but this run is '{identity}'. "
                "Reusing it would mix results from different providers (e.g. synthetic dry-run outputs). "
                "Use another --out-dir, or pass --reset-cache to delete this cache.")
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text(identity, encoding="utf-8")


class Cache:
    def __init__(self, root):
        self.root, self.hits, self.misses = Path(root), 0, 0

    def _path(self, key):
        return self.root / key["stage"] / (sha256_text(json.dumps(key, sort_keys=True)) + ".json")

    def get(self, key):
        path = self._path(key)
        if path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
            if stored.get("key") == key:
                self.hits += 1
                return stored["value"]
        self.misses += 1
        return None

    def put(self, key, value):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"key": key, "value": value}, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")


def _timed(pacer, fn):
    """Run fn, returning (result, seconds spent in pacing/backoff waits during it)."""
    before = pacer.wait_s
    result = fn()
    return result, pacer.wait_s - before


def run_classifier(case, provider, pacer, cache, model, prompt_sha):
    key = {"stage": "classifier", "case_id": case["id"], "prompt_sha256": prompt_sha,
           "model": model, "text_sha256": sha256_text(case["text"])}
    value = cache.get(key)
    cached = value is not None
    if not cached:
        report, waited = _timed(pacer, lambda: classify(case["text"], provider,
                                                        prompt_path=resolve(CLASSIFIER_PROMPT), seed=SEED))
        report["latency_s"] = max(0.0, report["latency_s"] - waited)
        failed = report["provider_error"] is not None or any(
            e.startswith("classifier:") for e in report["errors"])
        status = "error" if failed else "ok" if report["valid"] else "invalid"
        value = {"status": status, **{k: report[k] for k in (
            "result", "valid", "attempts", "errors", "provider_error", "input_tokens",
            "output_tokens", "latency_s", "prompt_sha256")}}
        if status != "error":
            cache.put(key, value)
    return {"case_id": case["id"], **value, "cached": cached}


def run_answer(case, version, provider, pacer, cache, model, prompt_sha):
    key = {"stage": "answer", "case_id": case["id"], "prompt_sha256": prompt_sha,
           "model": model, "text_sha256": sha256_text(case["text"])}
    value = cache.get(key)
    cached = value is not None
    if not cached:
        report, waited = _timed(pacer, lambda: main_answer(
            case["text"], provider, prompt_path=f"prompts/main/{version}.md", seed=SEED,
            max_tokens=ANSWER_MAX_TOKENS))
        if report["latency_s"] is not None:
            report["latency_s"] = max(0.0, report["latency_s"] - waited)
        value = {"status": "error" if report["error"] else "ok", **report}
        if not report["error"]:
            cache.put(key, value)
    return {"case_id": case["id"], "prompt_version": version, **value, "cached": cached}


def run_judge(case, version, answer_row, provider, cache, model, prompt_sha):
    base = {"case_id": case["id"], "prompt_version": version}
    if answer_row["status"] != "ok":
        return {**base, "status": "skipped_answer_error", "label": None, "abstained": None,
                "fabrication": None, "claims_unperformed_action": None, "reason": None,
                "valid": False, "attempts": 0, "errors": ["answer stage errored"],
                "input_tokens": 0, "output_tokens": 0, "prompt_sha256": prompt_sha,
                "judge_input_sha256": None, "cached": False}
    input_sha = sha256_text(compare_versions.judged_input(case, answer_row["answer"]))
    key = {"stage": "judge", "case_id": case["id"], "prompt_sha256": prompt_sha,
           "model": model, "text_sha256": input_sha}
    value = cache.get(key)
    cached = value is not None
    if not cached:
        report = judge(case, answer_row["answer"], provider, prompt_path=resolve(JUDGE_PROMPT), seed=SEED)
        provider_failed = not report["valid"] and any(
            e.startswith(("Provider error", "Prompt/input error")) for e in report["errors"])
        value = {"status": "error" if provider_failed else "ok" if report["valid"] else "invalid", **report}
        if not provider_failed:
            cache.put(key, value)
    return {**base, **value, "judge_input_sha256": input_sha, "cached": cached}


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run(*, provider_name, model, versions, out_dir, providers, rpm=10, limit=None,
        cases_path=DEFAULT_CASES, sleep=time.sleep, command=None, log=None, base_url=None,
        reset_cache=False):
    """Run the pipeline. `providers` maps stage ('classifier', 'answer', 'judge') to a provider.

    Raises CacheProviderMismatch before any call if the out-dir cache belongs to another provider.
    """
    # Git durumu çıktı dosyalarına dokunmadan ÖNCE ölçülür.
    run_commit, run_dirty = commit_hash(), git_dirty()
    started = datetime.now(timezone.utc).isoformat()
    cases_file = resolve(cases_path)
    cases = read_cases(cases_file)[:limit] if limit else read_cases(cases_file)
    out_dir = resolve(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    check_cache_provider(out_dir / "cache", provider_identity(provider_name, model, base_url), reset_cache)
    cost_inputs = compare_versions.snapshot_cost_inputs(provider_name, model)
    pacer = Pacer(rpm, sleep=sleep, enabled=provider_name != "dry")
    paced = {stage: Paced(p, pacer) for stage, p in providers.items()}
    cache = Cache(out_dir / "cache")
    hashes = {"classifier": load_prompt(resolve(CLASSIFIER_PROMPT))[1],
              "judge": load_prompt(resolve(JUDGE_PROMPT))[1],
              **{v: load_prompt(resolve(f"prompts/main/{v}.md"))[1] for v in versions}}
    classifier_rows, answers, judged = [], {v: [] for v in versions}, {v: [] for v in versions}
    for index, case in enumerate(cases, 1):
        row = run_classifier(case, paced["classifier"], pacer, cache, model, hashes["classifier"])
        classifier_rows.append(row)
        for version in versions:
            ans = run_answer(case, version, paced["answer"], pacer, cache, model, hashes[version])
            answers[version].append(ans)
            judged[version].append(run_judge(case, version, ans, paced["judge"], cache, model, hashes["judge"]))
        if log:
            log(f"[{index}/{len(cases)}] {case['id']} classifier={row['status']} "
                + " ".join(f"{v}={judged[v][-1]['status']}:{judged[v][-1]['label']}" for v in versions))
    write_jsonl(out_dir / "classifier.jsonl", classifier_rows)
    for version in versions:
        write_jsonl(out_dir / f"answers_{version}.jsonl", answers[version])
        write_jsonl(out_dir / f"judged_{version}.jsonl", judged[version])
    write_jsonl(out_dir / "results_for_labeling.jsonl",
                [{"case_id": a["case_id"], "prompt_version": v, "answer": a["answer"]}
                 for v in versions for a in answers[v] if a["status"] == "ok"])

    def count(rows, status):
        return sum(r["status"] == status for r in rows)

    errors = {"classifier": count(classifier_rows, "error"),
              **{f"answer_{v}": count(answers[v], "error") for v in versions},
              **{f"judge_{v}": count(judged[v], "error") + count(judged[v], "skipped_answer_error")
                 for v in versions}}
    meta = {
        "git_commit": run_commit, "git_dirty": run_dirty,
        "git_dirty_note": "measured before any output file was written",
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provider": provider_name, "model": model, "dry_run": provider_name == "dry",
        "versions": list(versions), "seed": SEED, "temperature": 0,
        "answer_max_tokens": ANSWER_MAX_TOKENS, "rpm": rpm, "limit": limit,
        "cases_path": rel(cases_file), "testset_sha256": sha256_bytes(cases_file.read_bytes()),
        "prompts": {"classifier": {"path": CLASSIFIER_PROMPT, "sha256": hashes["classifier"]},
                    "judge": {"path": JUDGE_PROMPT, "sha256": hashes["judge"]},
                    **{v: {"path": f"prompts/main/{v}.md", "sha256": hashes[v]} for v in versions}},
        "counts": {"cases": len(cases), "provider_calls_this_run": pacer.calls,
                   "cache_hits": cache.hits, "cache_misses": cache.misses},
        "errors": errors,
        "cost_inputs": cost_inputs,
        "cost_inputs_note": "prices and Week 1 spend snapshotted at run start; compare_versions uses these",
        "error_policy": "A provider error marks that case's stage as error; the run continues; "
                        "an errored (or invalid-judge) case counts as incorrect.",
        "command": command or ["python", "-m", "eval.run_e2e"],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    compare_versions.compare(out_dir)
    return meta


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", required=True, choices=["gemini", "ollama", "openai_compat", "dry"])
    p.add_argument("--model", required=True)
    p.add_argument("--versions", nargs="+", default=["v1", "v2", "v3"])
    p.add_argument("--rpm", type=float, default=10)
    p.add_argument("--limit", type=int)
    p.add_argument("--out-dir", default="eval/results/week2")
    p.add_argument("--cases", default=DEFAULT_CASES)
    p.add_argument("--base-url")
    p.add_argument("--api-key-env")
    p.add_argument("--reset-cache", action="store_true",
                   help="delete <out-dir>/cache first (needed when switching provider/model/base URL)")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.rpm <= 0 or (args.limit is not None and args.limit <= 0):
        parser().error("rpm and limit must be positive")
    try:
        base = make_provider(args.provider, args.model, args.base_url, args.api_key_env)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    providers = {"classifier": base, "answer": base,
                 "judge": DryJudgeProvider() if args.provider == "dry" else base}
    command = ["python", "-m", "eval.run_e2e", *(sys.argv[1:] if argv is None else argv)]
    for i, part in enumerate(command[:-1]):
        if part == "--base-url":
            command[i + 1] = "[redacted]"
    try:
        meta = run(provider_name=args.provider, model=args.model, versions=args.versions,
                   out_dir=args.out_dir, providers=providers, rpm=args.rpm, limit=args.limit,
                   cases_path=args.cases, command=command, log=lambda m: print(m, file=sys.stderr),
                   base_url=args.base_url, reset_cache=args.reset_cache)
    except CacheProviderMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"counts": meta["counts"], "errors": meta["errors"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
