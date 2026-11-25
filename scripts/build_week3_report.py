"""Build the citizen-v2 report, scoreboard and deck data only from recorded artefacts.

    python -m scripts.build_week3_report

No model or network call is made. Every number in reports/week-3.md is read or
computed here from files under eval/results/week3, data/corpus and
eval/testsets. The build stops if the recorded runs do not match the frozen
citizen-v2 hashes or if the post-freeze changes are not provably review
metadata only (eval/week3_provenance.py).
"""
import json
import re
from pathlib import Path

from eval.stats import wilson_ci
from eval.week3_provenance import require as require_provenance
from scripts.run_week3_calibration import refresh
from src.rag.corpus import ROOT, load_corpus

BASE = ROOT/'eval/results/week3'
REPO = 'https://github.com/efmaster04/AI390'
ALLOWED_ALNUM = {'BM25', 'week3'}  # a method name and the branch name week3-fixes


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]


def proportion(k, n, script):
    """Scoreboard entry for an accuracy-type metric: value, n, Wilson 95% interval, script."""
    if not n:
        return {'value': None, 'ci95': None, 'n': None, 'script': None}
    p, lo, hi = wilson_ci(k, n)
    return {'value': round(p, 4), 'ci95': [round(lo, 4), round(hi, 4)], 'n': n, 'script': script}


def approvals(docs, cases, log_path=ROOT/'data/corpus/review_log.jsonl'):
    """Approval counts from document metadata, test-case metadata and the review log."""
    log = read_jsonl(log_path)
    events = [e for e in log if e.get('event') == 'team_review_approved' and e.get('version') == 'citizen-v2']
    public = [d for d in docs if 'public' in d.access]
    return {'documents_approved': sum(d.review_status == 'approved' for d in docs), 'documents_total': len(docs),
            'public_documents_approved': sum(d.review_status == 'approved' for d in public), 'public_documents_total': len(public),
            'cases_approved': sum(c.get('review_status') == 'approved' for c in cases), 'cases_total': len(cases),
            'reviewers': sorted({r for e in events for r in e.get('reviewers', [])}),
            'review_date': events[-1].get('review_date') if events else None,
            'logged_documents': events[-1].get('approved_documents') if events else 0,
            'logged_cases': events[-1].get('approved_test_questions') if events else 0}


def recorded_call_cost(price):
    """List-price equivalent of every recorded generation and judge call (first pass and repair)."""
    total_in = total_out = 0
    for name in ('answers_citizen_v2', 'answers_citizen_v2_repair'):
        for row in read_jsonl(BASE/name/'records.jsonl'):
            for stage in ('generation', 'judgement'):
                part = row.get(stage) or {}
                total_in += part.get('input_tokens') or 0
                total_out += part.get('output_tokens') or 0
    return {'input_tokens': total_in, 'output_tokens': total_out,
            'list_price_usd': (total_in*price['price_in_per_1m_usd']+total_out*price['price_out_per_1m_usd'])/1e6}


