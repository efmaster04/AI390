# Beldesk Week 3 — seven-minute speaking draft

English delivery, 18 slides, three contiguous 140-second blocks. Efe 1–6; Doruk 7–12; Tarık 13–18. Advance the animation fragments as their content is mentioned. Pause at the recorded demo. These words describe the measured local draft, not a completed deployment. Human-label progress must be refreshed before presentation; no customer interviews are claimed.

## Efe · slides 1–6 · 0:00–2:20

### 1 · Opening · 10 s
Hello, we are presenting Beldesk, a Turkish and English municipal assistant. This week we added document retrieval and source-grounded answers for the fictional Yeşilvadi Municipality.

### 2 · Deliverables · 15 s
These are the eight Week Three requirements. We implemented the pipeline and retrieval experiments. The slide distinguishes working code, measured results and remaining work, including real customer interviews.

### 3 · Pipeline · 20 s
We prepared thirty public guides and one staff-only test document, with source, version, date and access metadata. We split them by section. BM25 and semantic search find candidates; RRF combines their rankings. A reranker sorts them again. Only authorized evidence reaches the answer model.

### 4 · Recorded answer · 40 s
This is a genuine recorded Gemini Three Point One response. The citizen asks about wheelchair accessibility and whether a health report is required. The answer follows our synthetic guide and points to numbered sources. Our code checks source numbers and exact evidence quotations. That verifies where the text came from; it does not prove the claim is supported. A separate judge checks that.

### 5 · Fixed fallback · 35 s
This example shows the software’s fixed no-source response. It is not a new model generation: when no authorized sources are supplied, the module returns this exact message without calling Gemini. A service error is recorded separately. Also, finding related text does not justify inventing an unknown fee, arrival time or completed action.

### 6 · Test set · 20 s
The test set has thirty-two answerable questions, sixteen Turkish and sixteen English, plus six unavailable-information controls. Retrieval metrics use only the thirty-two answerable questions. Each has a designated passage and evidence quote. Six development examples remain separate, and the synthetic labels are disclosed as drafts.

## Doruk · slides 7–12 ·2:20–4:40

### 7 · Retrieval results · 25 s
I am Doruk. The correct evidence appears in the first five results for thirty-one of thirty-two answerable questions. That is hit at five of about zero point nine six nine. MRR at ten is zero point nine five three. These measure finding sources, not generated-answer accuracy.

### 8 · Ablations · 25 s
We changed one component at a time. Dense and hybrid retrieval use the same reranker and have equal scores here, so we do not claim hybrid is better. With hybrid fixed, removing the reranker lowers MRR from zero point nine five three to zero point eight zero five. This supports reranking in this small test.

### 9 · Scoreboard · 30 s
We kept the same thirteen scoreboard rows. Null means unavailable, not zero. Last week’s answer score and this week’s retrieval score are not directly comparable. Service errors affect answer availability. The recovery run also reuses recorded successful responses, so cached and fresh results are separated. We are not claiming thirty-eight independent new generations.

### 10 · Faithfulness · 20 s
We check each claim against its cited evidence. A source number or copied quotation alone does not establish support. For example, ‘no fee is specified’ does not mean ‘the service is free’. The displayed rate has an explicit claim denominator and remains a provisional model estimate.

### 11 · Retrieval failure · 25 s
Our English privacy question asks whether a general service question requires identity details or uploaded documents. Its designated privacy passage missed the twenty-candidate pool. General service passages ranked higher. A reranker cannot recover a passage it never receives. We keep this failure and test improvements on separate development questions.

### 12 · Failure categories · 15 s
We separate failure stages: missing evidence is retrieval; an unsupported answer despite evidence is generation; HTTP five zero three is provider availability; an unavailable judge is evaluation. This tells us which component needs attention.

## Tarık · slides 13–18 ·4:40–7:00

### 13 · Human calibration · 30 s
I am Tarık. Doruk entered thirteen human labels; seven remaining items have separate supplementary notes. Those notes are excluded from human agreement. The claims come from historical model outputs, with evidence assigned afterward. This is a retrospective stress set, not current RAG accuracy. On thirteen matched labels, eight decisions agree and kappa is about zero point three nine. This limited agreement and the unchecked human reference keep our claim scores provisional.

### 14 · Evaluation boundaries · 25 s
We also updated the evaluation rule. A contact detail is not automatically fabricated if an authorized source provides it. The judge checks the evidence. Invented contacts, unperformed actions and instructions hidden inside retrieved documents must still be rejected.

### 15 · Remaining evidence · 25 s
The documents and test labels are synthetic drafts, with actual approvals recorded separately. The two real customer interviews have not been completed. Fictional personas are only rehearsal assumptions. The interview form is ready, but real conversations are still required before claiming the product track is complete.

### 16 · Next week · 40 s
Our first priority is to review human-label disagreements and expand the reference toward twenty labels. We report kappa without promising a score. Second, we add controlled lookup and sandbox writes, measuring whether tool results are valid. Creation needs confirmation and a successful result. Third, we measure multi-step task success with traces, limits, failures and cost evidence. Document retrieval alone cannot perform those actions.

### 17 · Reproduction · 15 s
The files include source versions, hashes, raw outputs and reproduction commands. Retrieval runs locally without a Gemini key. Recorded results can be recomputed offline. This version is shared on our Week Three working branch; it is not a release tag or deployed service.

### 18 · Close · 5 s
Thank you. We are ready for your questions and feedback.

## Questions to prepare

1. **What did you measure, and how sure are you?** Retrieval hit@k/MRR on 32 synthetic draft questions; separate live availability and claim metrics. Small set, no universal superiority claim.
2. **What failed, and why?** Privacy passage outside candidate pool; provider 503; unavailable judge. These are distinct stages.
3. **Is next week's plan the most important change?** Reliable evidence and evaluation must precede trusted task execution; controlled tools then address actual lookups and sandbox actions.
4. **Does 31/32 mean answer accuracy?** No, it is designated evidence retrieval.
5. **Is the fallback demonstration an LLM answer?** No, it is the actual deterministic no-source branch of the software.
6. **Were customer interviews conducted?** Not yet. The report says so; personas are explicitly fictional.
7. **Can a citizen request staff access?** No. Access filtering happens before ranking; application-authenticated role is required.


## Final result check before speaking

Use the numbers shown in the rebuilt deck. The recovery run first attempts every generation case, then judges valid answers with its remaining shared budget. “Valid saved answer” includes explicitly recorded cache reuse; it does not establish semantic accuracy. Source-support rates require valid judge verdicts and must state their claim denominator. Any κ uses only matched genuine human–judge pairs, not supplementary notes. Two actual customer interviews remain pending.
