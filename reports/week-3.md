# Weekly report

| Field | Value |
|---|---|
| Team | Beldesk |
| Use case | Custom, instructor-approved: bilingual (TR/EN) municipal citizen assistant for the fictional Yeşilvadi Municipality |
| Week | 3 |
| Repository | https://github.com/efmaster04/AI390 (branch `week3`; audit fixes on `week3-fixes`) |
| Commit tag | week-3 (not created yet; the team tags the final commit) |
| Presenter | TBD (team to fill) |
| Members and roles | Doruk Kal (data and retrieval lead); Efe İncirci (agent and tools lead); Tarık Edip Yenikomşu (evaluation and safety lead) |

## 1. Summary

We added retrieval-augmented answers over a synthetic citizen-service corpus (citizen-v2: 31 documents, 92 chunks) with hybrid search, a local reranker, numbered citations and a fixed refusal. Most important number: hit@5 = 1.00 (32/32, 95% CI 0.89–1.00), but only 31/32 questions had every required facet in the top 5. Gemini produced 36/38 valid answers; the judge marked 1/90 claims unsupported. An audit corrected the claim-rate definition and one stage label.

## 2. Deliverables

| ID | Status | Evidence | Note |
|---|---|---|---|
| W3.1 | done | [`data/corpus/documents/`](../data/corpus/documents/); [`data/corpus/manifest.json`](../data/corpus/manifest.json); [`data/corpus/review_log.jsonl`](../data/corpus/review_log.jsonl); [`src/rag/corpus.py`](../src/rag/corpus.py) | 31 synthetic documents (30 public guides, 1 staff-only access fixture) with source, date, version and access metadata. Approved: 31/31 documents and 38/38 test cases (Doruk Kal and Tarık Edip Yenikomşu, 2026-11-24), recorded after the evaluation run on unchanged content. |
| W3.2 | done | [`src/rag/chunking.py`](../src/rag/chunking.py); [`eval/results/week3/retrieval/chunks.json`](../eval/results/week3/retrieval/chunks.json) | 92 section-aware chunks; 140-word cap with 20-word overlap only for long sections. |
| W3.3 | done | [`src/rag/retrieval.py`](../src/rag/retrieval.py); [`src/rag/lexical.py`](../src/rag/lexical.py); [`config/retrieval.json`](../config/retrieval.json) | BM25 plus `multilingual-e5-small` dense search, reciprocal rank fusion (k = 60), local cross-encoder reranker; access filtering before ranking. |
| W3.4 | partial | [`src/rag/answer.py`](../src/rag/answer.py); [`prompts/rag/v1.md`](../prompts/rag/v1.md); [`config/rag_answer.json`](../config/rag_answer.json); [`eval/results/week3/answers_citizen_v2_complete/`](../eval/results/week3/answers_citizen_v2_complete/) | 36/38 valid citizen-v2 responses (first pass 35/38); 5/6 unavailable-information controls returned the fixed refusal. |
| W3.5 | done | [`eval/testsets/week3_retrieval.jsonl`](../eval/testsets/week3_retrieval.jsonl); [`eval/testsets/week3_citizen_v2_manifest.json`](../eval/testsets/week3_citizen_v2_manifest.json); [`docs/week3_benchmark_revision.md`](../docs/week3_benchmark_revision.md) | 32 answerable questions (16 TR / 16 EN) and 6 controls (3 TR / 3 EN) with exact evidence quotes; 6 separate development cases. |
| W3.6 | done | [`eval/faithfulness_week3.py`](../eval/faithfulness_week3.py); [`prompts/judge/week3_v1.md`](../prompts/judge/week3_v1.md); [`eval/results/week3/calibration/human_calibration.json`](../eval/results/week3/calibration/human_calibration.json) | Claim-level judge on current answers; κ = 0.771 on 20 historical claims (see limitation in section 4). |
| W3.7 | done | [`eval/retrieval_week3.py`](../eval/retrieval_week3.py); [`eval/rescore_retrieval_week3.py`](../eval/rescore_retrieval_week3.py); [`eval/results/week3/retrieval/rescored_summary.json`](../eval/results/week3/retrieval/rescored_summary.json); [`eval/results/week3/retrieval/paired_statistics.json`](../eval/results/week3/retrieval/paired_statistics.json) | Two one-change retrieval ablations on the frozen set. |
| W3.8 | done | [`eval/results/week3/retrieval/failures.json`](../eval/results/week3/retrieval/failures.json); [`eval/results/week3/answers_citizen_v2_complete/failures.json`](../eval/results/week3/answers_citizen_v2_complete/failures.json) | Failures labelled retrieval, generation or evaluation (section 5). |

## 3. Scoreboard

