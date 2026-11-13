# Week 2 Prompt Version Comparison (W2.5)

## 1. Accuracy and 95% Confidence Intervals (n = 40)

| Version | JSON Validity | Intent Accuracy (95% CI) | Urgency Accuracy (95% CI) | Abstention Correct (n=8, 95% CI) | End-to-End Accuracy (n=40, 95% CI) | Mean In/Out Tokens | List USD / 1,000 | p50 Latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `v1` | 1.00 (40/40) | 0.72 [0.59, 0.86] | 0.72 [0.59, 0.86] | 0.38 [0.04, 0.71] | **0.20** [0.08, 0.32] (8/40) | 661.9 / 334.4 | $0.6672 | 8.8683 |
| `v2` | 1.00 (40/40) | 0.90 [0.81, 0.99] | 1.00 [1.00, 1.00] | 0.88 [0.65, 1.00] | **0.30** [0.16, 0.44] (12/40) | 721.9 / 224.7 | $0.5175 | 2.5184 |
| `v3` | 1.00 (40/40) | 0.97 [0.93, 1.00] | 0.97 [0.93, 1.00] | 1.00 [1.00, 1.00] | **0.95** [0.88, 1.00] (38/40) | 3402.8 / 239.9 | $1.2106 | 5.6408 |

## 2. Paired McNemar Tests

| Comparison | Both Pass ($n_{11}$) | A Only ($n_{10}$) | B Only ($n_{01}$) | Both Fail ($n_{00}$) | $\Delta$ Accuracy (B - A) | McNemar $\chi^2$ | $\chi^2_{\text{cc}}$ | Exact Binomial $p$-value | Significant ($p < 0.05$) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `v2_vs_v3` | 12 | 0 | 26 | 2 | +0.6500 | 26.0000 | 24.0385 | 0.000000 | Yes |
| `v1_vs_v3` | 8 | 0 | 30 | 2 | +0.7500 | 30.0000 | 28.0333 | 0.000000 | Yes |
| `v1_vs_v2` | 7 | 1 | 5 | 27 | +0.1000 | 2.6667 | 1.5000 | 0.218750 | No |

## 3. Paired TR/EN Token Comparison on 6 Matched Pairs (`v3`, PF-01)

| Pair ID | EN Case | TR Case | EN Input Tokens | TR Input Tokens | TR - EN | TR / EN Ratio |
|---|---|---|---:|---:|---:|---:|
| `pair_jurisdiction` | W2-32 | W2-31 | 3394 | 3399 | +5 | 1.0015 |
| `pair_p1_signal` | W2-29 | W2-30 | 3391 | 3398 | +7 | 1.0021 |
| `pair_p4_bench` | W2-27 | W2-26 | 3395 | 3399 | +4 | 1.0012 |
| `pair_ticket_status` | W1-10 | W1-07 | 3400 | 3407 | +7 | 1.0021 |
| `pair_vip_grass` | W2-38 | W2-37 | 3417 | 3432 | +15 | 1.0044 |
| `pair_water_sub` | W1-02 | W1-03 | 3381 | 3387 | +6 | 1.0018 |

Mean difference across 6 pairs: **7.33 tokens** (mean ratio: **1.0022**).
