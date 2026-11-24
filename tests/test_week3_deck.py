"""Checks for the generated Week 3 deck (scripts/build_week3_presentation.py)."""
import base64
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_week3_presentation', ROOT / 'scripts/build_week3_presentation.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
DATA = json.loads((ROOT / 'eval/results/week3/presentation_data.json').read_text(encoding='utf-8'))


def build(tmp_path, data=None):
    out = tmp_path / 'index.html'
    man = builder.build(data_override=data, out=out, manifest=tmp_path / 'manifest.json', script=tmp_path / 'script.md')
    html = out.read_text(encoding='utf-8')
    comp = base64.b64decode(re.search(r'atob\("([A-Za-z0-9+/=]+)"\)', html)[1]).decode()
    show = json.loads(re.search(r'<script type="application/hyperframes-slideshow\+json">(.*?)</script>', comp, re.S)[1])
    return man, html, comp, show, (tmp_path / 'script.md').read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def deck(tmp_path_factory):
    return build(tmp_path_factory.mktemp('deck'))


def test_timing_split_and_narration(deck):
    man = deck[0]
    parts = {p['part']: p for p in man['parts']}
    assert {k: parts[k]['planned_seconds'] for k in parts} == {'demo': 120, 'scoreboard': 120, 'failures': 120, 'next': 60}
    assert man['total_speaking_seconds'] == 420
    for p in parts.values():  # narration at 150 wpm lands within 15% of each part's slot
        assert abs(p['narration_seconds_at_wpm'] - p['target_seconds']) <= 0.15 * p['target_seconds'], p
    assert 380 <= sum(p['narration_seconds_at_wpm'] for p in parts.values()) <= 460


def test_slideshow_contract(deck):
    man, html, comp, show, script = deck
    ids = [s['sceneId'] for s in show['slides']]
    assert len(ids) == len(man['slides']) == 19 and ids[0] == 'cover' and 'scoreboard' in ids
    for sid in ids + [q['id'] for q in show['slideSequences']]:
        assert f'data-composition-id="{sid}"' in comp
    starts = [float(m) for m in re.findall(r'data-composition-id="[^"]+" data-label="[^"]*" data-start="([\d.]+)"', comp)]
    assert starts == sorted(starts)
    hot = show['slides'][-1]['hotspots']
    seqs = {q['id'] for q in show['slideSequences']}
    assert len(hot) == 4 and {h['target'] for h in hot} == seqs  # every Q&A branch is reachable
    for s in show['slides']:
        assert s['fragments'] == sorted(s['fragments']) and s['notes'].strip()
    body = comp.split('<body>', 1)[1]
    assert not re.search(r'(src|href)="https?:', body)  # nothing loads from the network
    assert 3_000_000 < len(html) < 25_000_000


def test_roadmap_statuses_not_blank(deck):
    comp = deck[2]
    road = comp[comp.index('id="w3-roadmap"'):comp.index('id="w3-gate"')]
    assert 'done: <' not in road and ':</span>' not in road
    assert road.count('rm-chip') == 8 and 'partial' in road


def test_recorded_runs_marked_and_script_generated(deck):
    man, html, comp, show, script = deck
    notes = {s['sceneId']: s['notes'] for s in show['slides']}
    for sid in ('w3-answer', 'w3-r032', 'w3-r032-answer'):
        assert 'RECORDED RUN' in notes[sid]
    assert 'not live' in comp
    for s in man['slides']:
        assert s['notes'] in script


def test_numbers_come_from_data(tmp_path):
    data = copy.deepcopy(DATA)
    data['scoreboard']['unsupported_claims'] = {'value': 1 / 90, 'n': 90, 'numerator': 1, 'ci95': [0.002, 0.06]}
    data['scoreboard']['latency_p50_s'] = None
    man, html, comp, show, script = build(tmp_path, data)
    board = comp[comp.index('id="sb-table"'):comp.index('id="sb-tally"')]
    row = re.search(r'unsupported_claims</span>(.*?)</div>', board)[1]
    assert '0.011' in row and 'n=90' in row and '[0.00, 0.06]' in row
    lat = re.search(r'latency_p50_s</span>(.*?)</div>', board)[1]
    assert 'sb-null' in lat and 'null' in lat
    assert '1 / 90 unsupported' in comp


