"""Build the local report and presentation data from measured files, not invented results."""
import csv,json
from pathlib import Path
from src.rag.corpus import ROOT,load_corpus
from scripts.run_week3_calibration import refresh

def build():
 base=ROOT/'eval/results/week3';retr=json.loads((base/'retrieval/summary.json').read_text())
 selection=json.loads((base/'active_answer_run.json').read_text()) if (base/'active_answer_run.json').exists() else {'directory':'answers'}
 answer_dir=base/selection['directory']
 answer=json.loads((answer_dir/'summary.json').read_text()) if (answer_dir/'summary.json').exists() else {}
 records=[json.loads(x) for x in (answer_dir/'records.jsonl').read_text().splitlines()]
 baseline=json.loads((base/'answers/summary.json').read_text())
 supplementary=json.loads((base/'calibration/supplementary_review.json').read_text()) if (base/'calibration/supplementary_review.json').exists() else {}
 availability={'selected_directory':selection['directory'],'initial_valid':baseline.get('valid_generated_answers',0),'initial_processed':baseline.get('processed_cases',38),'retry_valid':answer.get('valid_generated_answers',0),'retry_processed':answer.get('processed_cases',0),'cache_hits':answer.get('valid_answers_from_cache',0),'fresh_valid':answer.get('valid_answers_fresh',0),'model':'gemini-3.1-flash-lite'}
 calibration=refresh();docs=load_corpus();approved=sum(d.review_status=='approved' for d in docs)
 r=retr['summaries']['hybrid_rerank'];n=r['n_answerable'];valid=answer.get('valid_generated_answers',sum(x['generation'].get('valid',False) for x in records))
 unknown={'value':None,'n':None,'script':None}
 score={'week':3,'test_set_size':38,'e2e_accuracy':dict(unknown),
        'abstention_correct':answer.get('abstention_correct',dict(unknown)),
        'unsupported_claims':answer.get('unsupported_claims',dict(unknown)),
        'hit_at_5':{'value':r['hit_at_k']['5'],'n':n,'script':'eval/retrieval_week3.py'},
        'mrr':{'value':r['mrr_at_10'],'n':n,'script':'eval/retrieval_week3.py','cutoff':10},
        'task_success':dict(unknown),'pass_k':{'k':None,'value':None,'n':None,'script':None},'injection_success':dict(unknown),
        'cost_per_task_usd':None,'latency_p50_s':answer.get('latency_p50_s'),'spend_week_usd':None,'spend_total_usd':None}
 (base/'scoreboard.json').write_text(json.dumps(score,ensure_ascii=False,indent=2)+'\n')
 statuses={f'W3.{i}':{'status':'done','note':''} for i in range(1,9)}
 statuses['W3.4']={'status':'done' if valid==38 and answer.get('abstention_correct',{}).get('value')==1 else 'partial','note':f'Cited-answer code and fixed fallback tested; {valid}/{len(records)} valid saved responses, with cached/fresh provenance; service failures recorded.'}
 statuses['W3.6']={'status':'done' if answer.get('faithfulness',{}).get('valid_judged_claims',0)>0 and calibration.get('n',0)>0 else 'partial','note':f'Claim support measured; {calibration.get("n",0)} matched human–judge pairs, {calibration["human_labels_completed"]} original human labels. Limited single-reviewer agreement does not establish judge accuracy.'}
 successes=[x for x in records if x['generation'].get('valid')]
 tr=next((x for x in successes if x['case_id']=='W3-R019'),next((x for x in successes if x['lang']=='tr'),successes[0] if successes else {}))
 en=next((x for x in successes if x['lang']=='en'),{})
 first_evidence=((tr.get('generation') or {}).get('claims') or [{}])[0].get('evidence',[{}])[0]
 evidence_source=next((x for x in tr.get('sources',[]) if x['citation']==first_evidence.get('citation')), {})
 demo={'question_tr':tr.get('question','Kiracıyım, su aboneliği için hangi belgeler gerekiyor?'),'question_en':en.get('question','What documents do I need for a water subscription as a tenant?'),
       'answer':(tr.get('generation') or {}).get('answer','Generation unavailable: HTTP503; no fabricated reply.'),
       'source_excerpt':((tr.get('generation') or {}).get('claims') or [{}])[0].get('evidence',[{}])[0].get('quote',''), 'source_label':evidence_source.get('passage_id',''),
       'abstain_question':'No authorized source was supplied (software contract check).','abstain_answer':json.loads((ROOT/'config/rag_answer.json').read_text())['fallback']['en'],
       'run_label':'Recorded Gemini 3.1 response / 24 Nov 2026'}
 failures={'generation':{'question':'Gemini3.1 live availability','answer':f'Initial run: {baseline["valid_generated_answers"]}/{baseline["processed_cases"]}. Selected recovery: {valid}/{len(records)} valid saved responses ({availability["cache_hits"]} cached, {availability["fresh_valid"]} fresh in that pass). Earlier errors remain recorded.', 'diagnosis':'Provider/validation failures; distinct from retrieval misses and unsupported-claim estimates.'},'evaluation':{'title':'Check what the cited source actually supports.','detail':'A contact detail may be valid if its authorized source provides it. Invented contacts, unperformed actions and instructions embedded in documents still fail the evidence check.'}}
 data={'status_date':'2026-11-24','tests_passed':json.loads((base/'qa_summary.json').read_text())['tests_passed'],'deliverables':statuses,'scoreboard':score,'availability':availability,'human_review':{'supplementary_review_completed':supplementary.get('assistant_completed',0), 'approved_documents':approved,'total_documents':len(docs),'claim_labels_completed':calibration['human_labels_completed'],'claim_labels_target':20,'observed_agreement':calibration.get('po'),'matched_human_judge_pairs':calibration.get('n',0),'automatic_claim_labels':calibration.get('valid_automatic_claim_labels',0),'calibration_status':calibration.get('status'),'calibration_origin':'Historical model claims; current evidence assigned post hoc; not current-RAG accuracy.','kappa':calibration.get('kappa')},'product':{'interviews_completed':2,'summary':'2/2 interviews completed (Beyaz Masa supervisor & municipal IT coordinator): need cited FAQ checklists, local ACL-filtered RAG, and confirmation-gated writes.'},'demo':demo,'generation':{'summary':f'{valid}/{len(records)} valid saved answers; cached and fresh calls distinguished.','unsupported_claims':score['unsupported_claims']['value'],'claims_total':answer.get('faithfulness',{}).get('valid_judged_claims',0),'kappa':calibration.get('kappa'),'errors':len(records)-valid},'failures':failures}
 (base/'presentation_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 report=f'''# Weekly report

| Field | Value |
|---|---|
| Team | Beldesk |
| Use case | Instructor-approved fictional Yeşilvadi bilingual municipal assistant |
| Week | 3 |
| Repository | https://github.com/efmaster04/AI390 |
| Working branch | week3 |
| Commit tag | week-3 planned; not created |
| Presenter | Efe İncirci, Doruk Kal, Tarık Edip Yenikomşu; contiguous three-speaker split |
| Members and roles | Efe: agent/tools; Doruk: data/retrieval; Tarık: evaluation/safety |

## 1. Summary

We implemented local hybrid retrieval over 31 synthetic documents, source-cited bilingual answers, fixed no-evidence fallbacks, a claim-level judge, human-review tooling and two retrieval ablations. Hybrid+reranker hit@5 is {r['hit_at_k']['5']:.4f} on 32 answerable questions, MRR@10 {r['mrr_at_10']:.4f}. Live Gemini 3.1 availability limited answer/judge measurements: {valid}/{len(records)} processed cases have valid saved answers (cached/fresh origin recorded). These are separate retrieval, availability and faithfulness measurements. Human calibration uses its actual matched sample with limitations, and we completed two customer discovery interviews with municipal citizen-relations and IT stakeholders.

## 2. Deliverables

| ID | Status | Evidence | Note |
|---|---|---|---|
| W3.1 | done | data/corpus/documents/; manifest.json | 30 public guides +1 staff-only fixture; metadata/source/version/access; {approved}/31 human-reviewed, other authored drafts disclosed. |
| W3.2 | done | src/rag/chunking.py; retrieval/chunks.json | 92 section-aware chunks. 140-word cap/20 overlap only for long sections; actual current overlap zero. |
| W3.3 | done | src/rag/lexical.py; models.py; retrieval.py | BM25+dense, RRF60, pinned local cross-encoder; access filter before ranking. |
| W3.4 | {statuses['W3.4']['status']} | src/rag/answer.py; prompts/rag/v1.md; {selection['directory']}/records.jsonl | Numbered valid source references, exact quote validation, fixed TR/EN fallback; live coverage, controls and service failures are measured in the selected run. |
| W3.5 | done | week3_retrieval.jsonl; eval/retrieval_week3.py | 32 answerable questions, 6 extra controls; draft gold passages/quotes; 6 development cases separate. |
| W3.6 | {statuses['W3.6']['status']} | eval/faithfulness_week3.py; calibration/ | Claim judge and blind review implemented. {calibration['human_labels_completed']} human labels; {calibration.get('n',0)} matched judge pairs; κ={calibration.get('kappa')}; target20 planned. Historical claims with post-hoc assigned evidence, not current-RAG accuracy. |
| W3.7 | done | retrieval/summary.json | Dense vs hybrid with reranking fixed; reranker off with hybrid fixed. |
| W3.8 | done | retrieval/failures.json; {selection['directory']}/failures.json | Retrieval, generation/provider and evaluation failures separated. |

## 3. Scoreboard

```json
{json.dumps(score,ensure_ascii=False,indent=2)}
```

Retrieval denominator is32; unavailable-information controls excluded. Answer records have their own denominator. Missing model judgements are not zero unsupported claims. Actual billing is unknown; existing dated list-price assumptions are separate. E2E answer adequacy was not measured and remains null. Reported latency is retrieval plus generation service time, excluding scheduling/backoff waits; it is not end-user wall time. Previous Week2 accuracy is not directly comparable to Week3 hit@5. Draft source/gold status limits generalization.

Changes to any test set this week: new Week3 set; Week1/2 preserved. Twelve evidence quote anchors were clarified during draft development; question texts and passage IDs stayed unchanged and every retrieval variant was rerun. No test-driven model-setting change is hidden.

## 4. Experiments

### Experiment 1: Dense versus hybrid retrieval

- **Hypothesis:** BM25 adds exact-term matches to dense retrieval.
- **Change:** Dense candidates versus BM25+dense RRF; same corpus, queries,20-candidate pool and reranker.
- **Result:** Both hit@5 31/32 (0.96875), MRR@10 0.953125; no observed quality advantage on this draft set.
- **Uncertainty:** Wilson95% interval for31/32 is approximately0.843–0.994. The paired hit@5 comparison with dense has no discordant cases (p=1). See retrieval/paired_statistics.json.
- **Decision:** Retain required hybrid implementation; do not claim superiority. This is one small synthetic paired set, not established statistical superiority.

### Experiment 2: Reranker off

- **Hypothesis:** Pairwise reranking promotes relevant evidence.
- **Change:** Only reranker off, same hybrid retrieval and pool.
- **Result:** hit@1 23/32 without versus30/32 with; hit@5 30/32 versus31/32; MRR@10 0.8046875 versus0.953125. Warm local retrieval time is reported in summary.json, excluding model load and generation.
- **Uncertainty:** Exact paired McNemar tests and Wilson intervals are saved in retrieval/paired_statistics.json. These are exploratory tests on draft synthetic labels.
- **Decision:** Keep reranker for this configuration; report its additional compute. No universal claim follows from this small draft experiment.

### Experiment 3: Live source-grounded answering and claim judging

- **Hypothesis:** Structured claims and citation validation permit grounded answers and measured faithfulness.
- **Change:** New Week3 prompt/validator and independent source-support judge; Gemini3.1 retained at the user's direction despite503 errors.
- **Result:** {valid}/{len(records)} valid saved answers; {availability['cache_hits']} historical cached and {availability['fresh_valid']} fresh successes. The provisional judge flagged {answer.get('unsupported_claims',{}).get('numerator')}/{answer.get('unsupported_claims',{}).get('n')} claims as unsupported or insufficient. Missing verdicts remain unavailable; full transport events are checkpointed.
- **Diagnosis:** A real minimal request returned503 `UNAVAILABLE` with the provider’s high-demand message; see provider_diagnosis.json. [Google’s retry guidance](https://aistudio.google.com/docs/troubleshooting#retry-strategy) recommends exponential backoff with jitter.
- **Decision:** Complete generation attempts before judging, then retry only transient errors with exponential backoff, jitter and bounded budgets. Preserve successful stage caches and the original run separately. No fallback model was silently substituted.
- **Availability provenance:** Initial run {baseline['valid_generated_answers']}/{baseline['processed_cases']}; selected run `{selection['directory']}` {valid}/{len(records)}. Historical cache successes and fresh outputs are recorded per stage; this is an operational retry comparison, not a randomized quality experiment.
- **Review provenance:** Doruk entered {calibration['human_labels_completed']} labels. The separate supplementary review preserves his entries and does not complete the human-label denominator. Only matched real human labels enter Cohen’s κ: current matched denominator n={calibration.get('n',0)}, automatic historical claim verdicts={calibration['valid_automatic_claim_labels']}, κ={calibration.get('kappa')}, observed agreement={calibration.get('po')}. This purposefully selected historical stress set has post-hoc assigned evidence; it does not measure current-RAG accuracy. These are single-reviewer labels awaiting independent adjudication; agreement is descriptive rather than judge validation.

## 5. Failure analysis

| # | Input | What happened | Root cause | Fix |
|---|---|---|---|---|
| 1 | W3-R008: identity/upload requirement | Designated privacy passage missed20-candidate pool. | retrieval | Keep failure; future improvements on separate development questions. |
| 2 | W3-R010, no-reranker variant | Fee-record-fields passage below top5. | retrieval | Reranking promoted it in measured configuration. |
| 3 | Initial Gemini calls |503/timeouts prevented answers or judge verdicts. | generation/provider or evaluation | Bounded retries, generation-first pass and stage-cache recovery; original errors retained. |
| 4 | Historical claim calibration | Human–judge agreement is limited (κ={calibration.get('kappa')}, n={calibration.get('n',0)}). | evaluation/reference disagreement | Inspect source support and label definitions; independent adjudication needed before claiming judge accuracy. |

## 6. Response to last week's feedback

The team reports generally positive Week2 feedback with no specific requested correction. We implemented the Week3 requirements and retained the earlier judge-validity caveat instead of inventing feedback.

## 7. Product track

**Completed: 2/2 customer discovery interviews** ([docs/product_interviews_week3.md](../docs/product_interviews_week3.md)). We interviewed a municipal Citizen Relations (Beyaz Masa) Desk Supervisor (`INT-W3-01`) and a Municipal IT & Digital Services Coordinator (`INT-W3-02`). Today, a 6-person desk handles ~350–450 daily inquiries across phone, web forms, and WhatsApp by manually checking PDF guides and copying field complaints into spreadsheets, while out-of-sync department guides cause citizens to arrive with missing documents. They would pay for a predictable monthly institutional subscription ($150–$300/month per desk or an on-premise/VPC license) that delivers source-cited FAQ checklists (`[1]`), local role-filtered retrieval (`public` vs `staff`), and pre-triaged P1–P4 complaint drafts. Their main AI fears are fabricated fees or crew arrival times, unconfirmed ticket creation promises, and KVKK/privacy leaks of third-party tickets or staff-only notes.

## 8. Contributions

| Member | Role | Work and evidence | Hours |
|---|---|---|---|
| Doruk Kal | Data/retrieval | Directed implementation, selected local retrieval, reviewed water guide and entered13human labels; corpus and experiments prepared with Codex. | Not recorded |
| Efe İncirci | Agent/tools | Assigned agent/tools review area; source-cited answer pipeline and integration checks prepared in this AI-assisted draft, individual review pending. | Not recorded |
| Tarık Edip Yenikomşu | Evaluation/safety | Assigned evaluation/safety review area; claim judge, harness and review tooling prepared in this AI-assisted draft, individual review pending. | Not recorded |

## 9. AI tools used

| Tool | Used for |
|---|---|
| Codex main agent and subagents | Corpus drafts, retrieval, generation/judge implementation, tests, report, matching local HTML deck. |
| Pinned multilingual E5 and cross-encoder | Real local embeddings/reranking, no inference API charge. |
| Gemini3.1Flash-Lite | Actual answer/judge attempts; successful outputs and errors recorded separately. |

## 10. Next week

| Priority | Metric it should move | Expected change |
|---|---|---|
| Review label disagreements and expand the human reference | Matched human–judge pairs; descriptive κ | From {calibration.get('n',0)} matched pairs toward20; no promised κ. |
| Add controlled lookup and sandbox writes with confirmation | Validated tool-result rate | From unmeasured to measured on explicit sandbox cases. |
| Measure multi-step tasks with traces and limits | task_success | From null to measured, with failures and cost evidence. |
'''
 (ROOT/'reports/week-3.md').write_text(report)
 print('Built local report, scoreboard and presentation data.')
if __name__=='__main__':build()
