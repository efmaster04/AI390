"""Checks for the generated single-file baseline Artifact."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_explorer.py"
OUTPUT = ROOT / "docs/baseline_explorer.html"


def test_explorer_build_and_artifact_contract():
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    page = OUTPUT.read_text(encoding="utf-8")
    lower = page.lower()
    assert "<title>Beldesk Baseline Explorer</title>" in page
    assert all(tag not in lower for tag in ("<html", "<body", "<!doctype"))
    assert page.startswith("<title>")
    assert '<meta name="claude:viewport-fit-sides" content="cover">' in page
    assert page.rstrip().endswith("</script>")

    match = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S)
    assert match is not None
    data = json.loads(match.group(1))
    assert len(data["inputs"]) == 25
    assert sum(len(item["responses"]) for item in data["inputs"]) == 75
    assert all(len(item["assessments"]["ratings"]) == 3 for item in data["inputs"])
    assert all(assessment["rating"] in {"meets", "partial", "fails"}
               for item in data["inputs"] for assessment in item["assessments"]["ratings"])
    assert {item["id"] for item in data["inputs"]} == {f"W1-{n:02d}" for n in range(1, 26)}
    assert len(re.findall(r'class="input-card"', page)) == 25
    assert all(sum(row["ratings"].values()) == 25 for row in data["summary"])
    assert "<\\/script" in match.group(1) or "</" not in match.group(1)

    external = re.findall(r'''(?:src|href)\s*=\s*["'](https?://[^"']+)["']''', page, re.I)
    assert len(external) == 1
    assert external[0].startswith("https://fonts.googleapis.com/")
    assert "x-goog-api-key: $GEMINI_API_KEY" in page
    assert "GEMINI_API_KEY" not in data["prompt"]
    assert "No inputs match these filters." in page
