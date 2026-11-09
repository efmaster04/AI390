"""Interactive playground: chat with the Week 1 baseline prompt from the terminal.

Usage:
    .venv/bin/python scripts/try_chat.py                 # temperature 0.7
    .venv/bin/python scripts/try_chat.py --temperature 0  # deterministic-ish
    .venv/bin/python scripts/try_chat.py --no-system      # raw model, no municipal prompt

Each message is sent on its own (no chat history), exactly like the baseline.
That is on purpose: it lets you see statelessness (a Module 1 concept) for yourself.
"""

import argparse
import os
from pathlib import Path
import sys
import time

# Repo kökünü import yoluna ekle; script hangi klasörden çalıştırılırsa çalışsın
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.baseline.providers import GeminiProvider, ProviderError  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", default="gemini-3.1-flash-lite")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-output-tokens", type=int, default=400)
    p.add_argument("--prompt", type=Path, default=ROOT / "prompts" / "baseline_v1.md")
    p.add_argument("--no-system", action="store_true", help="send no system prompt")
    args = p.parse_args()

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        # Anahtarın değeri asla yazdırılmaz; yalnızca var olup olmadığı söylenir
        print("GEMINI_API_KEY is not set. Open a NEW terminal after adding it to ~/.zshrc.")
        return 2

    system = "" if args.no_system else args.prompt.read_text(encoding="utf-8").strip()
    provider = GeminiProvider(args.model, key)
    print(f"Model: {args.model} | temperature: {args.temperature} | system prompt: "
          f"{'none' if args.no_system else args.prompt.name}")
    print("Type a message (Turkish or English). Empty line or Ctrl+C to quit.\n")

    total_in = total_out = 0
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            break
        start = time.monotonic()
        try:
            result = provider.generate(system or " ", user, args.temperature, args.max_output_tokens, 42)
        except ProviderError as exc:
            print(f"[error] {exc}\n")
            continue
        seconds = time.monotonic() - start
        total_in += result["input_tokens"] or 0
        total_out += result["output_tokens"] or 0
        print(f"\nbeldesk> {result['output'].strip()}")
        print(f"[tokens in={result['input_tokens']} out={result['output_tokens']} | "
              f"{seconds:.1f}s | finish={result.get('finish_reason')}]\n")

    print(f"Session total: {total_in} input + {total_out} output tokens "
          f"(free tier: $0; list price would be in config/prices.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
