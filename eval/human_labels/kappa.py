"""Kör insan etiketlerini vaka ve prompt sürümü üzerinden judge ile karşılaştırır."""

import argparse
import csv
import json
from pathlib import Path

from eval.stats import cohen_kappa


def evaluate_sheet(sheet, judged, labeler=1):
    """Return κ on matched pass/fail labels; separately count blank/unmatched rows.

    Confusion rows are human labels, columns are judge labels, ordered by labels.
    Invalid judge labels (including null) are skipped, never counted as failures.
    Duplicate judge keys are rejected because the match would be ambiguous.
    """
    if type(labeler) is not int or labeler < 1:
        raise ValueError("labeler must be a positive integer")
    judge_labels = {}
    with Path(judged).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            key = (row["case_id"], row["prompt_version"])
            if key in judge_labels:
                raise ValueError(f"Ambiguous duplicate judge key: {key}")
            judge_labels[key] = row.get("label")
    human, automatic = [], []
    skipped_empty = skipped_unmatched = skipped_invalid_judge = 0
    column = f"human_label_{labeler}"
    with Path(sheet).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {column, "case_id", "prompt_version"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Sheet requires columns: {sorted(required)}")
        for row in reader:
            label = (row[column] or "").strip()
            if not label:
                skipped_empty += 1
                continue
            if label not in ("pass", "fail"):
                raise ValueError(f"Invalid human label: {label!r}")
            key = (row["case_id"], row["prompt_version"])
            if key not in judge_labels:
                skipped_unmatched += 1
                continue
            judged_label = judge_labels[key]
            if judged_label not in ("pass", "fail"):
                skipped_invalid_judge += 1
                continue
            human.append(label)
            automatic.append(judged_label)
    return {**cohen_kappa(human, automatic), "labeler": labeler,
            "skipped_empty": skipped_empty, "skipped_unmatched": skipped_unmatched,
            "skipped_invalid_judge": skipped_invalid_judge}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--judged", required=True, type=Path)
    parser.add_argument("--labeler", type=int, default=1)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_sheet(args.sheet, args.judged, args.labeler)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    value = "undefined" if result["kappa"] is None else f"{result['kappa']:.4f}"
    print(f"n={result['n']} Cohen kappa={value}; skipped empty={result['skipped_empty']}, "
          f"unmatched={result['skipped_unmatched']}, invalid judge={result['skipped_invalid_judge']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
