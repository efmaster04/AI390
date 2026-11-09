# W1.4 — Data Inventory

**Project:** Beldesk — Yeşilvadi Municipality AI Assistant  
**Course:** AIC390 Prompt Engineering · Instructor: Huseyin Ulusoy  
**Team:** Efe İncirci (Agent & Tools Lead) · Doruk Kal (Data & Retrieval Lead) · Tarık Edip Yenikomşu (Evaluation & Safety Lead)  
**Week:** 1 · Last updated: 2026-11-09

---

## (a) Document Corpus

These documents will be **written from scratch** by the team, inspired by real Turkish municipal service guides publicly available on belediye.gov.tr portals and official ministry websites. No proprietary content is copied. All text is synthetic (R10: no real personal data; custom content).

| # | Title | Language | Inspiration / Source Type | Est. Length | Serves Input Type |
|---|-------|----------|--------------------------|-------------|-------------------|
| D1 | Official Marriage Application Guide | TR + EN | Civil registry service guides (nüfus müdürlüğü rehberleri) | ~600 words | FAQ, action |
| D2 | Building Permit & Occupancy Permit — Overview | TR + EN | Construction permit guides (imar müdürlüğü rehberleri) | ~800 words | FAQ, unanswerable boundary |
| D3 | Water Subscription Application Guide | TR + EN | Water utility (İSKİ-style) service documentation | ~500 words | FAQ, action |
| D4 | Social Assistance Application Guide | TR + EN | Social services directorate guides (sosyal hizmetler) | ~600 words | FAQ, unanswerable boundary |
| D5 | Pet Registration Guide | TR + EN | Veterinary services municipal guides | ~400 words | FAQ, action |
| D6 | Event & Stand Permit Guide | TR + EN | Municipal event licensing documentation | ~500 words | FAQ, action |
| D7 | Complaint Processing & SLA Policy | TR + EN | Customer relations / white desk policy documents | ~700 words | FAQ, multi-step action |
| D8 | KVKK Privacy Notice (Data Subject Disclosure) | TR + EN | KVKK template texts (kvkk.gov.tr guidance) | ~400 words | unanswerable boundary |
| D9 | Emergency Redirect Guide | TR + EN | Municipal emergency procedures (112/110/155 routing) | ~300 words | unanswerable boundary |
| D10 | 2026 Municipal Fee Schedule | TR + EN | Annual fee tariff bulletins (belediye meclis kararları) | ~500 words (table) | look-up, FAQ |

**License note:** All documents above are authored by the team for this project. Public municipal websites are used only as inspiration for structure and topics; we check each source's terms of use and do not reproduce third-party text.

---

## (b) Database Schema

The core schema below extends the draft provided in the project brief. Extensions and rationale are noted per table.

### Table: `tickets`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `ticket_id` | TEXT PK | `YV-2026-000123` | Format: `YV-YYYY-NNNNNN`; human-readable, year-scoped |
| `created_at` | DATETIME | `2026-11-09T18:34:00Z` | UTC ISO-8601 |
| `updated_at` | DATETIME | `2026-11-09T19:00:00Z` | UTC ISO-8601; AFTER UPDATE trigger refreshes it on ticket changes |
| `channel` | TEXT | `web` | Values: `web`, `whatsapp`, `phone`, `email`, `walk-in` |
| `language` | TEXT | `tr` | Values: `tr`, `en`; drives reply language |
| `category` | TEXT | `roads_sidewalks` | Values: `roads_sidewalks`, `street_lighting`, `waste_collection`, `water_sewer`, `parks_green`, `traffic_signals`, `permits_licensing`, `social_services`, `animals`, `noise_environment`, `other` |
| `department_id` | INTEGER FK | `3` | References `departments.id` |
| `neighborhood_id` | INTEGER FK | `7` | References `neighborhoods.id` |
| `street` | TEXT | `Çınar Sokak` | Free text; not FK — residents may use informal names |
| `description` | TEXT | `There is an open manhole cover...` | Raw citizen input; untrusted |
| `urgency` | TEXT | `P1` | CHECK: `P1`, `P2`, `P3`, `P4` |
| `status` | TEXT | `open` | CHECK: `open`, `in_progress`, `resolved`, `rejected` |
| `citizen_ref` | TEXT | `HASH-7f3a` | *Added:* hashed identifier (no real TC kimlik no); links repeat contacts anonymously |
| `contact_last4` | TEXT | `4821` | Last 4 digits of phone; used for ticket status lookup |
| `duplicate_of` | TEXT | `YV-2026-000119` | FK → `tickets.ticket_id`; NULL if not a duplicate |
| `staff_note` | TEXT | `Assigned to road crew` | *Added:* internal note by Beyaz Masa staff; untrusted input |
| `resolved_at` | DATETIME | `2026-11-10T10:00:00Z` | *Added:* NULL until resolved; enables SLA breach calculation |

