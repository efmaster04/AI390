"""Run one baseline prompt for every input and temperature."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from .providers import ProviderError, make_provider


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "model"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commit_hash():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", required=True, choices=["gemini", "ollama", "openai_compat", "dry"])
    p.add_argument("--model", required=True)
    p.add_argument("--inputs", required=True, type=Path)
    p.add_argument("--temps", nargs="+", type=float, default=[0, 0.7, 1.2])
    p.add_argument("--max-output-tokens", type=int, default=400)
    p.add_argument("--prompt", type=Path, default=Path("prompts/baseline_v1.md"))
    p.add_argument("--out-dir", type=Path, default=Path("eval/results/week1"))
    p.add_argument("--rpm", type=float, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--base-url")
    p.add_argument("--api-key-env")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.rpm <= 0 or args.max_output_tokens <= 0 or not args.temps or any(t < 0 for t in args.temps):
        parser().error("rpm and max-output-tokens must be positive; temperatures must be nonnegative")
    try:
        provider = make_provider(args.provider, args.model, args.base_url, args.api_key_env)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    system = args.prompt.read_text(encoding="utf-8").strip()
    inputs = []
    for line_no, line in enumerate(args.inputs.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        required = {"id", "lang", "category", "ingredients", "text", "expected_behavior", "expected_urgency", "notes"}
        if not required.issubset(item):
            parser().error(f"input line {line_no} lacks: {sorted(required - item.keys())}")
        inputs.append(item)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    safe = safe_name(args.model)
    files = {t: args.out_dir / f"{args.provider}__{safe}__t{t:g}.jsonl" for t in args.temps}
    for path in files.values():
        path.write_text("", encoding="utf-8")
    command = list(sys.argv if argv is None else ["python", "-m", "src.baseline.run", *argv])
    # Özel URL sorgusu veya kullanıcı bilgisi sır taşıyabilir.
    for index, part in enumerate(command[:-1]):
        if part == "--base-url":
            command[index + 1] = "[redacted]"
    command = ["--base-url=[redacted]" if part.startswith("--base-url=") else part for part in command]
    meta = {"provider": args.provider, "model": args.model, "temps": args.temps,
            "prompt": str(args.prompt), "prompt_sha256": sha256(args.prompt),
            "inputs": str(args.inputs), "inputs_sha256": sha256(args.inputs),
            "git_commit": commit_hash(), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "max_output_tokens": args.max_output_tokens, "seed": args.seed,
            "command": command}
    (args.out_dir / f"run_meta_{args.provider}__{safe}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    last_request = None
    for item in inputs:
        for temperature in args.temps:
            result = {"id": item["id"], "lang": item["lang"], "category": item["category"],
                      "temperature": temperature, "output": None, "input_tokens": None,
                      "output_tokens": None, "latency_s": None, "error": None,
                      "dry_run": args.provider == "dry"}
            start = time.monotonic()
            for attempt in range(5):
                if args.provider != "dry" and last_request is not None:
                    time.sleep(max(0, 60 / args.rpm - (time.monotonic() - last_request)))
                last_request = time.monotonic()
                try:
                    call_start = time.monotonic()
                    result.update(provider.generate(system, item["text"], temperature,
                                                    args.max_output_tokens, args.seed))
                    # Gecikme yalnızca başarılı çağrıyı ölçer (bekleme ve retry hariç).
                    result["latency_s"] = round(time.monotonic() - call_start, 6)
                    result["error"] = None
                    break
                except ProviderError as exc:
                    result["error"] = str(exc)
                    if not exc.retryable or attempt == 4:
                        break
                    time.sleep(min(2 ** attempt, 16))
                except Exception as exc:
                    result["error"] = type(exc).__name__
                    break
            result["wall_time_s"] = round(time.monotonic() - start, 6)
            with files[temperature].open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
