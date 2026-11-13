"""Request classifier runner at temperature 0 with validation and retry (W2.1)."""

import argparse
import json
from pathlib import Path
import re
import time

from src.baseline.providers import DryProvider, ProviderError, make_provider
from .schema import derive_department, extract_json_object, validate_classification

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLASSIFIER_PROMPT = ROOT / "prompts" / "classifier_v1.md"


def _dry_classify(user_text):
    """Deterministic schema-valid synthetic classifier output for offline dry-run tests."""
    is_tr = bool(re.search(r"[çğıöşüÇĞİÖŞÜ]|\b(mahalle|sokak|başvuru|şikayet|nedir|nasıl)\b", user_text, re.I))
    tid_match = re.search(r"YV-\d{4}-\d{6}", user_text)
    last4_match = re.search(r"\b(\d{4})\b", user_text.replace(tid_match.group(0), "") if tid_match else user_text)
    inj = bool(re.search(r"ignore|override|maintenance mode|\[SYSTEM|<!--|kuralları unut", user_text, re.I))
    third_party = bool(re.search(r"komşu|neighbor|colleague|başkasının", user_text, re.I))
    if re.search(r"ambulans|nefes alamıyo|112\b", user_text, re.I):
        intent, cat, urg, abstain = "emergency", None, None, True
    elif re.search(r"fatura.*öde|sue|legal rights|mayor's new parking|Mavikent|maaş|tax exemption", user_text, re.I):
        intent, cat, urg, abstain = "out_of_scope", None, None, True
    elif tid_match and not re.search(r"yeni şikayet|update|collapsed", user_text, re.I):
        intent, cat, urg, abstain = "status_inquiry", None, None, True
    elif re.search(r" çukur|pothole|kaldırım|sidewalk|lamba|streetlight|çöp|garbage|pipe|boru|kablo|cable|bank|bench|salıncak|swing|ışığı|traffic light|köpek|dog|matkap|noise|çim|grass", user_text, re.I):
        intent, cat, urg, abstain = "field_complaint", "roads_sidewalks", "P3", third_party
    else:
        intent, cat, urg, abstain = "faq", None, None, True
    payload = {
        "intent": intent,
        "language": "tr" if is_tr else "en",
        "category": cat,
        "urgency": urg,
        "urgency_reason": "Dry-run synthetic rubric classification" if urg else None,
        "entities": {
            "neighborhood": None,
            "street": None,
            "ticket_id": tid_match.group(0) if tid_match else None,
            "contact_last4": last4_match.group(1) if last4_match else None,
            "third_party_ticket": third_party,
        },
        "needs_abstention": abstain,
        "injection_detected": inj,
        "classifier_version": "classifier-v1",
        "reply": "[dry-run] Talebiniz alındı." if is_tr else "[dry-run] Request received.",
    }
    return json.dumps(payload, ensure_ascii=False)


def classify_request(
    provider,
    text,
    *,
    system_prompt=None,
    prompt_path=DEFAULT_CLASSIFIER_PROMPT,
    max_retries=2,
    max_output_tokens=600,
    seed=42,
    require_reply=False,
    rpm=None,
    last_call_ts=None,
):
    """Run request classification at strictly temperature=0 with schema validation and retry.

    Returns a dictionary with:
      - valid_json: bool
      - attempts: int
      - validation_errors: list[str]
      - classification: dict or None
      - department: dict or None (server-derived from category)
      - raw_output: str
      - input_tokens: int
      - output_tokens: int
      - latency_s: float
      - error: str or None
      - last_call_ts: float
    """
    system = system_prompt if system_prompt is not None else Path(prompt_path).read_text(encoding="utf-8").strip()
    wrapped_user = f"<citizen_message>{text}</citizen_message>"
    current_user = wrapped_user

    total_in_tokens = 0
    total_out_tokens = 0
    total_latency_s = 0.0
    attempts = 0
    last_raw = ""
    last_errors = []
    parsed_obj = None
    call_ts = last_call_ts

    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        if not isinstance(provider, DryProvider) and rpm and call_ts is not None:
            wait_s = max(0.0, 60.0 / rpm - (time.monotonic() - call_ts))
            if wait_s > 0:
                time.sleep(wait_s)

        call_start = time.monotonic()
        call_ts = call_start
        resp = None
        for net_attempt in range(5):
            try:
                call_start = time.monotonic()
                call_ts = call_start
                if isinstance(provider, DryProvider):
                    resp = {
                        "output": _dry_classify(text),
                        "input_tokens": len(current_user) // 4,
                        "output_tokens": 60,
                        "finish_reason": "STOP",
                    }
                else:
                    # W2.1 requires temperature = 0 strictly.
                    resp = provider.generate(system, current_user, 0.0, max_output_tokens, seed)
                break
            except ProviderError as exc:
                if exc.retryable and net_attempt < 4:
                    time.sleep(min(2 ** net_attempt, 16))
                    continue
                return {
                    "valid_json": False,
                    "attempts": attempts,
                    "validation_errors": [f"ProviderError: {exc}"],
                    "classification": None,
                    "department": None,
                    "raw_output": last_raw,
                    "input_tokens": total_in_tokens,
                    "output_tokens": total_out_tokens,
                    "latency_s": round(total_latency_s, 6),
                    "error": str(exc),
                    "last_call_ts": call_ts,
                }

        total_latency_s += time.monotonic() - call_start
        total_in_tokens += resp.get("input_tokens") or 0
        total_out_tokens += resp.get("output_tokens") or 0
        last_raw = resp.get("output") or ""

        try:
            candidate = extract_json_object(last_raw)
        except ValueError as exc:
            last_errors = [str(exc)]
            candidate = None

        if candidate is not None:
            is_valid, schema_errors = validate_classification(candidate, require_reply=require_reply)
            if is_valid:
                parsed_obj = candidate
                last_errors = []
                break
            last_errors = schema_errors

        if attempt < max_retries:
            error_bullet = "; ".join(last_errors)
            current_user = (
                f"{wrapped_user}\n\n"
                f"[VALIDATION_RETRY attempt={attempt + 1}]: Your previous output failed schema validation: "
                f"{error_bullet}. Return ONLY a corrected JSON object matching the exact schema."
            )

    dept = derive_department(parsed_obj.get("category")) if parsed_obj else None
    return {
        "valid_json": parsed_obj is not None,
        "attempts": attempts,
        "validation_errors": last_errors,
        "classification": parsed_obj,
        "department": dept,
        "raw_output": last_raw,
        "input_tokens": total_in_tokens,
        "output_tokens": total_out_tokens,
        "latency_s": round(total_latency_s, 6),
        "error": None if parsed_obj is not None else "Schema validation failed after retries",
        "last_call_ts": call_ts,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", default="dry", choices=["gemini", "ollama", "openai_compat", "dry"])
    p.add_argument("--model", default="dry")
    p.add_argument("--text", help="Single citizen message to classify")
    p.add_argument("--prompt", type=Path, default=DEFAULT_CLASSIFIER_PROMPT)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--base-url")
    p.add_argument("--api-key-env")
    args = p.parse_args(argv)
    provider = make_provider(args.provider, args.model, args.base_url, args.api_key_env)
    text = args.text or "Güneştepe mahallesi Akasya sokakta 3 gündür çöpler alınmıyor."
    result = classify_request(provider, text, prompt_path=args.prompt, max_retries=args.max_retries)
    result.pop("last_call_ts", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid_json"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
