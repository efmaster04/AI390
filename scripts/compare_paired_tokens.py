"""Compare measured request-input tokens for the two v2 TR/EN pairs.

This reads a fresh baseline run; it makes no model calls. It rejects v1 evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [('water-subscription', 'W1-02', 'W1-03'),
         ('ticket-status', 'W1-10', 'W1-07')]


def compare(results_dir, inputs_path, temperature=0):
    content = inputs_path.read_bytes()
    inputs = [json.loads(line) for line in content.decode('utf-8').splitlines() if line.strip()]
    if len(inputs) != 25 or len({r['id'] for r in inputs}) != 25:
        raise ValueError('Expected exactly 25 unique active inputs')
    by_id = {r['id']: r for r in inputs}
    for _, en_id, tr_id in PAIRS:
        en, tr = by_id[en_id], by_id[tr_id]
        if en['lang'] != 'en' or tr['lang'] != 'tr' or tr['expected_behavior'] != en['expected_behavior']:
            raise ValueError('Expected the documented v2 translation pairs')
    metadata_paths = list(results_dir.glob('run_meta_gemini__*.json'))
    if len(metadata_paths) != 1:
        raise ValueError('Use a directory with exactly one Gemini run')
    meta = json.loads(metadata_paths[0].read_text())
    if meta.get('inputs_sha256') != hashlib.sha256(content).hexdigest():
        raise ValueError('Run inputs differ from active v2. Rerun the 25 current inputs; do not reuse historical v1 responses.')
    if meta.get('prompt_sha256') != hashlib.sha256((ROOT / meta['prompt']).read_bytes()).hexdigest():
        raise ValueError('System prompt differs from the measured run')
    if temperature not in meta['temps']:
        raise ValueError('Selected temperature was not measured')
    result_path = metadata_paths[0].with_name(metadata_paths[0].name.replace('run_meta_', '').replace('.json', f'__t{temperature:g}.jsonl'))
    rows = [json.loads(line) for line in result_path.read_text().splitlines() if line.strip()]
    if len(rows) != 25 or len({r['id'] for r in rows}) != 25 or {r['id'] for r in rows} != set(by_id):
        raise ValueError('Expected 25 complete result rows matching current IDs')
    results = {r['id']: r for r in rows}
    comparisons = []
    for name, en_id, tr_id in PAIRS:
        en, tr = results[en_id], results[tr_id]
        if any(r.get('error') or r.get('dry_run') or r.get('temperature') != temperature for r in (en, tr)):
            raise ValueError('Pairs require successful, real, same-temperature calls')
        if any(not isinstance(r.get('input_tokens'), int) or r['input_tokens'] <= 0 for r in (en, tr)):
            raise ValueError('Measured input-token counts are required')
        comparisons.append({'pair': name, 'en_id': en_id, 'tr_id': tr_id,
                            'en_input_tokens': en['input_tokens'], 'tr_input_tokens': tr['input_tokens'],
                            'tr_minus_en': tr['input_tokens'] - en['input_tokens'],
                            'tr_over_en': tr['input_tokens'] / en['input_tokens']})
    return {'model': meta['model'], 'temperature': temperature, 'pair_count': 2,
            'inputs_sha256': meta['inputs_sha256'], 'prompt_sha256': meta['prompt_sha256'],
            'comparisons': comparisons,
            'limitations': 'Request input tokens include the common system prompt and request framing. Two translated pairs are illustrative, not a language-wide estimate. Generated output tokens are not a controlled tokenization comparison.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', required=True, type=Path)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'eval/testsets/week1_inputs.jsonl')
    parser.add_argument('--temperature', type=float, default=0)
    args = parser.parse_args()
    try:
        result = compare(args.results_dir, args.inputs, args.temperature)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f'Not measured: {exc}\n')
    (args.results_dir / 'paired_tokens.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('| Pair | EN input tokens | TR input tokens | TR - EN | TR / EN |')
    print('|---|---:|---:|---:|---:|')
    for r in result['comparisons']:
        print(f"| {r['pair']} | {r['en_input_tokens']} | {r['tr_input_tokens']} | {r['tr_minus_en']} | {r['tr_over_en']:.3f} |")
    print(result['limitations'])


if __name__ == '__main__':
    main()
