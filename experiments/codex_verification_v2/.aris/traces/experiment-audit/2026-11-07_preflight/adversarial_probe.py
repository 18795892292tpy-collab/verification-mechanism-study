"""Independent audit probes. Disposable fixtures only; no model calls or real results."""
from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'harness'), str(ROOT / 'tests')]
import runner
import evaluate
from test_v2 import V2Tests, valid_call
from test_runner_offline import VALID


def probe(name, events, extra_record=False):
    fixture = V2Tests()
    fixture.setUp()
    try:
        frozen = fixture.prepare_freeze()
        job = next(j for j in frozen['phase_schedule']['dev']['jobs'] if j['procedure'] == 'P0')
        item = next(i for i in runner.load_items() if i['item_id'] == job['item_id'])
        def mocked_call(cmd, **kwargs):
            Path(cmd[cmd.index('-o') + 1]).write_text(VALID)
            return subprocess.CompletedProcess(cmd, 0, '\n'.join(json.dumps(e) for e in events), '')
        with patch.object(runner.subprocess, 'run', side_effect=mocked_call) as mock:
            record = runner.response_task('dev', job, item, None, runner.file_sha(fixture.root/'protocol/frozen.json'))
        if extra_record:
            p = fixture.root/'runs/dev/unplanned_group/P0/record.json'
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(record))
        with patch.object(evaluate, 'R', fixture.root), contextlib.redirect_stdout(io.StringIO()):
            result = evaluate.run()
        return {'probe': name, 'mock_calls': mock.call_count, 'subject_calls': 0,
                'status': record['status'], 'passed_integrity': result['passed_integrity'],
                'usage_missing_attempts': result.get('usage_missing_attempts'),
                'sum_input_tokens': result.get('sum_input_tokens'),
                'sum_output_tokens': result.get('sum_output_tokens'),
                'unique_sessions': result['unique_sessions'],
                'actual_cli_attempts': result['actual_cli_attempts']}
    except Exception as exc:
        return {'probe': name, 'subject_calls': 0, 'raised': type(exc).__name__, 'message': str(exc)}
    finally:
        fixture.tearDown()


base = [{'type':'thread.started','thread_id':'audit-fixture-session'}, {'type':'turn.started'}]
probes = [
    probe('empty_usage', [*base, {'type':'turn.completed','usage':{}}]),
    probe('partial_usage', [*base, {'type':'turn.completed','usage':{'input_tokens':17}}]),
    probe('missing_session', [{'type':'turn.started'}, {'type':'turn.completed','usage':{'input_tokens':17,'output_tokens':9}}]),
    probe('unplanned_raw_record', [*base, {'type':'turn.completed','usage':{'input_tokens':17,'output_tokens':9}}], True),
    probe('repeated_turn_completed', [*base, {'type':'turn.completed','usage':{'input_tokens':17,'output_tokens':9}}, {'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':1}}]),
]
print(json.dumps(probes, ensure_ascii=False, indent=2))
