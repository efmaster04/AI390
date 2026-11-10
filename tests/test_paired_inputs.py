import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paired_tokens', ROOT / 'scripts/compare_paired_tokens.py')
paired = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paired)


def test_active_set_stays_25_and_pairs_keep_identifiers():
    rows = [json.loads(line) for line in (ROOT / 'eval/testsets/week1_inputs.jsonl').read_text().splitlines()]
    assert len(rows) == len({r['id'] for r in rows}) == 25
    assert Counter(r['lang'] for r in rows) == {'tr': 13, 'en': 12}
    assert Counter(r['category'] for r in rows) == {'question': 6, 'lookup': 4, 'action': 5, 'unanswerable': 4, 'multi_step': 3, 'untrusted': 3}
    by_id = {r['id']: r for r in rows}
    for _, en_id, tr_id in paired.PAIRS:
        en, tr = by_id[en_id], by_id[tr_id]
        assert en['lang'] == 'en' and tr['lang'] == 'tr'
        assert en['expected_behavior'] == tr['expected_behavior']
        assert en['expected_urgency'] == tr['expected_urgency']
        assert en['ingredients'] == tr['ingredients']
        assert re.findall(r'YV-\d{4}-\d{6}|\b\d{4}\b', en['text']) == re.findall(r'YV-\d{4}-\d{6}|\b\d{4}\b', tr['text'])


def test_historical_results_cannot_be_claimed_as_new_pairs():
    with pytest.raises(ValueError, match='differ from active v2'):
        paired.compare(ROOT / 'eval/results/week1', ROOT / 'eval/testsets/week1_inputs.jsonl')


def test_explorer_uses_original_input_hash_for_historical_results():
    spec = importlib.util.spec_from_file_location('explorer', ROOT / 'scripts/build_explorer.py')
    explorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explorer)
    meta = json.loads((ROOT / 'eval/results/week1/run_meta_gemini__gemini-3.1-flash-lite.json').read_text())
    rows, historical = explorer.result_inputs(meta)
    assert historical is True
    assert next(r for r in rows if r['id'] == 'W1-03')['text'].startswith('Yapı ruhsatı')
    assert next(r for r in rows if r['id'] == 'W1-07')['text'].startswith('YV-2026-004871')
