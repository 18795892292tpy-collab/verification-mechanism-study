#!/usr/bin/env python3
"""Render v2 only after all 800 real scheduled tasks have sealed terminal records.

No model calls, mock inputs, partial-result rendering, or resampling. --check-only
performs the same read-only provenance checks without producing figures.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2')
PROCS = ['P0', 'P1', 'P3', 'P7', 'P8']
COLORS = {'P0': '#566C80', 'P1': '#D38D2F', 'P3': '#297A93', 'P7': '#237658', 'P8': '#8C629B'}
TERMINAL = {'complete', 'parse_failure', 'technical_failure', 'protocol_failure', 'not_run_first_failed'}
NAMES = {'P0': 'Initial answer', 'P1': 'Free review', 'P3': 'Source review',
         'P7': 'Condition review', 'P8': 'Generic review'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def token_value(attempt, field):
    """Interpret each token field independently, without coercing unknown usage."""
    usage = attempt.get('usage')
    value = usage.get(field) if isinstance(usage, dict) else None
    return value if type(value) is int and value >= 0 else None


def raw_usage_totals(attempts):
    """Independently reconstruct the frozen scorer's seven resource columns."""
    result, missing_indices = {}, set()
    for field in ['input_tokens', 'output_tokens']:
        values = [token_value(a, field) for a in attempts]
        missing = {i for i, value in enumerate(values) if value is None}
        known = sum(value for value in values if value is not None)
        result['sum_' + field] = None if missing else known
        result['known_' + field] = known
        result[field.replace('_tokens', '_usage_missing_attempts')] = len(missing)
        missing_indices.update(missing)
    result['usage_missing_attempts'] = len(missing_indices)
    return result


def scored_task_usage(attempts):
    resource = raw_usage_totals(attempts)
    return {**resource,
            **{field: resource['sum_' + field] if attempts and resource['sum_' + field] is not None else ''
               for field in ['input_tokens', 'output_tokens']}}


def csv_value(value):
    # csv.DictWriter emits None as an empty field; JSON retains it as null.
    return '' if value is None else str(value)


