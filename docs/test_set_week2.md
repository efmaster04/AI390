# Week 2 Test Set — Cases with Expected Outputs (W2.3)

**File:** `eval/testsets/week2_cases.jsonl` (42 cases, one JSON object per line).
**Contract:** `config/case_labels.json` (contract v2) defines every field, allowed value and rule; it is the single source of truth. Urgency labels follow priority policy **v0.3-draft** (`docs/priority_policy.md`, decisions in `docs/priority_policy_decisions.md`).

## Contract v2 (short)

- `id` W2-001…W2-042; `source_id` = W1-xx for carried-over cases (W2-001…025 keep the Week 1 text byte-identical), else `null`.
- `lang` (tr/en/mixed), `type` (normal/unanswerable/adversarial/edge), `ingredients` (brief ingredients 1–8), `text` (citizen message, verbatim).
- `expected`: primary `intent`, `secondary_intents`, `issues`, `ticket_id`, `missing_fields`.
  - `issues` is non-empty **iff** `field_complaint` is the primary or a secondary intent. Each distinct fault is one issue (a two-fault message has two issues).
  - Each issue: `category`, `urgency` (P1–P4, or `null` **iff** `urgency_status` is `needs_clarification` because the incident itself is unclear), `location` (`neighborhood`, `street`, `detail` such as a parcel or landmark; `null` when nothing is stated), `scope` (single_point/partial/street/area/unknown), `onset_text` (verbatim duration phrase or `null`), `sensitive_use` (only when the text explicitly connects one, e.g. a school route), `referral_needed` (yes/no/unknown; the model never names the other body).
  - `missing_fields`: what the assistant should ask for (`location`, `issue_details`, `scope`, `onset`, `ticket_id`, `contact_last4`). Missing location never nulls urgency.
  - An `emergency` without a field complaint has no issues; the answer directs to 112 first.
- `expected_behavior`: 1–2 English sentences on the correct answer; ambiguous labels state the reason there.
- `answerable`: `false` when the honest answer is "can't answer / out of scope / not in the documents" (always `false` for type `unanswerable`).
- `review`: `status` (pending/approved/changed), `reviewer`, `note`, `updated_at`.

Facts are never invented: `scope`, `onset_text` and `sensitive_use` stay `unknown`/`null` when the text does not state them. They are extracted for the Week 4 queue ordering (decision 9).

## Counts

| Dimension | Counts |
|---|---|
| type | normal 21 · adversarial 8 · edge 7 · unanswerable 6 |
| lang | tr 21 · en 20 · mixed 1 |
| intent (primary) | field_complaint 18 · faq 11 · status_inquiry 7 · out_of_scope 5 · emergency 1 |
| issues per case | 0 22 · 1 19 · 2 1 |
| issue urgency | P1 3 · P2 4 · P3 11 · P4 2 · null 1 |
| issue category | street_lighting 5 · roads_sidewalks 4 · parks_green 3 · water_sewer 3 · waste_collection 2 · other 2 · noise_environment 1 · animals 1 |
| issue scope | single_point 13 · street 4 · unknown 2 · area 1 · partial 1 |
| referral_needed | no 20 · unknown 1 |
| missing_fields | location 3 · issue_details 2 · ticket_id 1 |
| review status | pending 24 · approved 17 · changed 1 |

42 cases, 21 issues. Regenerate the table with:

```
.venv/bin/python -c "import json,collections as C;R=[json.loads(l) for l in open('eval/testsets/week2_cases.jsonl')];I=[i for r in R for i in r['expected']['issues']];[print(k,dict(C.Counter(v))) for k,v in [('type',[r['type'] for r in R]),('lang',[r['lang'] for r in R]),('intent',[r['expected']['intent'] for r in R]),('issues per case',[len(r['expected']['issues']) for r in R]),('urgency',[i['urgency'] for i in I]),('category',[i['category'] for i in I]),('scope',[i['scope'] for i in I]),('referral',[i['referral_needed'] for i in I]),('missing',[m for r in R for m in r['expected']['missing_fields']]),('review',[r['review']['status'] for r in R])]]"
```

New cases (W2-026…042) add P4 complaints, a P1 open manhole and fallen tree, noise and animal complaints, unanswerable questions (mayor's salary, crew arrival time, weather), adversarial cases (urgency inflation, persona jailbreak, system-prompt leak, fake staff asking for a phone number, injection inside a complaint) and edge cases (single word, TR/EN mix, emoji-only with no location, long rambling message, two faults in one message, malformed ticket ID, a person collapsing who needs 112).

## Migration to v2

The 42 cases were human-reviewed under contract v1 (flat `category`/`urgency`/`location`). The migration moved those labels into `issues` and applied the annotation fixes decided with policy v0.3-draft (W2-014, 015, 017, 018, 023, 039, 040, 041). Cases that were fixed or received AI-drafted new content (scope, onset, sensitive use, referral, location detail, missing fields, new issues for W2-021/022) are back to `pending`, with a `v2:` prefix in the review note describing the change. Cases with only the mechanical move kept their status.

## Review rule

The expected outputs were **drafted by an AI** and are not ground truth until a human reviews them. Each case must be marked `approved` or `changed` on the review page (`.venv/bin/python -m tools.review.server`) before the set is used for scoring. `tests/test_week2_cases.py` checks only the format, vocabulary and contract rules, not whether the labels are correct.
