import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from src.baseline import providers
from src.baseline.providers import DryProvider, ProviderError
from src.classifier import validate
from src.classifier.classify import classify, load_prompt

ROOT = Path(__file__).resolve().parents[1]
classifier = importlib.import_module('src.classifier.classify')


def valid_result():
    return {
        'intent': 'field_complaint', 'secondary_intents': [], 'lang': 'tr',
        'ticket_id': None, 'missing_fields': [], 'issues': [{
            'category': 'street_lighting', 'urgency': 'P3', 'urgency_status': 'classified',
            'location': {'neighborhood': None, 'street': 'Test Sokak', 'detail': None},
            'scope': 'single_point', 'onset_text': None, 'sensitive_use': None,
            'referral_needed': 'no', 'urgency_reason': 'One failed streetlight.'}]}


class FakeProvider:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, system, user, temperature, max_tokens, seed, *, json_mode=False):
        self.calls.append(dict(system=system, user=user, temperature=temperature,
                               max_tokens=max_tokens, seed=seed, json_mode=json_mode))
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        if isinstance(output, dict):
            return output
        return {'output': output, 'input_tokens': 4, 'output_tokens': 8}


def test_first_valid_and_call_contract():
    provider = FakeProvider([json.dumps(valid_result())])
    report = classify('test', provider)
    assert report['valid'] and report['attempts'] == 1
    assert report['result'] == valid_result()
    assert report['errors'] == [] and report['provider_error'] is None
    assert report['input_tokens'] == 4 and report['output_tokens'] == 8
    assert report['latency_s'] >= 0 and len(report['prompt_sha256']) == 64
    assert provider.calls[0]['json_mode'] is True
    assert provider.calls[0]['temperature'] == 0
    assert provider.calls[0]['max_tokens'] == 800 and provider.calls[0]['seed'] == 42


@pytest.mark.parametrize('bad', ['broken JSON', json.dumps({'intent': 'faq'})])
def test_invalid_then_valid(bad):
    provider = FakeProvider([bad, json.dumps(valid_result())])
    report = classify('test', provider)
    assert report['valid'] and report['attempts'] == 2
    assert 'previous output was invalid' in provider.calls[1]['system']
    assert report['input_tokens'] == 8 and report['output_tokens'] == 16
    assert len(report['raw_outputs']) == 2


def test_exhausted():
    report = classify('test', FakeProvider(['bad'] * 3))
    assert not report['valid'] and report['result'] is None and report['attempts'] == 3
    assert report['errors'] and len(report['raw_outputs']) == 3


@pytest.mark.parametrize('wrapper', ['```json\n{}\n```', 'Some prose\n{}\nEnd.'])
def test_wrapped_json(wrapper):
    assert classify('test', FakeProvider([wrapper.format(json.dumps(valid_result()))]))['valid']


@pytest.mark.parametrize('raw', ['[]', '[{}]', '```json\n[{}]\n```'])
def test_lists_rejected(raw):
    assert not classify('test', FakeProvider([raw]), max_retries=0)['valid']


def test_truncation_feedback_and_unknown_usage():
    provider = FakeProvider([
        {'output': '{', 'input_tokens': None, 'output_tokens': 2, 'finish_reason': 'MAX_TOKENS'},
        {'output': json.dumps(valid_result()), 'input_tokens': 3, 'output_tokens': None}])
    report = classify('test', provider)
    assert report['valid']
    assert report['input_tokens'] is None and report['output_tokens'] is None
    assert 'keep the JSON short' in provider.calls[1]['system']


def test_retryable_transport_does_not_use_validation_attempt(monkeypatch):
    sleeps = []
    monkeypatch.setattr(classifier.time, 'sleep', sleeps.append)
    provider = FakeProvider([ProviderError('busy', True), json.dumps(valid_result())])
    report = classify('test', provider)
    assert report['valid'] and report['attempts'] == 1
    assert len(provider.calls) == 2 and sleeps == [2]


@pytest.mark.parametrize('retryable,count', [(False, 1), (True, 2)])
def test_provider_failure(monkeypatch, retryable, count):
    monkeypatch.setattr(classifier.time, 'sleep', lambda _: None)
    provider = FakeProvider([ProviderError('unavailable', retryable)] * 2)
    report = classify('test', provider)
    assert report['provider_error'] == 'unavailable'
    assert not report['valid'] and report['result'] is None
    assert report['attempts'] == 1 and len(provider.calls) == count


def test_prompt_loading(tmp_path):
    path = tmp_path / 'prompt.md'
    path.write_bytes(b'---\nversion: v1\n---\n\nClassify.\n')
    text, digest = load_prompt(path)
    assert text == 'Classify.\n'
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text('plain prompt')
    assert load_prompt(path)[0] == 'plain prompt'
    report = classify('test', DryProvider(), prompt_path=tmp_path / 'absent')
    assert not report['valid'] and report['attempts'] == 0


def test_dry():
    assert DryProvider().generate('s', 'hello', 0, 800, 42)['output'] == '[dry-run] hello'
    assert validate(json.loads(providers.DRY_JSON)) == []
    assert classify('test', DryProvider())['valid']


def test_valid_and_clarification():
    obj = valid_result()
    assert validate(obj) == []
    obj['issues'][0].update(urgency=None, urgency_status='needs_clarification', urgency_reason=None)
    obj['issues'][0]['location'] = None
    assert validate(obj) == []


