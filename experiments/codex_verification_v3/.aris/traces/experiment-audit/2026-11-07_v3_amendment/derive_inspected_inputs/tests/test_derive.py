"""Offline, outcome-independent regression tests. Never calls a CLI or model."""
from pathlib import Path
import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('posthoc_derive', HERE / 'derive.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = d.read(d.ROOT / 'protocol/output_schema.json')
        cls.record_path = next((d.ROOT / 'runs/p0').glob('*/*/record.json'))
        cls.meta = d.read(cls.record_path.parent / 'attempt_01/meta.json')
        cls.events = d.parse_events((cls.record_path.parent / 'attempt_01/events.jsonl').read_text())
        cls.response = (cls.record_path.parent / 'attempt_01/response.json').read_text()
        cls.stderr = (cls.record_path.parent / 'attempt_01/stderr.txt').read_text()

    def classify(self, events=None, meta=None, response=None, stderr=None):
        return d.classify_observed(meta if meta is not None else self.meta, events if events is not None else self.events,
                                  self.response if response is None else response, self.stderr if stderr is None else stderr, self.schema)

    def test_exact_observed_diagnostics_accepted(self):
        self.assertTrue(self.classify()['accepted'])

    def test_unknown_error_added_is_not_waived(self):
        events = copy.deepcopy(self.events)
        events['error_items'].append({'id': 'item_99', 'type': 'error', 'message': 'fatal response transport failed'})
        self.assertFalse(self.classify(events=events)['accepted'])

    def test_known_error_message_suffix_not_accepted(self):
        events = copy.deepcopy(self.events); events['error_items'][0]['message'] += ' plus fatal transport failure'
        self.assertFalse(self.classify(events=events)['accepted'])

    def test_known_diagnostic_object_extra_field_not_accepted(self):
        events = copy.deepcopy(self.events); events['error_items'][0]['severity'] = 'fatal'
        self.assertFalse(self.classify(events=events)['accepted'])

    def test_missing_or_duplicate_known_error_not_accepted(self):
        for replacement in [self.events['error_items'][:-1], self.events['error_items'] + [self.events['error_items'][0]]]:
            events = copy.deepcopy(self.events); events['error_items'] = replacement
            self.assertFalse(self.classify(events=events)['accepted'])

    def test_third_warning_before_turn_is_not_observed_signature(self):
        events = copy.deepcopy(self.events)
        events['pattern'][3], events['pattern'][4] = events['pattern'][4], events['pattern'][3]
        self.assertFalse(self.classify(events=events)['accepted'])

    def test_top_error_unknown_event_and_tool_are_rejected(self):
        for key in ['top_errors', 'unusual']:
            events = copy.deepcopy(self.events); events[key] = [{'type': 'command_execution'}]
            self.assertFalse(self.classify(events=events)['accepted'])

    def test_final_conflict_and_empty_output_are_rejected(self):
        self.assertFalse(self.classify(response='')['accepted'])
        parsed = json.loads(self.response); parsed['action'] = next(x for x in 'ABCD' if x != parsed['action'])
        self.assertFalse(self.classify(response=json.dumps(parsed, ensure_ascii=False))['accepted'])

    def test_raw_byte_hash_conflict_is_not_hidden_by_text_normalization(self):
        meta = copy.deepcopy(self.meta); meta['output_sha256'] = d.digest(self.response + '\r\n')
        self.assertFalse(self.classify(meta=meta)['accepted'])

    def test_invalid_schema_is_not_repaired(self):
        events = copy.deepcopy(self.events); events['messages'] = ['not-json']
        self.assertFalse(self.classify(events=events, response='not-json')['accepted'])

    def test_zero_exit_does_not_override_stderr_or_metadata_failure(self):
        self.assertFalse(self.classify(stderr='ERROR connection reset')['accepted'])
        for key, value in [('returncode', 1), ('returncode', False), ('error', 'timeout'), ('service_block', 'network_transport')]:
            meta = copy.deepcopy(self.meta); meta[key] = value
            self.assertFalse(self.classify(meta=meta)['accepted'])

    def test_duplicate_session_rejected(self):
        with self.assertRaisesRegex(d.AuditError, 'Duplicate session'):
            d.assert_unique_sessions(['same', 'same'])

    def test_lifecycle_missing_or_double_turn_rejected(self):
        for lifecycle in [[], self.events['lifecycle'] + ['turn.completed']]:
            events = copy.deepcopy(self.events); events['lifecycle'] = lifecycle
            self.assertFalse(self.classify(events=events)['accepted'])

    def test_missing_usage_stays_unknown(self):
        result = d.usage_summary([{'input_tokens': 12, 'output_tokens': 3}, {'input_tokens': None, 'output_tokens': 0}])
        self.assertIsNone(result['sum_input_tokens']); self.assertEqual(result['known_input_tokens'], 12)
        self.assertEqual(result['sum_output_tokens'], 3)
        self.assertIsNone(d.usage_summary([{'input_tokens': True, 'output_tokens': -1}])['sum_input_tokens'])

    def test_raw_change_detected_on_explicit_offline_fixture(self):
        frozen = d.read(d.ROOT / 'protocol/frozen.json')
        job = next(j for j in frozen['phase_schedule']['p0']['jobs'] if j['group_id'] == self.record_path.parent.parent.name)
        item = next(i for i in d.read(d.ROOT / 'prompts/p0_items.json') if i['item_id'] == job['item_id'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / 'runs/p0' / job['group_id'] / 'P0'
            shutil.copytree(self.record_path.parent, target)
            (target / 'attempt_01/response.json').write_text('changed')
            with self.assertRaisesRegex(d.AuditError, 'Raw hash mismatch'):
                d.validate_task(root, job, item, d.read(d.ROOT / 'protocol/prompts.json'), self.schema, d.timestamp(frozen['created_utc']))

    def test_canonical_readonly_derivation_preserves_every_original_input(self):
        frozen = d.read(d.ROOT / 'protocol/frozen.json'); before = d.inventory(d.ROOT, frozen)
        with d.quiescent_original_runs():
            result = d.derive()
        self.assertEqual(before, d.inventory(d.ROOT, frozen))
        self.assertEqual(result['summary']['actual_cli_attempts'], 80)
        self.assertEqual(result['summary']['derived_transport_accepted'], 80)
        self.assertEqual(result['summary']['original_status_counts'], {'technical_failure': 80})
        self.assertEqual(result['summary']['original_gate_status'], 'technical_block')
        self.assertFalse(result['summary']['original_challenge_allowed'])
        self.assertFalse(result['threshold_diagnostic']['automatic_execution_authorized'])
        self.assertTrue(result['threshold_diagnostic']['NOT_A_RUN_GATE'])
        self.assertEqual(result['summary']['new_model_calls_by_this_script'], 0)

    def test_readonly_lock_refuses_link_and_preserves_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'runs').mkdir(); target = root / 'sentinel'; target.write_text('original')
            (root / 'runs/.integrity.lock').symlink_to(target)
            with self.assertRaises(OSError):
                with d.quiescent_original_runs(root):
                    self.fail('unsafe lock acquired')
            self.assertEqual(target.read_text(), 'original')

    def test_readonly_lock_refuses_active_writer_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'runs').mkdir(); lock = root / 'runs/.integrity.lock'; lock.write_text('writer state')
            with lock.open('r+') as writer:
                d.fcntl.flock(writer.fileno(), d.fcntl.LOCK_EX | d.fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    with d.quiescent_original_runs(root):
                        self.fail('read lock acquired while writer active')
            self.assertEqual(lock.read_text(), 'writer state')


class ThresholdTests(unittest.TestCase):
    def rows(self):
        rows = []
        for kind in ['material', 'rule']:
            for family in range(4):
                for state in ['base', 'decisive_change', 'irrelevant', 'paraphrase', 'missing']:
                    for advice in ['aligned', 'flawed']:
                        wrong = state == 'base' and advice == 'flawed'
                        rows.append({'error_type': kind, 'family_id': kind + str(family), 'state': state, 'advice': advice,
                                     'derived_status': 'accepted_exact_diagnostics', 'derived_correct': int(not wrong)})
        return rows

    def test_threshold_pass_still_has_no_execution_authorization(self):
        result = d.threshold_diagnostic(self.rows(), True)
        self.assertEqual(result['hypothetical_threshold_status'], 'eligible_for_independent_holdout')
        self.assertFalse(result['automatic_execution_authorized']); self.assertFalse(result['original_challenge_allowed'])
        self.assertEqual(result['criteria']['rule']['observed']['natural_errors'], 4)

    def test_rejected_rows_do_not_become_natural_errors_and_force_block(self):
        rows = self.rows(); rows[1]['derived_status'] = 'rejected'; rows[1]['derived_correct'] = 0
        result = d.threshold_diagnostic(rows, False)
        self.assertEqual(result['hypothetical_threshold_status'], 'technical_block')
        self.assertEqual(result['criteria']['material']['observed']['natural_errors'], 3)

    def test_error_coverage_and_control_floors_both_required(self):
        rows = self.rows()
        for r in rows:
            if r['error_type'] == 'rule' and r['state'] == 'missing':
                r['derived_correct'] = 0
        result = d.threshold_diagnostic(rows, True)
        self.assertEqual(result['hypothetical_threshold_status'], 'development_gate_failed')
        self.assertFalse(result['criteria']['rule']['missing_accuracy_floor'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
