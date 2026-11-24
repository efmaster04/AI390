"""Retry the real source-support judge in small, checkpointed batches.

Preserves original human entries; supplementary labels are never read here.
Original judge_batch.json remains historical evidence. Run sequentially after
answer evaluation so both scripts do not independently exceed request pacing.
"""
import json
import os
from datetime import datetime, timezone
from src.rag.corpus import ROOT, digest
from eval.answer_week3 import BoundedProvider, TimedGeminiProvider, atomic_json, write_jsonl
from eval.faithfulness_week3 import judge_claims
from scripts.run_week3_calibration import refresh


def run():
    out = ROOT/'eval/results/week3/calibration'
    rows = [json.loads(s) for s in (out/'records.jsonl').read_text().splitlines()]
    pending = [r for r in rows if not r['judgement'].get('valid')]
    provider = BoundedProvider(TimedGeminiProvider('gemini-3.1-flash-lite', os.environ['GEMINI_API_KEY'], timeout_s=30),
        max_calls=20, rpm=8, deadline_s=360, transport_retries=3)
    results = []
    path = out/'judge_retry_batches.json'
    history = json.loads(path.read_text()).get('invocations', []) if path.exists() else []
    invocation = {'started_utc': datetime.now(timezone.utc).isoformat(), 'model': 'gemini-3.1-flash-lite',
        'batch_size': 5, 'batch_results': results, 'provider_events': provider.events,
        'method': 'Independent retrospective claims; current assigned sources; no supplementary labels supplied to judge.'}
    history.append(invocation)
    for offset in range(0, len(pending), 5):
        if provider.exhausted:
            break
        batch = pending[offset:offset+5]
        sources = [{**r['sources'][0], 'citation': i} for i, r in enumerate(batch, 1)]
        claims = [{'claim_id': f'C{i}', 'text': r['generation']['claims'][0]['text'], 'citations': [i]}
                  for i, r in enumerate(batch, 1)]
        record = {'valid': True, 'abstained': False, 'claims': claims,
                  'answer': '\n'.join(c['text']+f' [{i}]' for i, c in enumerate(claims, 1))}
        provider.case_id = ','.join(r['case_id'] for r in batch)
        provider.stage = 'retrospective_calibration_judge'
        result = judge_claims(record, sources, provider,
            question='Evaluate each independent historical claim against its assigned cited source only.',
            language='mixed', max_retries=0)
        results.append({'case_ids': [r['case_id'] for r in batch], 'judgement': result})
        if result.get('valid') and result.get('coverage_complete'):
            verdicts = {c['claim_id']: c for c in result['claims']}
            for i, row in enumerate(batch, 1):
                row['judgement'] = {'valid': True, 'claims': [dict(verdicts[f'C{i}'], claim_id='C1')],
                    'unlisted_claims': [], 'coverage_complete': True,
                    'reason': 'Real Gemini verdict from a five-claim retrospective batch; post-hoc assigned evidence.',
                    'batch_judge_input_sha256': result['judge_input_sha256'],
                    'model': 'gemini-3.1-flash-lite'}
        write_jsonl(out/'records.jsonl', rows)
        atomic_json(path, {'invocations': history})
        refresh(out, rows)
        print(f'Calibration batch {offset//5+1}: valid={result.get("valid")} calls={provider.calls}', flush=True)
    invocation['finished_utc'] = datetime.now(timezone.utc).isoformat()
    invocation['provider_calls'] = provider.calls
    atomic_json(path, {'invocations': history})
    return refresh(out, rows)


if __name__ == '__main__':
    run()
