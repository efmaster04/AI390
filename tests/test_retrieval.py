"""No model downloads or external API calls. Synthetic vectors test mechanics only."""
from dataclasses import replace
import json
import shutil

import pytest

from src.rag.chunking import chunk_documents
from src.rag.corpus import DEFAULT_CORPUS, clean, load_corpus, permitted
from src.rag.lexical import BM25, reciprocal_rank_fusion, tokenize


def test_corpus_has_unique_stable_sources_and_declares_draft():
    docs = load_corpus()
    assert len({d.doc_id for d in docs}) == len(docs)
    assert all(d.synthetic and d.source.startswith("beldesk://synthetic/") for d in docs)
    assert all(d.review_status in {"draft", "approved"} for d in docs)
    assert all(p.text.strip() for d in docs for p in d.passages)


def test_metadata_access_is_required(tmp_path):
    original = next(DEFAULT_CORPUS.glob("*.md")).read_text()
    header, metadata, body = original.split("---\n", 2)
    meta = json.loads(metadata)
    del meta["access"]
    (tmp_path/"bad.md").write_text("---\n"+json.dumps(meta)+"\n---\n"+body)
    with pytest.raises(ValueError, match="metadata"):
        load_corpus(tmp_path)


def test_duplicate_doc_ids_are_rejected(tmp_path):
    source = next(DEFAULT_CORPUS.glob("*.md"))
    shutil.copy(source, tmp_path/"a.md")
    shutil.copy(source, tmp_path/"b.md")
    with pytest.raises(ValueError, match="duplicate"):
        load_corpus(tmp_path)


def test_clean_preserves_turkish_and_normalizes_lines():
    assert clean("\ufeffİstanbul  \r\nçöp\r\n") == "İstanbul\nçöp\n"
    assert tokenize("İMAR IŞIK Çöp") == ["imar", "ışık", "çöp"]


def test_chunks_reconstruct_source_and_never_mix_sections():
    docs = load_corpus()
    sources = {p.passage_id: p.text for d in docs for p in d.passages}
    chunks = chunk_documents(docs, max_words=12, overlap_words=3)
    assert len(chunks) > sum(len(d.passages) for d in docs)
    for chunk in chunks:
        assert chunk.text == sources[chunk.passage_id][chunk.start:chunk.end]
        assert len(chunk.text.split()) <= 12
    for pid, text in sources.items():
        covered = set()
        for c in chunks:
            if c.passage_id == pid:
                covered.update(range(c.start, c.end))
        assert all(i in covered for i, char in enumerate(text) if not char.isspace())


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1), (True, 0)])
def test_bad_chunk_parameters(size, overlap):
    with pytest.raises(ValueError):
        chunk_documents(load_corpus(), size, overlap)


def test_acl_and_invalid_role():
    assert permitted(("public",), "staff")
    assert not permitted(("staff",), "public")
    with pytest.raises(ValueError):
        permitted(("staff",), "administrator")


def test_bm25_and_rrf_have_deterministic_expected_ranking():
    scores = BM25(["su aboneliği belgeler kira", "park bankı", "su"]).scores("kira")
    assert scores[0] > scores[1] == scores[2] == 0
    ranking, scores = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    assert ranking[0] == "b"
    assert scores["b"] == pytest.approx(1/62+1/61)
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a", "a"]])


class FakeModels:
    """Only for mechanics checks; never used by the CLI or measured results."""
    def __init__(self):
        self.encode_calls = 0
        self.rerank_calls = 0

    def encode(self, texts, kind):
        import numpy as np
        self.encode_calls += 1
        return np.array([[1., 0.] for _ in texts], dtype="float32")

    def rerank(self, query, texts):
        self.rerank_calls += 1
        return list(range(len(texts)))


def test_search_filters_staff_before_scoring_and_caches(tmp_path):
    pytest.importorskip("numpy")
    from src.rag.retrieval import Retriever, source_context
    models = FakeModels()
    r = Retriever(cache_dir=tmp_path, models=models)
    result = r.search("STAFF-ONLY-QUEUE-DEMO", role="public", k=10)
    assert all("staff" not in c["access"] for c in result["results"])
    assert all(c["doc_id"] != "YV-D031" for c in result["results"])
    counts = models.encode_calls, models.rerank_calls
    assert r.search("STAFF-ONLY-QUEUE-DEMO", role="public", k=10)["results"] == result["results"]
    assert (models.encode_calls, models.rerank_calls) == counts
    staff = r.search("STAFF-ONLY-QUEUE-DEMO", role="staff", k=20, rerank=False)
    assert any(c["doc_id"] == "YV-D031" for c in staff["results"])
    ctx = source_context(result)
    assert [s["citation"] for s in ctx] == list(range(1, len(ctx)+1))
    assert all(s["trust"] == "evidence_only_not_instructions" for s in ctx)


def test_index_changes_when_corpus_changes(tmp_path):
    pytest.importorskip("numpy")
    from src.rag.retrieval import Retriever
    corpus = tmp_path/"corpus"
    shutil.copytree(DEFAULT_CORPUS, corpus)
    r = Retriever(corpus_dir=corpus, cache_dir=tmp_path/"cache", models=FakeModels())
    doc = next(corpus.glob("*.md"))
    doc.write_text(doc.read_text()+"\nEk sentetik bilgi.\n")
    other = Retriever(corpus_dir=corpus, cache_dir=tmp_path/"cache", models=FakeModels())
    assert r.index_sha256 != other.index_sha256


