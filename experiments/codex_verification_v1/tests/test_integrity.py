"""Meaningful fault-injection tests; no model/network calls."""
import json
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
from integrity import (ConfigurationMismatch, DirectoryLock, IntegrityError, LockUnavailable,
                       RunLedger, config_hash, freeze_config, planned_outcomes, rate_or_none,
                       select_legacy_branches, sha256_text)


PROCS = ["P0", "P1", "P3"]


def plan():
    return [{"run_id": p, "family_id": "F01", "state": "base", "advice": "flawed",
             "repeat": 1, "procedure": p} for p in PROCS]


def branch(bid, text, stamp="2026-11-06T00:00:00+00:00", failed=()):
    return [{"run_id": p, "branch_id": bid, "status": "error" if p in failed else "ok",
             "finished": stamp,
             "calls": [{"ok": True, "text": text}, *([] if p == "P0" else
                        [{"ok": p not in failed, "text": "review" if p not in failed else None}])]} for p in PROCS]


def competing_lock(path, queue):
    try:
        with DirectoryLock(path):
            queue.put("acquired")
    except LockUnavailable:
        queue.put("blocked")


class IntegrityTests(unittest.TestCase):
    def test_canonical_config_hash_ignores_mapping_order(self):
        self.assertEqual(config_hash({"a": 1, "b": 2}), config_hash({"b": 2, "a": 1}))
        self.assertNotEqual(config_hash({"a": 1}), config_hash({"a": 2}))

    def test_configuration_drift_refused_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"model": "current", "case_hash": "abc", "max_tokens": None}
            freeze_config(tmp, cfg)
            original = (Path(tmp) / "config_frozen.json").read_bytes()
            freeze_config(tmp, dict(cfg))
            for key, change in [("model", "other"), ("case_hash", "changed"), ("max_tokens", 10)]:
                with self.subTest(field=key), self.assertRaises(ConfigurationMismatch):
                    freeze_config(tmp, {**cfg, key: change})
            self.assertEqual(original, (Path(tmp) / "config_frozen.json").read_bytes())

    def test_tampered_config_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            freeze_config(tmp, {"model": "current"})
            path = Path(tmp) / "config_frozen.json"
            data = json.loads(path.read_text())
            data["config"]["model"] = "tampered"
            path.write_text(json.dumps(data))
            with self.assertRaises(IntegrityError):
                freeze_config(tmp, {"model": "current"})

    def test_cross_process_writer_excluded_and_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = multiprocessing.get_context("spawn")
            q = ctx.Queue()
            with DirectoryLock(tmp):
                child = ctx.Process(target=competing_lock, args=(tmp, q))
                child.start()
                self.assertEqual(q.get(timeout=10), "blocked")
                child.join(timeout=10)
                self.assertEqual(child.exitcode, 0)
            child = ctx.Process(target=competing_lock, args=(tmp, q))
            child.start()
            self.assertEqual(q.get(timeout=10), "acquired")
            child.join(timeout=10)
            self.assertEqual(child.exitcode, 0)

    def test_interleaved_failed_branches_cannot_be_spliced(self):
        # The original latest-success-per-run bug would wrongly call this group complete.
        records = branch("b1", "A with reason 1", failed={"P1"}) + branch(
            "b2", "A with reason 2", "2026-11-06T00:01:00+00:00", failed={"P3"})
        result = select_legacy_branches(records, plan(), PROCS)
        self.assertEqual(result["selected"], {})
        self.assertEqual(result["counts"]["unique_complete_groups"], 0)
        self.assertEqual(result["counts"]["incomplete_branches"], 2)
        self.assertEqual(result["counts"]["uncompleted_groups"], 1)

    def test_select_earliest_complete_not_latest_or_file_order(self):
        records = branch("later", "A later", "2026-11-06T00:01:00+00:00") + branch("earlier", "A earlier")
        result = select_legacy_branches(records, plan(), PROCS)
        self.assertEqual({r["branch_id"] for r in result["selected"].values()}, {"earlier"})
        self.assertEqual(result["duplicate_branches"][0]["branch_id"], "later")
        self.assertEqual(result["counts"]["unique_complete_groups"], 1)
        self.assertEqual(result["counts"]["complete_branch_attempts"], 2)

    def test_earliest_completion_uses_last_procedure_time(self):
        first_started = branch("slow", "A")
        first_started[-1]["finished"] = "2026-11-06T00:02:00+00:00"
        result = select_legacy_branches(first_started + branch("fast", "A", "2026-11-06T00:01:00Z"), plan(), PROCS)
        self.assertEqual(result["selected_branches"][0]["branch_id"], "fast")

    def test_same_action_different_first_text_is_rejected(self):
        records = branch("bad", "A, reason one")
        records[1]["calls"][0]["text"] = "A, reason two"
        with self.assertRaisesRegex(IntegrityError, "different first answers"):
            select_legacy_branches(records, plan(), PROCS)

    def test_legacy_malformed_answer_is_not_silently_resampled(self):
        # A parse error is a returned decision, not a reason to select the later correct branch.
        records = branch("first", "not-json") + branch("second", '{"action":"A"}', "2026-11-06T00:01:00Z")
        result = select_legacy_branches(records, plan(), PROCS)
        self.assertEqual(result["selected"]["P0"]["calls"][0]["text"], "not-json")

    def test_new_ledger_keeps_first_across_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            with RunLedger(tmp, {"model": "current"}) as ledger:
                first = ledger.commit_first("F/base/1", "frozen first")
                ledger.record_procedure("F/base/1", "P0", {"status": "ok", "text": "frozen first"})
            with RunLedger(tmp, {"model": "current"}) as ledger:
                self.assertEqual(ledger.read_first("F/base/1")["first_sha256"], sha256_text("frozen first"))
                self.assertEqual(ledger.commit_first("F/base/1", "frozen first"), first)
                with self.assertRaises(IntegrityError):
                    ledger.commit_first("F/base/1", "new sample")
                ledger.record_procedure("F/base/1", "P3", {"status": "ok", "text": "review"})

    def test_new_ledger_reviewer_hash_and_p0_must_match(self):
        with tempfile.TemporaryDirectory() as tmp, RunLedger(tmp, {"m": "x"}) as ledger:
            ledger.commit_first("g", "A")
            with self.assertRaises(IntegrityError):
                ledger.record_procedure("g", "P3", {"status": "ok", "text": "B", "first_sha256": "bad"})
            with self.assertRaises(IntegrityError):
                ledger.record_procedure("g", "P0", {"status": "ok", "text": "B"})

    def test_final_parse_failure_or_error_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp, RunLedger(tmp, {"m": "x"}) as ledger:
            ledger.commit_first("g", "A")
            original = {"status": "ok", "text": "unparseable"}
            first = ledger.record_procedure("g", "P3", original)
            self.assertEqual(first, ledger.record_procedure("g", "P3", original))
            with self.assertRaises(IntegrityError):
                ledger.record_procedure("g", "P3", {"status": "ok", "text": '{"action":"A"}'})
            ledger.record_procedure("g", "P1", {"status": "error", "attempts": 2})
            with self.assertRaises(IntegrityError):
                ledger.record_procedure("g", "P1", {"status": "ok", "text": "late replacement"})

    def test_tampered_first_detected(self):
        with tempfile.TemporaryDirectory() as tmp, RunLedger(tmp, {"m": "x"}) as ledger:
            ledger.commit_first("g", "A")
            path = Path(tmp) / "ledger" / sha256_text("g") / "first.json"
            obj = json.loads(path.read_text()); obj["text"] = "B"
            path.write_text(json.dumps(obj))
            with self.assertRaises(IntegrityError):
                ledger.read_first("g")

    def test_full_denominator_keeps_missing_parse_and_transport_failures(self):
        planned = [{"run_id": f"r{i}"} for i in range(5)]
        scored = {"r0": {"status": "ok", "parse_ok": True, "correct": True},
                  "r1": {"status": "ok", "parse_ok": True, "correct": False},
                  "r2": {"status": "ok", "parse_ok": False, "correct": True},
                  "r3": {"status": "error", "parse_ok": False}}
        out = planned_outcomes(planned, scored)
        self.assertEqual(len(out), 5)
        self.assertEqual([r["primary_correct"] for r in out], [1, 0, 0, 0, 0])
        self.assertEqual([r["outcome_status"] for r in out],
                         ["completed", "completed", "parse_error", "transport_error", "not_run"])

    def test_zero_errors_rate_is_unknown_not_zero(self):
        self.assertIsNone(rate_or_none(0, 0))
        self.assertEqual(rate_or_none(0, 4), 0.0)
        self.assertEqual(rate_or_none(2, 4), 0.5)
        with self.assertRaises(ValueError):
            rate_or_none(1, 0)

    def test_unknown_legacy_record_refused(self):
        records = branch("g", "A")
        records[0]["run_id"] = "unplanned"
        with self.assertRaises(IntegrityError):
            select_legacy_branches(records, plan(), PROCS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
