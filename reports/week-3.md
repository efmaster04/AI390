# Weekly report

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

We implemented local hybrid retrieval over 31 synthetic documents, source-cited bilingual answers, fixed no-evidence fallbacks, a claim-level judge, human-review tooling and two retrieval ablations. Hybrid+reranker hit@5 is 0.9688 on 32 answerable questions, MRR@10 0.9531. Live Gemini 3.1 availability limited answer/judge measurements: 38/38 processed cases have valid saved answers (cached/fresh origin recorded). These are separate retrieval, availability and faithfulness measurements. Human calibration uses its actual matched sample with limitations, and we completed two customer discovery interviews with municipal citizen-relations and IT stakeholders.

## 2. Deliverables

| ID | Status | Evidence | Note |
|---|---|---|---|
| W3.1 | done | data/corpus/documents/; manifest.json | 30 public guides +1 staff-only fixture; metadata/source/version/access; 1/31 human-reviewed, other authored drafts disclosed. |
| W3.2 | done | src/rag/chunking.py; retrieval/chunks.json | 92 section-aware chunks. 140-word cap/20 overlap only for long sections; actual current overlap zero. |
| W3.3 | done | src/rag/lexical.py; models.py; retrieval.py | BM25+dense, RRF60, pinned local cross-encoder; access filter before ranking. |
| W3.4 | done | src/rag/answer.py; prompts/rag/v1.md; answers_retry_v3/records.jsonl | Numbered valid source references, exact quote validation, fixed TR/EN fallback; live coverage, controls and service failures are measured in the selected run. |
| W3.5 | done | week3_retrieval.jsonl; eval/retrieval_week3.py | 32 answerable questions, 6 extra controls; draft gold passages/quotes; 6 development cases separate. |
| W3.6 | done | eval/faithfulness_week3.py; calibration/ | Claim judge and human calibration completed: 20/20 adjudicated human labels; 20 matched judge pairs; κ=0.7710 (observed agreement 0.85). Historical claims with post-hoc assigned evidence, not current-RAG accuracy. |
| W3.7 | done | retrieval/summary.json | Dense vs hybrid with reranking fixed; reranker off with hybrid fixed. |
| W3.8 | done | retrieval/failures.json; answers_retry_v3/failures.json | Retrieval, generation/provider and evaluation failures separated. |

## 3. Scoreboard

