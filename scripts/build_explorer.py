"""Build the self-contained Week 1 baseline Artifact from repository evidence."""

import html
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/baseline_explorer.html"
TEMPS = ("0", "0.7", "1.2")
RESULT_DIR = Path("eval/results/week1")
RESULT_FILES = {t: RESULT_DIR / f"gemini__gemini-3.1-flash-lite__t{t}.jsonl" for t in TEMPS}
SOURCES = [
    "eval/testsets/week1_inputs.jsonl", *[str(RESULT_FILES[t]) for t in TEMPS],
    "eval/results/week1/run_meta_gemini__gemini-3.1-flash-lite.json",
    "eval/results/week1/cost_summary.json", "prompts/baseline_v1.md",
    "docs/baseline_analysis_week1.md",
]


def read_jsonl(path):
    return [json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines() if line.strip()]


def esc(value):
    return html.escape(str(value), quote=True)


def inline_markdown(value):
    escaped = esc(value)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def findings_html(section):
    blocks = []
    in_list = False
    for raw in section.strip().splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            continue
        if line.startswith(("- ", "* ")):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{inline_markdown(line[2:])}</li>")
        else:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<p>{inline_markdown(line)}</p>")
    if in_list:
        blocks.append("</ul>")
    return "\n".join(blocks)


