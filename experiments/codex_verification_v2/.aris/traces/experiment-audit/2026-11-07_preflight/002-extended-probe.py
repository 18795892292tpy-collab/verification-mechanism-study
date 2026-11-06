"""Independent recovery regression probe; all raw artifacts are disposable mocks."""
from pathlib import Path
import contextlib
import io
import json
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT/'harness'), str(ROOT/'tests')]
import runner
import evaluate
from test_v2 import V2Tests, service_error, valid_call

fixture = V2Tests()
fixture.setUp()
try:
    frozen = fixture.prepare_freeze()
    job = next(j for j in frozen['phase_schedule']['dev']['jobs'] if j['procedure']=='P0')
    item = next(i for i in runner.load_items() if i['item_id']==job['item_id'])
    config_hash = runner.file_sha(fixture.root/'protocol/frozen.json')
    with patch.object(runner.subprocess,'run',side_effect=service_error('TLS unexpected EOF')) as mocked:
        first = runner.response_task('dev',job,item,None,config_hash,runner.DispatchGate())
        calls1 = mocked.call_count
    attempt1 = fixture.root/'runs/dev'/job['group_id']/'P0/attempt_01'
    original = {p.name:p.read_bytes() for p in attempt1.iterdir()}
    with patch.object(runner.subprocess,'run',side_effect=valid_call) as mocked:
        second = runner.response_task('dev',job,item,None,config_hash,runner.DispatchGate())
        calls2 = mocked.call_count
    error = None
    with patch.object(evaluate,'R',fixture.root),contextlib.redirect_stdout(io.StringIO()):
        try:
            evaluate.run()
        except Exception as exc:
            error = str(exc)
    audit = runner.read(fixture.root/'analysis/dev/integrity_audit.json')
    summary = runner.read(fixture.root/'analysis/dev/summary.json')
    with patch.object(runner.subprocess,'run',side_effect=AssertionError('No duplicate sampling')) as mocked:
        resumed = runner.response_task('dev',job,item,None,config_hash,runner.DispatchGate())
        duplicate_calls = mocked.call_count
    out = {'probe':'no_final_network_resume_and_usage_provenance','subject_calls':0,
           'mock_calls_first':calls1,'mock_calls_second':calls2,'mock_calls_final_resume':duplicate_calls,
           'first_status':first['status'],'second_status':second['status'],
           'same_final_record':resumed==second,
           'attempt1_preserved':original=={p.name:p.read_bytes() for p in attempt1.iterdir()},
           'evaluation_error':error,'lifecycle_errors':audit['lifecycle_errors'],
           'passed_integrity':summary['passed_integrity'],
           'actual_cli_attempts':summary['actual_cli_attempts'],
           'sum_input_tokens':summary['sum_input_tokens'],'sum_output_tokens':summary['sum_output_tokens'],
           'known_input_tokens':summary['known_input_tokens'],'known_output_tokens':summary['known_output_tokens'],
           'usage_missing_attempts':summary['usage_missing_attempts']}
    print(json.dumps(out,ensure_ascii=False,indent=2))
finally:
    fixture.tearDown()
