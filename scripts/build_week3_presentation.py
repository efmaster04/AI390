"""Build the Week 3 deck: "the journey of one question".

One command rebuilds everything from recorded evidence (standard library only, no network, no model calls):

    python3 scripts/build_week3_presentation.py

Outputs
  docs/week3/index.html          single self-contained HTML (HyperFrames 0.9.30 slideshow, opens offline)
  docs/week3/deck_manifest.json  slide order, timing, speakers, narration word counts
  docs/week3_speaking_script.md  the narration, generated from the same notes as the speaker notes

Options
  --composition-dir DIR   also write the raw composition as DIR/index.html for `hyperframes check/snapshot`

The Week 2 deck (docs/week2/index.html) supplies the player, runtime, fonts, design kit and mascot art; it is read,
never edited. Slide content lives in scripts/week3_deck/ (data.py, scenes.py, deck.css, deck.js).
"""
from __future__ import annotations

import argparse
import base64
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from week3_deck import data as deckdata  # noqa: E402
from week3_deck.scenes import build_scenes, fmt, h, plan, ratio, count_of  # noqa: E402

KIT = Path(__file__).resolve().parent / 'week3_deck'
OUT = ROOT / 'docs/week3/index.html'
MANIFEST = ROOT / 'docs/week3/deck_manifest.json'
SCRIPT = ROOT / 'docs/week3_speaking_script.md'
WPM = 150
RECORDED = ('w3-answer', 'w3-r032', 'w3-r032-answer')
PARTS = [('demo', 'What we built · recorded demo', 120), ('scoreboard', 'Scoreboard', 120),
         ('failures', 'Failures and root causes', 120), ('next', 'Next week', 60)]


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.divs = []
        self.poses = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'div':
            self.divs.append(a)
        if tag == 'img' and 'bk-mascot-pose' in a.get('class', '') and self.divs:
            for pose in re.findall(r'bk-mascot--(\w+)', self.divs[-1].get('class', '')):
                if pose not in {'hero', 'aide'}:
                    self.poses.setdefault(pose, a['src'])

    def handle_endtag(self, tag):
        if tag == 'div' and self.divs:
            self.divs.pop()


def words(text):
    return len(re.findall(r"[\w’'.-]+", text))


def strip(text):
    return re.sub('<[^>]+>', '', text)


