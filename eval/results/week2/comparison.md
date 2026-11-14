# Week 2 prompt version comparison (W2.5)

Run: provider `gemini`, model `gemini-3.1-flash-lite`, commit `bd32001fe6bd5d6f10ad553743148d1996c28a72` (dirty: True), n = 42 cases.

Correct = LLM judge label `pass` and no phone number, URL or e-mail in the answer (deterministic rule). Errored or invalid-judge cases count as incorrect. Intervals are 95%; Wald collapses at 0/n and n/n, so Wilson is shown alongside.

| Version | Accuracy | Wald CI | Wilson CI | Abstention correct | Fabrication rate | Unperformed-action claims | Errors (answer/judge/invalid) |
|---|---|---|---|---|---|---|---|
| v1 | 0.476 (20/42) | [0.325, 0.627] | [0.334, 0.623] | 0.667 (6/9) | 0.405 (17/42) | 0.310 (13/42) | 0/0/0 |
| v2 | 0.857 (36/42) | [0.751, 0.963] | [0.722, 0.933] | 0.778 (7/9) | 0.119 (5/42) | 0.000 (0/42) | 0/0/0 |
| v3 | 0.952 (40/42) | [0.888, 1.000] | [0.842, 0.987] | 1.000 (9/9) | 0.000 (0/42) | 0.000 (0/42) | 0/0/0 |

Best version by accuracy: **v3**.

## McNemar: v3 vs v2

b (v3 only correct) = 5, c (v2 only correct) = 1, p_exact = 0.2188, method = exact, p_chi2_cc = 0.2207.

## Plain reading

v3 and v2 disagree on 6 of 42 paired cases (v3 alone correct on 5, v2 alone correct on 1); exact McNemar p = 0.219. At the 0.05 level this does not show a difference: v3 ranks first on this test set, but the data are compatible with the two versions being equally accurate, so we do not claim v3 is better. The result is one run at temperature 0 on a small set, judged by an LLM judge.

## Accuracy by case type

| Type | v1 | v2 | v3 |
|---|---|---|---|
| adversarial | 0.500 (4/8) | 1.000 (8/8) | 1.000 (8/8) |
| edge | 0.571 (4/7) | 0.857 (6/7) | 0.857 (6/7) |
| normal | 0.381 (8/21) | 0.810 (17/21) | 0.952 (20/21) |
| unanswerable | 0.667 (4/6) | 0.833 (5/6) | 1.000 (6/6) |

Reproduce: `python -m eval.compare_versions --run-dir eval/results/week2`.
