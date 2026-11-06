"""Full CLI regressions on explicitly synthetic, offline Mock responses.

Requires the repository's scipy dependency for branch_pooled. No provider,
credentials or historical files are used for fixture generation.
"""
import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "harness"))
import runner


class ScriptedMock(runner.Mock):
    def __init__(self, actions):
        super().__init__(4000)
        self.actions = iter(actions)

    def chat(self, messages):
        response = super().chat(messages)
        response["text"] = json.dumps({"action": next(self.actions), "cited_sources": [],
                                       "rationale": "Offline regression fixture; not experimental evidence."})
        return response


@unittest.skipUnless(importlib.util.find_spec("scipy"), "full report integration requires scipy")
class ReportIntegrationTests(unittest.TestCase):
    def command(self, *args):
        result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result.stdout

    def reports(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fams = {f["family_id"]: f for f in runner.cl.load_dir(STUDY / "cases/dev")}
            pooled_args = []
            single_reports = []
            for family in ("F01", "F02"):
                folder = root / family
                folder.mkdir()
                plan, records = [], []
                state = "missing" if mode == "missing_only" else "base"
                key = runner.cl.key_of(fams[family], state)
                wrong = next(a for a in runner.cl.state_view(fams[family], state)["options"] if a != key)
                for advice in ("aligned", "flawed"):
                    group = [{"run_id": f"{family}-{advice}-{p}", "family_id": family, "state": state,
                              "advice": advice, "procedure": p, "repeat": 1, "order": len(plan) + n}
                             for n, p in enumerate(("P0", "P1", "P3"))]
                    if mode in ("all_correct", "missing_only"):
                        actions = [key, key, key]
                    elif mode == "all_wrong_tied":
                        actions = [wrong, wrong, wrong]
                    elif mode == "all_repaired_tied":
                        actions = [wrong, key, key]
                    elif mode == "discordant":
                        actions = [wrong, key, wrong] if family == "F01" else [wrong, wrong, key]
                    else:
                        raise AssertionError(mode)
                    records.extend(runner.execute_branch(group, fams, ScriptedMock(actions)))
                    plan.extend(group)
                with (folder / "plan.csv").open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=runner.PLAN_FIELDS)
                    writer.writeheader()
                    writer.writerows(plan)
                (folder / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
                (folder / "manifest_fixture.json").write_text(json.dumps({"branching": True,
                    "backend": "mock", "params": runner.Mock(4000).params(), "procedures": ["P0", "P1", "P3"]}))
                self.command(STUDY / "harness/scorer.py", folder, "--cases", STUDY / "cases/dev")
                scored = folder / "scored_runs.csv"
                single_reports.append(self.command(STUDY / "analysis/branch_report.py", scored, "--cases", STUDY / "cases/dev"))
                pooled_args.extend(["--run", scored, STUDY / "cases/dev"])
            self.command(STUDY / "analysis/branch_pooled.py", *pooled_args, "--out", root / "pooled")
            pooled = (root / "pooled/pooled_report.md").read_text()
            for report in [*single_reports, pooled]:
                self.assertNotIn("nan", report.lower())
                self.assertIn("not evidence", report)
            return single_reports, pooled

    def test_no_natural_errors_reports_unestimable_repairs_and_tests(self):
        singles, pooled = self.reports("all_correct")
        for text in [*singles, pooled]:
            self.assertIn("| P1 | 0/0 | NA |", text)
            self.assertNotIn("| 0/0 | 0.00", text)
            self.assertNotIn("1.000", text)
        contrast = next(line for line in pooled.splitlines() if line.startswith("| P3 vs P1 |"))
        self.assertIn("| NA | NA | NA |", contrast)
        self.assertIn("sign p NA", contrast)

    def test_all_wrong_has_zero_damage_denominator_but_measured_zero_repair(self):
        singles, pooled = self.reports("all_wrong_tied")
        for text in [*singles, pooled]:
            self.assertIn("0.00 [", text)
            self.assertIn("| 0/0 | NA |", text)
            self.assertNotIn("1.000", text)
        self.assertIn("+0.000 [NA]", pooled)

    def test_missing_only_has_no_present_accuracy_denominator(self):
        singles, pooled = self.reports("missing_only")
        self.assertIn("| P0 | 0/0 = NA | 0/0 = NA |", pooled)
        for text in [*singles, pooled]:
            self.assertIn("| P1 | 0/0 | NA | 0/0 | NA |", text)
            self.assertNotIn("1.000", text)

    def test_observed_equal_repairs_are_kept_but_zero_difference_tests_are_na(self):
        singles, pooled = self.reports("all_repaired_tied")
        for text in [*singles, pooled]:
            self.assertIn("1.00 [", text)
            self.assertNotIn("1.000", text)
        self.assertIn("+0.000 [NA]", pooled)
        self.assertIn("sign p NA", pooled)

    def test_real_discordance_preserves_legitimate_p_equal_one(self):
        _, pooled = self.reports("discordant")
        contrast = next(line for line in pooled.splitlines() if line.startswith("| P3 vs P1 |"))
        self.assertIn("sign p 1.000", contrast)
        self.assertIn("2 : 2 (1.000)", contrast)
        self.assertNotIn("[NA]", contrast)


if __name__ == "__main__":
    unittest.main()
