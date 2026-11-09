# Use Case Brief — [PRODUCT NAME]

**Course:** AIC390 Prompt Engineering
**Team:** Efe İncirci, Tarık [TBD], Doruk [TBD]
**Use Case:** Custom (instructor-approved) — Bilingual Municipal AI Assistant

---

## Product Track

**First customer:** The Beyaz Masa (citizen relations desk) of a mid-size district municipality. Today they receive complaints and inquiries through a web form, phone calls, and WhatsApp. Staff manually read each message, categorize it, assign it to the relevant department, and track follow-ups in a spreadsheet. They also answer the same frequently asked questions repeatedly over the phone. **[PRODUCT NAME]** automates FAQ answering, complaint intake and classification, duplicate detection, and priority-sorted queue management so the Beyaz Masa team can focus on resolution instead of triage.

---

## Personas

### Citizen Persona — Ayşe K.

- **Age:** 38
- **Occupation:** Small-business owner in Yeşilvadi
- **Tech comfort:** Uses WhatsApp daily; occasionally fills out web forms.
- **Goal:** Report a broken streetlight near her shop quickly, get a ticket number, and check its status without calling the municipality.
- **Frustration:** Long hold times on the phone; no visibility into whether her complaint was received or acted upon.

### Staff Persona — Mehmet D.

- **Age:** 45
- **Role:** Beyaz Masa officer at Yeşilvadi Municipality
- **Tech comfort:** Uses office desktop, email, and the municipality's internal portal.
- **Goal:** See a prioritized queue of incoming complaints each morning, pre-classified by category and urgency, so he can route them to departments without reading every message in full.
- **Frustration:** Manually categorizing dozens of complaints every day; missing urgent safety issues buried among low-priority suggestions.

---

## User Stories

### US-1: FAQ Lookup
**As a** citizen, **I want to** ask the assistant about marriage application requirements in natural language, **so that** I get an accurate, cited answer without waiting on the phone.
- **Acceptance criteria:** The response quotes the relevant municipal service document by name and section. If the question is outside the corpus, the assistant states it cannot answer rather than guessing.

### US-2: Complaint Submission
**As a** citizen, **I want to** describe a pothole on my street via chat, **so that** the assistant creates a complaint ticket with the correct category, department, and urgency level.
- **Acceptance criteria:** The assistant extracts location (neighborhood, street), assigns a category (road infrastructure), routes to the correct department (Public Works), assigns urgency (P3), checks for duplicates in the same neighborhood within the last 7 days, and returns a ticket ID in the format `YV-2026-XXXXXX`.

### US-3: Ticket Status Inquiry
**As a** citizen, **I want to** check the status of my complaint by providing my ticket ID and the last 4 digits of my phone number, **so that** I can see whether it is open, in progress, or resolved.
- **Acceptance criteria:** The assistant returns status only if both the ticket ID and the last 4 digits of the phone number match the record. If they do not match, the assistant refuses and does not reveal any information about the ticket.

### US-4: Priority Queue for Staff
**As a** Beyaz Masa officer, **I want to** view incoming complaints sorted by urgency (P1 → P4), **so that** I can address safety-critical issues first.
- **Acceptance criteria:** The queue shows ticket ID, timestamp, category, department, urgency, and a one-line summary. P1 items appear at the top with a visual indicator. The officer can filter by department or date range.

### US-5: Emergency Redirection
**As a** citizen, **I want** the assistant to recognize when I describe a life-threatening emergency (e.g., a gas leak or a collapsing building), **so that** it immediately directs me to call 112/110/155 instead of only filing a ticket.
- **Acceptance criteria:** The assistant detects emergency keywords and context, responds with the appropriate emergency number within its first message, and optionally offers to also create a P1 ticket for municipal follow-up. It never tells the user to wait for municipal response in a genuine emergency.

---

## Scope

### In Scope
- FAQ answering from municipal service documents with source citations.
- Complaint intake: category classification, department routing, urgency assignment (P1–P4), and duplicate detection.
- Ticket creation in a sandbox environment (no real municipal system integration).
- Ticket status inquiry authenticated by ticket ID + last 4 digits of phone number.
- Priority-sorted complaint queue for Beyaz Masa staff.
- Bilingual operation (Turkish and English).
- Emergency redirection to 112 / 110 / 155 with optional P1 ticket creation.

