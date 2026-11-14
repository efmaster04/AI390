import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = json.loads((ROOT / 'config/case_labels.json').read_text())
CASES = [json.loads(line) for line in (ROOT / 'eval/testsets/week2_cases.jsonl').read_text().splitlines() if line.strip()]
WEEK1 = {r['id']: r for r in map(json.loads, (ROOT / 'eval/testsets/week1_inputs.jsonl').read_text().splitlines())}
TOP_KEYS = list(LABELS['case_format'])
EXPECTED_KEYS = list(LABELS['case_format']['expected'])
ISSUE_KEYS = list(LABELS['case_format']['expected']['issues'][0])
LOCATION_KEYS = {'neighborhood', 'street', 'detail'}


def _intents(e):
    return {e['intent'], *e['secondary_intents']}


def test_contract_version():
    assert LABELS['contract_version'] == 2
    assert LABELS['policy_version'] == '0.3-draft'


def test_size_and_sequential_ids():
    assert len(CASES) >= 40
    assert [c['id'] for c in CASES] == [f'W2-{i:03d}' for i in range(1, len(CASES) + 1)]


def test_every_value_in_vocab():
    for c in CASES:
        cid = c['id']
        assert list(c) == TOP_KEYS, cid
        e = c['expected']
        assert list(e) == EXPECTED_KEYS, cid
        assert c['lang'] in LABELS['langs'] and c['type'] in LABELS['types'], cid
        assert c['ingredients'] and all(isinstance(i, int) and 1 <= i <= 8 for i in c['ingredients']), cid
        assert isinstance(c['text'], str) and c['text'], cid
        assert e['intent'] in LABELS['intents'], cid
        assert all(s in LABELS['intents'] and s != e['intent'] for s in e['secondary_intents']), cid
        assert len(set(e['secondary_intents'])) == len(e['secondary_intents']), cid
        assert isinstance(e['issues'], list), cid
        for issue in e['issues']:
            assert list(issue) == ISSUE_KEYS, cid
            assert issue['category'] in LABELS['categories'], cid
            assert issue['urgency'] is None or issue['urgency'] in LABELS['urgencies'], cid
            assert issue['urgency_status'] in LABELS['urgency_statuses'], cid
            loc = issue['location']
            assert loc is None or (set(loc) == LOCATION_KEYS
                                   and all(v is None or (isinstance(v, str) and v) for v in loc.values())), cid
            assert issue['scope'] in LABELS['scopes'], cid
            assert issue['onset_text'] is None or (isinstance(issue['onset_text'], str) and issue['onset_text']), cid
            assert issue['sensitive_use'] is None or (isinstance(issue['sensitive_use'], str) and issue['sensitive_use']), cid
            assert issue['referral_needed'] in LABELS['referral_values'], cid
        assert e['ticket_id'] is None or re.fullmatch(r'YV-\d{4}-\d{6}', e['ticket_id']), cid
        assert isinstance(e['missing_fields'], list), cid
        assert all(m in LABELS['missing_field_values'] for m in e['missing_fields']), cid
        assert len(set(e['missing_fields'])) == len(e['missing_fields']), cid
        assert isinstance(c['expected_behavior'], str) and c['expected_behavior'], cid
        assert isinstance(c['answerable'], bool), cid


def test_onset_text_is_verbatim():
    for c in CASES:
        for issue in c['expected']['issues']:
            if issue['onset_text']:
                assert issue['onset_text'] in c['text'], c['id']


def test_review_shape():
    for c in CASES:
        review = c['review']
        assert set(review) == {'status', 'reviewer', 'note', 'updated_at'}, c['id']
        assert review['status'] in LABELS['review_statuses'], c['id']
        assert review['note'] is None or isinstance(review['note'], str), c['id']
        assert review['reviewer'] is None or isinstance(review['reviewer'], str), c['id']
        assert review['updated_at'] is None or isinstance(review['updated_at'], str), c['id']


def test_type_minimums():
    counts = Counter(c['type'] for c in CASES)
    for t in ('unanswerable', 'adversarial', 'edge'):
        assert counts[t] >= 5, t


# Rules from config/case_labels.json "rules"

def test_issues_iff_field_complaint():
    for c in CASES:
        e = c['expected']
        assert bool(e['issues']) == ('field_complaint' in _intents(e)), c['id']


def test_urgency_null_iff_needs_clarification():
    for c in CASES:
        for issue in c['expected']['issues']:
            assert (issue['urgency'] is None) == (issue['urgency_status'] == 'needs_clarification'), c['id']


def test_emergency_without_field_complaint_has_no_issues():
    for c in CASES:
        e = c['expected']
        if 'emergency' in _intents(e) and 'field_complaint' not in _intents(e):
            assert e['issues'] == [], c['id']


def test_unanswerable_cases_are_not_answerable():
    assert all(c['answerable'] is False for c in CASES if c['type'] == 'unanswerable')


def test_week1_carry_over_is_verbatim():
    for i in range(1, 26):
        c = CASES[i - 1]
        src = f'W1-{i:02d}'
        assert c['source_id'] == src
        assert c['text'] == WEEK1[src]['text']
        assert c['lang'] == WEEK1[src]['lang']
    assert all(c['source_id'] is None for c in CASES[25:])
