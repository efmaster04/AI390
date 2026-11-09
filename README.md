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
| `eval/results/` | Generated runs and summaries (do not commit run outputs) |
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

## Reproduce week 1

Use `eval/testsets/week1_inputs.jsonl` for the full 25 synthetic inputs when that file is available. Each runner command sends one request per input at temperatures 0, 0.7, and 1.2. Choose one provider command below; replace the model with the exact model you use. The dry example runs on the three sample inputs and makes no network calls. Store generated outputs outside the repository or leave them uncommitted.

```sh
.venv/bin/python -m src.baseline.run --provider dry --model dry --inputs eval/testsets/sample_inputs.jsonl --out-dir /tmp/w1dry
.venv/bin/python -m src.baseline.run --provider gemini --model gemini-2.5-flash-lite --inputs eval/testsets/week1_inputs.jsonl --out-dir /tmp/w1gemini
.venv/bin/python -m src.baseline.run --provider ollama --model qwen3:8b --inputs eval/testsets/week1_inputs.jsonl --out-dir /tmp/w1ollama
.venv/bin/python -m src.baseline.run --provider openai_compat --model openai/gpt-oss-20b --inputs eval/testsets/week1_inputs.jsonl --out-dir /tmp/w1groq
.venv/bin/python scripts/compare_temps.py --results-dir /tmp/w1dry --provider dry --model dry
.venv/bin/python scripts/cost_estimate.py --results-dir /tmp/w1dry --prices config/prices.json
```

For another provider, point the last two commands at its output directory and model. `--base-url` and `--api-key-env` override the OpenAI compatible defaults; `--rpm` defaults to 10. The run metadata records input and prompt hashes, command, timestamp, and commit hash. The cost script reports measured token averages, list price estimates for every configured model, and `null` where token counts or prices are unavailable. Free tier actual spend is assumed to be zero; list price is still shown. Dry run token counts are synthetic.

The full Week 1 report should use a tagged commit and the exact scripts, data, and commands from that commit (R8). No real personal data is allowed (R10); writes are sandbox only (R11), and API keys must never enter the repository (R13). Weekly reports go in `reports/week-N.md` and are due at least 24 hours before class with a `week-N` tag (R4).