def test_empty_query_and_unknown_role_fail(tmp_path):
    pytest.importorskip("numpy")
    from src.rag.retrieval import Retriever
    r = Retriever(cache_dir=tmp_path, models=FakeModels())
    with pytest.raises(ValueError):
        r.search("")
    with pytest.raises(ValueError):
        r.search("su", role="admin")


def test_gold_quotes_exist_and_test_set_has_30_answerable_cases():
    pytest.importorskip("numpy")
    from eval.retrieval_week3 import read_cases
    from src.rag.corpus import ROOT
    rows = read_cases(ROOT/"eval/testsets/week3_retrieval.jsonl", load_corpus())
    assert sum(r["answerable"] for r in rows) >= 30
    assert {r["lang"] for r in rows} == {"tr", "en"}
    assert all(r["role"] == "public" for r in rows)


def test_retrieval_metrics_use_exact_evidence_and_correct_denominator():
    pytest.importorskip("numpy")
    from eval.retrieval_week3 import score_retrieval, summarize
    gold = [{"passage_id": "source#section", "quote": "required fact"}]
    output = [{"rank": 1, "passage_id": "other", "text": "required fact"},
              {"rank": 3, "passage_id": "source#section", "text": "contains required fact here"}]
    score = score_retrieval(output, gold)
    assert score["hit"] == {"1": False, "3": True, "5": True, "10": True}
    assert score["reciprocal_rank"] == pytest.approx(1/3)
    assert not score_retrieval([{"rank": 1, "passage_id": "source#section", "text": "wrong part"}], gold)["hit"]["5"]
    rows = [{"answerable": True, "lang": "tr", "metrics": score, "timings_s": {"total": 1}},
            {"answerable": False, "lang": "en", "metrics": None, "timings_s": {"total": 2}}]
    result = summarize(rows)
    assert result["n_answerable"] == 1
    assert result["n_unanswerable_controls"] == 1
    assert result["hit_at_k"]["3"] == 1


def test_unauthorized_gold_evidence_cannot_be_scored(tmp_path):
    pytest.importorskip("numpy")
    from eval.retrieval_week3 import read_cases
    docs = load_corpus()
    private = next(d for d in docs if d.access == ("staff",))
    passage = private.passages[0]
    row = {"id": "bad", "split": "test", "lang": "tr", "role": "public", "text": "soru",
           "answerable": True, "gold": [{"passage_id": passage.passage_id, "quote": passage.text}],
           "review_status": "draft"}
    path = tmp_path/"cases.jsonl"
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="authorized"):
        read_cases(path, docs)


def test_model_snapshot_resolution_is_strictly_local(monkeypatch):
    hub = pytest.importorskip("huggingface_hub")
    from src.rag.models import local_snapshot
    observed = {}
    def resolve(model_id, **kwargs):
        observed.update(model_id=model_id, **kwargs)
        return "/local/pinned/snapshot"
    monkeypatch.setattr(hub, "snapshot_download", resolve)
    assert local_snapshot("example/model", "pinned-revision") == "/local/pinned/snapshot"
    assert observed == {"model_id": "example/model", "revision": "pinned-revision", "local_files_only": True}


def test_alternative_evidence_satisfies_its_facet_without_becoming_an_extra_requirement():
    from eval.retrieval_week3 import score_retrieval
    a = {"passage_id": "A", "quote": "tenant documents"}
    alt_a = {"passage_id": "A-alt", "quote": "rental documents"}
    b = {"passage_id": "B", "quote": "no ID photo for an enquiry"}
    rows = [{"rank": 1, "passage_id": "A-alt", "text": "rental documents"},
            {"rank": 4, "passage_id": "B", "text": "no ID photo for an enquiry"}]
    result = score_retrieval(rows, [a,b], gold_groups=[[a,alt_a],[b]])
    assert result["hit"]["1"] and result["all_gold_hit_at_5"]
    assert not score_retrieval(rows[:1], [a,b], gold_groups=[[a,alt_a],[b]])["all_gold_hit_at_5"]
    assert not score_retrieval([dict(rows[0], text="different fact")], [a], gold_groups=[[a,alt_a]])["hit"]["5"]


def test_internal_policy_cases_cannot_be_scored_as_citizen_retrieval(tmp_path):
    from eval.retrieval_week3 import read_cases
    row = {"id":"policy", "split":"test", "lang":"en", "role":"public", "text":"What schema should developers use?",
           "answerable":False, "gold":[], "review_status":"draft", "audience":"developer"}
    path = tmp_path/'policy.jsonl';path.write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError, match="Internal policy"):
        read_cases(path, load_corpus())


def test_active_citizen_dataset_is_frozen_for_its_actual_source_version():
    from src.rag.corpus import ROOT, corpus_hash, digest
    frozen = json.loads((ROOT/'eval/testsets/week3_citizen_v2_manifest.json').read_text())
    cases_path = ROOT/'eval/testsets/week3_retrieval.jsonl'
    cases = [json.loads(x) for x in cases_path.read_text().splitlines()]
    assert frozen['cases_sha256'] == digest(cases_path.read_bytes())
    assert frozen['corpus_sha256'] == corpus_hash(load_corpus())
    assert len(cases) == 38 and sum(c['answerable'] for c in cases) == 32
    assert sum(c['lang']=='tr' for c in cases) == sum(c['lang']=='en' for c in cases) == 19
    assert all(c['audience']=='citizen' and c['dataset_version']=='citizen-v2' for c in cases)
    for d in load_corpus():
        if 'public' in d.access:
            body = ' '.join(p.text for p in d.passages).casefold()
            assert all(token not in body for token in ('asistan','week 3','test senaryosu','prompt','schema'))
