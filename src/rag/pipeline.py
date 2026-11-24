"""Two-stage Beldesk pipeline connecting Week 2 Classifier -> Week 3 RAG (Handbook Section 2).

Stage 1 (Understand): Deterministic JSON request classifier (`src.classifier.classify`).
Stage 2 (Answer):     Role-filtered hybrid RAG retrieval + cited answer (`src.rag`).

- Pure `emergency` requests receive an immediate deterministic 112 redirection without RAG.
- `out_of_scope` requests receive an immediate deterministic refusal without RAG.
- `faq`, `field_complaint`, and `status_inquiry` requests proceed to public/authorized RAG
  retrieval and source-grounded answer generation, preserving classifier metadata (intent,
  urgency, issues, missing_fields) for downstream Week 4 tools.
"""
from __future__ import annotations

from src.classifier.classify import classify
from .answer import _language, answer_with_sources
from .retrieval import source_context

EMERGENCY_RESPONSE = {
    "tr": (
        "ACİL DURUM: Lütfen derhal 112 Acil Çağrı Merkezi'ni arayın. "
        "Beldesk acil müdahale veya ambulans/itfaiye/polis yönlendirmesi yapamaz."
    ),
    "en": (
        "EMERGENCY: Please call 112 immediately. "
        "Beldesk cannot dispatch emergency services or confirm emergency intervention."
    ),
}

OUT_OF_SCOPE_RESPONSE = {
    "tr": (
        "Bu talep Yeşilvadi Belediyesi Beyaz Masa asistanının kapsamı dışındadır. "
        "Belediye hizmet rehberleri veya saha arıza bildirimleri hakkında yardımcı olabilirim."
    ),
    "en": (
        "This request is outside the scope of the Yeşilvadi Municipality Beyaz Masa assistant. "
        "I can help with municipal service guidance and field problem reports."
    ),
}


def _resolve_language(text: str, classification: dict, explicit_language: str | None) -> str:
    if explicit_language in {"tr", "en"}:
        return explicit_language
    result = classification.get("result") or {}
    cls_lang = result.get("lang")
    if cls_lang in {"tr", "en"}:
        return cls_lang
    return _language(text, None)


def handle_citizen_request(
    text: str,
    provider,
    retriever,
    *,
    role: str = "public",
    k: int = 5,
    language: str | None = None,
    classifier_prompt_path: str = "prompts/classifier/v1.md",
    classifier_retries: int = 1,
    rag_retries: int = 0,
    seed: int = 42,
) -> dict:
    """Run Stage 1 (Week 2 Classifier) and route to Stage 2 (Week 3 RAG) when appropriate."""
    classification = classify(
        text,
        provider,
        prompt_path=classifier_prompt_path,
        max_retries=classifier_retries,
        seed=seed,
    )
    lang = _resolve_language(text, classification, language)

    if classification.get("valid") and isinstance(classification.get("result"), dict):
        cls_obj = classification["result"]
        intent = cls_obj.get("intent")
        secondary = cls_obj.get("secondary_intents") or []

        # Pure emergency without a municipal field complaint -> immediate 112 redirection
        if intent == "emergency" and "field_complaint" not in secondary:
            return {
                "route": "emergency_112",
                "stage_executed": "classifier_only",
                "language": lang,
                "classification": classification,
                "retrieval": None,
                "sources": [],
                "generation": {
                    "valid": True,
                    "abstained": False,
                    "answer": EMERGENCY_RESPONSE[lang],
                    "claims": [],
                    "sources": [],
                    "error": None,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }

        # Out-of-scope request -> immediate deterministic refusal without RAG call
        if intent == "out_of_scope":
            return {
                "route": "out_of_scope",
                "stage_executed": "classifier_only",
                "language": lang,
                "classification": classification,
                "retrieval": None,
                "sources": [],
                "generation": {
                    "valid": True,
                    "abstained": True,
                    "answer": OUT_OF_SCOPE_RESPONSE[lang],
                    "claims": [],
                    "sources": [],
                    "error": None,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }

        route = f"rag_{intent}"
    else:
        # Classifier unavailable or schema-invalid -> safe fallback to RAG retrieval
        route = "rag_fallback"

    retrieval = retriever.search(text, role=role, k=k)
    sources = source_context(retrieval)
    generation = answer_with_sources(
        text,
        provider,
        sources,
        language=lang,
        max_retries=rag_retries,
    )
    return {
        "route": route,
        "stage_executed": "classifier_then_rag",
        "language": lang,
        "classification": classification,
        "retrieval": retrieval,
        "sources": sources,
        "generation": generation,
    }
