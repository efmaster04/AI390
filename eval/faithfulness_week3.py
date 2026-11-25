"""Claim-level source faithfulness and genuinely blind human-label calibration.

Unsupported rate = (unsupported + insufficient_evidence) / valid judged claims.
A validated fixed refusal contributes zero factual claims (judge rubric).
Invalid or errored judgements are excluded and counted separately, never passed.
Human labels are never auto-filled from model labels or deterministic audits.
"""
import argparse
import csv
from html import escape
import json
from pathlib import Path
import random
import time

from eval.judge import load_prompt
from eval.stats import cohen_kappa
from src.rag.corpus import ROOT, digest

LABELS = {"supported", "unsupported", "insufficient_evidence"}
PROMPT = ROOT/"prompts/judge/week3_v1.md"
HUMAN_FIELDS = ["sample_id", "case_id", "claim_id", "question", "answer", "claim_text",
                "citations", "source_text", "human_label", "human_note"]


def _reason(value):
    return isinstance(value, str) and 1 <= len(value.split()) <= 45


def validate_judgement(raw, claim_ids, source_numbers):
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != {"claims", "unlisted_claims", "coverage_complete", "reason"}:
        raise ValueError("Expected exactly claims, unlisted_claims, coverage_complete and reason")
    if type(obj["coverage_complete"]) is not bool or not _reason(obj["reason"]):
        raise ValueError("Invalid coverage flag or summary reason")
    if not isinstance(obj["claims"], list) or not isinstance(obj["unlisted_claims"], list):
        raise ValueError("Claim collections must be arrays")
    got = []
    for row in obj["claims"]:
        if not isinstance(row, dict) or set(row) != {"claim_id", "label", "reason"}:
            raise ValueError("Claim verdict keys differ")
        if row["label"] not in LABELS or not _reason(row["reason"]):
            raise ValueError("Invalid claim label or reason")
        got.append(row["claim_id"])
    if len(got) != len(set(got)) or set(got) != set(claim_ids):
        raise ValueError("Verdict IDs must exactly cover supplied claims")
    for row in obj["unlisted_claims"]:
        if not isinstance(row, dict) or set(row) != {"text", "citations", "label", "reason"}:
            raise ValueError("Unlisted-claim keys differ")
        refs = row["citations"]
        if not isinstance(refs, list) or any(type(n) is not int or n not in source_numbers for n in refs):
            raise ValueError("Unlisted claim cites an unknown source")
        if len(refs) != len(set(refs)) or not isinstance(row["text"], str) or not row["text"].strip():
            raise ValueError("Invalid unlisted claim text or duplicate citation")
        if row["label"] not in LABELS or not _reason(row["reason"]):
            raise ValueError("Invalid unlisted claim label or reason")
    if obj["coverage_complete"] != (not obj["unlisted_claims"]):
        raise ValueError("Coverage must be complete iff unlisted_claims is empty")
    return obj


def judge_claims(answer_record, sources, provider, *, question="", language="tr",
                 prompt_path=PROMPT, max_retries=1, seed=42):
    start = time.perf_counter()
    result = {"valid": False, "error": None, "errors": [], "claims": [], "unlisted_claims": [],
              "coverage_complete": None, "reason": None, "attempts": 0,
              "input_tokens": 0, "output_tokens": 0, "latency_s": 0.0,
              "prompt_sha256": None, "judge_input_sha256": None}
    try:
        if type(max_retries) is not int or not 0 <= max_retries <= 2:
            raise ValueError("max_retries must be 0, 1 or 2")
        if not answer_record.get("valid"):
            raise ValueError("Cannot judge a failed generation as a valid answer")
        system, result["prompt_sha256"] = load_prompt(prompt_path)
        claims = answer_record.get("claims", [])
        ids = [c["claim_id"] for c in claims]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate input claim IDs")
        source_numbers = {s["citation"] for s in sources}
        payload = {"question": question, "language": language,
                   "displayed_answer": answer_record["answer"], "claims": claims,
                   "retrieved_sources": sources, "abstained": answer_record.get("abstained")}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        result["judge_input_sha256"] = digest(encoded)
        user = "<evaluation_data>\n"+escape(encoded, quote=False)+"\n</evaluation_data>"
        for attempt in range(max_retries+1):
            result["attempts"] = attempt+1
            feedback = "" if not result["errors"] else (
                "\nYour previous output was invalid. Return all required JSON keys and exactly the supplied claim IDs.")
            try:
                response = provider.generate(system, user+feedback, 0, 1600, seed, json_mode=True)
                if not isinstance(response, dict):
                    raise ValueError("Provider response is not an object")
                for key in ("input_tokens", "output_tokens"):
                    count = response.get(key)
                    result[key] = result[key]+count if type(count) is int and count >= 0 and result[key] is not None else None
                value = validate_judgement(response.get("output", ""), ids, source_numbers)
            except Exception as exc:
                # Never persist provider exception text, which may contain credentials.
                result["errors"].append(f"{type(exc).__name__}: invalid judgement or provider failure")
                continue
            result.update(value, valid=True)
            break
        if not result["valid"]:
            result["error"] = "Claim judgement unavailable after bounded attempts"
    except Exception as exc:
        result["error"] = f"Judge input/prompt error: {type(exc).__name__}"
    finally:
        result["latency_s"] = time.perf_counter()-start
    return result


