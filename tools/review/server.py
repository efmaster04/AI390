"""Local review server for the Week 2 test set answer key.

Run:  .venv/bin/python -m tools.review.server [--cases PATH] [--port 8765]

Standard library only. Binds to 127.0.0.1. The cases file is re-read on every
request, and every save rewrites the whole file atomically (temp file + os.replace).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "eval" / "testsets" / "week2_cases.jsonl"
DEFAULT_LABELS = ROOT / "config" / "case_labels.json"
INDEX_HTML = HERE / "index.html"

ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
TICKET_RE = re.compile(r"^YV-\d{4}-\d{6}$")
EDITABLE_KEYS = ("expected", "expected_behavior", "answerable", "type", "review")
MAX_BODY = 1_000_000


class ValidationError(ValueError):
    pass


# ---------------------------------------------------------------- file access

class CaseStore:
    def __init__(self, cases_path: Path, labels_path: Path = DEFAULT_LABELS):
        self.cases_path = Path(cases_path)
        self.labels_path = Path(labels_path)
        self.lock = threading.Lock()

    def labels(self) -> dict:
        return json.loads(self.labels_path.read_text(encoding="utf-8"))

    def _read(self) -> list[dict]:
        cases = []
        text = self.cases_path.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValidationError(f"{self.cases_path.name} line {n} is not valid JSON: {exc.msg}") from exc
        return cases

    def read(self) -> list[dict]:
        with self.lock:
            return self._read()

    def _write(self, cases: list[dict]) -> None:
        data = "".join(json.dumps(c, ensure_ascii=False, separators=(",", ":")) + "\n" for c in cases)
        fd, tmp = tempfile.mkstemp(prefix=".review-", suffix=".tmp", dir=self.cases_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.cases_path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def update(self, case_id: str, payload: dict) -> dict:
        labels = self.labels()
        with self.lock:
            cases = self._read()
            for i, case in enumerate(cases):
                if case.get("id") == case_id:
                    new_case = apply_update(case, payload, labels)
                    cases[i] = new_case
                    self._write(cases)
                    return new_case
        raise KeyError(case_id)


# ---------------------------------------------------------------- validation
#
# Vocabularies come from config/case_labels.json (contract v2). The structural
# rules below implement that file's "rules" list; the label names they refer to
# (field_complaint, needs_clarification, unanswerable) are part of the contract.

FIELD_COMPLAINT = "field_complaint"
NEEDS_CLARIFICATION = "needs_clarification"
UNANSWERABLE = "unanswerable"
LOCATION_KEYS = ("neighborhood", "street", "detail")


def _one_of(value, allowed, field):
    if value not in allowed:
        raise ValidationError(f"{field}: {value!r} is not allowed; expected one of {allowed}")


def _opt_str(value, field):
    if value is not None and not isinstance(value, str):
        raise ValidationError(f"{field} must be a string or null")
    if value is None:
        return None
    return value.strip() or None


def _exact_keys(obj, keys, field):
    if not isinstance(obj, dict):
        raise ValidationError(f"{field} must be an object")
    extra = set(obj) - set(keys)
    if extra:
        raise ValidationError(f"{field} has unknown keys: {sorted(extra)}")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValidationError(f"{field} is missing keys: {missing}")


def _unique_list(value, allowed, field):
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list")
    for v in value:
        _one_of(v, allowed, field)
    if len(set(value)) != len(value):
        raise ValidationError(f"{field} contains duplicates")
    return list(value)


def _expected_keys(labels: dict) -> tuple:
    return tuple(labels["case_format"]["expected"].keys())


def _issue_keys(labels: dict) -> tuple:
    return tuple(labels["case_format"]["expected"]["issues"][0].keys())


def validate_location(loc, field):
    if loc is None:
        return None
    if not isinstance(loc, dict) or set(loc) != set(LOCATION_KEYS):
        raise ValidationError(f'{field} must be null or {{"neighborhood": str|null, "street": str|null, "detail": str|null}}')
    out = {k: _opt_str(loc[k], f"{field}.{k}") for k in LOCATION_KEYS}
    return out if any(out.values()) else None


def validate_issue(issue, labels: dict, field: str) -> dict:
    _exact_keys(issue, _issue_keys(labels), field)
    _one_of(issue["category"], labels["categories"], f"{field}.category")
    status = issue["urgency_status"]
    _one_of(status, labels["urgency_statuses"], f"{field}.urgency_status")
    urgency = issue["urgency"]
    if status == NEEDS_CLARIFICATION:
        if urgency is not None:
            raise ValidationError(f"{field}.urgency must be null when urgency_status is {NEEDS_CLARIFICATION}")
    else:
        if urgency is None:
            raise ValidationError(f"{field}.urgency is required (null only when urgency_status is {NEEDS_CLARIFICATION})")
        _one_of(urgency, labels["urgencies"], f"{field}.urgency")
    _one_of(issue["scope"], labels["scopes"], f"{field}.scope")
    _one_of(issue["referral_needed"], labels["referral_values"], f"{field}.referral_needed")
    return {
        "category": issue["category"],
        "urgency": urgency,
        "urgency_status": status,
        "location": validate_location(issue["location"], f"{field}.location"),
        "scope": issue["scope"],
        "onset_text": _opt_str(issue["onset_text"], f"{field}.onset_text"),
        "sensitive_use": _opt_str(issue["sensitive_use"], f"{field}.sensitive_use"),
        "referral_needed": issue["referral_needed"],
    }


def validate_expected(expected, labels: dict) -> dict:
    if labels.get("contract_version") != 2:
        raise ValidationError(f"case_labels.json contract_version {labels.get('contract_version')!r} is not supported (need 2)")
    keys = _expected_keys(labels)
    _exact_keys(expected, keys, "expected")

    intent = expected["intent"]
    _one_of(intent, labels["intents"], "expected.intent")
    sec = _unique_list(expected["secondary_intents"], labels["intents"], "expected.secondary_intents")
    if intent in sec:
        raise ValidationError("expected.secondary_intents must not repeat the primary intent")

    issues = expected["issues"]
    if not isinstance(issues, list):
        raise ValidationError("expected.issues must be a list")
    has_fc = intent == FIELD_COMPLAINT or FIELD_COMPLAINT in sec
    if has_fc and not issues:
        raise ValidationError(f"expected.issues must have at least one issue when {FIELD_COMPLAINT} is the intent or a secondary intent")
    if not has_fc and issues:
        raise ValidationError(f"expected.issues must be empty unless {FIELD_COMPLAINT} is the intent or a secondary intent"
                              + (" (emergency without a field complaint has no issues)" if "emergency" in [intent, *sec] else ""))
    clean_issues = [validate_issue(it, labels, f"expected.issues[{i}]") for i, it in enumerate(issues)]

    tid = expected["ticket_id"]
    if tid is not None and (not isinstance(tid, str) or not TICKET_RE.match(tid)):
        raise ValidationError("expected.ticket_id must be null or match YV-YYYY-NNNNNN")

    missing = _unique_list(expected["missing_fields"], labels["missing_field_values"], "expected.missing_fields")
    missing = [m for m in labels["missing_field_values"] if m in missing]  # canonical order

    out = {"intent": intent, "secondary_intents": sec, "issues": clean_issues, "ticket_id": tid, "missing_fields": missing}
    return {k: out[k] for k in keys}


def apply_update(case: dict, payload: dict, labels: dict) -> dict:
    """Return a new case with the editable fields replaced. Immutable fields are untouched."""
    if not isinstance(payload, dict):
        raise ValidationError("body must be a JSON object")
    unknown = set(payload) - set(EDITABLE_KEYS)
    if unknown:
        raise ValidationError(f"these fields cannot be edited here: {sorted(unknown)}")

    new = copy.deepcopy(case)

    if "expected" in payload:
        new["expected"] = validate_expected(payload["expected"], labels)
    if "expected_behavior" in payload:
        eb = payload["expected_behavior"]
        if not isinstance(eb, str) or not eb.strip():
            raise ValidationError("expected_behavior must be a non-empty string")
        new["expected_behavior"] = eb.strip()
    if "answerable" in payload:
        if not isinstance(payload["answerable"], bool):
            raise ValidationError("answerable must be true or false")
        new["answerable"] = payload["answerable"]
    if "type" in payload:
        _one_of(payload["type"], labels["types"], "type")
        new["type"] = payload["type"]
    if new.get("type") == UNANSWERABLE and new.get("answerable") is not False:
        raise ValidationError("answerable must be false when type is unanswerable")

    review = payload.get("review")
    if review is None:
        raise ValidationError("review is required")
    if not isinstance(review, dict):
        raise ValidationError("review must be an object")
    extra = set(review) - {"status", "reviewer", "note", "updated_at"}
    if extra:
        raise ValidationError(f"review has unknown keys: {sorted(extra)}")
    status = review.get("status")
    _one_of(status, labels["review_statuses"], "review.status")
    reviewer = _opt_str(review.get("reviewer"), "review.reviewer")
    if status != "pending" and not reviewer:
        raise ValidationError("review.reviewer (your name) is required to approve or change a case")
    new["review"] = {
        "status": status,
        "reviewer": reviewer,
        "note": _opt_str(review.get("note"), "review.note"),
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    return new


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    store: CaseStore  # set on the subclass by make_server
    server_version = "BeldeskReview/1.0"

    def log_message(self, fmt, *args):  # quieter console
        if os.environ.get("REVIEW_QUIET"):
            return
        super().log_message(fmt, *args)

    # -- helpers
    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: int, msg: str) -> None:
        self._json(status, {"error": msg})

    def _origin_ok(self) -> bool:
        host = self.headers.get("Host", "")
        if urlsplit("//" + host).hostname not in ALLOWED_HOSTS:
            return False
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin != "null" and urlsplit(origin).hostname in ALLOWED_HOSTS

    # -- verbs
    def do_GET(self):
        if not self._origin_ok():
            return self._error(403, "forbidden host/origin")
        path = urlsplit(self.path).path
        try:
            if path in ("/", "/index.html"):
                return self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            if path == "/api/labels":
                return self._json(200, self.store.labels())
            if path == "/api/cases":
                return self._json(200, self.store.read())
        except ValidationError as exc:
            return self._error(500, str(exc))
        except FileNotFoundError as exc:
            return self._error(500, f"file not found: {exc.filename}")
        self._error(404, "not found")

    def do_PUT(self):
        if not self._origin_ok():
            return self._error(403, "forbidden host/origin")
        path = urlsplit(self.path).path
        m = re.fullmatch(r"/api/cases/([A-Za-z0-9_-]+)", path)
        if not m:
            return self._error(404, "not found")
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self._error(415, "Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._error(400, "bad Content-Length")
        if length <= 0 or length > MAX_BODY:
            return self._error(400, "missing or too large body")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(400, "body is not valid JSON")
        try:
            case = self.store.update(m.group(1), payload)
        except ValidationError as exc:
            return self._error(400, str(exc))
        except KeyError:
            return self._error(404, f"no case with id {m.group(1)}")
        self._json(200, case)

    def do_POST(self):
        self._error(405, "method not allowed")

    do_DELETE = do_POST


def make_server(cases_path: Path, port: int = 8765, labels_path: Path = DEFAULT_LABELS) -> ThreadingHTTPServer:
    store = CaseStore(cases_path, labels_path)
    handler = type("BoundHandler", (Handler,), {"store": store})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Beldesk test set review page")
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    cases = args.cases if args.cases.is_absolute() else (Path.cwd() / args.cases)
    if not cases.exists():
        raise SystemExit(f"cases file not found: {cases}")
    httpd = make_server(cases.resolve(), args.port)
    print(f"Review page: http://127.0.0.1:{httpd.server_address[1]}/  (cases: {cases})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
