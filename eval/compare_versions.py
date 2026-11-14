"""W2.5 version comparison + scoreboard, recomputed from a saved run directory (no API calls).

    python -m eval.compare_versions --run-dir eval/results/week2

Reads run_meta.json, classifier.jsonl, answers_vN.jsonl, judged_vN.jsonl and the test set
(read at compare time; labels are never cached) and writes comparison.json, comparison.md
and scoreboard.json. Output is a pure function of those files, so a rerun is byte-identical.

Judge verdicts are checked against the current test set: if a judged case's judge input
(text, expected_behavior, answerable, answer) changed since it was judged, compare stops
(exit 1) and asks for a run_e2e rerun, unless --allow-stale is given. Classifier accuracy
is recomputed from the current labels (no model call) and the labels' sha256 is recorded.
Prices and Week 1 spend come from the run_meta.json snapshot taken at run time; the
config files are only a fallback for older run dirs (the source used is recorded).
"""

import argparse
import hashlib
from collections import Counter, defaultdict
import json
import re
from pathlib import Path
import statistics
import sys

from eval.answer import resolve
from eval.stats import mcnemar, wald_ci, wilson_ci


ROOT = Path(__file__).resolve().parents[1]
PRICES = "config/prices.json"
WEEK1_COST = "eval/results/week1/cost_summary.json"
SCRIPT = "eval/run_e2e.py -> eval/compare_versions.py"


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def judged_input(case, answer):
    """The exact judge input run_e2e hashes into the judge cache key (shared, never duplicated)."""
    return json.dumps([case["text"], case["expected_behavior"], case["answerable"], answer],
                      ensure_ascii=False)


class StaleJudgementsError(ValueError):
    def __init__(self, case_ids, run_dir):
        self.case_ids = case_ids
        super().__init__(
            f"Stale judge verdicts for {len(case_ids)} case(s): {', '.join(case_ids)}. Their judge input "
            "(text, expected_behavior, answerable or answer) changed since they were judged. Rerun "
            f"`python -m eval.run_e2e` with the same provider/model/versions and --out-dir {run_dir}: "
            "classifier and answer calls come from the cache and only these cases are re-judged (the "
            "judge cache key covers the judge input). Or pass --allow-stale to compare anyway.")


def stale_judgements(judged, answers, cases, testset_changed):
    """Case ids whose recorded judge verdict no longer matches the current judge input.

    Rows without judge_input_sha256 (written before it was recorded) can only be checked
    through the test set hash: they count as stale when the test set changed since the run.
    """
    stale = set()
    for version, rows in judged.items():
        answer_by_case = {a["case_id"]: a for a in answers[version]}
        for row in rows:
            if row["status"] == "skipped_answer_error":
                continue
            stored = row.get("judge_input_sha256")
            if stored is None:
                if testset_changed:
                    stale.add(row["case_id"])
                continue
            answer = (answer_by_case.get(row["case_id"]) or {}).get("answer")
            if answer is None or sha256_text(judged_input(cases[row["case_id"]], answer)) != stored:
                stale.add(row["case_id"])
    return sorted(stale)


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def proportion(k, n):
    """{k, n, value, wald_ci95, wilson_ci95}; value/intervals are null when n == 0."""
    if not n:
        return {"k": k, "n": n, "value": None, "wald_ci95": None, "wilson_ci95": None}
    p, lo, hi = wald_ci(k, n)
    _, wlo, whi = wilson_ci(k, n)
    return {"k": k, "n": n, "value": p, "wald_ci95": [lo, hi], "wilson_ci95": [wlo, whi]}


def _issue_field(result, field):
    return Counter(issue.get(field) for issue in (result or {}).get("issues") or [])


