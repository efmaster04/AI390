# Week 2 Test Set — 40 Labeled Evaluation Cases (W2.3)

**File:** [`eval/testsets/week2_cases.jsonl`](../eval/testsets/week2_cases.jsonl)  
**Generator:** [`scripts/build_week2_testset.py`](../scripts/build_week2_testset.py)

---

## 1. Overview and Longitudinal Continuity (Rule R9)

The Week 2 evaluation set expands the 25-case Week 1 v2 set (`W1-01` through `W1-25`) with 15 new synthetic cases (`W2-26` through `W2-40`), totaling **40 cases (20 Turkish, 20 English)**.

- **Preservation of Week 1 Cases:** All 25 input texts and IDs from `eval/testsets/week1_inputs.jsonl` (v2) are preserved verbatim as the first 25 records so that Week 1 vs. Week 2 comparisons obey Rule R9.
- **Addressed Week 1 Gaps:**
  1. Added **4 explicit `P4` cases** (`W2-26`, `W2-27`, `W2-37`, `W2-38`) and a **`P3`/`P4` boundary case** (`W2-28`, loosened/rusted playground swing chain).
  2. Expanded matched Turkish/English translation pairs from 2 pairs (4 cases) to **6 matched pairs (12 cases)** across FAQ, status lookup, P4 complaint, P1 hazard, out-of-jurisdiction abstention, and adversarial VIP urgency inflation.

---

## 2. Distribution by Case Type (`case_type`) and Language

Handbook deliverable **W2.3** requires at least 40 cases with **at least 5 unanswerable, 5 adversarial, and 5 edge cases**.

| `case_type` | Turkish (`tr`) | English (`en`) | Total | Requirement |Case IDs |
|---|:---:|:---:|:---:|:---:|---|
| `standard` | 8 | 9 | **17** | — | `W1-01..12, 15, 20`; `W2-29, 30, 40` |
| `unanswerable` | 4 | 4 | **8** | $\ge 5$ ✅ | `W1-16, 17, 18, 19`; `W2-31, 32, 33, 34` |
| `adversarial` | 3 | 4 | **7** | $\ge 5$ ✅ | `W1-23, 24, 25`; `W2-35, 36, 37, 38` |
| `edge` | 5 | 3 | **8** | $\ge 5$ ✅ | `W1-13, 14, 21, 22`; `W2-26, 27, 28, 39` |
| **Total** | **20** | **20** | **40** | $\ge 40$ ✅ | `W1-01..25`, `W2-26..40` |

---

## 3. Distribution by Expected Intent and Urgency

| Expected Intent | Count | Expected Urgency | Count |
|---|---:|---|---:|
| `field_complaint` | 20 | `P1` (4h immediate hazard) | 3 (`W1-15, W2-29, W2-30`) |
| `faq` | 6 | `P2` (24h high-impact / injury risk) | 6 (`W1-12, 13, 23, 24, W2-40`) |
| `status_inquiry` | 5 | `P3` (72h routine repair) | 7 (`W1-11, 14, 20, 21, W2-28, 36, 39`) |
| `out_of_scope` | 8 | `P4` (7d cosmetic / suggestion) | 4 (`W2-26, 27, 37, 38`) |
| `emergency` | 1 (`W1-18`) | `null` (non-complaint or incomplete `W1-22`) | 20 |
| **Total** | **40** | **Total** | **40** |

---

## 4. Six Matched TR/EN Translation Pairs (`PF-01` Controlled Token Comparison)

To evaluate **PF-01 (Turkish agglutinative morphology token inflation)** without confounding request content, 12 of the 40 cases form **6 exact semantic pairs**:

| Pair ID | Category / Type | English Case | Turkish Case | Controlled Content |
|---|---|---|---|---|
| `pair_water_sub` | `faq` (`standard`) | `W1-02` | `W1-03` | Water subscription document requirements in Yeşilvadi |
| `pair_ticket_status` | `status_inquiry` (`standard`) | `W1-10` | `W1-07` | Status check for `YV-2026-011532` with phone last 4 `2274` |
| `pair_p4_bench` | `field_complaint` (`edge`, `P4`) | `W2-27` | `W2-26` | Peeling paint on usable wooden bench in Çınarlık Park |
| `pair_p1_signal` | `field_complaint` (`standard`, `P1`) | `W2-29` | `W2-30` | Pedestrian traffic signal stuck on green for cars at Atatürk Ave school crossing |
| `pair_jurisdiction` | `out_of_scope` (`unanswerable`) | `W2-32` | `W2-31` | Request for Yeşilvadi crew to collect garbage in neighboring Mavikent Municipality |
| `pair_vip_grass` | `field_complaint` (`adversarial`, `P4`) | `W2-38` | `W2-37` | Deputy Mayor `VIP-01` roleplay demanding `P1` without confirmation for overgrown park grass |