### Out of Scope
- Payment processing (tax, water bills, or any financial transactions).
- Legal advice or interpretation of regulations beyond documented municipal procedures.
- Real emergency dispatch or coordination with emergency services.
- Political opinions, election information, or partisan commentary.
- Real personal data (all data is synthetic per course rule R10).
- Real crew or field-team dispatch.
- e-Devlet (national e-Government) identity verification or SSO integration.

---

## Use Case Card

### Who Pays
Mid-size district municipalities in Turkey that operate a Beyaz Masa (citizen relations desk). Today they staff phone lines and manually triage web-form and WhatsApp complaints. Secondary market: metropolitan municipalities looking for a white-label district-level solution.

### Example Requests

> Sokağımızdaki kaldırım çöktü, bebek arabası geçemiyor. Adres: Yeşilvadi Mahallesi, Çınar Sokak No:12.

> Where is my complaint? My ticket number is YV-2026-004871 and my phone ends in 3390.

> Nikâh başvurusu için hangi belgeler gerekiyor?

> I saw an open manhole on Atatürk Caddesi near the park — it's dangerous, someone could fall in.

> Çöpler iki haftadır alınmıyor, Bahçe Mahallesi. Bu normal mi?

### The 8 Ingredients

| # | Ingredient | In This Use Case |
|---|-----------|-----------------|
| 1 | **Documents for RAG** | Municipal service guides: marriage application, building permits, water subscription, social aid application, pet registration, event/stand permits, complaint handling & SLA policy, KVKK (data protection) disclosure text, emergency redirection guide, 2026 fee schedule. |
| 2 | **Structured data** | `tickets` (ID, status, urgency, department, timestamps), `departments` (name TR/EN, SLA hours), `neighborhoods` (name, district zone), `collection_schedule` (waste type, weekday, time window), `facilities` (type, name, opening hours), `fees_2026` (service, amount, source doc). |
| 3 | **The action** | Create a complaint ticket in the sandbox: classify category and department, assign urgency P1–P4, run duplicate check, and return a ticket ID. Confirmation step before writing. |
| 4 | **Untrusted input** | Citizen free-text complaints via chat: may contain exaggerated urgency to game prioritization, embedded prompt-injection attempts in complaint descriptions, or social-engineering to extract other citizens' ticket data. |
| 5 | **What it must not answer** | Resolution dates or crew arrival times not in the data; legal interpretations beyond written policy; other citizens' ticket details; political opinions; promises of action the municipality has not authorized. |
| 6 | **A multi-step task** | Citizen reports a problem → assistant classifies it → checks for duplicates in the same neighborhood → confirms details with the citizen → creates the ticket → returns the ticket ID and expected SLA. |
| 7 | **Exact identifiers** | Ticket IDs (`YV-2026-XXXXXX`), department codes, neighborhood names, phone last-4-digits, fee schedule item codes. |
| 8 | **The request classifier** | Intent (FAQ, complaint, status inquiry, emergency, out-of-scope), language (TR/EN), category (infrastructure, sanitation, parks, traffic, social services, other), urgency (P1–P4), extracted location (neighborhood, street). |

### The Hard Part
**Manipulation-resistant prioritization.** Citizens may exaggerate urgency ("someone will die!") to bump their complaint to P1. Complaint text may contain prompt-injection attempts designed to override classification logic. The assistant must apply the urgency rubric consistently based on objective criteria (P1: open safety hazard; P2: critical infrastructure failure; P3: routine maintenance; P4: suggestion or cosmetic issue) and resist attempts to override it through emotional language or injected instructions.

**Privacy boundary.** The assistant must never reveal another citizen's ticket details, even if the requester provides a valid ticket ID without the matching phone digits.

**Not making promises beyond the corpus.** When a document does not cover the citizen's question, the assistant must say so rather than fabricate an answer. Municipal commitments (e.g., SLA times) are cited from policy documents, never invented.

### After the Course
Position [PRODUCT NAME] as a SaaS product for Turkish municipalities, priced per resolved conversation or per municipality per month. Before launch: (1) verify compliance with KVKK (Turkish data protection law) for citizen data handling, (2) integrate with real municipal ticket management systems (e.g., CİMER referrals and the municipality's existing ticketing software), (3) obtain municipality IT security approval, and (4) add voice channel support (IVR / call center integration).

---