def qa_slides(d):
    D = d['data']
    base = d['summaries'].get('hybrid_rerank', {})
    n = d['n_answerable']
    hit5 = count_of(base.get('hit_at_k', {}).get('5'), n)
    allf = count_of(base.get('all_gold_hit_at_5'), n)
    rf = D.get('retrieval_failure', {})
    sb = D.get('scoreboard', {})
    cm, apv = d['claims'], d['approvals']
    rm = d['retrieval_meta']
    rec = next((f for f in d['answer_failures'] if f.get('case_id') == rf.get('case_id')), {})
    counts = ', '.join(f'{name} {len(d["stage_cases"][key])}' for key, name in (('retrieval', 'retrieval'), ('generation', 'generation'), ('provider', 'provider'), ('judge', 'judge')))
    if d['stage_cases']['other']:
        counts += f', other {len(d["stage_cases"]["other"])}'
    dev_note = (' ' + ', '.join(dv['id'] for dv in d['deviations']) + ' is an accepted deviation by team decision, not a failure.') if d['deviations'] else ''
    labels = 'approved after the run' if apv['after_run'] else 'with their recorded review status'
    pri = d['priorities']
    return [
        ('w3-q-measurement', 'What did you measure, and how sure are you?',
         f'<strong>Retrieval:</strong> {fmt(n)} answerable citizen questions; hit@5 {ratio(hit5, n)}, all facets@5 {ratio(allf, n)}, MRR@10 {fmt(base.get("mrr_at_10"))}. '
         f'{fmt(d["n_controls"])} controls have their own denominator.',
         f'<strong>Limits:</strong> one small synthetic set, {fmt(apv["cases"])}/{fmt(apv["cases_total"])} cases {labels}; Wilson intervals stay wide (n = {fmt(n)}). Unsupported claims {fmt(cm["numerator"])} / {fmt(cm["n"])} come from a provisional judge.'),
        ('w3-q-failure', 'What failed, and do you know why?',
         f'<strong>{h(rf.get("case_id", "null"))} (root cause: {h(rec.get("stage") or "null")}):</strong> {h(rf.get("note") or rf.get("diagnosis") or "null")}',
         f'<strong>Stages:</strong> {h(counts)} records, counted separately so each points at its own fix.{h(dev_note)}'),
        ('w3-q-priority', 'Is next week’s plan the change that matters most?',
         (f'<strong>{h(pri[0]["priority"])}</strong> moves {h(pri[0]["metric"])}: {h(pri[0]["expected"])}.' if pri else 'null'),
         (' '.join(f'<strong>{h(p["priority"])}</strong> → {h(p["metric"])}.' for p in pri[1:3]) if len(pri) > 1 else 'null')),
        ('w3-q-corpus', f'Why {fmt(d["n_docs"])} documents and {fmt(d["n_chunks"])} chunks?',
         f'<strong>Documents:</strong> {fmt(d["n_public_docs"])} public service guides and {len(d["staff_docs"])} staff-only fixture with source, version and access metadata. The fixture tests the access gate.',
         f'<strong>Chunks:</strong> sections stay whole; a {fmt(d["config"].get("max_words"))}-word cap with {fmt(d["config"].get("overlap_words"))}-word overlap applies only to long sections. Access filtering runs before ranking.'),
        ('w3-q-reproduce', 'Can someone else reproduce these numbers?',
         '<strong>Commands:</strong> <span class="w3-mono" style="font-size:32px">python -m eval.retrieval_week3 · python -m eval.answer_week3 · python -m pytest -q · python scripts/build_week3_presentation.py</span>',
         '<strong>Hashes travel with the results:</strong> ' + h(' · '.join(f'{k} {(rm.get(k + "_sha256") or "null")[:12]}' for k in ('corpus', 'index', 'cases', 'config')))
         + f'; retrieval API calls {fmt(rm.get("api_calls"))}; {fmt(D.get("tests_passed"))} tests passed (recorded).'),
    ]


