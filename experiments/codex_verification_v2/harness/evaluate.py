#!/usr/bin/env python3
"""Deterministic scoring of every planned task; family-level descriptive contrasts."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, csv, json
import runner
R = runner.R


def entries(path):
    value = runner.read(path)
    if isinstance(value, list):
        return {x['item_id']: x for x in value}
    if 'items' in value:
        return {x['item_id']: x for x in value['items']}
    return value


def rate(n, d):
    return n / d if d else None


def mean(values):
    return sum(values) / len(values) if values else None


def valid_token_count(value):
    return type(value) is int and value >= 0


def usage_value(attempt, field):
    usage = attempt.get('usage')
    value = usage.get(field) if isinstance(usage, dict) else None
    return value if valid_token_count(value) else None


def usage_totals(attempts):
    inputs = [usage_value(a, 'input_tokens') for a in attempts]
    outputs = [usage_value(a, 'output_tokens') for a in attempts]
    input_missing = sum(v is None for v in inputs)
    output_missing = sum(v is None for v in outputs)
    known_input = sum(v for v in inputs if v is not None)
    known_output = sum(v for v in outputs if v is not None)
    return {'sum_input_tokens': None if input_missing else known_input,
            'sum_output_tokens': None if output_missing else known_output,
            'known_input_tokens': known_input, 'known_output_tokens': known_output,
            'input_usage_missing_attempts': input_missing, 'output_usage_missing_attempts': output_missing,
            'usage_missing_attempts': sum(i is None or o is None for i, o in zip(inputs, outputs))}


def row_usage_totals(rows):
    # Actual scored rows carry missing-attempt counts and known subtotals, so a
    # partially observed retry cannot disappear inside a row with unknown total.
    inputs = sum(r.get('input_usage_missing_attempts', int(not valid_token_count(r['input_tokens']))) for r in rows)
    outputs = sum(r.get('output_usage_missing_attempts', int(not valid_token_count(r['output_tokens']))) for r in rows)
    known_input = sum(r.get('known_input_tokens', r['input_tokens'] if valid_token_count(r['input_tokens']) else 0) for r in rows)
    known_output = sum(r.get('known_output_tokens', r['output_tokens'] if valid_token_count(r['output_tokens']) else 0) for r in rows)
    return {'sum_input_tokens': None if inputs else known_input, 'sum_output_tokens': None if outputs else known_output,
            'known_input_tokens': known_input, 'known_output_tokens': known_output,
            'input_usage_missing_attempts': inputs, 'output_usage_missing_attempts': outputs,
            'usage_missing_attempts': sum(r.get('usage_missing_attempts', int(not valid_token_count(r['input_tokens']) or not valid_token_count(r['output_tokens']))) for r in rows),
            'usage_known_tasks': sum(valid_token_count(r['input_tokens']) and valid_token_count(r['output_tokens']) for r in rows)}


def inventory_runs(frozen):
    """Account for the entire run tree before reading any planned result.

    Unknown phases/groups/procedures, extra attempts, extra raw files and
    symlinks all fail closed. Counts include unplanned artifacts as evidence.
    """
    base = R / 'runs'
    allowed = {}
    for phase, schedule in frozen['phase_schedule'].items():
        allowed[phase] = {(j['group_id'], j['procedure']) for j in schedule['jobs']}
    phase_files = {'.integrity.lock', 'plan.csv', 'manifest_identity.json', 'progress.jsonl'}
    task_files = {'prompt.txt', 'record.json'}
    raw_files = {'attempt_started.json', 'events.jsonl', 'stderr.txt', 'response.json', 'meta.json'}
    paths = sorted(base.rglob('*')) if base.exists() else []
    unplanned = []
    for path in paths:
        relative = path.relative_to(base)
        parts = relative.parts
        ok = not path.is_symlink() and parts[0] in allowed
        if ok:
            pairs = allowed[parts[0]]
            if len(parts) == 1:
                ok = path.is_dir()
            elif len(parts) == 2:
                ok = (parts[1] in phase_files and path.is_file()) or (parts[1] in {g for g, _ in pairs} and path.is_dir())
            elif len(parts) == 3:
                ok = (parts[1], parts[2]) in pairs and path.is_dir()
            elif len(parts) == 4:
                ok = (parts[1], parts[2]) in pairs and ((parts[3] in task_files and path.is_file()) or
                     (parts[3] in {'attempt_01', 'attempt_02'} and path.is_dir()))
            elif len(parts) == 5:
                ok = ((parts[1], parts[2]) in pairs and parts[3] in {'attempt_01', 'attempt_02'} and
                      parts[4] in raw_files and path.is_file())
            else:
                ok = False
        if not ok:
            unplanned.append({'path': str(Path('runs') / relative),
                              'kind': 'symlink' if path.is_symlink() else 'directory' if path.is_dir() else 'file'})
    return {'observed_paths': len(paths),
            'observed_record_files': sum(p.name == 'record.json' for p in paths),
            'observed_attempt_directories': sum(p.is_dir() and p.name.startswith('attempt_') for p in paths),
            'observed_started_attempt_files': sum(p.name == 'attempt_started.json' for p in paths),
            'observed_sealed_attempt_files': sum(p.name == 'meta.json' for p in paths),
            'unplanned_artifacts': unplanned}


def eligible(row, stratum):
    return {'present_flawed': row['state'] != 'missing' and row['advice'] == 'flawed',
            'all': True, 'aligned': row['advice'] == 'aligned',
            'missing': row['state'] == 'missing'}[stratum]


def contrast(groups, comparator, stratum='present_flawed', complete_pair=False, treatment='P7'):
    """Average within-family paired differences, then rule minus material.

    Repeats, advice versions and transformations never become independent families.
    Complete-pair sensitivity retains only groups with complete P0/P7/comparator.
    """
    by_family = defaultdict(list)
    family_type = {}
    for group in groups.values():
        baseline = group['P0']
        family_type[baseline['family_id']] = baseline['error_type']
        if not eligible(baseline, stratum):
            continue
        if complete_pair and any(group[p]['status'] != 'complete' for p in ['P0', treatment, comparator]):
            continue
        by_family[baseline['family_id']].append(group[treatment]['correct'] - group[comparator]['correct'])
    families = [{'family_id': f, 'error_type': kind, 'paired_groups': len(by_family[f]),
                 'difference': mean(by_family[f])} for f, kind in sorted(family_type.items())]
    diffs = {kind: [f['difference'] for f in families if f['error_type'] == kind and f['difference'] is not None]
             for kind in ['material', 'rule']}
    averages = {kind: mean(values) for kind, values in diffs.items()}
    estimate = None if any(v is None for v in averages.values()) else averages['rule'] - averages['material']
    return {'contrast': f'({treatment}-{comparator})_rule - ({treatment}-{comparator})_material',
            'stratum': stratum, 'complete_pair_only': complete_pair,
            'unit': 'family, equal weight within type', 'estimate': estimate,
            'type_mean_difference': averages, 'available_families_by_type': {k: len(v) for k, v in diffs.items()},
            'families': families,
            'type_family_difference_range': {k: [min(v), max(v)] if v else None for k, v in diffs.items()},
            'inference_note': 'Descriptive point estimates and family ranges only; four designed families per type. No confidence interval or confirmatory test. Ceiling does not establish equivalence.'}


def summarize(rows):
    groups = defaultdict(dict)
    for row in rows:
        groups[row['group_id']][row['procedure']] = row
    if any(set(group) != set(runner.PROCS) for group in groups.values()):
        raise ValueError('Every planned group must include all five procedures, including missing tasks')
    family_kinds = defaultdict(set)
    for row in rows:
        family_kinds[row['family_id']].add(row['error_type'])
    if any(len(types) != 1 or not types <= {'material', 'rule'} for types in family_kinds.values()):
        raise ValueError('Each family must have one known material/rule type')
    summaries = {}
    wrong = [g for g in groups.values() if g['P0']['correct'] == 0 and
             g['P0']['status'] == 'complete' and g['P0']['state'] != 'missing']
    right = [g for g in groups.values() if g['P0']['correct'] == 1 and g['P0']['state'] != 'missing']
    for procedure in runner.PROCS:
        subset = [r for r in rows if r['procedure'] == procedure]
        flawed = [r for r in subset if eligible(r, 'present_flawed')]
        missing = [r for r in subset if r['state'] == 'missing']
        repaired = sum(g[procedure]['correct'] for g in wrong)
        damaged = sum(1 - g[procedure]['correct'] for g in right)
        resource = row_usage_totals(subset)
        summaries[procedure] = {
            'planned': len(subset), 'complete': sum(r['status'] == 'complete' for r in subset),
            'correct': sum(r['correct'] for r in subset), 'accuracy': rate(sum(r['correct'] for r in subset), len(subset)),
            'present_flawed_correct': sum(r['correct'] for r in flawed), 'present_flawed_n': len(flawed),
            'missing_correct': sum(r['correct'] for r in missing), 'missing_n': len(missing),
            'natural_first_errors': len(wrong), 'families_with_first_errors': sorted({g['P0']['family_id'] for g in wrong}),
            'repaired': repaired if procedure != 'P0' else None,
            'repair_rate': rate(repaired, len(wrong)) if procedure != 'P0' else None,
            'first_correct_present': len(right), 'damaged': damaged if procedure != 'P0' else None,
            'damage_rate': rate(damaged, len(right)) if procedure != 'P0' else None,
            'failure_denominator_note': 'Every planned task remains in accuracy. Failure after a correct first answer counts as an unsuccessful retained decision in damage.',
            **resource, 'input_tokens': resource['sum_input_tokens'], 'output_tokens': resource['sum_output_tokens'],
            'seconds': sum(r['seconds'] for r in subset)}
    family = []
    for fid in sorted(family_kinds):
        for procedure in runner.PROCS:
            subset = [r for r in rows if r['family_id'] == fid and r['procedure'] == procedure]
            flawed = [r for r in subset if eligible(r, 'present_flawed')]
            family.append({'family_id': fid, 'error_type': next(iter(family_kinds[fid])), 'procedure': procedure,
                           'planned': len(subset), 'complete': sum(r['status'] == 'complete' for r in subset),
                           'correct': sum(r['correct'] for r in subset),
                           'present_flawed_n': len(flawed), 'present_flawed_correct': sum(r['correct'] for r in flawed)})
    primary = {'I78': contrast(groups, 'P8')}
    secondary_i73 = contrast(groups, 'P3')
    type_contrasts = {}
    for name, values in [('P7-P8', primary['I78']), ('P7-P3', secondary_i73),
                         ('P3-P1', contrast(groups, 'P1', treatment='P3'))]:
        type_contrasts[name] = {k: values[k] for k in ['type_mean_difference', 'available_families_by_type', 'families', 'type_family_difference_range']}
    sensitivity = {f'I7{other[1:]}': contrast(groups, other, complete_pair=True) for other in ['P8', 'P3']}
    secondary = {stratum: {f'I7{other[1:]}': contrast(groups, other, stratum) for other in ['P8', 'P3']}
                 for stratum in ['all', 'aligned', 'missing']}
    first_present = [g['P0'] for g in groups.values() if g['P0']['state'] != 'missing']
    first_complete = [r for r in first_present if r['status'] == 'complete']
    by_type = {}
    for kind in ['material', 'rule']:
        first = [g['P0'] for g in groups.values() if g['P0']['error_type'] == kind]
        flawed = [r for r in first if eligible(r, 'present_flawed')]
        aligned = [r for r in first if r['state'] != 'missing' and r['advice'] == 'aligned']
        missing = [r for r in first if r['state'] == 'missing']
        errors = [r for r in flawed if r['status'] == 'complete' and not r['correct']]
        by_type[kind] = {'present_flawed_planned': len(flawed), 'present_flawed_correct': sum(r['correct'] for r in flawed),
                         'present_flawed_completed': sum(r['status'] == 'complete' for r in flawed),
                         'present_flawed_natural_errors': len(errors),
                         'error_families': sorted({r['family_id'] for r in errors}),
                         'aligned_present_planned': len(aligned), 'aligned_present_correct': sum(r['correct'] for r in aligned),
                         'missing_planned': len(missing), 'missing_correct': sum(r['correct'] for r in missing)}
    diagnostic = {'by_type': by_type, 'P0_present_planned': len(first_present), 'P0_present_completed': len(first_complete),
                  'natural_first_errors': len(wrong),
                  'families_with_first_errors': sorted({g['P0']['family_id'] for g in wrong}),
                  'zero_observed_natural_errors': not wrong,
                  'complete_P0_present_ceiling': len(first_complete) == len(first_present) and not wrong,
                  'interpretation': 'No cases are screened out. Accuracy interactions remain computable at ceiling; repair is NA without initial errors, and a ceiling cannot show mechanism superiority or equivalence.'}
    return {'procedures': summaries, 'family_results': family, 'primary_interactions': primary,
            'secondary_interaction_I73': secondary_i73, 'within_type_contrasts': type_contrasts,
            'complete_pair_sensitivity': sensitivity, 'secondary_interactions': secondary,
            'difficulty_diagnostic': diagnostic, 'planned_groups': len(groups),
            'complete_groups': sum(all(r['status'] == 'complete' for r in g.values()) for g in groups.values()),
            'family_counts_by_type': dict(Counter(next(iter(t)) for t in family_kinds.values()))}


def run(phase='dev'):
    if phase != 'dev':
        raise ValueError('Only the 800-task development matrix exists')
    frozen = runner.verify()
    fhash = runner.file_sha(R / 'protocol/frozen.json')
    keys, items = entries(R / 'keys/dev_keys.json'), entries(R / 'prompts/dev_items.json')
    rows, sessions, real_attempts = [], [], []
    audit = {'frozen_hash': fhash, 'phase': phase, 'record_errors': [], 'unusual_item_types': [],
             'duplicate_session_ids': [], 'paused_tasks': [], 'unsealed_attempts': [], 'lifecycle_errors': []}
    audit['run_inventory'] = inventory_runs(frozen)
    if audit['run_inventory']['unplanned_artifacts']:
        audit['record_errors'].append('Unplanned run artifacts detected; complete run tree accounted for in run_inventory')
        out = R / 'analysis' / phase
        runner.dump(out / 'integrity_audit.json', audit)
        runner.dump(out / 'summary.json', {'phase': phase, 'passed_integrity': False,
                    'analysis_status': 'rejected_unplanned_artifacts', 'actual_cli_attempts': None,
                    'planned_tasks': len(frozen['phase_schedule'][phase]['jobs']), 'run_inventory': audit['run_inventory']})
        raise RuntimeError('Integrity audit failed: unplanned run artifacts')
    for job in frozen['phase_schedule'][phase]['jobs']:
        task = R / 'runs' / phase / job['group_id'] / job['procedure']
        rp = task / 'record.json'
        rec = runner.read(rp) if rp.exists() else {'status': 'not_executed', 'parsed': None, 'attempts': []}
        first_text = None
        if job['procedure'] != 'P0' and (rp.exists() or list(task.glob('attempt_*'))):
            first_job = {**job, 'procedure': 'P0'}
            first_path = task.parent / 'P0/record.json'
            if first_path.exists():
                first = runner.validate_record(phase, first_job, items[job['item_id']], None, fhash)
                first_text = first.get('raw_final')
        if rp.exists() and rec.get('attempts'):
            rec = runner.validate_record(phase, job, items[job['item_id']], first_text, fhash)
        elif rp.exists():
            if rec != runner.blocked_review_record(phase, job, fhash) or job['procedure'] == 'P0':
                raise RuntimeError('Invalid no-attempt terminal record: ' + str(rp))
            if first.get('status') in ['complete', 'parse_failure']:
                raise RuntimeError('Review skipped despite a usable P0 answer')
        else:
            # Preserve visibility of paused attempts without fabricating a terminal answer.
            prompt = runner.build_prompt(job, items[job['item_id']], first_text)
            identity = {**job, 'phase': phase, 'frozen_hash': fhash,
                        'first_sha256': runner.sha(first_text) if first_text is not None else None,
                        'prompt_sha256': runner.sha(prompt)}
            for ad in sorted(task.glob('attempt_*')):
                if not (ad / 'meta.json').exists():
                    if list(ad.iterdir()): audit['unsealed_attempts'].append(str(ad.relative_to(R)))
                    continue
                meta = runner.read(ad / 'meta.json')
                final = runner.validate_attempt(ad, meta, runner.sha(prompt), identity)
                rec['attempts'].append(meta)
                if final is not None and final.strip():
                    audit['record_errors'].append('Sealed final lacks terminal record: ' + str(ad.relative_to(R)))
            if rec['attempts']:
                rec['status'] = 'paused_unfinalized'
                audit['paused_tasks'].append({'group_id': job['group_id'], 'procedure': job['procedure']})
        for attempt in rec['attempts']:
            real_attempts.append(attempt)
            sessions += [sid for sid in attempt.get('thread_ids', []) if isinstance(sid, str) and sid.strip()]
            # The task's raw_final belongs only to its terminal attempt. Audit
            # each earlier failure against its own sealed output/events.
            attempt_prompt = runner.build_prompt(job, items[job['item_id']], first_text)
            attempt_identity = {**job, 'phase': phase, 'frozen_hash': fhash,
                                'first_sha256': runner.sha(first_text) if first_text is not None else None,
                                'prompt_sha256': runner.sha(attempt_prompt)}
            own_final = runner.validate_attempt(task / f"attempt_{attempt['attempt']:02d}", attempt,
                                                runner.sha(attempt_prompt), attempt_identity)
            if attempt.get('lifecycle_errors') and (attempt.get('turn_completed') or bool(own_final and own_final.strip())):
                audit['lifecycle_errors'].append({'group_id': job['group_id'], 'procedure': job['procedure'],
                                                 'attempt': attempt['attempt'], 'errors': attempt['lifecycle_errors']})
            audit['unusual_item_types'] += attempt.get('unexpected_items', [])
        key, item = keys[job['item_id']], items[job['item_id']]
        action = key.get('correct_action', key.get('action'))
        if action not in ['A', 'B', 'C', 'D']:
            raise ValueError('Invalid answer key: ' + job['item_id'])
        parsed, status = rec.get('parsed') or {}, rec['status']
        resource = usage_totals(rec['attempts'])
        rows.append({**job, 'family_id': item['family_id'], 'state': item['state'], 'advice': item['advice'],
                     'error_type': key['error_type'], 'status': status, 'correct_action': action,
                     'action': parsed.get('action', ''), 'correct': int(status == 'complete' and parsed.get('action') == action),
                     'parse_ok': int(bool(parsed)), 'pause_action': key.get('pause_action', key.get('escalate_action', '')),
                     'first_sha256': rec.get('first_sha256') or '', 'attempts': len(rec['attempts']),
                     'seconds': sum(a.get('seconds', 0) for a in rec['attempts']),
                     **resource,
                     'input_tokens': resource['sum_input_tokens'] if rec['attempts'] and resource['sum_input_tokens'] is not None else '',
                     'output_tokens': resource['sum_output_tokens'] if rec['attempts'] and resource['sum_output_tokens'] is not None else ''})
    audit['duplicate_session_ids'] = [k for k, n in Counter(sessions).items() if n > 1]
    results = summarize(rows)
    if results['family_counts_by_type'] != {'material': 4, 'rule': 4}:
        raise RuntimeError('Expected 4 material and 4 rule families')
    summary = {'phase': phase, 'planned_tasks': len(rows), 'actual_cli_attempts': len(real_attempts),
               'complete_tasks': sum(r['status'] == 'complete' for r in rows),
               'status_counts': dict(Counter(r['status'] for r in rows)), 'unique_sessions': len(set(sessions)),
               **usage_totals(real_attempts),
               'usage_known_tasks': sum(valid_token_count(r['input_tokens']) and valid_token_count(r['output_tokens']) for r in rows),
               **results,
               'resource_scope': 'Only subject CLI attempts; authoring, blind review and management overhead unknown and excluded.',
               'verified_billed_cost': None,
               'inference': 'Fixed-budget development simulation. Same 160 P0 calls serve as difficulty diagnosis and shared first answers. No independent screen, no human respondents, no confirmatory superiority claim.',
               'passed_integrity': not any(audit[k] for k in ['record_errors', 'unusual_item_types', 'duplicate_session_ids', 'unsealed_attempts', 'lifecycle_errors'])}
    out = R / 'analysis' / phase
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [('scored_runs.csv', rows), ('family_results.csv', results['family_results'])]:
        with (out / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    runner.dump(out / 'summary.json', summary)
    runner.dump(out / 'integrity_audit.json', audit)
    print(json.dumps({k: summary[k] for k in ['phase', 'planned_tasks', 'complete_tasks', 'actual_cli_attempts', 'status_counts', 'passed_integrity']}, ensure_ascii=False))
    if not summary['passed_integrity']:
        raise RuntimeError('Integrity audit failed')
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', nargs='?', default='dev', choices=['dev'])
    run(ap.parse_args().phase)