def load_concurrency_context(frozen, rows):
    """Read the during-run dispatch amendment without importing/executing its driver."""
    amendment_path = ROOT / 'protocol/CONCURRENCY_AMENDMENT_2026-11-07.json'
    driver_path = ROOT / 'harness/run_concurrency_override.py'
    applied_path = ROOT / 'audits/concurrency_amendment_applied.json'
    progress_path = ROOT / 'runs/dev/progress.jsonl'
    amendment = read(amendment_path)
    amendment_hash = sha256(amendment_path)
    expected = {'schema_version': 1, 'kind': 'dispatch_concurrency_only',
                'from_max_workers': 3, 'to_max_workers': 12, 'workers': 12,
                'baseline_frozen_sha256': sha256(ROOT / 'protocol/frozen.json'),
                'driver_sha256': sha256(driver_path)}
    require(all(amendment.get(k) == v for k, v in expected.items()), 'Dispatch amendment identity mismatch')
    require(frozen['execution_config']['max_workers'] == 3, 'Baseline worker limit changed')
    prior = amendment.get('prior_terminal_records')
    require(isinstance(prior, dict) and len(prior) == 667, 'Unexpected pre-amendment record inventory')
    planned_paths = {f"runs/dev/{r['group_id']}/{r['procedure']}/record.json": r for r in rows}
    require(set(prior) <= set(planned_paths), 'Foreign task in pre-amendment inventory')
    for relative, digest in prior.items():
        require(sha256(ROOT / relative) == digest, 'Pre-amendment terminal record changed: ' + relative)
    require(read(applied_path) == {'amendment_sha256': amendment_hash, 'amendment': amendment},
            'Missing or inconsistent applied amendment evidence')
    invocation_paths = sorted((ROOT / 'audits/concurrency_invocations').glob('*.json'))
    require(bool(invocation_paths), 'No saved amended-dispatch invocation')
    for path in invocation_paths:
        invocation = read(path)
        required = {'event': 'concurrency_amendment_invocation', 'amendment_sha256': amendment_hash,
                    'baseline_frozen_sha256': expected['baseline_frozen_sha256'],
                    'baseline_max_workers': 3, 'actual_workers': 12, 'scientific_configuration_changed': False}
        require(all(invocation.get(k) == v for k, v in required.items()), 'Unexpected amended-dispatch invocation')
    progress = [json.loads(line) for line in progress_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    starts = [event for event in progress if event.get('event') == 'invocation_started']
    require(bool(starts), 'No saved dispatcher startup events')
    sequence = []
    for event in starts:
        workers = event.get('workers')
        require(type(workers) is int and workers in {3, 12}, 'Unexpected recorded dispatcher worker count')
        if not sequence or workers != sequence[-1]:
            sequence.append(workers)
    require(sequence == [3, 12], 'Recorded dispatcher sequence differs from direct 3-to-12 amendment')
    progress_overrides = [event for event in progress if event.get('event') == 'concurrency_amendment_invocation']
    require(len(progress_overrides) == len(invocation_paths), 'Amended invocation count differs between audit and progress')
    for event in progress_overrides:
        require(event.get('amendment_sha256') == amendment_hash and event.get('actual_workers') == 12,
                'Amendment progress event mismatch')
    detail = {'kind': 'during_run_operational_amendment', 'created_utc': amendment['created_utc'],
              'from_workers': 3, 'to_workers': 12, 'observed_worker_limit_sequence': sequence,
              'six_workers_run': False, 'prior_terminal_tasks': len(prior),
              'prior_complete_tasks': sum(planned_paths[relative]['status'] == 'complete' for relative in prior),
              'remaining_tasks_at_amendment': len(rows) - len(prior),
              'amended_invocations': len(invocation_paths), 'amendment_sha256': amendment_hash,
              'prior_runner_exit_code': amendment.get('prior_runner_exit_code'),
              'prior_runner_exit_reason': amendment.get('prior_runner_exit_reason'),
              'operational_limits': amendment['operational_limits'],
              'interpretation': 'Worker limits are dispatch settings, not continuously achieved concurrency. '
                                'Mixed phases cannot identify causal speedup or fair cross-procedure wall-clock performance.'}
    sources = {amendment_path, driver_path, applied_path, progress_path, *invocation_paths}
    return detail, sources


def load_completed_data():
    """Verify exact target, raw records, frozen inputs, scoring and actual attempts."""
    require(socket.gethostname() == 'liekkas' and ROOT == TARGET,
            'Wrong host or target path; a copy is not the authorized experiment')
    paths = [ROOT / p for p in ['analysis/dev/summary.json', 'analysis/dev/scored_runs.csv',
                                'analysis/dev/integrity_audit.json', 'protocol/frozen.json']]
    require(all(p.is_file() for p in paths), 'Real evaluated data do not exist yet')
    summary = read(paths[0])
    with paths[1].open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    require(summary.get('phase') == 'dev' and summary.get('planned_tasks') == 800 and len(rows) == 800,
            'Expected the complete fixed 800-task development matrix')
    require(all(r['status'] in TERMINAL for r in rows), 'Unfinished tasks remain; refusing output')
    sys.path.insert(0, str(ROOT / 'harness'))
    import runner
    import evaluate
    frozen = runner.verify()  # Read-only hashes/identity; this never launches the model.
    inventory = evaluate.inventory_runs(frozen)
    require(not inventory['unplanned_artifacts'], 'Unplanned artifacts or symlinks in run tree')
    jobs = frozen['phase_schedule']['dev']['jobs']
    require(len(jobs) == 800, 'Wrong schedule size')
    expected = {(j['group_id'], j['procedure']): j for j in jobs}
    observed = {(r['group_id'], r['procedure']): r for r in rows}
    require(len(observed) == 800 and set(observed) == set(expected), 'Missing, duplicated, or foreign CSV tasks')
    record_paths = {k: ROOT / 'runs/dev' / k[0] / k[1] / 'record.json' for k in expected}
    require(all(p.is_file() for p in record_paths.values()), 'All 800 tasks must have real terminal records')
    require(set((ROOT / 'runs/dev').glob('*/*/record.json')) == set(record_paths.values()), 'Unexpected terminal records')
    items = evaluate.entries(ROOT / 'prompts/dev_items.json')
    keys = evaluate.entries(ROOT / 'keys/dev_keys.json')
    fhash = sha256(ROOT / 'protocol/frozen.json')
    records, attempts, sessions, typed_rows = {}, [], [], []
    for k in sorted(expected, key=lambda x: (x[0], PROCS.index(x[1]))):
        job, row = expected[k], observed[k]
        item, key = items[job['item_id']], keys[job['item_id']]
        rec = read(record_paths[k])
        require(rec.get('status') in TERMINAL, 'Nonterminal raw record: ' + str(k))
        first = records.get((k[0], 'P0')) if k[1] != 'P0' else None
        first_text = first.get('raw_final') if first else None
        if rec.get('attempts'):
            rec = runner.validate_record('dev', job, item, first_text, fhash)
        else:
            require(k[1] != 'P0' and rec == runner.blocked_review_record('dev', job, fhash),
                    'Invalid no-attempt record')
            require(first['status'] not in {'complete', 'parse_failure'}, 'Review skipped despite usable first answer')
            require(not list(record_paths[k].parent.glob('attempt_*')), 'Hidden attempts in blocked review')
        records[k] = rec
        parsed = rec.get('parsed') or {}
        action = key.get('correct_action', key.get('action'))
        task_usage = scored_task_usage(rec['attempts'])
        typed = {**job, 'family_id': item['family_id'], 'state': item['state'], 'advice': item['advice'],
                 'error_type': key['error_type'], 'status': rec['status'], 'correct_action': action,
                 'action': parsed.get('action', ''),
                 'correct': int(rec['status'] == 'complete' and parsed.get('action') == action),
                 'parse_ok': int(bool(parsed)), 'pause_action': key.get('pause_action', key.get('escalate_action', '')),
                 'first_sha256': rec.get('first_sha256') or '', 'attempts': len(rec['attempts']),
                 'seconds': sum(a.get('seconds', 0) for a in rec['attempts']),
                 **task_usage}
        require(set(row) == set(typed), 'Unexpected scored CSV schema')
        require(all(row[field] == csv_value(value) for field, value in typed.items()), 'CSV differs from raw record: ' + str(k))
        typed_rows.append(typed)
        for a in rec['attempts']:
            attempts.append({**a, 'procedure': k[1], 'group_id': k[0]})
            sessions.extend(sid for sid in a.get('thread_ids', []) if isinstance(sid, str) and sid.strip())
            ad = record_paths[k].parent / f"attempt_{a['attempt']:02d}"
            # validate_record() already verified these files and event metadata.
            # The final belongs to this attempt, not its later successful retry.
            own_final = runner.attempt_final(ad / 'response.json', a)
            require(not a.get('unexpected_items'), 'Unexpected raw event/item: ' + str(ad))
            require(not (a.get('lifecycle_errors') and
                         (a.get('turn_completed') or bool(own_final and own_final.strip()))),
                    'Invalid returned-answer lifecycle: ' + str(ad))
    # summarize() has deterministic means; preserve original evaluator row order.
    by_key = {(r['group_id'], r['procedure']): r for r in typed_rows}
    typed_rows = [by_key[(r['group_id'], r['procedure'])] for r in rows]
    recalculated = evaluate.summarize(typed_rows)
    require(all(summary.get(k) == v for k, v in recalculated.items()), 'Summary differs from deterministic rescoring')
    require(summary['family_counts_by_type'] == {'material': 4, 'rule': 4}, 'Expected four families per type')
    counts = dict(Counter(r['status'] for r in typed_rows))
    require(summary['status_counts'] == counts and summary['complete_tasks'] == counts.get('complete', 0), 'Status totals mismatch')
    require(summary['actual_cli_attempts'] == len(attempts), 'Actual attempt count mismatch')
    require(summary['unique_sessions'] == len(set(sessions)) and len(sessions) == len(set(sessions)), 'Session provenance mismatch')
    resource = raw_usage_totals(attempts)
    require(all(summary.get(k) == v for k, v in resource.items()), 'Summary resource total/NA/subtotal mismatch')
    known_tasks = sum(type(r['input_tokens']) is int and r['input_tokens'] >= 0 and
                      type(r['output_tokens']) is int and r['output_tokens'] >= 0 for r in typed_rows)
    require(summary['usage_known_tasks'] == known_tasks, 'Known task usage count mismatch')
    for p in PROCS:
        resource = raw_usage_totals([a for a in attempts if a['procedure'] == p])
        reported = summary['procedures'][p]
        require(all(reported.get(k) == v for k, v in resource.items()), 'Procedure resource mismatch: ' + p)
        require(all(reported[field] == resource['sum_' + field] for field in ['input_tokens', 'output_tokens']),
                'Procedure resource alias mismatch: ' + p)
    require(inventory['observed_record_files'] == 800, 'Run inventory record count mismatch')
    for field in ['observed_attempt_directories', 'observed_started_attempt_files', 'observed_sealed_attempt_files']:
        require(inventory[field] == len(attempts), 'Run inventory attempt count mismatch: ' + field)
    audit = read(ROOT / 'analysis/dev/integrity_audit.json')
    require(summary['passed_integrity'] is True and audit['frozen_hash'] == fhash, 'Integrity audit not passed')
    audit_fields = ['record_errors', 'unusual_item_types', 'duplicate_session_ids',
                    'paused_tasks', 'unsealed_attempts', 'lifecycle_errors']
    require(audit.get('phase') == 'dev' and all(k in audit for k in audit_fields), 'Incomplete or foreign audit schema')
    require(not any(audit[k] for k in audit_fields), 'Unresolved audit findings')
    require(audit.get('run_inventory') == inventory, 'Saved audit run inventory differs from current run tree')
    concurrency, concurrency_sources = load_concurrency_context(frozen, typed_rows)
    summary['presentation_concurrency'] = concurrency  # Derived in memory; never alters frozen/scored files.
    source_paths = set(paths) | set(record_paths.values()) | concurrency_sources
    source_paths |= {ROOT / 'runs/dev' / p for p in ['plan.csv', 'manifest_identity.json']}
    source_paths |= {ROOT / p for p in frozen['sha256']}
    source_paths |= {ROOT / p for p in ['analysis/plot_results.py', 'analysis/write_report.py', 'report/FIGURE_PROVENANCE.md']}
    for rp in record_paths.values():
        source_paths.update(p for p in rp.parent.rglob('*') if p.is_file())
    hashes = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(source_paths)}
    return summary, typed_rows, attempts, hashes


