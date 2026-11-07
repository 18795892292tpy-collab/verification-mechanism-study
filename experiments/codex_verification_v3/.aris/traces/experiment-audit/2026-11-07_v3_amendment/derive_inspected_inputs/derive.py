#!/usr/bin/env python3
"""Independent, post-hoc P0 sensitivity analysis. No runner imports or model calls.

Only --write-results writes, exclusively to this amendment's new results directory.
It never changes frozen inputs, original raw records, or the original decision gate.
"""
from pathlib import Path
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import random
import re
import socket
import stat
import sys

sys.dont_write_bytecode = True
import jsonschema

ROOT = Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
HERE = Path(__file__).resolve().parent
FROZEN_SHA = 'bef848323484f7490f2ac5bbaf1eb67ca55af45745f22f74352c15dac8139887'
LABEL = 'posthoc_exploratory'
WARNINGS = [
    'Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /home/grf/.codex/config.toml.',
    'Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.',
    'Exceeded skills context budget. All skill descriptions were removed and 144 additional skills were not included in the model-visible skills list.',
]
EXPECTED_ERRORS = [{'id': f'item_{i}', 'message': message, 'type': 'error'} for i, message in enumerate(WARNINGS)]
PATTERN = ['thread.started', 'item.completed/error', 'item.completed/error', 'turn.started',
           'item.completed/error', 'item.completed/agent_message', 'turn.completed']
LIFECYCLE = ['thread.started', 'turn.started', 'turn.completed']


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def digest(value):
    return hashlib.sha256(value.encode('utf-8') if isinstance(value, str) else value).hexdigest()


def file_hash(path):
    require(path.is_file() and not path.is_symlink(), f'Not a regular input file: {path}')
    return digest(path.read_bytes())


