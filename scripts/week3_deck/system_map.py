"""System map slide: what runs today on the fixed route, and what the agent layer will add.

Facts are read from the repository at build time (file paths are checked, model ids and retry
counts are read from config and source), so the slide cannot drift silently from the code.
"""
from __future__ import annotations

from html import escape
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def h(v):
    return escape(str(v), quote=True)


def _read(path):
    p = ROOT / path
    return p.read_text(encoding='utf-8') if p.exists() else ''


def _int(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def facts(d):
    """Every box on the slide, with its kind, files and the evidence it was derived from."""
    rcfg = json.loads(_read('config/retrieval.json') or '{}')
    acfg = json.loads(_read('config/rag_answer.json') or '{}')
    pipe = _read('src/rag/pipeline.py')
    demo = _read('scripts/try_rag.py')
    cls = _read('src/classifier/classify.py')
    plan = _read('docs/plan_tracker.md')
    api_model = (d['data'].get('availability') or {}).get('model')
    demo_model = (re.search(r"TimedGeminiProvider\('([^']+)'", demo) or [None, None])[1]
    cls_retries = _int(r'classifier_retries: int = (\d+)', pipe)
    rag_retries = _int(r'rag_retries: int = (\d+)', pipe)
    cls_temp = _int(r'provider\.generate\(system \+ feedback, text, (\d+),', cls)
    cfg_retries = acfg.get('max_retries')
    live_emergency = 'emergency_112' in pipe and 'handle_citizen_request' in demo
    eval_skips_classifier = 'handle_citizen_request' not in _read('eval/answer_week3.py')

    def calls(retries):  # one call, plus validation retries when allowed
        if retries is None:
            return 'calls unknown'
        return '1 call' if retries == 0 else f'1–{1 + retries} calls'

    f = {
        'channels': [
            dict(name='CLI demo', file='scripts/try_rag.py', line='classifier → RAG, live', kind='code'),
            dict(name='Eval harness', file='eval/answer_week3.py',
                 line='starts at step 3 · judge runs here' if eval_skips_classifier else 'full route · judge runs here', kind='code'),
            dict(name='Web form · WhatsApp', file='docs/use_case_brief.md', line='customer channels, not built', kind='planned'),
        ],
        'data': [
            dict(name='data/corpus/', file='data/corpus/manifest.json', line=f'{d["n_docs"]} docs → {d["n_chunks"]} chunks', kind='data'),
            dict(name='prompts/', file='prompts/rag/v1.md', line='classifier/v1 · rag/v1', kind='data'),
            dict(name='config/', file='config/retrieval.json', line='retrieval.json · rag_answer.json', kind='data'),
        ],
        'route': [
            dict(n=1, name='Classify', file='src/classifier/classify.py', line='intent, language, issues as JSON', kind='call', reads=['prompts/']),
            dict(n=2, name='Route rule', file='src/rag/pipeline.py', line='emergency → 112 · out of scope → refuse', kind='code'),
            dict(n=3, name='Access gate', file='src/rag/corpus.py', line='public role: staff chunks removed', kind='code', reads=['data/corpus/']),
            dict(n=4, name='Hybrid search', file='src/rag/lexical.py', line=f'BM25 + embeddings, {rcfg.get("candidate_k")} each', kind='local', reads=['data/corpus/', 'config/']),
            dict(n=5, name='Fuse + rerank', file='src/rag/retrieval.py', line=f'RRF k={rcfg.get("rrf_constant")} → reranker → top 5', kind='local', reads=['config/']),
            dict(n=6, name='Answer writer', file='src/rag/answer.py', line='claims + quotes · no source → fixed text', kind='call', reads=['prompts/', 'config/']),
            dict(n=7, name='Quote check', file='src/rag/answer.py', line='quotes must occur in cited source', kind='code'),
        ],
        'right': [
            dict(row=1, name=demo_model or 'null', file='src/baseline/providers.py', kind='call',
                 line=f'T={cls_temp} · JSON · {calls(cls_retries)}'),
            dict(row=2, name='Fixed 112 reply', file='src/rag/pipeline.py', kind='emergency', line='no retrieval, no answer call' if live_emergency else 'not wired'),
            dict(row=4, name=rcfg.get('embedding_model', 'null').split('/')[-1], file='src/rag/models.py', kind='local', line='local CPU · no API'),
            dict(row=5, name=rcfg.get('reranker_model', 'null').split('/')[-1].replace('-v1', ''), file='src/rag/models.py', kind='local', line='local CPU · no API'),
            dict(row=6, name=api_model or 'null', file='src/baseline/providers.py', kind='call',
                 line=f'T={acfg.get("temperature")} · JSON · {calls(rag_retries)} (config allows {cfg_retries} retry)'),
        ],
        'planned': [
            dict(name='Agent loop', week='W4', ref='W4.2', file='docs/plan_tracker.md'),
            dict(name='Doc search tool', week='W4', ref='W4.1', file='docs/plan_tracker.md'),
            dict(name='Data query tool', week='W4', ref='W4.1', file='docs/data_inventory.md'),
            dict(name='Write + confirm', week='W4', ref='W4.7', file='docs/data_inventory.md'),
            dict(name='MCP server', week='W5', ref='W5.1', file='docs/plan_tracker.md'),
            dict(name='Red-team guards', week='W5', ref='W5.5', file='docs/plan_tracker.md'),
        ],
        'meta': dict(api_model=api_model, demo_model=demo_model, cls_retries=cls_retries, rag_retries=rag_retries,
                     cfg_retries=cfg_retries, cls_temp=cls_temp, live_emergency=live_emergency,
                     eval_skips_classifier=eval_skips_classifier,
                     planned_open={p: bool(re.search(r'☐\s*' + re.escape(p) + r'\b', plan)) for p in ('W4.1', 'W4.2', 'W4.7', 'W5.1', 'W5.5')},
                     api_calls_per_request=None),
    }
    for group in ('channels', 'data', 'route', 'right', 'planned'):
        for box in f[group]:
            box['exists'] = (ROOT / box['file']).exists()
    return f


KIND_STYLE = {
    'code': 'background:var(--cream)',
    'call': 'background:var(--cream);border-left:16px solid var(--sun)',
    'local': 'background:var(--cream);border-left:16px solid var(--teal)',
    'data': 'background:var(--tan)',
    'emergency': 'background:var(--tomato-soft)',
    'planned': 'background:transparent;border-style:dashed;box-shadow:none;color:var(--ink-2)',
}
LIT = {'code': '#fff6e0', 'call': '#ffe48a', 'local': '#a9dccf'}

# Geometry (1920×1080)
LX, LW = 96, 440
MX, MW = 600, 590
RX, RW = 1240, 584
Y0, PITCH, BH = 336, 78, 72


def scene(d):
    f = facts(d)
    rows = {b['n']: Y0 + (b['n'] - 1) * PITCH for b in f['route']}
    body = []
    # Legend
    legend = [('code / rule', KIND_STYLE['code']), ('model call · API', KIND_STYLE['call']), ('local model · no API', KIND_STYLE['local']),
              ('data', KIND_STYLE['data']), ('emergency path', KIND_STYLE['emergency']), ('planned, not called', KIND_STYLE['planned'])]
    body.append('<div class="w3-abs sm-legend" style="left:96px;top:240px;display:flex;gap:26px;align-items:center">' + ''.join(
        f'<span style="display:inline-flex;align-items:center;gap:10px;font-size:28px;font-weight:700"><i style="display:inline-block;width:40px;height:26px;border:3px solid var(--ink);border-radius:6px;{st}"></i>{h(t)}</span>'
        for t, st in legend) + '</div>')
    for x, w, t in ((LX, LW, 'Channels · data'), (MX, MW, 'Fixed route · pipeline.py'), (RX, RW, 'Model calls')):
        body.append(f'<p class="bk-label w3-abs sm-head" style="left:{x}px;top:296px;width:{w}px">{h(t)}</p>')

    def card(cls, x, y, w, hgt, box, extra=''):
        return (f'<div class="w3-abs sm-box {cls}" style="left:{x}px;top:{y}px;width:{w}px;height:{hgt}px;padding:6px 14px;border:3px solid var(--ink);'
                f'border-radius:12px;box-shadow:4px 4px 0 var(--ink);{KIND_STYLE[box["kind"]]}{extra}">'
                f'<p style="font-size:28px;font-weight:800;line-height:1.08;white-space:nowrap">{h(box["name"])}</p>'
                f'<p style="font-size:25px;line-height:1.12;color:var(--ink-2);white-space:nowrap">{h(box["line"])}</p></div>')
    # Left lane
    y = 338
    for i, b in enumerate(f['channels']):
        body.append(card(f'sm-ch sm-ch{i}', LX, y, LW, 72, b))
        y += 80
    y += 16
    for i, b in enumerate(f['data']):
        body.append(card(f'sm-data sm-d-{b["name"].strip("/").replace("/", "-")}', LX, y, LW, 72, b))
        y += 80
    # Middle lane
    for b in f['route']:
        y = rows[b['n']]
        body.append(f'<div class="w3-abs sm-box sm-step sm-s{b["n"]}" data-lit="{LIT[b["kind"]]}" style="left:{MX}px;top:{y}px;width:{MW}px;height:{BH}px;padding:3px 14px 3px 64px;'
                    f'border:3px solid var(--ink);border-radius:12px;box-shadow:4px 4px 0 var(--ink);{KIND_STYLE[b["kind"]]}">'
                    f'<span class="w3-mono" style="position:absolute;left:14px;top:12px;width:38px;height:38px;border-radius:50%;border:3px solid var(--ink);background:var(--paper);text-align:center;line-height:32px;font-size:24px;font-weight:700">{b["n"]}</span>'
                    f'<p style="font-size:28px;font-weight:800;line-height:1.08;white-space:nowrap">{h(b["name"])} <span class="w3-mono" style="font-size:22px;font-weight:400;color:var(--ink-2)">{h(b["file"])}</span></p>'
                    f'<p style="font-size:25px;line-height:1.12;color:var(--ink-2);white-space:nowrap">{h(b["line"])}</p></div>')
    out_y = rows[7] + PITCH
    body.append(f'<div class="w3-abs sm-out" style="left:{MX}px;top:{out_y}px;width:{MW}px;height:54px;padding:6px 14px;border:3px solid var(--ink);border-radius:28px;background:var(--teal-soft);font-size:29px;font-weight:800;text-align:center">→ cited answer, or a fixed sentence</div>')
    # Route spine (behind the steps)
    body.append(f'<i class="w3-abs sm-spine" style="left:{MX - 22}px;top:{Y0 + 30}px;width:6px;height:{out_y - Y0}px;background:var(--ink);border-radius:3px;transform-origin:50% 0"></i>')
    # Right lane boxes + arrows
    svg = []
    for b in f['right']:
        y = rows[b['row']]
        body.append(card(f'sm-r sm-r{b["row"]}', RX, y, RW, BH, b))
        cy = y + BH / 2
        cls = {'call': 'sun', 'local': 'teal', 'emergency': 'tomato'}[b['kind']]
        dash = ' dash' if b['kind'] == 'local' else ''
        svg.append(f'<path class="sm-a sm-a{b["row"]} {cls}{dash}" d="M{MX + MW + 6} {cy} L{RX - 10} {cy}"/>')
    # Call-count tags on API arrows
    for b in f['right']:
        if b['kind'] == 'call':
            body.append(f'<span class="w3-tag w3-tag--sun w3-abs sm-n sm-n{b["row"]}" style="left:{MX + MW - 30}px;top:{rows[b["row"]] - 22}px;font-size:24px;padding:0 8px">API</span>')
    # Planned zone
    zy = rows[7] - 6
    body.append(f'<div class="w3-abs sm-zone" style="left:{RX}px;top:{zy}px;width:{RW}px;height:{1000 - zy}px;border:4px dashed var(--ink-2);border-radius:18px"></div>'
                f'<p class="bk-label w3-abs sm-zone-l" style="left:{RX + 18}px;top:{zy + 10}px">planned · not called</p>')
    for i, p in enumerate(f['planned']):
        cx, cy = RX + 16 + (i % 2) * 284, zy + 50 + (i // 2) * 46
        body.append(f'<span class="w3-abs sm-plan sm-p{i}" style="left:{cx}px;top:{cy}px;width:272px;height:40px;padding:0 10px;border:3px dashed var(--ink);border-radius:9px;'
                    f'font-size:26px;font-weight:800;line-height:34px;white-space:nowrap;color:var(--ink-2)">{h(p["name"])} <b class="w3-mono" style="font-size:22px;color:var(--tomato-ink)">{h(p["week"])}</b></span>')
    # Attach points: the agent loop replaces the route rule (2); the doc-search tool wraps steps 3–5.
    ax = RX - 24
    s2, s4 = rows[2] + BH / 2, rows[4] + BH / 2
    svg.append(f'<path class="sm-att dash" d="M{RX} {zy + 70} L{ax} {zy + 70} L{ax} {s2 + 14} L{MX + MW + 6} {s2 + 14}"/>')
    svg.append(f'<path class="sm-att dash" d="M{ax} {s4 + 14} L{MX + MW + 6} {s4 + 14}"/>')
    body.append(f'<svg class="w3-svg sm-svg" viewBox="0 0 1920 1080">{"".join(svg)}</svg>')
    # Loop glyph circling once next to the agent-loop chip
    body.append(f'<div class="w3-abs sm-loop" style="left:{RX + RW - 80}px;top:{zy + 2}px;width:52px;height:52px;border:5px dashed var(--tomato);border-radius:50%;border-right-color:transparent"></div>')
    # Bubble travelling down the route
    body.append(f'<div class="w3-rail-bub w3-abs sm-bub" style="left:{MX - 26}px;top:{rows[1] + 10}px;margin-left:-31px"></div>')
    m = f['meta']
    js = f'''
var steps=$(".sm-step");tl.fromTo(steps,{{opacity:0.3}},{{opacity:0.3,duration:.01}},0);tl.fromTo($(".sm-r, .sm-out"),{{opacity:0.25}},{{opacity:0.25,duration:.01}},0);
BK.fade(tl,".sm-legend",0.2);BK.rise(tl,$(".sm-head"),0.3,{{y:8,stagger:.06}});BK.slam(tl,$(".sm-ch, .sm-data"),0.45,{{stagger:.05}});BK.draw(tl,".sm-spine",0.5,{{axis:"y",duration:.6}});
tl.fromTo($(".sm-zone, .sm-zone-l, .sm-plan, .sm-loop"),{{opacity:0}},{{opacity:0,duration:.01}},0);
tl.fromTo(".sm-bub",{{opacity:0,scale:.5}},{{opacity:1,scale:1,duration:.3,ease:BK.EASE.pop}},0.8);
function lite(n,at){{var s=root.querySelector(".sm-s"+n);tl.fromTo(s,{{opacity:0.3}},{{opacity:1,duration:.2,immediateRender:false}},at);tl.fromTo(s,{{backgroundColor:"#fff6e0"}},{{backgroundColor:s.getAttribute("data-lit"),duration:.25,immediateRender:false}},at);}}
function move(n,at){{tl.fromTo(".sm-bub",{{y:(n-1)*{PITCH}}},{{y:n*{PITCH},duration:.3,ease:BK.EASE.move,immediateRender:false}},at);}}
function pulse(sel,at){{tl.fromTo($(sel),{{scale:1}},{{scale:1.06,duration:.15,immediateRender:false}},at);tl.fromTo($(sel),{{scale:1.06}},{{scale:1,duration:.2,immediateRender:false}},at+.15);}}
function call(r,at){{BK.string(tl,$(".sm-a"+r),at,{{duration:.3}});tl.fromTo(root.querySelector(".sm-r"+r),{{opacity:0.25}},{{opacity:1,duration:.25,immediateRender:false}},at+.15);var n=root.querySelector(".sm-n"+r);if(n)BK.stamp(tl,n,at+.3,{{rotation:0}});}}
var a=P.at[1];lite(1,a);pulse(".sm-d-prompts",a+.1);call(1,a+.2);move(1,a+.55);lite(2,a+.75);call(2,a+.85);
a=P.at[2];move(2,a);lite(3,a+.2);pulse(".sm-d-data-corpus",a+.25);move(3,a+.4);lite(4,a+.6);call(4,a+.65);pulse(".sm-d-config",a+.7);move(4,a+.8);lite(5,a+1.0);call(5,a+1.05);
a=P.at[3];move(5,a);lite(6,a+.2);pulse(".sm-d-prompts",a+.25);call(6,a+.3);move(6,a+.65);lite(7,a+.85);tl.fromTo(root.querySelector(".sm-out"),{{opacity:0.25}},{{opacity:1,duration:.25,immediateRender:false}},a+1.0);
a=P.at[4];tl.fromTo(".sm-zone",{{opacity:0,scale:.96}},{{opacity:1,scale:1,duration:.35,ease:BK.EASE.settle,immediateRender:false}},a);BK.fade(tl,".sm-zone-l",a+.1,{{later:true}});
tl.fromTo($(".sm-plan"),{{opacity:0,y:10}},{{opacity:1,y:0,duration:.25,stagger:.06,immediateRender:false}},a+.2);BK.string(tl,$(".sm-att"),a+.45,{{stagger:.15,duration:.35}});
tl.fromTo(".sm-loop",{{opacity:0,rotation:0}},{{opacity:1,rotation:360,duration:.7,ease:"power1.inOut",immediateRender:false}},a+.3);'''
    api_steps = [b['n'] for b in f['route'] if b['kind'] == 'call']
    notes = (f'Solid boxes run today; dashed ones are plans. A request follows seven fixed steps. '
             f'Only steps {api_steps[0]} and {api_steps[1]} call the {m["api_model"]} API; the embedding model and the reranker run locally, with no API call. '
             + ('An emergency message stops at step two with the fixed 112 reply. ' if m['live_emergency'] else '')
             + ('Our evaluation harness starts at step three, so the classifier was not part of the scores. ' if m['eval_skips_classifier'] else '')
             + 'The agent loop and its tools are not built; they will plug in at the routing step.')
    return dict(id='w3-system', part='next', speaker='Tarık', seconds=29, title='Today a fixed route; the agent loop is still dashed',
                label='System map · today vs planned', folio='BELDESK / SYSTEM MAP', repo='src/rag/pipeline.py · scripts/try_rag.py',
                steps=[1.4, 1.5, 1.4, 1.4], body=''.join(body), js=js, notes=notes, facts=f)