def verify_unchanged(hashes):
    for path, digest in hashes.items():
        require(sha256(ROOT / path) == digest, 'Source changed during generation: ' + path)


def resource_totals(attempts, procedure=None):
    aa = [a for a in attempts if procedure is None or a['procedure'] == procedure]
    result = {'attempts': len(aa)}
    for field in ['input_tokens', 'output_tokens', 'seconds']:
        values = [a.get(field) if field == 'seconds' else token_value(a, field) for a in aa]
        known = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0]
        result[field] = sum(known) if known else None
        result[field + '_known'] = len(known)
        result[field + '_missing'] = len(aa) - len(known)
        result[field + '_complete'] = len(known) == len(aa) and bool(aa)
    return result


def setup_style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 12,
                         'axes.spines.top': False, 'axes.spines.right': False, 'axes.axisbelow': True,
                         'grid.color': '#E2E7EB', 'svg.fonttype': 'none', 'pdf.fonttype': 42,
                         'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
    return matplotlib, plt


def frame(plt, title, subtitle, ncols=1, height=6.5):
    fig, axes = plt.subplots(1, ncols, figsize=(14, height), squeeze=False)
    fig.subplots_adjust(top=.77, bottom=.23, left=.07, right=.97, wspace=.30)
    fig.text(.04, .95, title, fontsize=19, weight='bold', va='top')
    fig.text(.04, .89, subtitle, color='#536978', va='top')
    return fig, list(axes[0])


