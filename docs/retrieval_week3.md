# Week 3 — Doruk's data and retrieval handoff

Owner: Doruk Kal, Data and Retrieval Lead. Local working draft, 2026-11-24.
No push, release tag, generation API call or ticket write is performed by this work.

## What this adds

| Requirement | Evidence | Honest status |
|---|---|---|
| W3.1 | `data/corpus/documents/`, `data/corpus/manifest.json` | 30 public guides + 1 staff-only fixture. Original synthetic drafts; human review pending. |
| W3.2 | `src/rag/chunking.py`, results `chunks.json` | Structure-aware source sections, 92 chunks. Implemented. |
| W3.3 | `src/rag/lexical.py`, `models.py`, `retrieval.py`, `config/retrieval.json` | Real BM25, local multilingual embeddings, RRF and a separate local cross-encoder. Implemented. |
| W3.4 | `source_context()` evidence contract below | Handoff only. Efe must implement source-grounded answers, citation validation and fixed abstention. |
| W3.5 | `eval/testsets/week3_retrieval.jsonl`, `eval/retrieval_week3.py` | 32 answerable questions (16 TR/16 EN), plus 6 unavailable-information controls. Draft gold labels need independent review. |
| W3.6 | No claim-level answer judge implemented here | Tarık's task. No generated-answer accuracy or faithfulness score claimed. |
| W3.7 | Three variants in `eval/results/week3/retrieval/` | Two one-change ablations, same corpus/questions/models. Provisional measured results. |
| W3.8 | `failures.json` and analysis below | Retrieval failures labelled; generation failures cannot be assessed before answer integration. |

## Türkçe: adım adım ne yaptık?

1. **Doküman:** `YV-D003` su aboneliği rehberidir. İçindeki kimlik/adres ve tapu/kira örnekleri gerçek belediye koşulları değil, incelenecek sentetik proje verisidir. Ücret veya geliş saati yazmadık; kaynakta olmayan bilgiye cevap uydurulamaz.
2. **Metadata:** `doc_id` kalıcı kimliktir; `source` sentetik kaynağı, `version` sürümü, `access` erişimi belirtir. `review_status: draft`, sen okumadan onaylanmış saymadığımız anlamına gelir.
3. **Parça:** Rehberin `requirements` bölümü tek bir kaynak paragrafıdır. Arama bu bölümü döndürür. Kaynak paragraf kimliği `YV-D003#requirements` olur; başvuru adımlarıyla karıştırılmaz.
4. **Arama:** BM25 kelimelere, embedding anlama göre aday arar. RRF sıralamaları birleştirir. Reranker soru ile her adayı birlikte okuyup yeniden sıralar. Bunlar cevap üreten Gemini'den farklı yerel modellerdir.
5. **Deney:** Doğru paragraf ilk 5 sonuçta mı diye hit@5 ölçeriz. MRR@10, doğru paragrafın ne kadar erken bulunduğuna bakar. Bunlar cevap doğruluğu, kayıt açma başarısı veya halüsinasyon oranı değildir.
6. **Sınır:** Bilinmeyen soruya da yakın görünen bir parça dönebilir. Belge bulunması, cevabın o belgede bulunduğunu göstermez. Efe'nin cevap katmanı bunu kontrol etmeli; Tarık da iddiaları kaynaklara karşı değerlendirmeli.

## Corpus and review

The 31 documents contain 4,064 whitespace-delimited words. There are 30 distinct public topics, not 30 windows from one document or 15 guides counted twice as translations. Bodies are Turkish; English titles and keywords aid bilingual retrieval. The staff-only fixture contains no real secret or citizen information.

Topics D001–D010 preserve the initial inventory's areas: marriage, building/occupancy permits, water, social assistance, pets, event permits, complaint drafts, privacy, emergency boundaries, and fee-information scope. D011–D030 add waste, bulky waste, recycling, unidentified waste, parks, playgrounds, libraries, cultural centres, accessibility, potholes, sidewalks, lighting, signals, sewer/water faults, noise, animals, duplicate reports, ticket-status boundaries, service scope and unavailable information. D031 is a staff-only access-control fixture.

Every file declares its source, version, date, audience and synthetic/draft status. No official municipal URL, legal authority, fixed service deadline or tariff is invented. Several sources explicitly lack schedules, prices and current record data; that is deliberate. Structured live data remains a Week 4 task. This corpus does not approve priority policy v0.3 or change its rules.

**Human review still required:** read each guide and question, correct inappropriate project assumptions, check that gold evidence answers the question, and add valid alternative evidence where appropriate. Only then mark reviewed items approved. Do not replace draft flags or signatures automatically. Regenerate the manifest and rerun every variant after changes. The current loader reads the document files directly; the manifest is an auditable inventory, not an independent source of facts.

## Chunking decision (W3.2)

