"""Offline re-validation of saved outputs: no provider call, explicit provenance."""
import json

import pytest

from eval.answer_week3 import read_jsonl
from eval.revalidate_week3 import BASE, NOT_JUDGED, SOURCE, build, revalidate_row
from src.rag.answer import PREVIOUS_VALIDATOR_VERSION, VALIDATOR_VERSION
from src.rag.corpus import ROOT

CONFIG = json.loads((ROOT/"config/rag_answer.json").read_text())


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    target = tmp_path_factory.mktemp("reval")/"answers_citizen_v2_revalidated"
    summary = build(SOURCE, target)
    return target, summary


def test_saved_outputs_rescue_exactly_the_two_rejected_answers(rebuilt):
    target, summary = rebuilt
    rows = {r["case_id"]: r for r in read_jsonl(target/"records.jsonl")}
    rescued = sorted(cid for cid, r in rows.items() if r["revalidated_offline"])
    assert rescued == ["W3-R019", "W3-R027"]
    assert summary["valid_generated_answers"] == 38 and summary["valid_claim_judgements"] == 35
    for cid in rescued:
        row = rows[cid]
        assert row["source_run"] == "answers_citizen_v2"
        assert row["generation"]["revalidation"]["provider_called"] is False
        assert (row["validator_version_before"], row["validator_version_after"]) == (PREVIOUS_VALIDATOR_VERSION, VALIDATOR_VERSION)
        assert row["judgement"]["error"] == NOT_JUDGED
        assert any("segments" in e for c in row["generation"]["claims"] for e in c["evidence"])
    meta = json.loads((target/"run_meta.json").read_text())
    assert meta["provider_calls_this_invocation"] == 0 and meta["revalidation"]["provider_called"] is False
    assert meta["components"][-1]["directory"] == SOURCE.name


def test_metrics_that_need_a_judge_or_controls_do_not_move(rebuilt):
    _, summary = rebuilt
    assert (summary["unsupported_claims"]["numerator"], summary["unsupported_claims"]["n"]) == (1, 90)
    assert (summary["abstention_correct"]["numerator"], summary["abstention_correct"]["n"]) == (5, 6)
    reasons = {}
    for c in summary["faithfulness"]["unjudged_claims"]:
        reasons.setdefault(c["case_id"], set()).add(c["reason"])
    assert {k: len([c for c in summary["faithfulness"]["unjudged_claims"] if c["case_id"] == k]) for k in reasons} == \
        {"W3-R019": 3, "W3-R020": 4, "W3-R027": 2}
    assert reasons["W3-R020"] == {"judge output invalid"}
    prov = summary["answer_provenance"]
    assert (prov["first_pass_valid"], prov["after_repair_valid"], prov["after_offline_revalidation_valid"]) == (35, 36, 38)


def test_previously_valid_answers_are_unchanged(rebuilt):
    target, _ = rebuilt
    old = {r["case_id"]: r for r in read_jsonl(SOURCE/"records.jsonl")}
    for row in read_jsonl(target/"records.jsonl"):
        if old[row["case_id"]]["generation"]["valid"]:
            assert row["generation"] == old[row["case_id"]]["generation"]
            assert row["judgement"] == old[row["case_id"]]["judgement"]


def test_a_validator_that_changes_a_valid_answer_is_refused():
    row = next(r for r in read_jsonl(SOURCE/"records.jsonl") if r["generation"]["valid"] and r["generation"]["claims"])
    row["generation"]["claims"][0]["text"] += " (edited)"
    with pytest.raises(ValueError, match="previously valid"):
        revalidate_row(row, CONFIG)


def test_existing_run_directories_are_never_overwritten(rebuilt):
    target, _ = rebuilt
    with pytest.raises(FileExistsError):
        build(SOURCE, target)


def test_committed_revalidated_run_matches_a_fresh_rebuild(rebuilt):
    target, _ = rebuilt
    committed = BASE/"answers_citizen_v2_revalidated"
    assert (committed/"records.jsonl").read_bytes() == (target/"records.jsonl").read_bytes()
    assert json.loads((committed/"summary.json").read_text()) == json.loads((target/"summary.json").read_text())
    active = json.loads((BASE/"active_answer_run.json").read_text())
    assert active["directory"] == committed.name
