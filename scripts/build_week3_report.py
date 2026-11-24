"""Build the citizen-v2 report/deck data only from matching measured artifacts."""
import json
from pathlib import Path
from src.rag.corpus import ROOT, load_corpus, digest
from scripts.run_week3_calibration import refresh


def read(path):
    return json.loads(path.read_text())


def build():
    base = ROOT/'eval/results/week3'
    frozen = read(ROOT/'eval/testsets/week3_citizen_v2_manifest.json')
    retrieval = read(base/'retrieval/summary.json')
    selection = read(base/'active_answer_run.json')
    answer_dir = base/selection['directory']
    answer = read(answer_dir/'summary.json')
    meta = read(answer_dir/'run_meta.json')
    for field in ('corpus_sha256', 'cases_sha256'):
        if retrieval[field] != frozen[field]:
            raise ValueError('Retrieval results do not match the frozen citizen-v2 sources/questions')
    if meta['identity']['corpus_sha256'] != frozen['corpus_sha256'] or meta['identity']['hashes']['cases'] != frozen['cases_sha256']:
        raise ValueError('Answer results do not match citizen-v2; do not reuse v1 metrics')
    records = [json.loads(x) for x in (answer_dir/'records.jsonl').read_text().splitlines()]
    questions = {c['id']:c for c in map(json.loads,(ROOT/'eval/testsets/week3_retrieval.jsonl').read_text().splitlines())}
    calibration = refresh()  # Human CSV and embedded v1 evidence are never rewritten.
    docs = load_corpus(); approved = sum(d.review_status=='approved' for d in docs)
    stats = read(base/'retrieval/paired_statistics.json')
    chunks = read(base/'retrieval/chunks.json')
    summaries = retrieval['summaries']; hybrid = summaries['hybrid_rerank']; dense = summaries['dense_rerank']; off = summaries['hybrid_no_rerank']
    n = hybrid['n_answerable']; valid = answer['valid_generated_answers']
    unknown = {'value':None,'n':None,'script':None}
    score = {'week':3,'test_set_size':len(questions),'e2e_accuracy':dict(unknown),
             'abstention_correct':answer['abstention_correct'],'unsupported_claims':answer['unsupported_claims'],
             'hit_at_5':{'value':hybrid['hit_at_k']['5'],'n':n,'script':'eval/retrieval_week3.py'},
             'mrr':{'value':hybrid['mrr_at_10'],'n':n,'cutoff':10,'script':'eval/retrieval_week3.py'},
             'task_success':dict(unknown),'pass_k':{'k':None,**unknown},'injection_success':dict(unknown),
             'cost_per_task_usd':None,'latency_p50_s':answer['latency_p50_s'],'spend_week_usd':None,'spend_total_usd':None}
    (base/'scoreboard.json').write_text(json.dumps(score,ensure_ascii=False,indent=2)+'\n')
    failures = read(base/'retrieval/failures.json')
    observed = next((f for f in failures if f['variant']=='hybrid_rerank'), failures[0] if failures else None)
    if observed:
        partial = observed.get('failure_kind')=='missing_required_facet'
        retrieval_failure = {'case_id':observed['case_id'],'question':questions[observed['case_id']]['text'],
            'variant':observed['variant'], 'diagnosis':'A required answer facet is missing from top 5' if partial else 'Required evidence is outside top 5',
            'evidence_label':', '.join(g[0]['passage_id'] for g in observed.get('missing_facets',[])),
            'note':f"{observed['root_cause']}. Finding one relevant passage does not cover every requested part; all-facet@5 = {hybrid['all_gold_hit_at_5']:.3f}."}
    else:
        retrieval_failure = {'case_id':'none','question':'No top-5 evidence miss was observed on this frozen draft set.',
            'variant':'hybrid_rerank','diagnosis':'No observed miss is not a guarantee on unseen questions','evidence_label':'none','note':'Small synthetic test; no failure example is invented.'}
    statuses={f'W3.{i}':{'status':'done','note':''} for i in range(1,9)}
    statuses['W3.4']={'status':'done' if valid==len(questions) and answer['abstention_correct']['value']==1 else 'partial',
                     'note':f'{valid}/{len(questions)} valid citizen-v2 responses; actual fixed-refusal results retained.'}
    statuses['W3.6']={'status':'done' if answer['faithfulness']['valid_judged_claims']>0 and calibration['n']>=20 else 'partial',
                     'note':f"Current claim support measured; {calibration['n']} historical human–judge pairs using preserved v1 sources. Not direct human grading of v2 answers."}
    successes=[r for r in records if r['generation']['valid']]
    tr=next((r for r in successes if r['case_id']=='W3-R003'),next((r for r in successes if r['lang']=='tr'),{}))
    claim=((tr.get('generation') or {}).get('claims') or [{}])[0]
    evidence=(claim.get('evidence') or [{}])[0]
    source=next((s for s in tr.get('sources',[]) if s['citation']==evidence.get('citation')), {})
    en=next((r for r in successes if r['lang']=='en'),{})
    demo={'question_tr':tr.get('question','No successful Turkish example recorded.'),'question_en':en.get('question',''),
          'answer':tr.get('generation',{}).get('answer','Model unavailable; no replacement invented.'),
          'source_excerpt':evidence.get('quote',''),'source_label':source.get('passage_id',''),
          'abstain_question':'No authorized sources supplied (software contract check).',
          'abstain_answer':read(ROOT/'config/rag_answer.json')['fallback']['en'],
          'run_label':'Recorded citizen-v2 Gemini 3.1 response / 24 Nov 2026'}
    availability={'selected_directory':selection['directory'],'dataset_version':'citizen-v2','retry_valid':valid,
                  'retry_processed':len(records),'cache_hits':answer['valid_answers_from_cache'],'fresh_valid':answer['valid_answers_fresh'],
                  'model':'gemini-3.1-flash-lite','comparable_to_retired_v1':False}
    fail_data={'generation':{'question':'Fresh model run on citizen-v2 sources and questions',
        'answer':f"{valid}/{len(records)} valid responses; {availability['fresh_valid']} fresh and {availability['cache_hits']} reused within this version. Retired v1 answers do not count.",
        'diagnosis':'Retrieval coverage, provider availability and claim support are distinct measurements.'},
        'evaluation':{'title':'Check what the cited service guide actually supports.',
        'detail':'Public guides explain citizen services. Output schemas, authority limits and citation-validation rules belong in prompts and code, outside the public knowledge corpus.'}}
    data={'status_date':'2026-11-24','dataset_version':'citizen-v2','tests_passed':read(base/'qa_summary.json')['tests_passed'],
          'deliverables':statuses,'scoreboard':score,'availability':availability,
          'multi_facet_count':len(frozen['multi_facet_cases']),'cross_service_count':2,'retrieval_failure':retrieval_failure,
          'human_review':{'approved_documents':approved,'total_documents':len(docs),'claim_labels_completed':calibration['human_labels_completed'],
            'claim_labels_target':20,'matched_human_judge_pairs':calibration['n'],'observed_agreement':calibration['po'],
            'kappa':calibration['kappa'],'calibration_status':calibration['status'],
            'calibration_origin':'Historical claims with embedded v1 evidence; not current citizen-v2 answer accuracy.'},
          'product':{'interviews_completed':2,'summary':'Two team-recorded interviews: citizen-relations desk supervisor and municipal IT coordinator; original notes preserved.'},
          'demo':demo,'generation':{'summary':f'{valid}/{len(records)} valid citizen-v2 responses; {answer["valid_claim_judgements"]} judged; v1 excluded.',
            'unsupported_claims':score['unsupported_claims']['value'],'claims_total':answer['faithfulness']['valid_judged_claims'],
            'kappa':calibration['kappa'],'errors':len(records)-valid},'failures':fail_data}
    (base/'presentation_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    def val(v):return 'null' if v is None else f'{v:.3f}'
    rows='\n'.join(f"| {label} | {v['hit_at_k']['1']:.3f} | {v['hit_at_k']['5']:.3f} | {v['all_gold_hit_at_5']:.3f} | {v['mrr_at_10']:.3f} |" for label,v in [('Hybrid + reranker',hybrid),('Dense + reranker',dense),('Hybrid, no reranker',off)])
    ci=stats['wilson_95']['hybrid_rerank']['5']
    report=f'''# Weekly report

| Field | Value |
|---|---|
| Team / week | Beldesk / 3 |
| Use case | Fictional Yeşilvadi bilingual municipal assistant |
| Repository / branch | https://github.com/efmaster04/AI390 / week3 |
| Source and benchmark version | citizen-v2 |
| Release tag | week-3 not created |
| Members | Efe İncirci: agent/tools; Doruk Kal: data/retrieval; Tarık Edip Yenikomşu: evaluation/safety |

## 1. Summary

We corrected a benchmark-design problem: v1 mixed developer-policy questions and internal instructions with citizen service knowledge. The active corpus now has 30 citizen-facing synthetic service guides and one staff-only ACL fixture. All32answerable questions describe resident situations; six unavailable-information/privacy controls remain separate. Corpus bodies and questions were reviewed for scope before freezing; no retrieval results were consulted during that rewrite. Earlier v1 scores and responses are archived, not relabelled as new results.

## 2. Deliverables

| ID | Status | Evidence |
|---|---|---|
| W3.1 | done | 31 cleaned documents, source/date/version/access metadata; {approved}/31 current explicit human approvals. Rewritten guides reset to draft. |
| W3.2 | done | {chunks['count']} section-aware chunks;140-word cap,20-word overlap only for long sections; actual overlap zero. |
| W3.3 | done | BM25+dense, RRF60, pinned local E5 and cross-encoder; public/staff filtering before ranking. |
| W3.4 | {statuses['W3.4']['status']} | {valid}/{len(records)} valid current responses; numbered references, quote validation and fixed TR/EN no-evidence response. |
| W3.5 | done | 32answerable questions(16TR/16EN),6controls(3TR/3EN), exact evidence;6separate dev cases. |
| W3.6 | {statuses['W3.6']['status']} | Claim support measured on current answers;20human labels against preserved v1 source snapshots; κ={calibration['kappa']:.3f}. |
| W3.7 | done | Two one-change retrieval ablations on the frozen citizen-v2 set. |
| W3.8 | done | Full misses and missing facets labelled retrieval; unsupported outputs/provider failures separated as generation/provider; judge failures separate. |

## 3. Scoreboard

```json
{json.dumps(score,ensure_ascii=False,indent=2)}
```

Retrieval denominator:32. Hit@k finds at least one required answer facet; all-facet@5 requires every requested facet. Alternatives within a facet were registered before scoring, not added after misses. Three questions need multiple passages; two span services. Answer availability is not semantic correctness; E2E adequacy remains unmeasured. Model claim judgements are provisional. Latency excludes scheduling/backoff waits; actual billing is unknown. v1 and v2 are different benchmarks, so their percentages are not a like-for-like improvement claim.

## 4. Experiments

| Configuration | hit@1 | hit@5 | all-facet@5 | MRR@10 |
|---|---:|---:|---:|---:|
{rows}

**Ablation1 — dense versus hybrid.** Hypothesis: lexical matching adds useful candidates. Change only candidate retrieval; keep corpus, questions,20-candidate budget and reranker fixed. Hybrid MRR={hybrid['mrr_at_10']:.4f}; dense={dense['mrr_at_10']:.4f}. Report the observed result without asserting hybrid superiority. Exact paired tests and Wilson intervals: `retrieval/paired_statistics.json`. Hybrid hit@5 Wilson95% interval: approximately{ci[1]:.3f}–{ci[2]:.3f}.

**Ablation2 — reranker off.** Hypothesis: reranking promotes useful evidence. Change only reranking with hybrid fixed. MRR={off['mrr_at_10']:.4f} without versus{hybrid['mrr_at_10']:.4f} with; hit@5={off['hit_at_k']['5']:.3f} versus{hybrid['hit_at_k']['5']:.3f}. This small, synthetic draft set does not establish universal superiority.

**Current answering and faithfulness.** Gemini3.1Flash-Lite remains unchanged,T=0. The run contains {valid}/{len(records)} valid responses, with {availability['fresh_valid']} fresh successes and {availability['cache_hits']} cache hits within citizen-v2. No v1 stage cache was copied. A bounded repair pass may replace only originally invalid generations; successful citizen-v2 stages remain recorded and are not selected by semantic score. Judge-labelled unsupported/insufficient claims: {score['unsupported_claims']['numerator']}/{score['unsupported_claims']['n']}. Valid answer-level judgements: {answer['valid_claim_judgements']}/{valid}; missing judgements do not count as supported claims. This is source-support estimation, not complete-answer accuracy. Current source/question hashes must match the frozen manifest before report generation.

**Historical judge check.** Preserve the team's20adjudicated human labels and real judge verdicts. Agreement={calibration['po']:.3f}, κ={calibration['kappa']:.3f},n={calibration['n']}. These are purposefully selected historical model claims with v1 evidence assigned afterward. They check the source-support rubric, not manual accuracy of new citizen-v2 answers. A small retrospective calibration does not by itself validate the current claim-rate estimate.

## 5. Failure analysis

Observed retrieval case: **{retrieval_failure['case_id']}**, variant `{retrieval_failure['variant']}`. {retrieval_failure['diagnosis']}. Missing evidence: `{retrieval_failure['evidence_label']}`. {retrieval_failure['note']}

In particular, a source answering one half of a multi-service request can produce hit@5 while the other half is missing. We retain that as an incomplete-evidence failure. W3-R017 also contains a judge-flagged unsupported claim about library membership requirements, recorded as a generation issue. Provider and exact-quote validation errors remain failed stages; they are not counted as honest refusals. W3-U004 returns a source-supported privacy-policy denial rather than the exact fixed sentence: no phone number is disclosed, but this fails the strict fixed-fallback contract. Semantic source support does not prove that every part of a citizen's request was answered.

## 6. Response to feedback and benchmark revision

Week2 feedback was generally positive. The subsequent review correctly identified meta-questions and developer instructions in v1. We rewrote all30public guides and all32answerable prompts, kept19TR/19EN overall, moved internal examples outside citizen scoring and archived v1 results. Labels, alternative evidence and source hashes were frozen before rerunning all variants. No post-score source or gold editing was used to raise a metric. See `docs/week3_benchmark_revision.md`.

## 7. Product track

Two team-recorded discovery interviews are preserved in `docs/product_interviews_week3.md`: a citizen-relations desk supervisor and an IT coordinator. Their recorded needs are cited FAQ checklists, controlled intake drafts, local access-filtered retrieval and confirmation before writes. Concerns include invented fees/arrival promises, privacy leakage and uncontrolled actions. These are the team's supplied interview notes; this revision adds no invented interviews or pricing evidence.

## 8. Contributions

| Member | Evidence and review area |
|---|---|
| Doruk Kal | Directed the correction; data/retrieval work and bilingual citizen benchmark prepared with Codex; earlier source approval kept version-specific. |
| Efe İncirci | Assigned agent/tools integration and review area. |
| Tarık Edip Yenikomşu | Team-recorded20-item adjudication preserved; assigned evaluation/safety area. |

Hours were not recorded. This revision does not reconstruct individual contribution hours.

## 9. AI tools used

Codex and subagents prepared citizen-guide drafts, independent question drafts, source-coverage review, code checks and report/deck updates. Human source/gold approval is not inferred from that work. Pinned multilingual E5 and cross-encoder run locally. Actual Gemini generation/judge records and provider errors are retained separately.

## 10. Next week

| Priority | Metric to move |
|---|---|
| Editorial review of citizen-v2 guides and expected answers | Current public-guide approvals:0/30 toward30/30; independently check draft gold labels. |
| Add controlled lookup and sandbox writes | Validated tool-result rate: unmeasured to measured; confirmation before any write. |
| Measure multi-step tasks with traces and limits | task_success: null to measured, with failure and cost evidence. |
'''
    (ROOT/'reports/week-3.md').write_text(report)
    print('Built citizen-v2 report, scoreboard and presentation data from matching artifacts.')
    return data


if __name__=='__main__':
    build()
