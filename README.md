# AIC390 — Beldesk

Beldesk is a bilingual Turkish and English citizen assistant for the fictional Yeşilvadi Municipality. It is being built in seven stages: understand requests with a classifier, answer with retrieval, look up structured data, act through sandbox writes with approval, connect via MCP, orchestrate an agent loop, and measure results. Week 1 establishes a reproducible prompt baseline without documents or tools.

Instructor: Huseyin Ulusoy. Reference: `../Prompt_Engineering_Project_Handbook.pdf`.

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
| `eval/results/week1/` | Committed Week 1 baseline runs and summaries as evidence; ad-hoc runs go to `/tmp` |
| `scripts/` | Temperature comparison and cost estimation |
| `config/` | Dated list price assumptions |
| `tests/` | Offline acceptance test |
| `src/classifier`, `src/rag`, `src/tools`, `src/agent`, `src/mcp_server` | Planned later stages |
| `data/corpus`, `data/structured`, `sandbox/` | Synthetic documents, tables, and resettable fake APIs |
| `docs/`, `reports/` | Plans, grading rules, and weekly reports |

## Setup

Run from the repository root. Python 3 is required. Set only the key for the provider you choose; the dry runner needs none.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GEMINI_API_KEY='your-key' # Gemini only; set in your shell, never commit it
export GROQ_API_KEY='your-key'   # Groq only; set in your shell, never commit it
export OLLAMA_HOST='http://localhost:11434' # Ollama only
```

## Dataset v2: still 25 inputs, with two exact translation pairs

The active `eval/testsets/week1_inputs.jsonl` still contains **25 inputs (13 TR / 12 EN)**. W1-03 is now the Turkish translation of W1-02, and W1-07 is the Turkish translation of W1-10. Only two user texts changed. See [the pair texts and comparison method](docs/test_set_week1.md#revision-v2-two-translation-pairs-inside-the-same-25-inputs).

Existing `eval/results/week1` results, analysis and presentation describe the earlier v1 input texts. The explorer retrieves those original texts from the recorded Git commit, preventing old responses from being attached to changed messages. A fresh run is required for v2; no new token differences have been measured yet.

## Run the current 25-input set

The Week 1 baseline model is **Gemini 3.1 Flash-Lite** (`gemini-3.1-flash-lite`, free tier). It was chosen because it still applies `temperature`; Gemini 3.5 Flash-Lite ignores sampling parameters, which would make the temperature experiment meaningless. The runner sends one request per input (25 synthetic inputs in `eval/testsets/week1_inputs.jsonl`) at temperatures 0, 0.7 and 1.2. The committed `eval/results/week1/` is historical v1 evidence; the commands below run current v2 into a separate directory. Ad-hoc experiments belong in `/tmp`. The deliverable commit will be tagged `week-1`; the tag has not been created yet.

```sh
.venv/bin/python -m src.baseline.run --provider gemini --model gemini-3.1-flash-lite --inputs eval/testsets/week1_inputs.jsonl --out-dir /tmp/beldesk-week1-v2
.venv/bin/python scripts/compare_temps.py --results-dir /tmp/beldesk-week1-v2 --provider gemini --model gemini-3.1-flash-lite
.venv/bin/python scripts/cost_estimate.py --results-dir /tmp/beldesk-week1-v2 --prices config/prices.json
.venv/bin/python scripts/compare_paired_tokens.py --results-dir /tmp/beldesk-week1-v2
```

Offline smoke test (no network, synthetic tokens): `.venv/bin/python -m src.baseline.run --provider dry --model dry --inputs eval/testsets/sample_inputs.jsonl --out-dir /tmp/w1dry`. Other providers are supported (`--provider ollama --model qwen3:8b`, `--provider openai_compat --model openai/gpt-oss-20b`); point the last two commands at their output directory and model. `--base-url` and `--api-key-env` override the OpenAI compatible defaults; `--rpm` defaults to 10. The run metadata records input and prompt hashes, command, timestamp, and commit hash. The cost script reports measured token averages, list price estimates for every configured model, and `null` where token counts or prices are unavailable. Free tier actual spend is assumed to be zero; list price is still shown. Dry run token counts are synthetic.

## Trying the model

With `GEMINI_API_KEY` set in your shell, run `.venv/bin/python scripts/try_chat.py` from the repository root. Type a Turkish or English message; submit an empty line or press Ctrl+C to exit. Use `--temperature 0` to sample at zero temperature, or `--no-system` to compare with a raw model response. Each message is sent independently without chat history. This interactive script uses the provider and is separate from the committed Week 1 baseline results.

The full Week 1 report should use the commit that will be tagged `week-1` and the exact scripts, data, and commands from that commit (R8). No real personal data is allowed (R10); writes are sandbox only (R11), and API keys must never enter the repository (R13). Weekly reports go in `reports/week-N.md` and are due at least 24 hours before class with a `week-N` tag (R4).
