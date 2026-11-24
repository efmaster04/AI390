# Weekly report

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
| W3.1 | done | 31 cleaned documents, source/date/version/access metadata; 0/31 current explicit human approvals. Rewritten guides reset to draft. |
| W3.2 | done | 92 section-aware chunks;140-word cap,20-word overlap only for long sections; actual overlap zero. |
| W3.3 | done | BM25+dense, RRF60, pinned local E5 and cross-encoder; public/staff filtering before ranking. |
| W3.4 | partial | 36/38 valid current responses; numbered references, quote validation and fixed TR/EN no-evidence response. |
| W3.5 | done | 32answerable questions(16TR/16EN),6controls(3TR/3EN), exact evidence;6separate dev cases. |
| W3.6 | done | Claim support measured on current answers;20human labels against preserved v1 source snapshots; κ=0.771. |
| W3.7 | done | Two one-change retrieval ablations on the frozen citizen-v2 set. |
| W3.8 | done | Full misses and missing facets labelled retrieval; unsupported outputs/provider failures separated as generation/provider; judge failures separate. |

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
    "value": 0.8333333333333334,
    "n": 6,
    "numerator": 5,
    "definition": "valid fixed-fallback response on unavailable-information controls"
  },
  "unsupported_claims": {
    "value": 0.02197802197802198,
    "n": 91,
    "numerator": 2,
    "definition": "unsupported plus insufficient_evidence divided by valid judged claims, including unlisted claims"
  },
  "hit_at_5": {
    "value": 1.0,
    "n": 32,
    "script": "eval/retrieval_week3.py"
  },
  "mrr": {
    "value": 0.7588541666666667,
    "n": 32,
    "cutoff": 10,
    "script": "eval/retrieval_week3.py"
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
  "latency_p50_s": 4.72438522905577,
  "spend_week_usd": null,
  "spend_total_usd": null
}
```

Retrieval denominator:32. Hit@k finds at least one required answer facet; all-facet@5 requires every requested facet. Alternatives within a facet were registered before scoring, not added after misses. Three questions need multiple passages; two span services. Answer availability is not semantic correctness; E2E adequacy remains unmeasured. Model claim judgements are provisional. Latency excludes scheduling/backoff waits; actual billing is unknown. v1 and v2 are different benchmarks, so their percentages are not a like-for-like improvement claim.

## 4. Experiments

| Configuration | hit@1 | hit@5 | all-facet@5 | MRR@10 |
|---|---:|---:|---:|---:|
| Hybrid + reranker | 0.594 | 1.000 | 0.969 | 0.759 |
| Dense + reranker | 0.594 | 1.000 | 0.969 | 0.761 |
| Hybrid, no reranker | 0.531 | 0.906 | 0.875 | 0.689 |

**Ablation1 — dense versus hybrid.** Hypothesis: lexical matching adds useful candidates. Change only candidate retrieval; keep corpus, questions,20-candidate budget and reranker fixed. Hybrid MRR=0.7589; dense=0.7615. Report the observed result without asserting hybrid superiority. Exact paired tests and Wilson intervals: `retrieval/paired_statistics.json`. Hybrid hit@5 Wilson95% interval: approximately0.893–1.000.

**Ablation2 — reranker off.** Hypothesis: reranking promotes useful evidence. Change only reranking with hybrid fixed. MRR=0.6893 without versus0.7589 with; hit@5=0.906 versus1.000. This small, synthetic draft set does not establish universal superiority.

**Current answering and faithfulness.** Gemini3.1Flash-Lite remains unchanged,T=0. The run contains 36/38 valid responses, with 1 fresh successes and 35 cache hits within citizen-v2. No v1 stage cache was copied. A bounded repair pass may replace only originally invalid generations; successful citizen-v2 stages remain recorded and are not selected by semantic score. Judge-labelled unsupported/insufficient claims: 2/91. Valid answer-level judgements: 35/36; missing judgements do not count as supported claims. This is source-support estimation, not complete-answer accuracy. Current source/question hashes must match the frozen manifest before report generation.

**Historical judge check.** Preserve the team's20adjudicated human labels and real judge verdicts. Agreement=0.850, κ=0.771,n=20. These are purposefully selected historical model claims with v1 evidence assigned afterward. They check the source-support rubric, not manual accuracy of new citizen-v2 answers. A small retrospective calibration does not by itself validate the current claim-rate estimate.

## 5. Failure analysis

Observed retrieval case: **W3-R032**, variant `hybrid_rerank`. A required answer facet is missing from top 5. Missing evidence: `YV-D006#details`. gold_in_candidates_but_below_top5. Finding one relevant passage does not cover every requested part; all-facet@5 = 0.969.

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
