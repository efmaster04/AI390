"""Local corpus inspection and retrieval demo; no Gemini key required."""
import argparse
import json
from pathlib import Path

from .corpus import ROOT, corpus_hash, load_corpus, manifest
from .chunking import chunk_documents, chunk_report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("download", help="Explicitly download the two pinned public model snapshots")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--out", type=Path)
    inventory = sub.add_parser("manifest", help="Refresh metadata inventory after document review or edits")
    inventory.add_argument("--out", type=Path, default=ROOT/"data/corpus/manifest.json")
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--k", type=int, default=5)
    search.add_argument("--role", choices=["public", "staff"], default="public",
                        help="Local demo only; real staff access must be authenticated by Efe's app")
    search.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    search.add_argument("--no-rerank", action="store_true")
    args = p.parse_args(argv)
    config = json.loads((ROOT/"config/retrieval.json").read_text())
    if args.command == "download":
        from .models import download_models
        download_models(config)
        print("Pinned local models downloaded; no inference API used.")
        return
    if args.command == "manifest":
        docs = load_corpus()
        output = {"review_status": "approved" if all(d.review_status == "approved" for d in docs)
                  else "draft_pending_human_review", "corpus_sha256": corpus_hash(docs), "documents": manifest(docs)}
    elif args.command == "inspect":
        docs = load_corpus()
        chunks = chunk_documents(docs, config["max_words"], config["overlap_words"])
        output = {"documents": manifest(docs), "chunking": chunk_report(chunks)}
    else:
        from .retrieval import Retriever, source_context
        output = Retriever().search(args.query, role=args.role, k=args.k, mode=args.mode, rerank=not args.no_rerank)
        output["context_for_answer_layer"] = source_context(output)
    text = json.dumps(output, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text+"\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
