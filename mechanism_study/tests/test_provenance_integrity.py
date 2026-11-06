"""Offline regressions for PR #4 prompt/case/plan identity findings.

Every fixture is produced by the real runner using its Mock backend and complete
manifest. Only temporary fixture files are changed; original cases/results are
read-only. Network-backend use is an assertion failure.
"""
import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "harness"))
import runner
from branch_integrity import IntegrityError, digest, select_run
from scorer import COLUMNS, score_directory


class ProvenanceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="legacy-provenance-test-")
        self.root = Path(self.tmp.name)
        self.cases = self.root / "cases"
        self.cases.mkdir()
        for name in ("F01.json", "F02.json"):
            (self.cases / name).write_bytes((STUDY / "cases/dev" / name).read_bytes())
        self.sequence = 0

    def tearDown(self):
        self.tmp.cleanup()

    def fixture(self, families="F01,F02"):
        self.sequence += 1
        directory = self.root / f"run-{self.sequence}"
        argv = ["runner", "--cases", str(self.cases), "--out", str(directory),
                "--backend", "mock", "--families", families, "--procedures", "P0,P1,P3",
                "--repeats", "1", "--branching", "--limit", "1", "--concurrency", "1"]
        with patch.object(sys, "argv", argv), patch.object(
                runner.OpenAICompatible, "chat", side_effect=AssertionError("network backend forbidden")):
            self.assertEqual(runner.main(), 0)
        # Positive control: a real manifest's integer plan hash must survive CSV loading.
        self.assertEqual(len(score_directory(directory, self.cases)[0]), 3)
        self.assertEqual(select_run(directory)[2]["unique_complete_groups"], 1)
        return directory

    @staticmethod
    def read_plan(directory):
        with (directory / "plan.csv").open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def write_plan(directory, plan):
        with (directory / "plan.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=runner.PLAN_FIELDS)
            writer.writeheader()
            writer.writerows(plan)

    @staticmethod
    def update_manifests(directory, mutate):
        for path in directory.glob("manifest_*.json"):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            mutate(manifest)
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def legacy_manifest(cls, directory):
        def mutate(manifest):
            for name in ("integrity_version", "plan_sha256", "review_text_sha256"):
                manifest.pop(name, None)
        cls.update_manifests(directory, mutate)

    @staticmethod
    def observed_plan_row(directory, plan):
        first = json.loads((directory / "responses.jsonl").read_text(encoding="utf-8").splitlines()[0])
        return next(row for row in plan if row["run_id"] == first["run_id"])

    def assert_scoring_refused_without_raw_change(self, directory):
        path = directory / "responses.jsonl"
        before = path.read_bytes()
        with self.assertRaises(IntegrityError):
            score_directory(directory, self.cases)
        self.assertEqual(path.read_bytes(), before)

    def test_current_plan_hash_is_verified_by_offline_read_and_scoring(self):
        directory = self.fixture()
        plan = self.read_plan(directory)
        # A pure order change leaves membership, prompt and answer keys untouched.
        # This must fail because of the stored full-plan hash, not a scoring effect.
        plan[0]["order"], plan[1]["order"] = plan[1]["order"], plan[0]["order"]
        self.write_plan(directory, plan)
        with self.assertRaises(IntegrityError):
            select_run(directory)
        self.assert_scoring_refused_without_raw_change(directory)

    def test_legacy_family_relabel_is_detected_from_raw_prompt(self):
        directory = self.fixture()
        self.legacy_manifest(directory)
        plan = self.read_plan(directory)
        for row in plan:
            row["family_id"] = {"F01": "F02", "F02": "F01"}[row["family_id"]]
        self.write_plan(directory, plan)
        self.assert_scoring_refused_without_raw_change(directory)

    def test_legacy_state_relabel_is_detected_from_raw_prompt(self):
        directory = self.fixture()
        self.legacy_manifest(directory)
        plan = self.read_plan(directory)
        source = self.observed_plan_row(directory, plan)["state"]
        other = next(state for state in runner.cl.STATES if state != source)
        swap = {source: other, other: source}
        for row in plan:
            row["state"] = swap.get(row["state"], row["state"])
        self.write_plan(directory, plan)
        self.assert_scoring_refused_without_raw_change(directory)

    def test_legacy_advice_relabel_is_detected_from_raw_prompt(self):
        directory = self.fixture()
        self.legacy_manifest(directory)
        plan = self.read_plan(directory)
        for row in plan:
            row["advice"] = {"aligned": "flawed", "flawed": "aligned"}[row["advice"]]
        self.write_plan(directory, plan)
        self.assert_scoring_refused_without_raw_change(directory)

    def test_legacy_unobserved_group_cannot_be_deleted_to_shrink_denominator(self):
        directory = self.fixture()
        self.legacy_manifest(directory)
        plan = self.read_plan(directory)
        observed = self.observed_plan_row(directory, plan)
        key = lambda row: tuple(row[k] for k in ("family_id", "state", "advice", "repeat"))
        deleted = next(key(row) for row in plan if key(row) != key(observed))
        plan = [row for row in plan if key(row) != deleted]
        # Keep valid order integers so failure specifically concerns plan membership.
        for order, row in enumerate(plan):
            row["order"] = order
        self.write_plan(directory, plan)
        self.assert_scoring_refused_without_raw_change(directory)

    def test_case_answer_key_drift_is_rejected_even_when_visible_prompt_unchanged(self):
        directory = self.fixture()
        row = self.observed_plan_row(directory, self.read_plan(directory))
        path = self.cases / (row["family_id"] + ".json")
        family = json.loads(path.read_text(encoding="utf-8"))
        state = family["states"][row["state"]]
        state["key_action"] = next(a for a in runner.cl.state_view(family, row["state"])["options"]
                                   if a != state["key_action"])
        path.write_text(json.dumps(family, ensure_ascii=False), encoding="utf-8")
        self.assert_scoring_refused_without_raw_change(directory)

    def test_case_text_drift_is_rejected(self):
        directory = self.fixture()
        row = self.observed_plan_row(directory, self.read_plan(directory))
        path = self.cases / (row["family_id"] + ".json")
        family = json.loads(path.read_text(encoding="utf-8"))
        family["states"][row["state"]]["context"] = "Changed offline fixture context."
        path.write_text(json.dumps(family, ensure_ascii=False), encoding="utf-8")
        self.assert_scoring_refused_without_raw_change(directory)

    def test_same_directory_semantic_code_hash_conflicts_are_rejected(self):
        for code_file in ("procedures.py", "caselib.py"):
            with self.subTest(code_file=code_file):
                directory = self.fixture()
                manifest = json.loads(next(directory.glob("manifest_*.json")).read_text(encoding="utf-8"))
                manifest["code_files"][code_file] = "0" * 64
                (directory / "manifest_zz_conflict.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(IntegrityError):
                    select_run(directory)
                self.assert_scoring_refused_without_raw_change(directory)

    def test_same_directory_review_hash_conflicts_are_rejected(self):
        directory = self.fixture()
        manifest = json.loads(next(directory.glob("manifest_*.json")).read_text(encoding="utf-8"))
        manifest["review_text_sha256"]["P1"] = "0" * 64
        (directory / "manifest_zz_conflict.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(IntegrityError):
            select_run(directory)
        self.assert_scoring_refused_without_raw_change(directory)

    def test_runner_code_hash_change_remains_a_supported_integrity_fix(self):
        directory = self.fixture()
        manifest = json.loads(next(directory.glob("manifest_*.json")).read_text(encoding="utf-8"))
        manifest["code_files"]["runner.py"] = "0" * 64
        (directory / "manifest_zz_safe_runner_fix.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(select_run(directory)[2]["manifest_conflicts"], [])
        self.assertEqual(len(score_directory(directory, self.cases)[0]), 3)

    def test_unknown_semantic_source_is_explicitly_refused(self):
        directory = self.fixture()
        self.legacy_manifest(directory)
        self.update_manifests(directory, lambda manifest: manifest["code_files"].update({"procedures.py": "9" * 64}))
        with self.assertRaisesRegex(IntegrityError, "Unverifiable semantic source"):
            score_directory(directory, self.cases)

    def test_new_manifest_cannot_silently_downgrade_by_dropping_plan_hash(self):
        directory = self.fixture()
        self.update_manifests(directory, lambda m: m.pop("plan_sha256"))
        with self.assertRaisesRegex(IntegrityError, "silent legacy downgrade"):
            select_run(directory)

    def test_resume_legacy_relabel_is_refused_before_any_manifest_or_raw_write(self):
        directory = self.fixture()
        self.legacy_manifest(directory)
        plan = self.read_plan(directory)
        for row in plan:
            row["family_id"] = {"F01": "F02", "F02": "F01"}[row["family_id"]]
        self.write_plan(directory, plan)
        protected = {p.name: p.read_bytes() for p in directory.iterdir() if p.name != ".runner.lock"}
        argv = ["runner", "--cases", str(self.cases), "--out", str(directory), "--backend", "mock",
                "--families", "F01,F02", "--procedures", "P0,P1,P3", "--repeats", "1", "--branching", "--limit", "1", "--concurrency", "1"]
        with patch.object(sys, "argv", argv), patch.object(runner.Mock, "chat", side_effect=AssertionError("must refuse before any call")):
            self.assertEqual(runner.main(), 3)
        self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir() if p.name != ".runner.lock"}, protected)

    def test_legacy_identical_prompts_cannot_prove_distinct_family_labels(self):
        family = json.loads((self.cases / "F01.json").read_text())
        family["family_id"] = "F02"
        (self.cases / "F02.json").write_text(json.dumps(family, ensure_ascii=False))
        directory = self.fixture()
        self.legacy_manifest(directory)
        with self.assertRaisesRegex(IntegrityError, "Ambiguous legacy prompt-to-label"):
            score_directory(directory, self.cases)

    def test_exact_crlf_case_reconstruction_is_supported_without_semantic_tolerance(self):
        directory = self.fixture()
        # Simulate an original Windows hash while retaining the identical LF checkout.
        import hashlib
        self.update_manifests(directory, lambda m: m.update(case_files={
            p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
            for p in self.cases.glob("*.json")}))
        rows, _, audit = score_directory(directory, self.cases)
        self.assertEqual(len(rows), 3)
        matches = [match for evidence in audit["provenance"]["case_file_evidence"].values() for match in evidence["matching"]]
        self.assertIn("reconstructed_CRLF", matches)

    @unittest.skipUnless(importlib.util.find_spec("scipy"), "pooling regression requires scipy")
    def test_two_valid_but_different_semantic_source_versions_cannot_be_pooled(self):
        first, second = self.fixture("F01"), self.fixture("F02")
        def old_source(manifest):
            manifest["code_files"]["procedures.py"] = "c88beeedef76b33356471108a520e1c51c7082880308fda04b4ddd49a85a2362"
            for field in ("review_prompt_chars", "review_text_sha256"):
                for proc in ("P5", "P6"):
                    manifest[field].pop(proc)
        self.update_manifests(second, old_source)
        for directory in (first, second):
            rows = score_directory(directory, self.cases)[0]
            self.assertEqual(len(rows), 3)  # Each source and raw prompt is independently verified.
            with (directory / "scored_runs.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
        result = subprocess.run([sys.executable, str(STUDY / "analysis/branch_pooled.py"),
            "--run", str(first / "scored_runs.csv"), str(self.cases),
            "--run", str(second / "scored_runs.csv"), str(self.cases),
            "--out", str(self.root / "pooled")], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pooling different", result.stderr)

    def test_same_length_actual_review_change_cannot_be_pooled(self):
        first, second = self.fixture("F01"), self.fixture("F02")
        old = runner.pr.REVIEW["P1"]
        changed = old[:-1] + ("！" if old[-1] != "！" else "。")
        self.assertEqual(len(changed), len(old))
        path = second / "responses.jsonl"
        plan = {row["run_id"]: row for row in self.read_plan(second)}
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        altered = 0
        for record in records:
            if plan[record["run_id"]]["procedure"] == "P1":
                appended = record["calls"][1]["messages_appended"]
                self.assertEqual(appended[1], {"role": "user", "content": old})
                appended[1]["content"] = changed
                altered += 1
        self.assertEqual(altered, 1)
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        self.update_manifests(second, lambda manifest: manifest["review_text_sha256"].update(P1=digest(changed)))
        # Either reject the internally inconsistent provenance immediately, or
        # allow independently verified alternate prompts but reject their pooling.
        try:
            second_rows = score_directory(second, self.cases)[0]
        except IntegrityError:
            return
        if importlib.util.find_spec("scipy") is None:
            self.skipTest("pool rejection integration requires scipy")
        sys.path.insert(0, str(STUDY / "analysis"))
        import branch_pooled
        for directory, rows in ((first, score_directory(first, self.cases)[0]), (second, second_rows)):
            with (directory / "scored_runs.csv").open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
        argv = ["branch_pooled", "--run", str(first / "scored_runs.csv"), str(self.cases),
                "--run", str(second / "scored_runs.csv"), str(self.cases), "--out", str(self.root / "pooled")]
        with patch.object(sys, "argv", argv), self.assertRaises(IntegrityError):
            branch_pooled.main()


if __name__ == "__main__":
    unittest.main()
