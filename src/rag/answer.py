"""Validated source-grounded answer generation (W3.4), separate from retrieval.

The model emits atomic claims with exact evidence quotes. Software checks structure
and citation provenance and renders the final answer; semantic entailment is still
an evaluation task, not established by matching a quote. No test gold labels enter
this module. No database/write/payment tool is available.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

from eval.judge import load_prompt
from src.baseline.providers import make_provider
from .corpus import ROOT


DEFAULT_CONFIG = ROOT / "config/rag_answer.json"


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _language(text, language):
    if language is not None:
        if language not in {"tr", "en"}:
            raise ValueError("language must be tr or en")
        return language
    words = re.findall(r"[\w]+", text.lower())
    en = sum(w in {"what", "how", "where", "when", "can", "could", "does", "do", "is", "are", "the", "my", "which", "have", "need"} for w in words)
    tr = sum(w in {"nasıl", "hangi", "ne", "için", "bir", "var", "mı", "mi", "ben", "gerekli", "gerekiyor", "başvuru"} for w in words)
    return "en" if en > tr else "tr"


def _sources(sources):
    if not isinstance(sources, list):
        raise ValueError("sources must be an authorized source list")
    ids = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Every source must be an object")
        cid = source.get("citation")
        if type(cid) is not int or cid < 1 or cid in ids:
            raise ValueError("Source citation numbers must be unique positive integers")
        if not isinstance(source.get("text"), str) or not source["text"].strip():
            raise ValueError("Every source needs nonempty text")
        ids.add(cid)
    # Snapshot input so a caller cannot mutate sources while the request is running.
    return json.loads(json.dumps(sources, ensure_ascii=False))


PERFORMED_ACTION = re.compile(
    r"\b(?:i\s+(?:have\s+)?(?:created|opened|submitted|forwarded|updated|checked|dispatched|booked|paid)|"
    r"i\s+(?:will|am going to)\s+(?:create|open|submit|forward|update|dispatch|book)|"
    r"(?:your\s+)?(?:ticket|report|application|reservation)\s+(?:has been|was)\s+(?:created|opened|submitted|forwarded|updated|booked))\b"
    r"|\b(?:kaydınızı|talebinizi|başvurunuzu|şikayetinizi|şikâyetinizi|randevunuzu)\s+(?:oluşturdum|açtım|ilettim|gönderdim|güncelledim|kontrol ettim|oluşturacağım|açacağım|ileteceğim|göndereceğim)\b"
    r"|\b(?:kayıt|talep|başvuru|ekip)\s+(?:oluşturuldu|açıldı|iletildi|gönderildi|yönlendirildi)\b",
    re.IGNORECASE,
)


def _claim_action_error(text):
    """Catch clear positive action claims; absence of a match is not a safety proof."""
    for match in PERFORMED_ACTION.finditer(text):
        # Explicit negation is safe to state, unlike a completed action claim.
        before = text[max(0, match.start()-12):match.start()].lower()
        if re.search(r"\b(?:no|not|never)\s*$", before):
            continue
        return True
    return False


def validate_output(output, sources, config):
    """Validate structure, known citations and exact quote provenance, not entailment."""
    try:
        def unique_keys(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError("Duplicate JSON keys are not allowed")
                obj[key] = value
            return obj
        value = json.loads(output, object_pairs_hook=unique_keys)
    except (TypeError, ValueError):
        raise ValueError("Return one valid JSON object without Markdown") from None
    if not isinstance(value, dict) or set(value) != {"answerable", "claims"}:
        raise ValueError("Required keys are exactly answerable and claims")
    if type(value["answerable"]) is not bool or not isinstance(value["claims"], list):
        raise ValueError("answerable must be boolean and claims must be an array")
    claims = value["claims"]
    if bool(claims) != value["answerable"]:
        raise ValueError("claims must be nonempty if and only if answerable is true")
    if len(claims) > config["max_claims"]:
        raise ValueError("Too many claims")
    by_id = {s["citation"]: s for s in sources}
    validated = []
    for index, claim in enumerate(claims, 1):
        if not isinstance(claim, dict) or set(claim) != {"text", "citations", "evidence"}:
            raise ValueError(f"Claim {index}: required keys are text, citations, evidence")
        text = claim["text"]
        if not isinstance(text, str) or not 1 <= len(text.split()) <= config["max_words_per_claim"] or "\n" in text:
            raise ValueError(f"Claim {index}: text must be a short nonempty single-line claim")
        if re.search(r"\[\s*\d", text):
            raise ValueError(f"Claim {index}: do not put citation numbers in claim text")
        if _claim_action_error(text):
            raise ValueError(f"Claim {index}: external-action claim or promise is not allowed")
        citations = claim["citations"]
        if not isinstance(citations, list) or not citations or any(type(c) is not int for c in citations):
            raise ValueError(f"Claim {index}: citations must be nonempty integer array")
        if len(citations) != len(set(citations)) or not set(citations) <= by_id.keys():
            raise ValueError(f"Claim {index}: duplicate or nonexistent source citation")
        evidence = claim["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Claim {index}: evidence is required")
        referenced = set()
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"citation", "quote"}:
                raise ValueError(f"Claim {index}: evidence needs citation and quote only")
            cid, quote = item["citation"], item["quote"]
            if type(cid) is not int or cid not in citations:
                raise ValueError(f"Claim {index}: evidence citation must match a cited source")
            if not isinstance(quote, str) or not 8 <= len(quote.strip()) <= config["max_evidence_characters"]:
                raise ValueError(f"Claim {index}: evidence quote length is invalid")
            if quote not in by_id[cid]["text"]:
                raise ValueError(f"Claim {index}: quote is not an exact substring of source {cid}")
            referenced.add(cid)
        if referenced != set(citations):
            raise ValueError(f"Claim {index}: every citation needs matching exact evidence")
        validated.append({"claim_id": f"C{index}", "text": text.strip(),
                          "citations": citations, "evidence": evidence})
    return {"answerable": value["answerable"], "claims": validated}


def render_answer(claims):
    """A final answer cannot contain prose absent from its scored claim list."""
    return "\n".join(c["text"] + " " + "".join(f"[{n}]" for n in c["citations"]) for c in claims)


def answer_with_sources(text, provider, sources, *, language=None, config_path=None, max_retries=None):
    """Return source-grounded answer/report; errors never masquerade as honest abstention.

    `provider` exposes the existing generate(system,user,temperature,max_tokens,seed,
    json_mode=True) interface. Caller controls transport pacing/retries. This function
    performs bounded corrective retries for malformed/invalid structured answers.
    Sources must already be authorized by the application/retrieval layer.
    """
    started = time.monotonic()
    report = {"answer": None, "claims": [], "sources": [], "abstained": False, "valid": False,
              "error": None, "errors": [], "attempts": 0, "input_tokens": 0, "output_tokens": 0,
              "latency_s": 0.0, "language": None, "prompt_sha256": None, "config_sha256": None,
              "code_sha256": _hash(Path(__file__).read_bytes()), "input_sha256": None,
              "finish_reason": None, "raw_outputs": [], "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    try:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Citizen message must be nonempty text")
        language = _language(text, language)
        report["language"] = language
        raw_config = Path(config_path or DEFAULT_CONFIG).read_bytes()
        config = json.loads(raw_config)
        report["config_sha256"] = _hash(raw_config)
        prompt_path = Path(config["prompt_path"])
        if not prompt_path.is_absolute():
            prompt_path = ROOT/prompt_path
        system, report["prompt_sha256"] = load_prompt(prompt_path)
        sources = _sources(sources)
        report["sources"] = sources
        user = json.dumps({"citizen_message": text, "language": language, "sources": sources}, ensure_ascii=False)
        report["input_sha256"] = _hash(user.encode("utf-8"))
        if not sources:
            report.update(answer=config["fallback"][language], abstained=True, valid=True)
            return report
        retries = config["max_retries"] if max_retries is None else max_retries
        if type(retries) is not int or not 0 <= retries <= 3:
            raise ValueError("max_retries must be an integer between 0 and 3")
        feedback = ""
        for attempt in range(retries+1):
            report["attempts"] = attempt+1
            try:
                response = provider.generate(system, user+feedback, config["temperature"],
                                             config["max_output_tokens"], config["seed"], json_mode=True)
            except Exception as exc:
                # ProviderError is already sanitized by the shared adapter; avoid
                # arbitrary exception strings, which could include credentials.
                report["error"] = f"provider_error:{type(exc).__name__}"
                report["errors"].append(report["error"])
                report["input_tokens"] = report["output_tokens"] = None
                return report
            if not isinstance(response, dict):
                report["error"] = "invalid_provider_response"
                report["input_tokens"] = report["output_tokens"] = None
                return report
            for key in ("input_tokens", "output_tokens"):
                count = response.get(key)
                report[key] = report[key]+count if type(count) is int and count >= 0 and report[key] is not None else None
            raw = response.get("output")
            report["raw_outputs"].append(raw)
            report["finish_reason"] = response.get("finish_reason")
            try:
                parsed = validate_output(raw, sources, config)
            except ValueError as exc:
                report["errors"].append(str(exc))
                feedback = "\n\nValidation feedback: " + str(exc) + ". Return corrected JSON only."
                continue
            report.update(claims=parsed["claims"], valid=True, abstained=not parsed["answerable"])
            report["answer"] = render_answer(parsed["claims"]) if parsed["answerable"] else config["fallback"][language]
            return report
        report["error"] = "validation_retries_exhausted"
        return report
    except Exception as exc:
        report["error"] = f"input_or_config_error:{type(exc).__name__}"
        return report
    finally:
        report["latency_s"] = time.monotonic()-started


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("text")
    p.add_argument("--provider", default="gemini", choices=["gemini", "ollama", "openai_compat"])
    p.add_argument("--model", default="gemini-3.1-flash-lite")
    p.add_argument("--language", choices=["tr", "en"])
    p.add_argument("--json", action="store_true", help="Print the full evidence/claim report")
    args = p.parse_args(argv)
    from .retrieval import Retriever, source_context
    found = Retriever().search(args.text, role="public", k=5)
    provider = make_provider(args.provider, args.model)
    result = answer_with_sources(args.text, provider, source_context(found), language=args.language)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["error"]:
        print(json.loads(DEFAULT_CONFIG.read_text())["error_message"][result["language"] or "tr"])
    else:
        print(result["answer"])
        if result["claims"]:
            used = {n for claim in result["claims"] for n in claim["citations"]}
            for source in result["sources"]:
                if source["citation"] in used:
                    print(f"[{source['citation']}] {source['title']} — {source['heading']} ({source['passage_id']})")
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
