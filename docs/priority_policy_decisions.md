# Priority policy — decision log (v0.2 → v0.3)

Decisions taken by **Efe on 2026-11-13** with Claude; they **still need confirmation by Doruk and Tarık**. Questions came from an independent Codex review, Claude and Efe. Result: [v0.3 draft](priority_policy.md); original: [v0.2](priority_policy_v0.2_original.md).

## Decisions

### D1. Does problem duration raise the priority class?
- **Source:** Efe (note on W2-014: "after some time it should become P2").
- **Options:** (a) keep v0.2 §5: duration orders within a class, plus a 14-day review list; (b) auto-upgrade after a threshold; (c) mandatory staff disposition at the threshold.
- **Decision:** (a).
- **Rationale:** Class reflects danger and impact, not age; auto-upgrade would let old single-light reports overtake real P2s; the test set has no timestamps.
- **Affected cases:** W2-014.

### D2. Are road or sidewalk defects with concretely described injury risk P2?
- **Source:** Codex (Q3).
- **Options:** (a) add "concretely described injury risk" to P2; (b) keep v0.2 (P2 only for essential-service disruption or major access loss).
- **Decision:** (a).
- **Rationale:** Otherwise W2-012 (large pothole near a school, near-miss) drops to P3; keeps the old rubric's injury-risk rationale.
- **Affected cases:** W2-012; PR-19.

### D3. Must the citizen say that people are endangered for P1?
- **Source:** Codex (Q2).
- **Options:** (a) a concretely described hazard implying exposure is enough; (b) the threat to people must be stated.
- **Decision:** (a).
- **Rationale:** Citizens should not have to explain why an open manhole is dangerous.
- **Affected cases:** W2-028, W2-040 (both stay P1).

### D4. Urgency for non-municipal emergencies
- **Source:** Codex (Q1).
- **Options:** (a) urgency null, intent `emergency`, direct to 112 first; (b) P1.
- **Decision:** (a).
- **Rationale:** Keeps municipal queue priority separate from emergency services and keeps health data out of the queue.
- **Affected cases:** W2-018.

### D5. What happens when information is missing?
- **Source:** Codex (Q4, Q5).
- **Options:** (a) assign the supported urgency, ask for a missing location separately, null only when the incident itself is ambiguous; (b) missing location → null.
- **Decision:** (a).
- **Rationale:** Location affects routing, not severity.
- **Affected cases:** W2-039 (stays P3, asks for location).

### D5b. Which requests get category-specific complaint forms?
- **Source:** Efe.
- **Options:** (a) field faults only; (b) also applications (marriage, permits); (c) decide later.
- **Decision:** (a).
- **Rationale:** Keeps the Week 1 scope (only field faults are filed). Forms with required fields come in Week 4; W2.1 gains `missing_fields` now.
- **Affected cases:** none directly.

### D6. Cosmetic defect on a usable asset: P3 or P4?
- **Source:** Codex (Q6).
- **Options:** (a) P4, adding "cosmetic defect without functional or safety impact"; (b) P3.
- **Decision:** (a).
- **Rationale:** Clear boundary: usable → P4, unusable → P3.
- **Affected cases:** W2-026 (stays P4); PR-20.

### D7. Two faults in one message
- **Source:** Codex (Q7).
- **Options:** (a) separate issues list; (b) primary issue only.
- **Decision:** (a).
- **Rationale:** Different faults need different categories, priorities, forms and departments.
- **Affected cases:** W2-041; PR-21.

### D7b. Sewage overflowing onto the street
- **Source:** Codex (test-set impact on W2-041).
- **Options:** (a) P2; (b) P3.
- **Decision:** (a), added as a P2 example.
- **Rationale:** Public-health risk and serious service failure, the same class as a burst pipe flooding a road (W2-024).
- **Affected cases:** W2-041; PR-21.

### D8. Faults owned by another body (e.g. the electricity distributor)
- **Source:** Codex (Q8).
- **Options:** (a) refer **and** keep a municipal record; urgency by hazard; `referral_needed` field; the model never names the body; (b) refer only.
- **Decision:** (a).
- **Rationale:** A P1 hazard must stay visible in the municipal queue.
- **Affected cases:** W2-015; PR-22.

### D9. Implement §4–§5 ordering, the 14-day review and duplicates in Week 2?
- **Source:** Claude (building on Codex's "What to defer").
- **Options:** (a) defer to Week 4; Week 2 only extracts `scope`, `onset_text`, `sensitive_use`; (b) defer entirely; (c) do it now.
- **Decision:** (a).
- **Rationale:** W2.1 asks for intent, entities and urgency; ordering needs message timestamps and the ticket database (Week 4).
- **Affected cases:** all field complaints (new extracted fields).

### D10. How to fix the policy document
- **Source:** Claude, from Codex's repo-conflict findings.
- **Options:** (a) v0.3 draft plus this decision log, keeping v0.2 unchanged; (b) decision log only.
- **Decision:** (a).
- **Rationale:** v0.2 made three false statements: "Team-approved" status; §10's claim that the classifier builds its prompt from the file (no such code); §6's "existing clarification fields" (none exist).
- **Affected cases:** none.

## Annotation fixes (eval/testsets/week2_cases.jsonl)

- **W2-014:** P2 → P3 (D1); replace Efe's note with "Karar 1: süre sınıfı değil, P3 içi sırayı etkiler."
- **W2-015:** category `street_lighting` → `other`; P1; `referral_needed` `unknown` (D8).
- **W2-017:** decline legal advice (point to a lawyer or the bar association); direct unpermitted construction to the municipality's zoning / building-inspection unit; no petition drafting; remove "ministry"; `answerable=false`, type `unanswerable`.
- **W2-018:** `answerable=true`, type `edge` (112 redirection is a correct in-scope answer).
- **W2-023:** expected_behavior P2 → P3 (label already P3; neighbourhood-wide lighting is P3, ordered first within P3).
- **W2-039:** expected_behavior adds "ask for the location".
- **W2-040:** expected_behavior `parks_green` → `roads_sidewalks`.
- **W2-041:** two issues, `water_sewer` P2 + `street_lighting` P3; replace the broken trailing text "And learn where there is" with "ask for the exact location".

## Deferred to Week 4

Codex questions 10–12 need timestamps and the ticket database:

- **Q10:** comparisons with unknown scope/duration: unresolved or timestamp fallback? (Codex: unresolved.)
- **Q11:** "first registration": first message, draft, or confirmed ticket? (Codex: first recorded message reporting the event.)
- **Q12:** 14-day review: flag only, recorded staff disposition, or auto-promote? (Codex: recorded disposition; D1 rules out auto-promotion.)