```json
{
  "week": 3,
  "test_set_size": 38,
  "e2e_accuracy": {
    "value": null,
    "ci95": null,
    "n": null,
    "script": null
  },
  "abstention_correct": {
    "value": 0.8333,
    "ci95": [
      0.4365,
      0.9699
    ],
    "n": 6,
    "script": "eval/answer_week3.py --recompute-only --out-dir eval/results/week3/answers_citizen_v2_complete"
  },
  "unsupported_claims": {
    "value": 0.0111,
    "ci95": [
      0.002,
      0.0603
    ],
    "n": 90,
    "script": "eval/answer_week3.py --recompute-only --out-dir eval/results/week3/answers_citizen_v2_complete (eval/faithfulness_week3.py)"
  },
  "hit_at_5": {
    "value": 1.0,
    "ci95": [
      0.8928,
      1.0
    ],
    "n": 32,
    "script": "eval/retrieval_week3.py (rankings) -> eval/rescore_retrieval_week3.py"
  },
  "mrr": {
    "value": 0.7589,
    "n": 32,
    "script": "eval/retrieval_week3.py (rankings) -> eval/rescore_retrieval_week3.py"
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
  "cost_per_task_usd": 0.001043,
  "latency_p50_s": 4.72,
  "spend_week_usd": 0.0,
  "spend_total_usd": 0.0
}
```

Values come from [`eval/results/week3/scoreboard.json`](../eval/results/week3/scoreboard.json), written by `python -m scripts.build_week3_report` from recorded artefacts without model calls. Intervals are Wilson 95% (`eval/stats.py`).

- `e2e_accuracy` is null because no answer-correctness rubric was applied to the citizen-v2 answers; claim support is not question completion, and Week 2's 0.952 was measured on a different test set.
- `abstention_correct`: 5/6 unavailable-information controls returned the fixed refusal; W3-U004 answered instead (section 5).
- `unsupported_claims`: metric definition corrected after audit. The judge had labelled the fixed refusal of W3-R032 as an unsupported claim, although its rubric excludes fixed refusals. Validated fixed refusals now contribute zero claims: 2/91 (0.022) became 1/90 (0.011). 1 answer (W3-R020) had no valid judgement, so its 4 claims are not in the denominator:

| Case | Claim | Text (not judged) |
|---|---|---|
| W3-R020 | C1 | You can report a pothole by providing the neighborhood, street, or avenue, the direction of the damage, and a nearby landmark. |
| W3-R020 | C2 | When reporting the pothole, you should describe observations such as vehicles swerving to avoid it, narrowed passage, or near-miss incidents. |
| W3-R020 | C3 | Include the time you observed the incident and specify whether the damage is at a single point or extends along the road. |
| W3-R020 | C4 | Providing a photograph can assist in identifying the location of the damage. |

- `hit_at_5` and `mrr` (MRR@10) use the 32 answerable questions. They were re-scored offline from the recorded rankings, reproducing the recorded metrics exactly. The rankings came from a working tree with uncommitted changes at `22577a6` (`"dirty": true`), so a clean rerun with the local models is still open.
- Answers: first pass 35/38 valid (no validation retry). Only the 3 invalid cases were retried once with one validation retry; 1 recovered, giving 36/38. This retry was chosen after seeing failures, so 35/38 is the same-policy figure. The 35 retained answers are first-pass calls, not cache hits.
- `cost_per_task_usd` is a list-price estimate (Week 2 convention): answer-generation tokens per case at the dated Gemini 3.1 Flash-Lite list price (USD 0.25 input / 1.50 output per million tokens, checked 2026-11-09); judge and local retrieval excluded. All recorded generation and judge calls together are equivalent to $0.0752 (a lower bound: usage of 3 failed transport attempts is unknown). Actual spend is $0 (free tier); `spend_total_usd` adds Weeks 1 and 2, also $0.
- `latency_p50_s`: median retrieval plus answer-generation service time over the 36 valid answers; excludes the classifier, the judge and rate-limit waits; not end-user wall time.
- Provenance: the runs read the files frozen with review status draft. Commit `576ef4b` later set the review fields to approved. `eval/week3_provenance.py` shows that restoring those fields reproduces the evaluated hashes exactly, so the measured content is unchanged.

Changes to any test set this week: new Week 3 set citizen-v2 (38 cases) replaced the first v1 draft before scoring ([`docs/week3_benchmark_revision.md`](../docs/week3_benchmark_revision.md)); after scoring, only review metadata changed.

## 4. Experiments

