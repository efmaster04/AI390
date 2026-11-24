# AIC390 — Beldesk

Beldesk is a bilingual Turkish and English citizen assistant for the fictional Yeşilvadi Municipality. For example, a resident can describe a pothole. The goal is to identify its urgency and route the report to the right municipal unit. It is being built in seven stages: understand requests with a classifier, answer with retrieval, look up structured data, act through sandbox writes with approval, connect via MCP, orchestrate an agent loop, and measure results. Week 1 establishes a reproducible prompt baseline without documents or tools.

Instructor: Huseyin Ulusoy. Course reference: *Prompt Engineering Project Handbook* (course materials).

## Team

- Efe İncirci — Agent and tools lead
- Doruk Kal — Data and retrieval lead
- Tarık Edip Yenikomşu — Evaluation and safety lead

## Repository structure

| Path | Purpose |
|---|---|
| `src/baseline/` | Provider adapters and Week 1 runner |
| `prompts/` | Versioned system prompts |
| `eval/testsets/` | Synthetic evaluation inputs |
| `eval/results/week1/` | Historical v1 baseline runs and summaries as evidence; ad-hoc runs go to `/tmp` |
| `scripts/` | Temperature comparison and cost estimation |
| `config/` | Dated list price assumptions |
| `tests/` | Offline tests |
| `src/classifier/` | Week 2 schema-validated request classifier |
| `src/rag/` | Week 3 local retrieval draft: chunking, BM25, embeddings, RRF and reranking |
| `src/tools`, `src/agent`, `src/mcp_server` | Planned later stages |
| `data/corpus/` | 30 public synthetic guide drafts and one staff-only access-control fixture |
| `data/structured`, `sandbox/` | SQL schema; structured seed data and sandbox implementation remain future work |
| `docs/`, `reports/` | Plans, grading rules, and weekly reports |

## Animated presentations

