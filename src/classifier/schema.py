"""JSON schema validation and server-side department routing for Beldesk (W2.1)."""

import json
import re

ALLOWED_INTENTS = {"faq", "field_complaint", "status_inquiry", "emergency", "out_of_scope"}
ALLOWED_LANGUAGES = {"tr", "en"}
ALLOWED_URGENCIES = {"P1", "P2", "P3", "P4", None}
ALLOWED_CATEGORIES = {
    "roads_sidewalks",
    "street_lighting",
    "waste_collection",
    "water_sewer",
    "parks_green",
    "traffic_signals",
    "permits_licensing",
    "social_services",
    "animals",
    "noise_environment",
    "other",
    None,
}

CATEGORY_TO_DEPARTMENT = {
    "roads_sidewalks": {"code": "public_works", "name_en": "Public Works Directorate", "name_tr": "Fen İşleri Müdürlüğü"},
    "street_lighting": {"code": "public_works", "name_en": "Public Works Directorate", "name_tr": "Fen İşleri Müdürlüğü"},
    "waste_collection": {"code": "sanitation", "name_en": "Sanitation Directorate", "name_tr": "Temizlik İşleri Müdürlüğü"},
    "water_sewer": {"code": "water_sewerage", "name_en": "Water & Sewerage Directorate", "name_tr": "Su ve Kanalizasyon Müdürlüğü"},
    "parks_green": {"code": "parks_gardens", "name_en": "Parks and Gardens Directorate", "name_tr": "Park ve Bahçeler Müdürlüğü"},
    "traffic_signals": {"code": "transportation", "name_en": "Transportation Directorate", "name_tr": "Ulaşım Müdürlüğü"},
    "permits_licensing": {"code": "zoning_licensing", "name_en": "Zoning & Licensing Directorate", "name_tr": "İmar ve Ruhsat Müdürlüğü"},
    "social_services": {"code": "social_services", "name_en": "Social Services Directorate", "name_tr": "Sosyal Hizmetler Müdürlüğü"},
    "animals": {"code": "veterinary", "name_en": "Veterinary Services Directorate", "name_tr": "Veteriner İşleri Müdürlüğü"},
    "noise_environment": {"code": "municipal_police", "name_en": "Environmental Protection / Zabıta", "name_tr": "Zabıta / Çevre Koruma Müdürlüğü"},
    "other": {"code": "beyaz_masa", "name_en": "Citizen Relations Desk", "name_tr": "Beyaz Masa"},
}

REQUIRED_TOP_KEYS = {
    "intent",
    "language",
    "category",
    "urgency",
    "urgency_reason",
    "entities",
    "needs_abstention",
    "injection_detected",
}

REQUIRED_ENTITY_KEYS = {
    "neighborhood",
    "street",
    "ticket_id",
    "contact_last4",
    "third_party_ticket",
}

TICKET_ID_RE = re.compile(r"^YV-\d{4}-\d{6}$")
LAST4_RE = re.compile(r"^\d{4}$")


def derive_department(category):
    """Derive canonical department deterministically on the server from category."""
    if not category:
        return None
    return CATEGORY_TO_DEPARTMENT.get(category)


def extract_json_object(raw_text):
    """Parse a JSON object from raw model text, stripping markdown code fences if present."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Empty model output")
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Output does not contain a JSON object")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON syntax: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Top-level JSON value must be an object")
    return parsed


def validate_classification(data, *, require_reply=False):
    """Validate a parsed classification dictionary against the Beldesk W2.1 schema.

    Returns (is_valid: bool, errors: list[str]).
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["Output is not a JSON object"]

    missing = sorted(REQUIRED_TOP_KEYS - set(data.keys()))
    if missing:
        errors.append(f"Missing required top-level keys: {missing}")

    if require_reply:
        reply = data.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            errors.append("Missing or empty 'reply' string")

    intent = data.get("intent")
    if intent not in ALLOWED_INTENTS:
        errors.append(f"Invalid 'intent': {intent!r}; expected one of {sorted(ALLOWED_INTENTS)}")

    language = data.get("language")
    if language not in ALLOWED_LANGUAGES:
        errors.append(f"Invalid 'language': {language!r}; expected 'tr' or 'en'")

    category = data.get("category")
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"Invalid 'category': {category!r}")

    urgency = data.get("urgency")
    if urgency not in ALLOWED_URGENCIES:
        errors.append(f"Invalid 'urgency': {urgency!r}; expected P1..P4 or null")

    urgency_reason = data.get("urgency_reason")
    if urgency is not None and (not isinstance(urgency_reason, str) or not urgency_reason.strip()):
        errors.append("'urgency_reason' must be a non-empty string when 'urgency' is set")
    if urgency_reason is not None and not isinstance(urgency_reason, str):
        errors.append("'urgency_reason' must be a string or null")

    if intent in {"faq", "status_inquiry", "emergency", "out_of_scope"} and urgency is not None:
        errors.append(f"'urgency' must be null when intent is {intent!r}")

    entities = data.get("entities")
    if not isinstance(entities, dict):
        errors.append("'entities' must be a JSON object")
    else:
        missing_ent = sorted(REQUIRED_ENTITY_KEYS - set(entities.keys()))
        if missing_ent:
            errors.append(f"Missing keys in 'entities': {missing_ent}")
        for str_key in ("neighborhood", "street"):
            val = entities.get(str_key)
            if val is not None and not isinstance(val, str):
                errors.append(f"entities.{str_key} must be a string or null")
        tid = entities.get("ticket_id")
        if tid is not None and (not isinstance(tid, str) or not TICKET_ID_RE.match(tid)):
            errors.append(f"entities.ticket_id {tid!r} must match YV-YYYY-NNNNNN or be null")
        last4 = entities.get("contact_last4")
        if last4 is not None and (not isinstance(last4, str) or not LAST4_RE.match(last4)):
            errors.append(f"entities.contact_last4 {last4!r} must be a 4-digit string or null")
        if not isinstance(entities.get("third_party_ticket"), bool):
            errors.append("entities.third_party_ticket must be a boolean")

    for bool_key in ("needs_abstention", "injection_detected"):
        if not isinstance(data.get(bool_key), bool):
            errors.append(f"'{bool_key}' must be a boolean")

    return len(errors) == 0, errors