def classifier_metrics(rows, cases):
    n = len(rows)
    counts = Counter()
    issue_cases = 0
    attempts = [r["attempts"] for r in rows if r.get("attempts")]
    labels = {r["case_id"]: cases[r["case_id"]]["expected"] for r in rows}
    for row in rows:
        expected = cases[row["case_id"]]["expected"]
        got = row["result"] if row["status"] == "ok" else None
        counts["valid"] += row["status"] == "ok"
        if got is None:
            issue_cases += bool(expected["issues"])
            continue
        counts["intent"] += got.get("intent") == expected["intent"]
        pairs = lambda obj: Counter((i.get("category"), i.get("urgency")) for i in obj.get("issues") or [])
        counts["issues"] += pairs(got) == pairs(expected)
        counts["missing_fields"] += set(got.get("missing_fields") or []) == set(expected["missing_fields"])
        if expected["issues"]:
            issue_cases += 1
            for field in ("urgency", "category", "scope"):
                counts[field] += _issue_field(got, field) == _issue_field(expected, field)
    return {
        "definitions": {
            "intent": "primary intent exact match; n = all cases",
            "issues_match": "multiset of (category, urgency) over issues equals expected; n = all cases",
            "urgency/category/scope": "multiset of that field over issues equals expected; "
                                      "n = cases whose expected issues are non-empty",
            "missing_fields": "set equality; n = all cases",
            "json_valid": "schema-valid result after retries; provider errors count as invalid",
            "errors": "errored or invalid classifier output counts as incorrect on every field",
            "labels": "expected labels are read from the test set at compare time (never cached); "
                      "labels_sha256 identifies the labels used",
        },
        "labels_sha256": sha256_text(json.dumps(labels, sort_keys=True, ensure_ascii=False)),
        "intent": proportion(counts["intent"], n),
        "issues_match": proportion(counts["issues"], n),
        "urgency": proportion(counts["urgency"], issue_cases),
        "category": proportion(counts["category"], issue_cases),
        "scope": proportion(counts["scope"], issue_cases),
        "missing_fields": proportion(counts["missing_fields"], n),
        "json_valid": proportion(counts["valid"], n),
        "mean_attempts": statistics.fmean(attempts) if attempts else None,
        "errors": sum(r["status"] == "error" for r in rows),
    }


# Deterministic fabrication check (Week 2): the system has no contact directory, so any
# phone number, URL or e-mail address in an answer is unsupported. Applied on top of the
# LLM judge because judge v2 missed invented numbers (e.g. "444 00 00") in 5 v2 answers.
CONTACT_RE = re.compile(
    r"(?<!\d)(?:\+?90[\s-]?)?(?:0?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}|\d{3}[\s-]\d{2}[\s-]\d{2}|\d{3}[\s-]\d[\s-]?\d{3})(?!\d)"
    r"|https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.]+")


def contact_fabrication(answer):
    return bool(answer) and bool(CONTACT_RE.search(answer))


def version_metrics(judged, answers, cases):
    answer_text = {a["case_id"]: a.get("answer") or "" for a in answers}
    rule_hit = {r["case_id"]: contact_fabrication(answer_text.get(r["case_id"], "")) for r in judged}
    correct = [r["label"] == "pass" and not rule_hit[r["case_id"]] for r in judged]
    unanswerable = [r for r in judged if cases[r["case_id"]]["answerable"] is False]
    valid = [r for r in judged if r["valid"]]
    by_type = defaultdict(lambda: [0, 0])
    for row, ok in zip(judged, correct):
        cell = by_type[cases[row["case_id"]]["type"]]
        cell[0] += ok
        cell[1] += 1
    return correct, {
        "accuracy": proportion(sum(correct), len(correct)),
        "abstention_correct": proportion(
            sum(r["abstained"] is True and r["label"] == "pass" and not rule_hit[r["case_id"]]
                for r in unanswerable), len(unanswerable)),
        "fabrication_rate": proportion(
            sum(r["fabrication"] is True or rule_hit[r["case_id"]] for r in valid), len(valid)),
        "contact_rule_hits": sorted(cid for cid, hit in rule_hit.items() if hit),
        "unperformed_action_rate": proportion(
            sum(r["claims_unperformed_action"] is True for r in valid), len(valid)),
        "by_type": {t: proportion(k, n) for t, (k, n) in sorted(by_type.items())},
        "errors": {"answer": sum(a["status"] == "error" for a in answers),
                   "judge_error": sum(r["status"] in ("error", "skipped_answer_error") for r in judged),
                   "judge_invalid": sum(r["status"] == "invalid" for r in judged)},
    }