def flattened_claims(rows):
    """Return raw per-claim records. This output contains automatic verdicts."""
    flat = []
    for row in rows:
        judgement, generation = row.get("judgement") or {}, row.get("generation") or {}
        if not generation.get("valid") or not judgement.get("valid"):
            continue
        original = {c["claim_id"]: c for c in generation.get("claims", [])}
        for j, verdict in enumerate([*judgement["claims"], *judgement["unlisted_claims"]]):
            is_original = j < len(judgement["claims"])
            cid = verdict["claim_id"] if is_original else f"U{j-len(judgement['claims'])+1}"
            claim = original[cid] if is_original else verdict
            refs = claim.get("citations", [])
            cited = [s for s in row.get("sources", []) if s["citation"] in refs]
            source_text = "\n\n".join(f"[{s['citation']}] {s['passage_id']}\n{s['text']}" for s in cited)
            identity = json.dumps([row["case_id"], cid, claim["text"], refs, source_text], ensure_ascii=False)
            flat.append({"sample_id": "HC-"+digest(identity)[:16], "case_id": row["case_id"],
                         "claim_id": cid, "question": row["question"], "answer": generation["answer"],
                         "claim_text": claim["text"], "citations": json.dumps(refs),
                         "source_text": source_text, "judge_label": verdict["label"],
                         "judge_reason": verdict["reason"], "unlisted": not is_original})
    return flat


ANSWER_CONFIG = ROOT/"config/rag_answer.json"
OLD_DEFINITION = "unsupported plus insufficient_evidence divided by valid judged claims, including unlisted claims"
DEFINITION = ("unsupported plus insufficient_evidence divided by valid judged claims, including unlisted claims; "
              "a validated fixed refusal contributes zero factual claims (judge rubric prompts/judge/week3_v1.md)")


def fixed_refusal_texts(config_path=ANSWER_CONFIG):
    return json.loads(Path(config_path).read_text(encoding="utf-8"))["fallback"]


def is_validated_fixed_refusal(row, fallback=None):
    """A valid abstention whose displayed answer is exactly the configured fixed sentence.

    The judge rubric says a fixed abstention sentence is not a factual claim, so
    any verdict the judge attached to it is not counted in the claim rate.
    """
    generation = row.get("generation") or {}
    fallback = fallback or fixed_refusal_texts()
    language = row.get("lang") or generation.get("language")
    return (generation.get("valid") is True and generation.get("abstained") is True
            and not generation.get("claims") and language in fallback
            and generation.get("answer") == fallback[language])


def _rate(claims, definition):
    n = len(claims)
    bad = sum(c["judge_label"] in {"unsupported", "insufficient_evidence"} for c in claims)
    return {"value": bad/n if n else None, "n": n, "numerator": bad, "definition": definition}


