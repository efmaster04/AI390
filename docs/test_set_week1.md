# Week 1 Test Set — User Inputs (W1.3)

## Purpose

This test set contains 25 realistic, labeled user inputs for evaluating Beldesk, a bilingual (Turkish + English) AI assistant for the fictional Yeşilvadi Municipality. Each input is tagged with the category it tests and the handbook ingredients (section 10) it exercises. The set is used in W1.5 (baseline evaluation) and subsequent weekly iterations.

## Revision v2: two translation pairs inside the same 25 inputs

Only W1-03 and W1-07 user texts were replaced. The active set remains **25 inputs: 13 Turkish and 12 English**. Four entries now form two matched translation pairs; the other 21 entries are not part of the paired comparison. No additional 25-input test set was created.

| Pair | English entry | Turkish entry | Controlled content |
|---|---|---|---|
| Water subscription | W1-02 | W1-03 | Same question and fictional municipality |
| Ticket status | W1-10 | W1-07 | Same question, ticket YV-2026-011532 and phone suffix 2274 |

**Pair 1 — EN:** What documents do I need to apply for a water subscription in Yeşilvadi?

**Pair 1 — TR:** Yeşilvadi’de su aboneliğine başvurmak için hangi belgelere ihtiyacım var?

**Pair 2 — EN:** Can you check the status of ticket YV-2026-011532? Last 4 of my phone: 2274.

**Pair 2 — TR:** YV-2026-011532 numaralı kaydın durumunu kontrol edebilir misiniz? Telefonumun son 4 hanesi: 2274.

The saved 75 responses in `eval/results/week1` belong to v1, whose exact inputs remain in Git at the commit recorded in run metadata. They must not be paired with the changed v2 messages. Rerun all 25 v2 inputs at three temperatures before updating result claims (R9).

For a small illustrative input-token comparison, use only these two pairs, the same model and system prompt, and one temperature. Input tokens include the shared system prompt and request framing. Do not pool all 13 TR and 12 EN messages as if their meanings were matched. Output-token differences also depend on generated content and are not a pure tokenization comparison. Two pairs cannot establish a general language-wide effect.

## Distribution: Category × Language

| Category         | Turkish (tr) | English (en) | Total |
|------------------|:---:|:---:|:---:|
| question         | 3   | 3   | **6**  |
| lookup           | 2   | 2   | **4**  |
| action           | 3   | 2   | **5**  |
| unanswerable     | 2   | 2   | **4**  |
| multi_step       | 2   | 1   | **3**  |
| untrusted        | 1   | 2   | **3**  |
| **Total**        | **13** | **12** | **25** |

## Ingredient Coverage

Every ingredient from handbook section 10 is exercised by at least 2 inputs.

| # | Ingredient           | Input IDs                                           | Count |
|---|----------------------|-----------------------------------------------------|:-----:|
| 1 | Documents            | W1-01, 02, 03, 04, 05, 06                           | 6     |
| 2 | Structured data      | W1-04, 06, 07, 08, 09, 10, 20, 21, 22, 25           | 10    |
| 3 | Action               | W1-11, 12, 13, 14, 15, 20, 21, 22, 23, 24           | 10    |
| 4 | Untrusted input      | W1-23, 24, 25                                        | 3     |
| 5 | Must not answer      | W1-16, 17, 18, 19, 22, 25                            | 6     |
| 6 | Multi-step tasks     | W1-20, 21, 22                                        | 3     |
| 7 | Exact identifiers    | W1-07, 09, 10, 13, 21, 22                            | 6     |
| 8 | Request classifier   | All 25                                               | 25    |

## Labeling Rules

1. **`category`** — Primary test purpose. One of: `question`, `lookup`, `action`, `unanswerable`, `multi_step`, `untrusted`.
2. **`ingredients`** — Array of integers (1–8) referencing handbook section 10. Ingredient 8 (request classifier) applies to every input because all messages must be routed.
3. **`expected_urgency`** — `"P1"` through `"P4"` when the described condition can be classified; `null` for questions, lookups, unanswerable cases, untrusted inputs with no legitimate ticket action, and incomplete complaints such as W1-22.
4. **`expected_behavior`** — English, 1–2 sentences describing the ideal assistant response.
5. **`lang`** — `"tr"` for Turkish, `"en"` for English. Reflects the primary language of the user message.
6. **Realism** — Inputs include deliberate typos, missing punctuation, mixed register, angry tone, and incomplete information to simulate real citizen messages.
7. **Untrusted inputs** — Prompt injections target only the Beldesk assistant. They do not contain instructions aimed at evaluators, graders, or external tools.
8. **Synthetic data only** — All names, ticket IDs (`YV-YYYY-NNNNNN`), phone digits, and addresses are fictional. No real personal data is used.

The canonical P1–P4 criteria and response targets are defined in [Use Case Brief, “Urgency rubric”](use_case_brief.md#urgency-rubric). The distribution below was counted from the 25 JSONL records after label corrections.

| Expected urgency | Inputs |
|------------------|-------:|
| P1 | 1 |
| P2 | 4 |
| P3 | 4 |
| P4 | 0 |
| `null` | 16 |

## Limitations

- The set covers all 8 ingredients but is small (n = 25); statistical conclusions about category-level accuracy require larger sets in later weeks.
- The [urgency rubric](use_case_brief.md#urgency-rubric) assigns one failed lamp to P3 and a street- or neighborhood-wide outage to P2. W1-22 has `null` urgency because the citizen has not described their own problem yet.
- Multi-language inputs (code-switching within a single message) are not explicitly represented; all messages are predominantly single-language.
- The untrusted inputs test three injection styles (system tag, curly-brace command, HTML comment); other vectors (e.g., Unicode tricks, base64 encoding) are deferred to red-teaming in week 5.

## Known gaps

- No P4 example appears in this fixed 25-input Week 1 set. Add a P4 example and a P3/P4 boundary case to the 40-case Week 2 set.
- v2 contains two matched TR/EN pairs. Their new token counts have not been measured yet; extend paired coverage in Week 2 before generalizing.
