# Week 3 citizen-service retrieval and source-cited answers

## What changed

The first benchmark mixed resident requests with developer questions about schemas, model behavior and citation validation. Some public documents also read like internal prompts. That measured a different task from answering municipal service enquiries.

The active citizen-v2 corpus now contains30public guides with ordinary application, preparation, service-routing and follow-up information; one staff-only fixture is retained for access tests. Source metadata still explicitly marks all documents as synthetic. Internal behavior rules are documented in `docs/week3_system_policy.md` and enforced in prompts/code, not retrieved as public service knowledge. No real municipal fees, official URLs, opening hours or legal deadlines were invented.

## Data and source boundaries

- Source directory: `data/corpus/documents/`; manifest records source, version, date, access, content hashes and draft status.
- All30rewritten public guides are `citizen-v2` drafts. The earlier water-guide approval remains a historical event and does not carry to edited text.
- Chunking:92section-aware chunks,140-word cap and20-word overlap only for long sections; actual overlap is zero.
- Retrieval: pinned multilingual E5-small + BM25, RRF60,20candidates, local cross-encoder reranking. Access filtering precedes both search paths.
- Public requests cannot grant a staff role. Real application authentication remains necessary before accepting any staff authorization.

## Frozen citizen benchmark

`eval/testsets/week3_retrieval.jsonl` has32answerable resident questions(16TR/16EN) plus6unavailable-information/privacy controls(3TR/3EN). Six development cases are separate. Questions were drafted independently of rankings, source coverage was checked, and the question/corpus hashes were frozen before measurement. `week3_citizen_v2_manifest.json` records that freeze.

Each `gold_groups` element is one requested answer facet. The first source in a group is canonical; remaining sources are pre-registered alternatives supporting that same facet. A relevant alternative is not an additional requirement. Three cases need multiple passages; two span services. Public source overlap was considered before scoring, not used afterward to repair misses.

- Hit@k: at least one required facet has accepted evidence within k.
- MRR@10: reciprocal rank of the first accepted evidence, capped at10.
- All-facet@5 (`all_gold_hit_at_5`): every required facet has accepted evidence within5.
- The six controls do not enter retrieval hit/MRR denominators.

## Measured citizen-v2 retrieval

| Variant | hit@1 | hit@3 | hit@5 | MRR@10 | all-facet@5 |
|---|---:|---:|---:|---:|---:|
| Hybrid + reranker | 0.59375 | 0.9375 | 1.0000 | 0.758854 | 0.96875 |
| Dense + reranker | 0.59375 | 0.96875 | 1.0000 | 0.761458 | 0.96875 |
| Hybrid, no reranker | 0.53125 | 0.84375 | 0.90625 | 0.689323 | 0.87500 |

Dense has slightly higher observed MRR here; hybrid does not demonstrate superiority. Reranking improves observed hybrid placement on this small set. Paired tests and Wilson intervals are in `eval/results/week3/retrieval/paired_statistics.json`; differences are exploratory, not universal performance claims.

**Actual incomplete-evidence case: W3-R032.** The resident asks both about permission for a park fair and an inaccessible entrance. Hybrid+reranker puts accessibility details at rank3 but event-application details at rank7. The top5contains one facet, so ordinary hit@5 passes while all-facet@5 fails. This remains a recorded retrieval failure; no gold/source edit was made after observing it.

## Generation, judging and replay

Gemini3.1Flash-Lite receives the actual public source context, not gold answers. Structured claims include source numbers and exact quotes. Code validates the structure, authorized citations and exact source quotations, then renders the answer. Exact matching establishes provenance, not semantic support. A separate claim judge checks support; it does not establish complete question coverage.

`active_answer_run.json` selects the recorded citizen-v2 run. Fresh calls use the revised source hash, so old v1 answer caches cannot pass as current responses. Service errors, invalid quotations, fixed no-evidence refusals and source-supported privacy denials are distinct outcomes. A privacy-policy denial may preserve privacy while still fail the exact fixed-fallback contract; record that distinction instead of labelling it a data leak or silently changing the control.

The classroom command is `.venv/bin/python -m scripts.try_rag`. Use `--search-only` for live local retrieval and `--replay W3-R003` for an explicitly recorded backup. Run from the repository root with the retrieval environment installed. Replay is not a live model generation.

## Historical calibration and product notes

Team updates for20human labels and2customer interviews are preserved. Judge κ≈0.771 refers to20historical claims checked against embedded v1 source snapshots, not manual grading of citizen-v2 answers. `scripts/build_week3_calibration.py` reconstructs that source version from its immutable Git ref rather than silently loading rewritten guides. Old supplementary notes remain historical only.

Old source/question versions and metrics are traceable through commit `be14fc0` and `eval/results/week3/archive/v1-meta-benchmark/`. v1 and citizen-v2 percentages are not a controlled before/after comparison. The current report and deck are rebuilt only after validating matching source/question hashes. See README for commands and `reports/week-3.md` for current answer/claim denominators.