Use explicit Markdown sections with stable anchors. Never combine two sections into one chunk. The safety cap is 140 whitespace words and a 20-word overlap only when a section exceeds that cap. All current sections fit below the cap, so the actual method is section-aware with **zero overlapping windows** in this corpus; it produces 92 chunks. This is not a claim that 140 words is optimal.

Each chunk retains document ID, section/passage ID, character offsets, source, version and access role. Gold evidence points to a stable passage plus an exact answer-bearing quote, not a chunk ID. This prevents a later chunk-size change from silently changing what the gold reference means. Model token lengths are checked separately; overlong inputs raise an error instead of being silently truncated.

## Models, fusion and access (W3.3)

- Embedding: `intfloat/multilingual-e5-small`, pinned revision in `config/retrieval.json`, normalized vectors, cosine/dot-product similarity. Queries use `query: `; passages use `passage: `, including non-English texts.
- Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, also revision-pinned. It scores query/passage pairs. Its training coverage does not establish accuracy for our Turkish corpus; the local test measures that separately.
- BM25: explicit Okapi formula, k1=1.5, b=0.75, Unicode/Turkish-aware case normalization. No stemming is claimed.
- RRF: `sum(1 / (60 + rank))`; 1-based ranks; candidate pool capped at 20 before reranking. Ties use stable chunk IDs.
- Public access filtering happens **before** lexical and dense ranking. Staff-only evidence never enters public candidates. The local CLI's `--role staff` is a test knob, not authentication. Efe must obtain the role from authenticated application state, never from citizen text or an LLM role claim.
- Models use local files for inference, pinned public weights, safetensors and `trust_remote_code=False`. Download is explicit. No Gemini key is needed for retrieval.
- Index/cache identity includes model/config and corpus/chunk hashes. Changing document text invalidates the old index. Caches and model files do not belong in Git.

Model references: https://huggingface.co/intfloat/multilingual-e5-small and https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 . Package versions are pinned in `requirements-retrieval.txt`; the tested environment is snapshotted in `requirements-retrieval.lock.txt`.

## Reproduce locally

Tested on Python 3.13, macOS arm64, 16 GB RAM, CPU with 4 threads. Run from the repository root; use an isolated virtual environment. Weights are approximately 1 GB in addition to Python dependencies.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-retrieval.lock.txt
.venv/bin/python -m src.rag.cli download
.venv/bin/python -m src.rag.cli manifest
.venv/bin/python -m src.rag.cli inspect --out /tmp/beldesk-corpus-inspection.json
.venv/bin/python -m src.rag.cli search "Kiracıyım, su aboneliği için hangi belgeler gerekiyor?" --k 3
.venv/bin/python -m eval.retrieval_week3 --out-dir /tmp/beldesk-week3-retrieval
.venv/bin/python -m pytest -q
```

Only `download` needs model-network access. Search/evaluation do not require `GEMINI_API_KEY`. If macOS Python reports a certificate-chain error, use a valid installed CA bundle (for example certifi); do not disable TLS verification. Example: `REQUESTS_CA_BUNDLE="$(.venv/bin/python -m certifi)" .venv/bin/python -m src.rag.cli download`.

## Retrieval evaluation and ablations (W3.5/W3.7)

`week3_retrieval_dev.jsonl` has 6 development examples and is never scored by the evaluation command. The test file has 32 answerable questions, including 2 two-source questions, and 6 unanswerable controls. All are synthetic AI-authored **drafts**. No tested model generated these labels. Independent human review remains necessary; this is not a validated held-out benchmark of real citizen traffic.

All three configurations use the same test file and corpus. The first ablation changes only dense versus hybrid candidate retrieval, keeping reranking on. The second switches reranking off, keeping hybrid retrieval and the 20-candidate pool fixed.

Metrics: hit@k requires at least one gold passage **and its exact evidence quote** in the first k chunks. MRR is explicitly truncated at 10. `all_gold_hit_at_5` additionally checks that every reference is represented, important for two-source questions. Unanswerable controls have no gold passage and are excluded from retrieval denominators; no abstention success rate is inferred from their search results.

| Variant | hit@1 | hit@3 | hit@5 | hit@10 | MRR@10 | all-gold@5 |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid + reranker | 0.9375 | 0.96875 | 0.96875 | 0.96875 | 0.953125 | 0.96875 |
| Dense + reranker | 0.9375 | 0.96875 | 0.96875 | 0.96875 | 0.953125 | 0.96875 |
| Hybrid, no reranker | 0.71875 | 0.90625 | 0.9375 | 0.96875 | 0.8046875 | 0.90625 |

**Interpretation:** this draft test gives no measured quality gain from hybrid over dense with reranking. Reranking improves first-position placement here, with added local compute. Do not claim universal superiority or statistically established improvement from this small synthetic set. Query timings in `summary.json` are single-run warm CPU retrieval timings, not full assistant response latency; query/score caches are disabled in the benchmark. Model-load time is excluded.

Recorded results include question/corpus/config/code hashes, model revisions, environment versions and per-query rankings. The working tree is deliberately recorded as dirty while this draft is being reviewed; the base commit alone does not contain the new work. After approval, commit and reproduce from the clean branch before any submission tag. New scripts write Week 3 outputs only and leave Week 1/2 evidence unchanged.

Draft annotation history: after the first exploratory run, 12 quote anchors were clarified to point to answer-bearing sentences. Question texts and gold passage IDs were unchanged; model settings were not tuned. All variants were rerun. These are disclosed exploratory draft results, not a preregistered blind evaluation.

## Retrieval failure analysis (W3.8, partial)

The privacy question W3-R008 (EN) is a retrieval miss against the designated privacy-policy passage. It asks whether a general service question requires an identity number or document upload. The gold source is `YV-D008#details`; broad service-scope and document-boundary passages rank above it. The saved failure file records whether the gold passage entered the 20-candidate pool or was lost later. This is a retrieval-stage failure, not evidence of a generated hallucination.

