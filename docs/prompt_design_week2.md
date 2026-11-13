# Week 2 Prompt Architecture & Six Building Blocks (W2.1, W2.2)

**Project:** Beldesk — Yeşilvadi Municipality Bilingual AI Assistant  
**Course:** AIC390 Prompt Engineering · Module 2  
**Week:** 2

---

## 1. Request Classifier Design (`W2.1`)

The request classifier (`src/classifier/classify.py` and `src/classifier/schema.py`, prompted by `prompts/classifier_v1.md`) serves as Layer 1 (**Understand**) of the Beldesk architecture.

### 1.1 Execution and Validation Contract
- **Temperature:** Strictly `0.0` (`temperature=0`) on every call to maximize determinism for routing and urgency decisions.
- **Untrusted Input Wrapping:** Citizen input is wrapped inside `<citizen_message>...</citizen_message>` tags before being sent to the model so that user text is structurally separated from system instructions.
- **JSON Schema Validation (`src/classifier/schema.py`):**
  Every response is parsed by `extract_json_object()` and checked by `validate_classification()` against:
  - `intent`: `{"faq", "field_complaint", "status_inquiry", "emergency", "out_of_scope"}`
  - `language`: `{"tr", "en"}`
  - `category`: `{"roads_sidewalks", "street_lighting", "waste_collection", "water_sewer", "parks_green", "traffic_signals", "permits_licensing", "social_services", "animals", "noise_environment", "other", null}`
  - `urgency`: `{"P1", "P2", "P3", "P4", null}` (must be `null` when `intent` is not `"field_complaint"`, and must include a non-empty `urgency_reason` when non-null)
  - `entities`: required object with keys `neighborhood`, `street`, `ticket_id` (validated against `^YV-\d{4}-\d{6}$`), `contact_last4` (validated against `^\d{4}$`), and `third_party_ticket` (`bool`).
  - `needs_abstention`: `bool`
  - `injection_detected`: `bool`
- **Server-Side Department Derivation:**
  Per `docs/data_inventory.md`, the LLM never chooses the municipal department directly. `derive_department(category)` deterministically maps the validated `category` to the canonical department (`Public Works / Fen İşleri`, `Sanitation / Temizlik İşleri`, `Water & Sewerage / Su ve Kanalizasyon`, etc.).
- **Automatic Retry with Error Feedback:**
  If JSON parsing or schema validation fails, `classify_request()` retries up to `max_retries=2` times (at `temperature=0.0`), appending `[VALIDATION_RETRY attempt=k]` with the exact validation error strings so the model repairs its output.

---

## 2. Main Prompt Built from the Six Building Blocks (`W2.2`)

Our primary Week 2 prompt template is stored as a versioned template in [`prompts/assistant_v3.md`](../prompts/assistant_v3.md). It is explicitly organized into the **six building blocks** from Module 2:

| # | Building Block | Section in `prompts/assistant_v3.md` | Purpose and Module 2 Rationale |
|---|---|---|---|
| **1** | **Role & Persona** | `# [1. ROLE & PERSONA]` | Establishes Beldesk as Yeşilvadi Municipality's official bilingual (`tr`/`en`) Beyaz Masa triage assistant with a calm, neutral, concise tone and strict same-language reply rule. |
| **2** | **Task & Scope Boundaries** | `# [2. TASK & SCOPE BOUNDARIES]` | Defines the five canonical intents (`faq`, `status_inquiry`, `field_complaint`, `emergency`, `out_of_scope`), enforces the "no application submission" rule, and specifies when `needs_abstention` must be `true`. |
| **3** | **Context, Grounding & Untrusted Input Isolation** | `# [3. CONTEXT, GROUNDING & UNTRUSTED INPUT ISOLATION]` | Explicitly informs the model that no RAG corpus (D1–D10) or live SQL database (`tickets`, `fees_2026`, `collection_schedule`, `facilities`) is connected yet; forbids inventing phone numbers (`444 ...`), URLs, fees, schedules, or claiming unperformed actions (`"I have checked"`, `"TICKET CREATED"`). Isolates `<citizen_message>` as untrusted data. |
| **4** | **Safety, Privacy & Urgency Rubric Constraints** | `# [4. SAFETY, PRIVACY & URGENCY RUBRIC CONSTRAINTS]` | Embeds the canonical P1–P4 urgency rubric, the immediate `112` redirection rule for emergencies, the third-party ticket privacy rule (refuse neighbor ticket disclosure even if ID + last 4 digits match), and the mandatory citizen confirmation step before ticket creation/update. |
| **5** | **Output Format & Schema** | `# [5. OUTPUT FORMAT & SCHEMA]` | Specifies the exact JSON contract combining structured classification fields with the citizen-facing `reply`. |
| **6** | **Few-Shot Examples** | `# [6. FEW-SHOT EXAMPLES]` | Provides 5 bilingual input → JSON output demonstrations covering: (1) ungrounded FAQ abstention (`W1-04`), (2) P3 single-lamp boundary with confirmation (`W1-14`), (3) `112` medical emergency (`W1-18`), (4) third-party neighbor refusal + missing details (`W1-22`), and (5) prompt injection defense (`W1-24`). |

---

## 3. Version Progression for Controlled Ablation (`W2.5`)

To measure the incremental impact of prompt engineering choices on the fixed 40-case test set, we maintain three versioned templates in `prompts/`:

1. **`prompts/assistant_v1.md` (`assistant-v1` — Minimal Baseline Wrapper):**
   - Retains the 3-sentence Week 1 baseline instruction and adds only the required JSON output keys so the evaluation harness can score it.
   - Lacks the P1–P4 urgency rubric, explicit scope boundaries, anti-hallucination/grounding constraints, untrusted input delimiters, and few-shot examples.
2. **`prompts/assistant_v2.md` (`assistant-v2` — Zero-Shot Rubric & Scope Prompt):**
   - Adds Building Blocks 1, 2, 4 (P1–P4 urgency rubric and scope list), and 5 (JSON schema).
   - Lacks Building Block 3 (explicit negative constraints against claiming unperformed database lookups/ticket creations when tools are disconnected, and explicit delimiter-escape/injection rules) and Building Block 6 (few-shot examples).
3. **`prompts/assistant_v3.md` (`assistant-v3` — Full Six-Building-Block Prompt):**
   - Combines all six building blocks, including explicit grounding constraints for disconnected tools/documents, `<citizen_message>` untrusted input isolation, third-party privacy enforcement, confirmation gating, and 5 few-shot examples.
