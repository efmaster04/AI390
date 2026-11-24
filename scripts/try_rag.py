"""Week 3 terminal demo: live RAG, local search, or explicitly recorded replay.

Run from the repository root: python -m scripts.try_rag
"""
import argparse
import json
import os
from pathlib import Path
from src.rag.corpus import ROOT


def show(answer, sources):
    print('\nbeldesk> '+answer.get('answer', ''))
    used = {n for c in answer.get('claims', []) for n in c.get('citations', [])}
    for source in sources:
        if source['citation'] in used:
            print(f"[{source['citation']}] {source['passage_id']} · {source['title']}")
    if not answer.get('valid'):
        print('No valid answer was generated. This is a service/validation error, not an evidence-based refusal.')
    print(f"[tokens in={answer.get('input_tokens')} out={answer.get('output_tokens')} · valid={answer.get('valid')}]")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--replay', metavar='CASE_ID', help='Show a saved example; no API call')
    group.add_argument('--search-only', action='store_true', help='Live local retrieval; no generation/API call')
    args = p.parse_args(argv)
    if args.replay:
        base = ROOT/'eval/results/week3'
        selection = json.loads((base/'active_answer_run.json').read_text())
        rows = [json.loads(line) for line in (base/selection['directory']/'records.jsonl').read_text().splitlines()]
        row = next((r for r in rows if r['case_id'] == args.replay), None)
        if row is None:
            p.error('Unknown recorded case ID')
        print('RECORDED EXAMPLE — no new model call. Run: '+selection['directory'])
        print('citizen> '+row['question'])
        show(row['generation'], row['sources'])
        return 0 if row['generation']['valid'] else 1
    from src.rag.retrieval import Retriever, source_context
    retriever = Retriever()
    provider = None
    if not args.search_only:
        from eval.answer_week3 import TimedGeminiProvider, BoundedProvider
        key = os.getenv('GEMINI_API_KEY')
        if not key:
            p.error('GEMINI_API_KEY is not set; use --search-only for local retrieval')
        provider = BoundedProvider(TimedGeminiProvider('gemini-3.1-flash-lite', key, timeout_s=30),
            max_calls=20, rpm=8, deadline_s=600, transport_retries=1)
    print('LIVE LOCAL RETRIEVAL — no API generation' if args.search_only else
          'LIVE RAG · Gemini 3.1 Flash-Lite · temperature 0 · public sources only')
    print('Turkish or English. Each question is independent. Empty line or Ctrl+C exits.')
    try:
        while True:
            question = input('\ncitizen> ').strip()
            if not question:
                break
            found = retriever.search(question, role='public', k=5)
            sources = source_context(found)
            if args.search_only:
                for source in sources[:3]:
                    print(f"\n[{source['citation']}] {source['passage_id']}\n{source['text']}")
                continue
            from src.rag.answer import answer_with_sources
            provider.case_id, provider.stage = 'interactive_demo', 'answer'
            result = answer_with_sources(question, provider, sources, max_retries=0)
            show(result, sources)
            if provider.exhausted:
                print('Demo request/time budget reached. Exit and restart if needed.')
                break
    except (EOFError, KeyboardInterrupt):
        print('\nDemo stopped.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