def summarize_faithfulness(rows, fallback=None):
    fallback = fallback or fixed_refusal_texts()
    raw = flattened_claims(rows)
    refusals = {r["case_id"] for r in rows if is_validated_fixed_refusal(r, fallback)}
    claims = [c for c in raw if c["case_id"] not in refusals]
    n = len(claims)
    counts = {label: sum(c["judge_label"] == label for c in claims) for label in sorted(LABELS)}
    valid_judgements = [r for r in rows if (r.get("judgement") or {}).get("valid")]
    missing = sum(c["unlisted"] for c in claims)
    unjudged = [{"case_id": r["case_id"], "claim_id": c["claim_id"], "text": c["text"],
                 "reason": ("not yet judged (answer accepted by offline re-validation)"
                            if (r.get("judgement") or {}).get("error") == "not_judged_offline_revalidation"
                            else "judge output invalid")}
                for r in rows if (r.get("generation") or {}).get("valid") and not (r.get("judgement") or {}).get("valid")
                and r["case_id"] not in refusals for c in (r["generation"].get("claims") or [])]
    return {"valid_judged_claims": n, "labels": counts,
            "unsupported_claims": _rate(claims, DEFINITION),
            "unsupported_claims_before_audit_correction": _rate(raw, OLD_DEFINITION),
            "metric_definition_corrected_after_audit": (
                "Fixed-refusal verdicts excluded from the claim rate, as the judge rubric already required."),
            "fixed_refusal_verdicts_excluded": [
                {"case_id": c["case_id"], "claim_id": c["claim_id"], "claim_text": c["claim_text"],
                 "judge_label": c["judge_label"]} for c in raw if c["case_id"] in refusals],
            "validated_fixed_refusals": sorted(refusals),
            "unjudged_claims": unjudged,
            "claim_coverage": {"unlisted_factual_claims": missing,
                               "answers_with_complete_claim_coverage": sum(
                                   r["judgement"]["coverage_complete"] is True or r["case_id"] in refusals
                                   for r in valid_judgements),
                               "n_valid_judgements": len(valid_judgements)},
            "generation_errors": sum(not (r.get("generation") or {}).get("valid") for r in rows),
            "judge_errors_or_skipped": sum(not (r.get("judgement") or {}).get("valid") for r in rows),
            "note": "An automatic provisional faithfulness estimate, not answer accuracy; human calibration required."}


def write_human_sheet(rows, path, *, n=20, seed=7):
    """Blind selection uses no judge label, preserving existing actual human edits."""
    pool = flattened_claims(rows)
    selected = random.Random(seed).sample(pool, min(n, len(pool)))
    path = Path(path)
    previous = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as h:
            previous = {r["sample_id"]: r for r in csv.DictReader(h)}
        # Keep previously presented items whose underlying evidence still exists.
        current = {r["sample_id"]: r for r in pool}
        kept = [current[key] for key in previous if key in current]
        selected = kept + [r for r in selected if r["sample_id"] not in {x["sample_id"] for x in kept}]
        selected = selected[:max(n, len(kept))]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=HUMAN_FIELDS)
        writer.writeheader()
        for row in selected:
            clean = {k: row[k] for k in HUMAN_FIELDS if k in row}
            clean["human_label"] = previous.get(row["sample_id"], {}).get("human_label", "")
            clean["human_note"] = previous.get(row["sample_id"], {}).get("human_note", "")
            writer.writerow(clean)
    return {"n_items": len(selected), "target": n, "labels_are_blank_unless_entered_by_human": True,
            "sampling": "seeded random actual claims, without stratifying on judge verdicts", "seed": seed}


def calibrate_human(sheet_path, rows):
    automatic = {c["sample_id"]: c["judge_label"] for c in flattened_claims(rows)}
    human, judge, skipped_empty, skipped_unmatched = [], [], 0, 0
    if not Path(sheet_path).exists():
        return {**cohen_kappa([], []), "status": "pending_human_labels", "skipped_empty": 0, "skipped_unmatched": 0}
    with Path(sheet_path).open(encoding="utf-8", newline="") as h:
        data = list(csv.DictReader(h))
    if len({r["sample_id"] for r in data}) != len(data):
        raise ValueError("Duplicate sample IDs in human label sheet")
    for row in data:
        label = (row.get("human_label") or "").strip()
        if not label:
            skipped_empty += 1
            continue
        if label not in LABELS:
            raise ValueError("Human label must be supported, unsupported or insufficient_evidence")
        if row["sample_id"] not in automatic:
            skipped_unmatched += 1
            continue
        human.append(label)
        judge.append(automatic[row["sample_id"]])
    return {**cohen_kappa(human, judge), "status": "complete" if len(human) >= 20 else "pending_human_labels",
            "skipped_empty": skipped_empty, "skipped_unmatched": skipped_unmatched,
            "note": "Real human labels only. Kappa may be undefined if labels lack variation; no threshold alone validates a judge."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(s) for s in args.records.read_text().splitlines() if s.strip()]
    value = calibrate_human(args.sheet, rows)
    args.out.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
