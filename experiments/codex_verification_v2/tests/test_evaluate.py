"""Independent analytic expectations for descriptive family-level scoring."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'harness'))
import evaluate
import runner
from test_v2 import items80


def make_rows():
    result = []
    for item in items80():
        for repeat in [1, 2]:
            for procedure in runner.PROCS:
                result.append({**item, 'repeat': repeat, 'group_id': item['item_id'] + f'_r{repeat}',
                               'procedure': procedure, 'error_type': 'material' if int(item['family_id'][1:]) <= 4 else 'rule',
                               'status': 'complete', 'correct': 1, 'input_tokens': 10,
                               'output_tokens': 5, 'seconds': 1})
    return result


class EvaluateTests(unittest.TestCase):
    def test_usage_requires_nonnegative_integers_and_preserves_partial_subtotals(self):
        invalid = [None, {}, [], '', True, False, -1, 1.5, '17']
        for value in invalid:
            with self.subTest(value=value):
                totals = evaluate.usage_totals([{'usage': {'input_tokens': value, 'output_tokens': 9}}])
                self.assertIsNone(totals['sum_input_tokens'])
                self.assertEqual(totals['known_input_tokens'], 0)
                self.assertEqual(totals['sum_output_tokens'], 9)
                self.assertEqual(totals['input_usage_missing_attempts'], 1)
                self.assertEqual(totals['output_usage_missing_attempts'], 0)
                self.assertEqual(totals['usage_missing_attempts'], 1)
        totals = evaluate.usage_totals([{'usage': {}}, {'usage': {'input_tokens': 17, 'output_tokens': 0}}])
        self.assertIsNone(totals['sum_input_tokens'])
        self.assertIsNone(totals['sum_output_tokens'])
        self.assertEqual(totals['known_input_tokens'], 17)
        self.assertEqual(totals['known_output_tokens'], 0)
        self.assertEqual(evaluate.usage_totals([{'usage': {'input_tokens': 0, 'output_tokens': 0}}])['sum_input_tokens'], 0)

    def test_procedure_usage_never_reports_unknown_as_zero(self):
        rows = make_rows()
        p0 = next(r for r in rows if r['procedure'] == 'P0')
        p0.update(input_tokens=17, output_tokens='', known_input_tokens=17, known_output_tokens=0,
                  input_usage_missing_attempts=0, output_usage_missing_attempts=1, usage_missing_attempts=1)
        result = evaluate.summarize(rows)['procedures']['P0']
        self.assertEqual(result['input_tokens'], 1607)
        self.assertEqual(result['sum_input_tokens'], 1607)
        self.assertIsNone(result['output_tokens'])
        self.assertIsNone(result['sum_output_tokens'])
        self.assertEqual(result['known_output_tokens'], 795)
        self.assertEqual(result['usage_known_tasks'], 159)
        self.assertEqual(result['output_usage_missing_attempts'], 1)

    def test_ceiling_zero_interaction_is_computable_but_repair_is_na(self):
        result = evaluate.summarize(make_rows())
        self.assertEqual(result['primary_interactions']['I78']['estimate'], 0)
        self.assertEqual(result['secondary_interaction_I73']['estimate'], 0)
        self.assertIsNone(result['procedures']['P7']['repair_rate'])
        self.assertEqual(result['procedures']['P7']['natural_first_errors'], 0)
        self.assertTrue(result['difficulty_diagnostic']['complete_P0_present_ceiling'])
        self.assertEqual(result['primary_interactions']['I78']['available_families_by_type'], {'material': 4, 'rule': 4})

    def test_interaction_sign_is_rule_minus_material(self):
        rows = make_rows()
        for row in rows:
            if row['procedure'] == 'P8' and row['error_type'] == 'rule' and evaluate.eligible(row, 'present_flawed'):
                row['correct'] = 0
        result = evaluate.summarize(rows)
        self.assertEqual(result['primary_interactions']['I78']['estimate'], 1)
        self.assertEqual(result['secondary_interaction_I73']['estimate'], 0)
        self.assertEqual(result['secondary_interactions']['aligned']['I78']['estimate'], 0)
        self.assertEqual(result['secondary_interactions']['missing']['I78']['estimate'], 0)

    def test_families_equal_weight_even_with_unequal_group_counts(self):
        rows = [r for r in make_rows() if r['family_id'] != 'F01' or r['state'] == 'base' and r['repeat'] == 1]
        for row in rows:
            if row['family_id'] == 'F01' and row['procedure'] == 'P8': row['correct'] = 0
        result = evaluate.summarize(rows)
        self.assertEqual(result['primary_interactions']['I78']['estimate'], -.25)
        self.assertEqual(result['primary_interactions']['I78']['type_mean_difference']['material'], .25)

    def test_failed_reviews_remain_in_full_denominator_and_pair_sensitivity_is_separate(self):
        rows = make_rows()
        for row in rows:
            if row['family_id'] == 'F01' and row['procedure'] == 'P8' and evaluate.eligible(row, 'present_flawed'):
                row['status'], row['correct'] = 'technical_failure', 0
        result = evaluate.summarize(rows)
        self.assertEqual(result['procedures']['P8']['planned'], 160)
        self.assertEqual(result['procedures']['P8']['complete'], 152)
        self.assertEqual(result['procedures']['P8']['accuracy'], 152 / 160)
        self.assertEqual(result['primary_interactions']['I78']['estimate'], -.25)
        self.assertEqual(result['complete_pair_sensitivity']['I78']['estimate'], 0)
        self.assertEqual(result['complete_pair_sensitivity']['I78']['available_families_by_type']['material'], 3)

    def test_repair_and_damage_use_natural_first_answers(self):
        rows = make_rows()
        target = rows[0]['group_id']
        for row in rows:
            if row['group_id'] == target and row['procedure'] == 'P0': row['correct'] = 0
        result = evaluate.summarize(rows)
        self.assertEqual(result['procedures']['P7']['natural_first_errors'], 1)
        self.assertEqual(result['procedures']['P7']['repair_rate'], 1)
        self.assertEqual(result['procedures']['P7']['damage_rate'], 0)
        for row in rows:
            if row['group_id'] == target and row['procedure'] == 'P0': row['status'] = 'parse_failure'
        result = evaluate.summarize(rows)
        self.assertEqual(result['procedures']['P7']['natural_first_errors'], 0)
        self.assertIsNone(result['procedures']['P7']['repair_rate'])

    def test_missing_group_procedure_and_mixed_family_type_rejected(self):
        with self.assertRaisesRegex(ValueError, 'all five procedures'): evaluate.summarize(make_rows()[1:])
        rows = make_rows()
        rows[0]['error_type'] = 'rule'
        with self.assertRaisesRegex(ValueError, 'one known'): evaluate.summarize(rows)


if __name__ == '__main__':
    unittest.main(verbosity=2)
