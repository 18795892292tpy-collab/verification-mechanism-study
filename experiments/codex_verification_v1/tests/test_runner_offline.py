"""Runner fault tests: subprocess is ALWAYS mocked, no model task is executed."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
import runner

VALID = json.dumps({"action": "A", "cited_sources": ["S1"],
                    "brief_justification": "依据给定规则", "confidence": 3}, ensure_ascii=False)


def fake_call(final=VALID, extra_events=(), returncode=0):
    def invoke(cmd, **kwargs):
        output = Path(cmd[cmd.index("-o") + 1])
        # Start marker must be persisted before a call is allowed to start.
        assert (output.parent / "attempt_started.json").is_file()
        if final is not None:
            output.write_text(final)
        events = [{"type": "thread.started", "thread_id": "test-session"},
                  {"type": "turn.started"}, *extra_events,
                  {"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 9}}]
        return subprocess.CompletedProcess(cmd, returncode, "\n".join(json.dumps(e) for e in events), "")
    return invoke


class RunnerOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch_r = patch.object(runner, "R", self.root)
        self.patch_r.start()
        self.job = {"group_id": "item_r1", "item_id": "item", "repeat": 1, "procedure": "P0"}
        self.item = {"public_text": "虚构规则：选 A。"}

    def tearDown(self):
        self.patch_r.stop()
        self.tmp.cleanup()

    @property
    def out(self):
        return self.root / "runs" / "toy" / self.job["group_id"] / self.job["procedure"]

    def execute(self, side_effect=None, first=None):
        with patch.object(runner.subprocess, "run", side_effect=side_effect or fake_call()) as mocked:
            result = runner.response_task("toy", self.job, self.item, first, "frozen")
        return result, mocked.call_count

    def test_completed_task_resumes_without_call_and_keeps_exact_text(self):
        first, calls = self.execute()
        self.assertEqual(calls, 1)
        self.assertEqual(first["status"], "complete")
        again, calls = self.execute()
        self.assertEqual(calls, 0)
        self.assertEqual(first, again)
        self.assertEqual(again["raw_final"], VALID)

    def test_interrupted_attempt_is_not_silently_resampled(self):
        ad = self.out / "attempt_01"
        ad.mkdir(parents=True)
        (ad / "attempt_started.json").write_text("{}")
        (ad / "response.json").write_text(VALID)
        with patch.object(runner.subprocess, "run", side_effect=AssertionError("must not call")) as mocked:
            with self.assertRaisesRegex(RuntimeError, "Uncommitted attempt"):
                runner.response_task("toy", self.job, self.item, None, "frozen")
        mocked.assert_not_called()
        self.assertEqual((ad / "response.json").read_text(), VALID)

    def test_marker_without_any_output_is_also_uncommitted(self):
        ad = self.out / "attempt_01"
        ad.mkdir(parents=True)
        (ad / "attempt_started.json").write_text("{}")
        with patch.object(runner.subprocess, "run") as mocked:
            with self.assertRaisesRegex(RuntimeError, "Uncommitted attempt"):
                runner.response_task("toy", self.job, self.item, None, "frozen")
        mocked.assert_not_called()

    def test_tampered_saved_raw_answer_rejected(self):
        result, _ = self.execute()
        result["raw_final"] = VALID.replace('"A"', '"B"')
        (self.out / "record.json").write_text(json.dumps(result))
        with self.assertRaisesRegex(RuntimeError, "final response hash"):
            self.execute()

    def test_tampered_parsed_answer_rejected(self):
        result, _ = self.execute()
        result["parsed"]["action"] = "B"
        (self.out / "record.json").write_text(json.dumps(result))
        with self.assertRaisesRegex(RuntimeError, "status/answer"):
            self.execute()

    def test_tampered_prompt_rejected(self):
        self.execute()
        (self.out / "prompt.txt").write_text("changed")
        with self.assertRaisesRegex(RuntimeError, "prompt mismatch"):
            self.execute()

    def test_tampered_event_log_rejected(self):
        self.execute()
        with (self.out / "attempt_01" / "events.jsonl").open("a") as stream:
            stream.write('\n{"type":"tool.called"}')
        with self.assertRaisesRegex(RuntimeError, "artifact hash"):
            self.execute()

    def test_sealed_attempt_response_checked_even_without_record(self):
        self.execute()
        (self.out / "record.json").unlink()
        (self.out / "attempt_01" / "response.json").write_text("changed")
        with patch.object(runner.subprocess, "run") as mocked:
            with self.assertRaisesRegex(RuntimeError, "response hash"):
                runner.response_task("toy", self.job, self.item, None, "frozen")
        mocked.assert_not_called()

    def test_sealed_attempt_recovers_record_without_resampling(self):
        original, _ = self.execute()
        (self.out / "record.json").unlink()
        recovered, calls = self.execute()
        self.assertEqual(calls, 0)
        self.assertEqual(recovered["raw_final"], original["raw_final"])
        self.assertEqual(recovered["attempts"], original["attempts"])

    def test_unknown_top_event_is_protocol_failure_no_retry(self):
        result, calls = self.execute(fake_call(extra_events=[{"type": "tool.called", "name": "exec"}]))
        self.assertEqual(result["status"], "protocol_failure")
        self.assertEqual(calls, 1)

    def test_unknown_item_is_protocol_failure_no_retry(self):
        result, calls = self.execute(fake_call(extra_events=[{"type": "item.completed", "item": {"type": "command_execution"}}]))
        self.assertEqual(result["status"], "protocol_failure")
        self.assertEqual(calls, 1)

    def test_non_json_stdout_is_not_ignored(self):
        info = runner.events_info('not-json\n{"type":"turn.completed","usage":{}}')
        self.assertEqual(len(info["unexpected_items"]), 1)

    def test_parse_failure_is_final_and_not_retried(self):
        result, calls = self.execute(fake_call(final="not-json"))
        self.assertEqual(result["status"], "parse_failure")
        self.assertEqual(calls, 1)
        resumed, calls = self.execute()
        self.assertEqual(resumed["status"], "parse_failure")
        self.assertEqual(calls, 0)

    def test_no_response_can_retry_at_most_twice(self):
        result, calls = self.execute(fake_call(final=None, returncode=1))
        self.assertEqual(calls, 2)
        self.assertEqual(result["status"], "technical_failure")
        _, calls = self.execute()
        self.assertEqual(calls, 0)

    def test_review_resume_refuses_a_different_first(self):
        self.job["procedure"] = "P3"
        first, calls = self.execute(first="same first A")
        self.assertEqual(first["first_sha256"], runner.sha("same first A"))
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            self.execute(first="another first A")

    def test_shared_first_failure_marks_every_review_in_plan(self):
        p0, _ = self.execute(fake_call(final=None, returncode=1))
        self.assertEqual(p0["status"], "technical_failure")
        jobs = [{**self.job, "procedure": p} for p in runner.PROCS]
        frozen = {"phase_schedule": {"toy": {"jobs": jobs}}}
        (self.root / "prompts").mkdir()
        (self.root / "prompts" / "toy_items.json").write_text(json.dumps([{"item_id": "item", **self.item}]))
        with patch.object(runner, "verify", return_value=frozen), \
             patch.object(runner, "file_sha", side_effect=lambda path: "frozen" if str(path).endswith("frozen.json") else runner.sha(Path(path).read_bytes())), \
             patch.object(runner.subprocess, "run") as mocked:
            runner.run("toy", "review", 1)
        mocked.assert_not_called()
        for p in runner.PROCS[1:]:
            rec = json.loads((self.out.parent / p / "record.json").read_text())
            self.assertEqual(rec["status"], "not_run_first_failed")
            self.assertEqual(rec["attempts"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
