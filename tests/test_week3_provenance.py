"""The measured citizen-v2 content is frozen; only review metadata changed after the runs."""
import json
from pathlib import Path

import pytest

from eval.week3_provenance import (CASES, MANIFEST, cases_bytes_with_review_values, cases_content_hash,
                                   corpus_content_hash, read_cases, require, verify)
from src.rag.corpus import DEFAULT_CORPUS, ROOT, load_corpus


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_restoring_evaluation_review_values_reproduces_the_evaluated_bytes():
    result = verify()
    assert result["ok"], result["checks"]


def test_runs_recorded_the_evaluated_hashes_not_the_post_approval_hashes():
    frozen = manifest()["evaluated_files"]
    retrieval = json.loads((ROOT/"eval/results/week3/retrieval/summary.json").read_text())
    assert (retrieval["corpus_sha256"], retrieval["cases_sha256"]) == (frozen["corpus_sha256"], frozen["cases_sha256"])
    for name in ("answers_citizen_v2", "answers_citizen_v2_complete"):
        identity = json.loads((ROOT/f"eval/results/week3/{name}/run_meta.json").read_text())["identity"]
        assert identity["corpus_sha256"] == frozen["corpus_sha256"]
        assert identity["hashes"]["cases"] == frozen["cases_sha256"]
    current = manifest()["current_files"]
    assert current["corpus_sha256"] != frozen["corpus_sha256"] and current["cases_sha256"] != frozen["cases_sha256"]


def test_content_hash_ignores_review_fields_but_not_measured_fields():
    cases = read_cases()
    base = cases_content_hash(cases)
    reviewed = [dict(c, review_status="draft", reviewer="Someone") for c in cases]
    assert cases_content_hash(reviewed) == base
    edited = [dict(c) for c in cases]
    edited[0]["text"] += " changed"
    assert cases_content_hash(edited) != base
    regold = [dict(c) for c in cases]
    regold[0]["gold"] = []
    assert cases_content_hash(regold) != base


def test_any_change_beyond_review_metadata_fails_the_check(tmp_path):
    corpus = tmp_path/"corpus"
    corpus.mkdir()
    for file in sorted(Path(DEFAULT_CORPUS).glob("*.md")):
        (corpus/file.name).write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
    first = sorted(corpus.glob("*.md"))[0]
    first.write_text(first.read_text(encoding="utf-8").replace("\n## ", "\n## Edited ", 1), encoding="utf-8")
    result = verify(corpus_dir=corpus)
    assert not result["ok"]
    assert not result["checks"]["current_measured_content_matches_frozen"]
    with pytest.raises(ValueError, match="provenance"):
        require(corpus_dir=corpus)
    cases_path = tmp_path/"cases.jsonl"
    rows = read_cases()
    rows[1]["answerable"] = not rows[1]["answerable"]
    cases_path.write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows), encoding="utf-8")
    assert not verify(cases_path=cases_path)["ok"]


def test_case_serialisation_round_trips_the_committed_file():
    cases = read_cases()
    values = {"review_status": cases[0]["review_status"], "reviewer": cases[0]["reviewer"]}
    assert all(c["review_status"] == values["review_status"] for c in cases)
    assert cases_bytes_with_review_values(cases, values) == CASES.read_bytes()


def test_content_hash_covers_every_document():
    docs = load_corpus()
    assert len(docs) == 31 and corpus_content_hash(docs) == manifest()["measured_content"]["corpus_content_sha256"]
