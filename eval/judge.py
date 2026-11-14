"""Şema doğrulamalı, yeniden denemeli açık uçlu cevap değerlendiricisi."""

import hashlib
from html import escape
import json
from pathlib import Path


def load_prompt(path):
    """Return prompt without YAML front matter and SHA-256 of original file bytes."""
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            raise ValueError("Unclosed prompt front matter")
        text = "".join(lines[end + 1:])
    return text.strip(), hashlib.sha256(raw).hexdigest()


def _validate(output):
    try:
        value = json.loads(output)
    except (TypeError, ValueError):
        raise ValueError("Invalid JSON") from None
    required = {"label", "abstained", "fabrication", "claims_unperformed_action", "reason"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Object must contain exactly the five required keys")
    if value["label"] not in ("pass", "fail"):
        raise ValueError("label must be pass or fail")
    for key in ("abstained", "fabrication", "claims_unperformed_action"):
        if type(value[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    if not isinstance(value["reason"], str) or not 1 <= len(value["reason"].split()) <= 30:
        raise ValueError("reason must contain 1 to 30 words")
    return value


def judge(case: dict, answer_text: str, provider, *,
          prompt_path="prompts/judge/v1.md", max_retries=2, seed=42) -> dict:
    """Evaluate with temperature=0 and JSON mode; retries are in addition to the first call.

    Invalid output, provider failures and prompt/input errors return valid=False,
    label=None and errors rather than raising. Token counts sum all received attempts;
    if any received response lacks a valid count, that total is None (unknown, never 0).
    """
    result = {"label": None, "abstained": None, "fabrication": None,
              "claims_unperformed_action": None, "reason": None, "valid": False,
              "attempts": 0, "errors": [], "input_tokens": 0, "output_tokens": 0,
              "prompt_sha256": None}
    try:
        if type(max_retries) is not int or max_retries < 0:
            raise ValueError("max_retries must be a nonnegative integer")
        system, result["prompt_sha256"] = load_prompt(prompt_path)
        if type(case["answerable"]) is not bool:
            raise ValueError("answerable must be boolean")
        user = "\n".join(
            f"<{name}>\n{escape(str(value), quote=False)}\n</{name}>"
            for name, value in (
                ("citizen_message", case["text"]),
                ("expected_behavior", case["expected_behavior"]),
                ("answerable", json.dumps(case["answerable"])),
                ("assistant_answer", answer_text),
            )
        )
    except Exception as exc:
        result["errors"].append(f"Prompt/input error: {type(exc).__name__}")
        return result
    for attempt in range(max_retries + 1):
        result["attempts"] = attempt + 1
        request = user
        if result["errors"]:
            request += ("\n\nYour previous output was invalid: " + result["errors"][-1]
                        + ". Return ONLY one JSON object.")
        try:
            response = provider.generate(system=system, user=request, temperature=0,
                                         max_tokens=512, seed=seed, json_mode=True)
        except Exception as exc:
            result["errors"].append(f"Provider error: {type(exc).__name__}")
            continue
        try:
            if not isinstance(response, dict):
                result["input_tokens"] = result["output_tokens"] = None
                raise ValueError("Provider response must be an object")
            for key in ("input_tokens", "output_tokens"):
                count = response.get(key)
                valid_count = type(count) is int and count >= 0
                result[key] = result[key] + count if valid_count and result[key] is not None else None
            value = _validate(response.get("output"))
        except ValueError as exc:
            result["errors"].append(str(exc))
            continue
        result.update(value, valid=True)
        return result
    return result
