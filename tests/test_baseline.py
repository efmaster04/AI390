import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dry_pipeline(tmp_path):
    run = subprocess.run(
        [sys.executable, "-m", "src.baseline.run", "--provider", "dry", "--model", "dry",
         "--inputs", "eval/testsets/sample_inputs.jsonl", "--out-dir", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stderr
    files = sorted(tmp_path.glob("dry__dry__t*.jsonl"))
    assert len(files) == 3
    for path in files:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 3
        assert all(row["dry_run"] is True and row["error"] is None for row in rows)
    meta = json.loads((tmp_path / "run_meta_dry__dry.json").read_text(encoding="utf-8"))
    assert len(meta["temps"]) == 3
    assert len(meta["prompt_sha256"]) == 64
    assert len(meta["inputs_sha256"]) == 64
    assert meta["command"] == ["python", "-m", "src.baseline.run", "--provider", "dry",
                               "--model", "dry", "--inputs", "eval/testsets/sample_inputs.jsonl",
                               "--out-dir", str(tmp_path)]
    assert meta["git_dirty"] is None or isinstance(meta["git_dirty"], bool)

    compare = subprocess.run(
        [sys.executable, "scripts/compare_temps.py", "--results-dir", str(tmp_path),
         "--provider", "dry", "--model", "dry"], cwd=ROOT, capture_output=True, text=True,
    )
    assert compare.returncode == 0, compare.stderr
    assert "Language heuristic" in (tmp_path / "temperature_comparison.md").read_text(encoding="utf-8")

    cost = subprocess.run(
        [sys.executable, "scripts/cost_estimate.py", "--results-dir", str(tmp_path),
         "--prices", "config/prices.json"], cwd=ROOT, capture_output=True, text=True,
    )
    assert cost.returncode == 0, cost.stderr
    summary = json.loads((tmp_path / "cost_summary.json").read_text(encoding="utf-8"))
    assert len(summary["results"]) == 3
    assert all(next(c for c in result["list_price_comparisons"] if c["provider"] == "openai_compat")
               ["list_price_cost_per_1000_usd"] is None for result in summary["results"])
