import http.client
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.review.server import make_server  # noqa: E402

REVIEW0 = {"status": "pending", "reviewer": None, "note": None, "updated_at": None}

def issue(**kw):
    base = {"category": "street_lighting", "urgency": "P3", "urgency_status": "classified",
            "location": None, "scope": "unknown", "onset_text": None, "sensitive_use": None,
            "referral_needed": "unknown"}
    base.update(kw)
    return base


def expected(intent, secondary=(), issues=(), ticket_id=None, missing=()):
    return {"intent": intent, "secondary_intents": list(secondary), "issues": list(issues),
            "ticket_id": ticket_id, "missing_fields": list(missing)}


FIXTURE = [
    {
        "id": "W2-001", "source_id": "W1-01", "lang": "tr", "type": "normal", "ingredients": [1, 8],
        "text": "nikah başvurusu için hangi belgeler lazım\nrandevu nasıl alınıyo",
        "expected": expected("faq"),
        "expected_behavior": "Answer from the marriage document and cite it.",
        "answerable": True, "review": dict(REVIEW0),
    },
    {
        "id": "W2-002", "source_id": None, "lang": "mixed", "type": "edge", "ingredients": [3],
        "text": "Sokak lambası yanmıyor, Atatürk Cd. — street light is out since Monday",
        "expected": expected("field_complaint", issues=[issue(
            location={"neighborhood": None, "street": "Atatürk Cd.", "detail": None},
            onset_text="since Monday", scope="single_point")]),
        "expected_behavior": "Open a street lighting ticket with P3 urgency.",
        "answerable": True, "review": dict(REVIEW0),
    },
    {
        "id": "W2-003", "source_id": None, "lang": "en", "type": "unanswerable", "ingredients": [5],
        "text": "What will the mayor have for lunch tomorrow?",
        "expected": expected("out_of_scope"),
        "expected_behavior": "Politely say this is out of scope.",
        "answerable": False, "review": dict(REVIEW0),
    },
    {
        "id": "W2-004", "source_id": None, "lang": "tr", "type": "normal", "ingredients": [2],
        "text": "Evde gaz kokusu var, ne yapmalıyım?",
        "expected": expected("emergency"),
        "expected_behavior": "Direct the citizen to 112 first.",
        "answerable": True, "review": dict(REVIEW0),
    },
]
IMMUTABLE = ("id", "text", "source_id", "lang", "ingredients")


