#!/usr/bin/env python3
"""Independent final V3/A1/extra-C audit; no runner, derive or driver imports.

Only run --write-final after root confirms all128 extra-C terminal records.
Uses the auditor's earlier stdlib helpers, never calls a model, never writes inputs.
"""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,socket,re,os,csv

R=Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
C=R/'amendments/A1_posthoc/challenge'
H=runpy.run_path(str(R/'audits/independent_recompute.py'))
read=H['read'];sha=H['file_hash'];require=H['require'];stamp=H['stamp'];digest=H['digest']
PHASE='independent_authored_draft_exploration'
REVIEWED_DRIVER='9412da448003e6ff148b8c4c2a2873e9f961492347fe117c2a0d6c3bdb0d1fa8'

def snapshot(paths):
 return {str(p.relative_to(R)):sha(p) for p in paths}

def peak(intervals):
 points=[(stamp(t),change) for a,b in intervals for t,change in [(a,1),(b,-1)]]
 active=maximum=0
 for _,change in sorted(points):active+=change;maximum=max(maximum,active)
 return maximum

def classify_raw(events,response,returncode,stderr,warnings):
 problems=[]
 seq=['thread.started','item.completed','item.completed','turn.started','item.completed','item.completed','turn.completed']
 keys=[{'type','thread_id'},{'type','item'},{'type','item'},{'type'},{'type','item'},{'type','item'},{'type','usage'}]
 if len(events)!=7 or any(not isinstance(e,dict) for e in events):return {'status':'technical_or_protocol_failure','parsed':None,'thread_id':None,'usage':None,'errors':[],'problem':'invalid event count/shape'}
 if [e.get('type') for e in events]!=seq or any(set(e)!=k for e,k in zip(events,keys)):problems.append('event sequence or envelope')
 messages=[];errors=[]
 for i in [1,2,4]:
  item=events[i].get('item',{})
  if set(item)!={'id','type','message'} or item.get('type')!='error' or not isinstance(item.get('id'),str):problems.append('diagnostic shape')
  errors.append(item.get('message'))
 final=events[5].get('item',{})
 if set(final)!={'id','type','text'} or final.get('type')!='agent_message' or not isinstance(final.get('id'),str):problems.append('final shape')
 if errors!=warnings:problems.append('unknown diagnostic')
 if type(returncode) is not int or returncode!=0:problems.append('returncode')
 if response is None or final.get('text')!=response:problems.append('final disagreement')
 sid=events[0].get('thread_id')
 if not isinstance(sid,str) or not sid.strip():problems.append('session')
 if stderr and not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z  WARN codex_http_client::native_roots: encountered errors while loading native root certificates native_root_error_count=2\n?',stderr):problems.append('unknown stderr')
 parsed=H['schema_parse'](response) if response is not None else None
 if parsed is None:problems.append('schema')
 return {'status':'complete' if not problems else 'technical_or_protocol_failure','parsed':parsed if not problems else None,'thread_id':sid if not problems else None,'usage':events[-1].get('usage') if not problems else None,'errors':errors if not problems else [],'problem':problems or None}

