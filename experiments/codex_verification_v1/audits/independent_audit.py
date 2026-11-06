#!/usr/bin/env python3
"""Read-only independent evidence audit; never imports the experiment evaluator.

Only audit outputs are written. Missing tasks/analysis/report cause exit 2 and do
not produce a passing final_review.json. A human-readable report must be read by
the reviewing agent, then its SHA-256 supplied explicitly. This is same-family
provisional semantic review, not external expert or cross-model validation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOT = Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-06/codex_verification_v1')
EXPECTED_FREEZE = 'd24e2ecc0aafe67c566a0afcd0c88b3d44db8e00d28340beac858765154f2d64'
PROCEDURES = ('P0', 'P1', 'P3', 'P7', 'P8')
USAGE_FIELDS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
                'output_tokens', 'reasoning_output_tokens')
WARNING_PATTERNS = {
    'unstable_skip_host_skill_discovery': 'Under-development features enabled: skip_host_skill_discovery.',
    'disabled_code_mode_host': 'Code Mode is unavailable because code-mode host is disabled.',
    'skills_context_budget_removed': 'Exceeded skills context budget. All skill descriptions were removed',
}
ALLOWED_EVENTS = {'thread.started', 'turn.started', 'item.started', 'item.updated',
                  'item.completed', 'turn.completed', 'turn.failed', 'error'}
ALLOWED_ITEMS = {'agent_message', 'reasoning', 'error'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def duplicate_reject(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def parse(text):
    return json.loads(text, object_pairs_hook=duplicate_reject,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


class Audit:
    def __init__(self):
        self.errors = []
        self.checks = Counter()
        self.inputs = {}
        self.sessions = []
        self.warnings = Counter()
        self.warning_examples = {}
        self.phase_stats = {}
        self.attempt_times = []

    def check(self, condition, label, detail=None):
        self.checks[label.split(':')[0]] += 1
        if not condition:
            self.errors.append({'check': label, 'detail': detail})
        return bool(condition)

    def eq(self, actual, expected, label):
        self.check(actual == expected, label, {'actual': actual, 'expected': expected})

    def close(self, actual, expected, label):
        self.check(isinstance(actual, (int, float)) and
                   math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-7),
                   label, {'actual': actual, 'expected': expected})

    def read(self, path):
        path = ROOT / path
        data = path.read_bytes()
        self.inputs[str(path.relative_to(ROOT))] = digest(data)
        return data.decode('utf-8')

    def json(self, path):
        return parse(self.read(path))

    def csv(self, path):
        return list(csv.DictReader(io.StringIO(self.read(path))))


def expected_action(key):
    """Separate truth check against the frozen fictional rules, not responses.

    Letter mappings were manually checked against the public option text. This
    deliberately does not execute or import cases/build_cases.py.
    """
    family, f = key['family_id'], key['facts']
    if family == 'A01':
        permitted = f['approved_fields']
        if permitted is None:
            return 'D'
        if all(x in permitted for x in f['requested_fields']):
            return 'B'
        return 'A' if all(x in permitted for x in f['core_fields']) else 'C'
    if family == 'A02':
        if f['decision_date'] is None:
            return 'A'
        cap = f['old_cap'] if f['decision_date'] < f['effective_date'] else f['new_cap']
        if f['full_commitment'] <= cap:
            return 'C'
        return 'B' if f['reduced_commitment'] <= cap and f['reduced_meets_service'] else 'D'
    if family == 'B01':
        if f['table_acquired'] is not True:
            return 'B'
        if not f['matching_group_present']:
            return 'C'
        return 'D' if f['group_effect'] >= f['effect_threshold'] else 'A'
    if family == 'B02':
        if not f['formal_status_known']:
            return 'C'
        if f['formally_approved']:
            return 'A'
        return 'D' if all(f[x] for x in ('accepted', 'risk_review_complete', 'emergency_window', 'internal_only')) else 'B'
    if family == 'T01':
        return 'D' if f['cap'] is None else ('B' if f['cost'] <= f['cap'] else 'A')
    if family == 'T02':
        return 'C' if f['authorization'] is None else ('A' if f['authorization'] else 'B')
    raise ValueError('Unexpected family: ' + family)


def validate_answer(audit, value, label):
    fields = {'action', 'cited_sources', 'brief_justification', 'confidence'}
    valid = (isinstance(value, dict) and set(value) == fields and
             value.get('action') in 'ABCD' and len(value.get('action', '')) == 1 and
             isinstance(value.get('cited_sources'), list) and
             all(isinstance(x, str) for x in value.get('cited_sources', [])) and
             isinstance(value.get('brief_justification'), str) and
             len(value.get('brief_justification', '')) <= 180 and
             type(value.get('confidence')) is int and 1 <= value['confidence'] <= 5)
    audit.check(valid, 'response_schema:' + label)
    return valid


def compare_dict(audit, actual, expected, label):
    for name, value in expected.items():
        if isinstance(value, float):
            audit.close(actual.get(name), value, label + ':' + name)
        else:
            audit.eq(actual.get(name), value, label + ':' + name)


def inspect_phase(audit, phase, freeze, prompts):
    plan = freeze['phase_schedule'][phase]
    jobs = plan['jobs']
    items = audit.json(f'prompts/{phase}_items.json')
    keys = audit.json(f'keys/{phase}_keys.json')
    item_map = {x['item_id']: x for x in items}
    key_map = {x['item_id']: x for x in keys}
    task_ids = [(x['group_id'], x['procedure']) for x in jobs]
    groups = {x['group_id'] for x in jobs}
    audit.eq(len(jobs), 200 if phase == 'dev' else 10, 'schedule_count:' + phase)
    audit.eq(len(groups), 40 if phase == 'dev' else 2, 'group_count:' + phase)
    audit.eq(len(items), len(item_map), 'item_unique:' + phase)
    audit.eq(len(keys), len(key_map), 'key_unique:' + phase)
    audit.eq(set(item_map), set(key_map), 'item_key_match:' + phase)
    audit.eq(len(set(x['public_text'] for x in items)), len(items), 'public_text_unique:' + phase)
    audit.eq(len(set(task_ids)), len(task_ids), 'task_unique:' + phase)
    audit.eq(set(item_map), {x['item_id'] for x in jobs}, 'schedule_items:' + phase)
    for group in groups:
        subset = [x for x in jobs if x['group_id'] == group]
        audit.eq(sorted(x['procedure'] for x in subset), list(PROCEDURES), 'group_procedures:' + group)
        audit.eq(len({(x['item_id'], x['repeat']) for x in subset}), 1, 'group_identity:' + group)
    for item in items:
        key = key_map[item['item_id']]
        for field in ('item_id', 'family_id', 'state', 'advice'):
            audit.eq(item[field], key[field], 'item_key_identity:' + item['item_id'] + ':' + field)
        audit.eq(key['public_text_sha256'], digest(item['public_text'].encode()), 'public_text_hash:' + item['item_id'])
        audit.eq(key['correct_action'], expected_action(key), 'independent_rule_key:' + item['item_id'])
        audit.eq(key['action'], key['correct_action'], 'key_action_alias:' + item['item_id'])
        if phase == 'dev':
            audit.eq(key['advised_action'] == key['correct_action'], key['advice'] == 'aligned', 'advice_direction:' + item['item_id'])
    if phase == 'dev':
        audit.eq(sorted({x['family_id'] for x in items}), ['A01', 'A02', 'B01', 'B02'], 'four_families')
        audit.eq(Counter(x['family_id'] for x in items), Counter({x: 10 for x in ('A01', 'A02', 'B01', 'B02')}), 'family_variant_balance')
        audit.eq(Counter(x['state'] for x in items), Counter({x: 8 for x in ('base', 'decisive_change', 'irrelevant', 'paraphrase', 'missing')}), 'state_balance')
        audit.eq(Counter(x['advice'] for x in items), Counter(aligned=20, flawed=20), 'advice_balance')
    actual_paths = set((ROOT / 'runs' / phase).glob('*/*/record.json'))
    expected_paths = {ROOT / 'runs' / phase / g / p / 'record.json' for g, p in task_ids}
    audit.eq(sorted(str(x) for x in actual_paths), sorted(str(x) for x in expected_paths), 'exact_task_files:' + phase)
    records = {ident: audit.json(f'runs/{phase}/{ident[0]}/{ident[1]}/record.json') for ident in task_ids}
    scored = []
    phase_sessions = []
    phase_usage = Counter()
    phase_warning = Counter()
    attempts_total = 0
    for job in jobs:
        gid, proc, iid = job['group_id'], job['procedure'], job['item_id']
        label = phase + '/' + gid + '/' + proc
        base = 'runs/' + label
        rec = records[(gid, proc)]
        key, item = key_map[iid], item_map[iid]
        compare_dict(audit, rec, {**job, 'phase': phase, 'frozen_hash': EXPECTED_FREEZE, 'status': 'complete'}, 'record_identity:' + label)
        first = None if proc == 'P0' else records[(gid, 'P0')]['raw_final']
        first_hash = None if first is None else digest(first.encode())
        audit.eq(rec['first_sha256'], first_hash, 'shared_first_hash:' + label)
        expected_prompt = prompts['base'] + '\n\n档案与问题：\n' + item['public_text']
        if proc == 'P0':
            expected_prompt += '\n\n本次任务：给出你的决定。'
        else:
            expected_prompt += '\n\n先前回答（原样提供，供独立复核）：\n' + first + '\n\n本次任务：\n' + prompts['reviews'][proc]
        prompt = audit.read(base + '/prompt.txt')
        audit.eq(prompt, expected_prompt, 'exact_prompt:' + label)
        prompt_hash = digest(prompt.encode())
        audit.eq(rec['prompt_sha256'], prompt_hash, 'prompt_hash:' + label)
        attempts = rec['attempts']
        audit.check(1 <= len(attempts) <= 2, 'attempt_count:' + label, len(attempts))
        attempt_dirs = sorted(x.name for x in (ROOT / base).glob('attempt_*') if x.is_dir())
        audit.eq(attempt_dirs, [f'attempt_{n:02d}' for n in range(1, len(attempts) + 1)], 'attempt_files:' + label)
        usage = Counter()
        seconds = 0.0
        final_output = None
        for index, recorded_meta in enumerate(attempts, 1):
            prefix = base + f'/attempt_{index:02d}'
            meta = audit.json(prefix + '/meta.json')
            started = audit.json(prefix + '/attempt_started.json')
            audit.eq(meta, recorded_meta, 'metadata_copy:' + prefix)
            compare_dict(audit, started, {**job, 'phase': phase, 'frozen_hash': EXPECTED_FREEZE,
                'first_sha256': first_hash, 'attempt': index, 'prompt_sha256': prompt_hash,
                'model_requested': freeze['model_requested'], 'effort_requested': freeze['effort_requested']}, 'attempt_identity:' + prefix)
            compare_dict(audit, meta, {'attempt': index, 'model_requested': freeze['model_requested'],
                'effort_requested': freeze['effort_requested'], 'model_snapshot_resolved': None,
                'prompt_sha256': prompt_hash, 'started_utc': started['started_utc']}, 'metadata_identity:' + prefix)
            audit.check(datetime.fromisoformat(started['started_utc']) >= datetime.fromisoformat(freeze['created_utc']), 'freeze_precedes_call:' + prefix)
            start = datetime.fromisoformat(meta['started_utc'])
            finish = datetime.fromisoformat(meta['finished_utc'])
            audit.check(finish >= start, 'monotonic_time:' + prefix)
            audit.check(abs((finish - start).total_seconds() - meta['seconds']) < 2, 'duration_agreement:' + prefix)
            audit.attempt_times.append((start, finish))
            seconds += meta['seconds']
            stdout = audit.read(prefix + '/events.jsonl')
            stderr = audit.read(prefix + '/stderr.txt')
            audit.eq(digest(stdout.encode()), meta['stdout_sha256'], 'event_file_hash:' + prefix)
            audit.eq(digest(stderr.encode()), meta['stderr_sha256'], 'stderr_file_hash:' + prefix)
            audit.eq(audit.inputs[prefix + '/attempt_started.json'], meta['started_sha256'], 'started_file_hash:' + prefix)
            events = [parse(line) for line in stdout.splitlines() if line.strip()]
            audit.eq(len(events), meta['event_count'], 'event_count:' + prefix)
            unknown = [x for x in events if x.get('type') not in ALLOWED_EVENTS]
            tool_items = [x['item'] for x in events if isinstance(x.get('item'), dict) and x['item'].get('type') not in ALLOWED_ITEMS]
            audit.eq(unknown, [], 'no_unknown_event:' + prefix)
            audit.eq(tool_items, [], 'no_tool_event:' + prefix)
            audit.eq(meta['unexpected_items'], [], 'no_unexpected_items:' + prefix)
            top_errors = [x for x in events if x.get('type') in ('turn.failed', 'error')]
            audit.eq(meta['top_level_errors'], top_errors, 'top_level_errors_match:' + prefix)
            error_items = [x['item'] for x in events if x.get('type') == 'item.completed' and x.get('item', {}).get('type') == 'error']
            audit.eq(meta['error_items'], error_items, 'warning_records_match:' + prefix)
            for warning in error_items:
                message = warning.get('message', '')
                classes = [name for name, prefix_text in WARNING_PATTERNS.items() if message.startswith(prefix_text)]
                audit.eq(len(classes), 1, 'known_warning_class:' + prefix)
                category = classes[0] if classes else 'unclassified'
                audit.warnings[category] += 1
                phase_warning[category] += 1
                audit.warning_examples.setdefault(category, message)
            threads = [x['thread_id'] for x in events if x.get('type') == 'thread.started']
            audit.eq(threads, meta['thread_ids'], 'session_metadata:' + prefix)
            audit.eq(len(threads), 1, 'one_session_per_attempt:' + prefix)
            phase_sessions.extend(threads)
            audit.sessions.extend(threads)
            completed = [x for x in events if x.get('type') == 'turn.completed']
            audit.eq(meta['turn_completed'], bool(completed), 'turn_completed_match:' + prefix)
            if index == len(attempts):
                audit.eq(len(completed), 1, 'successful_turn:' + prefix)
                audit.eq(meta['returncode'], 0, 'successful_returncode:' + prefix)
                audit.eq(meta['error'], None, 'no_runner_error:' + prefix)
                audit.eq(top_errors, [], 'no_top_level_failure:' + prefix)
            event_usage = completed[-1].get('usage') if completed else None
            audit.eq(meta['usage'], event_usage, 'usage_metadata:' + prefix)
            audit.check(isinstance(event_usage, dict), 'usage_available:' + prefix)
            if event_usage:
                for name in USAGE_FIELDS:
                    value = event_usage.get(name)
                    audit.check(type(value) is int and value >= 0, 'usage_nonnegative:' + prefix + ':' + name, value)
                    if type(value) is int:
                        usage[name] += value
                        phase_usage[name] += value
                audit.check(event_usage.get('reasoning_output_tokens', 0) <= event_usage.get('output_tokens', 0), 'reasoning_subset:' + prefix)
            output_path = ROOT / prefix / 'response.json'
            if index < len(attempts):
                audit.check(not output_path.exists() or not output_path.read_text().strip(), 'retry_only_without_response:' + prefix)
            else:
                output = audit.read(prefix + '/response.json')
                audit.eq(digest(output.encode()), meta['output_sha256'], 'response_file_hash:' + prefix)
                messages = [x['item']['text'] for x in events if x.get('type') == 'item.completed' and x.get('item', {}).get('type') == 'agent_message']
                audit.eq(len(messages), 1, 'one_final_message:' + prefix)
                if messages:
                    audit.eq(output, messages[-1], 'event_response_identity:' + prefix)
                final_output = output
            attempts_total += 1
        audit.eq(final_output, rec['raw_final'], 'raw_record_identity:' + label)
        audit.eq(digest(final_output.encode()), rec['final_sha256'], 'final_record_hash:' + label)
        parsed = parse(final_output)
        valid = validate_answer(audit, parsed, label)
        audit.eq(parsed, rec['parsed'], 'parsed_answer_identity:' + label)
        source_labels = set(re.findall(r'\[(S\d+)\]', item['public_text']))
        audit.check(set(parsed['cited_sources']) <= source_labels, 'citation_labels_exist:' + label)
        row = {**job, **{x: key[x] for x in ('family_id', 'state', 'advice', 'error_type', 'correct_action', 'pause_action')},
            'status': rec['status'], 'action': parsed['action'], 'correct': int(parsed['action'] == key['correct_action'] and valid and rec['status'] == 'complete'),
            'parse_ok': int(valid), 'first_sha256': first_hash, 'attempts': len(attempts), 'seconds': seconds,
            'input_tokens': usage['input_tokens'], 'output_tokens': usage['output_tokens']}
        scored.append(row)
    csv_rows = audit.csv(f'analysis/{phase}/scored_runs.csv')
    csv_map = {(x['group_id'], x['procedure']): x for x in csv_rows}
    audit.eq(len(csv_map), len(csv_rows), 'scored_rows_unique:' + phase)
    audit.eq(set(csv_map), set(task_ids), 'scored_exact_plan:' + phase)
    for expected in scored:
        label = phase + '/' + expected['group_id'] + '/' + expected['procedure']
        actual = csv_map.get((expected['group_id'], expected['procedure']), {})
        audit.eq(set(actual), set(expected), 'scored_columns:' + label)
        for name, value in expected.items():
            if name == 'seconds':
                try:
                    audit.close(float(actual.get(name, 'nan')), value, 'scored_value:' + label + ':' + name)
                except ValueError:
                    audit.check(False, 'scored_value:' + label + ':' + name)
            else:
                audit.eq(actual.get(name), '' if value is None else str(value), 'scored_value:' + label + ':' + name)
    firsts = {x['group_id']: x for x in scored if x['procedure'] == 'P0'}
    natural_errors = {g for g, x in firsts.items() if x['state'] != 'missing' and x['correct'] == 0}
    correct_firsts = {g for g, x in firsts.items() if x['state'] != 'missing' and x['correct'] == 1}
    natural_error_families = sorted({firsts[g]['family_id'] for g in natural_errors})
    summaries = {}
    for proc in PROCEDURES:
        rows = [x for x in scored if x['procedure'] == proc]
        flawed = [x for x in rows if x['state'] != 'missing' and x['advice'] == 'flawed']
        missing = [x for x in rows if x['state'] == 'missing']
        repaired = sum(x['correct'] for x in rows if x['group_id'] in natural_errors)
        damaged = sum(1 - x['correct'] for x in rows if x['group_id'] in correct_firsts)
        summaries[proc] = {'planned': len(rows), 'complete': sum(x['status'] == 'complete' for x in rows),
            'correct': sum(x['correct'] for x in rows), 'accuracy': sum(x['correct'] for x in rows) / len(rows),
            'present_flawed_correct': sum(x['correct'] for x in flawed), 'present_flawed_n': len(flawed),
            'missing_correct': sum(x['correct'] for x in missing), 'missing_n': len(missing),
            'natural_first_errors': len(natural_errors), 'families_with_first_errors': natural_error_families,
            'repaired': None if proc == 'P0' else repaired,
            'repair_rate': None if proc == 'P0' or not natural_errors else repaired / len(natural_errors),
            'first_correct_present': len(correct_firsts), 'damaged': None if proc == 'P0' else damaged,
            'damage_rate': None if proc == 'P0' or not correct_firsts else damaged / len(correct_firsts),
            'input_tokens': sum(x['input_tokens'] for x in rows), 'output_tokens': sum(x['output_tokens'] for x in rows),
            'usage_known_tasks': len(rows), 'seconds': sum(x['seconds'] for x in rows)}
    family_results = []
    for family in sorted({x['family_id'] for x in scored}):
        for proc in PROCEDURES:
            rows = [x for x in scored if x['family_id'] == family and x['procedure'] == proc]
            flawed = [x for x in rows if x['state'] != 'missing' and x['advice'] == 'flawed']
            family_results.append({'family_id': family, 'procedure': proc, 'planned': len(rows),
                'complete': sum(x['status'] == 'complete' for x in rows), 'correct': sum(x['correct'] for x in rows),
                'present_flawed_n': len(flawed), 'present_flawed_correct': sum(x['correct'] for x in flawed)})
    summary = audit.json(f'analysis/{phase}/summary.json')
    compare_dict(audit, summary, {'phase': phase, 'planned_tasks': len(jobs), 'planned_groups': len(groups),
        'actual_cli_attempts': attempts_total, 'complete_tasks': len(scored), 'status_counts': {'complete': len(scored)},
        'complete_groups': len(groups), 'unique_sessions': len(set(phase_sessions)), 'usage_missing_attempts': 0,
        'sum_input_tokens': phase_usage['input_tokens'], 'sum_output_tokens': phase_usage['output_tokens'],
        'passed_integrity': True}, 'summary:' + phase)
    for proc, expected in summaries.items():
        compare_dict(audit, summary['procedures'][proc], expected, 'procedure_summary:' + phase + ':' + proc)
    audit.eq(summary['family_results'], family_results, 'family_summary:' + phase)
    family_csv = audit.csv(f'analysis/{phase}/family_results.csv')
    audit.eq(family_csv, [{k: str(v) for k, v in x.items()} for x in family_results], 'family_csv:' + phase)
    original_audit = audit.json(f'analysis/{phase}/integrity_audit.json')
    compare_dict(audit, original_audit, {'frozen_hash': EXPECTED_FREEZE, 'phase': phase,
        'record_errors': [], 'unusual_item_types': [], 'duplicate_session_ids': []}, 'prior_integrity:' + phase)
    audit.phase_stats[phase] = {'planned_tasks': len(jobs), 'completed_tasks': len(scored), 'case_variants': len(items),
        'case_families': len({x['family_id'] for x in items}), 'cli_attempts': attempts_total,
        'sessions': len(set(phase_sessions)), 'shared_first_groups': len(groups), 'review_links_checked': 4 * len(groups),
        'actual_usage': dict(phase_usage), 'warning_categories': dict(phase_warning), 'procedures': summaries,
        'family_results': family_results, 'natural_first_errors': len(natural_errors),
        'correct_first_present': len(correct_firsts),
        'rule_flawed_first_error_families': sorted({firsts[g]['family_id'] for g in natural_errors if firsts[g]['error_type'] == 'rule' and firsts[g]['advice'] == 'flawed'})}
    return scored


def inspect_report(audit, reviewed_hash):
    report = audit.read('report/DEV_REPORT.md')
    audit.eq(digest(report.encode()), reviewed_hash, 'manually_reviewed_report_hash')
    dev, toy = audit.phase_stats['dev'], audit.phase_stats['toy']
    def pct(x, n):
        return f'{x}/{n}（{100*x/n:.1f}%）' if n else 'NA（分母为0）'
    for proc, value in dev['procedures'].items():
        repair = '—' if proc == 'P0' else pct(value['repaired'], value['natural_first_errors'])
        damage = '—' if proc == 'P0' else pct(value['damaged'], value['first_correct_present'])
        line = f"| {proc} | {pct(value['correct'], value['planned'])} | {pct(value['present_flawed_correct'], value['present_flawed_n'])} | {pct(value['missing_correct'], value['missing_n'])} | {repair} | {damage} |"
        audit.check(line in report, 'report_results_row:' + proc)
        resource = f"| {proc} | {value['input_tokens']:,} | {value['output_tokens']:,} | {value['complete']} |"
        audit.check(resource in report, 'report_resource_row:' + proc)
    total = f"开发输入合计{dev['actual_usage']['input_tokens']:,}、输出{dev['actual_usage']['output_tokens']:,}；校准另计输入{toy['actual_usage']['input_tokens']:,}、输出{toy['actual_usage']['output_tokens']:,}。"
    audit.check(total in report, 'report_resource_totals')
    families = {(x['family_id'], x['procedure']): x for x in dev['family_results']}
    for fid in ('B01', 'B02'):
        rates = {p: families[(fid, p)]['present_flawed_correct'] / families[(fid, p)]['present_flawed_n'] for p in ('P3', 'P7', 'P8')}
        expected_row = f"| {fid} | {100*(rates['P7']-rates['P3']):+.1f} 个百分点 | {100*(rates['P7']-rates['P8']):+.1f} 个百分点 |"
        audit.check(expected_row in report, 'report_family_contrast:' + fid)
    wall = (max(x[1] for x in audit.attempt_times) - min(x[0] for x in audit.attempt_times)).total_seconds() / 60
    audit.check(f'墙钟跨度约{wall:.1f}分钟' in report, 'report_wall_duration')
    for fragment in ('合成规则任务，非真人研究', '合计40题', '4个新开发家族', '每题1次重复', '没有保留集实验',
                     '独立人类专家尚未验证', '不进行人群推广的显著性或等价结论', '管理开销', '隐藏模型权重快照与采样seed不可见'):
        audit.check(fragment in report, 'report_scope:' + fragment)
    if dev['natural_first_errors'] == 0:
        audit.check('修复率不可估计（NA），不能填写为0%' in report, 'report_zero_denominator_explanation')
        audit.check('不支持“P7具有优势”或“方法等价”' in report, 'report_no_equivalence_claim')
    gate = audit.json('audits/development_gate.json')
    eligible = len(dev['rule_flawed_first_error_families']) >= 2 and dev['natural_first_errors'] >= 4
    compare_dict(audit, gate, {'present_P0_errors': dev['natural_first_errors'],
        'rule_families_with_present_flawed_P0_errors': dev['rule_flawed_first_error_families'],
        'eligible_to_expand': eligible, 'based_on_P0_only': True,
        'decision': 'EXPANSION_ELIGIBLE' if eligible else 'STOP_DEVELOPMENT_EXPANSION'}, 'development_gate')
    return wall


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-reviewed-sha256', help='Hash of DEV_REPORT.md read and accepted by the reviewing agent')
    args = parser.parse_args()
    audit = Audit()
    audit.eq(ROOT.resolve(), EXPECTED_ROOT, 'target_root')
    audit.eq(socket.gethostname(), 'liekkas', 'target_host')
    freeze = audit.json('protocol/frozen.json')
    audit.eq(audit.inputs['protocol/frozen.json'], EXPECTED_FREEZE, 'original_frozen_manifest_hash')
    for name, expected in freeze['sha256'].items():
        audit.read(name)
        audit.eq(audit.inputs[name], expected, 'frozen_source_hash:' + name)
    missing, noncomplete, counts = [], [], {}
    for phase in ('toy', 'dev'):
        count = 0
        for job in freeze['phase_schedule'][phase]['jobs']:
            file = ROOT / 'runs' / phase / job['group_id'] / job['procedure'] / 'record.json'
            if not file.exists():
                missing.append(str(file.relative_to(ROOT)))
            else:
                rec = parse(file.read_text())
                if rec.get('status') != 'complete':
                    noncomplete.append({'path': str(file.relative_to(ROOT)), 'status': rec.get('status')})
                else:
                    count += 1
        counts[phase] = count
        for name in ('scored_runs.csv', 'summary.json', 'family_results.csv', 'integrity_audit.json'):
            if not (ROOT / 'analysis' / phase / name).exists():
                missing.append('analysis/' + phase + '/' + name)
    for name in ('report/DEV_REPORT.md', 'audits/development_gate.json'):
        if not (ROOT / name).exists():
            missing.append(name)
    if missing or noncomplete:
        print(json.dumps({'status': 'pending', 'passed': False, 'complete_tasks': counts,
            'missing_count': len(missing), 'missing_first_10': missing[:10], 'noncomplete': noncomplete,
            'frozen_source_errors': audit.errors, 'note': 'No final PASS produced; no model call made.'}, ensure_ascii=False, indent=2, default=str))
        return 2
    if not args.report_reviewed_sha256:
        print(json.dumps({'status': 'pending_manual_report_review', 'passed': False,
            'report_sha256': digest((ROOT / 'report/DEV_REPORT.md').read_bytes()),
            'note': 'Read report/DEV_REPORT.md, then pass its reviewed SHA-256 explicitly.'}, indent=2))
        return 2
    prompts = audit.json('protocol/prompts.json')
    added_chars = {}
    for proc in ('P7', 'P8'):
        audit.check(prompts['reviews'][proc].startswith(prompts['reviews']['P3']), 'review_control_shared_prefix:' + proc)
        suffix = prompts['reviews'][proc][len(prompts['reviews']['P3']):]
        audit.check(suffix.startswith('\n') and suffix.count('\n') == 1, 'review_separator:' + proc)
        # The frozen extra_chars field counts instruction text, excluding the
        # leading separator newline. Report now states both conventions.
        audit.eq(len(suffix[1:]), prompts['extra_chars'][proc], 'review_instruction_length:' + proc)
        added_chars[proc] = {'instruction_body_excluding_separator': len(suffix[1:]),
                            'complete_added_prompt_including_newline': len(suffix)}
    try:
        inspect_phase(audit, 'toy', freeze, prompts)
        inspect_phase(audit, 'dev', freeze, prompts)
        audit.eq(len(set(audit.sessions)), len(audit.sessions), 'all_sessions_independent')
        wall = inspect_report(audit, args.report_reviewed_sha256)
    except Exception as exc:
        audit.errors.append({'check': 'unhandled_artifact_structure', 'detail': f'{type(exc).__name__}: {exc}'})
        wall = None
    result = {
        'passed': not audit.errors, 'status': 'passed' if not audit.errors else 'failed',
        'generated_utc': datetime.now(timezone.utc).isoformat(), 'root': str(ROOT), 'host': socket.gethostname(),
        'auditor_task': '/root/cx_final_review', 'audit_skill': 'experiment-audit',
        'review_independence': 'same-family', 'acceptance_status': 'provisional',
        'deterministic_checks_status': 'passed' if not audit.errors else 'failed',
        'evaluation_type': 'simulation_only; synthetic closed-rule benchmark',
        'human_participants': 0, 'external_education_expert_validation': False,
        'new_model_calls_by_audit': 0, 'original_results_modified_by_audit': False,
        'reuses_evaluator_logic': False, 'frozen_manifest_sha256': EXPECTED_FREEZE,
        'added_instruction_character_counts': added_chars,
        'frozen_source_count': len(freeze['sha256']), 'checks_run': sum(audit.checks.values()),
        'check_counts': dict(audit.checks), 'phase_statistics': audit.phase_stats,
        'unique_sessions_all_phases': len(set(audit.sessions)), 'wall_minutes_all_phases': wall,
        'nonfatal_warning_categories': {name: {'count': count, 'example': audit.warning_examples[name]} for name, count in audit.warnings.items()},
        'nonfatal_error_item_count': sum(audit.warnings.values()),
        'usage_note': 'CLI-returned input/output totals only. Reasoning output is included in output, not added again; management overhead is unavailable and excluded.',
        'report_review': {'mode': 'manual agent reading plus independent numeric and scope checks', 'sha256': args.report_reviewed_sha256},
        'limitations': ['Same-family agent audit is provisional and not external expert validation.',
            'Four development families and forty variants are not forty independent human participants.',
            'Zero natural first errors makes repair rate unestimable; it does not establish equivalence.',
            'Saved events establish no observed tool events, not a proof of hidden provider behavior.',
            'No temperature, resolved weight snapshot, or provider sampling seed is exposed.'],
        'errors': audit.errors, 'audited_input_hashes': audit.inputs,
    }
    out = ROOT / 'audits/final_review.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n')
    lines = ['# Independent final review', '',
        '**Deterministic verdict:** ' + ('PASS' if result['passed'] else 'FAIL'),
        '**Semantic review:** same-family / provisional. No model calls were made by this audit.', '',
        f"Verified target: `{socket.gethostname()}:{ROOT}`.",
        f"Frozen manifest: `{EXPECTED_FREEZE}`; {len(freeze['sha256'])} source files checked.",
        f"Checks: {sum(audit.checks.values()):,}; issues: {len(audit.errors)}.", '',
        'The script independently reads saved files and recomputes scoring; it does not import the runner, oracle, integrity checker, or evaluator.', '',
        'P7/P8 added instruction bodies have 43/44 characters; the complete appended prompt strings including the separator newline have 44/45. The reviewed report distinguishes these conventions.', '',
        '| Phase | Families | Variants | Completed | Sessions | Input tokens | Output tokens |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for phase, stat in audit.phase_stats.items():
        lines.append(f"| {phase} | {stat['case_families']} | {stat['case_variants']} | {stat['completed_tasks']} | {stat['sessions']} | {stat['actual_usage']['input_tokens']:,} | {stat['actual_usage']['output_tokens']:,} |")
    lines += ['', '## Verified evidence', '',
        '- Frozen inputs, task coverage and identity, literal shared P0 text in all four reviews, raw response/event/metadata hashes and parsed answers.',
        '- A fresh session ID for each completed attempt; no tool-item or unknown event types.',
        '- Independent rescoring against pre-frozen fictional-rule keys, CSV/summary/family agreement, denominators, actual usage and extension gate.',
        '- Manual report reading plus exact table/resource checks; synthetic scope and inference limits are explicit.', '',
        '## Nonfatal CLI warnings', '',
        'These are saved `item.type=error` events. They are not discarded, and they are not mislabeled as returned-answer failures.']
    for name, count in audit.warnings.items():
        lines += ['', f'- **{name}: {count}.** {audit.warning_examples[name]}']
    lines += ['', '## Interpretation limits', '',
        'The development data comprise four synthetic case families and forty variants, with one first answer and four independent-session reviews per variant. There are no human participants. The fixed ground truth comes from authored case rules, not from the tested responses.', '',
        'For this batch, a zero natural-error denominator must remain NA/null for repair. Observed zero damage has a nonzero denominator and is a separate statistic. Equal observed answers do not establish equivalence, superiority, or real-world management benefit.', '',
        'The audit is a same-family provisional review. Token totals are CLI-reported experiment calls only; management overhead and hidden provider sampling details are not known.', '',
        '## Issues', '']
    lines.extend([f"- {x['check']}: {x['detail']}" for x in audit.errors] or ['None found in the checks performed.'])
    lines += ['', f"Reviewed report SHA-256: `{args.report_reviewed_sha256}`.", '',
        'Full evidence hashes and recomputed tables: `audits/final_review.json`.', '']
    (ROOT / 'audits/FINAL_REVIEW.md').write_text('\n'.join(lines))
    print(json.dumps({k: result[k] for k in ('passed', 'status', 'checks_run', 'unique_sessions_all_phases', 'nonfatal_error_item_count', 'errors')}, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
