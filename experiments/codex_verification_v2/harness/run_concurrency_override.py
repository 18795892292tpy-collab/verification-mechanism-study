#!/usr/bin/env python3
"""Explicit post-freeze concurrency amendment. Original scientific inputs stay frozen.

Only a private copy of runner.run's MAX_WORKERS guard changes. All called
functions, including verify/execution_config/response_task, retain their
original module globals. Never execute this driver without a matching amendment.
"""
from pathlib import Path
import argparse
import json
import types
import uuid
import runner
import evaluate

AMENDMENT = 'protocol/CONCURRENCY_AMENDMENT_2026-11-07.json'
APPLIED = 'audits/concurrency_amendment_applied.json'
DRIVER = Path(__file__).resolve()


def clone_run():
    scope = dict(runner.run.__globals__)
    scope['MAX_WORKERS'] = 12
    return types.FunctionType(runner.run.__code__, scope, runner.run.__name__,
                              runner.run.__defaults__, runner.run.__closure__)


def check_amendment():
    frozen = runner.verify()  # Original function/globals; baseline max_workers remains 3.
    root = runner.R
    amendment_path = root / AMENDMENT
    amendment = runner.read(amendment_path)
    expected = {'schema_version': 1, 'kind': 'dispatch_concurrency_only',
                'from_max_workers': 3, 'to_max_workers': 12, 'workers': 12,
                'baseline_frozen_sha256': runner.file_sha(root / 'protocol/frozen.json'),
                'driver_sha256': runner.file_sha(DRIVER)}
    if any(amendment.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Concurrency amendment identity or scope mismatch')
    inventory_root = evaluate.R
    # Both modules must point to the same target. Normal invocation never changes either.
    if Path(inventory_root).resolve() != Path(root).resolve():
        raise RuntimeError('Inventory target differs from runner target')
    inventory = evaluate.inventory_runs(frozen)
    if inventory['unplanned_artifacts']:
        raise RuntimeError('Unplanned run artifacts; concurrency amendment refused')
    prior = amendment.get('prior_terminal_records')
    if not isinstance(prior, dict):
        raise RuntimeError('Missing prior terminal record SHA inventory')
    planned = {f"runs/dev/{j['group_id']}/{j['procedure']}/record.json"
               for j in frozen['phase_schedule']['dev']['jobs']}
    if not set(prior) <= planned:
        raise RuntimeError('Unplanned task in prior terminal record inventory')
    current = {str(p.relative_to(root)) for p in (root / 'runs/dev').glob('*/*/record.json')}
    for relative, digest in prior.items():
        path = root / relative
        if not path.is_file() or runner.file_sha(path) != digest:
            raise RuntimeError('Prior terminal record changed: ' + relative)
    applied = root / APPLIED
    evidence = {'amendment_sha256': runner.file_sha(amendment_path), 'amendment': amendment}
    if applied.exists():
        if runner.read(applied) != evidence:
            raise RuntimeError('Applied concurrency amendment cannot be replaced')
    elif current != set(prior):
        raise RuntimeError('Initial amendment must inventory every current terminal record')
    return amendment, evidence


def run(part='all', verify_only=False):
    root = runner.R
    out = root / 'runs/dev'
    # Refuse to inspect/apply while an original or amended dispatcher owns the run.
    with runner.DirectoryLock(out):
        amendment, evidence = check_amendment()
        if verify_only:
            return True
        if not (root / APPLIED).exists():
            runner.seal_json(root / APPLIED, evidence)
        invocation = {'utc': runner.now(), 'event': 'concurrency_amendment_invocation',
                      'amendment_sha256': evidence['amendment_sha256'],
                      'baseline_frozen_sha256': amendment['baseline_frozen_sha256'],
                      'baseline_max_workers': 3, 'actual_workers': 12, 'part': part,
                      'scientific_configuration_changed': False}
        runner.seal_json(root / 'audits/concurrency_invocations' / (uuid.uuid4().hex + '.json'), invocation)
        runner.append_progress(out, invocation)
    # The unmodified run body reacquires the same cross-process directory lock,
    # re-runs original verify, and uses unchanged original response_task/gate.
    return clone_run()('dev', part, 12)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--part', choices=['P0', 'review', 'all'], default='all')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if not run(args.part, args.verify):
        raise SystemExit(75)