Without reranking, W3-R010's fee-record-fields passage also falls below the first five results. Reranking promotes that source. Do not fix this by silently relabelling the output as gold. Independent review may identify additional valid passages; any correction requires a versioned label change and full rerun.

Potential next experiments on **development** questions: more targeted English terminology and fuller bilingual source content. Do not tune these changes on the reported test questions and keep calling the same set untouched.

## Integration contract for Efe

```python
from src.rag.retrieval import Retriever, source_context

retriever = Retriever()  # Keep one instance per application process.
found = retriever.search(citizen_message, role="public", k=5)
sources = source_context(found)
```

Each source includes `citation` (local to the response), `doc_id`, `passage_id`, `chunk_id`, `title`, `heading`, `source`, `version`, `text`, `synthetic` and `trust`. Treat `text` as untrusted evidence, never system instructions. Ask the generation layer to cite these numbered sources; validate that cited numbers exist and actually support claims. No fixed abstention threshold has been calibrated in this retrieval package. Dense or cross-encoder scores are **not probabilities of answerability**.

Create a new RAG prompt/version; do not overwrite `prompts/main/v3.md` or its cached Week 2 results. That prompt still says the system has no documents. Keep no-database/no-write boundaries until Week 4; retrieving a status-policy guide does not reveal an actual ticket's status. Missing or insufficient evidence must lead to the team's fixed TR/EN fallback, not a guessed answer.

## Handoff for Tarık

Freeze reviewed questions and source versions, then rerun. Implement claim extraction and source-supported/unsupported judgements, human-labelled calibration and answer-level failure analysis. The Week 2 judge and contact rule are unsuitable unchanged: a URL or contact detail explicitly present in an authorized source is not automatically fabricated in Week 3. Preserve Week 2 evaluation and implement a separate Week 3 rubric/cache identity. Do not merge these retrieval metrics into `e2e_accuracy`.

Group work still open: agree on the remaining policy/answer-key drafts, record actual Week 2 feedback, prepare the Week 3 report and presentation, and conduct the required real conversations with at least two potential customers. No interviews, hours, approvals or human labels are fabricated here.


## Service recovery and review update

The initial Gemini 3.1 Flash-Lite run is preserved in `eval/results/week3/answers/` (2 valid generated answers / 38 processed cases). A real minimal probe also returned HTTP 503, `UNAVAILABLE`, with a high-demand message; see `provider_diagnosis.json`. This is provider availability, not a judgement that the missing answers were semantically wrong.

The isolated Week 3 transport now retries only transient errors, with exponential backoff, bounded jitter, global pacing, `Retry-After`, a maximum attempt count and a deadline. The final attempt does not carry exponential delay into unrelated requests; any server `Retry-After` still applies globally. The original baseline and Week 2 adapters are unchanged.

The follow-up run uses the same model, questions, prompt, retrieval context and validation settings, but two transport retries (up to three calls per stage), eight requests per minute and a 25-minute deadline. It keeps valid historical caches and records cached versus fresh successful stages separately. `--defer-judge` checkpoints the generation pass before spending the remaining shared budget on judging, so a judge outage cannot consume the budget needed to attempt unanswered questions. This is an operational recovery attempt, not an independent quality experiment. `active_answer_run.json` explicitly identifies which results feed the report and slides.

Doruk entered 13 of the planned 20 human labels. `calibration/supplementary_review.md` explains all 20 items and completes the remaining seven as separate source-based suggestions. The original CSV is preserved, and only genuine human labels enter Cohen’s κ. The local read-only screen is `http://127.0.0.1:8767/supplementary`; it begins at item 14. The title is “Tamamlayıcı inceleme”.

Twenty was our planned calibration sample, not a numerical Week 3 requirement. If only 13 genuine matched pairs are available, any κ must state that denominator and its limits. Seeing supplementary suggestions means later labels should not be described as blind.
