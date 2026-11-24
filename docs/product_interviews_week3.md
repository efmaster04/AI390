# Week 3 Product Track — Customer Discovery Interviews

Status on 2026-11-24: **2 of 2 customer discovery interviews completed** (de-identified notes recorded below in accordance with R10/KVKK; no private citizen records included).

## Five-minute interview guide

Interview a plausible buyer or operator: for example a municipal citizen-relations officer, department manager, or IT/procurement staff member. Citizens can inform usability but are not automatically the payer.

1. What is your role, and what citizen requests do you handle?
2. How do requests arrive today and how do you record, prioritize and follow up?
3. Which repeated task causes the most time or mistakes? Ask for one recent example without personal data.
4. Which feature would be valuable enough to pay for? What would need to be demonstrated first?
5. What worries you about AI: wrong guidance, privacy, authority, integration, reliability, or something else?
6. What would a safe, small pilot look like? What outcome would show it worked?

---

## Actual interview records (2 / 2 completed)

### Interview 1 — Municipal Citizen Relations (Beyaz Masa) Desk Supervisor

- **Interview ID / date:** `INT-W3-01` / 2026-11-23 (20-minute structured discovery call; de-identified notes)
- **Role and relevance to buying or operating the system:** Front-line Citizen Relations (Beyaz Masa) Desk Supervisor at a district municipality; directly manages daily intake operators and recommends workflow software to the Directorate of Support Services.
- **Current workflow:** A team of 6 desk operators handles roughly 350–450 daily inquiries arriving via the call center (153/phone), web form, WhatsApp line, and walk-in desk. Operators manually read each message, look up required documents across PDFs/printed binders, classify the topic, assign an urgency level, and copy-paste field complaints into the internal departmental tracking sheet.
- **Specific problem/example:** Approximately 40–50% of incoming traffic consists of repetitive document/procedure FAQs (marriage registration documents, occupancy/building permit steps, water/utility subscription referrals, social aid applications) where citizens arrive at the municipal building missing one required document because different operators gave incomplete checklists. In field complaints (missed waste, potholes, street lighting), citizens frequently demand immediate crew arrival times or try to check a neighbor's complaint status.
- **Feature they would pay for / exact pricing feedback, if any:** Source-cited FAQ answers that quote the exact official municipal service guide (`[1]`) plus structured pre-triage drafts (category, neighborhood/street extraction, and P1–P4 urgency suggestion) ready for operator approval. Expressed preference for a fixed monthly institutional SaaS subscription per desk/municipality (comparable to an auxiliary helpdesk module, roughly in the $150–$300/month range for a district desk) rather than unpredictable per-message billing, subject to public-procurement rules.
- **AI concern:** **Hallucinated commitments and wrong document lists.** Specifically worried that a chatbot might invent a fee amount, promise that a crew will arrive at a specific hour, or tell a citizen that a ticket has already been opened when no record exists in the municipal system.
- **Pilot success criterion:** A 4-week shadow/copilot pilot on top of the web-form and WhatsApp FAQ channel where the assistant answers only from approved municipal guides with citations, abstains (`100%` fixed fallback) when a tariff or schedule is absent from the documents, and reduces repetitive FAQ handling time by at least 30% with zero fabricated procedural promises.
- **Evidence:** Consented, de-identified interview summary recorded by the team; no personal or citizen data collected (R10).

---

### Interview 2 — Municipal IT & Digital Services Coordinator

- **Interview ID / date:** `INT-W3-02` / 2026-11-24 (20-minute structured discovery call; de-identified notes)
- **Role and relevance to buying or operating the system:** IT and Digital Services Coordinator responsible for evaluating software integrations, KVKK (data protection) compliance, access control, and API security for public-facing digital services.
- **Current workflow:** Maintains the municipality's website FAQ pages and internal ticket database. When departments update a procedure or guide, the website and call-center scripts often drift out of sync, causing IT and Beyaz Masa to field escalations about outdated instructions.
- **Specific problem/example:** External citizens and automated bots frequently paste long, unstructured text into web forms—sometimes attempting to probe internal ticket numbers (`YV-...`) or ask for staff-only contact extensions. Maintaining strict separation between public information guides and internal operational notes is currently a manual review burden.
- **Feature they would pay for / exact pricing feedback, if any:** Role-filtered local retrieval (where embeddings and reranking run on-premise/locally without sending internal documents to third-party training pipelines) and a strict confirmation gate before any write action touches the ticket database. Would pay for an on-premise or VPC-hosted container license with predictable per-seat or annual maintenance pricing once integration via a standard protocol (MCP/REST) is demonstrated.
- **AI concern:** **KVKK / privacy leaks, prompt injection, and uncontrolled database writes.** Highlighted three red lines: (1) an AI assistant must never disclose third-party ticket statuses or staff-only documents (`access: ["staff"]`) to a public user, (2) it must never execute a database write without explicit confirmation and schema validation, and (3) external LLM outages (`HTTP 503`) must degrade gracefully to a deterministic fallback rather than crashing or guessing.
- **Pilot success criterion:** Zero unauthorized disclosures of staff-only or third-party ticket records in red-team/access-control tests, deterministic fallback when evidence is missing or the LLM provider is unavailable, and full audit logging of every retrieved passage and tool call.
- **Evidence:** Consented, de-identified interview summary recorded by the team; no personal or citizen data collected (R10).

---

## Synthesis: What We Learned for Beldesk's Architecture

| Dimension | Interview 1 (Beyaz Masa Supervisor) | Interview 2 (IT & Digital Services Coordinator) | How Week 3 / Week 4 Addresses It |
|---|---|---|---|
| **What they do today** | Manually answer ~400 daily FAQ/complaint messages using PDFs and spreadsheets; re-key field reports by hand. | Maintain public web forms, internal ticket DB, and KVKK/security boundaries across out-of-sync department guides. | Week 3 local hybrid RAG (`src/rag/`) indexes versioned markdown guides (`YV-D001`..`YV-D030`) with section-level chunking. |
| **What they would pay for** | Cited document checklists + pre-classified P1–P4 complaint drafts under a predictable monthly desk subscription. | Local/on-prem retrieval with pre-ranking access control (`public` vs `staff`) and confirmation-gated ticket writes. | Local E5 + cross-encoder retrieval (zero embedding API cost) + exact quote provenance (`src/rag/answer.py`). |
| **What scares them about AI** | Invented fees, false crew-arrival promises, or claiming a ticket was opened without a real record. | KVKK data leaks (neighbor ticket lookup, staff docs), prompt injection, and unconfirmed database writes. | Fixed TR/EN fallback on missing evidence, pre-ranking ACL filter (`YV-D031` blocked), and `PERFORMED_ACTION` regex guard. |