**Rationale for additions:** `updated_at` and `resolved_at` support SLA monitoring. The canonical urgency rubric and response targets are in [Use Case Brief, “Urgency rubric”](use_case_brief.md#urgency-rubric). The separate `ticket_drafts` table defines an optional persistence schema for draft lifecycle work; the no-write draft endpoint described below uses a short-lived in-memory proposal. Only confirmed complaints enter `tickets`. `citizen_ref` links repeat contacts without storing real identity. `staff_note` is untrusted input (see section d).

### Canonical category → department routing

| Category | Department (English / Turkish) |
|----------|--------------------------------|
| `roads_sidewalks` | Public Works / Fen İşleri |
| `street_lighting` | Public Works / Fen İşleri |
| `waste_collection` | Sanitation / Temizlik İşleri |
| `water_sewer` | Water & Sewerage / Su ve Kanalizasyon |
| `parks_green` | Parks and Gardens / Park ve Bahçeler |
| `traffic_signals` | Transportation / Ulaşım |
| `permits_licensing` | Zoning & Licensing / İmar ve Ruhsat |
| `social_services` | Social Services / Sosyal Hizmetler |
| `animals` | Veterinary Services / Veteriner İşleri |
| `noise_environment` | Environmental Protection / Zabıta |
| `other` | Citizen Relations Desk / Beyaz Masa |

### Table: `ticket_drafts`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `draft_id` | TEXT PK | `DRAFT-0047` | Opaque draft reference |
| `created_at` | DATETIME | `2026-11-09T18:34:00Z` | UTC ISO-8601 |
| `payload_json` | TEXT | `{...}` | Proposed ticket fields, if draft persistence is enabled later; no ticket row yet |
| `expires_at` | DATETIME | `2026-11-09T19:34:00Z` | UTC ISO-8601; stale drafts cannot be confirmed |

### Table: `ticket_updates`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `update_id` | INTEGER PK | `1` | |
| `ticket_id` | TEXT FK | `YV-2026-000123` | References confirmed ticket |
| `created_at` | DATETIME | `2026-11-09T19:00:00Z` | UTC ISO-8601 |
| `text` | TEXT | `The bench has collapsed.` | Citizen-provided extra information; untrusted |
| `source` | TEXT | `citizen` | `citizen`, `agent`, `staff` |

---

### Table: `departments`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `id` | INTEGER PK | `3` | |
| `code` | TEXT UNIQUE | `public_works` | Stable routing identifier |
| `name_tr` | TEXT | `Fen İşleri Müdürlüğü` | Turkish name |
| `name_en` | TEXT | `Public Works Directorate` | English name |
| `sla_hours` | INTEGER | `4` | *Added per urgency override:* default SLA; ticket urgency may tighten this |
| `email` | TEXT | `fen@yesilvadi.bel.tr` | *Added:* internal routing (synthetic) |

---

### Table: `neighborhoods`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `id` | INTEGER PK | `7` | |
| `name` | TEXT | `Çınarlık` | Neighborhood name (all synthetic) |
| `district_zone` | TEXT | `north` | Values: `north`, `south`, `east`, `west`, `central` |

---

### Table: `collection_schedule`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `id` | INTEGER PK | `12` | |
| `neighborhood_id` | INTEGER FK | `7` | |
| `waste_type` | TEXT | `general` | Values: `general`, `recycling`, `organic`, `bulky` |
| `weekday` | TEXT | `Monday` | Day of week |
| `time_window` | TEXT | `07:00–10:00` | *Added:* helps citizen plan disposal |

---

### Table: `facilities`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `id` | INTEGER PK | `5` | |
| `type` | TEXT | `park` | Values: `park`, `library`, `social_center`, `health_clinic`, `recycling_point` |
| `name` | TEXT | `Çınarlık Parkı` | Synthetic name |
| `neighborhood_id` | INTEGER FK | `7` | |
| `opening_hours` | TEXT | `08:00–22:00` | Stored as text; parsed by agent if needed |
| `address` | TEXT | `Çınar Sokak No:1` | *Added:* synthetic street address |

---

### Table: `fees_2026`

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `id` | INTEGER PK | `1` | |
| `item_code` | TEXT UNIQUE | `PET_REG_2026` | Stable fee item identifier |
| `service` | TEXT | `Pet registration` | English service name |
| `service_tr` | TEXT | `Evcil hayvan kaydı` | *Added:* Turkish service name for bilingual lookup |
| `amount_try` | REAL | `150.00` | Amount in Turkish Lira (synthetic) |
| `valid_from` | DATE | `2026-01-01` | |
| `source_doc` | TEXT | `2026-tariff-schedule.pdf` | Reference document name |

---

### Table: `audit_log` *(added)*

| Column | Type | Example Value | Notes |
|--------|------|---------------|-------|
| `id` | INTEGER PK | `9001` | |
| `ticket_id` | TEXT FK | `YV-2026-000123` | |
| `event_type` | TEXT | `status_change` | Values: `created`, `status_change`, `duplicate_flagged`, `confirmed`, `rejected` |
| `actor` | TEXT | `agent` | Values: `agent`, `staff`, `citizen` |
| `timestamp` | DATETIME | `2026-11-09T18:35:00Z` | |
| `detail` | TEXT | `Status changed: open → in_progress` | Free text log |

**Rationale:** Required for evaluation, SLA auditing, and safety review (tracing agent actions). Not in original brief but essential for a production system.

---

## (c) Action API Sketch

All endpoints are **sandbox-only** during Weeks 1–6. No real municipal system is connected. Confirmation step (R11) gates every write action.

### Base URL (sandbox)
```
http://localhost:8000/api/v1
```

---

### POST /tickets/drafts — Prepare a complaint

The agent checks for duplicates, classifies the complaint using the [canonical urgency rubric](use_case_brief.md#urgency-rubric), and returns a draft ID and summary for citizen review. This step **writes nothing to the database**. The `draft_id` refers to a short-lived in-memory proposal; it cannot appear in the staff queue. The `ticket_drafts` schema is reserved for a later persisted-draft option and is not used in this no-write flow.

**Request:**
```json
{
  "channel": "web",
  "language": "tr",
  "description": "Çınarlık Mahallesi Çınar Sokak'ta açık rögar kapağı var.",
  "neighborhood_id": 7,
  "street": "Çınar Sokak",
  "contact_last4": "4821"
}
```

**Response (draft; awaiting citizen confirmation):**
```json
{
  "draft_id": "DRAFT-0047",
  "category": "roads_sidewalks",
  "department": "Public Works Directorate",
  "urgency": "P1",
  "urgency_reason": "Open manhole — safety risk",
  "message_tr": "Şikayetinizi kaydedelim mi? (Evet/Hayır)",
  "message_en": "Shall we submit this complaint? (Yes/No)"
}
```

### POST /tickets/drafts/{draft_id}/confirm — Submit a confirmed complaint

The citizen reviews the summary and explicitly confirms. The agent calls this endpoint with the `draft_id`; the sandbox atomically creates a ticket with `status=open` and removes the draft. Expired drafts are rejected. No unconfirmed complaint enters `tickets`.

**Request:** `POST /tickets/drafts/DRAFT-0047/confirm` with `{"citizen_confirmed": true}`.

**Response (submitted):**
```json
{
  "ticket_id": "YV-2026-000123",
  "status": "open",
  "urgency": "P1",
  "department_tr": "Fen İşleri Müdürlüğü",
  "department_en": "Public Works Directorate",
  "sla_target": "4 hours",
  "message_tr": "Şikayetiniz alındı. Takip kodu: YV-2026-000123",
  "message_en": "Your complaint has been submitted. Reference: YV-2026-000123"
}
```

---

### GET /tickets/{ticket_id}?contact_last4= — Query own ticket status

**Example:** `GET /tickets/YV-2026-000123?contact_last4=4821`

**Response:**
```json
{
  "ticket_id": "YV-2026-000123",
  "status": "in_progress",
  "urgency": "P1",
  "category": "roads_sidewalks",
  "created_at": "2026-11-09T18:34:00Z",
  "message_tr": "Şikayetiniz işleme alındı.",
  "message_en": "Your complaint is being processed."
}
```

**Access rule:** The ticket ID and `contact_last4` must both match, or return 403 without ticket information. If the requester says the ticket belongs to someone else, withhold status even when both values match and ask that person to inquire themselves. **Known limitation:** ID plus last 4 digits does not prove ownership; SMS/OTP or e-Devlet verification is future work outside course scope. Do not present this lookup as strong authentication.

---

### POST /tickets/{ticket_id}/updates — Add information to own ticket

The agent first applies the ticket ID + phone last-4 access rule above and refuses a disclosed third-party ticket. It then shows the proposed extra text and asks the citizen to confirm before writing. Example request after confirmation: `{"contact_last4":"4455","text":"The bench has fully collapsed and a child tripped.","citizen_confirmed":true}`. The sandbox appends a `ticket_updates` row with `source=citizen`; it does not silently overwrite the original description. Staff or the agent classifier reassesses urgency under the [rubric](use_case_brief.md#urgency-rubric), with a possible P4 → P3 recommendation for the collapsed bench. The response reports the accepted update and any *proposed* reclassification; it does not claim an unapproved status change.

---

### GET /tickets/duplicates?neighborhood_id=&category=&hours= — Check for duplicates

**Example:** `GET /tickets/duplicates?neighborhood_id=7&category=roads_sidewalks&hours=48`

**Response:**
```json
{
  "duplicates": [
    {
      "ticket_id": "YV-2026-000119",
      "description_snippet": "Açık rögar — Çınar Sokak",
      "urgency": "P1",
      "status": "in_progress",
      "created_at": "2026-11-08T10:00:00Z"
    }
  ]
}
```

**Access and disclosure:** This is an internal, server-side agent tool only; citizens cannot call the endpoint directly. The agent uses it before preparing a draft. To the citizen it may reveal only minimal information, such as “A similar open report exists, ID: YV-2026-000119.” It never exposes another person's description, contact details, or internal notes.

---

### GET /queue — Staff priority queue (Beyaz Masa)

**Example:** `GET /queue?limit=20&status=open`

**Response:**
```json
{
  "queue": [
    {
      "ticket_id": "YV-2026-000123",
      "urgency": "P1",
      "category": "roads_sidewalks",
      "neighborhood": "Çınarlık",
      "description_snippet": "Open manhole cover on Çınar Sokak",
      "created_at": "2026-11-09T18:34:00Z",
      "sla_deadline": "2026-11-09T22:34:00Z"
    }
  ],
  "total_open": 47
}
```

**Access:** Staff-only endpoint. No citizen-facing exposure.

---

### Sandbox Note (R11)
Ticket creation follows `POST /tickets/drafts` → citizen confirmation → `POST /tickets/drafts/{draft_id}/confirm`. Citizen ticket updates also require an explicit summary and confirmation before `POST /tickets/{ticket_id}/updates`. The sandbox database is reset nightly. No real external system is called during Weeks 1–6.

---

## (d) Untrusted Input Sources

| Source | Description | Risk | First-line Defense |
|--------|-------------|------|--------------------|
| Citizen chat message | Free-text query or complaint via web/WhatsApp/phone | Prompt injection (e.g., embedded "Ignore previous instructions…"); urgency exaggeration; abusive content | Input sanitization; system prompt hardening; urgency classifier with rubric; injection detection layer |
| Complaint description field | Narrative text submitted as ticket body | Injection via description; inflated urgency claims; sensitive personal data included unintentionally | Strip control characters; classifier evaluates urgency independently of claimed severity; KVKK notice shown before submission |
| Uploaded photo caption / OCR | Text extracted from citizen-uploaded images | Adversarial text in image (white-on-white, tiny font); injected instructions via OCR | OCR output treated as low-trust; displayed to agent as `[IMAGE_TEXT: ...]` with explicit untrusted tag; human review for P1 derived from image |
| Staff note field (`staff_note`) | Internal note added by Beyaz Masa personnel | Accidental prompt injection if note is passed to LLM without escaping; insider data leakage | Notes passed in separate context block clearly labeled `[STAFF_NOTE — NOT citizen input]`; not echoed back to citizen |
| Inbound email / WhatsApp text | Messages ingested via channel adapter | Malformed Unicode, hidden characters, spoofed sender identity | Unicode normalization; sender validation at ingestion layer; channel metadata logged |
| External document content (RAG corpus) | Chunks retrieved from D1–D10 | If a future document is replaced or contaminated, injected instructions could reach the LLM | Documents authored internally; hash-verified at load time; retrieval output labeled with source document ID |

---