| Configuration | hit@1 | hit@5 (95% CI) | all-facet@5 | MRR@10 |
|---|---:|---:|---:|---:|
| Hybrid + reranker (default) | 0.594 | 1.000 (0.89–1.00) | 0.969 | 0.759 |
| Dense + reranker | 0.594 | 1.000 (0.89–1.00) | 0.969 | 0.761 |
| Hybrid, no reranker | 0.531 | 0.906 (0.76–0.97) | 0.875 | 0.689 |

### Experiment 1: Dense versus hybrid candidate retrieval

- **Hypothesis:** Lexical BM25 candidates add useful evidence to dense retrieval.
- **Change:** Candidate retrieval only (dense versus hybrid); corpus, questions, 20-candidate budget and reranker fixed.
- **Result:** hit@5 1.000 for both (n = 32); MRR@10 hybrid 0.7589, dense 0.7615. hit@1 paired McNemar: 0 versus 0 discordant, exact p = 1.00.
- **Decision:** Investigate further; no detectable difference on 32 synthetic questions. Hybrid stays the configured default.

### Experiment 2: Reranker off

- **Hypothesis:** Cross-encoder reranking moves required evidence into the top 5.
- **Change:** Reranking only, with hybrid retrieval fixed.
- **Result:** hit@5 0.906 (29/32, CI 0.76–0.97) without versus 1.000 with; MRR@10 0.6893 versus 0.7589. hit@5 discordant pairs 3 versus 0, exact p = 0.25; hit@1 6 versus 4, p = 0.75.
- **Decision:** Keep the reranker; all hit@5 discordant pairs favour it, but the difference is not significant at n = 32.

### Experiment 3: Judge check against human labels

- **Hypothesis:** The claim judge agrees with a human reviewer on source support.
- **Change:** 20 human labels, adjudicated by the evaluation and safety lead, compared with the judge's labels.
- **Result:** agreement 0.85, κ = 0.771 (n = 20).
- **Decision:** Use the judge provisionally. Limitation: κ was measured on earlier v1 (historical) model claims, with evidence assigned afterwards and samples chosen purposively, not on the citizen-v2 answers behind `unsupported_claims`.

## 5. Failure analysis

| # | Input (short) | What happened | Root cause | Fix (done or planned) |
|---|---|---|---|---|
| 1 | W3-R032: fair permit in a park plus an inaccessible entrance (two facets) | Permit evidence `YV-D006#details` ranked 7; the model saw the top 5 and returned the fixed refusal. | retrieval | Done: stage attribution now requires every facet (it was labelled generation). Proposed (team to confirm): a one-change multi-facet retrieval experiment; all-facet@5 is 31/32. |
| 2 | W3-U004: request for a neighbour's phone number from their complaint | Answered with a cited privacy statement instead of the fixed refusal; nothing disclosed, but the contract broke. | generation | Proposed (team to confirm): decide whether a privacy denial counts as refusal, then enforce it in prompt or code and re-measure `abstention_correct`. |
| 3 | W3-R019, W3-R027: accessibility report; street-lamp follow-up | Quotes were not exact substrings of the source after one retry; no answer shown. | generation | Existing: shown as an error, not counted as a refusal. Proposed (team to confirm): better quote-validation feedback, measured as valid answers out of 38. |

Also observed: W3-R017 contains one unsupported library-membership claim (generation). W3-R020 got invalid judge output, so its claims stay unjudged (evaluation). The judge's verdict on a fixed refusal was an evaluation-definition error, corrected in section 3.

## 6. Response to last week's feedback

| Feedback point | What we changed | Evidence |
|---|---|---|
| Instructor feedback on Week 2 | Not recorded in the repository. | TBD (team to fill) |
| Review of the first Week 3 draft: meta-questions and developer instructions mixed into the citizen benchmark | Rewrote the public guides and all answerable questions; moved internal cases out of citizen scoring; archived v1 results. | [`docs/week3_benchmark_revision.md`](../docs/week3_benchmark_revision.md); [`eval/testsets/week3_internal_policy_cases.jsonl`](../eval/testsets/week3_internal_policy_cases.jsonl) |
| Audit of the Week 3 branch: stale hashes, claim-rate definition, R032 stage, scoreboard fields, report contradictions | Restored the evaluated hashes with a metadata-only proof; corrected the metric and stage; added intervals and scripts; derived approvals from data. | Branch `week3-fixes`; [`eval/week3_provenance.py`](../eval/week3_provenance.py) |

## 7. Product track

Two team-recorded discovery interviews are preserved in [`docs/product_interviews_week3.md`](../docs/product_interviews_week3.md): a citizen-relations desk supervisor and an IT coordinator. Their recorded needs are cited FAQ checklists, controlled intake drafts, local access-filtered retrieval and confirmation before writes. Concerns include invented fees or arrival promises, privacy leakage and uncontrolled actions. No pricing evidence was collected.

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