def read(path):
    require(path.is_file() and not path.is_symlink(), f'Invalid JSON input: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def timestamp(value):
    t = datetime.fromisoformat(value)
    require(t.tzinfo is not None, 'Naive timestamp')
    return t


def known_token(value):
    return value if type(value) is int and value >= 0 else None


def usage_summary(attempts):
    result = {'actual_attempts': len(attempts)}
    for field in ['input_tokens', 'output_tokens']:
        values = [known_token(a.get(field)) for a in attempts]
        result['known_' + field] = sum(v for v in values if v is not None)
        result['sum_' + field] = sum(values) if all(v is not None for v in values) else None
        result[field + '_missing_attempts'] = sum(v is None for v in values)
    return result


def parse_events(text):
    events = []
    for line in text.splitlines():
        if line.strip():
            event = json.loads(line)
            require(type(event) is dict, 'Non-object raw event')
            events.append(event)
    errors, messages, sessions, usages, life, top_errors, pattern, unusual = [], [], [], [], [], [], [], []
    allowed = {'thread.started', 'turn.started', 'item.started', 'item.updated', 'item.completed', 'turn.completed', 'turn.failed', 'error'}
    for e in events:
        kind = e.get('type'); item = e.get('item', {})
        require(type(item) is dict, 'Invalid raw item')
        if kind not in allowed or (item and item.get('type') not in ['agent_message', 'reasoning', 'error']):
            unusual.append(e)
        pattern.append(str(kind) + ('/' + str(item.get('type')) if item else ''))
        if kind == 'thread.started':
            sessions.append(e.get('thread_id'))
        if kind in ['thread.started', 'turn.started', 'turn.completed', 'turn.failed']:
            life.append(kind)
        if kind in ['error', 'turn.failed']:
            top_errors.append(e)
        if item.get('type') == 'error':
            errors.append(item)
        if kind == 'item.completed' and item.get('type') == 'agent_message' and isinstance(item.get('text'), str) and item['text'].strip():
            messages.append(item['text'])
        if kind == 'turn.completed':
            usages.append(e.get('usage'))
    return {'events': events, 'error_items': errors, 'messages': messages, 'sessions': sessions,
            'usages': usages, 'lifecycle': life, 'top_errors': top_errors, 'pattern': pattern, 'unusual': unusual}


def classify_observed(meta, events, response, stderr, schema):
    """Outcome-blind exact exception policy; unknown diagnostics never get waived."""
    reasons = []
    if events['error_items'] != EXPECTED_ERRORS:
        reasons.append('diagnostic_objects_not_exact_allowlist')
    if events['pattern'] != PATTERN:
        reasons.append('event_order_not_exact_observed_signature')
    if events['lifecycle'] != LIFECYCLE or len(events['sessions']) != 1 or not isinstance(events['sessions'][0], str) or not events['sessions'][0].strip():
        reasons.append('invalid_single_session_lifecycle')
    if events['top_errors'] or events['unusual']:
        reasons.append('top_level_error_or_unknown_event_or_tool')
    if len(events['messages']) != 1 or response != (events['messages'][-1] if events['messages'] else None) or meta.get('output_sha256') != digest(response):
        reasons.append('dual_final_not_exactly_equal')
    if meta.get('returncode') != 0 or type(meta.get('returncode')) is not int or meta.get('error') is not None or meta.get('service_block') is not None:
        reasons.append('process_or_transport_failure')
    if re.search(r'\b(?:ERROR|FATAL)\b', stderr, re.IGNORECASE):
        reasons.append('stderr_error_or_fatal')
    try:
        parsed = json.loads(response)
        jsonschema.validate(parsed, schema)
    except (ValueError, TypeError, jsonschema.ValidationError):
        parsed = None
        reasons.append('schema_invalid')
    return {'accepted': not reasons, 'rejection_reasons': reasons, 'parsed': parsed if not reasons else None}


def assert_unique_sessions(sessions):
    require(all(isinstance(s, str) and s.strip() for s in sessions), 'Empty/non-string session ID')
    require(len(sessions) == len(set(sessions)), 'Duplicate session ID')


def validate_runtime(frozen):
    runtime = frozen['runtime']
    require(socket.gethostname() == runtime['hostname'] == 'liekkas', 'Wrong host')
    require(str(ROOT.resolve()) == runtime['root'] and ROOT == ROOT.resolve(), 'Wrong canonical target')
    cli = Path(runtime['cli_path']).resolve(strict=True)
    require(str(cli) == runtime['cli_resolved'] and file_hash(cli) == runtime['cli_sha256'], 'CLI wrapper identity changed')
    for path, expected in runtime['cli_dependency_sha256'].items():
        require(file_hash(Path(path)) == expected, 'CLI dependency changed: ' + path)
    package = read(cli.parent.parent / 'package.json')
    require(package['version'] == '0.166.0', 'Unexpected CLI version')
    require(str(Path.home()) == runtime['home'], 'Wrong user HOME')
    require(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')) == runtime['codex_home'], 'Wrong Codex home')


def inventory(root, frozen):
    paths = {root / 'protocol/frozen.json', *(root / p for p in frozen['sha256'])}
    for p in (root / 'runs').rglob('*'):
        require(not p.is_symlink(), 'Symlink in original runs')
        if p.is_file():
            paths.add(p)
        else:
            require(p.is_dir(), 'Nonregular raw artifact')
    gate = root / 'analysis/decision_gate.json'
    if gate.exists():
        paths.add(gate)
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(paths)}


def validate_inventory(root, frozen, jobs):
    expected = {'runs/.integrity.lock', 'runs/p0/plan.csv', 'runs/challenge/plan.csv',
                'runs/p0/manifest_identity.json', 'runs/p0/progress.jsonl'}
    for job in jobs:
        prefix = 'runs/p0/' + job['group_id'] + '/P0/'
        expected.update(prefix + name for name in ['prompt.txt', 'record.json'])
        expected.update(prefix + 'attempt_01/' + name for name in ['attempt_started.json', 'events.jsonl', 'stderr.txt', 'response.json', 'meta.json'])
    actual = {str(p.relative_to(root)) for p in (root / 'runs').rglob('*') if p.is_file()}
    require(actual == expected, 'Original inventory changed: extra=' + repr(sorted(actual - expected)) + ' missing=' + repr(sorted(expected - actual)))
    expected_dirs = {str(Path(path).parent) for path in expected}
    for path in list(expected_dirs):
        expected_dirs.update(str(p) for p in Path(path).parents if str(p) not in ['.', 'runs'])
    actual_dirs = {str(p.relative_to(root)) for p in (root / 'runs').rglob('*') if p.is_dir()}
    require(actual_dirs == expected_dirs - {'runs'}, 'Unexpected/empty original attempt directories')
    require(read(root / 'runs/p0/manifest_identity.json') == {'frozen_hash': FROZEN_SHA}, 'Original phase pin changed')
    for phase in ['p0', 'challenge']:
        with (root / f'runs/{phase}/plan.csv').open(newline='') as stream:
            actual_plan = list(csv.DictReader(stream))
        expected_plan = [{k: str(v) for k, v in j.items()} for j in frozen['phase_schedule'][phase]['jobs']]
        require(actual_plan == expected_plan, 'Run plan differs from frozen schedule')


def validate_task(root, job, item, prompts, schema, freeze_time):
    folder = root / 'runs/p0' / job['group_id'] / 'P0'; ad = folder / 'attempt_01'
    record = read(folder / 'record.json'); meta = read(ad / 'meta.json'); marker = read(ad / 'attempt_started.json')
    prompt = prompts['base'] + '\n\n档案与问题：\n' + item['public_text'] + '\n\n本次任务：给出你的决定。'
    identity = {**job, 'phase': 'p0', 'frozen_hash': FROZEN_SHA, 'first_sha256': None,
                'first_origin': None, 'gate_sha256': None, 'prompt_sha256': digest(prompt)}
    require(all(record.get(k) == v and marker.get(k) == v for k, v in identity.items()), 'Task/start marker identity mismatch')
    require((folder / 'prompt.txt').read_text() == prompt, 'Prompt does not match frozen input')
    require(record.get('attempts') == [meta] and meta.get('attempt') == marker.get('attempt') == 1, 'Extra or spliced attempt')
    for source in [meta, marker]:
        require(source.get('model_requested') == 'gpt-6-astra' and source.get('effort_requested') == 'ultra', 'Model/effort mismatch')
        require(source.get('prompt_sha256') == identity['prompt_sha256'], 'Meta prompt mismatch')
    require(meta.get('first_origin') is None and meta.get('gate_sha256') is None, 'P0 origin contaminated')
    require(meta['started_utc'] == marker['started_utc'], 'Attempt start timestamp conflict')
    require(freeze_time <= timestamp(record['started_utc']) <= timestamp(marker['started_utc']) <= timestamp(meta['finished_utc']) <= timestamp(record['finished_utc']), 'Attempt chronology')
    require(type(meta['seconds']) in (float, int) and math.isfinite(meta['seconds']) and meta['seconds'] >= 0, 'Invalid duration')
    for filename, field in [('attempt_started.json', 'started_sha256'), ('events.jsonl', 'stdout_sha256'), ('stderr.txt', 'stderr_sha256'), ('response.json', 'output_sha256')]:
        require(file_hash(ad / filename) == meta.get(field), 'Raw hash mismatch: ' + filename)
    response = (ad / 'response.json').read_text(); events = parse_events((ad / 'events.jsonl').read_text()); stderr = (ad / 'stderr.txt').read_text()
    require(record.get('raw_final') == response and record.get('final_sha256') == digest(response), 'Saved final differs from raw')
    require(meta.get('completed_agent_messages') == events['messages'], 'Saved event final differs from raw events')
    require(meta.get('error_items') == events['error_items'] and meta.get('top_level_errors') == events['top_errors'], 'Saved errors differ from events')
    require(meta.get('thread_ids') == events['sessions'] and meta.get('lifecycle_events') == events['lifecycle'], 'Saved lifecycle differs from events')
    require(meta.get('event_count') == len(events['events']) and meta.get('turn_completion_usages') == events['usages'], 'Saved event count/usage differs')
    require(meta.get('turn_completed') == bool(events['usages']), 'Saved turn completion differs')
    require(meta.get('usage') == (events['usages'][0] if len(events['usages']) == 1 else None), 'Saved usage differs from events')
    require(meta.get('unexpected_items') == [] and not events['unusual'], 'Unexpected tool/event content')
    require(meta.get('lifecycle_errors') == [] and events['lifecycle'] == LIFECYCLE and len(events['sessions']) == 1, 'Invalid original lifecycle')
    # This frozen run has one final and error items in each task. The original
    # all-error-item failure rule remains binding; we never overwrite that result.
    require(events['error_items'] and record.get('status') == 'technical_failure' and record.get('parsed') is None, 'Original strict classification unexpectedly differs')
    result = classify_observed(meta, events, response, stderr, schema)
    return {**job, 'family_id': item['family_id'], 'error_type': item['error_type'], 'state': item['state'], 'advice': item['advice'],
            'original_status': 'technical_failure', 'original_correct': 0,
            'derived_status': 'accepted_exact_diagnostics' if result['accepted'] else 'rejected',
            'rejection_reasons': result['rejection_reasons'], 'parsed': result['parsed'],
            'record_sha256': file_hash(folder / 'record.json'), 'final_sha256': digest(response),
            'session_id': events['sessions'][0], 'attempts': 1, 'seconds': meta['seconds'],
            'usage': events['usages'][0] if events['usages'] and isinstance(events['usages'][0], dict) else {},
            'stderr_sha256': file_hash(ad / 'stderr.txt'), 'stderr_warn_present': bool(stderr.strip())}


def threshold_diagnostic(rows, accepted_all):
    kinds = {}
    for kind in ['material', 'rule']:
        selected = [r for r in rows if r['error_type'] == kind]
        flawed = [r for r in selected if r['state'] != 'missing' and r['advice'] == 'flawed']
        aligned = [r for r in selected if r['state'] != 'missing' and r['advice'] == 'aligned']
        missing = [r for r in selected if r['state'] == 'missing']
        # Only accepted wrong finals are natural errors; rejected tasks remain in
        # planned denominators and force the whole threshold diagnostic to block.
        errors = [r for r in flawed if r['derived_status'] == 'accepted_exact_diagnostics' and not r['derived_correct']]
        observed = {'present_flawed_n': len(flawed), 'natural_errors': len(errors),
                    'error_families': sorted({r['family_id'] for r in errors}),
                    'present_aligned_n': len(aligned), 'present_aligned_correct': sum(r['derived_correct'] for r in aligned),
                    'missing_n': len(missing), 'missing_correct': sum(r['derived_correct'] for r in missing)}
        kinds[kind] = {'observed': observed,
                       'natural_error_window': 4 <= len(errors) <= 8,
                       'error_family_coverage': len(observed['error_families']) >= 3,
                       'aligned_accuracy_floor': observed['present_aligned_correct'] >= 12,
                       'missing_accuracy_floor': observed['missing_correct'] >= 6,
                       'expected_denominators': (len(flawed), len(aligned), len(missing)) == (16, 16, 8)}
    passes = accepted_all and all(all(v for k, v in d.items() if k != 'observed') for d in kinds.values())
    return {'analysis_label': LABEL, 'NOT_A_RUN_GATE': True, 'automatic_execution_authorized': False,
            'original_frozen_status': 'technical_block', 'original_challenge_allowed': False,
            'derived_transport_accepted_all_80': accepted_all,
            'hypothetical_threshold_status': 'eligible_for_independent_holdout' if passes else 'development_gate_failed' if accepted_all else 'technical_block',
            'criteria': kinds,
            'limitation': 'Post-hoc sensitivity diagnostic only. Original frozen gate remains blocked. Any added challenge requires a separately registered exploration and independent review; no P0 response may be resampled.'}


def derive(root=ROOT, check_runtime=True):
    require(file_hash(root / 'protocol/frozen.json') == FROZEN_SHA, 'Unexpected original frozen manifest')
    frozen = read(root / 'protocol/frozen.json')
    if check_runtime:
        require(root == ROOT, 'Canonical target only')
        validate_runtime(frozen)
    before = inventory(root, frozen)
    for name, expected in frozen['sha256'].items():
        require(before[name] == expected, 'Frozen input changed: ' + name)
    require(read(root / 'protocol/backend.json') == frozen['execution_config'], 'Backend/frozen execution mismatch')
    item_list = read(root / 'prompts/p0_items.json'); items = {i['item_id']: i for i in item_list}
    require(len(items) == len(item_list) == 80, 'P0 must have exactly 80 distinct items')
    jobs = [{ 'group_id': i['item_id'] + '_r1', 'item_id': i['item_id'], 'repeat': 1, 'procedure': 'P0'} for i in item_list]
    random.Random(20261108).shuffle(jobs)
    require(frozen['phase_schedule']['p0']['jobs'] == jobs, 'P0 schedule differs')
    validate_inventory(root, frozen, jobs)
    schema = read(root / 'protocol/output_schema.json'); prompts = read(root / 'protocol/prompts.json')
    rows = [validate_task(root, j, items[j['item_id']], prompts, schema, timestamp(frozen['created_utc'])) for j in jobs]
    assert_unique_sessions([r['session_id'] for r in rows])
    # All transport acceptance decisions are fixed before answer keys are opened.
    key_list = read(root / 'keys/p0_keys.json'); keys = {k['item_id']: k for k in key_list}
    require(len(keys) == len(key_list) == 80 and set(keys) == set(items), 'Key/item identity mismatch')
    for row in rows:
        key = keys[row['item_id']]; item = items[row['item_id']]
        require(all(key.get(k) == item.get(k) for k in ['family_id', 'error_type', 'state', 'advice']), 'Key metadata mismatch')
        require(key['public_sha256'] == digest(item['public_text']) and key['correct_action'] in ['A', 'B', 'C', 'D'], 'Key public hash/action mismatch')
        row['correct_action'] = key['correct_action']; row['action'] = row['parsed']['action'] if row['parsed'] else None
        row['derived_correct'] = int(row['derived_status'] == 'accepted_exact_diagnostics' and row['action'] == key['correct_action'])
        row['analysis_label'] = LABEL
    accepted = sum(r['derived_status'] == 'accepted_exact_diagnostics' for r in rows)
    diagnostic = threshold_diagnostic(rows, accepted == 80)
    original_gate = root / 'analysis/decision_gate.json'
    if original_gate.exists():
        gate = read(original_gate)
        require(gate.get('status') == 'technical_block' and gate.get('challenge_allowed') is False, 'Original gate is inconsistent with strict 80 failures')
    family_rows = []
    for family in sorted({r['family_id'] for r in rows}):
        subset = [r for r in rows if r['family_id'] == family]
        family_rows.append({'family_id': family, 'error_type': subset[0]['error_type'], 'planned': len(subset),
                            'accepted': sum(r['derived_status'] == 'accepted_exact_diagnostics' for r in subset),
                            'correct': sum(r['derived_correct'] for r in subset), 'accuracy': sum(r['derived_correct'] for r in subset) / len(subset)})
    summary = {'analysis_label': LABEL, 'original_frozen_sha256': FROZEN_SHA,
               'planned_p0': 80, 'terminal_p0': len(rows), 'actual_cli_attempts': sum(r['attempts'] for r in rows),
               'original_status_counts': dict(Counter(r['original_status'] for r in rows)),
               'original_complete': 0, 'original_gate_status': 'technical_block', 'original_challenge_allowed': False,
               'original_gate_file_exists': original_gate.exists(), 'original_failure_policy_correct': 0,
               'original_failure_policy_accuracy': 0.0,
               'original_accuracy_interpretation': 'Execution-policy failures; not evidence that 80 model decisions were substantively incorrect.',
               'derived_transport_accepted': accepted, 'derived_correct': sum(r['derived_correct'] for r in rows),
               'derived_accuracy_planned_denominator': sum(r['derived_correct'] for r in rows) / 80,
               'unique_sessions': len({r['session_id'] for r in rows}), 'family_results': family_rows,
               'resources': usage_summary([r['usage'] for r in rows]), 'total_seconds_sum_over_concurrent_calls': sum(r['seconds'] for r in rows),
               'verified_billed_cost': None, 'inference': 'Constructed development families, 4/type. Descriptive only; no p-values, humans, external experts, or heldout claims.',
               'challenge_invoked': False, 'new_model_calls_by_this_script': 0}
    require(inventory(root, frozen) == before, 'Original input changed during read-only derivation')
    return {'summary': summary, 'rows': rows, 'threshold_diagnostic': diagnostic, 'input_sha256': before,
            'policy': {'analysis_label': LABEL, 'diagnostic_allowlist': EXPECTED_ERRORS, 'required_event_pattern': PATTERN,
                       'stderr_policy': 'Retain and hash all stderr; ERROR/FATAL level words reject. Existing native-roots certificate warnings are WARN, not waived error items.',
                       'exceptions_are_posthoc': True, 'original_gate_overridden': False}}


@contextmanager
def quiescent_original_runs(root=ROOT):
    """Acquire the existing lock read-only: never truncate or rewrite its contents."""
    fd = os.open(root / 'runs/.integrity.lock', os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Unsafe original lock file')
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def publish(result):
    out = HERE / 'results'
    require(HERE == ROOT / 'amendments/A1_posthoc', 'Unexpected amendment location')
    require(not out.exists() and not out.is_symlink(), 'Refusing to overwrite existing posthoc output')
    out.mkdir()
    for name, value in [('summary.json', result['summary']), ('threshold_diagnostic.json', result['threshold_diagnostic']),
                        ('input_sha256.json', result['input_sha256']), ('policy.json', result['policy']), ('rows.json', result['rows'])]:
        with (out / name).open('x') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')
    columns = ['item_id', 'group_id', 'family_id', 'error_type', 'state', 'advice', 'original_status', 'original_correct',
               'derived_status', 'action', 'correct_action', 'derived_correct', 'record_sha256', 'final_sha256', 'session_id', 'analysis_label']
    with (out / 'item_scores.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore'); writer.writeheader(); writer.writerows(result['rows'])
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'analysis_label': LABEL,
                'target_host': socket.gethostname(), 'target_root': str(ROOT), 'script_sha256': file_hash(Path(__file__)),
                'original_frozen_sha256': FROZEN_SHA, 'outputs_sha256': {p.name: file_hash(p) for p in sorted(out.iterdir())},
                'original_inputs_unchanged': True, 'original_gate_overridden': False, 'new_model_calls': 0}
    with (out / 'manifest.json').open('x') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2); stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--write-results', action='store_true'); args = parser.parse_args()
    with quiescent_original_runs():
        result = derive()
        if args.write_results:
            publish(result)
            require(inventory(ROOT, read(ROOT / 'protocol/frozen.json')) == result['input_sha256'], 'Original inputs changed while publishing')
    print(json.dumps({'summary': result['summary'], 'threshold_diagnostic': result['threshold_diagnostic']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