def injection_field(run_dir):
    """W2.8 result from <run_dir>/injection/summary.json when present."""
    path = Path(run_dir) / "injection" / "summary.json"
    if not path.exists():
        return {"value": None, "n": None, "script": None}
    groups = json.loads(path.read_text(encoding="utf-8"))["groups"]
    k, n = sum(g["successes"] for g in groups), sum(g["n"] for g in groups)
    return {"value": (k / n) if n else None, "n": n, "script": "eval/injection/run_injection.py"}


def price_for(meta, prices):
    return next((p for p in prices if p["provider"] == meta["provider"] and p["model"] == meta["model"]), None)


def load_prices():
    return json.loads((ROOT / PRICES).read_text(encoding="utf-8"))


def week1_spend():
    """(spend_usd or None, file present). None when any Week 1 row has an unknown spend."""
    path = ROOT / WEEK1_COST
    if not path.exists():
        return None, False
    spent = [r.get("actual_spend_usd") for r in json.loads(path.read_text(encoding="utf-8"))["results"]]
    return (sum(spent) if spent and None not in spent else None), True


def snapshot_cost_inputs(provider, model):
    """Prices and Week 1 spend as they are at run time; stored in run_meta.json."""
    prices_raw = (ROOT / PRICES).read_bytes()
    spend, present = week1_spend()
    return {"price": price_for({"provider": provider, "model": model}, json.loads(prices_raw)),
            "prices_path": PRICES, "prices_sha256": hashlib.sha256(prices_raw).hexdigest(),
            "week1_spend_usd": spend, "week1_cost_path": WEEK1_COST, "week1_cost_present": present}


def cost_inputs(meta):
    """(price, week1_spend, sources): run_meta.json snapshot first, config files as fallback."""
    snap = meta.get("cost_inputs") or {}
    if "price" in snap:
        price, price_src = snap["price"], "run_meta.json"
    else:
        price, price_src = price_for(meta, load_prices()), PRICES
    if "week1_spend_usd" in snap:
        week1, week1_src = snap["week1_spend_usd"], "run_meta.json"
    else:
        week1, week1_src = week1_spend()[0], WEEK1_COST
    return price, week1, {"price": price_src, "week1_spend": week1_src}


def usd(tokens_in, tokens_out, price):
    if price is None or None in (tokens_in, tokens_out, price["price_in_per_1m_usd"], price["price_out_per_1m_usd"]):
        return None
    return tokens_in / 1e6 * price["price_in_per_1m_usd"] + tokens_out / 1e6 * price["price_out_per_1m_usd"]


def mean_or_none(values):
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def strict_mean(values):
    """Mean, or None when there are no values or any value is unknown (never silently dropped)."""
    return None if not values or None in values else statistics.fmean(values)


def _unknown_tokens(row):
    return row.get("input_tokens") is None or row.get("output_tokens") is None


def strict_sum(values):
    return None if None in values else sum(values)


