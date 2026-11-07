from pathlib import Path
from unittest.mock import patch
import importlib.util,contextlib,io,json,tempfile,subprocess,uuid,copy,sys
sys.dont_write_bytecode=True
ROOT=Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
source=ROOT/'amendments/A1_posthoc/challenge/driver.py'
spec=importlib.util.spec_from_file_location('reviewed_challenge',source);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
TRACE=Path(__file__).resolve().parent
source_hash=d.file_sha(source);(TRACE/('challenge_source_'+source_hash[:12]+'.py')).write_bytes(source.read_bytes())
RESULTS=[]
def record(name,passed,observed):RESULTS.append({'probe':name,'passed':bool(passed),'observed':observed})
RESPONSE=json.dumps({'action':'A','cited_sources':['S1'],'brief_justification':'依规则','confidence':4},ensure_ascii=False)
def events(output=RESPONSE):
 return [{'type':'thread.started','thread_id':uuid.uuid4().hex},
         {'type':'item.completed','item':{'id':'item_0','type':'error','message':d.DIAGNOSTICS[0]}},
         {'type':'item.completed','item':{'id':'item_1','type':'error','message':d.DIAGNOSTICS[1]}},
         {'type':'turn.started'},
         {'type':'item.completed','item':{'id':'item_2','type':'error','message':d.DIAGNOSTICS[2]}},
         {'type':'item.completed','item':{'id':'item_3','type':'agent_message','text':output}},
         {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':5}}]
def encoded(ev):return '\n'.join(map(json.dumps,ev))
def invoke(cmd,**kwargs):
 Path(cmd[cmd.index('-o')+1]).write_text(RESPONSE)
 return subprocess.CompletedProcess(cmd,0,encoded(events()),'')

with patch.object(d,'AMENDMENT',source.with_name('authorization.candidate.json')):
 try:
  a=d.authorization_check();f=d.manifest();observed={'jobs':len(f['jobs']),'posthoc_exploratory':f['posthoc_exploratory'],'strict_original_gate_override':f['strict_original_gate_override']};ok=len(f['jobs'])==128 and f['jobs']==d.read(ROOT/'protocol/frozen.json')['phase_schedule']['challenge']['jobs']
 except Exception as exc:ok=False;observed={'error':repr(exc)}
record('actual_candidate_and_baseline_binding',ok,observed)

p=d.read(ROOT/'protocol/prompts.json');its=d.items()
record('all_128_prompts_exact_original_drafts',all(d.prompt_for(j)==p['base']+'\n\n档案与问题：\n'+its[j['item_id']]['public_text']+'\n\n待复核草稿（作者预设，原样提供）：\n'+its[j['item_id']]['draft_text']+'\n\n本次任务：\n'+p['reviews'][j['procedure']] for j in d.schedule()),{'checked':128})
for name,mutator in [
 ('lifecycle_embedded_tool',lambda e:e[3].update(item={'type':'command_execution'})),
 ('unknown_top_error_payload',lambda e:e[-1].update(error={'message':'fatal transport failure'})),
 ('diagnostic_extra_field',lambda e:e[1]['item'].update(command='forbidden')),
 ('final_and_diagnostic_swap',lambda e:e.__setitem__(slice(4,6),[e[5],e[4]])),
 ('extra_top_error',lambda e:e.insert(-1,{'type':'error','message':'quota exceeded'}))]:
 ev=events();mutator(ev);c=d.classify(encoded(ev),RESPONSE,0);record(name,c['status']!='complete',c)
c=d.classify(encoded(events()),RESPONSE,False);record('boolean_returncode_rejected',c['status']!='complete',c)

job=d.schedule()[0]
with tempfile.TemporaryDirectory() as td:
 root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));runs=root/'runs'
 with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d,'FROZEN',frozen),patch.object(d.subprocess,'run',side_effect=invoke) as mock:
  rec=d.one(job,d.file_sha(frozen));again=d.one(job,d.file_sha(frozen));record('existing_final_no_resample',mock.call_count==1 and again==rec,{'calls_including_resume':mock.call_count})
  rp=runs/job['group_id']/job['procedure']/'record.json';bad=copy.deepcopy(rec);bad['has_response']=False;bad['artifact_sha256'].pop('response.json');rp.write_text(json.dumps(bad))
  caught=None
  try:d.check_task_dir(job,d.file_sha(frozen))
  except Exception as exc:caught=repr(exc)
  record('response_presence_cannot_escape_hash_coverage',caught is not None,{'exception':caught})

