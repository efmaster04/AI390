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

## Week 3: local retrieval

This Week 3 branch adds hybrid retrieval, source-cited answer generation and a claim-level judge; the integrated commands and measurement limits appear below. The 31 synthetic documents and the gold labels are drafts requiring human review. See [the step-by-step explanation, results and handoff](docs/retrieval_week3.md).

Use Python 3.13 and an isolated environment. These optional packages do not replace the Week 1/2 requirements. The first model download is about 1 GB, in addition to dependencies. After downloading, search and retrieval evaluation run locally without a Gemini key or inference API charge.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-retrieval.lock.txt
.venv/bin/python -m src.rag.cli download
.venv/bin/python -m src.rag.cli search "Kiracıyım, su aboneliği için hangi belgeler gerekiyor?" --k 3
.venv/bin/python -m eval.retrieval_week3 --out-dir /tmp/beldesk-week3-retrieval
```

The benchmark measures hit@1/3/5/10 and MRR@10 on 32 answerable questions, with 6 separate unanswerable controls and two one-change ablations. Results in `eval/results/week3/retrieval/` are provisional, not generated-answer accuracy. Never expose the CLI's staff-role switch as citizen-controlled authorization. Do not commit model downloads, `.venv` or `.cache`.

## Weekly submission

The full Week 1 report should use the commit that will be tagged `week-1` and the exact scripts, data, and commands from that commit (R8). No real personal data is allowed (R10); writes are sandbox only (R11), and API keys must never enter the repository (R13). Weekly reports go in `reports/week-N.md` and are due at least 24 hours before class with a `week-N` tag (R4).

## Week 3: integrated review branch

The local presentation is `docs/week3/index.html` (open the HTML file in a browser; no hosting change). The full draft report is `reports/week-3.md`. Generation uses the original Gemini3.1Flash-Lite at the user's direction; actual service failures are retained.

```sh
.venv/bin/python -m eval.answer_week3 --provider gemini --model gemini-3.1-flash-lite --out-dir /tmp/beldesk-w3-answers --transport-retries 2 --backoff-s 5 --stage-retries 0 --defer-judge --max-calls 150 --rpm 8 --timeout-s 30 --deadline-s 1500
.venv/bin/python -m eval.answer_week3 --out-dir eval/results/week3/answers --recompute-only
.venv/bin/python -m tools.week3_review.server --sheet eval/results/week3/calibration/human_sheet.csv --port 8767
.venv/bin/python -m scripts.run_week3_calibration --recompute-only
.venv/bin/python -m scripts.build_week3_report
.venv/bin/python scripts/build_week3_presentation.py
```

No push/deployment is part of these commands. Human labels must be entered by the real reviewer, never auto-filled from model verdicts. The historical calibration stress set is separate from current RAG quality. Two genuine customer interviews remain pending; see `docs/product_interviews_week3.md`. Speaking draft: `docs/week3_speaking_script.md`; Doruk's learning guide: `docs/week3_doruk_study.md`.


The original answer run stays in `eval/results/week3/answers/`; the recovery run is separate in `answers_retry_v2/`. Successful stages may be historical cache hits, recorded explicitly per row and in the summary. `active_answer_run.json` identifies the report input. Retry uses bounded exponential backoff, jitter and server `Retry-After`; it keeps Gemini 3.1 Flash-Lite and does not change quota or billing settings.

Doruk's 13 actual human labels are preserved. The remaining seven suggestions and an audit of the first thirteen are in [Tamamlayıcı inceleme](eval/results/week3/calibration/supplementary_review.md). The local read-only route is `http://127.0.0.1:8767/supplementary`. Supplementary suggestions are excluded from human–judge agreement. To retry the real calibration judge in small checkpointed batches, run `.venv/bin/python -m scripts.retry_week3_calibration` **after** any answer run, so the two processes do not independently use the same request budget.


### Week 3 classroom demo

Start the bounded interactive source-cited assistant from the repository root:

```sh
.venv/bin/python -m scripts.try_rag
```

For a live local-search demonstration without any API call, use `--search-only`. For a saved example, use `--replay W3-R019`; the terminal explicitly labels it as recorded. Replay is a backup, not a live model response. Each live question is independent, and only public sources are searched. This Week 3 entry point uses bounded 30-second transport attempts and one transient-error retry.


Week 3 review branch: [`week3`](https://github.com/efmaster04/AI390/tree/week3). The complete self-contained deck is [`docs/week3/index.html`](docs/week3/index.html): download the HTML and open it in a browser. The current GitHub Pages home remains the Week 2 presentation; this branch publication does not claim a Week 3 deployment or release tag.
