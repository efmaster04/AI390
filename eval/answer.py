"""Ana asistan cevabı: tek sistem prompt'u (vN), sıcaklık 0, sabit seed."""

from pathlib import Path
import time

from eval.judge import load_prompt


ROOT = Path(__file__).resolve().parents[1]


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def answer(text, provider, *, prompt_path, seed=42, max_tokens=1024, temperature=0) -> dict:
    """Return {answer, error, input_tokens, output_tokens, latency_s, finish_reason, prompt_sha256}.

    Never raises: provider failures and empty outputs set `error` and leave `answer` None.
    The prompt's YAML front matter is stripped; its hash covers the raw file bytes.
    `latency_s` is the wall time of the generate call (pacing waits are removed by the caller).
    """
    report = {"answer": None, "error": None, "input_tokens": None, "output_tokens": None,
              "latency_s": None, "finish_reason": None, "prompt_sha256": None}
    try:
        system, report["prompt_sha256"] = load_prompt(resolve(prompt_path))
    except Exception as exc:
        report["error"] = f"Prompt error: {type(exc).__name__}"
        return report
    started = time.monotonic()
    try:
        response = provider.generate(system, text, temperature, max_tokens, seed, json_mode=False)
    except Exception as exc:
        report["error"] = f"Provider error: {exc}" if str(exc) else f"Provider error: {type(exc).__name__}"
        return report
    finally:
        report["latency_s"] = time.monotonic() - started
    if not isinstance(response, dict):
        report["error"] = "Provider response must be an object"
        return report
    for key in ("input_tokens", "output_tokens", "finish_reason"):
        report[key] = response.get(key)
    output = response.get("output")
    if not isinstance(output, str) or not output.strip():
        report["error"] = f"Empty answer (finish_reason={report['finish_reason']})"
        return report
    report["answer"] = output
    return report
