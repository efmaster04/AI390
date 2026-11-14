"""Pure Python validation against case-label contract v2."""

import json
import re
from pathlib import Path


CONTRACT_PATH = Path(__file__).resolve().parents[2] / "config/case_labels.json"


def validate(obj) -> list[str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = contract["case_format"]["expected"]
    errors = []

    def keys(value, required, path):
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return False
        for key in sorted(set(required) - value.keys()):
            errors.append(f"{path}.{key}: missing key")
        for key in sorted(value.keys() - set(required), key=str):
            errors.append(f"{path}.{key}: unexpected key")
        return True

    def vocab(value, name, path):
        if value not in contract[name]:
            errors.append(f"{path}: {value!r} not in {name}")

    def string(value, path, nullable=True):
        if not isinstance(value, str) and not (nullable and value is None):
            errors.append(f"{path}: expected {'string or null' if nullable else 'string'}")

    def sequence(value, name, path):
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return []
        seen = []
        for i, item in enumerate(value):
            vocab(item, name, f"{path}[{i}]")
            if item in seen:
                errors.append(f"{path}[{i}]: duplicate value")
            seen.append(item)
        return value

    if not keys(obj, set(expected) | {"lang"}, "result"):
        return errors
    vocab(obj.get("intent"), "intents", "intent")
    vocab(obj.get("lang"), "langs", "lang")
    secondary = sequence(obj.get("secondary_intents"), "intents", "secondary_intents")
    if obj.get("intent") in secondary:
        errors.append("secondary_intents: contains primary intent")
    sequence(obj.get("missing_fields"), "missing_field_values", "missing_fields")
    ticket = obj.get("ticket_id")
    if ticket is not None and (not isinstance(ticket, str) or not re.fullmatch(r"YV-\d{4}-\d{6}", ticket)):
        errors.append("ticket_id: expected YV-YYYY-NNNNNN or null")
    issues = obj.get("issues")
    if not isinstance(issues, list):
        errors.append("issues: expected array")
        return errors
    field = obj.get("intent") == "field_complaint" or "field_complaint" in secondary
    if bool(issues) != field:
        errors.append("issues: non-empty iff field_complaint is an intent")
    if (obj.get("intent") == "emergency" or "emergency" in secondary) and not field and issues:
        errors.append("issues: emergency without field_complaint requires empty array")
    for i, issue in enumerate(issues):
        path = f"issues[{i}]"
        if not keys(issue, set(expected["issues"][0]) | {"urgency_reason"}, path):
            continue
        for key, name in (("category", "categories"), ("urgency_status", "urgency_statuses"),
                          ("scope", "scopes"), ("referral_needed", "referral_values")):
            vocab(issue.get(key), name, f"{path}.{key}")
        urgency = issue.get("urgency")
        status = issue.get("urgency_status")
        if urgency is not None:
            vocab(urgency, "urgencies", f"{path}.urgency")
        if (urgency is None) != (status == "needs_clarification"):
            errors.append(f"{path}.urgency: null iff urgency_status is needs_clarification")
        reason = issue.get("urgency_reason")
        string(reason, f"{path}.urgency_reason", nullable=status != "classified")
        if status == "classified" and isinstance(reason, str) and not reason.strip():
            errors.append(f"{path}.urgency_reason: must not be empty when classified")
        for key in ("onset_text", "sensitive_use"):
            string(issue.get(key), f"{path}.{key}")
        location = issue.get("location")
        if location is not None and keys(location, {"neighborhood", "street", "detail"}, f"{path}.location"):
            for key, value in location.items():
                string(value, f"{path}.location.{key}")
    return errors
