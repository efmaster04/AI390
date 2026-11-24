# Beldesk Week 3 — seven-minute speaking script

English delivery, 18 slides, three contiguous blocks of about 140 seconds. **Efe: 1–6; Doruk: 7–12; Tarık: 13–18.** Allow time for slide transitions and the recorded example. Read the paragraphs below; the preparation notes and questions are not part of the seven-minute speech. Current answer-generation counts must match the final deck.

## Efe · slides 1–6 · 0:00–2:20

### 1 · Opening · 10 s
Hello, we are presenting Beldesk, a Turkish and English municipal assistant. This week we added document retrieval and source-grounded answers for the fictional Yeşilvadi Municipality.

### 2 · Deliverables · 15 s
These are the eight Week Three requirements. We implemented retrieval, source-grounded answers, evaluation and two ablations. We also rewrote the public documents and questions for residents. Review of that new content remains separate.

### 3 · Pipeline · 20 s
The corpus has thirty public guides and one staff-only fixture, with source, version, date and access metadata. We split them into ninety-two sections. BM25 and semantic search find candidates; RRF combines their ranks. A reranker sorts them again. Only authorized evidence reaches the model.

### 4 · Recorded answer · 40 s
This is a genuine recorded citizen-v2 response. A tenant asks what to prepare for a water subscription and does not know the previous subscription number. The answer uses the revised public service guide and numbered references. Our validator checks that evidence quotations occur in the cited source. That proves provenance, while source support and complete question coverage still require separate evaluation.

### 5 · Fixed fallback · 35 s
This example shows the software’s fixed no-source response. With no authorized sources, the module returns this exact message without calling Gemini. A service error has a separate record. Related text alone does not justify an answer about an unknown fee, an exact arrival time or a completed action. The current model run measures its unavailable-information controls separately.

### 6 · Citizen test set · 20 s
There are thirty-two answerable citizen questions, sixteen Turkish and sixteen English, plus six separate controls. Implementation questions are outside this benchmark. Three questions require multiple facets; two combine services. We registered alternative evidence before evaluation. Six development questions remain separate, and the labels need independent review.

## Doruk · slides 7–12 · 2:20–4:40

### 7 · Retrieval results · 25 s
I am Doruk. Some relevant evidence appears in the first five results for all thirty-two answerable questions. All required facets appear for thirty-one of thirty-two. Hit at one is nineteen of thirty-two; MRR is about zero point seven five nine. These are evidence-retrieval scores, not perfect-answer scores.

### 8 · Ablations · 25 s
We changed one component at a time. Dense and hybrid both reach thirty-two of thirty-two at hit five. Dense has slightly higher MRR: zero point seven six one, against hybrid’s zero point seven five nine. Keeping hybrid fixed and removing the reranker lowers MRR to zero point six eight nine. This small experiment does not establish universal superiority.

### 9 · Scoreboard · 30 s
The thirteen scoreboard rows stay the same. Null means unavailable, not zero. Old and new benchmarks use different questions and documents. Current answer and judge values use the new run, with cached responses and errors separated. Evidence retrieval is not answer adequacy.

### 10 · Faithfulness · 20 s
Each claim is checked against its cited evidence. A source number or copied quotation alone is insufficient. An unspecified fee does not mean a free service. The displayed claim rate uses its actual denominator and remains a provisional judge estimate.

### 11 · Partial evidence failure · 25 s
This resident asks about a park fair and an inaccessible entrance. Accessibility details rank third; event-permit details rank seventh. Our five-passage answer context misses the permit facet. Hit five succeeds because some evidence was found, while complete-facet coverage fails. This is a retrieval and context-selection problem. We retain the frozen labels and observed failure.

### 12 · Failure stages · 15 s
Missing evidence, unsupported generation, provider availability and judge failures are separate stages. This citizen run has its own service records; retired results cannot replace them. The distinction tells us which component needs attention.

## Tarık · slides 13–18 · 4:40–7:00

### 13 · Historical human check · 30 s
I am Tarık. The team completed twenty historical human labels. Seventeen decisions agree with the judge; kappa is about zero point seven seven one. These claims use embedded evidence from the earlier corpus. We preserve that completed check without presenting it as human accuracy on the new citizen questions or answers.

### 14 · Evidence rule · 25 s
A contact detail is not automatically fabricated if an authorized source provides it. The judge checks what the evidence supports. Invented details, unperformed actions and instructions hidden inside retrieved text still require rejection. Public guides explain services; internal software rules stay outside the citizen knowledge base.

### 15 · Review and customer discovery · 25 s
The team’s two customer interviews are complete and their records are preserved. The rewritten public guides are a separate matter: none of the thirty has a new human approval yet. An approval for an earlier document version does not automatically approve new text. The citizen questions and gold evidence also need independent review.

### 16 · Next week · 40 s
First, we review the thirty rewritten public guides and their evidence labels, moving public approvals from zero toward complete review. Second, we add controlled lookup and sandbox writes, measuring whether tool results are valid. Creation needs confirmation and a successful result. Third, we measure multi-step task success with traces, limits, failures and cost evidence. Document retrieval alone cannot perform those actions.

### 17 · Reproduction · 15 s
The files include source versions, hashes, raw outputs and reproduction commands. Retrieval runs locally without a Gemini key. We archive the earlier benchmark separately. This version is shared on the week3 working branch; release tagging and deployment are separate steps.

### 18 · Close · 5 s
Thank you. We are ready for your questions and feedback.

## Questions to prepare — outside the seven-minute speech

1. **What did you measure, and how sure are you?** We measured retrieval on 32 synthetic citizen questions: any relevant facet at five is 32/32, all required facets at five is 31/32, MRR@10 is 0.758854. The six controls have a separate denominator. Draft labels and the small sample limit generalization.
2. **Does 32/32 mean every answer is correct?** No. It means some registered relevant evidence appeared in the first five. It does not prove complete evidence coverage, support for every generated claim or answer adequacy.
3. **What failed, and why?** R032 needs both event-permit and accessibility information. Permit details rank seventh, outside the five passages supplied for answering, while accessibility details rank third. The missing facet is a retrieval/context-selection issue.
4. **Why keep hybrid if dense has higher MRR?** Both reach hit@5=1 here. Dense MRR is 0.761458, hybrid 0.758854. Hybrid is a required course component and provides lexical matching; this test does not show hybrid superiority.
5. **Why is the new MRR lower than the old slide?** Both documents and questions changed. The old implementation-question benchmark is retired; the two scores are not a controlled before/after comparison.
6. **What does κ≈0.771 validate?** It describes agreement on 20 historical human labels with their original evidence snapshots. It is not human accuracy for citizen-v2 answers and does not establish universal judge correctness.
7. **Are the interviews still missing?** No. The team completed two interviews. Their records and the completed historical human labels are preserved.
8. **Why are there zero public-source approvals?** The 30 public guides were rewritten. Approval is version-specific, so earlier approval cannot carry across changed text.
9. **Why are some metrics null?** We leave a metric unavailable when its required measurement or denominator is missing; a missing measurement is not zero error.
10. **Can a citizen request staff access or create a ticket?** A message cannot grant a staff role. Search filters access before ranking. Actual lookup and write tools belong to the controlled sandbox plan, rather than the current RAG pipeline.

## Preparation notes

Use the final deck’s current citizen-run counts for generated responses, claim decisions and service failures. Do not reuse the retired v1 “38/38” or “0/61” as citizen-v2 results. The historical κ remains separate. The recorded example is explicitly recorded; a terminal replay is not a new live model response. If you add a terminal demonstration, replace part of the recorded-example explanation instead of extending the seven-minute slot.
