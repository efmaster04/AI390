# Week 2 code review (Codex) and what we did with it

Reviewer: Codex `gpt-6.1-sol`, read-only, no network, 2026-11-13, over `git diff main...week2` (src, eval, tools, tests) while the live evaluation was running. Triage by the coordinator (Claude); fixes by a Claude Opus sub-agent in commit `da49416`.

| # | Severity | Finding (Codex) | Decision | Where |
|---|---|---|---|---|
| 1 | high | `eval/run_e2e.py` cache keys do not include the provider; a dry run followed by a live run in the same out-dir could reuse synthetic results. | **Fixed** without changing cache keys: `cache/PROVIDER` marker; mismatch aborts (exit 2) unless `--reset-cache`. | `da49416` |
| 2 | high | `eval/compare_versions.py` counts a case as end-to-end correct when the judge passes even if the classifier errored. | **Not changed (deliberate).** e2e accuracy measures the main answer, which does not consume the classifier output this week; the classifier (W2.1) is reported separately with its own accuracy and CI. Stated in the report. | — |
| 3 | high | After humans edit `expected_behavior`/`answerable`, compare reuses stale judge verdicts and only sets a flag. | **Fixed**: per-row `judge_input_sha256`; compare exits non-zero on stale verdicts unless `--allow-stale`; rerunning `run_e2e` re-judges only changed cases (cache key includes the judge input). | `da49416` |
| 4 | medium | Injection runner drops an observed violation when the classifier stage errors. | **Fixed**: answer-side detectors still evaluated; classifier status recorded separately. | `da49416` |
| 5 | medium | Injection runner counts an empty answer as a failed attack. | **Fixed**: empty/non-string answer = error, excluded from the denominator. (Our live run had 18/18 non-empty answers, so its result is unaffected.) | `da49416` |
| 6 | medium | Unknown token counts become 0, under-reporting cost. | **Fixed**: kept as `None`; totals with unknown counts are `null` with `cost_incomplete: true`. | `da49416` |
| 7 | medium | Review page: two tabs on the same card can overwrite each other (no optimistic concurrency). | **Not fixed this week**: single reviewer; instruction is to use one tab. Candidate for Week 3 if more reviewers use it. | — |
| 8 | medium | Cost/spend recomputed from current `config/prices.json` and Week 1 file, so the same command can give different numbers later. | **Fixed**: prices and Week 1 spend snapshotted into `run_meta.json`. | `da49416` |

## Found afterwards by inspecting results (not by the code review)

The v1 LLM judge rewarded fabrication: in the McNemar discordant pairs, v1 answers that invented a waste-collection schedule or opening hours were labelled `pass`, while v2/v3 answers that honestly said "I don't have access" were `fail`, because several expected behaviours describe Week 3+ capabilities (documents, database, ticket tool) and the judge did not know what the system can do this week. Fix (user decision): judge prompt v2 (`prompts/judge/v2.md`) states this week's capabilities; the answer key is unchanged so Week 3 stays comparable; accuracy ties are broken by fabrication rate, then unperformed-action rate. All 126 answers were re-judged.

## Process note

Prompt versions v1–v3 (W2.2) were first assigned to an Antigravity worker (`claude-opus-4-6-thinking`); at the user's request the job was stopped before it wrote anything and reassigned to a Claude Opus 5.5 sub-agent (commit `eda831d`).