def build(composition_dir=None, data_override=None, out=OUT, manifest=MANIFEST, script=SCRIPT):
    reference = (ROOT / 'docs/week2/index.html').read_text(encoding='utf-8')
    m = re.search(r'atob\("([A-Za-z0-9+/=]+)"\)', reference)
    if not m:
        raise ValueError('Week 2 composition payload not found')
    comp = base64.b64decode(m[1]).decode()
    parser = AssetParser()
    parser.feed(comp)
    d = deckdata.load(data_override)
    d['wilson'] = deckdata.wilson

    # Week 2 cover, retitled.
    cs = comp.index('<div class="bk-stage">', comp.index('data-composition-file="scenes/cover.html"'))
    ce = comp.index('  </div></div>', cs)
    cover = (comp[cs:ce].replace('WEEK 02', 'WEEK 03').replace('Week 2 —', 'Week 3 —')
             .replace('Prompts and the evaluation harness', 'The journey of one question').replace('Case file / 02', 'Case file / 03'))

    scenes = build_scenes(d, cover)
    qa = qa_slides(d)
    tw = (1728 - 24 * (len(qa) - 1)) // len(qa)
    tiles = ''.join(f'<section class="bk-panel w3-abs qs-t" style="left:{96 + i * (tw + 24)}px;top:400px;width:{tw}px;height:440px;padding:28px 22px;display:flex;flex-direction:column;justify-content:space-between">'
                    f'<h3 style="font-family:var(--font-display);font-weight:900;font-size:36px;line-height:1.12">{h(t)}</h3><div><span class="w3-big" style="font-size:96px">0{i + 1}</span>'
                    f'<p class="bk-label">open answer →</p></div></section>' for i, (_, t, _, _) in enumerate(qa))
    scenes.append(dict(id='w3-questions', part='next', speaker='Tarık', seconds=10, title=f'{["No", "One", "Two", "Three", "Four", "Five", "Six"][len(qa)]} questions we expect', label='Questions and feedback',
                       folio='BELDESK / QUESTIONS', repo='Week 3 / Q&A', steps=[], body=tiles, pose=None,
                       js='BK.slam(tl,$(".qs-t"),0.3,{stagger:.1});',
                       notes=f'Thank you. We are ready for your questions. Each of these {len(qa)} cards opens a prepared answer with the evidence behind it, so pick any of them.'))
    total = len(scenes)
    scenes[0]['raw'] = scenes[0]['raw'].replace('01 / 20', f'01 / {total:02d}')
    poses = parser.poses

    def mascot(pose, sid, style=''):
        src = poses.get(pose) or next(iter(poses.values()))
        return f'<div id="{sid}-mascot" class="bk-mascot bk-mascot--aide bk-mascot--{pose} w3-mascot" style="{style}"><img class="bk-mascot-pose" src="{src}" alt=""></div>'

    mascot_pos = {'scoreboard': '', 'w3-next': 'left:1580px;top:760px;--h:230px'}
    metadata = {'slides': [], 'slideSequences': []}
    hosts, js_parts, offset, clock = [], [], 0.0, 0
    for index, s in enumerate(scenes, 1):
        sid = s['id']
        rests = plan(s.get('steps', []))
        # Windows on a 0.5 s grid keep data-start sums exact (no float overlap between consecutive slides).
        window = math.ceil((rests[-1] + 0.6) * 2) / 2 if sid != 'cover' else 3.0
        s['fragments_local'] = rests
        s['window'] = window
        frags = [round(offset + r, 3) for r in rests]
        note = ('[RECORDED RUN — not live] ' if sid in RECORDED else '') + s['notes']
        s['start_clock'] = clock
        full_note = f'{s["speaker"].upper()} · {s["seconds"]} s · starts {clock // 60}:{clock % 60:02d}\n{note}'
        clock += s['seconds']
        meta = {'sceneId': sid, 'notes': full_note, 'fragments': frags}
        if sid == 'w3-questions':
            meta['hotspots'] = [{'id': f'w3-h{i}', 'label': q[1], 'target': q[0],
                                 'region': {'x': round((96 + i * (tw + 24)) / 19.2, 2), 'y': 37, 'w': round(tw / 19.2, 2), 'h': 41}} for i, q in enumerate(qa)]
        metadata['slides'].append(meta)
        if sid == 'cover':
            stage = s['raw']
        else:
            pose = s.get('pose')
            stage = (f'<div class="bk-stage w3"><div class="bk-sheet"></div><header class="bk-band"><span class="bk-folio">{h(s.get("folio", "AIC390 / WEEK 03"))}</span>'
                     f'<span class="bk-section">{h(s["label"])}</span><span class="bk-no">{index:02d} / {total}</span></header><div class="bk-rule"></div>'
                     f'<h2 class="bk-title">{s["title"]}</h2>{s["body"]}<div class="bk-repo"><span class="bk-repo-k">repo</span>{h(s.get("repo", ""))}</div>'
                     + (mascot(pose, sid, mascot_pos.get(sid, '')) if pose else '') + '</div>')
        fr = ','.join(str(r) for r in rests)
        hosts.append(f'<div data-composition-file="scenes/{sid}.html" id="{sid}" data-composition-id="{sid}" data-label="{index:02d} / {total} {h(strip(s["title"]))}" '
                     f'data-start="{offset}" data-duration="{window}" data-window="{window}" data-track-index="{index - 1}" data-track-kind="graphics" data-width="1920" data-height="1080">'
                     f'<div style="width:1920px;height:1080px" data-hf-inner-root="true" data-hf-authored-id="root" data-hold="" data-width="1920" data-height="1080" data-window="{window}" data-fragments="{fr}">{stage}</div></div>')
        if sid == 'cover':
            js = ("BK.frame(tl,root,0);BK.rise(tl,root.querySelectorAll('.cover-hero,.cover-sub,.cover-team,.cover-repo,.cover-foot,.cover-eyebrow'),.15);"
                  "BK.mascotIn(tl,root.querySelector('#cover-mascot'),.2);BK.stamp(tl,root.querySelector('#cover-stamp'),.65);")
        else:
            js = 'BK.frame(tl,root,0);' + s['js'] + (f'BK.mascotIn(tl,root.querySelector("#{sid}-mascot"),0.3);' if s.get('pose') else '')
        js_parts.append(f'BK.scene({json.dumps(sid)},function(tl,root,BK){{var $=function(s){{return root.querySelectorAll(s);}};var P=BK.plan({json.dumps(s.get("steps", []))});{js}}});')
        offset = round(offset + window, 3)

    for i, (sid, title, p1, p2) in enumerate(qa):
        metadata['slideSequences'].append({'id': sid, 'label': title, 'slides': [{'sceneId': sid, 'notes': strip(p1 + '\n' + p2), 'fragments': [round(offset + 1.4, 3), round(offset + 2.5, 3)]}]})
        stage = (f'<div class="bk-stage w3"><div class="bk-sheet"></div><header class="bk-band"><span class="bk-folio">BELDESK / Q&amp;A</span><span class="bk-section">Week 3</span>'
                 f'<span class="bk-no">Q{i + 1}</span></header><div class="bk-rule"></div><h2 class="bk-title w3-title-sm">{h(title)}</h2>'
                 f'<section class="bk-panel w3-abs qa-a" style="left:96px;top:300px;width:1400px;padding:30px 34px;font-size:38px;line-height:1.27">{p1}</section>'
                 f'<section class="bk-panel w3-abs qa-b" style="left:96px;top:600px;width:1400px;padding:30px 34px;font-size:38px;line-height:1.27">{p2}</section>'
                 f'<p class="w3-cap w3-abs qa-c" style="left:96px;top:920px">Left arrow returns to the question slide.</p>{mascot("dusunen", sid, "left:1560px;top:620px")}</div>')
        hosts.append(f'<div data-composition-file="scenes/{sid}.html" id="{sid}" data-composition-id="{sid}" data-label="Q{i + 1} {h(title)}" data-start="{offset}" data-duration="3.5" data-window="3.5" '
                     f'data-track-index="{total + i}" data-track-kind="graphics" data-width="1920" data-height="1080"><div style="width:1920px;height:1080px" data-hf-inner-root="true" '
                     f'data-hf-authored-id="root" data-hold="" data-width="1920" data-height="1080" data-window="3.5" data-fragments="1.4,2.5">{stage}</div></div>')
        js_parts.append(f'BK.scene({json.dumps(sid)},function(tl,root,BK){{BK.frame(tl,root,0);BK.slam(tl,root.querySelector(".qa-a"),0.3);'
                        f'BK.slam(tl,root.querySelector(".qa-b"),1.45);BK.fade(tl,root.querySelector(".qa-c"),1.7);BK.mascotIn(tl,root.querySelector("#{sid}-mascot"),0.3);}});')
        offset = round(offset + 3.5, 3)

    css = (KIT / 'deck.css').read_text(encoding='utf-8')
    kitjs = (KIT / 'deck.js').read_text(encoding='utf-8')
    head = comp[:comp.index('</head>')].replace('<title>Beldesk Week 2</title>', '<title>Beldesk Week 3</title>')
    head += f'<style>{css}</style></head>'
    config = json.dumps(metadata, ensure_ascii=False, indent=2).replace('</', '<\\/')
    anim = kitjs + '\nwindow.__timelines=window.__timelines||{};\n' + '\n'.join(js_parts)
    composition = (head + '<body><script type="application/hyperframes-slideshow+json">' + config + '</script>'
                   + f'<div id="main" data-composition-id="main" data-start="0" data-duration="{offset}" data-width="1920" data-height="1080">' + ''.join(hosts)
                   + '</div><script type="text/hf-after-fonts">' + anim.replace('</script', '<\\/script') + '</script></body></html>')
    output = reference.replace('<title>Beldesk Week 2</title>', '<title>Beldesk Week 3</title>').replace('notes-storage-key="beldesk-week2"', 'notes-storage-key="beldesk-week3"')
    output = re.sub(r'(<script type="application/hyperframes-slideshow\+json">).*?(</script>)', lambda mm: mm[1] + config + mm[2], output, count=1, flags=re.S)
    payload = base64.b64encode(composition.encode()).decode()
    output = re.sub(r'atob\("[A-Za-z0-9+/=]+"\)', lambda _: f'atob("{payload}")', output, count=1)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(output, encoding='utf-8')
    if Path(out) == OUT:  # the GitHub Pages root shows the current week's deck
        (ROOT / 'docs/index.html').write_text(output, encoding='utf-8')
    if composition_dir:
        cd = Path(composition_dir)
        cd.mkdir(parents=True, exist_ok=True)
        (cd / 'index.html').write_text(composition, encoding='utf-8')
        (cd / 'hyperframes.json').write_text(json.dumps({'paths': {'blocks': 'compositions', 'components': 'compositions/components', 'assets': 'assets'}, 'media': {'autoProxy': True}}, indent=2))
        (cd / 'meta.json').write_text(json.dumps({'id': 'beldesk-week3', 'name': 'Beldesk Week 3'}))

    # ---- manifest + speaking script from the same notes ----
    speakers = {}
    for i, s in enumerate(scenes, 1):
        speakers.setdefault(s['speaker'], []).append(i)
    part_secs = {p: sum(s['seconds'] for s in scenes if s['part'] == p) for p, _, _ in PARTS}
    part_words = {p: sum(words(s['notes']) for s in scenes if s['part'] == p) for p, _, _ in PARTS}
    man = {'title': 'Beldesk Week 3 — the journey of one question', 'build_command': 'python3 scripts/build_week3_presentation.py',
           'total_speaking_seconds': sum(s['seconds'] for s in scenes), 'words_per_minute': WPM,
           'parts': [{'part': p, 'label': lbl, 'target_seconds': t, 'planned_seconds': part_secs[p], 'narration_words': part_words[p],
                      'narration_seconds_at_wpm': round(part_words[p] * 60 / WPM)} for p, lbl, t in PARTS],
           'speakers': {k: f'{v[0]}–{v[-1]}' for k, v in speakers.items()},
           'slides': [{'no': i, 'id': s['id'], 'title': strip(s['title']), 'label': s['label'], 'part': s['part'], 'speaker': s['speaker'],
                       'seconds': s['seconds'], 'narration_words': words(s['notes']), 'fragments_local': s['fragments_local'], 'window_s': s['window'],
                       'recorded_run': s['id'] in RECORDED, 'notes': s['notes'], 'repo': s.get('repo', '')}
                      for i, s in enumerate(scenes, 1)],
           'qa_branches': [q[0] for q in qa], 'source_data': str(deckdata.DATA.relative_to(ROOT)), 'reference': 'docs/week2/index.html (read only)',
           'note': 'Generated file. Numbers are read from recorded result files at build time; missing values print as null.'}
    Path(manifest).write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Beldesk Week 3 — seven-minute speaking script', '',
             '_Generated by `python3 scripts/build_week3_presentation.py` from the same notes as the speaker notes. Edit scripts/week3_deck/scenes.py, not this file._', '',
             f'English delivery, {len(scenes)} slides, about {man["total_speaking_seconds"]} s at {WPM} words per minute. '
             + ' · '.join(f'**{k}: slides {v}**' for k, v in man['speakers'].items()) + '.', '',
             'Parts: ' + ' · '.join(f'{p["label"]} {p["planned_seconds"]} s ({p["narration_words"]} words ≈ {p["narration_seconds_at_wpm"]} s)' for p in man['parts']), '']
    for p, lbl, _ in PARTS:
        lines += [f'## {lbl}', '']
        for i, s in enumerate(scenes, 1):
            if s['part'] != p:
                continue
            c = s['start_clock']
            tag = ' · recorded run, not live' if s['id'] in RECORDED else ''
            lines += [f'### {i} · {strip(s["title"])} · {s["speaker"]} · {s["seconds"]} s · {c // 60}:{c % 60:02d}{tag}', s['notes'], '']
    lines += ['## Prepared answers (Q&A branches, not part of the seven minutes)', '']
    for sid, title, p1, p2 in qa:
        lines += [f'### {title}', strip(p1), '', strip(p2), '']
    Path(script).write_text('\n'.join(lines), encoding='utf-8')
    print(f'Created {out}: {len(scenes)} main slides + {len(qa)} Q&A branches; {man["total_speaking_seconds"]} planned s; '
          + ', '.join(f'{p["part"]} {p["planned_seconds"]}s/{p["narration_seconds_at_wpm"]}s spoken' for p in man['parts']) + f'; {len(output):,} bytes')
    return man


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--composition-dir')
    build(ap.parse_args().composition_dir)
