"""Recorded control decisions: strict metric unchanged, W3.4 rule, schema and re-verification."""
import copy
import json

import pytest

from eval.answer_week3 import (CONTROL_DECISIONS, accepted_cited_refusal, failure_analysis,
                               load_control_decisions, read_jsonl, summarize_answers)
from scripts.build_week3_report import build, w34_status
from src.rag.corpus import ROOT

RUN = ROOT/"eval/results/week3/answers_citizen_v2_revalidated"


def rows():
    return read_jsonl(RUN/"records.jsonl")


def meta():
    return json.loads((RUN/"run_meta.json").read_text())


def test_decision_record_schema_and_honesty_fields():
    record = json.loads(CONTROL_DECISIONS.read_text())
    assert record["version"] == "control-decisions-v1"
    decision = load_control_decisions()["W3-U004"]
    assert decision["decided_after_results"] is True and decision["affects_strict_metric"] is False
    assert decision["reviewer_confirmation"].startswith("pending")
    assert decision["decided_by"] == "Efe İncirci"
    assert all((ROOT/p).exists() for p in decision["evidence"])


def test_invalid_decision_record_is_refused(tmp_path):
    record = json.loads(CONTROL_DECISIONS.read_text())
    record["decisions"][0]["affects_strict_metric"] = True
    path = tmp_path/"d.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        load_control_decisions(path)


def test_strict_metric_unchanged_and_post_hoc_figure_separate():
    summary = summarize_answers(rows(), meta())
    strict = summary["abstention_correct"]
    assert (strict["numerator"], strict["n"]) == (5, 6)
    assert strict["definition"] == "valid fixed-fallback response on unavailable-information controls"
    safe = summary["controls_handled_safely"]
    assert (safe["numerator"], safe["n"], safe["accepted_case_ids"]) == (6, 6, ["W3-U004"])
    assert "POST-HOC" in safe["definition"]


def test_u004_is_an_accepted_deviation_not_a_generation_failure():
    entry = [f for f in failure_analysis(rows()) if f["case_id"] == "W3-U004"]
    assert [(e["stage"], e["kind"]) for e in entry] == [("accepted_deviation", "accepted_cited_refusal_on_control")]
    assert entry[0]["decision_ref"].endswith("#W3-U004")
    without = [f for f in failure_analysis(rows(), decisions={}) if f["case_id"] == "W3-U004"]
    assert [(e["stage"], e["kind"]) for e in without] == [("generation", "answered_unavailable_information_control")]


def test_decision_does_not_cover_an_answer_that_discloses_contact_details():
    row = copy.deepcopy(next(r for r in rows() if r["case_id"] == "W3-U004"))
    decisions = load_control_decisions()
    assert accepted_cited_refusal(row, decisions)
    row["generation"]["answer"] += " Their number is 0532 123 45 67."
    assert not accepted_cited_refusal(row, decisions)
    row = copy.deepcopy(next(r for r in rows() if r["case_id"] == "W3-U004"))
    row["generation"]["claims"][0]["evidence"][0]["quote"] = "A quote that the source does not contain."
    assert not accepted_cited_refusal(row, decisions)


def test_w34_status_rule_with_and_without_a_decision():
    done = w34_status(38, 38, 36, 5, 6, ["W3-U004"], [])
    assert done["status"] == "done"
    assert done["note"] == ("38/38 valid (36/38 under the original quote rule); 5/6 controls returned the fixed refusal. "
                            "W3-U004 gave a cited privacy refusal, accepted by team decision after seeing the results; "
                            "reviewer confirmation pending.")
    assert len(done["card_note"]) <= 170
    assert w34_status(38, 38, 36, 5, 6, [], ["W3-U004"])["status"] == "partial"
    assert w34_status(37, 38, 36, 5, 6, ["W3-U004"], [])["status"] == "partial"
    assert w34_status(38, 38, None, 6, 6, [], [])["status"] == "done"


def test_report_shows_both_control_figures_and_scoreboard_is_strict():
    built = build(write=False)
    assert built["score"]["abstention_correct"]["value"] == round(5/6, 4)
    assert "controls_handled_safely" not in built["score"]
    report = built["report"]
    assert "6/6" in report and "Post-hoc reading, not a scoreboard row" in report
    assert "reviewer confirmation is pending (Tarık Edip Yenikomşu)" in report
    assert "whether that counts" not in report
    assert built["data"]["deliverables"]["W3.4"]["status"] == "done"