@pytest.fixture
def server(tmp_path):
    cases = tmp_path / "cases.jsonl"
    cases.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in FIXTURE), encoding="utf-8")
    httpd = make_server(cases, port=0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield httpd.server_address[1], cases
    finally:
        httpd.shutdown()
        httpd.server_close()


def request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    hdrs = {"Host": f"127.0.0.1:{port}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})
    conn.request(method, path, body=data, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    ctype = resp.getheader("Content-Type", "")
    return resp.status, (json.loads(raw) if "json" in ctype else raw.decode("utf-8"))


def read_lines(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def payload_for(case, **review):
    return {
        "expected": json.loads(json.dumps(case["expected"])),
        "expected_behavior": case["expected_behavior"],
        "answerable": case["answerable"],
        "type": case["type"],
        "review": {"status": "approved", "reviewer": "Efe", "note": None, **review},
    }


def test_get_index_labels_and_cases(server):
    port, _ = server
    status, html = request(port, "GET", "/")
    assert status == 200 and "Test seti incelemesi" in html
    status, labels = request(port, "GET", "/api/labels")
    assert status == 200 and "field_complaint" in labels["intents"]
    status, cases = request(port, "GET", "/api/cases")
    assert status == 200
    assert [c["id"] for c in cases] == ["W2-001", "W2-002", "W2-003", "W2-004"]
    assert cases[0]["text"] == FIXTURE[0]["text"]


def test_get_rereads_file(server):
    port, path = server
    rows = read_lines(path)
    rows[2]["expected_behavior"] = "edited in VS Code"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    _, cases = request(port, "GET", "/api/cases")
    assert cases[2]["expected_behavior"] == "edited in VS Code"


def test_valid_multi_issue_put_persists_and_keeps_immutable_fields(server):
    port, path = server
    body = payload_for(FIXTURE[1], status="changed", note="iki ayrı arıza")
    body["expected"]["secondary_intents"] = ["status_inquiry"]
    body["expected"]["issues"][0]["urgency"] = "P2"
    body["expected"]["issues"].append(issue(
        category="roads_sidewalks", urgency=None, urgency_status="needs_clarification",
        location={"neighborhood": "Kızılay", "street": None, "detail": "okul önü"},
        scope="partial", onset_text="2 haftadır", sensitive_use="school route", referral_needed="no"))
    body["expected"]["missing_fields"] = ["onset", "location"]
    body["expected"]["ticket_id"] = "YV-2026-000123"
    status, saved = request(port, "PUT", "/api/cases/W2-002", body)
    assert status == 200, saved
    assert saved["review"]["status"] == "changed"
    assert saved["review"]["reviewer"] == "Efe"
    assert saved["review"]["updated_at"].endswith("Z")

    rows = read_lines(path)
    assert [r["id"] for r in rows] == ["W2-001", "W2-002", "W2-003", "W2-004"]
    ex = rows[1]["expected"]
    assert len(ex["issues"]) == 2
    assert ex["issues"][0]["urgency"] == "P2"
    assert ex["issues"][1]["urgency"] is None
    assert ex["issues"][1]["location"]["detail"] == "okul önü"
    assert ex["missing_fields"] == ["location", "onset"]  # canonical vocab order
    assert ex["secondary_intents"] == ["status_inquiry"]
    assert rows[1]["review"]["note"] == "iki ayrı arıza"
    for key in IMMUTABLE:
        assert rows[1][key] == FIXTURE[1][key]
    assert rows[0] == FIXTURE[0] and rows[2] == FIXTURE[2] and rows[3] == FIXTURE[3]
    raw = path.read_text(encoding="utf-8")
    assert "Atatürk" in raw and "\\u" not in raw
    assert len(raw.splitlines()) == 4


def test_secondary_field_complaint_needs_issue(server):
    port, path = server
    body = payload_for(FIXTURE[0])
    body["expected"]["secondary_intents"] = ["field_complaint"]
    status, resp = request(port, "PUT", "/api/cases/W2-001", body)
    assert status == 400 and "issues" in resp["error"]
    body["expected"]["issues"] = [issue()]
    status, resp = request(port, "PUT", "/api/cases/W2-001", body)
    assert status == 200, resp


def test_put_cannot_change_immutable_fields(server):
    port, path = server
    for key, val in (("text", "hacked"), ("id", "W2-999"), ("lang", "en"), ("source_id", "W1-99"), ("ingredients", [1])):
        body = payload_for(FIXTURE[0])
        body[key] = val
        status, resp = request(port, "PUT", "/api/cases/W2-001", body)
        assert status == 400 and "cannot be edited" in resp["error"]
    assert read_lines(path) == FIXTURE


def test_invalid_intent_rejected(server):
    port, path = server
    body = payload_for(FIXTURE[0])
    body["expected"]["intent"] = "smalltalk"
    status, resp = request(port, "PUT", "/api/cases/W2-001", body)
    assert status == 400
    assert "expected.intent" in resp["error"]
    assert read_lines(path) == FIXTURE


def test_urgency_null_with_classified_status_rejected(server):
    port, path = server
    body = payload_for(FIXTURE[1])
    body["expected"]["issues"][0]["urgency"] = None
    status, resp = request(port, "PUT", "/api/cases/W2-002", body)
    assert status == 400 and "urgency" in resp["error"]
    body["expected"]["issues"][0]["urgency"] = "P2"
    body["expected"]["issues"][0]["urgency_status"] = "needs_clarification"
    status, resp = request(port, "PUT", "/api/cases/W2-002", body)
    assert status == 400 and "urgency" in resp["error"]
    assert read_lines(path) == FIXTURE


def test_issues_for_faq_only_rejected(server):
    port, path = server
    body = payload_for(FIXTURE[0])
    body["expected"]["issues"] = [issue()]
    status, resp = request(port, "PUT", "/api/cases/W2-001", body)
    assert status == 400 and "field_complaint" in resp["error"]
    assert read_lines(path) == FIXTURE


def test_emergency_only_with_issues_rejected(server):
    port, path = server
    body = payload_for(FIXTURE[3])
    body["expected"]["issues"] = [issue(category="other")]
    status, resp = request(port, "PUT", "/api/cases/W2-004", body)
    assert status == 400 and "emergency" in resp["error"]
    assert read_lines(path) == FIXTURE


def test_field_complaint_without_issues_rejected(server):
    port, _ = server
    body = payload_for(FIXTURE[1])
    body["expected"]["issues"] = []
    status, resp = request(port, "PUT", "/api/cases/W2-002", body)
    assert status == 400 and "issues" in resp["error"]


def test_other_invalid_values(server):
    port, _ = server
    for mutate in (
        lambda b: b["review"].update(status="done"),
        lambda b: b.update(type="weird"),
        lambda b: b.update(answerable="yes"),
        lambda b: b["review"].update(reviewer=None),
        lambda b: b.update(answerable=True),  # unanswerable => answerable false
        lambda b: b["expected"].update(ticket_id="YV-26-1"),
        lambda b: b["expected"].update(missing_fields=["phone"]),
        lambda b: b["expected"].update(category=None),  # v1 key no longer allowed
        lambda b: b["expected"].update(secondary_intents=["field_complaint"],
                                       issues=[issue(scope="everywhere")]),
        lambda b: b["expected"].update(secondary_intents=["field_complaint"],
                                       issues=[issue(location={"street": "X"})]),
        lambda b: b["expected"].update(secondary_intents=["field_complaint"],
                                       issues=[dict(issue(), extra=1)]),
        lambda b: b["expected"].update(secondary_intents=["field_complaint"],
                                       issues=[issue(referral_needed="maybe")]),
    ):
        body = payload_for(FIXTURE[2])
        mutate(body)
        status, resp = request(port, "PUT", "/api/cases/W2-003", body)
        assert status == 400, body
    status, _ = request(port, "PUT", "/api/cases/W2-999", payload_for(FIXTURE[2]))
    assert status == 404


def test_foreign_host_or_origin_rejected(server):
    port, path = server
    status, _ = request(port, "GET", "/api/cases", headers={"Host": "evil.example"})
    assert status == 403
    status, _ = request(port, "PUT", "/api/cases/W2-001", payload_for(FIXTURE[0]),
                        headers={"Origin": "http://evil.example"})
    assert status == 403
    assert read_lines(path) == FIXTURE
    status, _ = request(port, "GET", "/api/cases", headers={"Origin": f"http://localhost:{port}"})
    assert status == 200
