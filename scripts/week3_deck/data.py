"""Load recorded Week 3 results and derive everything the deck shows.

Every number on a slide comes from here. Nothing is typed by hand: when a value
is missing from the recorded files it stays ``None`` and the deck prints "null".
Only the standard library is used; no model, network or retrieval code is run.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W3 = ROOT / 'eval/results/week3'
DATA = W3 / 'presentation_data.json'


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def maybe_json(value):
    if isinstance(value, str) and value[:1] in '[{':
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def value(item):
    return item.get('value') if isinstance(item, dict) else item


def wilson(k, n, z=1.959963984540054):
    """Wilson score interval; used only when a numerator and n are recorded."""
    if not isinstance(k, (int, float)) or not isinstance(n, (int, float)) or n <= 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, centre - half), min(1.0, centre + half)]


# ---------------------------------------------------------------- lane ranks
def _rrf_pairs(score, k, c):
    """Integer lane-rank pairs (bm25, dense) whose reciprocal-rank sum equals score."""
    options = list(range(1, k + 1)) + [None]
    out = []
    for a in options:
        for b in options:
            v = (1 / (c + a) if a else 0) + (1 / (c + b) if b else 0)
            if score is not None and abs(v - score) < 1e-12:
                out.append((a, b))
    return out


def lane_ranks(results, k=20, c=60):
    """Recover BM25 and dense lane ranks from the recorded RRF scores.

    The recorded run stores each returned chunk's RRF score, BM25 score and dense
    score. Reciprocal-rank fusion is 1/(c+r_bm25) + 1/(c+r_dense); we keep the
    single assignment of integer ranks that is unique per lane and consistent with
    the recorded score order. If the assignment is not unique we return None
    rather than guess.
    """
    options = [_rrf_pairs(r.get('rrf_score'), k, c) for r in results]
    if not results or any(not o for o in options):
        return None
    good = []
    for combo in itertools.product(*options):
        ok = True
        for lane, key in ((0, 'bm25_score'), (1, 'dense_score')):
            ranked = [(pair[lane], r.get(key)) for pair, r in zip(combo, results) if pair[lane]]
            if len({a for a, _ in ranked}) < len(ranked):
                ok = False
                break
            for (a1, s1), (a2, s2) in itertools.combinations(ranked, 2):
                if s1 is None or s2 is None or s1 == s2:
                    continue
                if (a1 < a2) != (s1 > s2):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            good.append(combo)
            if len(good) > 1:
                return None
    if len(good) != 1:
        return None
    return {r['passage_id']: {'bm25': pair[0], 'dense': pair[1]} for pair, r in zip(good[0], results)}


def journey(case, config):
    """Ranked lists for one recorded retrieval case (hybrid + reranker)."""
    if not case:
        return None
    results = case.get('results', [])
    fused = case.get('candidate_passage_ids', [])
    lanes = lane_ranks(results, config.get('candidate_k', 20), config.get('rrf_constant', 60))
    by_pid = {r['passage_id']: r for r in results}
    gold_groups = [[g['passage_id'] for g in group] for group in case.get('gold_groups', [])]
    gold = {pid for group in gold_groups for pid in group}

    def card(pid):
        r = by_pid.get(pid, {})
        return {'pid': pid, 'title_en': r.get('title_en'), 'heading': r.get('heading'),
                'fused': fused.index(pid) + 1 if pid in fused else None,
                'rerank': r.get('rank'), 'gold': pid in gold,
                'bm25_score': r.get('bm25_score'), 'dense_score': r.get('dense_score'),
                'rrf_score': r.get('rrf_score'), 'reranker_score': r.get('reranker_score')}

    def lane(name):
        if lanes is None:
            return None
        ranked = sorted((v[name], pid) for pid, v in lanes.items() if v[name])
        slots = {r: pid for r, pid in ranked}
        return [card(slots[i]) if i in slots else {'pid': None, 'rank': i} for i in range(1, 6)]

    rerank_top = [r['passage_id'] for r in results[:5]]
    show = []
    for pid in fused[:5] + rerank_top + sorted(gold, key=lambda p: by_pid.get(p, {}).get('rank') or 99):
        if pid not in show and pid in by_pid and (by_pid[pid].get('rank') or 99) <= 10:
            show.append(pid)
    for pid in fused[:5]:
        if pid not in by_pid and pid not in show:
            show.append(pid)
    cards = [card(pid) for pid in show]
    if lanes:
        for c in cards:
            c.update({'lane_bm25': lanes.get(c['pid'], {}).get('bm25'), 'lane_dense': lanes.get(c['pid'], {}).get('dense')})
    metrics = case.get('metrics', {})
    facet_ranks = []
    for group in gold_groups:
        ranks = [by_pid[p]['rank'] for p in group if p in by_pid]
        facet_ranks.append({'pids': group, 'rank': min(ranks) if ranks else None,
                            'fused': min((fused.index(p) + 1 for p in group if p in fused), default=None)})
    return {'case_id': case.get('case_id'), 'query': case.get('query'), 'lang': case.get('lang'),
            'bm25': lane('bm25'), 'dense': lane('dense'), 'cards': cards, 'facets': facet_ranks,
            'first_relevant_rank': metrics.get('first_relevant_rank'),
            'all_gold_hit_at_5': metrics.get('all_gold_hit_at_5'), 'n_candidates': len(fused)}


# ------------------------------------------------------------------- loading
def load(data_override=None):
    data = data_override if data_override is not None else read_json(DATA, {})
    retrieval = read_json(W3 / 'retrieval/summary.json', {})
    summaries = retrieval.get('summaries', {})
    config = retrieval.get('config', {})
    paired = read_json(W3 / 'retrieval/paired_statistics.json', {})
    chunks = read_json(W3 / 'retrieval/chunks.json', {})
    manifest = read_json(ROOT / 'data/corpus/manifest.json', {})
    docs = manifest.get('documents', [])
    runs = {name: {c['case_id']: c for c in read_jsonl(W3 / f'retrieval/{name}.jsonl')}
            for name in ('hybrid_rerank', 'hybrid_no_rerank', 'dense_rerank')}
    answer_dir = W3 / (data.get('availability', {}).get('selected_directory') or 'answers_citizen_v2_complete')
    answers = {r['case_id']: r for r in read_jsonl(answer_dir / 'records.jsonl')}
    answer_summary = read_json(answer_dir / 'summary.json', {})
    answer_failures = read_json(answer_dir / 'failures.json', [])
    calib = read_json(W3 / 'calibration/human_calibration.json', {})
    old = read_json(ROOT / 'eval/results/week2/scoreboard.json', {})

    chunk_list = chunks.get('chunks', [])
    staff_chunks = [c for c in chunk_list if 'public' not in c.get('access', [])]
    public_docs = [d for d in docs if 'public' in d.get('access', [])]
    staff_docs = [d for d in docs if 'public' not in d.get('access', [])]

    base = runs['hybrid_rerank']
    answerable = [c for c in base.values() if c.get('answerable')]
    controls = [c for c in base.values() if not c.get('answerable')]
    dots = [{'id': c['case_id'], 'lang': c.get('lang'),
             'rank': c.get('metrics', {}).get('first_relevant_rank'),
             'all5': c.get('metrics', {}).get('all_gold_hit_at_5')} for c in sorted(answerable, key=lambda c: (c.get('lang') != 'tr', c['case_id']))]

    # Recorded generation records for the demo and failure cases.
    def answer_view(case_id):
        rec = answers.get(case_id)
        if not rec:
            return None
        gen = maybe_json(rec.get('generation')) or {}
        src = maybe_json(rec.get('sources')) or []
        judge = maybe_json(rec.get('judgement')) or {}
        return {'case_id': case_id, 'question': rec.get('question'), 'answer': gen.get('answer'),
                'claims': gen.get('claims') or [], 'abstained': gen.get('abstained'),
                'sources': [{k: s.get(k) for k in ('citation', 'passage_id', 'title', 'heading', 'text')} for s in src],
                'judge_claims': judge.get('claims') or [], 'judge_unlisted': judge.get('unlisted_claims') or [],
                'judge_reason': judge.get('reason'), 'model': gen.get('model')}

    demo_q = data.get('demo', {}).get('question_tr')
    demo_id = next((cid for cid, c in base.items() if demo_q and c.get('query') == demo_q), None)
    fail_id = data.get('retrieval_failure', {}).get('case_id')

    # Human vs judge calibration pairs (historical v1 evidence).
    human = {}
    sheet = W3 / 'calibration/human_sheet.csv'
    if sheet.exists():
        with sheet.open(encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                human[(row['case_id'], row['claim_id'])] = row.get('human_label') or None
    pairs = []
    for rec in read_jsonl(W3 / 'calibration/records.jsonl'):
        judge = maybe_json(rec.get('judgement')) or {}
        for cl in judge.get('claims') or []:
            pairs.append({'id': rec['case_id'], 'human': human.get((rec['case_id'], cl.get('claim_id'))), 'judge': cl.get('label')})

    # Failure stages: the recorded failures.json "stage" field decides; generation_or_provider_error goes to
    # Provider and evaluation goes to Judge. Retrieval all-facet misses are added once per case.
    stage_cases = {'retrieval': [], 'generation': [], 'provider': [], 'judge': []}
    fail_ranks = {}
    for c in answerable:
        if c.get('metrics', {}).get('all_gold_hit_at_5') is False:
            fail_ranks[c['case_id']] = journey(c, config)
    stage_of = {'retrieval': 'retrieval', 'generation': 'generation', 'evaluation': 'judge', 'judge': 'judge', 'provider': 'provider'}
    kind_text = {'unsupported_or_insufficient_claim': 'unsupported claim', 'abstained_on_answerable_question': 'refused an answerable question',
                 'answered_unavailable_information_control': 'answered a control', 'judge_error_or_invalid': 'judge output invalid'}
    # Records that are not failures (e.g. an answer re-validated offline whose claims are not judged yet)
    # are kept apart, so they never appear in a failure stage.
    NOT_FAILURES = {'claims_not_yet_judged'}
    pending = [{'id': f.get('case_id'), 'claims': f.get('unjudged_claims'), 'note': f.get('note')} for f in answer_failures if f.get('kind') in NOT_FAILURES]
    for f in answer_failures:
        kind = f.get('kind')
        if kind in NOT_FAILURES:
            continue
        stage = 'provider' if kind == 'generation_or_provider_error' else stage_of.get(f.get('stage'), 'generation')
        text = kind_text.get(kind) or (f.get('error') or kind or 'null').replace('_', ' ')
        if f.get('missing_facets'):
            j = fail_ranks.get(f.get('case_id'))
            rank = next((c.get('rerank') for c in (j or {}).get('cards', []) if c['pid'] in f['missing_facets']), None)
            text = f'facet {", ".join(f["missing_facets"])} at rank {rank if rank is not None else "null"}; {text}'
        if f.get('unjudged_claims'):
            text += f' · {f["unjudged_claims"]} claims unjudged'
        stage_cases[stage].append({'id': f.get('case_id'), 'kind': text, 'stage_raw': f.get('stage'), 'raw': f})
    for cid, j in fail_ranks.items():
        if not any(c['id'] == cid for c in stage_cases['retrieval']):
            stage_cases['retrieval'].append({'id': cid, 'kind': 'required facet outside top 5', 'stage_raw': 'retrieval', 'raw': {}})

    # Unsupported-claim rate: numerator from the scoreboard, else the run summary, else the judge label counts.
    sb_us = (data.get('scoreboard') or {}).get('unsupported_claims')
    sb_us = sb_us if isinstance(sb_us, dict) else {}
    faith = answer_summary.get('faithfulness', {}) or {}
    sum_us = answer_summary.get('unsupported_claims') if isinstance(answer_summary.get('unsupported_claims'), dict) else {}
    labels = faith.get('labels') or {}
    numerator = next((v for v in (sb_us.get('numerator'), sum_us.get('numerator'),
                                  (labels.get('unsupported', 0) + labels.get('insufficient_evidence', 0)) if labels else None) if isinstance(v, int)), None)
    claim_n = next((v for v in (sb_us.get('n'), sum_us.get('n'), faith.get('valid_judged_claims')) if isinstance(v, int)), None)
    before = faith.get('unsupported_claims_before_audit_correction') or {}
    claims = {'numerator': numerator, 'n': claim_n, 'value': value(sb_us) if sb_us else sum_us.get('value'),
              'ci95': sb_us.get('ci95'), 'supported': labels.get('supported'),
              'before': {'numerator': before.get('numerator'), 'n': before.get('n'), 'value': before.get('value')} if before else None,
              'correction': faith.get('metric_definition_corrected_after_audit'),
              'excluded_refusals': [x.get('case_id') for x in faith.get('fixed_refusal_verdicts_excluded') or []],
              'unjudged': faith.get('unjudged_claims') or [],
              'gen_errors': answer_summary.get('judgements_skipped_generation_error'),
              'pending': pending,
              'valid_original_rule': (answer_summary.get('answer_provenance') or {}).get('after_repair_valid'),
              'revalidated': (answer_summary.get('answer_provenance') or {}).get('revalidated_offline_case_ids') or [],
              'judge_errors': answer_summary.get('judgements_failed_or_invalid'),
              'first_pass_valid': (answer_summary.get('answer_provenance') or {}).get('first_pass_valid')}

    # Human approvals: current review fields plus the run-time status of the evaluated cases.
    testset = read_jsonl(ROOT / 'eval/testsets/week3_retrieval.jsonl')
    review_events = [e for e in read_jsonl(ROOT / 'data/corpus/review_log.jsonl') if e.get('event') == 'team_review_approved']
    run_status = {c.get('review_status') for c in base.values()}
    approvals = {'docs': sum(dd.get('review_status') == 'approved' for dd in docs) if docs else None, 'docs_total': len(docs) or None,
                 'cases': sum(c.get('review_status') == 'approved' for c in testset) if testset else None, 'cases_total': len(testset) or None,
                 'reviewers': review_events[-1].get('reviewers') if review_events else None,
                 'after_run': bool(testset) and run_status == {'draft'} and all(c.get('review_status') == 'approved' for c in testset)}

    # Next-week priorities from the team report (section "Next week" table).
    priorities = []
    report = ROOT / 'reports/week-3.md'
    if report.exists():
        txt = report.read_text(encoding='utf-8')
        m = re.search(r'^##\s*\d*\.?\s*Next week\s*$(.*?)(?=^##\s|\Z)', txt, re.M | re.S)
        if m:
            for line in m.group(1).splitlines():
                cells = [x.strip() for x in line.strip().strip('|').split('|')]
                if len(cells) >= 3 and re.match(r'\d+\.', cells[0]):
                    priorities.append({'priority': cells[0], 'metric': cells[1].replace('`', ''), 'expected': cells[2]})

    return {
        'data': data, 'old': old, 'summaries': summaries, 'config': config, 'paired': paired,
        'retrieval_meta': {k: retrieval.get(k) for k in ('corpus_sha256', 'index_sha256', 'config_sha256', 'cases_sha256', 'api_calls')},
        'n_docs': len(docs) or None, 'n_public_docs': len(public_docs) or None, 'staff_docs': staff_docs,
        'n_chunks': chunks.get('count'), 'staff_chunks': staff_chunks, 'chunk_list': chunk_list,
        'approved_public': sum(d.get('review_status') == 'approved' for d in public_docs) if docs else None,
        'dots': dots, 'n_answerable': len(answerable) or None, 'n_controls': len(controls),
        'control_ids': sorted(c['case_id'] for c in controls),
        'demo_journey': journey(base.get(demo_id), config), 'demo_answer': answer_view(demo_id) if demo_id else None,
        'fail_journey': journey(base.get(fail_id), config), 'fail_answer': answer_view(fail_id) if fail_id else None,
        'fail_no_rerank': journey(runs['hybrid_no_rerank'].get(fail_id), config) if fail_id else None,
        'answer_summary': answer_summary, 'answer_failures': answer_failures, 'stage_cases': stage_cases,
        'calib': calib, 'pairs': pairs, 'claims': claims, 'approvals': approvals, 'priorities': priorities,
        'provenance_script': (ROOT / 'eval/week3_provenance.py').exists(),
        'answer_dir': answer_dir.name,
    }