def footer(fig, text):
    fig.text(.04, .035, text, fontsize=9, color='#536978', va='bottom', linespacing=1.4)


def design_figure(plt, summary, rows, attempts):
    from matplotlib.patches import FancyBboxPatch
    fig, (ax,) = frame(plt, 'Planned design: 800 tasks', 'Design schematic; these counts describe the fixed plan, not successful responses.')
    ax.set(xlim=(-.025, 1.025), ylim=(0, 1)); ax.axis('off')
    def box(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=.012', fc='#F7F9FA', ec=color, lw=1.4))
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=10, color=color, linespacing=1.5)
    box(.01, .33, .21, .34, '8 designed families\n4 material + 4 rule\n5 states × 2 advice versions\n80 items', '#445B70')
    box(.30, .33, .18, .34, '2 repeats per item\n160 P0 tasks\nOne shared first answer\nper item / repeat', COLORS['P0'])
    ax.annotate('', (.29, .5), (.23, .5), arrowprops={'arrowstyle': '->'})
    for p, y in zip(PROCS[1:], [.78, .55, .32, .09]):
        box(.59, y, .20, .16, p + ': ' + NAMES[p] + '\n160 planned review tasks', COLORS[p])
        ax.annotate('', (.58, y+.08), (.49, .5), arrowprops={'arrowstyle': '->', 'color': '#9AABB5'})
        ax.annotate('', (.87, .5), (.80, y+.08), arrowprops={'arrowstyle': '->', 'color': '#9AABB5'})
    box(.88, .33, .10, .34, 'Fixed key\nAction\nscoring\n800 tasks', '#445B70')
    footer(fig, f"Observed execution: 800 terminal records; {summary['complete_tasks']} successful; "
           f"{800-summary['complete_tasks']} failed or blocked; {len(attempts)} actual CLI attempts.\n"
           '160 initial tasks + 640 review tasks. No additional subject screening; no human participants.')
    return fig


