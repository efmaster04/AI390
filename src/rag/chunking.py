"""Structure-aware, word-bounded windows; a chunk never crosses a source section.

Gold labels point to passages and exact evidence quotes, never chunk IDs. This
keeps evaluation labels valid if window size changes in a later experiment.
"""
from dataclasses import asdict, dataclass
import re

from .corpus import digest


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    passage_id: str
    title: str
    title_en: str
    heading: str
    text: str
    search_text: str
    start: int
    end: int
    source: str
    version: str
    access: tuple


def chunk_documents(documents, max_words=140, overlap_words=20):
    if type(max_words) is not int or type(overlap_words) is not int or not 0 <= overlap_words < max_words:
        raise ValueError("Need integer 0 <= overlap_words < max_words")
    chunks = []
    for doc in documents:
        for passage in doc.passages:
            words = list(re.finditer(r"\S+", passage.text))
            for offset in range(0, len(words), max_words-overlap_words):
                chosen = words[offset:offset+max_words]
                start, end = chosen[0].start(), chosen[-1].end()
                text = passage.text[start:end]
                cid = f"{passage.passage_id}:{start}-{end}:{digest(text)[:10]}"
                search = f"{doc.title}\n{doc.title_en}\n{passage.heading}\n{' '.join(doc.keywords)}\n{text}"
                chunks.append(Chunk(cid, doc.doc_id, passage.passage_id, doc.title, doc.title_en,
                                    passage.heading, text, search, start, end, doc.source, doc.version, doc.access))
                if offset+max_words >= len(words):
                    break
    return chunks


def chunk_report(chunks):
    sizes = [len(c.text.split()) for c in chunks]
    return {"count": len(chunks), "documents": len({c.doc_id for c in chunks}),
            "passages": len({c.passage_id for c in chunks}), "max_words_observed": max(sizes, default=0),
            "mean_words": sum(sizes)/len(sizes) if sizes else 0,
            "chunks": [asdict(c) for c in chunks]}
