"""Week 3 scenes: "the journey of one question".

Each scene returns a dict with its HTML body (inside .bk-stage), its timeline code (run inside
BK.scene with tl, root, BK, W3, P in scope), its step plan (fragment holds) and its narration.
All numbers come from week3_deck.data.load(); missing values print as "null".
"""
from __future__ import annotations

from html import escape
import re

STATIONS = ['Question', 'Access gate', 'BM25 | Embeddings', 'RRF', 'Reranker', 'Cited answer', 'Measured']
RAIL_W = 1700


def h(v):
    return escape(str(v), quote=True)


def fmt(v, d=3):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, float):
        return f'{v:.{d}f}'
    return str(v)


def count_of(rate, n):
    if not isinstance(rate, (int, float)) or not isinstance(n, int):
        return None
    return int(round(rate * n))


def ratio(k, n):
    return f'{fmt(k)} / {fmt(n)}'


def plan(steps):
    rests = [1.4]
    for s in steps:
        rests.append(round(rests[-1] + s, 3))
    return rests


# Hand-made English glosses for the recorded Turkish texts. Keyed by the exact recorded text, so a
# changed recording simply drops the gloss instead of showing a stale translation.
GLOSS = {
    'Yeni taşındığım evde kiracıyım. Su aboneliğini üzerime almak için ne hazırlamalıyım? Önceki abone numarasını bilmiyorum.':
        'I rent the home I just moved into. What do I prepare to put the water subscription in my name? I don’t know the previous subscriber number.',
    'Yeni su aboneliği başvurusu için kimlik belgesi, kullanım adresini gösteren bir belge ve kira sözleşmesi hazırlamanız gerekmektedir.':
        'Prepare an ID, a document showing the address and the rental agreement.',
    'Eski abone numarasını bilmiyorsanız, kullanım adresi ve diğer belgelerle başvuru yapmaya devam edebilirsiniz.':
        'Without the old number you can still apply with the address and the other documents.',
    'Su aboneliği başvurunuzu Su ve Kanalizasyon başvuru birimine yapmalısınız.':
        'Apply at the Water and Sewerage application unit.',
}
# Facet phrases of the failing case, per registered gold group (document id -> phrase in the question).
FACET_PHRASES = {'YV-D006': 'What do we need for permission', 'YV-D019': 'how can we report the access problem'}


def reason_of(note):
    """The sentence of a status note that explains why an item is open (else the whole note)."""
    parts = re.split(r'(?<=[.;])\s+(?=[A-Z])', note.strip())
    hit = [p for p in parts if re.match(r'(Not done|Partial|Open|Pending)', p)]
    return (hit[-1] if hit else note).strip()


def rail(at, came_from=None, bad=None, bub_bad=False, extra=''):
    xs = [14 + i * RAIL_W / 6 for i in range(7)]
    out = ['<div class="w3-rail"><i class="w3-rail-line"></i>']
    if at > 0:
        out.append(f'<i class="w3-rail-done" style="width:{xs[at] - 14:.0f}px"></i>')
    for i, name in enumerate(STATIONS):
        cls = 'is-done' if i < at else 'is-now' if i == at else ''
        if bad is not None and i == bad:
            cls = 'is-bad'
        last = ' is-last' if i == 6 else ''
        dot = '<i></i><b></b>' if i == 2 else '<b></b>'
        out.append(f'<div class="w3-st {cls}{last}" style="left:{xs[i]:.0f}px">{dot}<span>{h(name)}</span></div>')
    src = xs[came_from] - xs[at] if came_from is not None else -120
    out.append(f'<div class="w3-rail-bub{" is-bad" if bub_bad else ""}" style="left:{xs[at]:.0f}px" data-from="{src:.0f}"></div>{extra}</div>')
    return ''.join(out)


def rail_dx(a, b):
    return (b - a) * RAIL_W / 6


def card(c, x, y, w, badge, alt=None, score=None, cid='', extra='', dy=None):
    if c.get('pid') is None:
        return (f'<div class="w3-card is-unknown" style="left:{x}px;top:{y}px;width:{w}px"><span class="w3-rk"><span>{h(c.get("rank"))}</span></span>'
                f'<span class="w3-ttl">chunk outside the final top 10 · not recorded</span></div>')
    cls = 'w3-card is-gold' if c.get('gold') else 'w3-card'
    rk = f'<span class="w3-rk"><span class="rk-a">{h(badge)}</span>' + (f'<span class="rk-b">{h(alt)}</span>' if alt is not None else '') + '</span>'
    sc = f'<span class="w3-sc">{h(score)}</span>' if score is not None else ''
    d = f' data-dy="{dy}"' if dy is not None else ''
    title = c.get('title_en') or ''
    return (f'<div class="{cls}" id="{cid}" style="left:{x}px;top:{y}px;width:{w}px"{d}>{rk}<span class="w3-pid">{h(c["pid"])}</span>'
            f'<span class="w3-ttl">{h(title)}</span>{sc}{extra}</div>')


def ranklist(prefix, cards, x, y, w, pitch=84, gap=40):
    """Cards laid out in rerank order; each starts at its fused slot (data-dy) and moves on W3.reorder."""
    fused_order = sorted(cards, key=lambda c: (c.get('fused') or 99))
    rerank_order = sorted(cards, key=lambda c: (c.get('rerank') or 99))

    def top(i):
        return y + i * pitch + (gap if i >= 5 else 0)
    html = []
    for c in cards:
        fi, ri = fused_order.index(c), rerank_order.index(c)
        jump = (c.get('fused') or 0) - (c.get('rerank') or 0)
        tag = ''
        if c.get('fused') and c.get('rerank') and abs(jump) >= 2:
            tag = f'<span class="w3-jump{" down" if jump < 0 else ""}">{"↑" if jump > 0 else "↓"} {abs(jump)}</span>'
        html.append(card(c, x, top(ri), w, c.get('fused') or '–', c.get('rerank') or '–', cid=f'{prefix}-{c["pid"].replace("#", "-")}',
                         extra=tag, dy=top(fi) - top(ri)))
    return ''.join(html), top(5) - gap / 2


def scene_js(body):
    return body