def family_figure(plt, summary, rows, attempts):
    import numpy as np
    families = sorted({r['family_id'] for r in rows}, key=lambda f: (next(r['error_type'] for r in rows if r['family_id'] == f), f))
    fig, axes = frame(plt, 'Observed accuracy by designed family',
                      'Every planned task stays in the denominator; unsuccessful and blocked tasks score zero.', 2, height=8)
    for ax, flawed, title in zip(axes, [False, True], ['All items', 'Evidence present + flawed advice']):
        matrix, labels = [], []
        for fid in families:
            kind = next(r['error_type'] for r in rows if r['family_id'] == fid)
            labels.append(f'{fid} [{kind}]')
            line = []
            for p in PROCS:
                rr = [r for r in rows if r['family_id'] == fid and r['procedure'] == p and
                      (not flawed or (r['state'] != 'missing' and r['advice'] == 'flawed'))]
                line.append((sum(r['correct'] for r in rr), len(rr)))
            matrix.append(line)
        values = np.array([[100*n/d if d else np.nan for n,d in line] for line in matrix])
        im = ax.imshow(values, cmap='cividis', vmin=0, vmax=100, aspect='auto')
        ax.set_xticks(range(5), PROCS); ax.set_yticks(range(8), labels, fontsize=8)
        ax.set_title(title, loc='left', pad=12)
        for y, line in enumerate(matrix):
            for x, (n, d) in enumerate(line):
                v = values[y, x]
                ax.text(x, y, f'{n}/{d}\n{v:.0f}%' if d else 'NA', ha='center', va='center',
                        color='white' if v < 50 else '#17242D', fontsize=8)
        fig.colorbar(im, ax=ax, fraction=.04, pad=.025, label='Correct (%)', ticks=[0, 50, 100])
    footer(fig, 'Cell labels are observed correct / planned counts. Repeats and variants are dependent within a family.\n'
               'Eight constructed families, four per type; descriptive development results only. No confidence intervals.')
    return fig


def contrast_figure(plt, summary, rows, attempts):
    fig, axes = frame(plt, 'Family contrasts on evidence-present flawed advice',
                      'Dots: paired within-family differences. Diamonds: equal-family type means. Lines: observed family min–max.', 2, 7)
    for ax, contrast, name in zip(axes, [summary['primary_interactions']['I78'], summary['secondary_interaction_I73']],
                                  ['I78 (primary): P7 − P8', 'I73 (secondary): P7 − P3']):
        labels = []
        for y, kind in enumerate(['material', 'rule']):
            ff = [f for f in contrast['families'] if f['error_type'] == kind and f['difference'] is not None]
            vals = [100*f['difference'] for f in ff]
            if vals:
                mean_y = y + .31
                ax.hlines(mean_y, min(vals), max(vals), color='#75838D', linewidth=2)
                ax.vlines([min(vals), max(vals)], mean_y-.035, mean_y+.035, color='#75838D', linewidth=1.5)
                for index, (f, value) in enumerate(zip(ff, vals)):
                    offset = (index-(len(ff)-1)/2)*.10
                    ax.scatter([value], [y+offset], s=40, color=['#297A93', '#D38D2F'][y], zorder=3)
                    ax.annotate(f['family_id'], (value, y+offset), xytext=(6, 2), textcoords='offset points', fontsize=7)
                ax.scatter([100*contrast['type_mean_difference'][kind]], [mean_y], marker='D', s=65,
                           facecolors='white', edgecolors='#162F3C', zorder=4)
            labels.append(kind + f' (n={len(ff)} families)')
        ax.axvline(0, color='#A3ADB4', linestyle='--', linewidth=1)
        ax.set(xlim=(-110, 110), ylim=(-.65, 1.65), xlabel='P7 minus comparator (percentage points)')
        ax.set_yticks([0, 1], labels); ax.set_title(name, loc='left', pad=15); ax.grid(axis='x')
        estimate = contrast['estimate']
        ax.text(.01, -.23, 'Interaction (rule − material): ' + ('NA' if estimate is None else f'{100*estimate:+.2f} pp'),
                transform=ax.transAxes, fontsize=11, weight='bold')
    footer(fig, 'Ranges are observed family min–max, NOT confidence intervals; a zero-width range collapses to its mean marker.\n'
               'Failure-inclusive planned denominator. An interaction of zero or a ceiling does not establish equivalence or mechanism isolation.')
    return fig


