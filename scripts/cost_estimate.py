"""Estimate list price from measured token counts."""

import argparse
import json
from pathlib import Path


def mean(values):
    return sum(values) / len(values) if values else None


def cost(input_tokens, output_tokens, price):
    price_in = price["price_in_per_1m_usd"]
    price_out = price["price_out_per_1m_usd"]
    if None in (input_tokens, output_tokens, price_in, price_out):
        return None
    return 1000 * (input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out)


def summarize(results_dir, prices):
    summaries = []
    for path in sorted(results_dir.glob("*__t*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        parts = path.stem.rsplit("__t", 1)[0].split("__", 1)
        if len(parts) != 2:
            continue
        provider, safe_model = parts
        meta_path = results_dir / f"run_meta_{provider}__{safe_model}.json"
        model = json.loads(meta_path.read_text(encoding="utf-8"))["model"] if meta_path.exists() else safe_model
        valid = [r for r in rows if not r.get("error")]
        in_avg = mean([r["input_tokens"] for r in valid if r.get("input_tokens") is not None])
        out_avg = mean([r["output_tokens"] for r in valid if r.get("output_tokens") is not None])
        languages = {}
        for lang in ("tr", "en"):
            subset = [r for r in valid if r.get("lang") == lang]
            languages[lang] = {
                "avg_input_tokens": mean([r["input_tokens"] for r in subset if r.get("input_tokens") is not None]),
                "avg_output_tokens": mean([r["output_tokens"] for r in subset if r.get("output_tokens") is not None]),
            }
        matched = next((p for p in prices if p["provider"] == provider and p["model"] == model), None)
        matched_cost = cost(in_avg, out_avg, matched) if matched else None
        comparisons = [{"provider": p["provider"], "model": p["model"],
                        "list_price_cost_per_1000_usd": cost(in_avg, out_avg, p)} for p in prices]
        summaries.append({"file": path.name, "provider": provider, "model": model, "n": len(rows),
                          "avg_input_tokens": in_avg, "avg_output_tokens": out_avg,
                          "by_language": languages, "error_count": len(rows) - len(valid),
                          "actual_spend_usd": 0 if matched and matched["free_tier"] else None,
                          "list_price_cost_per_1000_usd": matched_cost,
                          "list_price_comparisons": comparisons})
    return summaries


def display(value):
    return "null" if value is None else f"{value:.6f}" if isinstance(value, float) else str(value)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", type=Path, required=True)
    p.add_argument("--prices", type=Path, default=Path("config/prices.json"))
    args = p.parse_args(argv)
    prices = json.loads(args.prices.read_text(encoding="utf-8"))
    summaries = summarize(args.results_dir, prices)
    output = {"formula": "cost_per_request = in_tok/1e6*price_in + out_tok/1e6*price_out; cost_per_1000 = 1000*cost_per_request",
              "assumptions": "Token means exclude error rows; missing token counts and unknown prices yield null. Free tier actual spend is 0 USD by assumption. List prices are estimates, not billed amounts. Dry-run tokens are synthetic.",
              "prices": prices, "results": summaries}
    (args.results_dir / "cost_summary.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Formula: `cost_per_request = in_tok/1e6*price_in + out_tok/1e6*price_out`; `cost_per_1000 = 1000*cost_per_request`.\n")
    print("Assumptions: Token means exclude errors; missing measurements or prices are null. Free tier actual spend is assumed 0 USD. List prices are estimates; dry-run tokens are synthetic.\n")
    print("| Result | n | Mean in | Mean out | TR in/out | EN in/out | Errors | Actual spend USD | List USD / 1,000 |")
    print("|---|---:|---:|---:|---|---|---:|---:|---:|")
    for s in summaries:
        tr, en = s["by_language"]["tr"], s["by_language"]["en"]
        print(f"| {s['file']} | {s['n']} | {display(s['avg_input_tokens'])} | {display(s['avg_output_tokens'])} | {display(tr['avg_input_tokens'])}/{display(tr['avg_output_tokens'])} | {display(en['avg_input_tokens'])}/{display(en['avg_output_tokens'])} | {s['error_count']} | {display(s['actual_spend_usd'])} | {display(s['list_price_cost_per_1000_usd'])} |")
    print("\n### List-price comparison (same measured token means)\n")
    print("| Result | Price model | USD / 1,000 |")
    print("|---|---|---:|")
    for s in summaries:
        for c in s["list_price_comparisons"]:
            print(f"| {s['file']} | {c['provider']}/{c['model']} | {display(c['list_price_cost_per_1000_usd'])} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