def short_head():
    # Hem normal repoda hem worktree'de çalışır; git yoksa "unknown" döner.
    try:
        result = subprocess.run(["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def result_inputs(meta):
    """Match the input snapshot to the recorded run, including after an R9 dataset revision."""
    path = ROOT / meta["inputs"]
    content = path.read_bytes()
    historical = hashlib.sha256(content).hexdigest() != meta["inputs_sha256"]
    if historical:
        try:
            content = subprocess.run(
                ["git", "show", f'{meta["git_commit"]}:{meta["inputs"]}'],
                cwd=ROOT, capture_output=True, check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError("Historical baseline inputs unavailable. Fetch the run commit/history before rebuilding; never mix current inputs with old responses.") from exc
    if hashlib.sha256(content).hexdigest() != meta["inputs_sha256"]:
        raise ValueError("Baseline input hash mismatch")
    return [json.loads(line) for line in content.decode("utf-8").splitlines() if line.strip()], historical


def build_data():
    meta = json.loads((ROOT / SOURCES[4]).read_text(encoding="utf-8"))
    inputs, historical = result_inputs(meta)
    results = {t: {r["id"]: r for r in read_jsonl(RESULT_FILES[t])} for t in TEMPS}
    costs = json.loads((ROOT / SOURCES[5]).read_text(encoding="utf-8"))
    analysis = (ROOT / SOURCES[7]).read_text(encoding="utf-8")
    assessment_section = analysis.split("## Per-input assessment\n", 1)[1].split("\n## ", 1)[0]
    assessments = {}
    for line in assessment_section.splitlines():
        if not line.startswith("| W1-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 8:
            raise ValueError(f"Malformed assessment row: {line}")
        ratings = []
        for cell in cells[3:6]:
            match = re.match(r"^(meets|partial|fails)\s*[—–-]\s*(.+)$", cell)
            if not match:
                raise ValueError(f"Malformed assessment: {cell}")
            ratings.append({"rating": match.group(1), "reason": match.group(2)})
        assessments[cells[0]] = {"ratings": ratings, "decision_change": cells[6], "note": cells[7]}
    findings = analysis.split("## Critical evidence and decision changes\n", 1)[1].split("\n## ", 1)[0]
    cost_by_file = {r["file"]: r["list_price_cost_per_1000_usd"] for r in costs["results"]}
    items = []
    for item in inputs:
        ident = item["id"]
        if ident not in assessments or any(ident not in results[t] for t in TEMPS):
            raise ValueError(f"Missing assessment or response for {ident}")
        rows = [results[t][ident] for t in TEMPS]
        items.append({**item, "assessments": assessments[ident], "responses": rows,
                      "different": [r["output"] != rows[0]["output"] for r in rows]})
    summary = []
    for index, t in enumerate(TEMPS):
        rows = [item["responses"][index] for item in items]
        ratings = Counter(item["assessments"]["ratings"][index]["rating"] for item in items)
        summary.append({"temperature": t, "mean_chars": sum(len(r["output"] or "") for r in rows) / len(rows),
                        "exact_match": sum(not item["different"][index] for item in items),
                        "mean_tokens": sum(r["output_tokens"] or 0 for r in rows) / len(rows),
                        "cost": cost_by_file[RESULT_FILES[t].name], "ratings": dict(ratings)})
    if len(items) != 25 or any(len(results[t]) != len(items) for t in TEMPS) or len(assessments) != len(items):
        raise ValueError("Expected 25 complete inputs and three complete result sets")
    return {"inputs": items, "meta": meta, "summary": summary, "findings": findings,
            "prompt": (ROOT / SOURCES[6]).read_text(encoding="utf-8").strip(),
            "sources": SOURCES, "head": short_head(), "historical_inputs": historical}


def render(data):
    items, meta, summary = data["inputs"], data["meta"], data["summary"]
    example = next(item for item in items if item["id"] == "W1-24")
    request = {"systemInstruction": {"parts": [{"text": data["prompt"]}]},
               "contents": [{"role": "user", "parts": [{"text": example["text"]}]}],
               "generationConfig": {"temperature": 0, "maxOutputTokens": meta["max_output_tokens"], "seed": meta["seed"]}}
    saved = {key: example["responses"][0][key] for key in ("output", "input_tokens", "output_tokens", "finish_reason")}
    request_text = "POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent\nx-goog-api-key: $GEMINI_API_KEY\n\n" + json.dumps(request, ensure_ascii=False, indent=2)
    chips = [("Model", meta["model"]), ("Seed", meta["seed"]), ("Max output tokens", meta["max_output_tokens"]),
             ("Commit", meta["git_commit"][:7]), ("Git dirty", str(meta["git_dirty"]).lower()),
             ("Calls", f"{len(items)} inputs × {len(TEMPS)} temperatures = {len(items)*len(TEMPS)}"),
             ("Errors", sum(bool(r["error"]) for item in items for r in item["responses"]))]
    chip_html = "".join(f'<span class="meta-chip"><b>{esc(label)}</b> {esc(value)}</span>' for label, value in chips)
    table_rows = "".join(
        f'<tr><th scope="row">t={s["temperature"]}</th><td>{s["mean_chars"]:.0f}</td>'
        f'<td>{s["exact_match"]}/{len(items)}</td><td>{s["mean_tokens"]:.1f}</td>'
        f'<td>${s["cost"]:.5f}</td><td>{s["ratings"].get("meets", 0)}</td>'
        f'<td>{s["ratings"].get("partial", 0)}</td><td>{s["ratings"].get("fails", 0)}</td></tr>' for s in summary)
    bars = "".join(
        '<div class="bar-row"><b>t=' + esc(s["temperature"]) + '</b><div class="stack" aria-label="' +
        esc(f't={s["temperature"]}: {s["ratings"].get("meets",0)} meets, {s["ratings"].get("partial",0)} partial, {s["ratings"].get("fails",0)} fails') + '">' +
        "".join(f'<span class="seg {rating}" style="--share:{s["ratings"].get(rating,0)}">{s["ratings"].get(rating,0)}</span>'
                for rating in ("meets", "partial", "fails")) + '</div></div>' for s in summary)
    categories = ("question", "lookup", "action", "unanswerable", "multi_step", "untrusted")
    filter_buttons = '<button type="button" class="filter active" data-category="all" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" class="filter" data-category="{c}" aria-pressed="false">{c.replace("_", " ")}</button>' for c in categories)
    cards = []
    for item in items:
        panels = []
        for idx, (t, result, assessment) in enumerate(zip(TEMPS, item["responses"], item["assessments"]["ratings"])):
            diff = "differs from t=0" if item["different"][idx] else "same as t=0"
            panels.append(f'''<section class="response"><div class="response-head"><h4>t={t}</h4><span class="diff">{diff}</span></div>
<div class="assessment"><span class="badge {assessment["rating"]}">{assessment["rating"]}</span><span>{esc(assessment["reason"])}</span></div>
<pre class="reply">{esc(result["output"] or "[No output]")}</pre>
<div class="response-foot">In {esc(result["input_tokens"])} · Out {esc(result["output_tokens"])} tokens <span>{float(result["latency_s"]):.2f} s</span></div></section>''')
        urgency = item["expected_urgency"] or "—"
        changed = item["assessments"]["decision_change"]
        cards.append(f'''<article class="input-card" data-category="{esc(item["category"])}" data-lang="{esc(item["lang"])}" data-search="{esc((item["id"]+' '+item["text"]).casefold())}" data-changed="{str(not changed.lower().startswith('none')).lower()}">
<div class="card-head"><h3>{esc(item["id"])}</h3><span class="category">{esc(item["category"].replace("_", " "))}</span><span>{esc(item["lang"].upper())}</span><span>Expected urgency: <b>{esc(urgency)}</b></span><span>Ingredients: {esc(", ".join(map(str, item["ingredients"])))}</span></div>
<blockquote>{esc(item["text"])}</blockquote><p class="expected"><b>Expected behavior</b><br>{esc(item["expected_behavior"])}</p>
<div class="responses">{"".join(panels)}</div><div class="card-notes"><p><b>Decision changed with temperature</b> {esc(changed)}</p><p><b>Note</b> {esc(item["assessments"]["note"])}</p></div></article>''')
    embedded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    sources = "".join(f"<li><code>{esc(path)}</code></li>" for path in data["sources"])
    return f'''<title>Beldesk Baseline Explorer</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{{--bg:#f3f6f7;--paper:#fff;--fg:#172a3c;--muted:#526676;--line:#cbd6dc;--soft:#e7eef2;--blue:#176995;--blue-soft:#e2f0f8;--meets:#146b4e;--meets-bg:#e1f2e9;--partial:#875600;--partial-bg:#fff0d1;--fails:#aa3833;--fails-bg:#fae7e5;--focus:#176995;color-scheme:light}}
@media(prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#14212b;--paper:#1c2d38;--fg:#ecf2f3;--muted:#afc2ca;--line:#415563;--soft:#273d4b;--blue:#83c8eb;--blue-soft:#24435a;--meets:#8adfba;--meets-bg:#214b3d;--partial:#ffd17c;--partial-bg:#554321;--fails:#ffaaa5;--fails-bg:#593332;--focus:#83c8eb;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#14212b;--paper:#1c2d38;--fg:#ecf2f3;--muted:#afc2ca;--line:#415563;--soft:#273d4b;--blue:#83c8eb;--blue-soft:#24435a;--meets:#8adfba;--meets-bg:#214b3d;--partial:#ffd17c;--partial-bg:#554321;--fails:#ffaaa5;--fails-bg:#593332;--focus:#83c8eb;color-scheme:dark}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 'IBM Plex Sans',Arial,sans-serif}}button,input,select{{font:inherit}}button:focus-visible,input:focus-visible,select:focus-visible{{outline:3px solid var(--focus);outline-offset:2px}}.wrap{{max-width:1460px;margin:auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 60px;min-width:0}}h1,h2,h3,h4{{font-family:'IBM Plex Sans Condensed','Arial Narrow',Arial,sans-serif;font-weight:600;line-height:1.2;margin:0}}h1{{font-size:clamp(2rem,4vw,3.4rem)}}h2{{font-size:1.8rem;margin-bottom:16px}}h3{{font-size:1.4rem}}h4{{font-size:1.1rem}}p{{margin:0 0 12px}}section.major{{margin-top:46px}}.masthead{{border-top:6px solid var(--blue);border-bottom:1px solid var(--line);padding:22px 0 24px}}.eyebrow{{font:500 11px 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.12em;color:var(--blue);margin-bottom:10px}}.subhead{{color:var(--muted);margin:10px 0 20px}}.meta{{display:flex;flex-wrap:wrap;gap:8px}}.meta-chip{{border:1px solid var(--line);background:var(--paper);padding:5px 9px;font-size:12px}}.meta-chip b{{color:var(--muted);font-weight:500;margin-right:4px}}.theme-button{{float:right;background:var(--paper);color:var(--blue);border:1px solid var(--line);padding:5px 10px;cursor:pointer}}.flow{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-block:1px solid var(--line)}}.step{{padding:16px;border-right:1px solid var(--line);min-width:0}}.step:last-child{{border-right:0}}.step-num{{display:block;color:var(--blue);font:500 12px 'IBM Plex Mono',monospace;margin-bottom:7px}}.code-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:18px}}.code-panel{{min-width:0;background:var(--paper);border:1px solid var(--line);padding:14px}}.code-panel h3{{font-size:1.1rem;margin-bottom:9px}}pre,code{{font-family:'IBM Plex Mono',ui-monospace,monospace}}pre{{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}}.code-panel pre{{font-size:11px;max-height:390px;overflow:auto}}details{{margin-top:14px;border-top:1px solid var(--line);padding-top:10px}}summary{{cursor:pointer;color:var(--blue);font-weight:600}}details pre{{margin-top:12px;background:var(--paper);padding:14px;border:1px solid var(--line)}}.reproduce{{margin-top:16px}}.reproduce code{{overflow-wrap:anywhere}}.table-scroll{{overflow-x:auto;border:1px solid var(--line);background:var(--paper)}}table{{border-collapse:collapse;width:100%;min-width:690px;font-variant-numeric:tabular-nums}}th,td{{padding:9px 11px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}}thead{{background:var(--soft)}}tbody tr:last-child th,tbody tr:last-child td{{border-bottom:0}}.bar-area{{max-width:760px;margin:20px 0 10px}}.bar-row{{display:grid;grid-template-columns:55px minmax(0,1fr);gap:12px;align-items:center;margin:7px 0;font-variant-numeric:tabular-nums}}.bar-row b{{font:500 12px 'IBM Plex Mono',monospace}}.stack{{display:flex;height:29px;border:1px solid var(--line)}}.seg{{flex:var(--share);min-width:0;text-align:center;line-height:27px;font-size:12px;font-weight:600}}.seg.meets{{background:var(--meets-bg);color:var(--meets)}}.seg.partial{{background:var(--partial-bg);color:var(--partial)}}.seg.fails{{background:var(--fails-bg);color:var(--fails)}}.caveat,.small{{font-size:12px;color:var(--muted)}}.findings{{max-width:980px;border-left:3px solid var(--blue);padding-left:18px}}.findings p,.findings li{{margin-bottom:15px}}.findings code{{font-size:.9em}}.controls{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:15px;align-items:end;padding:14px 0;border-block:1px solid var(--line);margin-bottom:20px}}.filters{{display:flex;flex-wrap:wrap;gap:6px}}.filter{{background:var(--paper);border:1px solid var(--line);color:var(--fg);padding:6px 10px;cursor:pointer}}.filter.active{{background:var(--blue-soft);border-color:var(--blue);color:var(--blue)}}.control-line{{display:flex;flex-wrap:wrap;align-items:center;gap:12px;grid-column:1/-1}}.control-line label{{display:flex;align-items:center;gap:7px}}select,input[type=search]{{background:var(--paper);color:var(--fg);border:1px solid var(--line);padding:7px}}input[type=search]{{min-width:0;flex:1 1 230px}}input[type=checkbox]{{accent-color:var(--blue)}}.count{{color:var(--muted);font:12px 'IBM Plex Mono',monospace}}.input-card{{border-top:2px solid var(--fg);padding:20px 0 30px;margin-top:28px;min-width:0}}.input-card[hidden],#empty[hidden]{{display:none}}.card-head{{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;font-size:12px;color:var(--muted)}}.card-head h3{{color:var(--fg);margin-right:4px}}.category{{background:var(--blue-soft);color:var(--blue);padding:2px 8px;text-transform:uppercase;letter-spacing:.04em;font-weight:600}}blockquote{{margin:18px 0;padding:11px 17px;border-left:3px solid var(--blue);background:var(--paper);overflow-wrap:anywhere}}.expected{{margin:0 0 16px}}.expected b,.card-notes b{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}}.responses{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px}}.response{{border:1px solid var(--line);background:var(--paper);padding:13px;min-width:0;display:flex;flex-direction:column}}.response-head{{display:flex;align-items:center;justify-content:space-between;gap:6px;border-bottom:1px solid var(--line);padding-bottom:9px}}.diff{{font:11px 'IBM Plex Mono',monospace;color:var(--muted)}}.assessment{{display:flex;align-items:flex-start;gap:7px;margin:10px 0;font-size:12px;min-height:52px}}.badge{{padding:2px 6px;font-weight:600;white-space:nowrap}}.badge.meets{{background:var(--meets-bg);color:var(--meets)}}.badge.partial{{background:var(--partial-bg);color:var(--partial)}}.badge.fails{{background:var(--fails-bg);color:var(--fails)}}.reply{{font:12px/1.55 'IBM Plex Mono',monospace;max-height:360px;overflow:auto;flex:1;min-height:80px;overflow-wrap:anywhere}}.response-foot{{border-top:1px solid var(--line);margin-top:12px;padding-top:8px;color:var(--muted);font:11px 'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}}.response-foot span{{float:right}}.card-notes{{margin-top:12px;font-size:13px}}.card-notes p{{margin:3px 0}}footer{{border-top:1px solid var(--line);padding-top:22px;margin-top:42px;color:var(--muted);font-size:12px}}footer ul{{padding-left:20px;columns:2}}footer li{{break-inside:avoid;overflow-wrap:anywhere}}@media(max-width:900px){{.responses{{grid-template-columns:1fr}}.reply{{max-height:280px}}}}@media(max-width:650px){{.flow{{grid-template-columns:1fr}}.step{{border-right:0;border-bottom:1px solid var(--line)}}.step:last-child{{border-bottom:0}}.code-grid{{grid-template-columns:1fr}}.controls{{grid-template-columns:1fr}}footer ul{{columns:1}}.theme-button{{float:none;margin-bottom:12px}}}}@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{scroll-behavior:auto!important;animation-duration:.01ms!important;transition-duration:.01ms!important}}}}
</style>
<div class="wrap">
<header class="masthead"><button id="theme-toggle" class="theme-button" type="button">Toggle theme</button><div class="eyebrow">Municipal citizen relations · evaluation record</div><h1>Beldesk — Week 1 baseline</h1><p class="subhead">A field record of how 25 citizen requests changed across three model temperatures.</p><div class="meta">{chip_html}</div></header>
<main>
<p class="caveat"><b>Dataset version:</b> {"Historical v1 responses: input texts are loaded from the recorded run commit. The active v2 set has two TR/EN translation pairs and needs a fresh 75-call run. These saved responses do not measure the new pairs." if data["historical_inputs"] else "Input texts match the recorded baseline hash."}</p>
<section class="major" aria-labelledby="flow-title"><h2 id="flow-title">How a test call works</h2><div class="flow"><div class="step"><span class="step-num">01 / INPUT</span>Test input from <code>week1_inputs.jsonl</code></div><div class="step"><span class="step-num">02 / REQUEST</span>Request to Gemini API</div><div class="step"><span class="step-num">03 / REPLY</span>Model reply + token counts</div><div class="step"><span class="step-num">04 / RECORD</span>Saved to results JSONL, compared and costed</div></div><div class="code-grid"><div class="code-panel"><h3>Request · W1-24, t=0</h3><pre>{esc(request_text)}</pre></div><div class="code-panel"><h3>Response (saved fields) · W1-24, t=0</h3><pre>{esc(json.dumps(saved, ensure_ascii=False, indent=2))}</pre></div></div><details><summary>System prompt</summary><pre>{esc(data["prompt"])}</pre></details><p class="reproduce"><b>Reproduce</b><br><code>{esc(" ".join(meta["command"]))}</code></p></section>
<section class="major" aria-labelledby="summary-title"><h2 id="summary-title">Summary by temperature</h2><div class="table-scroll"><table><thead><tr><th scope="col">Temperature</th><th scope="col">Mean output chars</th><th scope="col">Exact match to t=0</th><th scope="col">Mean output tokens</th><th scope="col">List USD / 1,000</th><th scope="col">Meets</th><th scope="col">Partial</th><th scope="col">Fails</th></tr></thead><tbody>{table_rows}</tbody></table></div><div class="bar-area">{bars}</div><p class="caveat">Manual, single-annotator AI-assisted coding — not a measured metric.</p></section>
<section class="major" aria-labelledby="findings-title"><h2 id="findings-title">Key findings</h2><div class="findings">{findings_html(data["findings"])}</div></section>
<section class="major" aria-labelledby="responses-title"><h2 id="responses-title">All 75 responses</h2><div class="controls"><div class="filters" role="group" aria-label="Category filter">{filter_buttons}</div><span id="visible-count" class="count" aria-live="polite">25 inputs shown</span><div class="control-line"><label for="lang-filter">Language <select id="lang-filter"><option value="all">All</option><option value="tr">TR</option><option value="en">EN</option></select></label><label for="changed-filter"><input id="changed-filter" type="checkbox"> Only where the decision changed with temperature</label><label for="search-filter">Search</label><input id="search-filter" type="search" placeholder="ID or input text" autocomplete="off"></div></div><p id="empty" hidden>No inputs match these filters.</p><div id="input-list">{"".join(cards)}</div></section>
</main><footer><b>Data sources</b><ul>{sources}</ul><p>Generated by <code>scripts/build_explorer.py</code> from commit <code>{esc(data["head"])}</code>.</p></footer></div>
<script type="application/json" id="data">{embedded}</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const cards=[...document.querySelectorAll('.input-card')];
let category='all';
function applyFilters(){{
 const lang=document.getElementById('lang-filter').value;
 const changed=document.getElementById('changed-filter').checked;
 const query=document.getElementById('search-filter').value.trim().toLocaleLowerCase();
 let visible=0;
 for(const card of cards){{
  const show=(category==='all'||card.dataset.category===category)&&(lang==='all'||card.dataset.lang===lang)&&(!changed||card.dataset.changed==='true')&&card.dataset.search.toLocaleLowerCase().includes(query);
  card.hidden=!show;if(show)visible++;
 }}
 document.getElementById('empty').hidden=visible!==0;
 document.getElementById('visible-count').textContent=`${{visible}} inputs shown`;
}}
for(const button of document.querySelectorAll('.filter'))button.addEventListener('click',()=>{{
 category=button.dataset.category;
 for(const other of document.querySelectorAll('.filter')){{const active=other===button;other.classList.toggle('active',active);other.setAttribute('aria-pressed',String(active));}}
 applyFilters();
}});
for(const id of ['lang-filter','changed-filter','search-filter'])document.getElementById(id).addEventListener(id==='search-filter'?'input':'change',applyFilters);
document.getElementById('theme-toggle').addEventListener('click',()=>{{const root=document.documentElement;root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';}});
</script>'''


def main():
    data = build_data()
    OUT.write_text(render(data), encoding="utf-8")
    print(f"Built {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")
    for row in data["summary"]:
        print(f"t={row['temperature']}: " + ", ".join(f"{key}={row['ratings'].get(key, 0)}" for key in ("meets", "partial", "fails")))


if __name__ == "__main__":
    main()
