"""Versioned synthetic corpus with strict metadata and stable source passages."""
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "data/corpus/documents"


def digest(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def clean(text):
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")).lstrip("\ufeff")
    return "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"


@dataclass(frozen=True)
class Passage:
    passage_id: str
    heading: str
    text: str


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    title_en: str
    language: str
    version: str
    updated_at: str
    source: str
    access: tuple
    synthetic: bool
    review_status: str
    keywords: tuple
    passages: tuple
    sha256: str
    path: str


def load_corpus(path=DEFAULT_CORPUS):
    documents, ids = [], set()
    for file in sorted(Path(path).glob("*.md")):
        raw = file.read_text(encoding="utf-8-sig")
        parts = clean(raw).split("---\n", 2)
        if len(parts) != 3 or parts[0]:
            raise ValueError(f"{file.name}: expected JSON metadata between --- delimiters")
        meta, body = json.loads(parts[1]), parts[2]
        required = {"doc_id", "title", "title_en", "language", "version", "updated_at", "source",
                    "access", "synthetic", "review_status", "keywords"}
        if set(meta) != required:
            raise ValueError(f"{file.name}: metadata keys differ: {set(meta) ^ required}")
        if not re.fullmatch(r"YV-D\d{3}", meta["doc_id"]) or meta["doc_id"] in ids:
            raise ValueError(f"{file.name}: invalid or duplicate document ID")
        if not all(isinstance(meta[k], str) and meta[k].strip() for k in
                   ("title", "title_en", "language", "version", "updated_at", "source")):
            raise ValueError(f"{file.name}: missing metadata value")
        date.fromisoformat(meta["updated_at"])
        if meta["language"] not in {"tr", "en"} or meta["synthetic"] is not True:
            raise ValueError(f"{file.name}: only declared synthetic TR/EN documents are allowed")
        if not isinstance(meta["access"], list) or not meta["access"] or not set(meta["access"]) <= {"public", "staff"}:
            raise ValueError(f"{file.name}: invalid access roles")
        if meta["review_status"] not in {"draft", "approved"}:
            raise ValueError(f"{file.name}: invalid review status")
        if not isinstance(meta["keywords"], list) or not all(isinstance(k, str) for k in meta["keywords"]):
            raise ValueError(f"{file.name}: invalid keywords")
        matches = list(re.finditer(r"^## (.+?) \{#([a-z0-9-]+)\}\s*$", body, re.M))
        passages, sections = [], set()
        for i, match in enumerate(matches):
            section = match[2]
            text = clean(body[match.end():matches[i+1].start() if i+1 < len(matches) else len(body)]).strip()
            if section in sections or not text:
                raise ValueError(f"{file.name}: duplicate or empty section")
            sections.add(section)
            passages.append(Passage(f"{meta['doc_id']}#{section}", match[1], text))
        if not passages:
            raise ValueError(f"{file.name}: no source passages")
        ids.add(meta["doc_id"])
        documents.append(Document(**{**meta, "access": tuple(meta["access"]), "keywords": tuple(meta["keywords"])},
                                  passages=tuple(passages), sha256=digest(clean(raw)), path=file.name))
    if not documents:
        raise ValueError("Corpus is empty")
    return documents


def corpus_hash(documents):
    return digest(json.dumps([(d.doc_id, d.sha256) for d in documents], ensure_ascii=False))


def permitted(access, role):
    if role not in {"public", "staff"}:
        raise ValueError("role must be public or staff; application must authenticate staff")
    return "public" in access or role in access


def manifest(documents):
    return [{k: v for k, v in asdict(d).items() if k != "passages"} |
            {"passage_count": len(d.passages), "words": sum(len(p.text.split()) for p in d.passages)}
            for d in documents]
