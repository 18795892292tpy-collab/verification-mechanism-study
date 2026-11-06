"""Independent exact-size 667 -> 800 recovery probe. No real model calls."""
from pathlib import Path
import contextlib,io,json,sys,threading
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'harness'),str(ROOT/'tests')]
import runner,evaluate,run_concurrency_override as driver
from test_v2 import V2Tests,valid_call
from integrity import LockUnavailable
x=V2Tests();x.setUp()
try:
 with patch.object(evaluate,'R',x.root):
  frozen=x.prepare_freeze();cfg=runner.file_sha(x.root/'protocol/frozen.json')
  items={i['item_id']:i for i in runner.load_items()};jobs=frozen['phase_schedule']['dev']['jobs']
  baseline=[j for j in jobs if j['procedure']=='P0']+[j for j in jobs if j['procedure']!='P0'][:507]
  with patch.object(runner.subprocess,'run',side_effect=valid_call):
   for job in baseline:
    first=None if job['procedure']=='P0' else runner.read(x.root/'runs/dev'/job['group_id']/'P0/record.json')['raw_final']
    runner.response_task('dev',job,items[job['item_id']],first,cfg)
  prior={str(p.relative_to(x.root)):runner.file_sha(p) for p in (x.root/'runs/dev').glob('*/*/record.json')}
  amendment={'schema_version':1,'kind':'dispatch_concurrency_only','from_max_workers':3,'to_max_workers':12,'workers':12,
   'baseline_frozen_sha256':cfg,'driver_sha256':runner.file_sha(driver.DRIVER),'prior_terminal_records':prior}
  runner.dump(x.root/driver.AMENDMENT,amendment)
  locked=False
  with runner.DirectoryLock(x.root/'runs/dev'):
   try:driver.run(verify_only=True)
   except LockUnavailable:locked=True
  barrier=threading.Barrier(12);guard=threading.Lock();counts={'calls':0,'active':0,'peak':0}
  def call(cmd,**kwargs):
   with guard:
    counts['calls']+=1;number=counts['calls'];counts['active']+=1;counts['peak']=max(counts['peak'],counts['active'])
   if number<=12:barrier.wait(timeout=5)
   result=valid_call(cmd,**kwargs)
   with guard:counts['active']-=1
   return result
  with patch.object(runner.subprocess,'run',side_effect=call),contextlib.redirect_stdout(io.StringIO()):
   done=driver.run('all');summary=evaluate.run()
  with patch.object(runner.subprocess,'run',side_effect=AssertionError('duplicate sample')) as mock,contextlib.redirect_stdout(io.StringIO()):
   resumed=driver.run('all')
  changed={k for k,v in prior.items() if runner.file_sha(x.root/k)!=v}
  runner.dump(x.root/driver.AMENDMENT,{**amendment,'extra_field':'amended after applied'})
  ledger_rejected=False
  try:driver.run(verify_only=True)
  except RuntimeError as e:ledger_rejected='cannot be replaced' in str(e)
  out={'prior_records':len(prior),'new_mock_calls':counts['calls'],'peak_simultaneous_mock_calls':counts['peak'],
       'finished':done,'resume_finished':resumed,'resume_new_mock_calls':mock.call_count,'prior_records_changed':len(changed),
       'frozen_hash_unchanged':cfg==runner.file_sha(x.root/'protocol/frozen.json'),'baseline_max_workers':runner.MAX_WORKERS,
       'baseline_execution_config_max_workers':runner.execution_config()['max_workers'],'competing_lock_rejected':locked,
       'applied_amendment_replacement_rejected':ledger_rejected,'complete_tasks':summary['complete_tasks'],
       'passed_integrity':summary['passed_integrity'],'unique_sessions':summary['unique_sessions'],'subject_calls':0}
  print(json.dumps(out,ensure_ascii=False,indent=2))
  assert out['prior_records']==667 and out['new_mock_calls']==133 and out['peak_simultaneous_mock_calls']==12
  assert out['prior_records_changed']==0 and out['resume_new_mock_calls']==0 and out['passed_integrity']
  assert out['complete_tasks']==800 and out['unique_sessions']==800 and out['frozen_hash_unchanged']
  assert locked and ledger_rejected and runner.MAX_WORKERS==3
finally:x.tearDown()
