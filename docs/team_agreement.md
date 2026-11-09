# Team Agreement — Beldesk

**Course:** AIC390 Prompt Engineering (Instructor: Hüseyin Ulusoy)
**Date:** November 2026
**Team:** Yeşilvadi Municipality AI Assistant

---

## 1. Team Roles

| Member | Role | 7-Week Responsibilities |
|--------|------|------------------------|
| Efe İncirci | Agent and Tools Lead | Designs and maintains the tools (search, data query, write/sandbox action with confirmation), the agent loop, and the MCP server; owns tool-call safety and the baseline/prompt runner. Owns `src/tools/`, `src/agent/`, `src/mcp_server/` and `sandbox/`. |
| Doruk Kal | Data and Retrieval Lead | Writes and curates the document corpus and the synthetic structured data (`data/`), builds chunking, hybrid search (BM25 + dense) and reranking, and owns retrieval metrics (hit@5, MRR). |
| Tarık Edip Yenikomşu | Evaluation and Safety Lead | Owns the test sets and evaluation harness (`eval/`), the scoreboard and its statistics, abstention and faithfulness checks, injection tests and the red-team exchange. |


## 2. Meeting Schedule

- **Meeting 1:** [TBD — day and time] — Sprint planning and task review.
- **Meeting 2:** [TBD — day and time] — Integration check and deliverable review before submission.
- **Format:** In-person or online (Discord/Google Meet); decisions are logged in a shared document.

## 3. Decision Rule

1. The team seeks **consensus** on all decisions.
2. If consensus cannot be reached within the meeting, a **2/3 majority vote** decides.
3. On purely **technical matters** within a single role's domain, the respective lead makes the final call.

## 4. Non-Delivery Procedure

1. If a member cannot deliver their assigned task by the agreed deadline, they must notify the team **at least 48 hours** in advance.
2. On first occurrence, the team discusses the situation and **redistributes the work** among the remaining members.
3. If a pattern of non-delivery continues after a verbal warning, the team will **notify the instructor** and request guidance.

## 5. Post-Course Ownership

- All intellectual property created during the course is owned **equally (1/3 each)** by the three team members, subject to the university's IP policy.
- Any team member may continue developing the project after the course, provided the other members are notified and credited.
- Commercialization requires **written agreement** from all three members.

---

**Signatures**

| Name | Signature | Date |
|------|-----------|------|
| Efe İncirci | _______________ | _______________ |
| Tarık Edip Yenikomşu | _______________ | _______________ |
| Doruk Kal | _______________ | _______________ |
