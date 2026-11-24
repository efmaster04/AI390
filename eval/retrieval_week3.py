"""Retrieval-only evaluation. No generated answers and no LLM judge calls.

    python -m eval.retrieval_week3 --out-dir eval/results/week3/retrieval

Gold evidence is an exact quote in a stable source passage, not a window ID.
Unanswerable control questions are excluded from hit/MRR denominators. Finding
some nearby text is never reported as proof that those questions are answerable.
"""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import statistics
import subprocess

from src.rag.corpus import ROOT, digest, permitted
from src.rag.retrieval import Retriever
from src.rag.chunking import chunk_report

VARIANTS = {"hybrid_rerank": ("hybrid", True), "dense_rerank": ("dense", True),
            "hybrid_no_rerank": ("hybrid", False)}


def read_cases(path, documents):
    rows = [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]
    ids, passages = set(), {p.passage_id: p for d in documents for p in d.passages}
    access = {p.passage_id: d.access for d in documents for p in d.passages}
    for case in rows:
        if case["id"] in ids:
            raise ValueError("Duplicate retrieval case ID")
        ids.add(case["id"])
        if case["split"] != "test" or type(case["answerable"]) is not bool:
            raise ValueError("Only the frozen test split may be scored here")
        if case["review_status"] not in {"draft", "approved"} or case["lang"] not in {"tr", "en"}:
            raise ValueError("Invalid review status or language")
        if not isinstance(case["text"], str) or not case["text"].strip():
            raise ValueError("Question text is empty")
        permitted(("public",), case["role"])
        if bool(case["gold"]) != case["answerable"]:
            raise ValueError("Answerable cases need gold evidence; unanswerable cases must have none")
        for gold in case["gold"]:
            if gold["passage_id"] not in passages or not gold["quote"].strip():
                raise ValueError("Missing gold passage or quote")
            if gold["quote"] not in passages[gold["passage_id"]].text:
                raise ValueError(f"{case['id']}: gold quote is absent from the source")
            if not permitted(access[gold["passage_id"]], case["role"]):
                raise ValueError(f"{case['id']}: gold source is not authorized for this role")
    return rows


def score_retrieval(results, gold):
    def matches(chunk, item):
        return chunk["passage_id"] == item["passage_id"] and item["quote"] in chunk["text"]
    ranks = [r["rank"] for r in results if any(matches(r, g) for g in gold)]
    first = min(ranks) if ranks else None
    return {"first_relevant_rank": first, "reciprocal_rank": 1/first if first else 0,
            "hit": {str(k): first is not None and first <= k for k in (1, 3, 5, 10)},
            "all_gold_hit_at_5": all(any(r["rank"] <= 5 and matches(r, g) for r in results) for g in gold)}


def summarize(rows):
    answerable = [r for r in rows if r["answerable"]]
    n = len(answerable)
    if not n:
        raise ValueError("Need answerable questions to measure retrieval")
    return {"n_answerable": n, "n_unanswerable_controls": len(rows)-n,
            "hit_at_k": {str(k): sum(r["metrics"]["hit"][str(k)] for r in answerable)/n for k in (1, 3, 5, 10)},
            "mrr_at_10": sum(r["metrics"]["reciprocal_rank"] for r in answerable)/n,
            "all_gold_hit_at_5": sum(r["metrics"]["all_gold_hit_at_5"] for r in answerable)/n,
            "by_language": {lang: {"n": len(part), "hit_at_5": sum(r["metrics"]["hit"]["5"] for r in part)/len(part),
                                       "mrr_at_10": sum(r["metrics"]["reciprocal_rank"] for r in part)/len(part)}
                            for lang in sorted({r["lang"] for r in answerable})
                            if (part := [r for r in answerable if r["lang"] == lang])},
            "query_latency_p50_s": statistics.median(r["timings_s"]["total"] for r in rows)}


def git_state():
    def call(*args):
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else None
    dirty = call("status", "--porcelain")
    return {"commit": call("rev-parse", "HEAD"), "dirty": None if dirty is None else bool(dirty)}


