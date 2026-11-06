"""V2 scheduling, provenance and service-breaker tests. Every CLI call is mocked."""
import contextlib
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'harness'))
import runner
import evaluate
from integrity import DirectoryLock, LockUnavailable
from test_runner_offline import VALID, fake_call


def items80():
    return [{'item_id': f'F{family:02d}_{state}_{advice}', 'family_id': f'F{family:02d}',
             'state': state, 'advice': advice, 'public_text': '虚构规则：选择A。'}
            for family in range(1, 9)
            for state in ['base', 'decisive_change', 'irrelevant', 'paraphrase', 'missing']
            for advice in ['aligned', 'flawed']]


def valid_call(cmd, **kwargs):
    output = Path(cmd[cmd.index('-o') + 1])
    assert (output.parent / 'attempt_started.json').is_file()
    output.write_text(VALID)
    events = [{'type': 'thread.started', 'thread_id': runner.sha(str(output))},
              {'type': 'turn.started'}, {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 5}}]
    return subprocess.CompletedProcess(cmd, 0, '\n'.join(json.dumps(e) for e in events), '')


def service_error(message='You have hit your usage limit. Try again later.', final=None):
    def invoke(cmd, **kwargs):
        output = Path(cmd[cmd.index('-o') + 1])
        if final is not None: output.write_text(final)
        events = [{'type': 'thread.started', 'thread_id': runner.sha(str(output))},
                  {'type': 'turn.failed', 'error': {'message': message}}]
        return subprocess.CompletedProcess(cmd, 1, '\n'.join(json.dumps(e) for e in events), '')
    return invoke