def costs(meta, classifier, answers, judged, best, price, week1, sources):
    cls = {r["case_id"]: r for r in classifier}
    per_task = [usd(*(None if cls[a["case_id"]][k] is None or a[k] is None else cls[a["case_id"]][k] + a[k]
                      for k in ("input_tokens", "output_tokens")), price) for a in answers[best]]
    judge_rows = [r for r in judged[best] if r["attempts"]]
    judge_cost = [usd(r["input_tokens"], r["output_tokens"], price) for r in judge_rows]
    every = [*classifier, *(a for v in answers for a in answers[v]), *(r for v in judged for r in judged[v])]
    unknown_rows = sum(_unknown_tokens(r) for r in every)
    tok_in = strict_sum([r.get("input_tokens") for r in every])
    tok_out = strict_sum([r.get("output_tokens") for r in every])
    list_total = usd(tok_in, tok_out, price)
    if meta["provider"] == "dry" or (price and price["free_tier"]):
        actual = 0.0
    else:
        actual = list_total
    return {
        "basis": "list price from config/prices.json applied to measured token counts "
                 "(thinking tokens counted as output); NOT billed: the free tier bills 0 USD",
        "price": price,
        "cost_inputs_source": sources,
        "cost_incomplete": unknown_rows > 0,
        "rows_with_unknown_tokens": unknown_rows,
        "cost_per_task_list_usd": strict_mean(per_task),
        "cost_per_task_definition": f"classifier + answer ({best}) tokens per case; judge excluded",
        "eval_judge_cost_per_task_list_usd": strict_mean(judge_cost),
        "week_tokens": {"input": tok_in, "output": tok_out,
                        "note": "all stages and versions recorded in this run dir (cached calls counted once); "
                                "null when any row has an unknown token count"},
        "week_list_price_equivalent_usd": list_total,
        "spend_week_usd": actual,
        "spend_week1_usd": week1,
        "spend_total_usd": None if actual is None or week1 is None else actual + week1,
    }


def latency_p50(classifier, answers):
    cls = {r["case_id"]: r for r in classifier}
    values = [cls[a["case_id"]]["latency_s"] + a["latency_s"] for a in answers
              if a["status"] == "ok" and cls[a["case_id"]]["status"] != "error"
              and cls[a["case_id"]]["latency_s"] is not None and a["latency_s"] is not None]
    return (statistics.median(values) if values else None), len(values)


def reading(versions, best_pair, test):
    if test is None:
        return "Only one version was run, so no paired comparison is possible."
    a, b = best_pair
    base = (f"{a} and {b} disagree on {test['a_only'] + test['b_only']} of {test['n']} paired cases "
            f"({a} alone correct on {test['a_only']}, {b} alone correct on {test['b_only']}); "
            f"exact McNemar p = {test['p_exact']:.3f}.")
    if test["p_exact"] > 0.05:
        return (base + f" At the 0.05 level this does not show a difference: {a} ranks first on this test set, "
                "but the data are compatible with the two versions being equally accurate, so we do not claim "
                f"{a} is better. The result is one run at temperature 0 on a small set, judged by an LLM judge.")
    return (base + f" At the 0.05 level the difference is unlikely to be chance alone on this test set. "
            "It is one run at temperature 0 on a small set, judged by an LLM judge, so it says nothing "
            "about other cases or settings.")


def fmt(p):
    if p is None or p.get("value") is None:
        return "n/a"
    return f"{p['value']:.3f} ({p['k']}/{p['n']})"


def fmt_ci(ci):
    return "n/a" if ci is None else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def markdown(comp):
    lines = ["# Week 2 prompt version comparison (W2.5)", "",
             f"Run: provider `{comp['run']['provider']}`, model `{comp['run']['model']}`, commit "
             f"`{comp['run']['git_commit']}` (dirty: {comp['run']['git_dirty']}), n = {comp['n']} cases."
             + (" **Dry run: synthetic outputs, not a measurement.**" if comp["run"]["dry_run"] else ""), "",
             "Correct = LLM judge label `pass` and no phone number, URL or e-mail in the answer (deterministic rule). Errored or invalid-judge cases count as incorrect. "
             "Intervals are 95%; Wald collapses at 0/n and n/n, so Wilson is shown alongside.", "",
             "| Version | Accuracy | Wald CI | Wilson CI | Abstention correct | Fabrication rate | "
             "Unperformed-action claims | Errors (answer/judge/invalid) |",
             "|---|---|---|---|---|---|---|---|"]
    for v, m in comp["versions"].items():
        e = m["errors"]
        lines.append(f"| {v} | {fmt(m['accuracy'])} | {fmt_ci(m['accuracy']['wald_ci95'])} | "
                     f"{fmt_ci(m['accuracy']['wilson_ci95'])} | {fmt(m['abstention_correct'])} | "
                     f"{fmt(m['fabrication_rate'])} | {fmt(m['unperformed_action_rate'])} | "
                     f"{e['answer']}/{e['judge_error']}/{e['judge_invalid']} |")
    lines += ["", f"Best version by accuracy: **{comp['best_version']}**"
              + (" (accuracy tie broken by fabrication rate, then unperformed-action rate, then version order)" if comp["tie"] else "") + ".", ""]
    t = comp["mcnemar"]
    if t:
        lines += [f"## McNemar: {t['a']} vs {t['b']}", "",
                  f"b ({t['a']} only correct) = {t['b_count']}, c ({t['b']} only correct) = {t['c_count']}, "
                  f"p_exact = {t['p_exact']:.4f}, method = {t['method']}"
                  + (f", p_chi2_cc = {t['p_chi2_cc']:.4f}" if t["p_chi2_cc"] is not None else "") + ".", ""]
    if comp.get("stale_judgements"):
        lines += ["**Stale judge verdicts (compared with --allow-stale):** "
                  + ", ".join(comp["stale_judgements"]) + ". Rerun eval.run_e2e to re-judge them.", ""]
    lines += ["## Plain reading", "", comp["reading"], "", "## Accuracy by case type", "",
              "| Type | " + " | ".join(comp["versions"]) + " |",
              "|---|" + "---|" * len(comp["versions"])]
    types = sorted({t for m in comp["versions"].values() for t in m["by_type"]})
    for kind in types:
        lines.append(f"| {kind} | " + " | ".join(fmt(m["by_type"].get(kind)) for m in comp["versions"].values()) + " |")
    lines += ["", f"Reproduce: `python -m eval.compare_versions --run-dir {comp['run']['run_dir']}`.", ""]
    return "\n".join(lines)