```json
{
  "week": 3,
  "test_set_size": 38,
  "e2e_accuracy": {
    "value": null,
    "n": null,
    "script": null
  },
  "abstention_correct": {
    "value": 1.0,
    "n": 6,
    "numerator": 6,
    "definition": "valid fixed-fallback response on unavailable-information controls"
  },
  "unsupported_claims": {
    "value": 0.0,
    "n": 61,
    "numerator": 0,
    "definition": "unsupported plus insufficient_evidence divided by valid judged claims, including unlisted claims"
  },
  "hit_at_5": {
    "value": 0.96875,
    "n": 32,
    "script": "eval/retrieval_week3.py"
  },
  "mrr": {
    "value": 0.953125,
    "n": 32,
    "script": "eval/retrieval_week3.py",
    "cutoff": 10
  },
  "task_success": {
    "value": null,
    "n": null,
    "script": null
  },
  "pass_k": {
    "k": null,
    "value": null,
    "n": null,
    "script": null
  },
  "injection_success": {
    "value": null,
    "n": null,
    "script": null
  },
  "cost_per_task_usd": null,
  "latency_p50_s": 2.521084417006932,
  "spend_week_usd": null,
  "spend_total_usd": null
}
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
- **Result:** 38/38 valid saved answers; 36 historical cached and 2 fresh successes. The provisional judge flagged 0/61 claims as unsupported or insufficient. Missing verdicts remain unavailable; full transport events are checkpointed.
- **Diagnosis:** A real minimal request returned503 `UNAVAILABLE` with the provider’s high-demand message; see provider_diagnosis.json. [Google’s retry guidance](https://aistudio.google.com/docs/troubleshooting#retry-strategy) recommends exponential backoff with jitter.
- **Decision:** Complete generation attempts before judging, then retry only transient errors with exponential backoff, jitter and bounded budgets. Preserve successful stage caches and the original run separately. No fallback model was silently substituted.
- **Availability provenance:** Initial run 2/38; selected run `answers_retry_v3` 38/38. Historical cache successes and fresh outputs are recorded per stage; this is an operational retry comparison, not a randomized quality experiment.
- **Review provenance:** Doruk completed the initial 13 labels; Evaluation & Safety Lead (Tarık) adjudicated all 20 items (`human_sheet.csv`), correcting 4 initial errors (`W3-H03`, `W3-H04`, `W3-H06`, `W3-H07`) where claims absent from or refuted by the source had been marked `supported`, and completing the remaining 7 items (`W3-H14`..`W3-H20`). On the completed matched denominator n=20/20 (3-class rubric: `supported`, `insufficient_evidence`, `unsupported`), Cohen’s κ is **0.7710** with observed agreement **0.85** (17/20 exact matches; the 3 disagreements are `W3-H03` and `W3-H13` where human selected `insufficient_evidence` vs judge `unsupported`, plus compound-claim `W3-H18`). This retrospective stress set has post-hoc assigned evidence and does not measure current-RAG accuracy.

## 5. Failure analysis

| # | Input | What happened | Root cause | Fix |
|---|---|---|---|---|
| 1 | W3-R008: identity/upload requirement | Designated privacy passage missed 20-candidate pool. | retrieval | Keep failure; future improvements on separate development questions. |
| 2 | W3-R010, no-reranker variant | Fee-record-fields passage below top 5. | retrieval | Reranking promoted it in measured configuration. |
| 3 | Initial Gemini calls | 503/timeouts prevented answers or judge verdicts. | generation | Bounded retries, generation-first pass and stage-cache recovery; original errors retained. |
| 4 | Historical claim calibration (`W3-H03`, `W3-H13`, `W3-H18`) | 3 residual borderline disagreements (`insufficient_evidence` vs `unsupported`/compound claim) after fixing 4 initial human-labeling errors (κ=0.7710, n=20). | evaluation | Completed 20/20 human adjudication; refine compound-claim boundary in Week 4 judge prompt. |

## 6. Response to last week's feedback

The team reports generally positive Week 2 feedback with no specific requested correction. We implemented the Week 3 requirements and completed 20/20 adjudicated claim-level human calibration (κ=0.7710).

## 7. Product track

**Completed: 2/2 customer discovery interviews** ([docs/product_interviews_week3.md](../docs/product_interviews_week3.md)). We interviewed a municipal Citizen Relations (Beyaz Masa) Desk Supervisor (`INT-W3-01`) and a Municipal IT & Digital Services Coordinator (`INT-W3-02`). Today, a 6-person desk handles ~350–450 daily inquiries across phone, web forms, and WhatsApp by manually checking PDF guides and copying field complaints into spreadsheets, while out-of-sync department guides cause citizens to arrive with missing documents. They would pay for a predictable monthly institutional subscription ($150–$300/month per desk or an on-premise/VPC license) that delivers source-cited FAQ checklists (`[1]`), local role-filtered retrieval (`public` vs `staff`), and pre-triaged P1–P4 complaint drafts. Their main AI fears are fabricated fees or crew arrival times, unconfirmed ticket creation promises, and KVKK/privacy leaks of third-party tickets or staff-only notes.

## 8. Contributions

| Member | Role | Work and evidence | Hours |
|---|---|---|---|
| Doruk Kal | Data/retrieval | Directed implementation, selected local retrieval, reviewed water guide (`YV-D003`) and entered initial 13 human labels; corpus (`data/corpus/`) and retrieval experiments (`eval/retrieval_week3.py`). | 10 |
| Efe İncirci | Agent/tools | Source-cited answer pipeline (`src/rag/answer.py`, `prompts/rag/v1.md`), deterministic fallback contract, and integration checks (`tests/test_rag_answer.py`). | 9 |
| Tarık Edip Yenikomşu | Evaluation/safety | Claim-level judge calibration (`eval/faithfulness_week3.py`, `eval/results/week3/calibration/human_sheet.csv`: adjudicated all 20/20 labels, κ=0.7710), product track customer discovery interviews (`docs/product_interviews_week3.md`), and Week 3 report/deck updates. | 10 |

## 9. AI tools used

| Tool | Used for |
|---|---|
| Codex main agent and subagents | Corpus drafts, retrieval, generation/judge implementation, tests, report, matching local HTML deck. |
| Pinned multilingual E5 and cross-encoder | Real local embeddings/reranking, no inference API charge. |
| Gemini 3.1 Flash-Lite | Actual answer/judge attempts; successful outputs and errors recorded separately. |

## 10. Next week

| Priority | Metric it should move | Expected change |
|---|---|---|
| Add controlled lookup and sandbox writes with confirmation | task_success | From null to measured on >=10 explicit multi-step sandbox tasks. |
| Connect Week 2 classifier to Week 3 RAG and Week 4 tools | e2e_accuracy | From null in Week 3 back to measured end-to-end accuracy with 95% CI. |
| Calibrate judge on live Week 4 tool-backed answers and compound claims | unsupported_claims | Keep unsupported_claims near 0.0 with adjudicated human–judge agreement. |
