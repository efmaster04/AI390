"""Provenance checks for the frozen citizen-v2 corpus and test set.

Two kinds of hash are kept apart:

* Byte hashes (``corpus_hash`` over cleaned document files, SHA-256 of the
  test-set file) identify the exact files a run read. They change whenever any
  byte changes, including review metadata.
* Measured-content hashes ignore review metadata (``review_status`` on
  documents; ``review_status`` and ``reviewer`` on test cases). They cover
  everything that can change a measurement: IDs, metadata used for access and
  retrieval, passage text, question text, answerability and gold evidence.

Commit 576ef4b approved every document and case after the evaluation run. The
check below proves, without git history, that the approval changed nothing
else: putting the recorded evaluation-time review values back into the current
files must reproduce the byte hashes the runs recorded.
"""
import json
from pathlib import Path

from src.rag.corpus import DEFAULT_CORPUS, ROOT, clean, corpus_hash, digest, load_corpus

MANIFEST = ROOT/"eval/testsets/week3_citizen_v2_manifest.json"
CASES = ROOT/"eval/testsets/week3_retrieval.jsonl"
DOCUMENT_REVIEW_FIELDS = ("review_status",)
CASE_REVIEW_FIELDS = ("review_status", "reviewer")


def document_content(document):
    """Everything in a loaded document except review metadata and file identity."""
    excluded = {*DOCUMENT_REVIEW_FIELDS, "sha256", "path", "passages"}
    meta = {k: v for k, v in document.__dict__.items() if k not in excluded}
    meta["passages"] = [[p.passage_id, p.heading, p.text] for p in document.passages]
    return meta


def corpus_content_hash(documents):
    return digest(json.dumps([document_content(d) for d in documents], ensure_ascii=False,
                             sort_keys=True, default=list))


def read_cases(path=CASES):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]


def cases_content_hash(cases):
    content = [{k: v for k, v in c.items() if k not in CASE_REVIEW_FIELDS} for c in cases]
    return digest(json.dumps(content, ensure_ascii=False, sort_keys=True))


def corpus_with_review_values(corpus_dir, values, out_dir):
    """Copy the corpus into out_dir with each document's review fields set to values.

    Only the JSON value of each named field changes; every other byte is kept.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for file in sorted(Path(corpus_dir).glob("*.md")):
        text = file.read_text(encoding="utf-8-sig")
        meta = json.loads(clean(text).split("---\n", 2)[1])
        for field, value in values.items():
            old = f'"{field}":{json.dumps(meta[field], ensure_ascii=False)}'
            if text.count(old) != 1:
                raise ValueError(f"{file.name}: expected exactly one compact {field} entry in the metadata")
            text = text.replace(old, f'"{field}":{json.dumps(value, ensure_ascii=False)}')
        (out_dir/file.name).write_text(text, encoding="utf-8")
    return out_dir


def cases_bytes_with_review_values(cases, values):
    """Serialise cases exactly as the test-set file is written, with review fields replaced."""
    rows = []
    for case in cases:
        missing = [k for k in values if k not in case]
        if missing:
            raise ValueError(f"{case.get('id')}: review field missing: {missing}")
        rows.append({k: (values[k] if k in values else v) for k, v in case.items()})
    return "".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows).encode("utf-8")


def verify(manifest=None, *, corpus_dir=DEFAULT_CORPUS, cases_path=CASES, work_dir=None):
    """Return every provenance check; ``ok`` is True only if all of them hold."""
    import tempfile
    manifest = manifest or json.loads(MANIFEST.read_text(encoding="utf-8"))
    evaluated, current, content = manifest["evaluated_files"], manifest["current_files"], manifest["measured_content"]
    documents, cases = load_corpus(corpus_dir), read_cases(cases_path)
    reverted = current["evaluation_time_review_values"]
    with tempfile.TemporaryDirectory(dir=work_dir) as tmp:
        old_docs = load_corpus(corpus_with_review_values(corpus_dir, reverted["documents"], tmp))
    old_case_bytes = cases_bytes_with_review_values(cases, reverted["cases"])
    old_cases = [json.loads(s) for s in old_case_bytes.decode("utf-8").splitlines()]
    checks = {
        "current_corpus_bytes_match_manifest": corpus_hash(documents) == current["corpus_sha256"],
        "current_cases_bytes_match_manifest": digest(Path(cases_path).read_bytes()) == current["cases_sha256"],
        "current_measured_content_matches_frozen": (corpus_content_hash(documents) == content["corpus_content_sha256"]
                                                    and cases_content_hash(cases) == content["cases_content_sha256"]),
        "evaluated_measured_content_matches_frozen": (corpus_content_hash(old_docs) == content["corpus_content_sha256"]
                                                      and cases_content_hash(old_cases) == content["cases_content_sha256"]),
        "restoring_review_fields_reproduces_evaluated_corpus": corpus_hash(old_docs) == evaluated["corpus_sha256"],
        "restoring_review_fields_reproduces_evaluated_cases": digest(old_case_bytes) == evaluated["cases_sha256"],
        "restoring_review_fields_reproduces_each_evaluated_document": {d.doc_id: d.sha256 for d in old_docs} == evaluated["corpus_content_hashes"],
    }
    return {"ok": all(checks.values()), "checks": checks,
            "current_corpus_sha256": corpus_hash(documents),
            "current_cases_sha256": digest(Path(cases_path).read_bytes()),
            "corpus_content_sha256": corpus_content_hash(documents),
            "cases_content_sha256": cases_content_hash(cases)}


def require(manifest=None, **kwargs):
    result = verify(manifest, **kwargs)
    if not result["ok"]:
        failed = [k for k, v in result["checks"].items() if not v]
        raise ValueError(f"citizen-v2 provenance check failed: {failed}")
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