with tempfile.TemporaryDirectory() as td,tempfile.TemporaryDirectory() as elsewhere:
 root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));(root/'runtime_empty').symlink_to(elsewhere,target_is_directory=True)
 with patch.object(d,'HERE',root),patch.object(d,'RUNS',root/'runs'),patch.object(d,'FROZEN',frozen),patch.object(d.subprocess,'run',side_effect=invoke) as mock:
  caught=None
  try:d.one(job,d.file_sha(frozen))
  except Exception as exc:caught=repr(exc)
  record('runtime_empty_symlink_rejected_before_call',mock.call_count==0 and caught is not None,{'calls':mock.call_count,'exception':caught})

with patch.object(d.socket,'gethostname',return_value='other-host'):
 caught=None
 try:d.baseline_check()
 except Exception as exc:caught=repr(exc)
record('wrong_host_rejected',caught is not None,{'exception':caught})

candidate=d.read(source.with_name('authorization.candidate.json'));real_read=d.read
for name,which,mutator in [
 ('candidate_wrong_job_inventory',source.with_name('authorization.candidate.json'),lambda a:a['jobs'].pop()),
 ('derived_not_all80_accepted',ROOT/'amendments/A1_posthoc/results/threshold_diagnostic.json',lambda a:a.update(derived_transport_accepted_all_80=False)),
 ('derived_gate_pass_cannot_authorize_this_extra_stage',ROOT/'amendments/A1_posthoc/results/threshold_diagnostic.json',lambda a:a.update(hypothetical_threshold_status='eligible_for_independent_holdout'))]:
 def changed(path):
  value=copy.deepcopy(real_read(path))
  if Path(path)==which:mutator(value)
  return value
 caught=None
 with patch.object(d,'AMENDMENT',source.with_name('authorization.candidate.json')),patch.object(d,'read',side_effect=changed):
  try:d.authorization_check()
  except Exception as exc:caught=repr(exc)
 record(name,caught is not None,{'exception':caught})

# Service failure stops new dispatch, preserves all started responses, and never
# repeats any existing final on a subsequent invocation.
with tempfile.TemporaryDirectory() as td:
 root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));runs=root/'runs';jobs=d.schedule();count=[0]
 def service(cmd,**kwargs):
  count[0]+=1
  if count[0]==1:return subprocess.CompletedProcess(cmd,1,'{"type":"error","message":"quota exhausted"}','')
  return invoke(cmd,**kwargs)
 with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d,'FROZEN',frozen),patch.object(d,'verify',return_value={'jobs':jobs}),patch.object(d.subprocess,'run',side_effect=service),contextlib.redirect_stdout(io.StringIO()):
  error=None
  try:d.run()
  except BaseException as exc:error=repr(exc)
  first_count=count[0];second_error=None
  try:d.run()
  except BaseException as exc:second_error=repr(exc)
 record('service_breaker_and_failed_resume_no_sampling',error is not None and second_error is not None and 1<=first_count<=12 and count[0]==first_count,{'first_invocation_calls':first_count,'total_calls_after_resume':count[0],'first_error':error,'resume_error':second_error})

with tempfile.TemporaryDirectory() as td:
 root=Path(td);frozen=root/'frozen.json';frozen.write_text(json.dumps({'created_utc':'2000-01-01T00:00:00+00:00'}));runs=root/'runs';jobs=d.schedule();late=jobs[-1];ad=runs/late['group_id']/late['procedure']/'attempt_01';ad.mkdir(parents=True);(ad/'response.json').write_text(RESPONSE)
 with patch.object(d,'HERE',root),patch.object(d,'RUNS',runs),patch.object(d,'FROZEN',frozen),patch.object(d,'verify',return_value={'jobs':jobs}),patch.object(d.subprocess,'run',side_effect=AssertionError('Must not call')) as mocked,contextlib.redirect_stdout(io.StringIO()):
  caught=None
  try:d.run()
  except Exception as exc:caught=repr(exc)
 record('late_unsealed_final_blocks_all_dispatch',mocked.call_count==0 and caught is not None,{'calls':mocked.call_count,'error':caught})

print(json.dumps({'source_sha256':source_hash,'real_model_calls':0,'results':RESULTS},ensure_ascii=False,indent=2))
