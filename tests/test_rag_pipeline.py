"""Offline unit tests for the two-stage Classifier -> RAG pipeline (src/rag/pipeline.py)."""
import json

from src.rag.pipeline import (
    EMERGENCY_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    handle_citizen_request,
)


SAMPLE_RESULT = {
    "rank": 1,
    "chunk_id": "YV-D003#requirements:0-100:abc",
    "doc_id": "YV-D003",
    "passage_id": "YV-D003#requirements",
    "title": "Yeşilvadi Su Aboneliği Başvuru Rehberi",
    "heading": "Başvuruda istenen belgeler",
    "source": "beldesk://synthetic/YV-D003",
    "version": "citizen-v2",
    "text": "Kiracı için kira sözleşmesi ve kimlik belgesi gerekir.",
    "access": ["public"],
}


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, query, role="public", k=5):
        self.calls.append((query, role, k))
        return {"query": query, "results": [SAMPLE_RESULT], "timings_s": {"total": 0.005}}


class FakeProvider:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, system, user, temperature, max_tokens, seed, json_mode=True):
        self.calls.append((system, user, temperature, max_tokens, seed, json_mode))
        out = next(self.outputs)
        return {"output": out, "input_tokens": 50, "output_tokens": 25, "finish_reason": "STOP"}


def _cls_payload(intent, lang="tr", issues=None, secondary=None):
    return json.dumps({
        "lang": lang,
        "intent": intent,
        "secondary_intents": secondary or [],
        "issues": issues or [],
        "ticket_id": None,
        "missing_fields": [],
    })


def _rag_payload(text, quote):
    return json.dumps({
        "answerable": True,
        "claims": [{
            "text": text,
            "citations": [1],
            "evidence": [{"citation": 1, "quote": quote}],
        }],
    })


def test_faq_routes_through_classifier_then_rag():
    retriever = FakeRetriever()
    provider = FakeProvider([
        _cls_payload("faq", lang="tr"),
        _rag_payload("Kiracı için kira sözleşmesi ve kimlik belgesi gerekir.", "Kiracı için kira sözleşmesi ve kimlik belgesi gerekir."),
    ])
    out = handle_citizen_request("Kiracıyım, su aboneliği için hangi belgeler lazım?", provider, retriever)
    assert out["route"] == "rag_faq"
    assert out["stage_executed"] == "classifier_then_rag"
    assert len(retriever.calls) == 1
    assert retriever.calls[0][1] == "public"
    assert out["generation"]["valid"] is True
    assert "[1]" in out["generation"]["answer"]


def test_emergency_short_circuits_to_112_without_rag():
    retriever = FakeRetriever()
    provider = FakeProvider([_cls_payload("emergency", lang="tr")])
    out = handle_citizen_request("Komşum nefes alamıyor bayıldı!", provider, retriever)
    assert out["route"] == "emergency_112"
    assert out["stage_executed"] == "classifier_only"
    assert len(retriever.calls) == 0
    assert out["generation"]["answer"] == EMERGENCY_RESPONSE["tr"]
    assert "112" in out["generation"]["answer"]


def test_out_of_scope_short_circuits_without_rag():
    retriever = FakeRetriever()
    provider = FakeProvider([_cls_payload("out_of_scope", lang="en")])
    out = handle_citizen_request("Who should I vote for in the election?", provider, retriever)
    assert out["route"] == "out_of_scope"
    assert out["stage_executed"] == "classifier_only"
    assert len(retriever.calls) == 0
    assert out["generation"]["abstained"] is True
    assert out["generation"]["answer"] == OUT_OF_SCOPE_RESPONSE["en"]


def test_field_complaint_preserves_classifier_issues_and_calls_rag():
    retriever = FakeRetriever()
    issue = {
        "category": "water_sewer",
        "urgency": "P2",
        "urgency_status": "classified",
        "urgency_reason": "Active burst pipe flooding street",
        "location": {"neighborhood": "Yeşilova", "street": "Selvi", "detail": None},
        "scope": "street",
        "onset_text": None,
        "sensitive_use": None,
        "referral_needed": "no",
    }
    provider = FakeProvider([
        _cls_payload("field_complaint", lang="tr", issues=[issue]),
        _rag_payload("Kiracı için kira sözleşmesi ve kimlik belgesi gerekir.", "Kiracı için kira sözleşmesi ve kimlik belgesi gerekir."),
    ])
    out = handle_citizen_request("Selvi sokakta su borusu patladı.", provider, retriever)
    assert out["route"] == "rag_field_complaint"
    assert out["stage_executed"] == "classifier_then_rag"
    assert out["classification"]["result"]["issues"][0]["urgency"] == "P2"
    assert len(retriever.calls) == 1


def test_classifier_failure_falls_back_safely_to_rag():
    retriever = FakeRetriever()
    provider = FakeProvider([
        "not json",
        "still not json",
        _rag_payload("Kiracı için kira sözleşmesi ve kimlik belgesi gerekir.", "Kiracı için kira sözleşmesi ve kimlik belgesi gerekir."),
    ])
    out = handle_citizen_request("Su aboneliği belgeleri neler?", provider, retriever, classifier_retries=1)
    assert out["route"] == "rag_fallback"
    assert out["stage_executed"] == "classifier_then_rag"
    assert out["classification"]["valid"] is False
    assert len(retriever.calls) == 1
    assert out["generation"]["valid"] is True