def test_lane_ranks_recovered_from_rrf():
    from week3_deck import data as dd
    d = dd.load()
    j = d['fail_journey']
    assert j['case_id'] == DATA['retrieval_failure']['case_id']
    ranks = {c['pid']: c['rerank'] for c in j['cards']}
    assert ranks.get(DATA['retrieval_failure']['evidence_label']) > 5  # the missed facet sits below the top-5 cut
    for c in j['cards']:
        if c.get('lane_bm25') or c.get('lane_dense'):
            v = (1 / (60 + c['lane_bm25']) if c['lane_bm25'] else 0) + (1 / (60 + c['lane_dense']) if c['lane_dense'] else 0)
            assert abs(v - c['rrf_score']) < 1e-12


def _scene(comp, sid, nxt):
    start = comp.index(f'data-composition-id="{sid}"')
    return comp[start:comp.index(f'data-composition-id="{nxt}"', start)]


def test_corrected_claim_rate_and_cost_notes(deck):
    man, html, comp, show, script = deck
    from week3_deck import data as dd
    d = dd.load()
    cm = d['claims']
    assert isinstance(cm['numerator'], int) and isinstance(cm['n'], int)  # numerator found via the fallback chain
    claims = _scene(comp, 'w3-claims', 'scoreboard')
    assert f'{cm["numerator"]} / {cm["n"]} unsupported' in claims and 'null / ' not in claims
    assert claims.count('cl-bad') >= 1
    if cm['before']:
        assert f'{cm["before"]["numerator"]} / {cm["before"]["n"]}' in claims
    board = _scene(comp, 'scoreboard', 'w3-r032')
    sb = DATA['scoreboard']
    if sb.get('cost_per_task_usd') is not None:
        assert 'list-price estimate' in board and 'billing unknown' not in board


def test_failure_attribution_follows_recorded_stage(deck):
    man, html, comp, show, script = deck
    from week3_deck import data as dd
    d = dd.load()
    rec = {f['case_id']: f for f in d['answer_failures']}
    for key, stage in (('retrieval', 'retrieval'), ('judge', 'evaluation')):
        for c in d['stage_cases'][key]:
            assert rec.get(c['id'], {}).get('stage', stage) == stage
    fid = DATA['retrieval_failure']['case_id']
    assert all(c['id'] != fid for c in d['stage_cases']['generation'])
    ans = _scene(comp, 'w3-r032-answer', 'w3-stages')
    assert f'Root cause: {rec[fid]["stage"]}' in ans
    notes = {s['sceneId']: s['notes'] for s in show['slides']}
    for text in (notes['w3-r032-answer'], script):
        assert 'fails twice' not in text and 'marked that refusal unsupported' not in text


def test_approvals_and_next_week_from_files(deck):
    man, html, comp, show, script = deck
    from week3_deck import data as dd
    d = dd.load()
    apv = d['approvals']
    rev = _scene(comp, 'w3-reviews', 'w3-next')
    assert f'{apv["docs"]} / {apv["docs_total"]}' in rev and f'{apv["cases"]} / {apv["cases_total"]}' in rev
    nxt = _scene(comp, 'w3-next', 'w3-reproduce')
    assert d['priorities'] and all(p['metric'] in nxt.replace('&#x27;', "'") for p in d['priorities'][:3])


def test_no_null_counts_in_speaking_script():
    """A renamed data field must not surface as 'null of N' or 'null /' in narration."""
    import re
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1] / 'docs' / 'week3_speaking_script.md').read_text(encoding='utf-8')
    assert not re.search(r'\bnull (of|/) ?\d', script)
    assert '5 of 6 unavailable-information controls' in script
