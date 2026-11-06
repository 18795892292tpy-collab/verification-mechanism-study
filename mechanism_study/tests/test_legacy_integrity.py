"""Offline regression tests. Only the in-process/CLI mock backend is exercised."""
import copy
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "harness"))
import runner
from audit_results import audit_folder
from branch_integrity import DirectoryLock, IntegrityError, read_records, select_branches, select_run, validate_resume
from scorer import COLUMNS, load_verified_branch_rows, score_directory


class BranchSelectionTests(unittest.TestCase):
    def setUp(self):
        self.fams = {f["family_id"]: f for f in runner.cl.load_dir(STUDY / "cases/dev")}
        self.group = [{"run_id": p, "family_id": "F01", "state": "base", "advice": "flawed", "procedure": p, "repeat": 1, "order": n}
                      for n, p in enumerate(("P0", "P1", "P3"))]

    def branch(self, seed=1, finished="2026-11-07T01:00:00+00:00"):
        records = runner.execute_branch(self.group, self.fams, runner.Mock(4000, seed))
        for r in records:
            r["finished"] = finished
        return records

    def select(self, *branches):
        return select_branches(self.group, list(enumerate([r for b in branches for r in b], 1)))

    def test_earliest_completed_whole_branch_not_last_successful_rows(self):
        early = self.branch(1)
        late = self.branch(2, "2026-11-07T02:00:00+00:00")
        selected, audit = self.select(late, early)
        self.assertEqual({r["branch_id"] for r in selected.values()}, {early[0]["branch_id"]})
        self.assertEqual(audit["duplicate_group_count"], 1)

    def test_incomplete_retry_cannot_contaminate_complete_branch(self):
        complete = self.branch(1)
        retry = self.branch(2, "2026-11-07T02:00:00+00:00")
        retry[-1]["status"] = "error"
        retry[-1]["calls"][-1]["ok"] = False
        selected, _ = self.select(complete, retry)
        self.assertEqual({r["branch_id"] for r in selected.values()}, {complete[0]["branch_id"]})
        # Successful rows from two partial branches must not synthesize a completion.
        complete[0]["status"] = "error"
        self.assertEqual(self.select(complete, retry)[0], {})

    def test_same_action_different_full_text_and_review_replay_rejected(self):
        branch = copy.deepcopy(self.branch())
        branch[1]["calls"][0] = copy.deepcopy(branch[1]["calls"][0])
        branch[1]["calls"][0]["text"] += "\nDifferent rationale, same action."
        self.assertFalse(self.select(branch)[0])
        branch = copy.deepcopy(self.branch())
        branch[1]["calls"][1]["messages_appended"][0]["content"] += " changed"
        self.assertFalse(self.select(branch)[0])

    def test_transport_success_parse_failure_and_truncation_are_not_resampled(self):
        branch = self.branch()
        branch[1]["calls"][-1].update(text="unparseable", finish_reason="length")
        selected, _ = self.select(branch)
        self.assertEqual(len(selected), 3)

    def test_duplicate_member_or_unknown_id_audited(self):
        branch = self.branch()
        self.assertFalse(self.select(branch + [copy.deepcopy(branch[0])])[0])
        unknown = {"run_id": "unknown", "status": "error"}
        selected, audit = self.select(branch, [unknown])
        self.assertEqual(len(selected), 3)
        self.assertEqual(audit["unknown_run_id_lines"], [4])


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name) / "run"
        self.args = ["runner", "--cases", str(STUDY / "cases/dev"), "--out", str(self.directory),
                     "--backend", "mock", "--families", "F01", "--procedures", "P0,P1,P3", "--repeats", "1", "--branching", "--limit", "2"]

    def tearDown(self):
        self.tmp.cleanup()

    def run_mock(self, *extra):
        with patch.object(sys, "argv", self.args + list(extra)), patch.object(runner.OpenAICompatible, "chat", side_effect=AssertionError("network backend forbidden")):
            return runner.main()

    def test_resume_skip_complete_and_verify_manifest_without_mutating_raw(self):
        self.assertEqual(self.run_mock(), 0)
        before = (self.directory / "responses.jsonl").read_bytes()
        manifests_before = len(list(self.directory.glob("manifest_*.json")))
        for flag, value in (("--max-tokens", "1234"), ("--repeats", "2"), ("--system", "plain"), ("--seed", "4")):
            self.assertEqual(self.run_mock(flag, value), 3)
            self.assertEqual((self.directory / "responses.jsonl").read_bytes(), before)
        self.assertEqual(len(list(self.directory.glob("manifest_*.json"))), manifests_before)
        self.assertEqual(self.run_mock(), 0)
        self.assertEqual(select_run(self.directory)[2]["unique_complete_groups"], 4)
        self.assertEqual(select_run(self.directory)[2]["duplicate_group_count"], 0)

    def test_legacy_manifest_resume_compatible_but_conflicts_refused(self):
        self.assertEqual(self.run_mock(), 0)
        path = next(self.directory.glob("manifest_*.json"))
        manifest = json.loads(path.read_text())
        for key in ("integrity_version", "review_text_sha256", "plan_sha256"):
            manifest.pop(key)
        manifest["code_files"]["runner.py"] = "legacy-runner-version"
        path.write_text(json.dumps(manifest))
        self.assertEqual(self.run_mock(), 0)
        manifest["case_files"]["F01.json"] = "changed-case"
        path.write_text(json.dumps(manifest))
        before = (self.directory / "responses.jsonl").read_bytes()
        self.assertEqual(self.run_mock(), 3)
        self.assertEqual((self.directory / "responses.jsonl").read_bytes(), before)

    def test_csv_raw_verification_rejects_stale_hash_and_reads_legacy_columns(self):
        self.run_mock()
        rows, _, _ = score_directory(self.directory, STUDY / "cases/dev")
        path = self.directory / "scored_runs.csv"
        def write(columns):
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        write(COLUMNS[:-3])
        self.assertEqual(len(load_verified_branch_rows(path, STUDY / "cases/dev")), 6)
        rows[0]["first_text_sha256"] = "tampered"
        write(COLUMNS)
        with self.assertRaises(IntegrityError):
            load_verified_branch_rows(path, STUDY / "cases/dev")

    def test_audit_counts_actual_calls_once_and_cost_is_na_without_prices(self):
        self.run_mock()
        audit = audit_folder(self.directory)
        self.assertEqual(audit["unique_complete_groups"], 2)
        self.assertEqual(audit["observed_unique_calls"], 6)
        self.assertIsNone(audit["cost"]["total"])
        self.assertIsNone(audit["cost"]["recorded_call_subtotal"])

    def test_price_and_usage_are_required_and_unlogged_retries_make_total_na(self):
        self.run_mock()
        path = self.directory / "responses.jsonl"
        records = [r for _, r in read_records(path)[0]]
        for r in records:
            for c in r["calls"]:
                c["usage"]["prompt_cache_hit_tokens"] = 0
        def write():
            path.write_text("".join(json.dumps(r) + "\n" for r in records))
        write()
        prices = {"currency": "fixture-only", "source": "offline test fixture, not a provider quote", "models": {"mock":
                  {"prompt_uncached_per_million": 1, "prompt_cached_per_million": 0, "completion_per_million": 2}}}
        audit = audit_folder(self.directory, prices)
        self.assertEqual(audit["cost"]["priced_calls"], 6)
        self.assertGreater(audit["cost"]["total"], 0)
        records[1]["calls"][-1]["attempts"] = 2
        write()
        self.assertIsNone(audit_folder(self.directory, prices)["cost"]["total"])

    def test_nonbranching_history_retains_legacy_selection(self):
        self.args.remove("--branching")
        self.assertEqual(self.run_mock(), 0)
        _, selected, audit, _, _ = select_run(self.directory)
        self.assertEqual(len(selected), 2)
        self.assertFalse(audit["branching"])
        self.assertEqual(audit["selection_policy"], "legacy_nonbranching_latest_ok")

    def test_resume_refuses_tampered_plan(self):
        self.run_mock()
        path = self.directory / "plan.csv"
        plan = runner.read_plan(path)
        plan[0]["run_id"] = "different-id"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=runner.PLAN_FIELDS)
            writer.writeheader()
            writer.writerows(plan)
        self.assertEqual(self.run_mock(), 3)

    def test_malformed_tail_refuses_resume(self):
        self.run_mock()
        path = self.directory / "responses.jsonl"
        with path.open("a") as f:
            f.write('{"run_id":')
        before = path.read_bytes()
        self.assertEqual(self.run_mock(), 3)
        self.assertEqual(path.read_bytes(), before)


class ProcessLockTests(unittest.TestCase):
    def test_second_process_refused_then_acquires_after_release(self):
        with tempfile.TemporaryDirectory() as directory:
            code = "from branch_integrity import DirectoryLock\nimport sys\nwith DirectoryLock(sys.argv[1]): print('acquired')"
            env = dict(os.environ, PYTHONPATH=str(STUDY / "harness"))
            with DirectoryLock(directory):
                result = subprocess.run([sys.executable, "-c", code, directory], env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("locked by another writer", result.stderr)
            result = subprocess.run([sys.executable, "-c", code, directory], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