# ===================================================================== scenes
def build_scenes(d, cover_html):
    D = d['data']
    S = []
    sb = D.get('scoreboard', {})
    base = d['summaries'].get('hybrid_rerank', {})
    nrr = d['summaries'].get('hybrid_no_rerank', {})
    dense = d['summaries'].get('dense_rerank', {})
    n = d['n_answerable']
    hit = {k: base.get('hit_at_k', {}).get(k) for k in ('1', '3', '5', '10')}
    hitc = {k: count_of(v, n) for k, v in hit.items()}
    allf = base.get('all_gold_hit_at_5')
    allc = count_of(allf, n)
    mrr = base.get('mrr_at_10')
    dj, da = d['demo_journey'], d['demo_answer']
    fj, fa = d['fail_journey'], d['fail_answer']
    demo = D.get('demo', {})

    def add(**kw):
        kw.setdefault('pose', None)
        kw.setdefault('repo', '')
        S.append(kw)

    # ------------------------------------------------------------ 1 cover
    add(id='cover', part='demo', speaker='Efe', seconds=10, title='Beldesk — Week 3', label='Opening', steps=[], raw=cover_html,
        js='', notes='Hello, we are Beldesk, a Turkish and English assistant for the fictional Yeşilvadi Municipality. Today you follow one real citizen question through our new retrieval pipeline.')

    # ------------------------------------------------------------ 2 roadmap
    names = [('W3.1', 'Corpus', f'{fmt(d["n_docs"])} synthetic documents with source, version and access metadata'),
             ('W3.2', 'Chunking', f'{fmt(d["n_chunks"])} section-aware chunks'),
             ('W3.3', 'Hybrid search', 'BM25 + embeddings + RRF + reranker'),
             ('W3.4', 'Cited answers', 'Numbered citations and a fixed fallback'),
             ('W3.5', 'Retrieval set', f'{fmt(n)} answerable questions + {fmt(d["n_controls"])} controls'),
             ('W3.6', 'Faithfulness', 'Claim-level judge + human calibration'),
             ('W3.7', 'Two ablations', 'Dense vs hybrid; reranker on / off'),
             ('W3.8', 'Failure analysis', 'Each failure assigned to one stage')]
    deliv = D.get('deliverables', {})
    tiles = []
    for i, (did, name, default) in enumerate(names):
        st = deliv.get(did, {}) if isinstance(deliv.get(did), dict) else {}
        status = st.get('status') or 'null'
        note = (st.get('card_note') or '').strip() or (st.get('note') or '').strip() or default
        if status != 'done' and not st.get('card_note'):  # an open item shows the sentence that says why it is open
            note = reason_of(note)
        col, row = i % 2, i // 2
        kind = 'teal' if status == 'done' else 'sun' if status == 'partial' else 'muted'
        tiles.append(f'<section class="bk-panel w3-abs rm-tile" style="left:{96 + col * 880}px;top:{268 + row * 174}px;width:848px;height:168px;padding:10px 24px">'
                     f'<div style="display:flex;align-items:center;gap:18px"><span class="w3-mono" style="font-size:34px;font-weight:700">{did}</span>'
                     f'<span style="font-family:var(--font-display);font-weight:900;font-size:40px">{h(name)}</span>'
                     f'<span class="w3-tag w3-tag--{kind} rm-chip" style="margin-left:auto">{h(status)}</span></div>'
                     f'<p class="w3-cap" style="margin-top:2px;font-size:28px;line-height:1.08">{h(note)}</p></section>')
    partial = [did for did, *_ in names if isinstance(deliv.get(did), dict) and deliv[did].get('status') != 'done']
    add(id='w3-roadmap', part='demo', speaker='Efe', seconds=10, title='Eight deliverables and where each one stands', label='Week 3 / W3.1–W3.8',
        folio='BELDESK / MAP', repo='reports/week-3.md · eval/results/week3/presentation_data.json', steps=[1.1],
        body=''.join(tiles),
        js='''var t=$(".rm-tile");BK.slam(tl,[t[0],t[1],t[2],t[3]],0.3,{stagger:0.08});BK.stamp(tl,[$(".rm-chip")[0],$(".rm-chip")[1],$(".rm-chip")[2],$(".rm-chip")[3]],0.8,{stagger:0.06,rotation:0});
BK.slam(tl,[t[4],t[5],t[6],t[7]],P.at[1],{stagger:0.08});BK.stamp(tl,[$(".rm-chip")[4],$(".rm-chip")[5],$(".rm-chip")[6],$(".rm-chip")[7]],P.at[1]+0.4,{stagger:0.06,rotation:0});''',
        notes=(('All eight requirements are done' if not partial else f'Eight requirements this week. {8 - len(partial)} are done')
               + ''.join(f'; {p_} is {deliv[p_].get("status")}, and its card gives the reason' for p_ in partial)
               + ''.join(f'; {did} rests on a team decision about {dv["id"]} taken after seeing the results' for did, *_ in names for dv in d['deviations']
                         if isinstance(deliv.get(did), dict) and dv['id'] in (deliv[did].get('note') or '') and dv.get('after_results'))
               + '. Each status comes from our data file.'))

    # ------------------------------------------------------------ 3 gate
    q = dj['query'] if dj else demo.get('question_tr')
    gloss = GLOSS.get(q)
    chunks = d['chunk_list']
    cols, tw, th, gx, gy = 12, 58, 34, 10, 10
    fx, fy = 1006, 430
    tiles = []
    staff_ix = [i for i, c in enumerate(chunks) if 'public' not in c.get('access', [])]
    tray_x, tray_y = 1006, 878
    for i, c in enumerate(chunks):
        x, y = fx + (i % cols) * (tw + gx), fy + (i // cols) * (th + gy)
        if i in staff_ix:
            k = staff_ix.index(i)
            tx, ty = tray_x + 250 + k * (tw + 16), tray_y
            tiles.append(f'<i class="w3-abs gt-staff" style="left:{x}px;top:{y}px;width:{tw}px;height:{th}px;border:3px solid var(--ink);border-radius:6px;background:var(--tomato)" data-tx="{tx - x}" data-ty="{ty - y}"></i>')
        else:
            tiles.append(f'<i class="w3-abs gt-tile" style="left:{x}px;top:{y}px;width:{tw}px;height:{th}px;border:3px solid var(--ink);border-radius:6px;background:var(--cream)"></i>')
    rows = (len(chunks) + cols - 1) // cols
    field_h = rows * (th + gy)
    staff_doc = d['staff_docs'][0] if d['staff_docs'] else {}
    n_pub_chunks = (d['n_chunks'] - len(d['staff_chunks'])) if isinstance(d['n_chunks'], int) else None
    body = rail(1, 0)
    body += (f'<div class="w3-bubble gt-bub" style="left:96px;top:430px;width:820px"><span class="w3-q">{h(q)}</span>'
             + (f'<span class="w3-gloss"><b data-layout-ignore>EN</b>{h(gloss)}</span>' if gloss else '') + '</div>')
    body += f'<p class="bk-label w3-abs gt-case" style="left:96px;top:384px">{h(dj["case_id"] if dj else "null")} · role = public</p>'
    body += f'<p class="bk-label w3-abs gt-h" style="left:{fx}px;top:372px"><span class="gt-n1">{fmt(d["n_docs"])} documents → {fmt(d["n_chunks"])} chunks</span></p>'
    body += ''.join(tiles)
    body += f'<i class="w3-abs gt-gate" style="left:{fx - 26}px;top:{fy - 12}px;width:10px;height:{field_h + 6}px;background:var(--ink);border-radius:5px"></i>'
    body += (f'<div class="w3-abs gt-tray" style="left:{tray_x}px;top:{tray_y - 14}px;width:820px;height:64px;border:4px dashed var(--tomato);border-radius:14px"></div>'
             f'<p class="w3-abs w3-mono gt-tray-l" style="left:{tray_x + 18}px;top:{tray_y - 4}px;font-size:28px;font-weight:700;color:var(--tomato-ink)">{h(staff_doc.get("doc_id", "null"))} staff</p>'
             f'<span class="bk-stamp bk-stamp--tomato w3-abs gt-stamp" style="left:{tray_x + 400}px;top:{tray_y - 6}px;font-size:28px;padding:2px 12px" data-layout-allow-overlap>removed before ranking</span>')
    body += (f'<div class="bk-panel w3-abs gt-left" style="left:96px;top:840px;width:820px;padding:18px 26px"><span class="w3-big gt-count" style="font-size:72px;color:var(--teal-ink)">{fmt(d["n_chunks"])}</span>'
             f'<span class="w3-cap" style="margin-left:14px">chunks may compete for a public question</span></div>')
    add(id='w3-gate', part='demo', speaker='Efe', seconds=18, title='One question enters; staff-only text never competes', label='W3.1 / W3.2 · access gate',
        folio='THE JOURNEY · 1/4', repo='src/rag/retrieval.py · data/corpus/', steps=[1.3, 1.1], body=body,
        js=f'''W3.rail(tl,root,0.15);BK.slam(tl,".gt-bub",0.35);BK.fade(tl,".gt-case",0.7);
BK.rise(tl,".gt-h",0.5,{{y:8}});tl.fromTo($(".gt-tile, .gt-staff"),{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:.25,stagger:{{each:.006,from:"start"}},ease:"power2.out"}},0.55);
BK.slam(tl,".gt-left",0.8);
BK.draw(tl,".gt-gate",P.at[1],{{axis:"y",duration:.35}});BK.fade(tl,".gt-tray, .gt-tray-l",P.at[1]+0.1);
$(".gt-staff").forEach(function(e){{tl.fromTo(e,{{x:0,y:0}},{{x:+e.getAttribute("data-tx"),y:+e.getAttribute("data-ty"),duration:.7,ease:"power2.inOut"}},P.at[1]+0.25);}});
BK.count(tl,".gt-count",{n_pub_chunks if n_pub_chunks is not None else 0},P.at[1]+0.4,{{from:{d["n_chunks"] or 0},duration:.6}});
BK.stamp(tl,".gt-stamp",P.at[2]);tl.fromTo($(".gt-tile"),{{backgroundColor:"#fff6e0"}},{{backgroundColor:"#a9dccf",duration:.3,stagger:.003,immediateRender:false}},P.at[2]+0.1);''',
        notes=(('Here is the question: a tenant asks what to prepare for a water subscription and does not know the old subscriber number. ' if gloss else 'Here is the recorded citizen question. ') +
               f'Before any ranking, an access gate removes the staff-only document, {staff_doc.get("doc_id", "null")}. Its {len(d["staff_chunks"])} chunks never compete, '
               f'so {fmt(n_pub_chunks)} of {fmt(d["n_chunks"])} section chunks remain for a public question.'))

    # ------------------------------------------------------------ 4 lanes
    lx, rx, lw, ly, pitch = 96, 1006, 818, 470, 92
    body = rail(2, 1)
    body += (f'<div class="bk-panel w3-abs ln-hl" style="left:{lx}px;top:384px;width:{lw}px;padding:12px 22px"><span style="font-family:var(--font-display);font-weight:900;font-size:40px">BM25</span>'
             f'<span class="w3-cap" style="margin-left:14px">shared words · score</span></div>'
             f'<div class="bk-panel w3-abs ln-hr" style="left:{rx}px;top:384px;width:{lw}px;padding:12px 22px"><span style="font-family:var(--font-display);font-weight:900;font-size:40px">Embeddings</span>'
             f'<span class="w3-cap" style="margin-left:14px">shared meaning · cosine</span></div>')
    links = []
    if dj and dj['bm25'] and dj['dense']:
        for side, lane, x, key, dg in (('l', dj['bm25'], lx, 'bm25_score', 2), ('r', dj['dense'], rx, 'dense_score', 3)):
            for i, c in enumerate(lane):
                sc = fmt(c.get(key), dg) if c.get('pid') else None
                body += card(dict(c, rank=i + 1) if c.get('pid') is None else c, x, ly + 22 + i * pitch, lw, i + 1, score=sc, cid=f'ln-{side}{i}').replace('w3-card', f'w3-card ln-{side}', 1)
        lpos = {c['pid']: i for i, c in enumerate(dj['bm25']) if c.get('pid')}
        for j, c in enumerate(dj['dense']):
            if c.get('pid') in lpos:
                i = lpos[c['pid']]
                y1, y2 = ly + 22 + i * pitch + 36, ly + 22 + j * pitch + 36
                links.append(f'<path class="ln-link {"sun" if c.get("gold") else "dash"}" d="M{lx + lw + 4} {y1} C{(lx + lw + rx) / 2} {y1} {(lx + lw + rx) / 2} {y2} {rx - 4} {y2}"/>')
    else:
        body += '<p class="w3-lead w3-abs" style="left:96px;top:520px">Lane ranks: null (not recoverable from the recorded scores)</p>'
    body += f'<svg class="w3-svg" viewBox="0 0 1920 1080">{"".join(links)}</svg>'
    body += f'<p class="bk-note bk-note--plain bk-note--ink w3-abs ln-foot" style="left:96px;top:940px;font-size:28px">Lane ranks recovered from the recorded RRF scores (k = {fmt(d["config"].get("rrf_constant"))}); dashed = a chunk not in the recorded top 10.</p>'
    both = len(links)
    add(id='w3-lanes', part='demo', speaker='Efe', seconds=19, title='Two searches rank the same chunks differently', label='W3.3 · two lanes',
        folio='THE JOURNEY · 2/4', repo='src/rag/lexical.py · src/rag/retrieval.py', steps=[1.2, 1.2, 1.1], body=body,
        js='''W3.rail(tl,root,0.15);BK.slam(tl,".ln-hl, .ln-hr",0.35,{stagger:.1});
tl.fromTo($(".ln-l"),{opacity:0,x:-60},{opacity:1,x:0,duration:.35,stagger:.12,ease:BK.EASE.settle},P.at[1]);
tl.fromTo($(".ln-r"),{opacity:0,x:60},{opacity:1,x:0,duration:.35,stagger:.12,ease:BK.EASE.settle},P.at[2]);
BK.string(tl,$(".ln-link"),P.at[3],{stagger:.12});BK.note(tl,".ln-foot",P.at[3]+0.3);''',
        notes=(f'The question now splits into two lanes. BM25 ranks chunks by shared words; the multilingual embedding model ranks them by meaning. '
               + (f'Both put {dj["bm25"][0]["pid"]} first, but the rest of the lists differ. ' if dj and dj['bm25'] and dj['dense'] and dj['bm25'][0].get('pid') and dj['bm25'][0].get('pid') == dj['dense'][0].get('pid') else 'The two lists differ. ')
               + f'The lines connect the {both} chunks both lanes found in their top five.'))

    # ------------------------------------------------------------ 5 fuse
    body = rail(3, 2)
    if dj:
        rl, cut_y = ranklist('fu', dj['cards'], 630, 392, 610)
        body += rl
        body += f'<div class="w3-cut fu-cut" style="left:612px;top:{cut_y:.0f}px;width:650px"><span>top-5 cut</span></div>'
        top5 = sorted([c for c in dj['cards'] if c.get('rerank') and c['rerank'] <= 5], key=lambda c: c['rerank'])
        slots = ''.join(f'<span class="w3-slot fu-slot">[{c["rerank"]}] <b>{h(c["pid"])}</b></span>' for c in top5)
        body += f'<div class="w3-model fu-model" style="left:1300px;top:392px;width:524px"><h4>→ answer model</h4>{slots}</div>'
        req = next((c for c in dj['cards'] if c.get('gold')), None)
        jumper = max(dj['cards'], key=lambda c: (c.get('fused') or 0) - (c.get('rerank') or 0))
        fx_ = (f'<div class="bk-panel w3-abs fu-fx" style="left:96px;top:392px;width:490px;padding:22px 24px"><span class="bk-tab bk-tab--sun">RRF</span>'
               f'<p class="w3-mono" style="font-size:30px;line-height:1.4;margin-top:6px">score =<br>1/({fmt(d["config"].get("rrf_constant"))}+r<sub>BM25</sub>)<br>+ 1/({fmt(d["config"].get("rrf_constant"))}+r<sub>dense</sub>)</p>'
               f'<p class="w3-cap" style="margin-top:10px">{h(req["pid"] if req else "null")}: ranks {fmt(req.get("lane_bm25") if req else None)} and {fmt(req.get("lane_dense") if req else None)} → {fmt(req.get("rrf_score") if req else None, 4)}</p></div>'
               f'<div class="bk-panel w3-abs fu-rr" style="left:96px;top:700px;width:490px;padding:22px 24px"><span class="bk-tab bk-tab--teal">Reranker</span>'
               f'<p class="w3-cap" style="margin-top:6px">A cross-encoder reads question + passage together. {h(jumper["pid"])} moves {fmt(jumper.get("fused"))} → {fmt(jumper.get("rerank"))}.</p></div>')
        body += fx_
    add(id='w3-fuse', part='demo', speaker='Efe', seconds=18, title='RRF merges the lists; the reranker reads each passage', label='W3.3 · fuse and rerank',
        folio='THE JOURNEY · 3/4', repo='config/retrieval.json · src/rag/retrieval.py', steps=[1.3, 1.2], body=body,
        js=f'''W3.rail(tl,root,0.15);BK.slam(tl,".fu-fx",0.35);
tl.fromTo($(".w3-card"),{{opacity:0,x:function(i){{return i%2?90:-90;}}}},{{opacity:1,x:0,duration:.4,stagger:.08,ease:BK.EASE.settle}},0.55);
W3.railStep(tl,root,{rail_dx(3, 4):.0f},P.at[1],3,4);BK.slam(tl,".fu-rr",P.at[1]);W3.reorder(tl,root,P.at[1]+0.15);
$(".w3-card").forEach(function(c){{var a=c.querySelector(".rk-a"),b=c.querySelector(".rk-b");if(b){{W3.flip(tl,a,b,P.at[1]+0.5);}}var j=c.querySelector(".w3-jump");if(j)BK.stamp(tl,j,P.at[1]+0.7,{{rotation:0}});}});
BK.draw(tl,".fu-cut",P.at[2],{{duration:.5}});BK.slam(tl,".fu-model",P.at[2]+0.15);BK.rise(tl,$(".fu-slot"),P.at[2]+0.4,{{y:8,stagger:.08}});''',
        notes=(f'Reciprocal rank fusion merges the two lists using only their ranks, so one constant k equal to {fmt(d["config"].get("rrf_constant"))} replaces score calibration. '
               f'Then a cross-encoder reranker reads the question together with each passage. {jumper["pid"] if dj else "null"} jumps from {fmt(jumper.get("fused")) if dj else "null"} to {fmt(jumper.get("rerank")) if dj else "null"}. Only the top five reach the model.'))

    # ------------------------------------------------------------ 6 demo answer
    body = rail(5, 4)
    claims = da['claims'] if da else []
    lines = []
    for i, cl in enumerate(claims):
        cites = ''.join(f'<span class="w3-cite an-c{i}">[{c}]</span>' for c in cl.get('citations', []))
        g = GLOSS.get(cl.get('text'))
        prompt = '<b class="bk-term-bot">beldesk&gt;</b> ' if i == 0 else ''
        lines.append(f'<span class="w3-claim an-l{i}">{prompt}<span class="an-t{i}">{h(cl.get("text"))}</span>{cites}'
                     + (f'<span class="w3-en an-e{i}"><b data-layout-ignore>EN</b>{h(g)}</span>' if g else '') + '</span>')
    labels = [c.get('label') for c in (da['judge_claims'] if da else [])]
    sup = sum(l == 'supported' for l in labels)
    term = (f'<div class="bk-term w3-term an-term" style="left:96px;top:378px;width:1110px"><div class="bk-term-bar"><i></i><i></i><i></i><b>recorded run · not live · {h(dj["case_id"] if dj else "null")}</b></div>'
            f'<div class="bk-term-body">{"".join(lines)}<span class="bk-term-meta an-meta">judge: {sup} / {len(labels)} claims supported</span></div></div>')
    body += term + '<div class="w3-abs an-col" style="left:1256px;top:378px;width:568px;display:flex;flex-direction:column;gap:22px">'
    srcs = {}
    for i, cl in enumerate(claims):
        for ev in cl.get('evidence', []):
            srcs.setdefault(ev.get('citation'), []).append((i, ev.get('quote')))
    sy = 380
    paths = []
    for cit in sorted(srcs):
        s = next((x for x in da['sources'] if x.get('citation') == cit), {})
        quotes = ' … '.join(f'<span class="bk-scan bk-scan--sun an-q{i}">{h(qt)}</span>' for i, qt in srcs[cit])
        body += (f'<div class="w3-src an-s{cit}"><div class="w3-src-h"><span class="w3-cite">[{cit}]</span>'
                 f'<span class="w3-mono" style="font-size:28px;font-weight:700">{h(s.get("passage_id", "null"))}</span></div><p>{quotes}</p></div>')
        nq = sum(len(qt or '') for _, qt in srcs[cit])
        sy += 120 + 42 * (nq // 40 + 1)
        for i, _ in srcs[cit]:
            paths.append(f'<path class="an-p{i} sun" data-link-from=".an-c{i}" data-link-to=".an-q{i}"/>')
    body += '</div>' + f'<svg class="w3-svg an-svg" viewBox="0 0 1920 1080">{"".join(paths)}</svg>'
    n_claims = len(claims)
    steps = [1.7] * max(n_claims, 1) + [0.9]
    js = 'W3.measureLinks(root);for(var i=0;i<%d;i++)BK.words(root.querySelector(".an-t"+i));W3.rail(tl,root,0.15);BK.slam(tl,".an-term",0.3);BK.slam(tl,$(".w3-src"),0.5,{stagger:.12});\n' % n_claims
    for i in range(n_claims):
        at = f'P.at[{i + 1}]'
        js += (f'(function(){{var e=BK.stream(tl,".an-t{i}",{at},{{wps:28}});BK.fade(tl,$(".an-c{i}"),e,{{duration:.2}});BK.fade(tl,$(".an-e{i}"),e+0.05,{{duration:.25}});'
               f'BK.string(tl,$(".an-p{i}"),e+0.1,{{stagger:.1,duration:.45}});BK.scan(tl,$(".an-q{i}"),e+0.4,{{duration:.4}});}})();\n')
    js += f'BK.rise(tl,".an-meta",P.at[{n_claims + 1}],{{y:8}});'
    add(id='w3-answer', part='demo', speaker='Efe', seconds=25, title='The recorded answer points to the sentence it used', label='W3.4 · recorded demo',
        folio='THE JOURNEY · 4/4', repo=f'eval/results/week3/{d["answer_dir"]}/', steps=steps, body=body, js=js,
        notes=(f'This is a recorded run, not a live call: {demo.get("run_label", "null")}. '
               f'Every claim carries a citation number, and each citation draws a line to the exact sentence it quotes. Our validator checks each quote, including elided ones, against the cited source; '
               f'the judge then rated {sup} of {len(labels)} claims supported. The English lines are our translation.'))

    # ------------------------------------------------------------ 7 fallback
    ab = sb.get('abstention_correct', {}) if isinstance(sb.get('abstention_correct'), dict) else {}
    body = rail(5, 5, bad=None, bub_bad=True)
    shelf = ''.join(f'<i class="w3-abs fb-slot" style="left:{120 + k * 104}px;top:470px;width:84px;height:150px;border:4px dashed var(--ink-2);border-radius:10px"></i>' for k in range(5))
    body += (f'<div class="bk-panel w3-abs fb-shelf" style="left:96px;top:390px;width:560px;height:320px;padding:18px 24px"><span class="bk-tab">authorized sources</span></div>{shelf}'
             f'<i class="w3-abs fb-board" style="left:110px;top:630px;width:530px;height:12px;background:var(--ink);border-radius:6px"></i>'
             f'<p class="w3-abs w3-mono fb-zero" style="left:120px;top:656px;font-size:28px;font-weight:700">0 passages supplied</p>')
    body += (f'<div class="w3-model is-off fb-model" style="left:730px;top:430px;width:420px;height:210px"><h4>answer model</h4><span class="w3-slot" style="color:var(--ink);font-size:32px">not called<br>0 tokens</span></div>'
             f'<span class="bk-stamp bk-stamp--ink w3-abs fb-nocall" style="left:820px;top:664px;font-size:32px">no call</span>')
    body += (f'<div class="bk-panel w3-abs fb-out" style="left:1220px;top:390px;width:604px;padding:26px 28px"><span class="bk-tab bk-tab--sun">fixed fallback</span>'
             f'<p class="fb-text" style="font-size:36px;line-height:1.26;margin-top:6px">{h(demo.get("abstain_answer", "null"))}</p></div>'
             f'<span class="bk-stamp bk-stamp--teal w3-abs fb-fixed" style="left:1540px;top:690px;font-size:30px">fixed text</span>')
    dots = ''
    num, den = ab.get('numerator'), ab.get('n')
    if not isinstance(num, int):  # the scoreboard dropped 'numerator'; the run summary still records it
        num = (d['answer_summary'].get('abstention_correct') or {}).get('numerator')
    devs = [dv for dv in d['deviations'] if dv['id'] in d['control_ids']]
    if isinstance(num, int) and isinstance(den, int):
        kinds = ['ok'] * num + ['dev'] * min(len(devs), den - num)
        kinds += ['bad'] * (den - len(kinds))
        colour = {'ok': 'var(--teal)', 'dev': 'var(--sun)', 'bad': 'var(--tomato)'}
        for k, kd in enumerate(kinds):
            dots += f'<i class="w3-abs fb-dot" style="left:{560 + k * 64}px;top:842px;width:46px;height:46px;border-radius:50%;border:3px solid var(--ink);background:{colour[kd]}"></i>'
    other_n = (den - num - len(devs)) if isinstance(num, int) and isinstance(den, int) else None
    dev_txt = '; '.join(f'{dv["id"]} {dv["kind"]}' + (' (decided after results; review ' + (dv.get('reviewer') or 'null').split(' (')[0] + ')' if dv.get('after_results') else '') for dv in devs)
    safe = d['controls'].get('handled_safely_post_hoc') or {}
    body += (f'<div class="bk-panel w3-abs fb-run" style="left:96px;top:800px;width:1728px;height:130px;padding:20px 26px"><span class="bk-tab bk-tab--teal">recorded model run</span>'
             f'<p class="w3-cap" style="margin-top:8px;width:440px">{fmt(den)} unavailable-information controls</p>'
             f'<p class="w3-cap" style="position:absolute;left:960px;top:18px;width:750px;line-height:1.15"><b>{fmt(num)} fixed refusals</b>'
             + (f' · <span style="background:var(--sun-soft);padding:0 6px">{h(dev_txt)}</span>' if devs else '')
             + (f' · {other_n} other' if other_n else '') + '</p></div>' + dots)
    add(id='w3-fallback', part='demo', speaker='Efe', seconds=20, title='No authorized evidence: no model call, one fixed sentence', label='W3.4 · fixed fallback',
        folio='THE JOURNEY · FALLBACK', repo='src/rag/answer.py · prompts/rag/', steps=[1.1, 1.6, 1.1], body=body,
        js='''W3.rail(tl,root,0.15);BK.slam(tl,".fb-shelf",0.3);BK.fade(tl,$(".fb-slot"),0.5,{stagger:.05});BK.draw(tl,".fb-board",0.6);BK.fade(tl,".fb-zero",0.8);
BK.slam(tl,".fb-model",P.at[1]);BK.stamp(tl,".fb-nocall",P.at[1]+0.35);
BK.slam(tl,".fb-out",P.at[2]);BK.words(root.querySelector(".fb-text"));BK.stream(tl,".fb-text",P.at[2]+0.2,{wps:28});BK.stamp(tl,".fb-fixed",P.at[2]+1.05);
BK.slam(tl,".fb-run",P.at[3]);tl.fromTo($(".fb-dot"),{scale:0},{scale:1,duration:.25,stagger:.06,ease:BK.EASE.pop},P.at[3]+0.2);''',
        notes=(f'When nothing authorized is left, the code never calls the model and returns one fixed sentence; that is a deterministic check. '
               f'In the recorded run, {fmt(num)} of {fmt(den)} unavailable-information controls got it; the scoreboard counts exactly that. '
               + ''.join(f'{dv["id"]} gave a cited privacy refusal, accepted by the team' + (' after seeing the results, review pending' if dv.get('after_results') else '') + '. ' for dv in devs)
               + (f'Post hoc, {fmt(safe.get("numerator"))} of {fmt(safe.get("n"))} were handled safely.' if devs and safe else '')))

    # ------------------------------------------------------------ 8 retrieval
    dots, rings, ring_ids = [], [], []
    lang_rows = {'tr': 0, 'en': 1}
    seen = {'tr': 0, 'en': 0}
    for c in d['dots']:
        r = lang_rows.get(c['lang'], 1)
        k = seen.get(c['lang'], 0)
        seen[c['lang']] = k + 1
        x, y = 176 + (k % 8) * 100, 430 + r * 196 + (k // 8) * 90
        rk = c['rank'] if c['rank'] is not None else '–'
        tier = 1 if c['rank'] == 1 else 3 if c['rank'] and c['rank'] <= 3 else 5 if c['rank'] and c['rank'] <= 5 else 10
        dots.append(f'<div class="w3-dot rt-dot" style="left:{x}px;top:{y}px;width:72px;height:72px;line-height:66px;font-size:32px"><i class="rt-k{tier}"></i><span>{h(rk)}</span></div>')
        if c['all5'] is False:
            rings.append(f'<i class="w3-ring rt-ring" style="left:{x - 9}px;top:{y - 9}px;width:90px;height:90px"></i>')
            ring_ids.append(c['id'])
    ctl = ''.join(f'<i class="w3-sq ctl rt-ctl" style="left:{176 + k * 60}px;top:836px"></i>' for k in range(d['n_controls']))
    wil = d['paired'].get('wilson_95', {}).get('hybrid_rerank', {})
    bars = ''
    for i, k in enumerate(('1', '3', '5', '10')):
        v = hit[k]
        ci = wil.get(k)
        y = 430 + i * 100
        cih = ''
        if ci and v is not None:
            cih = f'<i class="w3-ci rt-ci{i}" style="left:{ci[1] * 100:.2f}%;width:{(ci[2] - ci[1]) * 100:.2f}%"></i>'
        bars += (f'<p class="w3-abs w3-mono rt-bl{i}" style="left:1050px;top:{y}px;font-size:30px;font-weight:700">hit@{k}</p>'
                 f'<div class="w3-bar rt-b{i}" style="left:1190px;top:{y - 4}px;width:440px"><div class="w3-track"><i class="w3-fill rt-f{i}" data-v="{v or 0}"></i></div>{cih}</div>'
                 f'<p class="w3-abs w3-mono rt-v{i}" style="left:1650px;top:{y}px;font-size:30px;font-weight:700"><span class="rt-n{i}">{fmt(hitc[k])}</span> / {fmt(n)}</p>')
    body = (f'<p class="w3-cap w3-abs" style="left:96px;top:372px">{fmt(n)} answerable questions · number = rank of the first evidence</p>'
            f'<p class="w3-abs w3-mono" style="left:96px;top:496px;font-size:30px;font-weight:700">TR</p><p class="w3-abs w3-mono" style="left:96px;top:692px;font-size:30px;font-weight:700">EN</p>'
            + ''.join(dots) + ''.join(rings) + ctl +
            f'<p class="w3-cap w3-abs rt-ctl-l" style="left:{176 + d["n_controls"] * 60 + 16}px;top:840px">{fmt(d["n_controls"])} controls · outside hit@k</p>' + bars +
            f'<div class="bk-panel w3-abs rt-mrr" style="left:1050px;top:836px;width:774px;padding:14px 24px"><span class="w3-mono" style="font-size:30px;font-weight:700">MRR@10 {fmt(mrr)} · all facets@5 {ratio(allc, n)}</span><br><span class="w3-cap" style="color:var(--tomato-ink)">ring: {h(", ".join(ring_ids) or "none")} misses a required facet</span></div>'
            f'<p class="bk-note bk-note--plain bk-note--ink w3-abs rt-foot" style="left:96px;top:930px;font-size:28px">Whiskers: Wilson 95% interval, n = {fmt(n)}.</p>')
    add(id='w3-retrieval', part='scoreboard', speaker='Doruk', seconds=30, title=f'Evidence in the top five for {ratio(hitc["5"], n)} questions', label='Scoreboard / W3.5',
        folio='BELDESK / SCOREBOARD', repo='eval/results/week3/retrieval/summary.json', steps=[1.1, 1.1, 1.1, 1.1], body=body, pose=None,
        js='''tl.fromTo($(".rt-dot"),{opacity:0,scale:.5},{opacity:1,scale:1,duration:.25,stagger:.015,ease:BK.EASE.pop},0.3);BK.fade(tl,$(".rt-ctl"),0.7,{stagger:.04});BK.fade(tl,".rt-ctl-l",0.9);
var tiers=[[".rt-k1"],[".rt-k3"],[".rt-k5",".rt-k10"]];
for(var s=0;s<3;s++){var at=P.at[s+1];tl.fromTo(root.querySelectorAll(tiers[s].join(",")),{scale:0},{scale:1,duration:.3,stagger:.02,ease:BK.EASE.pop},at);
 var ix=s<2?[s]:[2,3];ix.forEach(function(i){BK.fade(tl,$(".rt-bl"+i+", .rt-b"+i+", .rt-v"+i),at);var f=root.querySelector(".rt-f"+i);W3.morph(tl,f,0,parseFloat(f.getAttribute("data-v")),at+0.05,true);var nn=root.querySelector(".rt-n"+i);var v=parseInt(nn.textContent,10);if(!isNaN(v))BK.count(tl,nn,v,at+0.05,{duration:.6});var ci=root.querySelector(".rt-ci"+i);if(ci)BK.draw(tl,ci,at+0.5,{duration:.3});});}
tl.fromTo($(".rt-ring"),{opacity:0,scale:1.6},{opacity:1,scale:1,duration:.35,ease:BK.EASE.settle},P.at[4]);BK.slam(tl,".rt-mrr",P.at[4]+0.1);BK.note(tl,".rt-foot",P.at[4]+0.3);''',
        notes=(f'I am Doruk, with the measurements. Each dot is one of {fmt(n)} answerable questions, and its number is the rank of the first registered evidence. '
               f'At rank one, {fmt(hitc["1"])} light up; by rank three, {fmt(hitc["3"])}; by rank five, {fmt(hitc["5"])}. The whiskers are Wilson intervals: even a perfect score only bounds hit at five above {fmt(wil.get("5", [None, None])[1], 2)}. '
               f'The {fmt(d["n_controls"])} unanswerable controls are excluded. One ring matters: all required facets reach the top five for {ratio(allc, n)}. MRR at ten is {fmt(mrr)}.'))

    # ------------------------------------------------------------ 9 ablations
    configs = [('hybrid_rerank', 'hybrid + reranker', base), ('hybrid_no_rerank', 'hybrid, reranker off', nrr), ('dense_rerank', 'dense + reranker', dense)]
    metrics = [('hit@1', lambda s: s.get('hit_at_k', {}).get('1')), ('hit@5', lambda s: s.get('hit_at_k', {}).get('5')), ('MRR@10', lambda s: s.get('mrr_at_10'))]
    body = ''
    body += (f'<div class="bk-panel w3-abs ab-sw" style="left:96px;top:390px;width:720px;height:350px;padding:28px 30px"><span class="bk-tab">one switch at a time</span></div>'
             f'<div class="w3-switch ab-s1" style="left:130px;top:450px"><span class="w3-opt">dense</span><span class="w3-sw"><i class="ab-k1" style="left:66px"></i></span><span class="w3-opt">hybrid</span><span class="bk-label" style="margin-left:10px">candidates</span></div>'
             f'<div class="w3-switch ab-s2" style="left:130px;top:560px"><span class="w3-opt">off</span><span class="w3-sw"><i class="ab-k2" style="left:66px"></i></span><span class="w3-opt">on</span><span class="bk-label" style="margin-left:10px">reranker</span></div>'
             f'<p class="w3-abs w3-mono ab-cfg" style="left:130px;top:660px;font-size:34px;font-weight:700"><span class="w3-flip">' + ''.join(f'<span class="ab-c{i}">{h(lbl)}</span>' for i, (_, lbl, _) in enumerate(configs)) + '</span></p>')
    for m, (mn, getter) in enumerate(metrics):
        y = 420 + m * 120
        vals = [getter(c[2]) for c in configs]
        body += (f'<p class="w3-abs w3-mono" style="left:880px;top:{y}px;font-size:30px;font-weight:700">{mn}</p>'
                 f'<div class="w3-bar ab-b{m}" style="left:1080px;top:{y - 4}px;width:520px"><div class="w3-track"><i class="w3-fill ab-f{m}"></i></div></div>'
                 f'<p class="w3-abs w3-mono" style="left:1630px;top:{y}px;font-size:34px;font-weight:700"><span class="w3-flip">' + ''.join(f'<span class="ab-v{m}-{i}">{fmt(v)}</span>' for i, v in enumerate(vals)) + '</span></p>')
    f = [[mt[1](c[2]) or 0 for c in configs] for mt in metrics]
    pt = d['paired'].get('paired_tests', {})
    ps = [t.get('p_exact') for t in pt.values() if isinstance(t.get('p_exact'), (int, float))]
    rr5 = pt.get('hybrid_rerank_vs_hybrid_no_rerank_hit5', {})
    rr1 = pt.get('hybrid_rerank_vs_hybrid_no_rerank_hit1', {})
    dh1 = pt.get('hybrid_rerank_vs_dense_rerank_hit1', {})
    body += (f'<div class="bk-panel w3-abs ab-t1" style="left:96px;top:790px;width:850px;padding:22px 26px"><span class="bk-tab bk-tab--sun">reranker off → on</span>'
             f'<p class="w3-cap" style="margin-top:6px">hit@5: {fmt(rr5.get("a_only"))} questions gained, {fmt(rr5.get("b_only"))} lost · exact p = {fmt(rr5.get("p_exact"), 2)}<br>hit@1: +{fmt(rr1.get("a_only"))} / −{fmt(rr1.get("b_only"))} · p = {fmt(rr1.get("p_exact"), 2)}</p></div>'
             f'<div class="bk-panel w3-abs ab-t2" style="left:974px;top:790px;width:850px;padding:22px 26px"><span class="bk-tab bk-tab--sun">hybrid → dense</span>'
             f'<p class="w3-cap" style="margin-top:6px">hit@1: {fmt(dh1.get("a_only"))} gained, {fmt(dh1.get("b_only"))} lost · exact p = {fmt(dh1.get("p_exact"), 2)}<br>MRR@10 {fmt(base.get("mrr_at_10"))} vs {fmt(dense.get("mrr_at_10"))}</p></div>')
    js = 'BK.slam(tl,".ab-sw",0.3);BK.rise(tl,".ab-s1, .ab-s2, .ab-cfg",0.45,{y:10});'
    js += ''.join(f'W3.morph(tl,".ab-f{m}",0,{f[m][0]},0.6,true);' for m in range(3))
    js += 'tl.fromTo($(".ab-c1, .ab-c2"),{opacity:0},{opacity:0,duration:.01},0);' + ''.join(f'tl.fromTo($(".ab-v{m}-1, .ab-v{m}-2"),{{opacity:0}},{{opacity:0,duration:.01}},0);' for m in range(3))
    js += 'tl.fromTo(".ab-k2",{left:66},{left:5,duration:.35,ease:BK.EASE.slam},P.at[1]);W3.flip(tl,".ab-c0",".ab-c1",P.at[1]+0.2);'
    js += ''.join(f'W3.morph(tl,".ab-f{m}",{f[m][0]},{f[m][1]},P.at[1]+0.3);W3.flip(tl,".ab-v{m}-0",".ab-v{m}-1",P.at[1]+0.35);' for m in range(3))
    js += 'BK.slam(tl,".ab-t1",P.at[1]+0.5);'
    js += 'tl.fromTo(".ab-k2",{left:5},{left:66,duration:.35,ease:BK.EASE.slam,immediateRender:false},P.at[2]);tl.fromTo(".ab-k1",{left:66},{left:5,duration:.35,ease:BK.EASE.slam},P.at[2]+0.15);W3.flip(tl,".ab-c1",".ab-c2",P.at[2]+0.3);'
    js += ''.join(f'W3.morph(tl,".ab-f{m}",{f[m][1]},{f[m][2]},P.at[2]+0.35);W3.flip(tl,".ab-v{m}-1",".ab-v{m}-2",P.at[2]+0.4);' for m in range(3))
    js += 'BK.slam(tl,".ab-t2",P.at[2]+0.55);'
    add(id='w3-ablations', part='scoreboard', speaker='Doruk', seconds=26, title='Two ablations, one switch at a time', label='Scoreboard / W3.7',
        folio='BELDESK / SCOREBOARD', repo='eval/retrieval_week3.py · retrieval/paired_statistics.json', steps=[1.4, 1.4], body=body, js=js,
        notes=(f'We changed one component at a time on the same {fmt(n)} questions. Switching the reranker off drops hit at five from {fmt(hit["5"])} to {fmt(nrr.get("hit_at_k", {}).get("5"))} and MRR from {fmt(mrr)} to {fmt(nrr.get("mrr_at_10"))}: '
               f'{fmt(rr5.get("a_only"))} questions gained evidence with the reranker and {fmt(rr5.get("b_only"))} lost it; the exact test gives p = {fmt(rr5.get("p_exact"), 2)}. '
               f'Switching candidates from hybrid to dense gives MRR {fmt(dense.get("mrr_at_10"))} against {fmt(mrr)}. '
               + (f'With {fmt(n)} questions, none of these differences is significant.' if ps and min(ps) >= 0.05 else f'The smallest exact p is {fmt(min(ps) if ps else None, 3)}.')))

    # ------------------------------------------------------------ 10 claims
    fa_sum = d['answer_summary']
    cm = d['claims']
    nc, bad = cm['n'], cm['numerator']
    bad_ids = [c['id'] for c in d['stage_cases']['generation'] if c['kind'] == 'unsupported claim']
    sq = ''
    if isinstance(nc, int):
        per = 13
        for k in range(nc):
            x, y = 96 + (k % per) * 52, 392 + (k // per) * 52
            is_bad = isinstance(bad, int) and k >= nc - bad
            sq += f'<i class="w3-cell cl-{"bad" if is_bad else "ok"}{" bad" if is_bad else ""}" style="left:{x}px;top:{y}px;width:42px;height:42px"></i>'
    if cm['revalidated'] and cm['valid_original_rule'] is not None:
        fp = f' ({fmt(cm["valid_original_rule"])} under the original quote rule; first pass {fmt(cm["first_pass_valid"])})'
    else:
        fp = f' (first pass {fmt(cm["first_pass_valid"])})' if cm['first_pass_valid'] is not None else ''
    funnel = [('cases', fa_sum.get('planned_cases')), (f'valid answers{fp}', fa_sum.get('valid_generated_answers')),
              ('judged answers', fa_sum.get('valid_claim_judgements')), ('claims judged', nc)]
    fun = ''.join(f'<div class="bk-panel w3-abs cl-fun" style="left:{900 + i * 40}px;top:{384 + i * 92}px;width:{880 - i * 80}px;height:78px;padding:10px 24px;display:flex;align-items:center;gap:20px">'
                  f'<span class="w3-big" style="font-size:52px">{fmt(v)}</span><span class="w3-cap" style="line-height:1.08">{h(lbl)}</span></div>' for i, (lbl, v) in enumerate(funnel))
    bf = cm['before']
    corr = ''
    if bf and bf.get('n') is not None:
        corr = (f'<div class="bk-panel bk-panel--sun w3-abs cl-corr" style="left:96px;top:266px;width:1728px;padding:14px 26px 12px"><p class="w3-cap" style="color:var(--ink)">'
                f'Corrected after audit: <s>{fmt(bf.get("numerator"))} / {fmt(bf.get("n"))}</s> → <b>{fmt(bad)} / {fmt(nc)}</b> · {h(cm["correction"] or "metric definition corrected")}</p></div>')
    unj = len(cm['unjudged'])
    groups = {}
    for u in cm['unjudged']:
        groups.setdefault(u.get('reason') or 'unjudged', {}).setdefault(u.get('case_id'), 0)
        groups[u.get('reason') or 'unjudged'][u.get('case_id')] += 1
    unj_txt = '; '.join(' + '.join(f'{k} {cid}' for cid, k in sorted(ids.items())) + f' ({re.sub(r" [(].*", "", reason)})' for reason, ids in groups.items())
    rule_txt = (f' Quote rule widened after seeing results; {", ".join(cm["revalidated"])} re-validated offline from saved outputs, no model call.' if cm['revalidated'] else '')
    body = corr + sq + fun + (f'<div class="bk-panel bk-panel--tomato w3-abs cl-bad-l" style="left:900px;top:768px;width:924px;padding:14px 24px"><span class="w3-mono" style="font-size:30px;font-weight:700">'
                       f'{fmt(bad)} / {fmt(nc)} unsupported = {fmt(cm["value"])} · {h(", ".join(bad_ids) or "null")}</span></div>'
                       f'<p class="bk-note bk-note--plain bk-note--ink w3-abs cl-foot" style="left:96px;top:880px;width:1728px;font-size:28px;white-space:normal;line-height:1.25">{unj} claims not in the denominator: {h(unj_txt or "none")}; none counted as passes.' + (f' {fmt(cm["gen_errors"])} answers with generation errors.' if cm['gen_errors'] else '') + f'{h(rule_txt)}</p>')
    add(id='w3-claims', part='scoreboard', speaker='Doruk', seconds=24, title=f'{fmt(cm["supported"])} of {fmt(nc)} claims match their cited source', label='Scoreboard / W3.6',
        folio='BELDESK / SCOREBOARD', repo=f'eval/results/week3/{d["answer_dir"]}/summary.json', steps=[1.8, 1.1], body=body,
        js='''BK.slam(tl,".cl-corr",0.3);BK.slam(tl,$(".cl-fun"),0.4,{stagger:.12});
tl.fromTo($(".cl-ok, .cl-bad"),{opacity:0,scale:.4},{opacity:1,scale:1,duration:.2,stagger:.012,ease:BK.EASE.pop},P.at[1]);
tl.fromTo($(".cl-bad"),{scale:1},{scale:1.25,duration:.25,ease:BK.EASE.pop,immediateRender:false},P.at[2]);BK.slam(tl,".cl-bad-l",P.at[2]+0.1);BK.note(tl,".cl-foot",P.at[2]+0.3);''',
        notes=(f'Of {fmt(fa_sum.get("planned_cases"))} cases, {fmt(fa_sum.get("valid_generated_answers"))} answers are valid and {fmt(fa_sum.get("valid_claim_judgements"))} were judged: {fmt(nc)} claims, {fmt(bad)} unsupported, from {", ".join(bad_ids) or "null"}. '
               + (f'After an audit a validated refusal counts zero claims, so {fmt(bf.get("numerator"))} of {fmt(bf.get("n"))} became {fmt(bad)} of {fmt(nc)}. ' if bf and bf.get('n') is not None else '')
               + (f'{unj} claims stay out because they are unjudged. ' if unj else '')
               + (f'We widened the quote rule after seeing results and re-validated {len(cm["revalidated"])} saved answers offline, with no new model call. ' if cm['revalidated'] else '')
               + 'The judge is provisional.'))

    # ------------------------------------------------------------ 11 scoreboard (Week 2 layout)
    old = d['old']
    rows = ['test_set_size', 'e2e_accuracy', 'abstention_correct', 'unsupported_claims', 'hit_at_5', 'mrr', 'task_success', 'pass_k',
            'injection_success', 'cost_per_task_usd', 'latency_p50_s', 'spend_week_usd', 'spend_total_usd']
    extra_ci = {'hit_at_5': (wil.get('5') or [None, None, None])[1:]}

    def cell(key, item, current=True):
        v = item.get('value') if isinstance(item, dict) else item
        if v is None:
            return None, ''
        dg = 5 if key == 'cost_per_task_usd' else 1 if key == 'latency_p50_s' else 3
        txt = f'{v:.{dg}f}' if isinstance(v, float) else str(v)
        if key.endswith('_usd'):
            txt = '$' + txt
        if key == 'latency_p50_s':
            txt += ' s'
        small = []
        if current and isinstance(item, dict):
            ci = item.get('ci95') or extra_ci.get(key)
            if not ci and isinstance(item.get('numerator'), int) and isinstance(item.get('n'), int):
                ci = d['wilson'](item['numerator'], item['n'])
            if ci and ci[0] is not None:
                small.append(f'[{ci[0]:.2f}, {ci[1]:.2f}]')
            if item.get('n') is not None:
                small.append(f'n={item["n"]}')
        return txt, ' '.join(small)
    sbr = []
    for i, key in enumerate(rows):
        cur, small = cell(key, sb.get(key))
        prev, _ = cell(key, old.get(key), False)
        grp = 0 if i < 5 else 1 if i < 9 else 2
        mk = ''
        if cur is not None:
            mk += '<i class="sb-mk sb-mk--on" style="--k:3"></i>'
            if prev is not None:
                mk = '<i class="sb-link" style="left:calc(var(--sb-m) + var(--sb-v) + var(--sb-l) + 1.5 * var(--sb-w))"></i><i class="sb-mk sb-mk--on" style="--k:2"></i>' + mk
        else:
            mk += '<i class="sb-mk" style="--k:3"></i>'
        val = (f'<span class="sb-val">{h(cur)}' + (f' <small>{h(small)}</small>' if small else '') + '</span>') if cur is not None else '<span class="sb-null">null</span>'
        sbr.append(f'<div class="sb-row sb-g{grp}"><span class="sb-name">{key}</span>{val}<span class="sb-last">{h(prev if prev is not None else "null")}</span>{mk}</div>')
    measured = sum((sb.get(k).get('value') if isinstance(sb.get(k), dict) else sb.get(k)) is not None for k in rows)
    null_rows = [k for k in rows if value_of(sb.get(k)) is None]
    cost_v, spend_v = value_of(sb.get('cost_per_task_usd')), value_of(sb.get('spend_week_usd'))
    cost_note = ('cost: list-price estimate, not billed' if cost_v is not None else 'cost unknown → null')
    cost_note += (f' · spend ${spend_v:g} actual' if spend_v is not None else ' · spend unknown → null')
    body = ('<span id="sb-cap" class="bk-label">same rows · same order</span><section id="sb-table" class="bk-panel"><div class="sb-col sb-col--now" style="--k:3"></div><div class="sb-col" style="--k:4"></div><div class="sb-col" style="--k:6"></div>'
            '<div class="sb-row sb-head"><span>metric</span><span>this week</span><span>last week</span>' + ''.join(f'<span class="sb-wk">W{i}</span>' for i in range(1, 7)) + '</div>' + ''.join(sbr) + '</section>'
            f'<section id="sb-tally" class="bk-panel"><span class="bk-tab bk-tab--teal">measured</span><div class="sb-tally-n"><span id="sb-7">{measured}</span><span class="sb-of">/ 13</span></div><span class="bk-label sb-tally-l">rows with a value</span></section>'
            '<span id="sb-stamp" class="bk-stamp">null =<br>not measured</span>'
            '<p id="sb-foot" class="bk-note bk-note--plain bk-note--ink">[ ] = 95% interval (recorded, else Wilson) · n = denominator · W2 and W3 sets differ: no like-for-like claim.<br>'
            f'Latency: retrieval + generation, waits excluded · {h(cost_note)}<br>Judge-based rows are provisional.</p>')
    add(id='scoreboard', part='scoreboard', speaker='Doruk', seconds=40, title=f'{measured} rows measured; the rest stay null', label='Scoreboard / W3',
        folio='BELDESK / SCOREBOARD', repo='eval/results/week3/scoreboard.json', steps=[1.6, 1.4], body=body, pose='dusunen', scoreboard=True,
        js='''BK.slam(tl,"#sb-table",0.25,{duration:.42});BK.rise(tl,".sb-head",0.35,{y:8,duration:.3});BK.fade(tl,$(".sb-col"),0.4,{duration:.3});
var groups=[".sb-g0",".sb-g1",".sb-g2"],ats=[0.35,P.at[1],P.at[2]];
groups.forEach(function(g,i){var rs=$(g);tl.fromTo(rs,{opacity:0,x:-30},{opacity:1,x:0,duration:.28,stagger:.1,ease:BK.EASE.settle},ats[i]);
 rs.forEach(function(r,j){var m=r.querySelectorAll(".sb-mk");BK.formula(tl,m,ats[i]+j*.1+.1,{stagger:.05});var l=r.querySelector(".sb-link");if(l)BK.draw(tl,l,ats[i]+j*.1+.15,{duration:.2});});});
BK.slam(tl,"#sb-tally",P.at[2]+0.5,{duration:.4});BK.count(tl,"#sb-7",parseInt(root.querySelector("#sb-7").textContent,10)||0,P.at[2]+0.55,{duration:.45});
BK.stamp(tl,"#sb-stamp",P.at[2]+0.8);BK.note(tl,"#sb-foot",P.at[2]+0.7);BK.rise(tl,"#sb-cap",0.4,{y:8});''',
        notes=(f'The same thirteen rows as Week two, in the same order. '
               f'Test set size is {fmt(sb.get("test_set_size"))}. End-to-end accuracy stays null: we have no answer-adequacy rubric yet. Abstention is {fmt((sb.get("abstention_correct") or {}).get("value") if isinstance(sb.get("abstention_correct"), dict) else None)} on only {fmt(ab.get("n"))} controls, so its interval is wide. '
               f'Unsupported claims are {fmt(cm["value"])} on {fmt(nc)} claims. The rows {", ".join(k.replace("_", " ") for k in null_rows if k not in ("e2e_accuracy", "cost_per_task_usd", "spend_week_usd", "spend_total_usd")) or "No other row"} stay null this week. '
               f'Latency is {fmt(value_of(sb.get("latency_p50_s")), 1)} seconds without waits. '
               + (f'Cost per task is a list-price estimate of {fmt(cost_v, 5)} dollars, not a bill' if cost_v is not None else 'Cost stays null')
               + (f'; actual spend is {spend_v:g} dollars. ' if spend_v is not None else '; spend stays null. ')
               + f'{measured} of thirteen rows have a value. Week two used a different set, so this is not a like-for-like comparison.'))

    # ------------------------------------------------------------ 12 R032 journey
    body = rail(4, 6, bad=None, bub_bad=True)
    fq = fj['query'] if fj else D.get('retrieval_failure', {}).get('question', 'null')
    qhtml = h(fq)
    facet_cls = {}
    if fj:
        for i, fc in enumerate(fj['facets']):
            doc = fc['pids'][0].split('#')[0] if fc['pids'] else ''
            ph = FACET_PHRASES.get(doc)
            kind = 'tomato' if (fc['rank'] or 99) > 5 else 'teal'
            facet_cls[fc['pids'][0] if fc['pids'] else ''] = kind
            if ph and ph in fq:
                qhtml = qhtml.replace(h(ph), f'<span class="bk-scan bk-scan--{kind} rf-f{i}">{h(ph)}</span>', 1)
    body += f'<div class="w3-bubble rf-bub" style="left:96px;top:400px;width:740px"><span class="w3-q" style="font-size:36px">{qhtml}</span></div>'
    legend = ''
    if fj:
        for i, fc in enumerate(fj['facets']):
            kind = 'tomato' if (fc['rank'] or 99) > 5 else 'teal'
            legend += (f'<p class="w3-abs rf-leg" style="left:96px;top:{790 + i * 62}px;font-size:30px;font-weight:700"><span class="w3-tag w3-tag--{kind}">facet {"AB"[i] if i < 2 else i + 1}</span> '
                       f'<span class="w3-mono">{h(", ".join(fc["pids"]))}</span> · rank {fmt(fc["rank"])}</p>')
        rl, cut_y = ranklist('rf', fj['cards'], 900, 392, 924, pitch=74, gap=34)
        body += rl + f'<div class="w3-cut rf-cut" style="left:880px;top:{cut_y:.0f}px;width:964px"><span>top-5 cut</span></div>'
        gold_out = [c for c in fj['cards'] if c['gold'] and (c.get('rerank') or 99) > 5]
        if gold_out:
            body += '<span class="bk-stamp bk-stamp--tomato w3-abs rf-stamp" style="left:660px;top:786px;font-size:28px;padding:2px 12px">left out</span>'
    body += legend
    nr_rank = None
    fa_ = max(fj['facets'], key=lambda f: f['rank'] or 99) if fj else {}
    fb = min(fj['facets'], key=lambda f: f['rank'] or 99) if fj else {}
    fjump = max(fj['cards'], key=lambda c: (c.get('fused') or 0) - (c.get('rerank') or 0)) if fj else {}
    if d['fail_no_rerank']:
        nr_rank = max((fc['rank'] or 99) for fc in d['fail_no_rerank']['facets'])
    add(id='w3-r032', part='failures', speaker='Doruk', seconds=34, title=f'{h(fj["case_id"] if fj else "null")}: same route, one facet falls below the cut', label='Failure analysis / retrieval',
        folio='FAILURE · REPLAY', repo='eval/results/week3/retrieval/hybrid_rerank.jsonl', steps=[1.1, 1.3, 1.1], body=body,
        js='''W3.rail(tl,root,0.15);BK.slam(tl,".rf-bub",0.35);BK.scan(tl,$(".rf-f0"),0.8);BK.scan(tl,$(".rf-f1"),1.0);BK.rise(tl,$(".rf-leg"),0.9,{y:8,stagger:.12});
tl.fromTo($(".w3-card"),{opacity:0,x:80},{opacity:1,x:0,duration:.35,stagger:.07,ease:BK.EASE.settle},P.at[1]);
W3.reorder(tl,root,P.at[2]);$(".w3-card").forEach(function(c){var a=c.querySelector(".rk-a"),b=c.querySelector(".rk-b");if(b)W3.flip(tl,a,b,P.at[2]+0.4);var j=c.querySelector(".w3-jump");if(j)BK.stamp(tl,j,P.at[2]+0.7,{rotation:0});});
BK.draw(tl,".rf-cut",P.at[3],{duration:.6});var below=[];$(".w3-card").forEach(function(c){if(parseFloat(c.style.top)>parseFloat(root.querySelector(".rf-cut").style.top))below.push(c);});BK.dim(tl,below,P.at[3]+0.5,{to:.55});BK.stamp(tl,".rf-stamp",P.at[3]+0.6);''',
        notes=(f'Now the same journey with a case that fails, {fj["case_id"] if fj else "null"}. The resident asks two things: what a park fair needs for permission, and how to report a blocked entrance. '
               f'After fusion, the access facet sits at {fmt(fb.get("fused"))} and the permit facet at {fmt(fa_.get("fused"))}. '
               f'The reranker lifts {fjump.get("pid", "null")} from {fmt(fjump.get("fused"))} to {fmt(fjump.get("rerank"))}, and the permit facet slips to {fmt(fa_.get("rank"))}. '
               f'The top-five cut leaves it out; without the reranker it sat at {fmt(nr_rank)}, still outside. Hit at five calls this a success; all facets at five does not.'))

    # ------------------------------------------------------------ 13 R032 answer
    body = rail(5, 4, bad=5, bub_bad=True)
    if fa:
        slots = ''.join(f'<span class="w3-slot fr-slot">[{s["citation"]}] <b>{h(s["passage_id"])}</b></span>' for s in fa['sources'])
        body += f'<div class="w3-model fr-ctx" style="left:96px;top:390px;width:560px"><h4>context sent to the model</h4>{slots}</div>'
        body += (f'<div class="bk-term w3-term fr-term" style="left:730px;top:390px;width:1094px"><div class="bk-term-bar"><i></i><i></i><i></i><b>recorded run · {h(fa["case_id"])}</b></div>'
                 f'<div class="bk-term-body"><span class="bk-term-line"><b class="bk-term-bot">beldesk&gt;</b> <span class="fr-ans">{h(fa["answer"])}</span></span></div></div>')
    rec = next((f for f in d['answer_failures'] if fa and f.get('case_id') == fa['case_id']), {})
    stage = rec.get('stage') or 'null'
    covered = next((fc for fc in fj['facets'] if (fc['rank'] or 99) <= 5), None) if fj else None
    missing = next((fc for fc in fj['facets'] if (fc['rank'] or 99) > 5), None) if fj else None
    validated = bool(fa) and fa['case_id'] in (d['answer_summary'].get('faithfulness', {}).get('validated_fixed_refusals') or [])
    excluded = bool(fa) and fa['case_id'] in d['claims']['excluded_refusals']
    if fa:
        jtxt = ('Validated fixed refusal: it adds 0 claims to the claim rate' + (' (its earlier unsupported verdict was removed after audit).' if excluded else '.')) if validated else 'Refusal not validated as the fixed fallback.'
        body += (f'<div class="bk-panel w3-abs fr-judge" style="left:730px;top:640px;width:1094px;padding:18px 26px"><span class="bk-tab bk-tab--sun">evaluation</span>'
                 f'<p class="w3-cap" style="margin-top:6px">{h(jtxt)}</p></div>')
        tags = [rec.get('kind')] + ([f'facets in context: {rec["gold_facets_in_context"]}'] if rec.get('gold_facets_in_context') else [])
        body += ''.join(f'<span class="w3-tag w3-tag--tomato w3-abs fr-tag" style="left:96px;top:{700 + i * 58}px;font-size:28px;padding:2px 8px">{h(t)}</span>' for i, t in enumerate(t for t in tags if t))
    body += (f'<div class="bk-panel w3-abs fr-root" style="left:96px;top:850px;width:1728px;padding:16px 26px"><p class="w3-cap" style="color:var(--ink)">'
             f'<b>Root cause: {h(stage)}.</b> Missing facet {h(", ".join(rec.get("missing_facets") or (missing["pids"] if missing else ["null"])))} ranked {fmt(missing["rank"] if missing else None)}; the model saw only the top 5.</p></div>')
    add(id='w3-r032-answer', part='failures', speaker='Tarık', seconds=23, title='Five passages in, a fixed refusal out', label=f'Failure analysis / {stage}',
        folio='FAILURE · REPLAY', repo=f'eval/results/week3/{d["answer_dir"]}/failures.json', steps=[1.6, 1.1, 1.1], body=body,
        js='''W3.rail(tl,root,0.15);BK.slam(tl,".fr-ctx",0.3);BK.rise(tl,$(".fr-slot"),0.5,{y:8,stagger:.08});BK.slam(tl,".fr-term",0.6);
BK.words(root.querySelector(".fr-ans"));BK.stream(tl,".fr-ans",P.at[1],{wps:22});
BK.slam(tl,".fr-judge",P.at[2]);
BK.stamp(tl,$(".fr-tag"),P.at[2]+0.3,{rotation:0,stagger:.15});BK.slam(tl,".fr-root",P.at[3]);''',
        notes=(f'I am Tarık. The model received these five passages: the access facet at rank {fmt(covered["rank"] if covered else None)}, but not the permit facet. '
               f'It returned the fixed refusal' + (', which our validator accepts as the fixed fallback, so it adds no claims to the claim rate. ' if validated else '. ')
               + f'We record the root cause as {stage}: {fmt(rec.get("gold_facets_in_context"))} required facets reached the context, and the missing one ranked {fmt(missing["rank"] if missing else None)}.'))

    # ------------------------------------------------------------ 14 stage flow
    stages = [('retrieval', 'Retrieval'), ('generation', 'Generation'), ('provider', 'Provider'), ('judge', 'Judge')]
    body = '<i class="w3-abs sf-pipe" style="left:150px;top:460px;width:1620px;height:12px;background:var(--ink);border-radius:6px"></i>'
    for i, (key, name) in enumerate(stages):
        x = 96 + i * 446
        cs = d['stage_cases'][key]
        body += f'<div class="w3-stagebox sf-box sf-b{i}{" sf-hit" if cs else ""}" style="left:{x}px"><h4>{h(name)}</h4><div class="w3-n">{len(cs)} record{"s" if len(cs) != 1 else ""}</div></div>'
        body += f'<div class="w3-abs" style="left:{x}px;top:540px;display:flex;flex-direction:column;gap:10px">' + (''.join(
            f'<div class="w3-case sf-c{i}"><b>{h(c["id"])}</b>{h(c["kind"])}</div>' for c in cs[:4]) or
            f'<div class="w3-case sf-c{i}" style="border-style:dashed;background:transparent;color:var(--ink-2)">no failure in this run</div>') + '</div>'
    strips = []
    if d['deviations']:
        strips.append('<b>Accepted deviation:</b> ' + h('; '.join(f'{dv["id"]} {dv["kind"]}, decided by {dv.get("decided_by") or "null"}' + (' after seeing results' if dv.get('after_results') else '') for dv in d['deviations'])))
    if d['stage_cases']['other']:
        strips.append('<b>Other stage:</b> ' + h('; '.join(f'{c["id"]} {c["kind"]} ({c["stage_raw"] or "no stage"})' for c in d['stage_cases']['other'])))
    if strips:
        body += (f'<div class="bk-panel w3-abs sf-dev" style="left:96px;top:{730 if cm["pending"] else 800}px;width:1728px;padding:12px 26px;box-shadow:none;background:var(--sun-soft)">'
                 f'<p class="w3-cap" style="color:var(--ink)">{"<br>".join(strips)}</p></div>')
    pend = cm['pending']
    if pend:
        body += (f'<div class="bk-panel w3-abs sf-pend" style="left:96px;top:800px;width:1728px;padding:14px 26px;border-style:dashed;box-shadow:none;background:transparent">'
                 f'<p class="w3-cap" style="color:var(--ink)"><b>Not failures:</b> {h(", ".join(f"{p_['id']} ({p_['claims']} claims)" for p_ in pend))} re-validated offline, claims not yet judged.</p></div>')
    body += f'<p class="bk-note bk-note--plain bk-note--ink w3-abs sf-foot" style="left:96px;top:948px;width:1728px;text-align:right;font-size:28px">{sum(len(v) for k, v in d["stage_cases"].items() if k != "other")} failure records: failures.json + retrieval all-facets@5 misses</p>'
    add(id='w3-stages', part='failures', speaker='Tarık', seconds=23, title='Every failure is assigned to one stage', label='Failure analysis / W3.8',
        folio='FAILURE · STAGES', repo=f'eval/results/week3/{d["answer_dir"]}/failures.json', steps=[1.2, 1.2, 1.1], body=body,
        js='''BK.draw(tl,".sf-pipe",0.3,{duration:.6});BK.slam(tl,$(".sf-box"),0.4,{stagger:.1});
[0,1,2,3].forEach(function(i){var at=P.at[1+Math.floor(i/2)]+(i%2)*0.35;var b=root.querySelector(".sf-b"+i);if(b.classList.contains("sf-hit"))tl.fromTo(b,{backgroundColor:"#fff6e0"},{backgroundColor:"#f7b79a",duration:.25},at);BK.slam(tl,$(".sf-c"+i),at+0.15,{stagger:.08});});
BK.note(tl,".sf-foot",P.at[3]);var pe=root.querySelector(".sf-pend");if(pe)BK.slam(tl,pe,P.at[3]+0.1);var dv=root.querySelector(".sf-dev");if(dv)BK.slam(tl,dv,P.at[3]+0.2);''',
        notes=('We assign every failure to the first stage where it went wrong. '
               + ' '.join(f'{name}: ' + (', '.join(c["id"] for c in d['stage_cases'][key]) or 'none') + '.' for key, name in stages)
               + (f' {" and ".join(p_["id"] for p_ in cm["pending"])} are not failures: they were re-validated offline and their claims are not judged yet.' if cm['pending'] else '')
               + ''.join(f' {dv["id"]} is an accepted deviation by team decision, not a failure.' for dv in d['deviations'])
               + (f' {len(d["stage_cases"]["other"])} record has an unrecognised stage and is shown separately.' if d['stage_cases']['other'] else '')
               + ' Each stage points to a different fix.'))

    # ------------------------------------------------------------ 15 judge calibration
    labs = ['supported', 'insufficient_evidence', 'unsupported']
    short = {'supported': 'supported', 'insufficient_evidence': 'insufficient', 'unsupported': 'unsupported'}
    mx, my, cw, chh = 420, 420, 250, 150
    body = ''
    for r, lr in enumerate(labs):
        body += f'<p class="w3-abs w3-mono jc-ax" style="left:96px;top:{my + r * chh + 52}px;font-size:28px;font-weight:700;width:310px;text-align:right">{short[lr]}</p>'
        for c, lc in enumerate(labs):
            body += f'<i class="w3-abs jc-cell{" jc-diag" if r == c else ""}" style="left:{mx + c * cw}px;top:{my + r * chh}px;width:{cw - 10}px;height:{chh - 10}px;border:3px solid var(--ink);border-radius:12px;background:{"var(--teal-soft)" if r == c else "var(--cream)"}"></i>'
    for c, lc in enumerate(labs):
        body += f'<p class="w3-abs w3-mono jc-ax" style="left:{mx + c * cw}px;top:{my - 46}px;width:{cw - 10}px;text-align:center;font-size:28px;font-weight:700">{short[lc]}</p>'
    body += f'<p class="bk-label w3-abs" style="left:{mx}px;top:{my - 96}px">judge →</p><p class="bk-label w3-abs" style="left:96px;top:{my - 46}px">human ↓</p>'
    fill = {}
    agree = 0
    for p in d['pairs']:
        if p['human'] not in labs or p['judge'] not in labs:
            continue
        r, c = labs.index(p['human']), labs.index(p['judge'])
        k = fill.get((r, c), 0)
        fill[(r, c)] = k + 1
        x, y = mx + c * cw + 14 + (k % 5) * 44, my + r * chh + 16 + (k // 5) * 44
        ok = r == c
        agree += ok
        body += f'<i class="w3-abs jc-dot{" jc-bad" if not ok else ""}" style="left:{x}px;top:{y}px;width:36px;height:36px;border-radius:50%;border:3px solid var(--ink);background:{"var(--teal)" if ok else "var(--tomato)"}" title="{h(p["id"])}"></i>'
    cal = d['calib']
    npairs = sum(fill.values())
    dis = [p for p in d['pairs'] if p['human'] in labs and p['judge'] in labs and p['human'] != p['judge']]
    dis_h = {p['human'] for p in dis}
    dis_text = (f'All {len(dis)} disagreements are claims a human marked {short[dis_h.pop()]}.' if len(dis_h) == 1 else f'{len(dis)} claims disagree.')
    body += (f'<div class="bk-panel w3-abs jc-side" style="left:1230px;top:400px;width:594px;padding:24px 28px"><span class="bk-tab bk-tab--teal">agreement</span>'
             f'<span class="w3-big" style="font-size:120px;color:var(--teal-ink)"><span class="jc-n">{agree}</span></span><span class="w3-big" style="font-size:56px"> / {npairs}</span>'
             f'<p class="w3-mono" style="font-size:32px;font-weight:700;margin-top:10px">Cohen’s κ = {fmt(cal.get("kappa"))}</p></div>'
             f'<div class="bk-panel w3-abs jc-scope" style="left:1230px;top:700px;width:594px;padding:20px 26px"><span class="bk-tab bk-tab--sun">scope</span>'
             f'<p class="w3-cap" style="margin-top:4px">Historical claims with v1 evidence. Not human accuracy on the citizen-v2 answers.</p></div>')
    add(id='w3-judge', part='failures', speaker='Tarık', seconds=25, title=f'Judge vs human on {npairs} claims: {agree} agree', label='Failure analysis / evaluation',
        folio='FAILURE · JUDGE', repo='eval/results/week3/calibration/', steps=[1.8, 1.1, 1.1], body=body,
        js='''BK.fade(tl,$(".jc-cell"),0.3,{stagger:.03});BK.fade(tl,$(".jc-ax"),0.4);
tl.fromTo($(".jc-dot"),{opacity:0,y:-60},{opacity:1,y:0,duration:.3,stagger:.06,ease:BK.EASE.settle},P.at[1]);
BK.slam(tl,".jc-side",P.at[2]);BK.count(tl,".jc-n",parseInt(root.querySelector(".jc-n").textContent,10)||0,P.at[2]+0.15,{duration:.6});tl.fromTo($(".jc-bad"),{scale:1},{scale:1.3,duration:.25,ease:BK.EASE.pop,immediateRender:false},P.at[2]+0.4);
BK.slam(tl,".jc-scope",P.at[3]);''',
        notes=(f'Can we trust the judge? The team labelled {npairs} claims by hand. Each dot is one claim, placed by human label and judge label. '
               f'{agree} fall on the diagonal; Cohen’s kappa is {fmt(cal.get("kappa"))}. {dis_text} '
               f'These are historical claims with the earlier evidence, so this calibrates the rubric, not accuracy on today’s answers.'))

    # ------------------------------------------------------------ 16 rules and reviews
    pr = D.get('product', {})
    ev = D.get('failures', {}).get('evaluation', {})
    apv = d['approvals']
    apv_note = ('Recorded after the run (run records say draft)' + ('; content unchanged per eval/week3_provenance.py.' if d.get('provenance_script') else '.')) if apv['after_run'] else 'Review status as recorded in the files.'
    body = (f'<div class="bk-panel w3-abs rv-c" style="left:96px;top:390px;width:1728px;padding:26px 30px"><span class="bk-tab">judge rule</span>'
            f'<p class="w3-lead" style="margin-top:6px;font-size:44px">{h(ev.get("title", "null"))}</p><p class="w3-cap" style="font-size:34px;margin-top:8px">Week 2 marked every phone number or URL as invented. Now a detail passes only if an authorized source contains it.</p></div>'
            f'<div class="bk-panel w3-abs rv-c" style="left:96px;top:680px;width:840px;padding:26px 30px"><span class="bk-tab bk-tab--teal">human approval</span>'
            f'<span class="w3-big" style="font-size:64px">{fmt(apv["docs"])} / {fmt(apv["docs_total"])}</span><span class="w3-cap" style="font-size:30px"> docs</span> '
            f'<span class="w3-big" style="font-size:64px;margin-left:16px">{fmt(apv["cases"])} / {fmt(apv["cases_total"])}</span><span class="w3-cap" style="font-size:30px"> cases</span>'
            f'<p class="w3-cap" style="font-size:30px">{h(apv_note)}</p></div>'
            f'<div class="bk-panel w3-abs rv-c" style="left:984px;top:680px;width:840px;padding:26px 30px"><span class="bk-tab bk-tab--teal">product track</span>'
            f'<span class="w3-big" style="font-size:96px">{fmt(pr.get("interviews_completed"))} / 2</span><p class="w3-cap" style="font-size:34px">customer interviews, notes preserved</p></div>')
    add(id='w3-reviews', part='failures', speaker='Tarık', seconds=15, title='The rules and reviews behind the numbers', label='Failure analysis / evaluation',
        folio='BELDESK / REVIEW', repo='prompts/judge/ · reports/week-3.md', steps=[1.1, 1.1], body=body,
        js='''var c=$(".rv-c");BK.slam(tl,c[0],0.3);BK.slam(tl,c[1],P.at[1]);BK.slam(tl,c[2],P.at[2]);''',
        notes=(f'Two boundaries behind these numbers. The judge now accepts a contact detail only if an authorized source contains it. '
               f'The team approved {fmt(apv["docs"])} of {fmt(apv["docs_total"])} documents and {fmt(apv["cases"])} of {fmt(apv["cases_total"])} test cases' + (', recorded after the run on the same content. ' if apv['after_run'] else '. ')
               + f'Our {fmt(pr.get("interviews_completed"))} customer interviews are done.'))

    # ------------------------------------------------------------ 17 next week
    xs = [14 + i * 900 / 6 for i in range(7)]
    st = ''.join(f'<div class="w3-st is-done{" is-last" if i == 6 else ""}" style="left:{xs[i]:.0f}px"><b></b></div>' for i in range(7))
    new = ['Lookup', 'Confirm', 'Agent loop', 'Measured']
    nx = [1080, 1300, 1490, 1714]
    st += ''.join(f'<div class="w3-st is-new nx-new{" is-last" if i == 3 else ""}" style="left:{x}px"><b></b><span>{h(nm)}</span></div>' for i, (x, nm) in enumerate(zip(nx, new)))
    body = (f'<div class="w3-rail nx-rail"><i class="w3-rail-line" style="right:auto;width:900px"></i><i class="w3-rail-done" style="width:900px"></i>{st}'
            f'<i class="nx-ext" style="position:absolute;left:914px;top:14px;width:{nx[-1] - 914}px;height:0;border-top:4px dashed var(--ink);transform-origin:0 50%"></i>'
            f'<span class="bk-label" style="position:absolute;left:0;top:44px">Week 3 route</span></div>')
    pri = d['priorities'] or [{'priority': '1. null', 'metric': 'null', 'expected': 'null'}]
    cards = ''
    for i, pr_ in enumerate(pri[:3]):
        title = re.sub(r'^\d+\.\s*', '', pr_['priority'])
        title, _, aside = title.partition(' (')
        cards += (f'<section class="bk-panel w3-prio nx-p" style="left:{96 + i * 589}px;top:400px;height:530px"><span class="bk-tab bk-tab--sun">priority {i + 1} · plan</span>'
                  f'<h3 style="margin-top:6px;font-size:34px;margin-bottom:8px">{h(title)}</h3>' + (f'<p style="font-size:28px">({h(aside)}</p>' if aside else '') +
                  f'<p class="bk-label" style="margin-top:12px">metric it should move</p><span class="w3-tag w3-tag--sun" style="position:static;display:inline-block;white-space:normal;margin-top:6px">{h(pr_["metric"])}</span>'
                  f'<p class="bk-label" style="margin-top:12px">expected change</p><p>{h(pr_["expected"])}</p></section>')
    body += cards
    add(id='w3-next', part='next', speaker='Tarık', seconds=35, title='Next week: three priorities, each tied to a metric', label='Next week / plan',
        folio='BELDESK / NEXT WEEK', repo='reports/week-3.md · Next week', steps=[1.3, 1.1, 1.1], body=body,
        js='''BK.draw(tl,".nx-rail .w3-rail-line",0.2);BK.fade(tl,$(".nx-rail .w3-st.is-done"),0.3,{stagger:.03});BK.draw(tl,".nx-rail .w3-rail-done",0.4);
BK.draw(tl,".nx-ext",0.55,{duration:.45});tl.fromTo($(".nx-new"),{opacity:0,scale:.5},{opacity:1,scale:1,duration:.28,stagger:.08,ease:BK.EASE.pop},0.75);
var p=$(".nx-p");BK.slam(tl,p[0],P.at[1]);BK.slam(tl,p[1],P.at[2]);BK.slam(tl,p[2],P.at[3]);''',
        notes=('These are plans, not results; each names the metric it should move. '
               + ' '.join(f'{["First", "Second", "Third"][k]}: {re.sub(r"^[0-9]+[.] *", "", p_["priority"]).split(" (")[0].lower()}, for {p_["metric"].replace("_", " ")}.' for k, p_ in enumerate(pri[:3]))
               + ' On the route, the new stations are tools, confirmation and an agent loop, and every station gets measured before we trust it.'))

    # ------------------------------------------------------------ 18 reproduce
    rm = d['retrieval_meta']
    body = (f'<div class="bk-term w3-abs rp-term" style="left:96px;top:390px;width:1100px"><div class="bk-term-bar"><i></i><i></i><i></i><b>reproduce</b></div>'
            f'<div class="bk-term-body" style="font-size:32px"><span class="bk-term-line">python -m eval.retrieval_week3</span><span class="bk-term-line">python -m eval.answer_week3</span>'
            f'<span class="bk-term-line">python -m pytest -q</span><span class="bk-term-line">python scripts/build_week3_presentation.py</span></div></div>'
            f'<div class="bk-panel w3-abs rp-h" style="left:1250px;top:390px;width:574px;padding:24px 28px"><span class="bk-tab">hashes travel with results</span>'
            + ''.join(f'<p class="w3-mono" style="font-size:28px;margin-top:6px">{k}: {h((rm.get(k + "_sha256") or "null")[:12])}</p>' for k in ('corpus', 'index', 'cases', 'config')) +
            f'<p class="w3-mono" style="font-size:28px;margin-top:10px">retrieval API calls: {fmt(rm.get("api_calls"))}</p></div>'
            f'<div class="bk-panel w3-abs rp-t" style="left:96px;top:760px;width:1100px;padding:20px 28px"><span class="w3-big" style="font-size:64px">{fmt(D.get("tests_passed"))}</span><span class="w3-cap" style="margin-left:16px">tests passed (recorded in presentation_data.json)</span></div>')
    add(id='w3-reproduce', part='next', speaker='Tarık', seconds=15, title='Every number traces back to a command and a hash', label='Next week / reproducibility',
        folio='BELDESK / EVIDENCE', repo='README.md · eval/results/week3/', steps=[1.1], body=body,
        js='''BK.slam(tl,".rp-term",0.3);BK.slam(tl,".rp-h",0.5);BK.slam(tl,".rp-t",P.at[1]);''',
        notes='Every number in this deck is read from recorded result files when the deck is built, so a corrected metric updates every slide. Retrieval runs locally without an API key, and corpus, index and question hashes travel with the results.')

    return S


def value_of(item):
    return item.get('value') if isinstance(item, dict) else item
