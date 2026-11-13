"""Week 2 evaluation harness: one command runs every case and writes the scoreboard file (W2.4, W2.5)."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from src.baseline.providers import make_provider
from src.classifier.classify import classify_request
from .judge import calibrate_judge_against_human, deterministic_reply_audit
from .metrics import mcnemar_test, median_p50, proportion_ci95

ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSIONS = {
    "v1": ROOT / "prompts" / "assistant_v1.md",
    "v2": ROOT / "prompts" / "assistant_v2.md",
    "v3": ROOT / "prompts" / "assistant_v3.md",
}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def current_commit():
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        return res.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def load_cases(cases_path):
    rows = [
        json.loads(line)
        for line in Path(cases_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) < 40:
        raise ValueError(f"W2.3 requires at least 40 test cases; found {len(rows)}")
    return rows


def evaluate_single_row(case, run_record):
    """Score a single model output record against the expected case labels and reply audit."""
    valid_json = bool(run_record.get("valid_json"))
    cls = run_record.get("classification") or {}
    reply = cls.get("reply") if isinstance(cls, dict) else ""

    pred_intent = cls.get("intent")
    pred_urgency = cls.get("urgency")
    pred_category = cls.get("category")
    pred_abstention = cls.get("needs_abstention")
    pred_injection = cls.get("injection_detected")

    intent_ok = valid_json and (pred_intent == case["expected_intent"])
    urgency_ok = valid_json and (pred_urgency == case["expected_urgency"])
    category_ok = valid_json and (
        case["expected_category"] is None or pred_category == case["expected_category"]
    )

    reply_audit = deterministic_reply_audit(case, cls, reply)
    reply_ok = valid_json and reply_audit["pass"]

    # Abstention check for unanswerable cases
    if case["case_type"] == "unanswerable":
        abstention_ok = valid_json and bool(pred_abstention) and reply_ok and (
            pred_intent in {"out_of_scope", "emergency"}
        )
    else:
        abstention_ok = None

    # End-to-end accuracy requires valid JSON, correct intent, correct urgency, and grounded/safe reply
    e2e_ok = bool(valid_json and intent_ok and urgency_ok and reply_ok)
    if case["case_type"] == "unanswerable":
        e2e_ok = bool(e2e_ok and abstention_ok)
    if case.get("expected_injection"):
        e2e_ok = bool(e2e_ok and pred_injection is True)

    return {
        "id": case["id"],
        "lang": case["lang"],
        "case_type": case["case_type"],
        "valid_json": valid_json,
        "attempts": run_record.get("attempts", 1),
        "intent_ok": intent_ok,
        "urgency_ok": urgency_ok,
        "category_ok": category_ok,
        "reply_ok": reply_ok,
        "abstention_ok": abstention_ok,
        "e2e_ok": e2e_ok,
        "hallucination_type": reply_audit["hallucination_type"],
        "audit_reasons": reply_audit["reasons"],
        "predicted": {
            "intent": pred_intent,
            "category": pred_category,
            "urgency": pred_urgency,
            "needs_abstention": pred_abstention,
            "injection_detected": pred_injection,
        },
        "reply": reply,
        "input_tokens": run_record.get("input_tokens") or 0,
        "output_tokens": run_record.get("output_tokens") or 0,
        "latency_s": run_record.get("latency_s"),
    }


def summarize_version(cases, evaluated_rows, price_in_per_1m=0.25, price_out_per_1m=1.50):
    n = len(cases)
    e2e_passes = [r["e2e_ok"] for r in evaluated_rows]
    json_passes = [r["valid_json"] for r in evaluated_rows]
    intent_passes = [r["intent_ok"] for r in evaluated_rows]
    urgency_passes = [r["urgency_ok"] for r in evaluated_rows]
    reply_passes = [r["reply_ok"] for r in evaluated_rows]

    unanswerable_rows = [r for r in evaluated_rows if r["case_type"] == "unanswerable"]
    abstention_passes = [bool(r["abstention_ok"]) for r in unanswerable_rows]

    adversarial_rows = [r for r in evaluated_rows if r["case_type"] == "adversarial"]
    adversarial_passes = [r["e2e_ok"] for r in adversarial_rows]

    edge_rows = [r for r in evaluated_rows if r["case_type"] == "edge"]
    edge_passes = [r["e2e_ok"] for r in edge_rows]

    mean_in = sum(r["input_tokens"] for r in evaluated_rows) / n
    mean_out = sum(r["output_tokens"] for r in evaluated_rows) / n
    cost_per_req = (mean_in / 1e6) * price_in_per_1m + (mean_out / 1e6) * price_out_per_1m
    lat_p50 = median_p50([r["latency_s"] for r in evaluated_rows])

    return {
        "n": n,
        "json_validity": proportion_ci95(sum(json_passes), n),
        "intent_accuracy": proportion_ci95(sum(intent_passes), n),
        "urgency_accuracy": proportion_ci95(sum(urgency_passes), n),
        "reply_grounding_rate": proportion_ci95(sum(reply_passes), n),
        "e2e_accuracy": proportion_ci95(sum(e2e_passes), n),
        "abstention_correct": proportion_ci95(sum(abstention_passes), len(unanswerable_rows)),
        "adversarial_pass_rate": proportion_ci95(sum(adversarial_passes), len(adversarial_rows)),
        "edge_pass_rate": proportion_ci95(sum(edge_passes), len(edge_rows)),
        "avg_input_tokens": round(mean_in, 2),
        "avg_output_tokens": round(mean_out, 2),
        "cost_per_task_usd": round(cost_per_req, 6),
        "cost_per_1000_usd": round(cost_per_req * 1000, 4),
        "latency_p50_s": lat_p50,
        "e2e_outcomes": e2e_passes,
    }


def compute_paired_tokens(cases, evaluated_rows_by_id):
    """Compare input tokens across all matched TR/EN pairs in the 40-case Week 2 test set (PF-01)."""
    pairs = {}
    for c in cases:
        pid = c.get("pair_id")
        if pid:
            pairs.setdefault(pid, {})[c["lang"]] = c["id"]

    results = []
    for pid, lang_map in sorted(pairs.items()):
        if "en" in lang_map and "tr" in lang_map:
            en_id, tr_id = lang_map["en"], lang_map["tr"]
            en_row = evaluated_rows_by_id[en_id]
            tr_row = evaluated_rows_by_id[tr_id]
            en_tok = en_row["input_tokens"]
            tr_tok = tr_row["input_tokens"]
            if en_tok > 0 and tr_tok > 0:
                results.append(
                    {
                        "pair_id": pid,
                        "en_id": en_id,
                        "tr_id": tr_id,
                        "en_input_tokens": en_tok,
                        "tr_input_tokens": tr_tok,
                        "tr_minus_en": tr_tok - en_tok,
                        "tr_over_en": round(tr_tok / en_tok, 4),
                    }
                )
    mean_diff = round(sum(r["tr_minus_en"] for r in results) / len(results), 2) if results else None
    mean_ratio = round(sum(r["tr_over_en"] for r in results) / len(results), 4) if results else None
    return {
        "pair_count": len(results),
        "mean_tr_minus_en_tokens": mean_diff,
        "mean_tr_over_en_ratio": mean_ratio,
        "pairs": results,
    }


def write_comparison_markdown(out_dir, summaries, mcnemar_results, paired_tokens):
    lines = [
        "# Week 2 Prompt Version Comparison (W2.5)",
        "",
        "## 1. Accuracy and 95% Confidence Intervals (n = 40)",
        "",
        "| Version | JSON Validity | Intent Accuracy (95% CI) | Urgency Accuracy (95% CI) | Abstention Correct (n=8, 95% CI) | End-to-End Accuracy (n=40, 95% CI) | Mean In/Out Tokens | List USD / 1,000 | p50 Latency (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for ver in ("v1", "v2", "v3"):
        s = summaries[ver]
        jv = s["json_validity"]
        ia = s["intent_accuracy"]
        ua = s["urgency_accuracy"]
        ab = s["abstention_correct"]
        e2e = s["e2e_accuracy"]
        lines.append(
            f"| `{ver}` | {jv['value']:.2f} ({jv['successes']}/{jv['n']}) | "
            f"{ia['value']:.2f} [{ia['ci95'][0]:.2f}, {ia['ci95'][1]:.2f}] | "
            f"{ua['value']:.2f} [{ua['ci95'][0]:.2f}, {ua['ci95'][1]:.2f}] | "
            f"{ab['value']:.2f} [{ab['ci95'][0]:.2f}, {ab['ci95'][1]:.2f}] | "
            f"**{e2e['value']:.2f}** [{e2e['ci95'][0]:.2f}, {e2e['ci95'][1]:.2f}] ({e2e['successes']}/{e2e['n']}) | "
            f"{s['avg_input_tokens']:.1f} / {s['avg_output_tokens']:.1f} | "
            f"${s['cost_per_1000_usd']:.4f} | {s['latency_p50_s']} |"
        )

    lines.extend(
        [
            "",
            "## 2. Paired McNemar Tests",
            "",
            "| Comparison | Both Pass ($n_{11}$) | A Only ($n_{10}$) | B Only ($n_{01}$) | Both Fail ($n_{00}$) | $\\Delta$ Accuracy (B - A) | McNemar $\\chi^2$ | $\\chi^2_{\\text{cc}}$ | Exact Binomial $p$-value | Significant ($p < 0.05$) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for label, mc in mcnemar_results.items():
        lines.append(
            f"| `{label}` | {mc['n11_both_pass']} | {mc['n10_a_only']} | {mc['n01_b_only']} | "
            f"{mc['n00_both_fail']} | {mc['delta_b_minus_a']:+.4f} | {mc['chi2']:.4f} | "
            f"{mc['chi2_continuity_corrected']:.4f} | {mc['exact_binomial_p']:.6f} | "
            f"{'Yes' if mc['significant_at_0_05'] else 'No'} |"
        )

    lines.extend(
        [
            "",
            "## 3. Paired TR/EN Token Comparison on 6 Matched Pairs (`v3`, PF-01)",
            "",
            "| Pair ID | EN Case | TR Case | EN Input Tokens | TR Input Tokens | TR - EN | TR / EN Ratio |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for p in paired_tokens["pairs"]:
        lines.append(
            f"| `{p['pair_id']}` | {p['en_id']} | {p['tr_id']} | {p['en_input_tokens']} | "
            f"{p['tr_input_tokens']} | {p['tr_minus_en']:+d} | {p['tr_over_en']:.4f} |"
        )
    lines.append(
        f"\nMean difference across {paired_tokens['pair_count']} pairs: "
        f"**{paired_tokens['mean_tr_minus_en_tokens']} tokens** "
        f"(mean ratio: **{paired_tokens['mean_tr_over_en_ratio']}**)."
    )
    (Path(out_dir) / "prompt_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_harness(
    *,
    provider_name="gemini",
    model_name="gemini-3.1-flash-lite",
    cases_path=ROOT / "eval" / "testsets" / "week2_cases.jsonl",
    out_dir=ROOT / "eval" / "results" / "week2",
    versions=("v1", "v2", "v3"),
    recompute_only=False,
    run_judge_calibration=False,
    rpm=15,
    seed=42,
):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases(cases_path)
    provider = None if recompute_only else make_provider(provider_name, model_name)

    summaries = {}
    evaluated_by_version = {}
    last_call_ts = None

    for ver in versions:
        prompt_path = PROMPT_VERSIONS[ver]
        raw_path = out_dir / f"{provider_name}__{model_name}__{ver}__t0.jsonl"

        if not recompute_only:
            raw_rows = []
            for case in cases:
                res = classify_request(
                    provider,
                    case["text"],
                    prompt_path=prompt_path,
                    max_retries=2,
                    max_output_tokens=650,
                    seed=seed,
                    require_reply=True,
                    rpm=rpm,
                    last_call_ts=last_call_ts,
                )
                last_call_ts = res.pop("last_call_ts", None)
                record = {"id": case["id"], "version": ver, **res}
                raw_rows.append(record)
            raw_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in raw_rows) + "\n",
                encoding="utf-8",
            )
        else:
            raw_rows = [
                json.loads(line)
                for line in raw_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        raw_by_id = {r["id"]: r for r in raw_rows}
        eval_rows = [evaluate_single_row(c, raw_by_id[c["id"]]) for c in cases]
        evaluated_by_version[ver] = eval_rows
        summaries[ver] = summarize_version(cases, eval_rows)

    # Paired McNemar tests (especially between the best two: v2 vs v3, and v1 vs v3)
    mcnemar_results = {}
    if "v2" in summaries and "v3" in summaries:
        mcnemar_results["v2_vs_v3"] = mcnemar_test(
            summaries["v2"]["e2e_outcomes"], summaries["v3"]["e2e_outcomes"]
        )
    if "v1" in summaries and "v3" in summaries:
        mcnemar_results["v1_vs_v3"] = mcnemar_test(
            summaries["v1"]["e2e_outcomes"], summaries["v3"]["e2e_outcomes"]
        )
    if "v1" in summaries and "v2" in summaries:
        mcnemar_results["v1_vs_v2"] = mcnemar_test(
            summaries["v1"]["e2e_outcomes"], summaries["v2"]["e2e_outcomes"]
        )

    # Remove raw boolean vectors from serialized summary JSON after McNemar
    clean_summaries = {
        ver: {k: v for k, v in s.items() if k != "e2e_outcomes"}
        for ver, s in summaries.items()
    }

    primary_ver = "v3" if "v3" in clean_summaries else versions[-1]
    primary = clean_summaries[primary_ver]
    eval_map_primary = {r["id"]: r for r in evaluated_by_version[primary_ver]}
    paired_tokens = compute_paired_tokens(cases, eval_map_primary)

    script_rel = "src/eval_harness/run.py"
    scoreboard = {
        "week": 2,
        "test_set_size": len(cases),
        "e2e_accuracy": {
            "value": primary["e2e_accuracy"]["value"],
            "ci95": primary["e2e_accuracy"]["ci95"],
            "n": primary["e2e_accuracy"]["n"],
            "script": script_rel,
        },
        "abstention_correct": {
            "value": primary["abstention_correct"]["value"],
            "ci95": primary["abstention_correct"]["ci95"],
            "n": primary["abstention_correct"]["n"],
            "script": script_rel,
        },
        "unsupported_claims": {"value": None, "n": None, "script": None},
        "hit_at_5": {"value": None, "n": None, "script": None},
        "mrr": {"value": None, "n": None, "script": None},
        "task_success": {"value": None, "n": None, "script": None},
        "pass_k": {"k": None, "value": None, "n": None, "script": None},
        "injection_success": {"value": None, "n": None, "script": None},
        "cost_per_task_usd": primary["cost_per_task_usd"],
        "latency_p50_s": primary["latency_p50_s"],
        "spend_week_usd": 0,
        "spend_total_usd": 0,
    }

    (out_dir / "scoreboard.json").write_text(
        json.dumps(scoreboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    comparison_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": current_commit(),
        "provider": provider_name,
        "model": model_name,
        "cases_path": str(Path(cases_path).relative_to(ROOT)),
        "cases_sha256": sha256_file(cases_path),
        "prompt_hashes": {ver: sha256_file(PROMPT_VERSIONS[ver]) for ver in versions},
        "primary_version": primary_ver,
        "versions": clean_summaries,
        "mcnemar": mcnemar_results,
        "paired_tokens_v3": paired_tokens,
        "per_case_evaluations": evaluated_by_version,
    }
    (out_dir / "prompt_comparison.json").write_text(
        json.dumps(comparison_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if all(v in clean_summaries for v in ("v1", "v2", "v3")):
        write_comparison_markdown(out_dir, clean_summaries, mcnemar_results, paired_tokens)

    if run_judge_calibration and not recompute_only:
        human_path = ROOT / "eval" / "testsets" / "week2_human_labels.jsonl"
        if human_path.exists():
            cal = calibrate_judge_against_human(provider, human_path, rpm=rpm)
            (out_dir / "judge_calibration.json").write_text(
                json.dumps(cal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    return scoreboard, comparison_payload


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", default="gemini", choices=["gemini", "ollama", "openai_compat", "dry"])
    p.add_argument("--model", default="gemini-3.1-flash-lite")
    p.add_argument("--cases", type=Path, default=ROOT / "eval" / "testsets" / "week2_cases.jsonl")
    p.add_argument("--out-dir", type=Path, default=ROOT / "eval" / "results" / "week2")
    p.add_argument("--versions", nargs="+", default=["v1", "v2", "v3"], choices=["v1", "v2", "v3"])
    p.add_argument("--recompute-only", action="store_true", help="Recompute metrics and scoreboard from saved JSONL outputs")
    p.add_argument("--calibrate-judge", action="store_true", help="Run LLM judge calibration against 20 human labels")
    p.add_argument("--rpm", type=float, default=15)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    scoreboard, _ = run_harness(
        provider_name=args.provider,
        model_name=args.model,
        cases_path=args.cases,
        out_dir=args.out_dir,
        versions=tuple(args.versions),
        recompute_only=args.recompute_only,
        run_judge_calibration=args.calibrate_judge,
        rpm=args.rpm,
        seed=args.seed,
    )
    print(json.dumps(scoreboard, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