def ci_pair(p):
    return {"value": p["value"], "ci95": p["wald_ci95"], "n": p["n"], "script": SCRIPT}


def compare(run_dir, cases_path=None, allow_stale=False):
    run_dir = resolve(run_dir)
    meta = json.loads((run_dir / "run_meta.json").read_text(encoding="utf-8"))
    cases_file = resolve(cases_path or meta["cases_path"])
    cases = {c["id"]: c for c in read_jsonl(cases_file)}
    testset_sha = hashlib.sha256(cases_file.read_bytes()).hexdigest()
    classifier = read_jsonl(run_dir / "classifier.jsonl")
    versions = meta["versions"]
    answers = {v: read_jsonl(run_dir / f"answers_{v}.jsonl") for v in versions}
    judged = {v: read_jsonl(run_dir / f"judged_{v}.jsonl") for v in versions}
    unknown = {r["case_id"] for r in classifier} - cases.keys()
    if unknown:
        raise ValueError(f"Run contains case ids missing from the test set: {sorted(unknown)}")
    vectors, metrics = {}, {}
    for v in versions:
        if [r["case_id"] for r in judged[v]] != [r["case_id"] for r in classifier]:
            raise ValueError(f"judged_{v}.jsonl is not aligned with classifier.jsonl")
        vectors[v], metrics[v] = version_metrics(judged[v], answers[v], cases)
    def _rate(v, key):
        value = metrics[v][key]["value"]
        return 1.0 if value is None else value
    # Ties on accuracy are broken by fewer fabrications, then fewer unperformed-action claims,
    # then version order (a version that fabricates must not win a tie by position).
    ranking = sorted(versions, key=lambda v: (-(metrics[v]["accuracy"]["value"] or 0),
                                              _rate(v, "fabrication_rate"),
                                              _rate(v, "unperformed_action_rate"),
                                              versions.index(v)))
    best = ranking[0]
    tie = len(ranking) > 1 and metrics[ranking[0]]["accuracy"]["k"] == metrics[ranking[1]]["accuracy"]["k"]
    test = None
    if len(ranking) > 1:
        a, b = ranking[:2]
        raw = mcnemar(vectors[a], vectors[b])
        test = {"a": a, "b": b, "b_count": raw["a_only"], "c_count": raw["b_only"], **raw}
    stale = stale_judgements(judged, answers, cases, testset_sha != meta["testset_sha256"])
    if stale and not allow_stale:
        raise StaleJudgementsError(stale, _rel(run_dir))
    price, week1, sources = cost_inputs(meta)
    cost = costs(meta, classifier, answers, judged, best, price, week1, sources)
    p50, p50_n = latency_p50(classifier, answers[best])
    run_info = {k: meta[k] for k in ("provider", "model", "git_commit", "git_dirty", "dry_run",
                                     "started_utc", "testset_sha256", "versions")}
    run_info["run_dir"] = _rel(run_dir)
    run_info["testset_sha256_at_compare"] = testset_sha
    run_info["testset_changed_since_run"] = testset_sha != meta["testset_sha256"]
    comparison = {
        "n": len(classifier), "run": run_info, "versions": metrics,
        "ranking": ranking, "best_version": best, "tie": tie,
        "mcnemar": test, "reading": reading(versions, ranking[:2], test),
        "stale_judgements": stale,
        "notes": ["correct = judge label pass AND no phone number, URL or e-mail in the answer (deterministic contact-fabrication rule; the system has no contact directory this week); errored or invalid judge outputs count as incorrect",
                  "abstention_correct = among answerable=false cases, judge abstained AND label pass",
                  "fabrication/unperformed-action rates are over schema-valid judge outputs",
                  "McNemar is between the two highest-ranked versions (accuracy; ties broken by fabrication rate, unperformed-action rate, then version order)"],
    }
    cls_metrics = classifier_metrics(classifier, cases)
    board = {
        "week": 2,
        "test_set_size": len(classifier),
        "e2e_accuracy": ci_pair(metrics[best]["accuracy"]),
        "abstention_correct": ci_pair(metrics[best]["abstention_correct"]),
        "unsupported_claims": {"value": None, "n": None, "script": None},
        "hit_at_5": {"value": None, "n": None, "script": None},
        "mrr": {"value": None, "n": None, "script": None},
        "task_success": {"value": None, "n": None, "script": None},
        "pass_k": {"k": None, "value": None, "n": None, "script": None},
        "injection_success": injection_field(run_dir),
        "cost_per_task_usd": cost["cost_per_task_list_usd"],
        "latency_p50_s": p50,
        "spend_week_usd": cost["spend_week_usd"],
        "spend_total_usd": cost["spend_total_usd"],
        "best_version": best,
        "dry_run": meta["dry_run"],
        "cost_incomplete": cost["cost_incomplete"],
        "stale_judgements": stale,
        "notes": {
            "e2e_accuracy": f"main prompt {best} (best of {', '.join(versions)} by accuracy); "
                            "ci95 = Wald; errored cases count as incorrect",
            "cost_per_task_usd": "LIST-PRICE EQUIVALENT (config/prices.json) of classifier + answer tokens; "
                                 "actual billed cost on the free tier is 0",
            "latency_p50_s": f"classifier + answer latency, judge excluded, pacing waits excluded; "
                             f"n = {p50_n} cases without stage errors",
            "spend": "actual USD billed (free tier = 0); list-price equivalent under list_price",
        },
        "list_price": {k: cost[k] for k in ("basis", "cost_inputs_source", "rows_with_unknown_tokens",
                                            "eval_judge_cost_per_task_list_usd",
                                            "week_list_price_equivalent_usd", "week_tokens")},
        "classifier": cls_metrics,
        "errors": meta["errors"],
    }
    comparison["classifier"] = cls_metrics
    dump = lambda obj: json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    (run_dir / "comparison.json").write_text(dump(comparison), encoding="utf-8")
    (run_dir / "comparison.md").write_text(markdown(comparison), encoding="utf-8")
    (run_dir / "scoreboard.json").write_text(dump(board), encoding="utf-8")
    return comparison, board


def _rel(path):
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-dir", default="eval/results/week2")
    p.add_argument("--cases", help="override the test set path recorded in run_meta.json")
    p.add_argument("--allow-stale", action="store_true",
                   help="compare even if judge verdicts are stale (listed under stale_judgements)")
    args = p.parse_args(argv)
    try:
        comparison, _ = compare(args.run_dir, args.cases, allow_stale=args.allow_stale)
    except StaleJudgementsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(markdown(comparison))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