def run(cases_path, out_dir):
    started = datetime.now(timezone.utc).isoformat()
    git = git_state()
    retriever = Retriever()
    cases = read_cases(cases_path, retriever.documents)
    cases_hash = digest(Path(cases_path).read_bytes())
    code_hashes = {str(p.relative_to(ROOT)): digest(p.read_bytes())
                   for p in [*sorted((ROOT/"src/rag").glob("*.py")), Path(__file__)]}
    if sum(c["answerable"] for c in cases) < 30:
        raise ValueError("W3.5 requires at least 30 answerable retrieval questions in this benchmark")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Warm both models; model loading and first-call setup excluded from query latency.
    retriever.search("su aboneliği", k=1, cache_scores=False)
    summaries, failures = {}, []
    for name, (mode, rerank) in VARIANTS.items():
        rows = []
        for i, case in enumerate(cases, 1):
            result = retriever.search(case["text"], role=case["role"], k=10,
                                      mode=mode, rerank=rerank, cache_scores=False)
            metrics = score_retrieval(result["results"], case["gold"]) if case["answerable"] else None
            row = {"case_id": case["id"], "lang": case["lang"], "answerable": case["answerable"],
                   "review_status": case["review_status"], "gold": case["gold"],
                   "metrics": metrics, **result}
            rows.append(row)
            if metrics and not metrics["hit"]["5"]:
                failures.append({"case_id": case["id"], "variant": name, "failure_stage": "retrieval",
                                 "gold": case["gold"], "top5": [r["passage_id"] for r in result["results"][:5]],
                                 "gold_in_candidates": any(g["passage_id"] in result["candidate_passage_ids"] for g in case["gold"]),
                                 "root_cause": "gold_outside_candidate_pool" if not any(
                                     g["passage_id"] in result["candidate_passage_ids"] for g in case["gold"])
                                     else "gold_in_candidates_but_below_top5",
                                 "interpretation": "Ranking observation only; question/gold labels still need independent human review."})
            print(f"[{name}] {i}/{len(cases)} {case['id']}", flush=True)
        (out/f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows), encoding="utf-8")
        summaries[name] = summarize(rows)
    if digest(Path(cases_path).read_bytes()) != cases_hash:
        raise ValueError("Test set changed during evaluation; rerun every variant on one frozen set")
    if any(digest((ROOT/p).read_bytes()) != h for p, h in code_hashes.items()):
        raise ValueError("Retrieval code changed during evaluation; rerun every variant")
    state = {"stage": "retrieval_only", "provisional": any(c["review_status"] != "approved" for c in cases)
             or any(d.review_status != "approved" for d in retriever.documents),
             "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
             "git": git, "api_calls": 0, "config": retriever.config,
             "config_sha256": digest((ROOT/"config/retrieval.json").read_bytes()),
             "corpus_sha256": retriever.corpus_sha256, "index_sha256": retriever.index_sha256,
             "cases_sha256": cases_hash, "code_sha256": code_hashes,
             "python": platform.python_version(),
             "packages": {n: importlib.metadata.version(n) for n in
                          ["sentence-transformers", "transformers", "torch", "numpy", "huggingface-hub"]},
             "latency_note": "CPU warm inference; query and reranker score caches disabled; index embeddings cached; single run",
             "metric_note": "Hit@k = at least one gold quote found; MRR truncated at 10; controls excluded; not answer accuracy",
             "summaries": summaries, "ablations": {
                 "dense_vs_hybrid": {"base": "hybrid_rerank", "changed": "dense_rerank", "only_change": "candidate retrieval method"},
                 "reranker_off": {"base": "hybrid_rerank", "changed": "hybrid_no_rerank", "only_change": "reranking"}}}
    (out/"summary.json").write_text(json.dumps(state, ensure_ascii=False, indent=2)+"\n")
    (out/"failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2)+"\n")
    (out/"chunks.json").write_text(json.dumps(chunk_report(retriever.chunks), ensure_ascii=False, indent=2)+"\n")
    return state


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", type=Path, default=ROOT/"eval/testsets/week3_retrieval.jsonl")
    p.add_argument("--out-dir", type=Path, default=ROOT/"eval/results/week3/retrieval")
    args = p.parse_args()
    print(json.dumps(run(args.cases, args.out_dir)["summaries"], indent=2))


if __name__ == "__main__":
    main()