def resources_figure(plt, summary, rows, attempts):
    fig, axes = frame(plt, 'Recorded resources across actual subject attempts',
                      'Known usage is shown as a subtotal when incomplete; missing usage is never filled with zero.', 3, 6.7)
    totals = {p: resource_totals(attempts, p) for p in PROCS}
    for ax, field, heading in zip(axes, ['input_tokens', 'output_tokens', 'seconds'],
                                  ['Input tokens', 'Output tokens', 'Summed attempt duration (s)']):
        vals = [totals[p][field] for p in PROCS]
        scale = max([v for v in vals if v is not None] or [1]) or 1
        for x, p in enumerate(PROCS):
            t, value = totals[p], vals[x]
            if value is None:
                ax.text(x, scale*.2, 'NA', ha='center')
            else:
                ax.bar(x, value, color=COLORS[p], width=.6,
                       hatch=None if t[field+'_complete'] else '///', edgecolor='white')
                label = f'{value:,.0f}' + ('' if t[field+'_complete'] else '*')
                ax.text(x, value+scale*.025, label, ha='center', fontsize=8)
            ax.text(x, -scale*.14, f"{t[field+'_known']}/{t['attempts']}", ha='center', fontsize=8)
        ax.set_xticks(range(5), PROCS); ax.set_ylim(0, scale*1.22)
        ax.set_title(heading, loc='left'); ax.grid(axis='y'); ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 4))
    c = summary['presentation_concurrency']
    footer(fig, f"{len(attempts)} actual attempts for 800 planned tasks. Below bars: known-field / actual attempts. * Hatched bars: known subtotal.\n"
               f"Dispatch limit {c['from_workers']} → {c['to_workers']} after {c['prior_terminal_tasks']} terminal tasks; "
               f"{c['remaining_tasks_at_amendment']} tasks remained. Six workers were never used.\n"
               'Mixed dispatch phases: summed durations are not wall time or causal speedup. Billed cost: NA.\n'
               'Subject tasks only; authoring, same-family review and management overhead are unknown and excluded.')
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        summary, rows, attempts, hashes = load_completed_data()
        if args.check_only:
            print(json.dumps({'ready': True, 'terminal_tasks': len(rows), 'actual_attempts': len(attempts),
                              'source_files': len(hashes)}))
            return 0
        matplotlib, plt = setup_style()
        out = ROOT / 'figures'; out.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.render_', dir=out) as td:
            staging = Path(td); names = []
            for name, builder in [('fig1_design', design_figure), ('fig2_family_accuracy', family_figure),
                                  ('fig3_family_contrasts', contrast_figure), ('fig4_resources', resources_figure)]:
                fig = builder(plt, summary, rows, attempts)
                try:
                    for ext in ['svg', 'png', 'pdf']:
                        target = staging / f'{name}.{ext}'
                        fig.savefig(target, dpi=300, bbox_inches='tight', pad_inches=.2)
                        names.append(target.name)
                finally:
                    plt.close(fig)
            verify_unchanged(hashes)
            manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'phase': 'dev',
                        'planned_tasks': 800, 'terminal_tasks': len(rows), 'complete_tasks': summary['complete_tasks'],
                        'actual_cli_attempts': len(attempts), 'families_by_type': {'material': 4, 'rule': 4},
                        'dispatch_concurrency': summary['presentation_concurrency'],
                        'input_sha256': hashes, 'outputs': {n: sha256(staging/n) for n in names},
                        'matplotlib_version': matplotlib.__version__, 'visual_review': 'pending',
                        'uncertainty': 'Descriptive points and observed family ranges; no confidence intervals',
                        'data_origin': 'Real saved CLI responses to synthetic rule tasks; no mock measurements'}
            for name in names:
                (staging/name).replace(out/name)
            (out/'figure_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({'figures': names, 'visual_review': 'pending'}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print('Refusing to render: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