@pytest.mark.parametrize('path,value,fragment', [
    (('intent',), 'invalid', 'intent'),
    (('lang',), 'de', 'lang'),
    (('secondary_intents',), ['faq', 'faq'], 'duplicate'),
    (('secondary_intents',), ['field_complaint'], 'primary intent'),
    (('secondary_intents',), ['nope'], 'secondary_intents[0]'),
    (('secondary_intents',), None, 'secondary_intents'),
    (('missing_fields',), ['location', 'location'], 'duplicate'),
    (('missing_fields',), ['bad'], 'missing_fields[0]'),
    (('missing_fields',), 'location', 'missing_fields'),
    (('ticket_id',), 'YV-26-012345', 'ticket_id'),
    (('ticket_id',), 123, 'ticket_id'),
    (('issues',), [], 'non-empty iff'),
    (('issues',), {}, 'issues'),
    (('issues', 0), [], 'issues[0]'),
    (('issues', 0, 'category'), 'bad', 'issues[0].category'),
    (('issues', 0, 'urgency'), 'P5', 'issues[0].urgency'),
    (('issues', 0, 'urgency'), None, 'null iff'),
    (('issues', 0, 'urgency_status'), 'bad', 'issues[0].urgency_status'),
    (('issues', 0, 'urgency_status'), 'needs_clarification', 'null iff'),
    (('issues', 0, 'scope'), 'bad', 'issues[0].scope'),
    (('issues', 0, 'referral_needed'), 'maybe', 'issues[0].referral_needed'),
    (('issues', 0, 'urgency_reason'), '', 'must not be empty'),
    (('issues', 0, 'urgency_reason'), '  ', 'must not be empty'),
    (('issues', 0, 'urgency_reason'), None, 'issues[0].urgency_reason'),
    (('issues', 0, 'urgency_reason'), 3, 'issues[0].urgency_reason'),
    (('issues', 0, 'location'), 'here', 'issues[0].location'),
    (('issues', 0, 'location', 'street'), 1, 'issues[0].location.street'),
    (('issues', 0, 'onset_text'), 1, 'issues[0].onset_text'),
    (('issues', 0, 'sensitive_use'), [], 'issues[0].sensitive_use'),
])
def test_schema_rule(path, value, fragment):
    obj = valid_result()
    target = obj
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    assert any(fragment in error for error in validate(obj))


@pytest.mark.parametrize('path', [(), ('issues', 0), ('issues', 0, 'location')])
def test_exact_keys(path):
    obj = valid_result()
    target = obj
    for part in path:
        target = target[part]
    key = next(iter(target))
    del target[key]
    target['extra'] = None
    errors = validate(obj)
    assert any(f'{key}: missing key' in error for error in errors)
    assert any('extra: unexpected key' in error for error in errors)


@pytest.mark.parametrize('obj', [None, [], 'text', 4])
def test_root_object(obj):
    assert validate(obj) == ['result: expected object']


def test_emergency_and_secondary_field_complaint():
    obj = valid_result()
    obj['intent'] = 'emergency'
    errors = validate(obj)
    assert any('emergency without' in error for error in errors)
    assert any('non-empty iff' in error for error in errors)
    obj['secondary_intents'] = ['field_complaint']
    assert validate(obj) == []
    obj['secondary_intents'] = []
    obj['issues'] = []
    assert validate(obj) == []


def test_all_42_expected_outputs():
    rows = [json.loads(line) for line in (ROOT / 'eval/testsets/week2_cases.jsonl').read_text().splitlines()]
    assert len(rows) == 42
    for case in rows:
        expected = copy.deepcopy(case['expected'])
        expected['lang'] = case['lang']
        for issue in expected['issues']:
            issue['urgency_reason'] = 'x' if issue['urgency_status'] == 'classified' else None
        assert validate(expected) == [], case['id']


@pytest.mark.parametrize('name', ['gemini', 'ollama', 'openai_compat'])
@pytest.mark.parametrize('json_mode', [False, True])
def test_provider_json_payloads(monkeypatch, name, json_mode):
    captured = []
    monkeypatch.setattr(providers, '_post', lambda *args, **kwargs: captured.append(kwargs['payload']) or {})
    if name == 'gemini':
        provider = providers.GeminiProvider('model', '')
    elif name == 'ollama':
        provider = providers.OllamaProvider('model', 'http://localhost')
    else:
        provider = providers.OpenAICompatProvider('model', 'http://localhost', '')
    response = provider.generate('s', 'u', 0, 800, 42, json_mode=json_mode)
    assert response['output'] == ''
    payload = captured[0]
    if name == 'gemini':
        assert payload['generationConfig'].get('responseMimeType') == ('application/json' if json_mode else None)
    elif name == 'ollama':
        assert payload.get('format') == ('json' if json_mode else None)
    else:
        assert payload.get('response_format') == ({'type': 'json_object'} if json_mode else None)


def test_empty_gemini_candidates_retry(monkeypatch):
    monkeypatch.setattr(providers, '_post', lambda *args, **kwargs: {'candidates': []})
    report = classify('test', providers.GeminiProvider('model', ''))
    assert not report['valid'] and report['attempts'] == 3
    assert report['raw_outputs'] == ['', '', '']
