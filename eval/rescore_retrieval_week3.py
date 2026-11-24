"""Re-score the recorded Week 3 retrieval rankings offline. No model is loaded.

    python -m eval.rescore_retrieval_week3

The rankings in eval/results/week3/retrieval/<variant>.jsonl were produced by
eval/retrieval_week3.py at commit 22577a6 in a working tree with uncommitted
changes ("dirty": true in summary.json). This script does not change that
provenance: it re-applies the committed scoring code to the recorded rankings
and the committed test set, checks that the recorded per-case metrics and the
recorded summary are reproduced exactly, and writes rescored_summary.json with
Wilson 95% intervals. A fresh ranking run with the pinned local models at a
clean tagged commit is still needed to remove the dirty-tree caveat.
"""
import argparse
import json
from pathlib import Path

from eval.retrieval_week3 import VARIANTS, score_retrieval, summarize
from eval.stats import wilson_ci
from eval.week3_provenance import CASES, cases_content_hash, read_cases
from src.rag.corpus import ROOT, digest

RESULTS = ROOT/"eval/results/week3/retrieval"


def rescore(results_dir=RESULTS, cases_path=CASES):
    results_dir = Path(results_dir)
    recorded = json.loads((results_dir/"summary.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in read_cases(cases_path)}
    summaries, checks = {}, {}
    for name in VARIANTS:
        path = results_dir/f"{name}.jsonl"
        rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
        if sorted(r["case_id"] for r in rows) != sorted(cases):
            raise ValueError(f"{name}: recorded case IDs differ from the test set")
        rescored, same_gold, same_metrics = [], True, True
        for row in rows:
            case = cases[row["case_id"]]
            groups = case.get("gold_groups", [[g] for g in case["gold"]])
            same_gold &= row["gold"] == case["gold"] and row["gold_groups"] == groups and row["answerable"] == case["answerable"]
            metrics = score_retrieval(row["results"], case["gold"], gold_groups=case.get("gold_groups")) if case["answerable"] else None
            same_metrics &= metrics == row["metrics"]
            rescored.append({**row, "answerable": case["answerable"], "metrics": metrics})
        summary = summarize(rescored)
        answerable = [r for r in rescored if r["answerable"]]
        n = len(answerable)
        summary["wilson_95"] = {
            **{f"hit_at_{k}": list(wilson_ci(sum(r["metrics"]["hit"][k] for r in answerable), n)[1:]) for k in ("1", "3", "5", "10")},
            "all_gold_hit_at_5": list(wilson_ci(sum(r["metrics"]["all_gold_hit_at_5"] for r in answerable), n)[1:])}
        summary["counts"] = {"hit_at_5": sum(r["metrics"]["hit"]["5"] for r in answerable),
                             "all_gold_hit_at_5": sum(r["metrics"]["all_gold_hit_at_5"] for r in answerable)}
        summaries[name] = summary
        checks[name] = {"recorded_gold_equals_committed_gold": same_gold,
                        "recorded_case_metrics_reproduced": same_metrics,
                        "recorded_summary_reproduced": {k: v for k, v in summary.items() if k in recorded["summaries"][name]}
                                                       == recorded["summaries"][name],
                        "rankings_sha256": digest(path.read_bytes())}
    ok = all(v for c in checks.values() for k, v in c.items() if k != "rankings_sha256")
    return {"stage": "retrieval_rescore_from_recorded_rankings",
            "is_fresh_model_run": False,
            "note": ("Metrics recomputed offline from the recorded rankings with the committed scoring code and test set; "
                     "no retrieval model was run. The rankings themselves come from the run described in summary.json."),
            "ranking_run": {"git": recorded["git"], "started_utc": recorded["started_utc"],
                            "corpus_sha256": recorded["corpus_sha256"], "cases_sha256": recorded["cases_sha256"],
                            "index_sha256": recorded["index_sha256"], "config_sha256": recorded["config_sha256"],
                            "summary_sha256": digest((results_dir/"summary.json").read_bytes())},
            "open_issue": ("Rankings were produced from a working tree with uncommitted changes (dirty=true) at 22577a6, "
                           "before the citizen-v2 commit; rerun eval/retrieval_week3.py with the pinned local models "
                           "at a clean tagged commit to close this."),
            "scoring_inputs": {"cases_sha256": digest(Path(cases_path).read_bytes()),
                               "cases_content_sha256": cases_content_hash(list(cases.values())),
                               "scoring_code_sha256": digest((ROOT/"eval/retrieval_week3.py").read_bytes()),
                               "rescore_code_sha256": digest(Path(__file__).read_bytes())},
            "checks": checks, "all_checks_pass": ok, "summaries": summaries}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", type=Path, default=RESULTS)
    args = p.parse_args(argv)
    result = rescore(args.results_dir)
    if not result["all_checks_pass"]:
        raise SystemExit(json.dumps(result["checks"], indent=2))
    (args.results_dir/"rescored_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v["hit_at_k"]["5"] for k, v in result["summaries"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
