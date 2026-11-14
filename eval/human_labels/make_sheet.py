"""Judge sonucunu içermeyen tabakalı insan etiketleme tablosu üretir."""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import random


DEFAULT_CASES = Path(__file__).resolve().parents[1] / "testsets" / "week2_cases.jsonl"
FIELDS = ["item_id", "case_id", "prompt_version", "lang", "type", "text",
          "expected_behavior", "answerable", "answer", "human_label_1", "human_note_1"]


def _read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def make_sheet(results, out, n=20, seed=7, cases_path=DEFAULT_CASES):
    """Sample up to n distinct cases; reserve min(3, available) for each type.

    A seeded shuffle selects one result per case (also across prompt versions).
    If n cannot accommodate the type quotas, raise ValueError rather than silently
    break stratification. Case metadata comes from the reference test set.
    """
    if type(n) is not int or n <= 0:
        raise ValueError("n must be a positive integer")
    cases = {case["id"]: case for case in _read_jsonl(cases_path)}
    records = _read_jsonl(results)
    for record in records:
        if not {"case_id", "prompt_version", "answer"}.issubset(record):
            raise ValueError("Results require case_id, prompt_version and answer")
        if record["case_id"] not in cases:
            raise ValueError(f"Unknown case_id: {record['case_id']}")
    rng = random.Random(seed)
    rng.shuffle(records)
    unique = {}
    for record in records:
        unique.setdefault(record["case_id"], record)
    groups = defaultdict(list)
    for record in unique.values():
        groups[cases[record["case_id"]]["type"]].append(record)
    target = min(n, len(unique))
    quota = sum(min(3, len(group)) for group in groups.values())
    if target < quota:
        raise ValueError(f"n={n} cannot meet type quotas requiring {quota} cases")
    selected, remaining = [], []
    for kind in sorted(groups):
        group = groups[kind]
        rng.shuffle(group)
        selected.extend(group[:3])
        remaining.extend(group[3:])
    rng.shuffle(remaining)
    selected.extend(remaining[:target - len(selected)])
    rng.shuffle(selected)
    rows = []
    for index, record in enumerate(selected, 1):
        case = cases[record["case_id"]]
        rows.append({
            "item_id": f"H{index:03d}", "case_id": record["case_id"],
            "prompt_version": record["prompt_version"],
            **{key: case[key] for key in ("lang", "type", "text", "expected_behavior")},
            "answerable": json.dumps(case["answerable"]), "answer": record["answer"],
            "human_label_1": "", "human_note_1": "",
        })
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args(argv)
    try:
        rows = make_sheet(args.results, args.out, args.n, args.seed, args.cases)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(f"Wrote {len(rows)} items to {args.out}; no judge labels included.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
