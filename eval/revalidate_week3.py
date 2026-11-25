"""Re-validate SAVED model outputs with the current evidence-quote validator. No model call.

    python -m eval.revalidate_week3            # writes answers_citizen_v2_revalidated
    python -m eval.revalidate_week3 --select   # ...and makes it the active answer run

Why: the contiguous-quote validator (evidence-quote-v1-contiguous) rejected
answers whose evidence quote joined two verbatim, non-adjacent sentences of the
same source with an ellipsis. The rule was widened AFTER the test results were
seen (src/rag/answer.py, evidence-quote-v2-elided-segments). This script applies
the new rule to the raw outputs that were already recorded; it never calls a
provider and never overwrites an existing run directory.

For every record of the source run:
* a valid generation is kept unchanged, after checking that the new validator
  accepts its recorded raw output and produces the same claims;
* an invalid generation is re-validated attempt by attempt on its saved
  raw_outputs; the first output that now passes becomes the answer. Its claims
  have NOT been judged (that needs a model call), so its judgement is marked
  "not_judged_offline_revalidation" and its claims stay out of the
  unsupported-claim denominator.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from eval.answer_week3 import atomic_json, read_jsonl, recompute, write_jsonl
from src.rag.answer import (PREVIOUS_VALIDATOR_VERSION, VALIDATOR_VERSION, render_answer,
                            validate_output)
from src.rag.corpus import ROOT, digest

BASE = ROOT/"eval/results/week3"
SOURCE = BASE/"answers_citizen_v2_complete"
TARGET = BASE/"answers_citizen_v2_revalidated"
CONFIG = ROOT/"config/rag_answer.json"
NOT_JUDGED = "not_judged_offline_revalidation"


def _plain(claims):
    """Claims without the validator's added 'segments' annotations."""
    return [{**c, "evidence": [{k: e[k] for k in ("citation", "quote")} for e in c["evidence"]]} for c in claims]


def revalidate_row(row, config):
    """Return (new_row, changed). Raises if a previously valid answer would change."""
    generation = row["generation"]
    out = deepcopy(row)
    out["validator_version_before"] = PREVIOUS_VALIDATOR_VERSION
    out["validator_version_after"] = VALIDATOR_VERSION
    raws = generation.get("raw_outputs") or []
    if generation.get("valid"):
        if raws:
            parsed = validate_output(raws[-1], row["sources"], config)
            if _plain(parsed["claims"]) != generation["claims"] or (not parsed["answerable"]) != bool(generation.get("abstained")):
                raise ValueError(f"{row['case_id']}: the new validator changes a previously valid answer")
        out["revalidated_offline"] = False
        return out, False
    for index, raw in enumerate(raws):
        try:
            parsed = validate_output(raw, row["sources"], config)
        except ValueError:
            continue
        language = generation.get("language") or row.get("lang")
        new = deepcopy(generation)
        new.update(claims=parsed["claims"], valid=True, abstained=not parsed["answerable"], error=None,
                   answer=render_answer(parsed["claims"]) if parsed["answerable"] else config["fallback"][language],
                   validator_version=VALIDATOR_VERSION,
                   revalidation={"revalidated_offline": True, "provider_called": False,
                                 "accepted_raw_output_index": index,
                                 "original_error": generation.get("error"),
                                 "original_errors": generation.get("errors", []),
                                 "validator_version_before": PREVIOUS_VALIDATOR_VERSION,
                                 "validator_version_after": VALIDATOR_VERSION})
        out["generation"] = new
        out["judgement"] = {"valid": False, "error": NOT_JUDGED, "claims": [], "unlisted_claims": [],
                            "input_tokens": 0, "output_tokens": 0, "attempts": 0}
        out["generation_from_cache"] = out["judgement_from_cache"] = False
        out["revalidated_offline"] = True
        return out, True
    out["revalidated_offline"] = False
    return out, False


def first_pass_under_new_validator(first_run, config):
    """Same-policy figure: how many first-pass outputs the new validator accepts."""
    rows = read_jsonl(first_run/"records.jsonl")
    valid = 0
    for row in rows:
        raws = row["generation"].get("raw_outputs") or []
        if row["generation"].get("valid") and not raws:
            valid += 1
            continue
        try:
            validate_output(raws[0], row["sources"], config) if raws else None
            valid += bool(raws)
        except ValueError:
            pass
    return {"valid": valid, "n": len(rows), "run": first_run.name}


def build(source=SOURCE, target=TARGET, config_path=CONFIG, select=False):
    source, target = Path(source), Path(target)
    if (target/"records.jsonl").exists():
        raise FileExistsError(f"{target} already exists; remove it deliberately before re-creating it")
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    meta = json.loads((source/"run_meta.json").read_text(encoding="utf-8"))
    rows, changed = [], []
    for row in read_jsonl(source/"records.jsonl"):
        new, was_changed = revalidate_row(row, config)
        rows.append(new)
        if was_changed:
            changed.append(row["case_id"])
    first_run = BASE/meta["components"][0]["directory"] if meta.get("components") else source
    new_meta = deepcopy(meta)
    new_meta.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "composition_method": (meta.get("composition_method", "") + " Then offline re-validation of the saved raw "
                               "outputs of invalid records with the widened evidence-quote validator; no model call."),
        "components": [*meta.get("components", []),
                       {"directory": source.name, "records_sha256": digest((source/"records.jsonl").read_bytes()),
                        "run_meta_sha256": digest((source/"run_meta.json").read_bytes()),
                        "provider_calls": 0, "transport_errors": 0}],
        "provider_calls_this_invocation": 0, "provider_events": [],
        "revalidation": {"script": "eval/revalidate_week3.py",
                         "script_sha256": digest(Path(__file__).read_bytes()),
                         "validator_code_sha256": digest((ROOT/"src/rag/answer.py").read_bytes()),
                         "config_sha256": digest(Path(config_path).read_bytes()),
                         "validator_version_before": PREVIOUS_VALIDATOR_VERSION,
                         "validator_version_after": VALIDATOR_VERSION,
                         "rule_changed_after_seeing_results": True,
                         "provider_called": False,
                         "revalidated_case_ids": changed,
                         "previously_valid_answers_unchanged": True,
                         "first_pass_under_new_validator": first_pass_under_new_validator(first_run, config),
                         "claims_of_revalidated_answers_judged": False,
                         "note": "Generation identity (prompt, model, recorded config hash) is that of the original "
                                 "calls; only the validator applied afterwards differs."}})
    write_jsonl(target/"records.jsonl", rows)
    atomic_json(target/"run_meta.json", new_meta)
    summary = recompute(target)
    if select:
        atomic_json(BASE/"active_answer_run.json", {
            "directory": target.name, "dataset_version": "citizen-v2",
            "reason": new_meta["composition_method"], "comparable_to_v1_metrics": False})
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--target", type=Path, default=TARGET)
    p.add_argument("--select", action="store_true", help="make the new directory the active answer run")
    args = p.parse_args(argv)
    summary = build(args.source, args.target, select=args.select)
    print(json.dumps({k: summary[k] for k in ("valid_generated_answers", "valid_claim_judgements")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
