# Week 1 Test Set — User Inputs (W1.3)

## Purpose

This test set contains 25 realistic, labeled user inputs for evaluating Beldesk, a bilingual (Turkish + English) AI assistant for the fictional Yeşilvadi Municipality. Each input is tagged with the category it tests and the handbook ingredients (section 10) it exercises. The set is used in W1.5 (baseline evaluation) and subsequent weekly iterations.

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
| 2 | Structured data      | W1-06, 07, 08, 09, 10, 20, 21, 25                   | 8     |
| 3 | Action               | W1-11, 12, 13, 14, 15, 20, 21, 22, 23, 24           | 10    |
| 4 | Untrusted input      | W1-23, 24, 25                                        | 3     |
| 5 | Must not answer      | W1-16, 17, 18, 19, 22, 25                            | 6     |
| 6 | Multi-step tasks     | W1-20, 21, 22                                        | 3     |
| 7 | Exact identifiers    | W1-07, 09, 10, 13, 21, 22                            | 6     |
| 8 | Request classifier   | All 25                                               | 25    |

## Labeling Rules

1. **`category`** — Primary test purpose. One of: `question`, `lookup`, `action`, `unanswerable`, `multi_step`, `untrusted`.
2. **`ingredients`** — Array of integers (1–8) referencing handbook section 10. Ingredient 8 (request classifier) applies to every input because all messages must be routed.
3. **`expected_urgency`** — `"P1"` through `"P4"` for inputs that should result in a ticket; `null` for questions, lookups, unanswerable cases, and untrusted inputs with no legitimate ticket action.
4. **`expected_behavior`** — English, 1–2 sentences describing the ideal assistant response.
5. **`lang`** — `"tr"` for Turkish, `"en"` for English. Reflects the primary language of the user message.
6. **Realism** — Inputs include deliberate typos, missing punctuation, mixed register, angry tone, and incomplete information to simulate real citizen messages.
7. **Untrusted inputs** — Prompt injections target only the Beldesk assistant. They do not contain instructions aimed at evaluators, graders, or external tools.
8. **Synthetic data only** — All names, ticket IDs (YV-2026-NNNNNN), phone digits, and addresses are fictional. No real personal data is used.

## Limitations

- The set covers all 8 ingredients but is small (n = 25); statistical conclusions about category-level accuracy require larger sets in later weeks.
- Street lighting rule added to the urgency rubric: a single lamp out = P3; a street- or neighborhood-wide outage = P2.
- Urgency boundary cases (e.g., P2 vs. P3 for lighting outages) are subjective; the `expected_urgency` reflects the team's best-effort interpretation of the rubric and may be revised after instructor feedback.
- Multi-language inputs (code-switching within a single message) are not explicitly represented; all messages are predominantly single-language.
- The untrusted inputs test three injection styles (system tag, curly-brace command, HTML comment); other vectors (e.g., Unicode tricks, base64 encoding) are deferred to red-teaming in week 5.
