#!/usr/bin/env python3
import importlib.util,json,sys,threading,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).with_name('driver.py'); spec=importlib.util.spec_from_file_location('posthoc_challenge',P);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
def make_events(output):
 return '\n'.join(json.dumps(e) for e in [{'type':'thread.started','thread_id':'thread-test'},{'type':'item.completed','item':{'id':'a','type':'error','message':d.DIAGNOSTICS[0]}},{'type':'item.completed','item':{'id':'b','type':'error','message':d.DIAGNOSTICS[1]}},{'type':'turn.started'},{'type':'item.completed','item':{'id':'c','type':'error','message':d.DIAGNOSTICS[2]}},{'type':'item.completed','item':{'id':'d','type':'agent_message','text':output}},{'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':1}}])+'\n'
class Tests(unittest.TestCase):
 def setUp(self):self.response=json.dumps({'action':'A','cited_sources':['S1'],'brief_justification':'测试','confidence':4});self.events=make_events(self.response)
 def test_valid(self):self.assertEqual(d.classify(self.events,self.response,0)['status'],'complete')
 def test_unknown_diagnostic(self):self.assertNotEqual(d.classify(self.events.replace(d.DIAGNOSTICS[1],d.DIAGNOSTICS[1]+'!'),self.response,0)['status'],'complete')
 def test_mismatch(self):self.assertNotEqual(d.classify(self.events,self.response+' ',0)['status'],'complete')
 def test_tool(self):self.assertNotEqual(d.classify(self.events.replace('agent_message','command_execution'),self.response,0)['status'],'complete')
 def test_lifecycle(self):self.assertNotEqual(d.classify(self.events.replace('turn.completed','turn.failed'),self.response,0)['status'],'complete')
 def test_no_response_never_complete(self):self.assertNotEqual(d.classify(self.events,None,0)['status'],'complete')
 def test_128_and_resume_no_calls(self):
  jobs=d.schedule(); self.assertEqual(len(jobs),128); active=0;maximum=0;calls=[];lock=threading.Lock()
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));runs=root/'runs'; fake=type('CP',(),{})
   def invoke(cmd,**kw):
    nonlocal active,maximum
    with lock:active+=1;maximum=max(maximum,active);calls.append(1);call_id=len(calls)
    time.sleep(.025);Path(cmd[cmd.index('-o')+1]).write_text(self.response); x=fake();x.stdout=self.events.replace('thread-test','thread-'+str(call_id));x.stderr='';x.returncode=0
    with lock:active-=1
    return x
   with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d,'FROZEN',frozen),patch.object(d,'verify',return_value={'jobs':jobs}),patch.object(d.subprocess,'run',side_effect=invoke),patch('builtins.print'):
    d.run();self.assertEqual(len(calls),128); self.assertEqual(maximum,12)
    d.run();self.assertEqual(len(calls),128)
    # A planned task with an unsealed attempt blocks all subsequent calls.
    target=runs/jobs[0]['group_id']/jobs[0]['procedure']/'record.json';target.unlink()
    with self.assertRaises(RuntimeError):d.run()
    self.assertEqual(len(calls),128)
 def test_lifecycle_item_refused(self):
  events=self.events.replace('\"turn.started\"','\"turn.started\", \"item\": {\"type\": \"command_execution\"}')
  self.assertNotEqual(d.classify(events,self.response,0)['status'],'complete')
 def test_unknown_stderr_refused(self):self.assertNotEqual(d.classify(self.events,self.response,0,'network error')['status'],'complete')
 def test_p0_session_duplicate_refused(self):
  job=d.schedule()[0];gate=d.read(d.ROOT/'analysis/decision_gate.json');p0=d.read(d.ROOT/next(iter(gate['p0_record_sha256'])));tid=p0['attempts'][0]['thread_ids'][0]
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));runs=root/'runs'
   def invoke(cmd,**kw):
    Path(cmd[cmd.index('-o')+1]).write_text(self.response);x=type('CP',(),{})();x.stdout=self.events.replace('thread-test',tid);x.stderr='';x.returncode=0;return x
   with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d,'FROZEN',frozen),patch.object(d,'verify',return_value={'jobs':[job]}),patch.object(d.subprocess,'run',side_effect=invoke),patch('builtins.print'):
    with self.assertRaises(SystemExit):d.run()
 def test_completed_error_payload_refused(self):
  e=self.events.replace('\"turn.completed\"','\"turn.completed\", \"error\": {\"message\": \"fatal transport failure\"}')
  self.assertNotEqual(d.classify(e,self.response,0)['status'],'complete')
 def test_false_returncode_refused(self):self.assertNotEqual(d.classify(self.events,self.response,False)['status'],'complete')
 def test_runtime_symlink_refused_before_marker(self):
  with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as outside:
   root=Path(td);(root/'runtime_empty').symlink_to(outside,target_is_directory=True);runs=root/'runs';job=d.schedule()[0]
   with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d.subprocess,'run') as execute:
    with self.assertRaises(RuntimeError):d.one(job,'fake')
    execute.assert_not_called();self.assertFalse(runs.exists())
 def test_response_metadata_mismatch_refused(self):
  job=d.schedule()[0]
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));runs=root/'runs'
   def invoke(cmd,**kw):
    Path(cmd[cmd.index('-o')+1]).write_text(self.response);x=type('CP',(),{})();x.stdout=self.events;x.stderr='';x.returncode=0;return x
   with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d,'FROZEN',frozen),patch.object(d.subprocess,'run',side_effect=invoke):
    h=d.file_sha(frozen);d.one(job,h);path=runs/job['group_id']/job['procedure']/'record.json';rec=json.loads(path.read_text());rec['has_response']=False;rec['artifact_sha256'].pop('response.json');path.write_text(json.dumps(rec))
    with self.assertRaises(RuntimeError):d.check_task_dir(job,h)
 def test_unknown_path_refused(self):
  with tempfile.TemporaryDirectory() as td:
   with patch.object(d,'RUNS',Path(td)):
    (Path(td)/'unplanned').mkdir()
    with self.assertRaises(RuntimeError):d.inventory(d.schedule())
if __name__=='__main__':unittest.main(verbosity=2)
