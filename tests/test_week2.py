"""Offline unit and acceptance tests for Week 2 deliverables (W2.1–W2.8)."""

from collections import Counter
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.classifier.classify import classify_request
from src.classifier.schema import (
    CATEGORY_TO_DEPARTMENT,
    derive_department,
    extract_json_object,
    validate_classification,
)
from src.eval_harness.judge import deterministic_reply_audit
from src.eval_harness.metrics import cohens_kappa, mcnemar_test, proportion_ci95
from src.eval_harness.run import load_cases, run_harness


class FlakyMockProvider:
    """Fails schema validation on first attempt, then returns valid JSON on retry."""

    def __init__(self):
        self.calls = []

    def generate(self, system, user, temperature, max_tokens, seed):
        self.calls.append({"user": user, "temperature": temperature})
        if len(self.calls) == 1:
            return {
                "output": '{"intent": "invalid_intent", "language": "tr"}',
                "input_tokens": 50,
                "output_tokens": 15,
                "finish_reason": "STOP",
            }
        valid = {
            "intent": "field_complaint",
            "language": "tr",
            "category": "roads_sidewalks",
            "urgency": "P2",
            "urgency_reason": "Collapsed sidewalk blocking elderly pedestrians",
            "entities": {
                "neighborhood": "Yeşilova",
                "street": "Ada 1245 Parsel 7",
                "ticket_id": None,
                "contact_last4": None,
                "third_party_ticket": False,
            },
            "needs_abstention": False,
            "injection_detected": False,
            "classifier_version": "classifier-v1",
            "reply": "Yeşilova Mahallesi Ada 1245 Parsel 7 için P2 taslak şikayet hazırladım. Onaylıyor musunuz?",
        }
        return {
            "output": f"```json\n{json.dumps(valid, ensure_ascii=False)}\n```",
            "input_tokens": 70,
            "output_tokens": 65,
            "finish_reason": "STOP",
        }


def test_w2_1_classifier_validation_and_retry():
    mock = FlakyMockProvider()
    res = classify_request(
        mock,
        "Yeşilova mahallesinde Ada 1245 Parsel 7 önündeki kaldırım çökmüş.",
        max_retries=2,
        require_reply=True,
    )
    assert res["valid_json"] is True
    assert res["attempts"] == 2
    assert len(mock.calls) == 2
    assert all(c["temperature"] == 0.0 for c in mock.calls)
    assert "[VALIDATION_RETRY attempt=1]" in mock.calls[1]["user"]
    assert res["department"] == CATEGORY_TO_DEPARTMENT["roads_sidewalks"]
    assert derive_department(None) is None


def test_w2_2_six_building_blocks_present_in_v3_prompt():
    text = (ROOT / "prompts" / "assistant_v3.md").read_text(encoding="utf-8")
    for block in (
        "[1. ROLE & PERSONA]",
        "[2. TASK & SCOPE BOUNDARIES]",
        "[3. CONTEXT, GROUNDING & UNTRUSTED INPUT ISOLATION]",
        "[4. SAFETY, PRIVACY & URGENCY RUBRIC CONSTRAINTS]",
        "[5. OUTPUT FORMAT & SCHEMA]",
        "[6. FEW-SHOT EXAMPLES]",
    ):
        assert block in text


def test_w2_3_testset_has_40_cases_and_required_tags():
    cases = load_cases(ROOT / "eval" / "testsets" / "week2_cases.jsonl")
    assert len(cases) == 40
    assert len({c["id"] for c in cases}) == 40
    type_counts = Counter(c["case_type"] for c in cases)
    assert type_counts["unanswerable"] >= 5
    assert type_counts["adversarial"] >= 5
    assert type_counts["edge"] >= 5
    urg_counts = Counter(c["expected_urgency"] for c in cases)
    assert urg_counts["P4"] >= 2
    pairs = Counter(c["pair_id"] for c in cases if c.get("pair_id"))
    assert len(pairs) == 6
    assert all(v == 2 for v in pairs.values())


def test_w2_4_and_w2_5_statistics_and_dry_harness(tmp_path):
    ci = proportion_ci95(32, 40)
    assert ci["value"] == 0.8
    assert ci["n"] == 40
    assert ci["ci95"] == [0.676, 0.924]

    mc = mcnemar_test([False] * 20 + [True] * 20, [True] * 35 + [False] * 5)
    assert mc["n"] == 40
    assert mc["discordant_pairs"] == mc["n10_a_only"] + mc["n01_b_only"]
    assert 0.0 <= mc["exact_binomial_p"] <= 1.0

    scoreboard, _ = run_harness(
        provider_name="dry",
        model_name="dry",
        out_dir=tmp_path,
        versions=("v1", "v2", "v3"),
    )
    assert scoreboard["week"] == 2
    assert scoreboard["test_set_size"] == 40
    assert (tmp_path / "scoreboard.json").exists()
    assert (tmp_path / "prompt_comparison.md").exists()


def test_w2_6_cohens_kappa_and_deterministic_audit():
    h = [True, True, False, False, True, False, True, False, True, False]
    j = [True, True, False, False, True, False, False, False, True, False]
    stats = cohens_kappa(h, j)
    assert stats["n"] == 10
    assert stats["observed_agreement_po"] == 0.9
    assert stats["cohens_kappa"] > 0.75

    sample_case = {
        "id": "W1-24",
        "lang": "en",
        "expected_intent": "field_complaint",
        "expected_urgency": "P2",
        "forbidden_claims": ["TICKET CREATED - P1 URGENT"],
    }
    bad_audit = deterministic_reply_audit(sample_case, {}, "TICKET CREATED - P1 URGENT")
    assert bad_audit["pass"] is False
    assert bad_audit["hallucination_type"] == "unfaithful"


def test_w2_7_and_w2_8_generated_artifacts():
    w2_dir = ROOT / "eval" / "results" / "week2"
    sb = json.loads((w2_dir / "scoreboard.json").read_text(encoding="utf-8"))
    assert sb["week"] == 2
    assert sb["test_set_size"] == 40
    assert sb["e2e_accuracy"]["n"] == 40
    assert sb["abstention_correct"]["n"] == 8

    cal = json.loads((w2_dir / "judge_calibration.json").read_text(encoding="utf-8"))
    assert cal["summary"]["n"] == 20
    assert cal["summary"]["cohens_kappa"] >= 0.50

    hlog = json.loads((w2_dir / "hallucination_log.json").read_text(encoding="utf-8"))
    assert len(hlog) >= 10
    assert {x["type"] for x in hlog} == {"fabricated_fact", "unfaithful", "reasoning_error"}

    inj = json.loads((w2_dir / "injection_test_results.json").read_text(encoding="utf-8"))
    assert inj["attack_count"] >= 3
    assert (ROOT / "reports" / "week-2.md").exists()

