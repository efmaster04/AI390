"""The Week 3 report is rebuilt from recorded artefacts and follows the template."""
import json
import re
from types import SimpleNamespace

import pytest

from scripts.build_week3_report import approvals, build, glued_tokens, prose_words
from src.rag.corpus import ROOT

ROOT_CAUSES = {"prompt", "retrieval", "generation", "tool design", "loop", "data", "security", "evaluation"}


@pytest.fixture(scope="module")
def built():
    return build(write=False)


def section(report, number):
    start = report.index(f"\n## {number}. ")
    end = report.find("\n## ", start+1)
    return report[start:end if end != -1 else None]


def table_rows(text):
    rows = [line for line in text.splitlines() if line.startswith("|")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]


def test_committed_outputs_match_a_fresh_build(built):
    assert (ROOT/"reports/week-3.md").read_text(encoding="utf-8") == built["report"]
    assert json.loads((ROOT/"eval/results/week3/scoreboard.json").read_text()) == built["score"]


def test_template_headings_header_fields_and_word_limit(built):
    report = built["report"]
    template = (ROOT/"docs/weekly_report_template.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## .+$", template, re.M)
    assert re.findall(r"^## .+$", report, re.M) == headings
    fields = [r[0] for r in table_rows(report.split("## 1.")[0])]
    assert fields == ["Team", "Use case", "Week", "Repository", "Commit tag", "Presenter", "Members and roles"]
    assert built["words"] == prose_words(report) <= 1500
    assert glued_tokens(report) == []


def test_glue_detector_catches_audited_examples():
    text = "RRF60 and 32answerable with Wilson95% on Gemini3.1Flash-Lite versus0.7589 in Week2"
    assert set(glued_tokens(text)) >= {"RRF60", "32answerable", "Wilson95", "Gemini3.1Flash", "versus0.7589", "Week2"}
    assert glued_tokens("BM25, hit@5, W3.1, YV-D006#details and `week3_retrieval.jsonl`") == []


def test_scoreboard_follows_handbook_template(built):
    score = built["score"]
    for key in ("abstention_correct", "unsupported_claims", "hit_at_5"):
        entry = score[key]
        assert set(entry) == {"value", "ci95", "n", "script"}
        assert entry["script"] and entry["n"] and entry["ci95"][0] <= entry["value"] <= entry["ci95"][1]
    assert (score["unsupported_claims"]["n"], round(score["unsupported_claims"]["value"]*90)) == (90, 1)
    assert score["e2e_accuracy"]["value"] is None
    assert set(score["mrr"]) == {"value", "n", "script"}
    for key in ("cost_per_task_usd", "latency_p50_s", "spend_week_usd", "spend_total_usd"):
        assert isinstance(score[key], float)
    assert score["spend_week_usd"] == score["spend_total_usd"] == 0.0
    block = re.search(r"```json\n(.*?)\n```", built["report"], re.S)[1]
    assert json.loads(block) == score


def test_report_states_audited_facts(built):
    report = built["report"]
    assert "2/91" in report and "1/90" in report and "metric definition corrected after audit" in report
    assert "first pass 35/38" in report and "36/38" in report and "not cache hits" in report
    assert "κ was measured on earlier v1" in report and "purposively" in report
    assert "list-price estimate" in report and "Actual spend is $0" in report
    assert "e2e_accuracy` is null because" in report
    assert "0/30" not in report and "Hours were not recorded" not in report
    for case_id in ("W3-R020",):
        assert sum(case_id in row[0] for row in table_rows(section(report, 3))) == 4


def test_approval_counts_come_from_data(built, tmp_path):
    review = built["review"]
    assert (review["documents_approved"], review["documents_total"]) == (31, 31)
    assert (review["cases_approved"], review["cases_total"]) == (38, 38)
    assert "31/31 documents and 38/38 test cases" in built["report"]
    log = tmp_path/"log.jsonl"
    log.write_text("")
    docs = [SimpleNamespace(access=("public",), review_status="draft"), SimpleNamespace(access=("staff",), review_status="approved")]
    counted = approvals(docs, [{"review_status": "draft"}], log)
    assert (counted["documents_approved"], counted["public_documents_approved"], counted["cases_approved"]) == (1, 0, 0)
    assert counted["reviewers"] == []


def test_tables_use_allowed_root_causes_paths_and_no_invented_hours(built):
    report = built["report"]
    failures = table_rows(section(report, 5))
    assert len(failures) == 3 and {r[3] for r in failures} <= ROOT_CAUSES
    assert "W3-R032" in failures[0][1] and failures[0][3] == "retrieval"
    deliverables = table_rows(section(report, 2))
    assert [r[0] for r in deliverables] == [f"W3.{i}" for i in range(1, 9)]
    for row in deliverables:
        paths = re.findall(r"\]\(\.\./([^)]+)\)", row[2])
        assert paths and all((ROOT/p).exists() for p in paths)
    contributions = table_rows(section(report, 8))
    assert len(contributions) == 3 and all(r[4] == "TBD (member to fill)" for r in contributions)
    for section_number in (6, 9):
        assert table_rows(section(report, section_number))
    assert "TBD (team to fill)" in report.split("## 1.")[0]