def audit():
 require(socket.gethostname()=='liekkas' and R.resolve()==R and Path(__file__).resolve().parents[1]==R,'Wrong host/root')
 frozen=read(R/'protocol/frozen.json');fhash=sha(R/'protocol/frozen.json');gate=read(R/'analysis/decision_gate.json')
 require(gate['status']=='technical_block' and gate['challenge_allowed'] is False,'Original scientific gate must remain blocked')
 original_inputs=read(R/'amendments/A1_posthoc/results/input_sha256.json')
 require(all(sha(R/p)==h for p,h in original_inputs.items()),'Original input drift since A1')
 H['scan_inventory'](R,{phase:frozen['phase_schedule'][phase]['jobs'] for phase in ['p0','challenge']})
 require({str(p.relative_to(R)) for p in (R/'runs').rglob('*') if p.is_file()}=={p for p in original_inputs if p.startswith('runs/')},'Original run inventory changed')
 require(all(sha(R/p)==h for p,h in frozen['sha256'].items()),'Original frozen drift')
 rt=frozen['runtime'];require(rt['hostname']==socket.gethostname() and rt['root']==str(R),'Runtime target')
 require(str(Path(rt['cli_path']).resolve())==rt['cli_resolved'] and sha(Path(rt['cli_resolved']))==rt['cli_sha256'],'CLI wrapper drift')
 require(all(sha(Path(p))==h for p,h in rt['cli_dependency_sha256'].items()),'CLI native/package drift')
 require(rt['home']==str(Path.home()) and rt['codex_home']==os.environ.get('CODEX_HOME',str(Path.home()/'.codex')),'Runtime home drift')
 cf=read(C/'frozen.json');chash=sha(C/'frozen.json');auth=read(C/'authorization.json')
 require(cf['driver_sha256']==sha(C/'driver.py')==REVIEWED_DRIVER,'Unreviewed driver')
 require(cf['authorization_sha256']==sha(C/'authorization.json'),'Authorization drift')
 require(cf['original_frozen_sha256']==fhash and cf['original_gate_sha256']==sha(R/'analysis/decision_gate.json'),'Source identity drift')
 require(cf['posthoc_exploratory'] is True and cf['strict_original_gate_override'] is False and cf['phase']==PHASE,'Misrepresented phase')
 require(cf['model']=='gpt-6-astra' and cf['effort']=='ultra' and cf['flags']==frozen['execution_config']['flags'],'Changed subject settings')
 require(cf['max_attempts']==1 and cf['max_workers']==12 and cf['timeout_seconds']==600,'Challenge budget drift')
 require(all(sha(R/p)==h for p,h in cf['inputs'].items()),'Challenge source input drift')
 require(auth['jobs']==cf['jobs']==frozen['phase_schedule']['challenge']['jobs'] and len(cf['jobs'])==128,'Changed128 schedule')
 require(auth['original_gate_challenge_allowed'] is False and auth['prior_strict_gate_outcome']=='technical_block' and auth['posthoc_exploratory'] is True,'Authorization misstates original gate')
 require(cf['diagnostic_allowlist']==auth['diagnostic_allowlist'],'Warning policy drift')
 a1=R/'amendments/A1_posthoc/results';am=read(a1/'manifest.json')
 require(all(sha(a1/p)==h for p,h in am['outputs_sha256'].items()),'A1 published artifact drift')
 require(sha(R/auth['posthoc_analysis_path'])==auth['posthoc_analysis_sha256'] and sha(a1/'summary.json')==auth['posthoc_summary_sha256'] and sha(a1/'manifest.json')==auth['posthoc_manifest_sha256'] and sha(a1/'input_sha256.json')==auth['posthoc_input_manifest_sha256'],'A1 authorization binding drift')
 prompts=read(R/'protocol/prompts.json');pitems={x['item_id']:x for x in read(R/'prompts/p0_items.json')};pkeys={x['item_id']:x for x in read(R/'keys/p0_keys.json')}
 citems={x['item_id']:x for x in read(R/'prompts/challenge_items.json')};ckeys={x['item_id']:x for x in read(R/'keys/challenge_keys.json')}
 for phase,its,keys in [('p0',pitems,pkeys),('challenge',citems,ckeys)]:H['validate_design'](list(its.values()),keys,phase)
 sessions=[];prows=[];pintervals=[]
 for j in frozen['phase_schedule']['p0']['jobs']:
  row=H['audit_task'](R,j,pitems[j['item_id']],pkeys[j['item_id']],'p0',prompts,fhash,stamp(frozen['created_utc']),None)
  require(row['status']=='technical_failure','Strict original P0 classification changed')
  d=R/'runs/p0'/j['group_id']/'P0/attempt_01';meta=read(d/'meta.json');pintervals.append((meta['started_utc'],meta['finished_utc']))
  events=[json.loads(s) for s in (d/'events.jsonl').read_text().splitlines() if s.strip()]
  cl=classify_raw(events,(d/'response.json').read_text(),meta['returncode'],(d/'stderr.txt').read_text(),cf['diagnostic_allowlist'])
  require(cl['status']=='complete','P0 exact diagnostic interpretation changed')
  sessions.append(cl['thread_id']);row.update(status='complete',action=cl['parsed']['action'],correct=int(cl['parsed']['action']==pkeys[j['item_id']]['correct_action']));prows.append(row)
 require(gate['complete_p0_observed']==0 and gate['complete_p0_required']==80,'Strict gate count mismatch')
 require(gate['p0_record_sha256']=={str(Path('runs/p0')/row['group_id']/'P0/record.json'):row['record_sha256'] for row in prows},'Strict gate source record mismatch')
 require(all(stamp(gate['created_utc'])>=stamp(row['finished_utc']) for row in prows),'Strict gate predates P0')
 ps=H['phase_stats'](prows,'p0');saved=read(a1/'summary.json')
 require(saved['derived_correct']==sum(x['correct'] for x in prows) and saved['derived_transport_accepted']==ps['complete_tasks'],'A1 score differs from independent raw recomputation')
 for k in ['sum_input_tokens','sum_output_tokens','known_input_tokens','known_output_tokens']:require(saved['resources'][k]==ps[k],'A1 usage differs')
 expected_files={'runs/.integrity.lock'};expected_dirs={'runs'}
 for j in cf['jobs']:
  prefix='runs/'+j['group_id']+'/'+j['procedure'];expected_files.update(prefix+'/'+x for x in ['prompt.txt','record.json','attempt_01/attempt_started.json','attempt_01/events.jsonl','attempt_01/stderr.txt','attempt_01/response.json'])
 for p in expected_files:expected_dirs.update(str(v) for v in Path(p).parents if str(v)!='.')
 actual_files=set();actual_dirs={'runs'}
 for p in (C/'runs').rglob('*'):
  require(not p.is_symlink(),'Symlink in challenge results')
  (actual_files if p.is_file() else actual_dirs).add(str(p.relative_to(C)))
 require(actual_files==expected_files and actual_dirs==expected_dirs,'Incomplete or unplanned challenge inventory')
 all_sources={R/p for p in original_inputs}|{C/p for p in actual_files}|{C/'authorization.json',C/'frozen.json',C/'driver.py'}|{a1/p for p in am['outputs_sha256']}|{a1/'manifest.json'}
 before=snapshot(all_sources)
 crows=[];intervals=[];warning_counts=Counter();records={};failures=[]
 for j in cf['jobs']:
  d=C/'runs'/j['group_id']/j['procedure'];a=d/'attempt_01';rec=read(d/'record.json');marker=read(a/'attempt_started.json');i=citems[j['item_id']];key=ckeys[j['item_id']];text=H['prompt_text'](prompts,i,j['procedure'],'challenge')
  require(rec['job']==marker['job']==j and rec['challenge_frozen_sha256']==marker['challenge_frozen_sha256']==chash,'Challenge task identity')
  require(rec['first_origin']==marker['first_origin']=='authored_fixed_draft' and rec['posthoc_exploratory'] is True and marker['posthoc_exploratory'] is True,'Authored/posthoc origin')
  require(rec['original_strict_gate_status']=='technical_block' and marker['phase']==PHASE and marker['original_gate_authorizes_run'] is False and marker['attempt']==1,'Strict gate or attempt metadata')
  require(rec['first_sha256']==marker['first_sha256']==digest(i['draft_text']) and rec['prompt_sha256']==marker['prompt_sha256']==digest(text) and (d/'prompt.txt').read_text()==text,'Prompt/fixed first mismatch')
  require(type(rec['has_response']) is bool and rec['has_response'] is True,'Missing final response')
  require(set(rec['artifact_sha256'])=={'attempt_started.json','events.jsonl','stderr.txt','response.json'} and all(sha(a/p)==h for p,h in rec['artifact_sha256'].items()),'Challenge raw artifact hash/coverage')
  require(stamp(cf['created_utc'])<=stamp(marker['started_utc'])<=stamp(rec['finished_utc']),'Challenge chronology')
  events=[json.loads(s) for s in (a/'events.jsonl').read_text().splitlines() if s.strip()];cl=classify_raw(events,(a/'response.json').read_text(),rec['returncode'],(a/'stderr.txt').read_text(),cf['diagnostic_allowlist'])
  require(cl['status']==rec['classification']['status'] and cl['parsed']==rec['classification']['parsed'],'Saved C classification differs')
  require(all(cl[k]==rec['classification'][k] for k in ['thread_id','usage','errors']),'Saved C session/usage/errors differs')
  # Resource and session provenance remains in raw events even when the frozen
  # classifier deliberately clears those fields on a failed task.
  raw_info=H['parse_events']((a/'events.jsonl').read_text())
  require(len(raw_info['sessions'])==1 and isinstance(raw_info['sessions'][0],str) and raw_info['sessions'][0].strip(),'Missing raw session identity')
  raw_sid=raw_info['sessions'][0];raw_usage=raw_info['usages'][0] if len(raw_info['usages'])==1 and isinstance(raw_info['usages'][0],dict) else {}
  sessions.append(raw_sid);warning_counts.update(e.get('message','') for e in raw_info['errors']);intervals.append((marker['started_utc'],rec['finished_utc']))
  attempt={'input_tokens':H['token'](raw_usage.get('input_tokens')),'output_tokens':H['token'](raw_usage.get('output_tokens')),'sessions':[raw_sid],'seconds':rec['seconds']}
  raw_parsed=H['schema_parse']((a/'response.json').read_text());raw_action=raw_parsed['action'] if raw_parsed else None
  primary_action=cl['parsed']['action'] if cl['status']=='complete' else None
  if cl['status']!='complete':
   failures.append({**j,'draft_condition':i['draft_condition'],'record_path':str((d/'record.json').relative_to(R)),'stderr_path':str((a/'stderr.txt').relative_to(R)),'stored_problem':rec['classification']['problem'],'independent_problems':cl['problem'],'returncode':rec['returncode'],'raw_action':raw_action,'correct_action':key['correct_action'],'raw_content_correct':raw_action==key['correct_action'],'primary_correct':0,'raw_usage':raw_usage,'raw_session_id':raw_sid,'resampled':False})
  crows.append({**j,'family_id':i['family_id'],'error_type':i['error_type'],'state':i['state'],'advice':None,'draft_condition':i['draft_condition'],'first_origin':'authored_fixed_draft','status':cl['status'],'correct':int(cl['status']=='complete' and primary_action==key['correct_action']),'correct_action':key['correct_action'],'action':primary_action,'raw_action':raw_action,'raw_content_correct':int(raw_action==key['correct_action']),'attempts':[attempt],'record_sha256':sha(d/'record.json')})
  records[str((d/'record.json').relative_to(R))]=sha(d/'record.json')
 require(len(sessions)==len(set(sessions))==208,'Cross-phase duplicate session')
 require(peak(intervals)<=12 and peak(pintervals)<=12,'Recorded concurrency exceeds12')
 cs=H['phase_stats'](crows,'challenge');require(cs['planned_tasks']==cs['terminal_tasks']==128,'Challenge denominator/count')
 require(snapshot(all_sources)==before,'Inputs changed during audit')
 return {'audit_skill':'experiment-audit','stage':'final-raw-independent','verdict':'WARN','integrity_status':'pass','scientific_status':'posthoc_exploratory_only_original_gate_blocked','review_independence':'same-family','acceptance_status':'provisional','generated_at':datetime.now(timezone.utc).isoformat(),'original_gate_status':'technical_block','original_challenge_allowed':False,'original_p0_strict':{'planned':80,'complete':0,'technical_failure':80,'failure_policy_correct':0,'interpretation':'Execution-policy failures, not content mistakes'},'A1_p0_posthoc':ps,'extra_C':cs,'extra_C_failures':failures,'extra_C_raw_content_correct_all_finals':sum(x['raw_content_correct'] for x in crows),'extra_C_status':'posthoc_exploratory; separately authorized deviation from original blocked gate','all_subject_attempts':208,'unique_sessions':208,'no_resampling':True,'recorded_peak_concurrency':{'p0':peak(pintervals),'extra_C':peak(intervals)},'diagnostic_warning_counts_extra_C':dict(warning_counts),'combined_subject_usage':H['usage_summary']([a for row in prows+crows for a in row['attempts']]),'verified_billed_cost':None,'management_authoring_review_usage':'unknown','original_frozen_sha256':fhash,'extra_C_frozen_sha256':chash,'source_hashes':before,'p0_rows':prows,'extra_C_rows':crows,'real_model_calls_by_audit':0,'scope':'simulation_only; eight development families, four/type; no human/external expert/heldout validation; no p-values, superiority/equivalence claims'}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--write-final',action='store_true');args=ap.parse_args();require(args.write_final,'Use only --write-final after root confirms128 terminal records')
 result=audit();out=R/'audits/FINAL_EXPERIMENT_AUDIT.json';require(not out.exists(),'Refuse overwrite of final audit');out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'saved':str(out),'verdict':result['verdict'],'extra_C':result['extra_C']['procedures'],'usage':result['combined_subject_usage']},ensure_ascii=False,indent=2))