| Week | Open in the browser | File |
|---|---|---|
| Week 2 (current) | **[efmaster04.github.io/AI390](https://efmaster04.github.io/AI390/)** | [`docs/index.html`](docs/index.html) |
| Week 1 | [efmaster04.github.io/AI390/week1](https://efmaster04.github.io/AI390/week1/) | [`docs/week1/index.html`](docs/week1/index.html) |

No terminal or installation required. Use the arrow keys to navigate, or choose Present. The Week 2 deck has 20 slides and 3 question branches; its numbers come from `eval/results/week2/` at tag `week-2`.

### Week 1 presentation

Each presentation is a single self-contained file. All artwork, fonts, and player code are embedded. You can also download that file and open it in Chrome or Edge without a server or internet connection.

It contains 22 main slides and 3 question branches. Some speaker notes still contain placeholders from the latest Claude version. The measured examples describe the historical baseline; the revised paired-input set still needs a fresh run, as explained below.

## Setup on macOS or Linux

For a first checkout:

```sh
git clone https://github.com/efmaster04/AI390.git
cd AI390
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The Gemini demo reads `GEMINI_API_KEY` from your terminal environment. Keep the key out of the repository. To check that it is set without displaying it:

```sh
test -n "$GEMINI_API_KEY" && echo "Key set" || echo "Key missing"
```

## Live demo

From the project directory, start the chat:

```sh
.venv/bin/python scripts/try_chat.py
```

At `you>`, type a message such as “Sokağımızda büyük bir çukur var. Bunun için kayıt açar mısın?” (“There is a large pothole on our street. Can you file a report?”) and press Enter. The assistant generates text; the Week 1 demo has no connection to a municipal ticketing system. Each request includes the current message and system instructions. Previous turns are omitted.

The default temperature is 0.7. To try another setting, exit with an empty line or Ctrl+C and restart with `--temperature 0` or `--temperature 1.2`. Use the same message to compare responses. The terminal shows input tokens, output tokens and elapsed time.

## Dataset v2: still 25 inputs, with two exact translation pairs

The active `eval/testsets/week1_inputs.jsonl` still contains **25 inputs (13 TR / 12 EN)**. W1-03 is now the Turkish translation of W1-02, and W1-07 is the Turkish translation of W1-10. Only two user texts changed. See [the pair texts and comparison method](docs/test_set_week1.md#revision-v2-two-translation-pairs-inside-the-same-25-inputs).

Existing `eval/results/week1` results, analysis and presentation describe the earlier v1 input texts. The explorer retrieves those original texts from the recorded Git commit, preventing old responses from being attached to changed messages. In a live demo, the English water-subscription request used 74 input tokens and its Turkish translation used 80 (+6), including the same system instructions. This is a single-pair observation. A complete v2 run across all three temperatures has yet to be published.

## Run the current 25-input set

The Week 1 baseline model is **Gemini 3.1 Flash-Lite** (`gemini-3.1-flash-lite`, free tier). The runner uses 25 inputs at three temperatures (0, 0.7 and 1.2), for 75 planned responses. The committed `eval/results/week1/` is historical v1 evidence; the commands below run current v2 into a separate directory. Ad-hoc experiments belong in `/tmp`. The deliverable commit will be tagged `week-1`; the tag has not been created yet.

```sh
.venv/bin/python -m src.baseline.run --provider gemini --model gemini-3.1-flash-lite --inputs eval/testsets/week1_inputs.jsonl --out-dir /tmp/beldesk-week1-v2
.venv/bin/python scripts/compare_temps.py --results-dir /tmp/beldesk-week1-v2 --provider gemini --model gemini-3.1-flash-lite
.venv/bin/python scripts/cost_estimate.py --results-dir /tmp/beldesk-week1-v2 --prices config/prices.json
.venv/bin/python scripts/compare_paired_tokens.py --results-dir /tmp/beldesk-week1-v2
```

The runner recreates its result files when it starts. Use a new output directory for each run you want to keep and pass that directory to the analysis commands. A recorded row can contain an API error such as HTTP 503. Check the error fields before reporting the number of successful responses.

## Offline checks and alternative providers

Run local tests with `.venv/bin/python -m pytest -q`. To check the runner without a key or network access:

```sh
.venv/bin/python -m src.baseline.run --provider dry --model dry --inputs eval/testsets/sample_inputs.jsonl --out-dir /tmp/w1dry
```

Dry-run token counts are synthetic. For Ollama, use `--provider ollama --model qwen3:8b` with a running local server (`OLLAMA_HOST` overrides its address). For Groq, set `GROQ_API_KEY` and use `--provider openai_compat --model openai/gpt-oss-20b`. The compatible provider supports `--base-url` and `--api-key-env`. The runner defaults to 10 requests per minute.

Use the matching provider and model for temperature comparisons. The paired-token script currently reads Gemini run metadata. Run metadata includes the input and prompt hashes, command, timestamp and Git commit. Cost estimates use the dated prices in `config/prices.json`. Unavailable estimates are reported as `null`. Zero free-tier spend is an assumption, not a billing measurement.

## Week 2: reproduce

All Week 2 numbers come from `eval/results/week2/` ([report](reports/week-2.md)). Run from the repository root:

```sh
# 1. Classifier, answers (v1, v2, v3) and judge for all 42 cases; writes the run files and scoreboard.json
.venv/bin/python -m eval.run_e2e --provider gemini --model gemini-3.1-flash-lite --versions v1 v2 v3 --rpm 9 --out-dir eval/results/week2

# 2. Recompute comparison.md, comparison.json and scoreboard.json from the saved run files only
.venv/bin/python -m eval.compare_versions --run-dir eval/results/week2

# 3. W2.8 injection test (18 trials; not cached, so this calls the provider)
.venv/bin/python -m eval.injection.run_injection --provider gemini --model gemini-3.1-flash-lite --versions v1 v3 --repeats 3 --out eval/results/week2/injection --rpm 10

# 4. Offline tests
.venv/bin/python -m pytest -q

# 5. Answer-key review page (local only, http://127.0.0.1:8765)
.venv/bin/python -m tools.review.server
```

- Every model call of step 1 is cached in the committed `eval/results/week2/cache/`, so a rerun is pure cache hits and reproduces the numbers without API calls (`run_meta.json` records `provider_calls_this_run` and `cache_hits`). The runner still checks that `GEMINI_API_KEY` is set. Step 2 never calls a model.
- `cost_per_task_usd` is the list-price equivalent from `config/prices.json`, not actual spend; the free tier bills 0 USD.
- W2.6 human labels: see [eval/human_labels/HOW_TO_LABEL.md](eval/human_labels/HOW_TO_LABEL.md).

## Week 3: citizen service RAG

The active **citizen-v2** corpus contains **30 citizen-facing service guides** and one staff-only access-control fixture. The guides explain applications, required preparation, service routing and complaint follow-up. They are declared **fictional project data**, not real municipal regulations. Internal assistant instructions belong in prompts/code, outside the public knowledge corpus.

The main test set contains **32 resident questions (16 TR / 16 EN)** and **6 unavailable-information/privacy controls (3 TR / 3 EN)**. Examples include checking a payment receipt, following up an unresolved lamp report, reporting a household power outage and clearing a clogged rain drain. Developer/schema/citation-proof questions were removed from citizen scoring. See [the revision](docs/week3_benchmark_revision.md), [the questions](eval/testsets/week3_retrieval.jsonl) and [the frozen source/label manifest](eval/testsets/week3_citizen_v2_manifest.json).

### Local retrieval

Use an isolated Python 3.13 environment. Optional retrieval dependencies do not replace Week 1/2 requirements. The first model download is approximately 1 GB; later retrieval runs locally without a Gemini key.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-retrieval.lock.txt
.venv/bin/python -m src.rag.cli download
.venv/bin/python -m src.rag.cli search "Kiracıyım, su aboneliği için ne hazırlamalıyım?" --k 3
.venv/bin/python -m eval.retrieval_week3 --out-dir eval/results/week3/retrieval
.venv/bin/python -m eval.retrieval_stats_week3
```

Measured citizen-v2 hybrid results: **hit@5 32/32**, **all-required-facets@5 31/32**, **MRR@10 0.7589**. A hit on one half of a multi-service question does not prove complete evidence coverage. Canonical/alternative evidence groups were fixed before scoring. Dense versus hybrid and reranker on/off use the same frozen questions. These are small, synthetic draft-set measurements, not generated-answer accuracy or a guarantee on unseen citizen questions.

### Source-cited answers and classroom demo

```sh
.venv/bin/python -m scripts.try_rag
.venv/bin/python -m scripts.try_rag --search-only
.venv/bin/python -m scripts.try_rag --replay W3-R003
```

The first command calls Gemini 3.1 Flash-Lite at temperature 0 with bounded attempts. `--search-only` is live local retrieval without generation. `--replay` explicitly labels a saved example; it is not a fresh model response. Each question is independent and only public evidence is searched. The staff-role CLI switch is a test surface, not citizen-controlled authorization.

For a fresh answer/judge experiment, use a separate output directory:

```sh
.venv/bin/python -m eval.answer_week3 --provider gemini --model gemini-3.1-flash-lite --out-dir /tmp/beldesk-citizen-v2 --transport-retries 1 --stage-retries 1 --defer-judge --max-calls 120 --rpm 8 --timeout-s 30 --deadline-s 1200
.venv/bin/python -m scripts.run_week3_calibration --recompute-only
.venv/bin/python -m scripts.build_week3_report
.venv/bin/python scripts/build_week3_presentation.py
```

`eval/results/week3/active_answer_run.json` identifies the actual recorded answer run used by the report. Report generation rejects source/question hashes that do not match citizen-v2. Semantic source support is measured claim by claim, separately from answer completeness and fixed-refusal behavior. Unknown billing stays unknown; saved-token price equivalents are not actual spend.

### Historical evidence and reviews

Old v1 results are preserved in `eval/results/week3/archive/v1-meta-benchmark/`; old questions are in `eval/testsets/archive/`. **Do not present the old 31/32 or old model responses as citizen-v2 results.** The two benchmarks are not a like-for-like improvement experiment. Retired internal questions are unscored examples in `eval/testsets/week3_internal_policy_cases.jsonl`; they are outside citizen retrieval metrics.

The team's **20 adjudicated human labels** and **two interview records** are preserved. Historical judge calibration (κ≈0.771) uses embedded **v1 source snapshots** and is not direct human grading of the new citizen-v2 answers. Earlier supplementary notes are retained under `calibration/history/`. Rewritten public guides reset to draft; an approval of older text is not approval of its replacement.

See [the technical guide](docs/retrieval_week3.md), [weekly report](reports/week-3.md), [speaking script](docs/week3_speaking_script.md), [Doruk's study guide](docs/week3_doruk_study.md) and [team interview notes](docs/product_interviews_week3.md). The self-contained deck is [docs/week3/index.html](docs/week3/index.html): download and open the HTML locally. Branch: [week3](https://github.com/efmaster04/AI390/tree/week3). This branch does not change the current Week 2 GitHub Pages home.

## Weekly submission

The full Week 1 report should use the commit that will be tagged `week-1` and the exact scripts, data, and commands from that commit (R8). No real personal data is allowed (R10); writes are sandbox only (R11), and API keys must never enter the repository (R13). Weekly reports go in `reports/week-N.md` and are due at least 24 hours before class with a `week-N` tag (R4).
