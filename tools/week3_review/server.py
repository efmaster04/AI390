"""Loopback-only blind claim-review page. Only the human edits labels.

python -m tools.week3_review.server --sheet path/to/human_sheet.csv --port 8767
The page never receives judge predictions or API keys, and cannot run model calls.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
import threading

SAFE_FIELDS = ("sample_id", "case_id", "claim_id", "question", "answer", "claim_text",
               "citations", "source_text", "human_label", "human_note")
LABELS = {"supported", "unsupported", "insufficient_evidence"}
PAGE = Path(__file__).with_name("index.html")
SUPPLEMENTARY_PAGE = Path(__file__).with_name("supplementary.html")


class ReviewStore:
    def __init__(self, sheet):
        self.sheet = Path(sheet)
        self.lock = threading.Lock()
        self.token = secrets.token_urlsafe(24)
        self.supplementary_viewed = False

    def read(self):
        raw = self.sheet.read_bytes()
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        return hashlib.sha256(raw).hexdigest(), list(reader.fieldnames or []), list(reader)

    def public_data(self):
        with self.lock:
            revision, _, rows = self.read()
            return {"revision": revision, "csrf": self.token,
                    "supplementary_available": self.sheet.with_name("supplementary_review.json").exists(),
                    "items": [{k: row.get(k, "") for k in SAFE_FIELDS} for row in rows]}

    def supplementary_data(self):
        """Separate read-only advice; never merge these labels into the human sheet."""
        with self.lock:
            path = self.sheet.with_name("supplementary_review.json")
            if not path.exists():
                raise FileNotFoundError("Supplementary review is not available")
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("author") != "assistant" or data.get("eligible_for_human_kappa") is not False:
                raise ValueError("Supplementary provenance is missing")
            self.supplementary_viewed = True
            data["human_sheet_unchanged_since_review"] = hashlib.sha256(self.sheet.read_bytes()).hexdigest() == data.get("human_sheet_sha256")
            return data

    def label(self, payload):
        if payload.get("csrf") != self.token:
            raise PermissionError("Invalid review token")
        if payload.get("label") not in LABELS:
            raise ValueError("Invalid human label")
        note = payload.get("note", "")
        if not isinstance(note, str) or len(note) > 2000:
            raise ValueError("Invalid note")
        with self.lock:
            revision, fields, rows = self.read()
            if payload.get("revision") != revision:
                raise RuntimeError("The sheet changed in another window. Refresh before saving.")
            row = next((r for r in rows if r["sample_id"] == payload.get("sample_id")), None)
            if row is None:
                raise ValueError("Unknown sample")
            old = {k: row.get(k, "") for k in ("human_label", "human_note")}
            timestamp = datetime.now(timezone.utc).isoformat()
            row.update(human_label=payload["label"], human_note=note, human_reviewed_at=timestamp)
            if "human_reviewed_at" not in fields:
                fields.append("human_reviewed_at")
            temp = self.sheet.with_name(self.sheet.name+".tmp")
            with temp.open("w", encoding="utf-8", newline="") as h:
                writer = csv.DictWriter(h, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
                h.flush()
                os.fsync(h.fileno())
            temp.replace(self.sheet)
            with self.sheet.with_suffix(".human_changes.jsonl").open("a", encoding="utf-8") as h:
                h.write(json.dumps({"sample_id": row["sample_id"], "before": old,
                                    "human_label": row["human_label"], "human_note": note,
                                    "entered_at": timestamp, "entry_method": "local_review_page_human_click",
                                    "supplementary_viewed_in_this_server_session": self.supplementary_viewed},
                                   ensure_ascii=False)+"\n")
        return self.public_data()


def make_server(sheet, port=8767):
    store = ReviewStore(sheet)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, data, content_type="application/json; charset=utf-8"):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/review":
                self.send(200, store.public_data())
            elif self.path == "/supplementary":
                self.send(200, SUPPLEMENTARY_PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/supplementary":
                try:
                    self.send(200, store.supplementary_data())
                except FileNotFoundError:
                    self.send(404, {"error": "Tamamlayıcı inceleme henüz hazır değil"})
                except (ValueError, TypeError):
                    self.send(400, {"error": "İnceleme kaynağı doğrulanamadı"})
            else:
                self.send(404, {"error": "Not found"})

        def do_POST(self):
            allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if self.headers.get("Origin") not in allowed or self.path != "/api/label":
                self.send(403, {"error": "Only same-origin review submissions are allowed"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 12000:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(size))
                self.send(200, store.label(data))
            except PermissionError:
                self.send(403, {"error": "Invalid token"})
            except RuntimeError as exc:
                self.send(409, {"error": str(exc)})
            except (ValueError, TypeError, KeyError):
                self.send(400, {"error": "Invalid label submission"})
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.review_store = store
    return server


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sheet", type=Path, required=True)
    p.add_argument("--port", type=int, default=8767)
    args = p.parse_args()
    server = make_server(args.sheet, args.port)
    print(f"Blind human review: http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