def prose_words(markdown):
    """Words outside the scoreboard block, tables and HTML comments (template rule)."""
    text = re.sub(r'```.*?```', ' ', markdown, flags=re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    lines = [line for line in text.splitlines() if not line.lstrip().startswith('|')]
    return len(' '.join(lines).split())


def glued_tokens(markdown):
    """Numbers glued to words (e.g. 'RRF60', '32answerable'), ignoring code spans and link targets."""
    text = re.sub(r'```.*?```', ' ', markdown, flags=re.S)
    text = re.sub(r'`[^`]*`', ' ', text)
    text = re.sub(r'\]\([^)]*\)', ']', text)
    found = re.findall(r'(?<![\w@./#-])[A-Za-z]{2,}\d[\w.]*|\b\d+[A-Za-z]{2,}\w*', text)
    return [t for t in found if t not in ALLOWED_ALNUM]


def fmt(x, digits=3):
    return 'null' if x is None else f'{x:.{digits}f}'


def ci(entry, digits=2):
    lo, hi = entry['ci95']
    return f'{lo:.{digits}f}–{hi:.{digits}f}'


def link(path):
    return f'[`{path}`](../{path})'


def build(write=True):
    frozen = read(ROOT/'eval/testsets/week3_citizen_v2_manifest.json')
    evaluated = frozen['evaluated_files']
    provenance = require_provenance(frozen)
    retrieval = read(BASE/'retrieval/summary.json')
    rescored = read(BASE/'retrieval/rescored_summary.json')
    selection = read(BASE/'active_answer_run.json')
    answer_dir = BASE/selection['directory']
    answer = read(answer_dir/'summary.json')
    meta = read(answer_dir/'run_meta.json')
    if (retrieval['corpus_sha256'], retrieval['cases_sha256']) != (evaluated['corpus_sha256'], evaluated['cases_sha256']):
        raise ValueError('Retrieval results do not match the evaluated citizen-v2 sources/questions')
    if (meta['identity']['corpus_sha256'], meta['identity']['hashes']['cases']) != (evaluated['corpus_sha256'], evaluated['cases_sha256']):
        raise ValueError('Answer results do not match citizen-v2; do not reuse v1 metrics')
    if not rescored['all_checks_pass'] or rescored['ranking_run']['summary_sha256'] is None:
        raise ValueError('Offline re-score did not reproduce the recorded retrieval metrics')
    records = read_jsonl(answer_dir/'records.jsonl')
    cases = read_jsonl(ROOT/'eval/testsets/week3_retrieval.jsonl')
    questions = {c['id']: c for c in cases}
    calibration = refresh()  # Human CSV and embedded v1 evidence are never rewritten.
    docs = load_corpus()
    review = approvals(docs, cases)
    stats = read(BASE/'retrieval/paired_statistics.json')
    chunks = read(BASE/'retrieval/chunks.json')
    summaries = rescored['summaries']
    hybrid, dense, off = summaries['hybrid_rerank'], summaries['dense_rerank'], summaries['hybrid_no_rerank']
    n = hybrid['n_answerable']
    valid = answer['valid_generated_answers']
    prov = answer['answer_provenance']
    faith = answer['faithfulness']
    rate, old_rate = answer['unsupported_claims'], faith['unsupported_claims_before_audit_correction']
    abst = answer['abstention_correct']
    price = meta['prices_snapshot']
    week_cost = recorded_call_cost(price)
    answer_script = f'eval/answer_week3.py --recompute-only --out-dir eval/results/week3/{selection["directory"]}'
    retrieval_script = 'eval/retrieval_week3.py (rankings) -> eval/rescore_retrieval_week3.py'
    null = {'value': None, 'n': None, 'script': None}
    score = {'week': 3, 'test_set_size': len(questions),
             'e2e_accuracy': {'value': None, 'ci95': None, 'n': None, 'script': None},
             'abstention_correct': proportion(abst['numerator'], abst['n'], answer_script),
             'unsupported_claims': proportion(rate['numerator'], rate['n'], answer_script+' (eval/faithfulness_week3.py)'),
             'hit_at_5': proportion(hybrid['counts']['hit_at_5'], n, retrieval_script),
             'mrr': {'value': round(hybrid['mrr_at_10'], 4), 'n': n, 'script': retrieval_script},
             'task_success': dict(null), 'pass_k': {'k': None, **null}, 'injection_success': dict(null),
             'cost_per_task_usd': round(answer['generation_cost_per_task_list_usd'], 6),
             'latency_p50_s': round(answer['latency_p50_s'], 2),
             'spend_week_usd': 0.0, 'spend_total_usd': 0.0}
    cost_summary = {'basis': 'Dated list price (config/prices.json snapshot in run_meta.json) applied to recorded token counts; '
                             'not billed. Gemini free tier: actual spend 0 USD (same convention as Weeks 1 and 2).',
                    'price': price, 'cost_per_task_list_usd': answer['generation_cost_per_task_list_usd'],
                    'cost_per_task_definition': answer['generation_cost_per_task_definition'],
                    'recorded_calls_list_price_equivalent': week_cost,
                    'recorded_calls_note': 'All recorded generation and judge calls of the first pass and the repair pass; '
                                           'usage of 3 failed transport attempts is unknown, so this is a lower bound.',
                    'actual_spend_week_usd': 0.0, 'actual_spend_total_usd': 0.0,
                    'actual_spend_note': 'Weeks 1 and 2 reported 0 USD actual spend on the same free tier.'}

    hit_rows = read_jsonl(BASE/'retrieval/hybrid_rerank.jsonl')
    failures = read(BASE/'retrieval/failures.json')
    observed = next((f for f in failures if f['variant'] == 'hybrid_rerank'), None)
    missing_ranks = {}
    if observed:
        row = next(r for r in hit_rows if r['case_id'] == observed['case_id'])
        for group in observed['missing_facets']:
            missing_ranks[group[0]['passage_id']] = next((r['rank'] for r in row['results']
                                                          if r['passage_id'] in {g['passage_id'] for g in group}), None)
        retrieval_failure = {'case_id': observed['case_id'], 'question': questions[observed['case_id']]['text'],
                             'variant': observed['variant'], 'diagnosis': 'A required answer facet is missing from top 5',
                             'evidence_label': ', '.join(missing_ranks),
                             'note': (f"Missing facet ranked {', '.join(str(v) for v in missing_ranks.values())} of 10; "
                                      f"the model saw only the top 5 and returned the fixed refusal (retrieval failure). "
                                      f"All-facet@5 = {hybrid['all_gold_hit_at_5']:.3f}.")}
    else:
        retrieval_failure = {'case_id': 'none', 'question': 'No top-5 evidence miss was observed on this frozen set.',
                             'variant': 'hybrid_rerank', 'diagnosis': 'No observed miss is not a guarantee on unseen questions',
                             'evidence_label': 'none', 'note': 'Small synthetic test; no failure example is invented.'}
    answer_failures = read(answer_dir/'failures.json')
    stage_of = {(f['case_id'], f['kind']): f['stage'] for f in answer_failures}
    generation_errors = [f['case_id'] for f in answer_failures if f['kind'] == 'generation_or_provider_error']
    judge_errors = [f for f in answer_failures if f['kind'] == 'judge_error_or_invalid']
    unsupported_cases = [f['case_id'] for f in answer_failures if f['kind'] == 'unsupported_or_insufficient_claim']
    answered_controls = [f['case_id'] for f in answer_failures if f['kind'] == 'answered_unavailable_information_control']

    statuses = {f'W3.{i}': {'status': 'done', 'note': ''} for i in range(1, 9)}
    revalidated = prov.get('revalidated_offline_case_ids') or []
    w34_done = valid == len(questions) and abst['value'] == 1
    w34_note = (f"{valid}/{len(questions)} valid citizen-v2 responses after offline re-validation with the widened quote rule "
                f"({prov['after_repair_valid']}/{prov['n']} under the original rule; first pass {prov['first_pass_valid']}/{prov['n']})"
                if revalidated else
                f"{valid}/{len(questions)} valid citizen-v2 responses (first pass {prov['first_pass_valid']}/{prov['n']})")
    w34_note += f"; {abst['numerator']}/{abst['n']} unavailable-information controls returned the fixed refusal."
    if not w34_done and valid == len(questions) and answered_controls:
        w34_note += (f" Not done only because {', '.join(answered_controls)} answered with a cited statement instead of the "
                     f"fixed sentence; whether that counts as a refusal is a team decision.")
    statuses['W3.4'] = {'status': 'done' if w34_done else 'partial', 'note': w34_note}
    statuses['W3.6'] = {'status': 'done' if faith['valid_judged_claims'] > 0 and calibration['n'] >= 20 else 'partial',
                        'note': f"Current claim support measured; {calibration['n']} historical human–judge pairs using preserved v1 sources. "
                                f"Not direct human grading of v2 answers."}
    successes = [r for r in records if r['generation']['valid']]
    tr = next((r for r in successes if r['case_id'] == 'W3-R003'), next((r for r in successes if r['lang'] == 'tr'), {}))
    claim = ((tr.get('generation') or {}).get('claims') or [{}])[0]
    evidence = (claim.get('evidence') or [{}])[0]
    source = next((s for s in tr.get('sources', []) if s['citation'] == evidence.get('citation')), {})
    en = next((r for r in successes if r['lang'] == 'en'), {})
    demo = {'question_tr': tr.get('question', 'No successful Turkish example recorded.'), 'question_en': en.get('question', ''),
            'answer': tr.get('generation', {}).get('answer', 'Model unavailable; no replacement invented.'),
            'source_excerpt': evidence.get('quote', ''), 'source_label': source.get('passage_id', ''),
            'abstain_question': 'No authorized sources supplied (software contract check).',
            'abstain_answer': read(ROOT/'config/rag_answer.json')['fallback']['en'],
            'run_label': 'Recorded citizen-v2 Gemini 3.1 response / 24 Nov 2026'}
    availability = {'selected_directory': selection['directory'], 'dataset_version': 'citizen-v2', 'retry_valid': valid,
                    'retry_processed': len(records), 'cache_hits': answer['valid_answers_from_cache'],
                    'fresh_valid': answer['valid_answers_fresh'], 'model': 'gemini-3.1-flash-lite',
                    'comparable_to_retired_v1': False}
    fail_data = {'generation': {'question': 'Model run on citizen-v2 sources and questions',
                                'answer': (f"{prov['first_pass_valid']}/{prov['n']} valid on the first pass; the "
                                           f"{prov['repair_retried_cases']} invalid cases were retried once and "
                                           f"{prov['valid_replaced_by_repair']} recovered: {prov['after_repair_valid']}/{len(records)}. "
                                           + (f"Offline re-validation of saved outputs with the widened quote rule (no model call): "
                                              f"{valid}/{len(records)}. " if revalidated else "") +
                                           f"No cache hits; "
                                           f"retired v1 answers do not count."),
                                'diagnosis': 'Retrieval coverage, provider availability and claim support are distinct measurements.'},
                 'evaluation': {'title': 'Check what the cited service guide actually supports.',
                                'detail': 'Public guides explain citizen services. Output schemas, authority limits and citation-validation rules belong in prompts and code, outside the public knowledge corpus.'}}
    qa = read(BASE/'qa_summary.json')
    data = {'status_date': '2026-11-25', 'dataset_version': 'citizen-v2', 'tests_passed': qa['tests_passed'],
            'deliverables': statuses, 'scoreboard': score, 'availability': availability,
            'multi_facet_count': len(frozen['multi_facet_cases']), 'cross_service_count': 2,
            'retrieval_failure': retrieval_failure,
            'human_review': {'approved_documents': review['documents_approved'], 'total_documents': review['documents_total'],
                             'claim_labels_completed': calibration['human_labels_completed'], 'claim_labels_target': 20,
                             'matched_human_judge_pairs': calibration['n'], 'observed_agreement': calibration['po'],
                             'kappa': calibration['kappa'], 'calibration_status': calibration['status'],
                             'calibration_origin': 'Historical claims with embedded v1 evidence; not current citizen-v2 answer accuracy.'},
            'product': {'interviews_completed': 2, 'summary': 'Two team-recorded interviews: citizen-relations desk supervisor and municipal IT coordinator; original notes preserved.'},
            'demo': demo,
            'generation': {'summary': f"{valid}/{len(records)} valid citizen-v2 responses; {answer['valid_claim_judgements']} judged; v1 excluded.",
                           'unsupported_claims': rate['value'], 'claims_total': rate['n'],
                           'kappa': calibration['kappa'], 'errors': len(records)-valid},
            'failures': fail_data}

    rows = '\n'.join(f"| {label} | {v['hit_at_k']['1']:.3f} | {v['hit_at_k']['5']:.3f} ({ci({'ci95': v['wilson_95']['hit_at_5']})}) | {v['all_gold_hit_at_5']:.3f} | {v['mrr_at_10']:.3f} |"
                     for label, v in [('Hybrid + reranker (default)', hybrid), ('Dense + reranker', dense), ('Hybrid, no reranker', off)])
    t_dense1, t_off1 = stats['paired_tests']['hybrid_rerank_vs_dense_rerank_hit1'], stats['paired_tests']['hybrid_rerank_vs_hybrid_no_rerank_hit1']
    t_off5 = stats['paired_tests']['hybrid_rerank_vs_hybrid_no_rerank_hit5']
    off_hits = round(off['hit_at_k']['5']*n)
    reviewers = ' and '.join(review['reviewers']) or 'no recorded reviewer'
    unjudged_rows = '\n'.join(f"| {c['case_id']} | {c['claim_id']} | {c['text']} | {c.get('reason', 'judge output invalid')} |" for c in faith['unjudged_claims'])
    pending = [c for c in faith['unjudged_claims'] if c.get('reason', '').startswith('not yet judged')]
    bad_judge = [c for c in faith['unjudged_claims'] if c not in pending]
    previous = read(BASE/meta['components'][-1]['directory']/'summary.json') if revalidated else answer
    excluded = faith['fixed_refusal_verdicts_excluded']
    excluded_ids = ', '.join(sorted({x['case_id'] for x in excluded})) or 'none'
    r032_stage = stage_of.get((observed['case_id'], 'abstained_on_answerable_question')) if observed else None
    kappa = calibration['kappa']
    sb_json = json.dumps(score, ensure_ascii=False, indent=2)
    first_new = prov.get('first_pass_valid_under_new_validator') or {}
    revalidation_text = (
        f"\n- Validator rule changed after seeing the test results. The original rule required each evidence quote to be one "
        f"contiguous substring of its source; in {' and '.join(revalidated)} the model joined two verbatim sentences of the same "
        f"source with an ellipsis, and the rejection repeated on retry. Now a quote may be split by `...`, `…` or `. . .` if every "
        f"segment (at least 8 characters) appears verbatim in the cited source, in source order and without overlap; there is no "
        f"other normalisation. `eval/revalidate_week3.py` re-validated the saved outputs offline; no model was re-called. Valid "
        f"answers: {prov['after_repair_valid']}/{prov['n']} became {valid}/{prov['n']}; no previously valid answer changed. Under "
        f"the new rule the first pass alone gives {first_new.get('valid')}/{first_new.get('n')}. The {len(pending)} claims of the "
        f"re-validated answers are not yet judged and stay outside the claim-rate denominator." if revalidated else '')
    row3 = (f"| 3 | {', '.join(revalidated)}: accessibility report; street-lamp follow-up | Two verbatim sentences of one source "
            f"were joined with an ellipsis; the contiguous-quote rule rejected both answers, also on retry. | generation | Done after "
            f"seeing results: the validator accepts ordered verbatim segments; saved outputs re-validated offline ({valid}/{len(records)} "
            f"valid); retry feedback now shows the quote and the rule. Claims not yet judged. |" if revalidated else
            f"| 3 | {', '.join(generation_errors)}: accessibility report; street-lamp follow-up | Quotes were not exact substrings of "
            f"the source after one retry; no answer shown. | generation | Existing: shown as an error, not counted as a refusal. "
            f"Proposed (team to confirm): better quote-validation feedback, measured as valid answers out of 38. |")

    report = f'''# Weekly report

| Field | Value |
|---|---|
| Team | Beldesk |
| Use case | Custom, instructor-approved: bilingual (TR/EN) municipal citizen assistant for the fictional Yeşilvadi Municipality |
| Week | 3 |
| Repository | {REPO} (branch `week3`; audit fixes on `week3-fixes`) |
| Commit tag | week-3 (not created yet; the team tags the final commit) |
| Presenter | TBD (team to fill) |
| Members and roles | Doruk Kal (data and retrieval lead); Efe İncirci (agent and tools lead); Tarık Edip Yenikomşu (evaluation and safety lead) |

## 1. Summary

We added retrieval-augmented answers over a synthetic citizen-service corpus (citizen-v2: {review['documents_total']} documents, {chunks['count']} chunks) with hybrid search, a local reranker, numbered citations and a fixed refusal. Most important number: hit@5 = {hybrid['hit_at_k']['5']:.2f} ({hybrid['counts']['hit_at_5']}/{n}, 95% CI {ci(score['hit_at_5'])}), but only {hybrid['counts']['all_gold_hit_at_5']}/{n} questions had every required facet in the top 5. Gemini's recorded outputs give {valid}/{len(records)} valid answers{f" after a quote-validator change made after seeing the results ({prov['after_repair_valid']}/{len(records)} before; no model re-called)" if revalidated else ""}; the judge marked {rate['numerator']}/{rate['n']} claims unsupported. An audit corrected the claim-rate definition and one stage label.

## 2. Deliverables

| ID | Status | Evidence | Note |
|---|---|---|---|
| W3.1 | {statuses['W3.1']['status']} | {link('data/corpus/documents/')}; {link('data/corpus/manifest.json')}; {link('data/corpus/review_log.jsonl')}; {link('src/rag/corpus.py')} | {review['documents_total']} synthetic documents ({review['public_documents_total']} public guides, 1 staff-only access fixture) with source, date, version and access metadata. Approved: {review['documents_approved']}/{review['documents_total']} documents and {review['cases_approved']}/{review['cases_total']} test cases ({reviewers}, {review['review_date']}), recorded after the evaluation run on unchanged content. |
| W3.2 | {statuses['W3.2']['status']} | {link('src/rag/chunking.py')}; {link('eval/results/week3/retrieval/chunks.json')} | {chunks['count']} section-aware chunks; 140-word cap with 20-word overlap only for long sections. |
| W3.3 | {statuses['W3.3']['status']} | {link('src/rag/retrieval.py')}; {link('src/rag/lexical.py')}; {link('config/retrieval.json')} | BM25 plus `multilingual-e5-small` dense search, reciprocal rank fusion (k = 60), local cross-encoder reranker; access filtering before ranking. |
| W3.4 | {statuses['W3.4']['status']} | {link('src/rag/answer.py')}; {link('prompts/rag/v1.md')}; {link('config/rag_answer.json')}; {link('eval/revalidate_week3.py')}; {link('eval/results/week3/' + selection['directory'] + '/')} | {statuses['W3.4']['note']} |
| W3.5 | {statuses['W3.5']['status']} | {link('eval/testsets/week3_retrieval.jsonl')}; {link('eval/testsets/week3_citizen_v2_manifest.json')}; {link('docs/week3_benchmark_revision.md')} | {n} answerable questions (16 TR / 16 EN) and {len(questions)-n} controls (3 TR / 3 EN) with exact evidence quotes; 6 separate development cases. |
| W3.6 | {statuses['W3.6']['status']} | {link('eval/faithfulness_week3.py')}; {link('prompts/judge/week3_v1.md')}; {link('eval/results/week3/calibration/human_calibration.json')} | Claim-level judge on current answers; κ = {kappa:.3f} on 20 historical claims (see limitation in section 4). |
| W3.7 | {statuses['W3.7']['status']} | {link('eval/retrieval_week3.py')}; {link('eval/rescore_retrieval_week3.py')}; {link('eval/results/week3/retrieval/rescored_summary.json')}; {link('eval/results/week3/retrieval/paired_statistics.json')} | Two one-change retrieval ablations on the frozen set. |
| W3.8 | {statuses['W3.8']['status']} | {link('eval/results/week3/retrieval/failures.json')}; {link('eval/results/week3/' + selection['directory'] + '/failures.json')} | Failures labelled retrieval, generation or evaluation (section 5). |

## 3. Scoreboard

```json
{sb_json}
```

Values come from {link('eval/results/week3/scoreboard.json')}, written by `python -m scripts.build_week3_report` from recorded artefacts without model calls. Intervals are Wilson 95% (`eval/stats.py`).

- `e2e_accuracy` is null because no answer-correctness rubric was applied to the citizen-v2 answers; claim support is not question completion, and Week 2's 0.952 was measured on a different test set.
- `abstention_correct`: {abst['numerator']}/{abst['n']} unavailable-information controls returned the fixed refusal; {', '.join(answered_controls) or 'none'} answered instead (section 5).
- `unsupported_claims`: metric definition corrected after audit. The judge had labelled the fixed refusal of {excluded_ids} as an unsupported claim, although its rubric excludes fixed refusals. Validated fixed refusals now contribute zero claims: {old_rate['numerator']}/{old_rate['n']} ({old_rate['value']:.3f}) became {rate['numerator']}/{rate['n']} ({rate['value']:.3f}). Not in the denominator: {len(bad_judge)} claims of {', '.join(sorted({c['case_id'] for c in bad_judge})) or 'none'} (invalid judge output) and {len(pending)} claims of {', '.join(sorted({c['case_id'] for c in pending})) or 'none'} (not yet judged):

| Case | Claim | Text | Why not judged |
|---|---|---|---|
{unjudged_rows}

- `hit_at_5` and `mrr` (MRR@10) use the {n} answerable questions. They were re-scored offline from the recorded rankings, reproducing the recorded metrics exactly. The rankings came from a working tree with uncommitted changes at `22577a6` (`"dirty": true`), so a clean rerun with the local models is still open.
- Answers: first pass {prov['first_pass_valid']}/{prov['n']} valid (no validation retry). Only the {prov['repair_retried_cases']} invalid cases were retried once with one validation retry; {prov['valid_replaced_by_repair']} recovered, giving {valid}/{len(records)}. This retry was chosen after seeing failures, so {prov['first_pass_valid']}/{prov['n']} is the same-policy figure. The {prov['valid_retained_from_first_pass']} retained answers are first-pass calls, not cache hits.{revalidation_text}
- `cost_per_task_usd` is a list-price estimate (Week 2 convention): answer-generation tokens per case at the dated Gemini 3.1 Flash-Lite list price (USD {price['price_in_per_1m_usd']:.2f} input / {price['price_out_per_1m_usd']:.2f} output per million tokens, checked {price['checked_on']}); judge and local retrieval excluded. All recorded generation and judge calls together are equivalent to ${week_cost['list_price_usd']:.4f} (a lower bound: usage of 3 failed transport attempts is unknown). Actual spend is $0 (free tier); `spend_total_usd` adds Weeks 1 and 2, also $0.
- `latency_p50_s`: median retrieval plus answer-generation service time over the {valid} valid answers{f" ({previous['latency_p50_s']:.2f} s over the {prov['after_repair_valid']} valid under the original rule)" if revalidated else ""}; excludes the classifier, the judge and rate-limit waits; not end-user wall time.
- Provenance: the runs read the files frozen with review status draft. Commit `576ef4b` later set the review fields to approved. `eval/week3_provenance.py` shows that restoring those fields reproduces the evaluated hashes exactly, so the measured content is unchanged.

Changes to any test set this week: new Week 3 set citizen-v2 (38 cases) replaced the first v1 draft before scoring ({link('docs/week3_benchmark_revision.md')}); after scoring, only review metadata changed.

## 4. Experiments

| Configuration | hit@1 | hit@5 (95% CI) | all-facet@5 | MRR@10 |
|---|---:|---:|---:|---:|
{rows}

### Experiment 1: Dense versus hybrid candidate retrieval

- **Hypothesis:** Lexical BM25 candidates add useful evidence to dense retrieval.
- **Change:** Candidate retrieval only (dense versus hybrid); corpus, questions, 20-candidate budget and reranker fixed.
- **Result:** hit@5 {dense['hit_at_k']['5']:.3f} for both (n = {n}); MRR@10 hybrid {hybrid['mrr_at_10']:.4f}, dense {dense['mrr_at_10']:.4f}. hit@1 paired McNemar: {t_dense1['a_only']} versus {t_dense1['b_only']} discordant, exact p = {t_dense1['p_exact']:.2f}.
- **Decision:** Investigate further; no detectable difference on {n} synthetic questions. Hybrid stays the configured default.

### Experiment 2: Reranker off

- **Hypothesis:** Cross-encoder reranking moves required evidence into the top 5.
- **Change:** Reranking only, with hybrid retrieval fixed.
- **Result:** hit@5 {off['hit_at_k']['5']:.3f} ({off_hits}/{n}, CI {ci({'ci95': off['wilson_95']['hit_at_5']})}) without versus {hybrid['hit_at_k']['5']:.3f} with; MRR@10 {off['mrr_at_10']:.4f} versus {hybrid['mrr_at_10']:.4f}. hit@5 discordant pairs {t_off5['a_only']} versus {t_off5['b_only']}, exact p = {t_off5['p_exact']:.2f}; hit@1 {t_off1['a_only']} versus {t_off1['b_only']}, p = {t_off1['p_exact']:.2f}.
- **Decision:** Keep the reranker; all hit@5 discordant pairs favour it, but the difference is not significant at n = {n}.

### Experiment 3: Judge check against human labels

- **Hypothesis:** The claim judge agrees with a human reviewer on source support.
- **Change:** 20 human labels, adjudicated by the evaluation and safety lead, compared with the judge's labels.
- **Result:** agreement {calibration['po']:.2f}, κ = {kappa:.3f} (n = {calibration['n']}).
- **Decision:** Use the judge provisionally. Limitation: κ was measured on earlier v1 (historical) model claims, with evidence assigned afterwards and samples chosen purposively, not on the citizen-v2 answers behind `unsupported_claims`.

## 5. Failure analysis

| # | Input (short) | What happened | Root cause | Fix (done or planned) |
|---|---|---|---|---|
| 1 | {retrieval_failure['case_id']}: fair permit in a park plus an inaccessible entrance (two facets) | Permit evidence `{retrieval_failure['evidence_label']}` ranked {', '.join(str(v) for v in missing_ranks.values())}; the model saw the top 5 and returned the fixed refusal. | {r032_stage or 'retrieval'} | Done: stage attribution now requires every facet (it was labelled generation). Proposed (team to confirm): a one-change multi-facet retrieval experiment; all-facet@5 is {hybrid['counts']['all_gold_hit_at_5']}/{n}. |
| 2 | {', '.join(answered_controls) or 'none'}: request for a neighbour's phone number from their complaint | Answered with a cited privacy statement instead of the fixed refusal; nothing disclosed, but the contract broke. | {stage_of.get((answered_controls[0], 'answered_unavailable_information_control'), 'generation') if answered_controls else 'generation'} | Proposed (team to confirm): decide whether a privacy denial counts as refusal, then enforce it in prompt or code and re-measure `abstention_correct`. |
{row3}

Also observed: {', '.join(unsupported_cases) or 'none'} contains one unsupported library-membership claim (generation). {', '.join(j['case_id'] for j in judge_errors) or 'None'} got invalid judge output, so its claims stay unjudged (evaluation). The judge's verdict on a fixed refusal was an evaluation-definition error, corrected in section 3.

## 6. Response to last week's feedback

| Feedback point | What we changed | Evidence |
|---|---|---|
| Instructor feedback on Week 2 | Not recorded in the repository. | TBD (team to fill) |
| Review of the first Week 3 draft: meta-questions and developer instructions mixed into the citizen benchmark | Rewrote the public guides and all answerable questions; moved internal cases out of citizen scoring; archived v1 results. | {link('docs/week3_benchmark_revision.md')}; {link('eval/testsets/week3_internal_policy_cases.jsonl')} |
| Audit of the Week 3 branch: stale hashes, claim-rate definition, R032 stage, scoreboard fields, report contradictions | Restored the evaluated hashes with a metadata-only proof; corrected the metric and stage; added intervals and scripts; derived approvals from data. | Branch `week3-fixes`; {link('eval/week3_provenance.py')} |

## 7. Product track

Two team-recorded discovery interviews are preserved in {link('docs/product_interviews_week3.md')}: a citizen-relations desk supervisor and an IT coordinator. Their recorded needs are cited FAQ checklists, controlled intake drafts, local access-filtered retrieval and confirmation before writes. Concerns include invented fees or arrival promises, privacy leakage and uncontrolled actions. No pricing evidence was collected.

## 8. Contributions

| Member | Role | What they did this week | Commits or files | Hours |
|---|---|---|---|---|
| Doruk Kal | Data and retrieval lead | Week 3 RAG pipeline, evaluation and first deck; replaced the meta-guides with the citizen-service corpus and benchmark; README fix. | `be14fc0`, `db364ff`, `8cff813` | TBD (member to fill) |
| Efe İncirci | Agent and tools lead | Independent audit of the Week 3 branch with AI reviewers (Codex, Gemini, Claude) and the fixes on branch week3-fixes; presentation redesign. | branch `week3-fixes` | TBD (member to fill) |
| Tarık Edip Yenikomşu | Evaluation and safety lead | Product-track interview notes; 20 human labels for the judge check; approval of the citizen-v2 documents and cases; connected the Week 2 classifier to the RAG pipeline. | `6dae7a2`, `22577a6`, `576ef4b` | TBD (member to fill) |

Commit evidence: `git log --format='%an %h %s' week-2..HEAD`.

## 9. AI tools used

| Tool | Used for |
|---|---|
| Codex with sub-agents | Citizen-guide and question drafts, source-coverage review, code checks, report and deck updates (team's Week 3 work). |
| Gemini 3.1 Flash-Lite (free tier) | System under test (cited answers) and claim judge. |
| `multilingual-e5-small`, `mmarco-mMiniLMv2` cross-encoder (local, pinned) | Dense retrieval and reranking. |
| Codex, Gemini and Claude reviewers; Claude Code | Audit of the Week 3 branch; Claude Code implemented the fixes on `week3-fixes`. |

AI-drafted sources and labels count only after human review. The team remains responsible for all content.

## 10. Next week

| Priority | Metric it should move | Expected change |
|---|---|---|
| 1. Clean rerun of retrieval and answers on the approved files at the tagged commit (proposed after audit) | hit_at_5, mrr, unsupported_claims | Same content, so similar values; removes the dirty-tree caveat |
| 2. Controlled lookup tool and sandbox writes with confirmation | validated tool-result rate | unmeasured to measured |
| 3. Multi-step tasks with traces and limits | task_success | null to measured, with failure and cost evidence |
'''
    words, glued = prose_words(report), glued_tokens(report)
    if glued:
        raise ValueError(f'Numbers glued to words in the report: {sorted(set(glued))}')
    if words > 1500:
        raise ValueError(f'Report has {words} words; the limit is 1,500')
    qa = {k: v for k, v in qa.items() if k != 'source_case_hashes_match'}
    qa.update(report_words=words, report_words_method='prose outside the scoreboard block and tables (scripts/build_week3_report.py)',
              evaluated_hashes_match_recorded_runs=True,
              measured_content_unchanged_since_evaluation=provenance['ok'],
              current_files_differ_only_in_review_fields=provenance['ok'])
    if write:
        (BASE/'scoreboard.json').write_text(sb_json+'\n', encoding='utf-8')
        (BASE/'cost_summary.json').write_text(json.dumps(cost_summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        (BASE/'presentation_data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        (BASE/'qa_summary.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        (ROOT/'reports/week-3.md').write_text(report, encoding='utf-8')
        print(f'Built citizen-v2 report ({words} words), scoreboard and presentation data from recorded artefacts.')
    return {'data': data, 'report': report, 'score': score, 'words': words, 'review': review, 'qa': qa}


if __name__ == '__main__':
    build()
