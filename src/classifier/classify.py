"""Deterministic classification with bounded validation and transport retries."""

import argparse
import hashlib
import json
from pathlib import Path
import time

from src.baseline.providers import ProviderError, make_provider
from .schema import validate


ROOT = Path(__file__).resolve().parents[2]


def load_prompt(path):
    path = Path(path)
    if not path.is_absolute() and not path.exists():
        path = ROOT / path
    content = path.read_bytes()
    text = content.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                text = "".join(lines[i + 1:]).lstrip("\r\n")
                break
    return text, hashlib.sha256(content).hexdigest()


def _parse(raw):
    # Önce bütünü ayrıştır: nesne içeren bir JSON listesi kabul edilmemeli.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        if cleaned.startswith("["):
            raise ValueError("result: expected object, not array")
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end < start:
            raise ValueError("result: invalid JSON object") from None
        return json.loads(cleaned[start:end + 1])


def classify(text, provider, *, prompt_path="prompts/classifier/v1.md", max_retries=2,
             seed=42, max_tokens=800) -> dict:
    started = time.monotonic()
    report = {"result": None, "valid": False, "attempts": 0, "errors": [],
              "raw_outputs": [], "input_tokens": 0, "output_tokens": 0,
              "latency_s": 0.0, "prompt_sha256": "", "provider_error": None}
    try:
        system, report["prompt_sha256"] = load_prompt(prompt_path)
        feedback = ""
        for _ in range(1 + max_retries):
            report["attempts"] += 1
            for transport_attempt in range(2):
                try:
                    response = provider.generate(system + feedback, text, 0, max_tokens, seed, json_mode=True)
                    break
                except ProviderError as exc:
                    if exc.retryable and transport_attempt == 0:
                        time.sleep(2)
                        continue
                    report["provider_error"] = str(exc)
                    return report
            raw = response.get("output", "")
            report["raw_outputs"].append(raw)
            for key in ("input_tokens", "output_tokens"):
                count = response.get(key)
                report[key] = None if count is None or report[key] is None else report[key] + count
            parse_failed = False
            try:
                obj = _parse(raw)
            except (ValueError, TypeError) as exc:
                errors = [f"result: JSON parse error ({exc})"]
                parse_failed = True
            else:
                errors = validate(obj)
            report["errors"] = errors
            if not errors:
                report.update(result=obj, valid=True)
                return report
            detail = "; ".join(errors[:3])[:400]
            feedback = (f"\n\nYour previous output was invalid: {detail}. "
                        "Return ONLY one JSON object that follows the schema.")
            if parse_failed and response.get("finish_reason") == "MAX_TOKENS":
                feedback += " Please keep the JSON short."
    except Exception as exc:
        # İstemci, dosya ve beklenmedik sağlayıcı hataları da yapılandırılmış döner.
        report["errors"] = [f"classifier: {type(exc).__name__}"]
    finally:
        report["latency_s"] = time.monotonic() - started
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("gemini", "dry", "ollama", "openai_compat"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("text")
    args = parser.parse_args()
    try:
        provider = make_provider(args.provider, args.model)
    except Exception as exc:
        print(json.dumps({"valid": False, "result": None, "provider_error": str(exc)}))
        return
    print(json.dumps(classify(args.text, provider), ensure_ascii=False))


if __name__ == "__main__":
    main()