class V2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch_r = patch.object(runner, 'R', self.root)
        self.patch_r.start()
        self.cli = self.root / 'mock-codex'
        self.cli.write_text('offline fixture, never executed')
        self.patch_cli = patch.object(runner, 'CLI', str(self.cli))
        self.patch_cli.start()
        self.job = {'group_id': 'item_r1', 'item_id': 'item', 'repeat': 1, 'procedure': 'P0'}
        self.item = {'public_text': '选择A。'}

    def tearDown(self):
        self.patch_cli.stop()
        self.patch_r.stop()
        self.tmp.cleanup()

    @property
    def task(self):
        return self.root / 'runs/dev/item_r1/P0'

    def prepare_freeze(self):
        for name in runner.FROZEN_FILES:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('{}')
        runner.dump(self.root / 'prompts/dev_items.json', items80())
        runner.dump(self.root / 'keys/dev_keys.json', {
            i['item_id']: {'correct_action': 'A', 'error_type': 'material' if int(i['family_id'][1:]) <= 4 else 'rule',
                           'pause_action': 'D'} for i in items80()})
        with contextlib.redirect_stdout(io.StringIO()): runner.freeze()
        return runner.verify()

    def respond(self, call=valid_call, gate=None):
        with patch.object(runner.subprocess, 'run', side_effect=call) as mock:
            rec = runner.response_task('dev', self.job, self.item, None, 'fixed', gate)
        return rec, mock.call_count

    def test_missing_or_duplicate_session_and_turn_lifecycle_rejected(self):
        good = [{'type': 'thread.started', 'thread_id': 'session'}, {'type': 'turn.started'},
                {'type': 'turn.completed', 'usage': {'input_tokens': 17, 'output_tokens': 9}}]
        variants = [good[1:], [*good[:2], good[2], good[2]], [good[0], good[2]],
                    [good[0], good[0], *good[1:]], [good[1], good[0], good[2]],
                    [{'type': 'thread.started', 'thread_id': ''}, *good[1:]],
                    [{'type': 'thread.started', 'thread_id': '  '}, *good[1:]],
                    [{'type': 'thread.started', 'thread_id': {'bad': 'id'}}, *good[1:]]]
        for events in variants:
            with self.subTest(events=events):
                info = runner.events_info('\n'.join(json.dumps(e) for e in events))
                status, _, _ = runner.classify_final({**info, 'returncode': 0, 'output_sha256': 'hash'}, VALID)
                self.assertEqual(status, 'protocol_failure')
                self.assertTrue(info['lifecycle_errors'])
        doubled = runner.events_info('\n'.join(json.dumps(e) for e in variants[1]))
        self.assertIsNone(doubled['usage'])
        self.assertEqual(len(doubled['turn_completion_usages']), 2)

    def test_no_final_connection_failure_without_session_remains_recoverable(self):
        info = runner.events_info(json.dumps({'type': 'turn.failed', 'error': {'message': 'TLS unexpected EOF'}}))
        status, _, _ = runner.classify_final({**info, 'returncode': 1, 'output_sha256': None}, None)
        self.assertEqual(status, 'technical_failure')
        self.assertFalse(info['unexpected_items'])
        self.assertEqual(runner.service_block_reason(info, '', 1), 'network_transport')

    def evaluated_usage_fixture(self, usage):
        frozen = self.prepare_freeze()
        job = next(j for j in frozen['phase_schedule']['dev']['jobs'] if j['procedure'] == 'P0')
        item = next(i for i in runner.load_items() if i['item_id'] == job['item_id'])
        def call(cmd, **kwargs):
            Path(cmd[cmd.index('-o') + 1]).write_text(VALID)
            events = [{'type': 'thread.started', 'thread_id': 'usage-test-session'}, {'type': 'turn.started'},
                      {'type': 'turn.completed', 'usage': usage}]
            return subprocess.CompletedProcess(cmd, 0, '\n'.join(json.dumps(e) for e in events), '')
        with patch.object(runner.subprocess, 'run', side_effect=call):
            runner.response_task('dev', job, item, None, runner.file_sha(self.root / 'protocol/frozen.json'))
        with patch.object(evaluate, 'R', self.root), contextlib.redirect_stdout(io.StringIO()):
            result = evaluate.run()
        with (self.root / 'analysis/dev/scored_runs.csv').open() as stream:
            row = next(r for r in csv.DictReader(stream) if r['group_id'] == job['group_id'] and r['procedure'] == 'P0')
        return result, row

    def test_no_final_tls_pause_then_success_passes_end_to_end_evaluation(self):
        frozen = self.prepare_freeze()
        job = next(j for j in frozen['phase_schedule']['dev']['jobs'] if j['procedure'] == 'P0')
        item = next(i for i in runner.load_items() if i['item_id'] == job['item_id'])
        frozen_hash = runner.file_sha(self.root / 'protocol/frozen.json')
        with patch.object(runner.subprocess, 'run', side_effect=service_error('TLS unexpected EOF')) as mock:
            first = runner.response_task('dev', job, item, None, frozen_hash, runner.DispatchGate())
        self.assertEqual(first['status'], 'paused_service')
        self.assertEqual(mock.call_count, 1)
        task = self.root / 'runs/dev' / job['group_id'] / 'P0'
        original = {p.name: p.read_bytes() for p in (task / 'attempt_01').iterdir()}
        with patch.object(runner.subprocess, 'run', side_effect=valid_call) as mock:
            second = runner.response_task('dev', job, item, None, frozen_hash, runner.DispatchGate())
        self.assertEqual(second['status'], 'complete')
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(second['raw_final'], VALID)
        self.assertTrue(second['attempts'][0]['lifecycle_errors'])
        self.assertFalse(second['attempts'][1]['lifecycle_errors'])
        self.assertEqual(original, {p.name: p.read_bytes() for p in (task / 'attempt_01').iterdir()})
        with patch.object(evaluate, 'R', self.root), contextlib.redirect_stdout(io.StringIO()):
            result = evaluate.run()
        self.assertTrue(result['passed_integrity'])
        self.assertEqual(result['actual_cli_attempts'], 2)
        self.assertEqual(result['complete_tasks'], 1)
        self.assertEqual(result['known_input_tokens'], 10)
        self.assertEqual(result['known_output_tokens'], 5)
        self.assertEqual(result['usage_missing_attempts'], 1)
        self.assertIsNone(result['sum_input_tokens'])
        self.assertIsNone(result['sum_output_tokens'])
        audit = runner.read(self.root / 'analysis/dev/integrity_audit.json')
        self.assertEqual(audit['lifecycle_errors'], [])

    def test_empty_usage_is_unknown_in_rows_procedures_and_totals(self):
        result, row = self.evaluated_usage_fixture({})
        self.assertEqual(row['input_tokens'], '')
        self.assertEqual(row['output_tokens'], '')
        for values in [result, result['procedures']['P0']]:
            self.assertIsNone(values['sum_input_tokens'])
            self.assertIsNone(values['sum_output_tokens'])
            self.assertEqual(values['known_input_tokens'], 0)
            self.assertEqual(values['known_output_tokens'], 0)
            self.assertEqual(values['input_usage_missing_attempts'], 1)
            self.assertEqual(values['output_usage_missing_attempts'], 1)
            self.assertEqual(values['usage_missing_attempts'], 1)
            self.assertEqual(values['usage_known_tasks'], 0)

    def test_partial_usage_retains_known_input_and_unknown_output(self):
        result, row = self.evaluated_usage_fixture({'input_tokens': 17})
        self.assertEqual(row['input_tokens'], '17')
        self.assertEqual(row['output_tokens'], '')
        for values in [result, result['procedures']['P0']]:
            self.assertEqual(values['sum_input_tokens'], 17)
            self.assertIsNone(values['sum_output_tokens'])
            self.assertEqual(values['known_input_tokens'], 17)
            self.assertEqual(values['input_usage_missing_attempts'], 0)
            self.assertEqual(values['output_usage_missing_attempts'], 1)
            self.assertEqual(values['usage_missing_attempts'], 1)
            self.assertEqual(values['usage_known_tasks'], 0)

    def test_unplanned_group_records_are_rejected_and_counted(self):
        self.prepare_freeze()
        path = self.root / 'runs/dev/unplanned_group/P0/record.json'
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        with patch.object(evaluate, 'R', self.root), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'unplanned run artifacts'): evaluate.run()
        audit = runner.read(self.root / 'analysis/dev/integrity_audit.json')
        self.assertEqual(audit['run_inventory']['observed_record_files'], 1)
        self.assertTrue(any(x['path'].endswith('unplanned_group/P0/record.json') for x in audit['run_inventory']['unplanned_artifacts']))
        summary = runner.read(self.root / 'analysis/dev/summary.json')
        self.assertFalse(summary['passed_integrity'])
        self.assertIsNone(summary['actual_cli_attempts'])

    def test_inventory_rejects_extra_attempt_procedure_phase_and_raw_files(self):
        frozen = self.prepare_freeze()
        job = frozen['phase_schedule']['dev']['jobs'][0]
        extras = [f'dev/{job["group_id"]}/{job["procedure"]}/attempt_03/meta.json',
                  f'dev/{job["group_id"]}/P99/record.json', 'toy/ghost/P0/record.json',
                  f'dev/{job["group_id"]}/{job["procedure"]}/attempt_01/unsealed-copy.json']
        for relative in extras:
            path = self.root / 'runs' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}')
        with patch.object(evaluate, 'R', self.root):
            inventory = evaluate.inventory_runs(frozen)
        rejected = {r['path'] for r in inventory['unplanned_artifacts']}
        self.assertTrue(all('runs/' + relative in rejected for relative in extras))
        self.assertEqual(inventory['observed_record_files'], 2)
        self.assertEqual(inventory['observed_attempt_directories'], 2)

    def test_v1_base_review_schema_and_cli_flags_are_unchanged(self):
        expected = {
            'BASE': 'b864664d1921109d573e51af182faacc1cebb3e02230af62512f83a1463cc2bf',
            'REVIEWS': '41f0cf9c9a468babdf43d1891ca9fc8be6d013d1751445e4530da49bb8341b04',
            'SCHEMA': '8987026152982b172f3d73e5a601063681befe04c38480b1266d88ce9581b833',
            'FLAGS': '4d59b2436b3bae8e14733ac71eac7d86e6abbcdf63b2b6136da856f8e71b9b41'}
        for key, expected_hash in expected.items():
            self.assertEqual(runner.sha(json.dumps(getattr(runner, key), ensure_ascii=False, sort_keys=True)), expected_hash)
        self.assertEqual((runner.MODEL, runner.EFFORT), ('gpt-6-astra', 'ultra'))

    def test_exact_800_schedule_and_two_distinct_first_answers(self):
        jobs = runner.build_schedule(items80())
        self.assertEqual(len(jobs), 800)
        self.assertEqual(len({(j['group_id'], j['procedure']) for j in jobs}), 800)
        self.assertEqual(len({j['group_id'] for j in jobs}), 160)
        for procedure in runner.PROCS:
            self.assertEqual(sum(j['procedure'] == procedure for j in jobs), 160)
        for repeat in [1, 2]:
            self.assertEqual(sum(j['repeat'] == repeat for j in jobs), 400)
        self.assertEqual(jobs, runner.build_schedule(items80()))

    def test_incomplete_or_duplicated_factorial_refused(self):
        for invalid in [items80()[:-1], [items80()[0]] * 80]:
            with self.assertRaises(RuntimeError): runner.build_schedule(invalid)
        bad = items80()
        bad[0] = {**bad[0], 'state': bad[2]['state']}
        with self.assertRaisesRegex(RuntimeError, '5 states'): runner.build_schedule(bad)

    def test_manifest_parameter_file_schedule_and_cli_drift_refused(self):
        self.prepare_freeze()
        path = self.root / 'protocol/frozen.json'
        original = path.read_bytes()
        f = runner.read(path)
        f['execution_config']['effort'] = 'low'
        runner.dump(path, f)
        with self.assertRaisesRegex(RuntimeError, 'parameters'): runner.verify()
        path.write_bytes(original)
        f = runner.read(path)
        f['phase_schedule']['dev']['jobs'][0]['repeat'] = 3
        runner.dump(path, f)
        with self.assertRaisesRegex(RuntimeError, 'schedule'): runner.verify()
        path.write_bytes(original)
        p = self.root / 'keys/dev_keys.json'
        previous = p.read_bytes()
        p.write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'Frozen file'): runner.verify()
        p.write_bytes(previous)
        self.cli.write_text('changed binary')
        with self.assertRaisesRegex(RuntimeError, 'CLI identity'): runner.verify()

    def test_pinned_manifest_rejects_timestamp_only_change(self):
        self.prepare_freeze()
        path = self.root / 'protocol/frozen.json'
        runner.seal_json(self.root / 'runs/dev/manifest_identity.json', {'frozen_hash': runner.file_sha(path)})
        f = runner.read(path)
        f['created_utc'] = 'changed'
        runner.dump(path, f)
        with self.assertRaisesRegex(RuntimeError, 'manifest hash'): runner.verify()

    def test_run_lock_is_checked_before_manifest_or_calls(self):
        with DirectoryLock(self.root / 'runs/dev'), patch.object(runner, 'verify') as verify:
            with self.assertRaises(LockUnavailable): runner.run('dev', 'P0', 1)
        verify.assert_not_called()

    def test_quota_pauses_one_attempt_then_resumes_without_overwrite(self):
        gate = runner.DispatchGate()
        rec, calls = self.respond(service_error(), gate)
        self.assertEqual(calls, 1)
        self.assertTrue(gate.stopped)
        self.assertEqual(rec['status'], 'paused_service')
        self.assertFalse((self.task / 'record.json').exists())
        old = {p.name: p.read_bytes() for p in (self.task / 'attempt_01').iterdir()}
        rec, calls = self.respond(gate=runner.DispatchGate())
        self.assertEqual(calls, 1)
        self.assertEqual(rec['status'], 'complete')
        self.assertEqual(len(rec['attempts']), 2)
        self.assertEqual(old, {p.name: p.read_bytes() for p in (self.task / 'attempt_01').iterdir()})
        _, calls = self.respond()
        self.assertEqual(calls, 0)

    def test_auth_failure_stops_without_immediate_second_request(self):
        gate = runner.DispatchGate()
        rec, calls = self.respond(service_error('Unauthorized: authentication token expired (401)'), gate)
        self.assertEqual(calls, 1)
        self.assertEqual(rec['status'], 'paused_service')
        self.assertEqual(gate.reason, 'authentication')

    def test_tls_eof_and_connection_errors_pause_without_retry_storm(self):
        for message in ['TLS connect error: unexpected EOF', 'error sending request for url',
                        'Network is unreachable', 'stream disconnected before completion']:
            with self.subTest(message=message):
                info = runner.events_info(json.dumps({'type': 'turn.failed', 'error': {'message': message}}))
                self.assertEqual(runner.service_block_reason(info, '', 1), 'network_transport')
        gate = runner.DispatchGate()
        rec, calls = self.respond(service_error('TLS connect error: unexpected EOF'), gate)
        self.assertEqual(calls, 1)
        self.assertEqual(rec['status'], 'paused_service')
        self.assertEqual(gate.reason, 'network_transport')
        rec, calls = self.respond(gate=runner.DispatchGate())
        self.assertEqual(calls, 1)
        self.assertEqual(rec['status'], 'complete')

    def test_quota_second_attempt_is_terminal_no_third_attempt(self):
        self.respond(service_error(), runner.DispatchGate())
        rec, calls = self.respond(service_error(), runner.DispatchGate())
        self.assertEqual(calls, 1)
        self.assertEqual(len(rec['attempts']), 2)
        self.assertEqual(rec['status'], 'technical_failure')
        rec, calls = self.respond()
        self.assertEqual(calls, 0)
        self.assertEqual(rec['status'], 'technical_failure')

    def test_quota_with_final_answer_cannot_be_resampled(self):
        rec, calls = self.respond(service_error(final=VALID), runner.DispatchGate())
        self.assertEqual(calls, 1)
        self.assertEqual(rec['status'], 'protocol_failure')
        self.assertTrue(rec['attempts'][0]['lifecycle_errors'])
        self.assertEqual(rec['raw_final'], VALID)
        again, calls = self.respond()
        self.assertEqual(calls, 0)
        self.assertEqual(again, rec)

    def test_completed_event_answer_without_output_file_is_never_resampled(self):
        events = [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': VALID}}]
        rec, calls = self.respond(fake_call(final=None, extra_events=events, returncode=1))
        self.assertEqual(calls, 1)
        self.assertEqual(rec['status'], 'technical_failure')
        self.assertEqual(rec['raw_final'], VALID)
        again, calls = self.respond()
        self.assertEqual(calls, 0)
        self.assertEqual(again, rec)

    def test_unrecorded_attempt_directory_is_not_silently_ignored(self):
        self.respond()
        (self.task / 'attempt_02').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'Unrecorded attempt'): self.respond()

    def test_ordinary_cli_warning_does_not_trip_breaker(self):
        events = [{'type': 'item.completed', 'item': {'type': 'error',
                   'message': 'Under-development features enabled: skip_host_skill_discovery; skills context budget exceeded'}}]
        gate = runner.DispatchGate()
        rec, calls = self.respond(fake_call(extra_events=events), gate)
        self.assertEqual(rec['status'], 'complete')
        self.assertFalse(gate.stopped)
        self.assertEqual(calls, 1)

    def test_service_text_in_successful_answer_does_not_trip_breaker(self):
        final = json.loads(VALID)
        final['brief_justification'] = 'The supplied document mentions quota and 401, unrelated to transport.'
        gate = runner.DispatchGate()
        rec, _ = self.respond(fake_call(final=json.dumps(final)), gate)
        self.assertEqual(rec['status'], 'complete')
        self.assertFalse(gate.stopped)

    def test_three_worker_breaker_preserves_started_and_stops_dispatch(self):
        self.prepare_freeze()
        barrier = threading.Barrier(3)
        count, guard = [0], threading.Lock()
        def call(cmd, **kwargs):
            with guard:
                count[0] += 1
                index = count[0]
            barrier.wait(timeout=5)
            if index == 1: return service_error()(cmd, **kwargs)
            time.sleep(.06)
            return valid_call(cmd, **kwargs)
        with patch.object(runner.subprocess, 'run', side_effect=call) as mock, contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(runner.run('dev', 'P0', 3))
        self.assertEqual(mock.call_count, 3)
        records = list((self.root / 'runs/dev').glob('*/*/record.json'))
        self.assertEqual(len(records), 2)
        self.assertTrue(all(runner.read(p)['status'] == 'complete' for p in records))
        with patch.object(runner.subprocess, 'run', side_effect=valid_call) as mock, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(runner.run('dev', 'P0', 3))
        self.assertEqual(mock.call_count, 158)
        self.assertEqual(len(list((self.root / 'runs/dev').glob('*/P0/record.json'))), 160)

    def test_runtime_directory_and_unusable_phase_refused(self):
        (self.root / 'runtime_empty').mkdir()
        (self.root / 'runtime_empty/AGENTS.md').write_text('contamination')
        with self.assertRaisesRegex(RuntimeError, 'must remain empty'): self.respond()
        with self.assertRaises(ValueError): runner.run('toy', 'all', 3)
        with self.assertRaises(ValueError): runner.run('dev', 'all', 4)

    def test_review_cannot_run_while_first_pass_paused(self):
        self.prepare_freeze()
        with patch.object(runner.subprocess, 'run') as mock, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'P0 missing or paused'): runner.run('dev', 'review', 1)
        mock.assert_not_called()

    def test_shared_first_literal_and_no_cross_review_content(self):
        first = VALID + '\n'
        for procedure in ['P1', 'P3', 'P7', 'P8']:
            prompt = runner.build_prompt({**self.job, 'procedure': procedure}, self.item, first)
            self.assertIn(first + '\n\n本次任务：\n' + runner.REVIEWS[procedure], prompt)
            self.assertEqual(prompt.count(first), 1)

    def test_full_800_offline_end_to_end_and_zero_call_resume(self):
        self.prepare_freeze()
        with patch.object(runner.subprocess, 'run', side_effect=valid_call) as mock, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(runner.run('dev', 'all', 3))
        self.assertEqual(mock.call_count, 800)
        with patch.object(runner.subprocess, 'run', side_effect=AssertionError('no resampling')) as mock, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(runner.run('dev', 'all', 3))
        mock.assert_not_called()
        with patch.object(evaluate, 'R', self.root), contextlib.redirect_stdout(io.StringIO()):
            result = evaluate.run()
        self.assertEqual(result['planned_tasks'], 800)
        self.assertEqual(result['complete_tasks'], 800)
        self.assertEqual(result['planned_groups'], 160)
        self.assertEqual(result['unique_sessions'], 800)
        self.assertTrue(result['passed_integrity'])
        self.assertEqual(result['family_counts_by_type'], {'material': 4, 'rule': 4})
        self.assertEqual(result['primary_interactions']['I78']['estimate'], 0)
        self.assertIsNone(result['procedures']['P7']['repair_rate'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
