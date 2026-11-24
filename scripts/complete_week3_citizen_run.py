"""One bounded validity-repair pass, then compose immutable full-set evidence.

Run only after answers_citizen_v2 finishes. No successful answer is regenerated
or selected by a semantic score. The sole policy change is one validation retry
on the originally invalid cases; component results and provenance stay intact.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from eval.answer_week3 import atomic_json, read_jsonl, recompute, run, write_jsonl
from src.rag.corpus import ROOT, digest
from src.rag.retrieval import Retriever

BASE = ROOT/'eval/results/week3'
ORIGINAL = BASE/'answers_citizen_v2'
REPAIR = BASE/'answers_citizen_v2_repair'
COMPLETE = BASE/'answers_citizen_v2_complete'
CASES = ROOT/'eval/testsets/week3_retrieval.jsonl'


def select(directory, note):
    atomic_json(BASE/'active_answer_run.json', {
        'directory': directory.name, 'dataset_version': 'citizen-v2',
        'reason': note, 'comparable_to_v1_metrics': False})


def same_identity(a, b):
    for key in ('provider', 'model', 'temperature', 'seed', 'corpus_sha256', 'index_sha256'):
        assert a[key] == b[key], f'Component identity changed: {key}'
    for key in ('generation_prompt', 'judge_prompt', 'answer_config'):
        assert a['hashes'][key] == b['hashes'][key], f'Prompt/config changed: {key}'
    assert a['code'] == b['code'], 'Generation/judge/evaluator code changed between components'


def component(path, meta):
    return {'directory': path.name, 'identity': meta['identity'],
            'records_sha256': digest((path/'records.jsonl').read_bytes()),
            'run_meta_sha256': digest((path/'run_meta.json').read_bytes()),
            'provider_calls': meta['provider_calls_this_invocation'],
            'transport_errors': meta.get('transport_errors', 0)}


def main():
    meta = json.loads((ORIGINAL/'run_meta.json').read_text())
    assert meta.get('finished_utc') and meta.get('phase') == 'finished', 'Original run is still active'
    assert meta['identity']['provider'] == 'gemini' and meta['identity']['model'] == 'gemini-3.1-flash-lite'
    cases = read_jsonl(CASES)
    assert digest(CASES.read_bytes()) == meta['identity']['hashes']['cases'], 'Frozen full test changed'
    rows = read_jsonl(ORIGINAL/'records.jsonl')
    assert len(rows) == len(cases) == meta['planned_cases'] == 38
    by_case = {c['id']: c for c in cases}
    assert len({r['case_id'] for r in rows}) == 38 and set(by_case) == {r['case_id'] for r in rows}
    assert all(r['question'] == by_case[r['case_id']]['text'] for r in rows)
    failed = [r for r in rows if not r['generation'].get('valid')]
    if not failed or len(failed) > 5:
        note = 'No repair needed.' if not failed else 'More than five invalid generations: bounded repair skipped.'
        select(ORIGINAL, note)
        print(note)
        return recompute(ORIGINAL)
    if (COMPLETE/'run_meta.json').exists():
        saved = json.loads((COMPLETE/'run_meta.json').read_text())
        assert saved.get('finished_utc'), 'Incomplete composition needs inspection'
        summary = recompute(COMPLETE)
        select(COMPLETE if summary['run_complete'] else ORIGINAL, saved['composition_method'])
        return summary
    assert not (REPAIR/'run_meta.json').exists(), 'A repair was already attempted; inspect it instead of making more calls'
    retriever = Retriever()
    assert retriever.corpus_sha256 == meta['identity']['corpus_sha256']
    assert retriever.index_sha256 == meta['identity']['index_sha256']
    for file, sha in meta['identity']['code'].items():
        assert digest((ROOT/file).read_bytes()) == sha, f'Execution code changed: {file}'
    config = json.loads((ROOT/'config/rag_answer.json').read_text())
    for path, key in [(ROOT/config['prompt_path'], 'generation_prompt'),
                      (ROOT/'prompts/judge/week3_v1.md', 'judge_prompt'),
                      (ROOT/'config/rag_answer.json', 'answer_config')]:
        assert digest(path.read_bytes()) == meta['identity']['hashes'][key], f'Input changed: {path.name}'
    subset = [by_case[r['case_id']] for r in failed]
    subset_path = REPAIR/'frozen_failed_inputs.jsonl'
    write_jsonl(subset_path, subset)
    run(provider_name='gemini', model='gemini-3.1-flash-lite', out_dir=REPAIR,
        cases_path=subset_path, retriever=retriever, transport_retries=0,
        validation_retries=1, defer_judge=True, max_calls=12, rpm=8,
        timeout_s=30, deadline_s=150)
    repair_meta = json.loads((REPAIR/'run_meta.json').read_text())
    same_identity(meta['identity'], repair_meta['identity'])
    repair_rows = {r['case_id']: r for r in read_jsonl(REPAIR/'records.jsonl')}
    assert set(repair_rows) <= {r['case_id'] for r in failed}
    composed, replaced = [], []
    for original in rows:
        retry = repair_rows.get(original['case_id'])
        if retry:
            for key in ('question', 'lang', 'expected_answerable', 'gold', 'gold_groups', 'sources'):
                assert retry.get(key) == original.get(key), f'Repair context changed: {original["case_id"]} {key}'
        if not original['generation'].get('valid') and retry and retry['generation'].get('valid'):
            row = deepcopy(retry)
            row['source_run'] = REPAIR.name
            replaced.append(row['case_id'])
        else:
            row = deepcopy(original)
            # Retained first-pass records are earlier calls of this run, not
            # stage-cache hits. (The recorded answers_citizen_v2_complete was
            # composed before this fix and marks them generation_from_cache;
            # eval.answer_week3.summarize_answers ignores that flag for
            # composed runs and counts them by source_run instead.)
            row['retained_from_first_pass'] = True
            row['source_run'] = ORIGINAL.name
        composed.append(row)
    now = datetime.now(timezone.utc).isoformat()
    method = 'Original successes retained; only originally invalid generations may be replaced by one bounded validity-repair pass. Not 38 independent new calls.'
    composed_meta = {'started_utc': meta['started_utc'], 'finished_utc': now,
        'planned_cases': 38, 'processed_cases': 38, 'phase': 'finished',
        'identity': deepcopy(meta['identity']), 'composition_method': method,
        'composition_code_sha256': digest(Path(__file__).read_bytes()),
        'components': [component(ORIGINAL, meta), component(REPAIR, repair_meta)],
        'replaced_case_ids': replaced, 'repair_validation_retries': 1,
        'original_validation_retries': meta['validation_retries'],
        'provider_calls_this_invocation': 0, 'provider_events': [], 'transport_errors': 0,
        'component_provider_calls_total': meta['provider_calls_this_invocation']+repair_meta['provider_calls_this_invocation'],
        'cache_hits': sum(r['generation_from_cache']+r['judgement_from_cache'] for r in composed),
        'retained_first_pass_records': sum(r.get('retained_from_first_pass', False) for r in composed),
        'cached_results_are_historical_model_calls': True,
        'actual_spend_usd': None, 'cached_consumption_unknown': True,
        'prices_snapshot': meta.get('prices_snapshot')}
    write_jsonl(COMPLETE/'records.jsonl', composed)
    atomic_json(COMPLETE/'run_meta.json', composed_meta)
    summary = recompute(COMPLETE)
    select(COMPLETE if summary['run_complete'] else ORIGINAL,
           method if summary['run_complete'] else 'Repair composition has unattempted stages; original selected, repair evidence retained.')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == '__main__':
    main()
