"""Compare temperature runs for one provider and model."""

import argparse
import json
from pathlib import Path
import re


TURKISH_WORDS = {"ve", "bir", "için", "nasıl", "nerede", "belediye", "merhaba", "şikayet", "şikâyet", "lütfen", "teşekkür", "istiyorum", "sokak"}


def guessed_language(text):
    words = set(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.lower()))
    return "tr" if re.search(r"[çğıöşü]", text.lower()) or words & TURKISH_WORDS else "en"


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "model"


def escape(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", type=Path, required=True)
    p.add_argument("--provider", required=True)
    p.add_argument("--model", required=True)
    args = p.parse_args(argv)
    paths = sorted(args.results_dir.glob(f"{args.provider}__{safe_name(args.model)}__t*.jsonl"))
    if len(paths) != 3:
        p.error(f"expected 3 temperature files, found {len(paths)}")
    by_temp = {}
    for path in paths:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        temperature = rows[0]["temperature"] if rows else float(path.stem.rsplit("__t", 1)[1])
        by_temp[temperature] = {row["id"]: row for row in rows}
    temps = sorted(by_temp)
    baseline = by_temp[temps[0]]
    ids = list(baseline)
    lines = [f"# Temperature comparison: {args.provider} / {args.model}", "",
             "Language heuristic: a reply is classified Turkish if it contains ç, ğ, ı, ö, ş, ü or one of: " +
             ", ".join(sorted(TURKISH_WORDS)) + ". Otherwise it is classified English. This is a rough proxy, not a validated language detector.", "",
             "| ID | Category | " + " | ".join(f"t{t:g} first 200 chars | t{t:g} length" for t in temps) + " |",
             "|---|---|" + "---|---:|" * len(temps)]
    for id_ in ids:
        row = baseline[id_]
        cells = []
        for t in temps:
            current = by_temp[t].get(id_, {})
            output = current.get("output") or ""
            cells.extend([escape(output[:200]), str(len(output))])
        lines.append(f"| {escape(id_)} | {escape(row['category'])} | " + " | ".join(cells) + " |")
    lines += ["", "## Summary", "", "| Temperature | Mean output length (chars) | Exact match to t0 | Errors | Language match |", "|---:|---:|---:|---:|---:|"]
    for t in temps:
        rows = [by_temp[t].get(id_) for id_ in ids]
        valid = [r for r in rows if r and not r.get("error") and r.get("output") is not None]
        avg_len = sum(len(r["output"]) for r in valid) / len(valid) if valid else None
        comparable = [(baseline[id_], by_temp[t].get(id_)) for id_ in ids]
        comparable = [(a, b) for a, b in comparable if b and not a.get("error") and not b.get("error") and a.get("output") is not None and b.get("output") is not None]
        same = sum(a["output"] == b["output"] for a, b in comparable) / len(comparable) if comparable else None
        language = sum(guessed_language(r["output"]) == r["lang"] for r in valid) / len(valid) if valid else None
        fmt = lambda n: "null" if n is None else f"{n:.3f}"
        lines.append(f"| {t:g} | {fmt(avg_len)} | {fmt(same)} | {len(ids) - len(valid)} | {fmt(language)} |")
    lines += ["", "Interpretation: temperature changes the model's sampling distribution, so wording and length may vary. This table measures observed differences only; it cannot prove that temperature caused a specific answer or that one answer is better. Dry-run outputs are deterministic and identical across temperatures."]
    out = args.results_dir / "temperature_comparison.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
