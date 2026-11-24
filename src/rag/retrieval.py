"""BM25 + multilingual dense retrieval + RRF + cross-encoder reranking.

This module returns evidence, not an answer or a ticket. Efe's answer layer can
consume the returned source objects. Authorization belongs to the application:
never expose the local CLI's staff-role switch as a citizen-controlled input.
"""
from dataclasses import asdict
import json
from pathlib import Path
import time

from .chunking import chunk_documents
from .corpus import ROOT, DEFAULT_CORPUS, corpus_hash, digest, load_corpus, permitted
from .lexical import BM25, reciprocal_rank_fusion


class Retriever:
    def __init__(self, *, corpus_dir=DEFAULT_CORPUS, config_path=None, cache_dir=None, models=None):
        import numpy as np
        self.np = np
        self.config = json.loads(Path(config_path or ROOT/"config/retrieval.json").read_text(encoding="utf-8"))
        self.documents = load_corpus(corpus_dir)
        self.chunks = chunk_documents(self.documents, self.config["max_words"], self.config["overlap_words"])
        self.cache_dir = Path(cache_dir or ROOT/".cache/retrieval")
        self.corpus_sha256 = corpus_hash(self.documents)
        identity = {"corpus": self.corpus_sha256, "config": self.config,
                    "chunks": [(c.chunk_id, digest(c.search_text)) for c in self.chunks]}
        self.index_sha256 = digest(json.dumps(identity, sort_keys=True, ensure_ascii=False))
        self.cache_path = self.cache_dir/self.index_sha256
        self.cache_path.mkdir(parents=True, exist_ok=True)
        if models is None:
            from .models import LocalModels
            models = LocalModels(self.config)
        self.models = models
        vector_path = self.cache_path/"passages.npy"
        if vector_path.exists():
            self.vectors = np.load(vector_path, allow_pickle=False)
        else:
            self.vectors = self.models.encode([c.search_text for c in self.chunks], "passage")
            np.save(vector_path, self.vectors, allow_pickle=False)
        if self.vectors.ndim != 2 or self.vectors.shape[0] != len(self.chunks) or not np.isfinite(self.vectors).all():
            raise ValueError("Invalid embedding cache: rebuild the local index")

    def search(self, query, *, role="public", k=5, mode="hybrid", rerank=True, cache_scores=True):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be nonempty text")
        if type(k) is not int or not 1 <= k <= self.config["candidate_k"]:
            raise ValueError("k must be between 1 and candidate_k")
        if mode not in {"hybrid", "dense", "bm25"}:
            raise ValueError("mode must be hybrid, dense or bm25")
        start = time.perf_counter()
        # Filter before both ranking stages, not after the public top-k is formed.
        eligible = [i for i, c in enumerate(self.chunks) if permitted(c.access, role)]
        if not eligible:
            return {"query": query, "results": [], "timings_s": {"total": time.perf_counter()-start}}
        lookup = {self.chunks[i].chunk_id: i for i in eligible}
        candidates = max(k, self.config["candidate_k"])
        ranks, lexical_scores, dense_scores = [], {}, {}
        if mode in {"hybrid", "bm25"}:
            scores = BM25([self.chunks[i].search_text for i in eligible]).scores(query)
            lexical_scores = {self.chunks[i].chunk_id: score for i, score in zip(eligible, scores)}
            ranks.append(sorted((cid for cid, score in lexical_scores.items() if score > 0),
                                key=lambda cid: (-lexical_scores[cid], cid))[:candidates])
        if mode in {"hybrid", "dense"}:
            q_path = self.cache_path/("query-"+digest(query)+".npy")
            if cache_scores and q_path.exists():
                q = self.np.load(q_path, allow_pickle=False)
            else:
                q = self.models.encode([query], "query")[0]
                if cache_scores:
                    self.np.save(q_path, q, allow_pickle=False)
            if q.ndim != 1 or q.shape[0] != self.vectors.shape[1] or not self.np.isfinite(q).all():
                raise ValueError("Invalid query embedding cache")
            scores = self.vectors[eligible] @ q
            dense_scores = {self.chunks[i].chunk_id: float(score) for i, score in zip(eligible, scores)}
            ranks.append(sorted(dense_scores, key=lambda cid: (-dense_scores[cid], cid))[:candidates])
        if mode == "hybrid":
            order, fusion_scores = reciprocal_rank_fusion(ranks, self.config["rrf_constant"])
        else:
            order, fusion_scores = ranks[0], {}
        order = order[:candidates]
        candidate_passages = [self.chunks[lookup[cid]].passage_id for cid in order]
        retrieval_end = time.perf_counter()
        rerank_scores = {}
        if rerank and order:
            # Cache is keyed by complete model/index identity, query, and candidate order.
            key = digest(json.dumps([query, order], ensure_ascii=False))
            score_path = self.cache_path/("rerank-"+key+".json")
            if cache_scores and score_path.exists():
                values = json.loads(score_path.read_text(encoding="utf-8"))
            else:
                values = [float(x) for x in self.models.rerank(query, [self.chunks[lookup[c]].search_text for c in order])]
                if cache_scores:
                    score_path.write_text(json.dumps(values), encoding="utf-8")
            if len(values) != len(order) or not all(self.np.isfinite(v) for v in values):
                raise ValueError("Invalid reranker score cache")
            rerank_scores = dict(zip(order, values))
            order.sort(key=lambda cid: (-rerank_scores[cid], cid))
        results = []
        for rank, cid in enumerate(order[:k], 1):
            c = self.chunks[lookup[cid]]
            results.append({"rank": rank, **asdict(c), "bm25_score": lexical_scores.get(cid),
                            "dense_score": dense_scores.get(cid), "rrf_score": fusion_scores.get(cid),
                            "reranker_score": rerank_scores.get(cid)})
        return {"query": query, "role": role, "mode": mode, "rerank": rerank,
                "corpus_sha256": self.corpus_sha256, "index_sha256": self.index_sha256,
                "candidate_passage_ids": candidate_passages,
                "results": results,
                "timings_s": {"retrieval": retrieval_end-start,
                              "reranking": time.perf_counter()-retrieval_end,
                              "total": time.perf_counter()-start}}


def source_context(search_result):
    """Evidence contract for the generation owner; not a claim of answerability.

    Citation numbers are local to one answer. A real, relevant source must support
    each claim; merely retrieving a chunk (or attaching [1]) does not prove this.
    """
    return [{"citation": i, "doc_id": c["doc_id"], "passage_id": c["passage_id"],
             "chunk_id": c["chunk_id"], "title": c["title"], "heading": c["heading"],
             "source": c["source"], "version": c["version"], "text": c["text"],
             "synthetic": True, "trust": "evidence_only_not_instructions"}
            for i, c in enumerate(search_result["results"], 1)]
