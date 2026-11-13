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
| `src/classifier/` | Week 2 JSON schema validator, retry loop, and request classifier (`T=0`) |
| `src/eval_harness/` | Week 2 single-command evaluation harness, statistical metrics (95% CI, McNemar, Cohen's $\kappa$), and LLM judge |
| `prompts/` | Versioned system prompts (`baseline_v1`, `classifier_v1`, `assistant_v1`..`v3`, `judge_v1`) |
| `eval/testsets/` | Synthetic evaluation inputs (`week1_inputs.jsonl`, `week2_cases.jsonl`, `week2_human_labels.jsonl`) |
| `eval/results/week1/` | Historical v1 baseline runs and summaries as evidence; ad-hoc runs go to `/tmp` |
| `eval/results/week2/` | Week 2 evaluation results (`v1`, `v2`, `v3`), scoreboard, prompt comparison, judge calibration, hallucination log, and injection tests |
| `scripts/` | Temperature comparison, cost estimation, and Week 2 experiment orchestration |
| `config/` | Dated list price assumptions |
| `tests/` | Offline unit and acceptance tests (Week 1 + Week 2) |
| `src/rag`, `src/tools`, `src/agent`, `src/mcp_server` | Planned later stages |
| `data/corpus`, `data/structured`, `sandbox/` | SQL schema for synthetic records; document corpus and sandbox API implementation are planned |
| `docs/`, `reports/` | Plans, prompt design, test-set specs, hallucination/injection logs, and weekly reports (`week-1.md`, `week-2.md`) |

## Week 1 animated presentation

**[Open the animated presentation](https://efmaster04.github.io/AI390/)** — no terminal or installation required. Use the arrow keys to navigate, or choose Present.

The presentation is a single self-contained file: [`docs/index.html`](docs/index.html). All artwork, fonts, and player code are embedded. You can also download that file and open it in Chrome or Edge without a server or internet connection.

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

## Reproduce Week 2 (Classifier, Evaluation Harness, and Judge Calibration)

Week 2 adds a schema-validated JSON classifier (`src/classifier/`), three versioned prompt templates (`prompts/assistant_v1.md`, `v2`, `v3`), a 40-case evaluation suite (`eval/testsets/week2_cases.jsonl`), a single-command evaluation harness (`src/eval_harness/run.py`), and an LLM-as-judge calibrated against 20 human labels (`src/eval_harness/judge.py`).

To run the full Week 2 evaluation harness from cached results (recomputes `scoreboard.json`, `prompt_comparison.json`, and `prompt_comparison.md` without calling the network):

```sh
.venv/bin/python -m src.eval_harness.run --provider gemini --model gemini-3.1-flash-lite --inputs eval/testsets/week2_cases.jsonl --out-dir eval/results/week2 --prices config/prices.json --versions v1,v2,v3 --skip-existing
```

To execute fresh API runs across all 40 cases (`v1`, `v2`, `v3`), calibrate the LLM judge (`judge_calibration.json`), and generate the hallucination (`hallucination_log.json`) and injection (`injection_test_results.json`) artifacts:

```sh
.venv/bin/python scripts/run_week2_experiments.py
```

To run the offline test suite (Week 1 + Week 2 unit and acceptance tests):

```sh
.venv/bin/python -m pytest -v
```

## Weekly submission

The full Week 1 report should use the commit that will be tagged `week-1` and the exact scripts, data, and commands from that commit (R8). No real personal data is allowed (R10); writes are sandbox only (R11), and API keys must never enter the repository (R13). Weekly reports go in `reports/week-N.md` and are due at least 24 hours before class with a `week-N` tag (R4).
