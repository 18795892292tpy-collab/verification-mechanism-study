#!/usr/bin/env python3
"""Isolated post-hoc authored-draft challenge; never alters frozen V3 or its gate."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, random, re, socket, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import jsonschema

ROOT=Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
HERE=ROOT/'amendments/A1_posthoc/challenge'
sys.path.insert(0,str(ROOT/'harness'))
import runner as original
from integrity import DirectoryLock, _write_once

DIAGNOSTICS=(
 'Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /home/grf/.codex/config.toml.',
 'Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.',
 'Exceeded skills context budget. All skill descriptions were removed and 144 additional skills were not included in the model-visible skills list.',
)
EXPECTED_SEQUENCE=['thread.started','item.completed','item.completed','turn.started','item.completed','item.completed','turn.completed']
FROZEN=HERE/'frozen.json'; RUNS=HERE/'runs'; AMENDMENT=HERE/'authorization.json'
def sha(v):return hashlib.sha256(v if isinstance(v,bytes) else v.encode()).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def seal(p,data):
 if not _write_once(p,data):raise RuntimeError('Refusing overwrite: '+str(p))
def seal_text(p,data):
 with p.open('x',encoding='utf8') as h:h.write(data);h.flush();os.fsync(h.fileno())
def items():return {x['item_id']:x for x in read(ROOT/'prompts/challenge_items.json')}
def schedule():
 result=[{'group_id':i['item_id']+'_r1','item_id':i['item_id'],'repeat':1,'procedure':p} for i in items().values() for p in ['P1','P3','P7','P8']]
 random.Random(20261109).shuffle(result)
 assert len(result)==128 and len({(j['group_id'],j['procedure']) for j in result})==128
 return result

def baseline_check():
 if socket.gethostname()!='liekkas' or Path.cwd().resolve()!=ROOT:raise RuntimeError('Requires canonical V3 original root and host')
 f=original.verify();strict=read(ROOT/'analysis/decision_gate.json')
 if strict['frozen_hash']!=file_sha(ROOT/'protocol/frozen.json') or strict['challenge_allowed'] is not False or strict['status']!='technical_block':raise RuntimeError('Original strict gate is not the frozen technical block')
 for path,h in strict['p0_record_sha256'].items():
  if file_sha(ROOT/path)!=h:raise RuntimeError('Prior P0 record changed')
 if len(strict['p0_record_sha256'])!=80:raise RuntimeError('Original 80 P0 records required')
 # Revalidate original records, raw events, output files and metadata before any new work.
 byid={x['item_id']:x for x in original.load_items('p0')}
 for job in f['phase_schedule']['p0']['jobs']:
  original.validate_record('p0',job,byid[job['item_id']],None,file_sha(ROOT/'protocol/frozen.json'))
 return f

def authorization_check():
 a=read(AMENDMENT)
 required={'kind':'explicit_posthoc_challenge','prior_strict_gate_outcome':'technical_block','original_gate_challenge_allowed':False,'phase':'independent_authored_draft_exploration','first_origin':'authored_fixed_draft','max_planned_tasks':128,'max_workers':12,'posthoc_exploratory':True,'original_frozen_sha256':file_sha(ROOT/'protocol/frozen.json'),'original_gate_sha256':file_sha(ROOT/'analysis/decision_gate.json'),'challenge_items_sha256':file_sha(ROOT/'prompts/challenge_items.json'),'challenge_keys_sha256':file_sha(ROOT/'keys/challenge_keys.json')}
 for k,v in required.items():
  if a.get(k)!=v:raise RuntimeError('Authorization mismatch: '+k)
 rel=Path(a['posthoc_analysis_path'])
 if rel.is_absolute() or '..' in rel.parts or rel.parts[:2]!=('amendments','A1_posthoc'):raise RuntimeError('Invalid derived analysis path')
 if file_sha(ROOT/rel)!=a['posthoc_analysis_sha256']:raise RuntimeError('Derived analysis changed')
 if rel.as_posix()!='amendments/A1_posthoc/results/threshold_diagnostic.json':raise RuntimeError('Unexpected diagnostic path')
 derived=read(ROOT/rel)
 expected={'analysis_label':'posthoc_exploratory','NOT_A_RUN_GATE':True,'automatic_execution_authorized':False,'original_frozen_status':'technical_block','original_challenge_allowed':False,'derived_transport_accepted_all_80':True,'hypothetical_threshold_status':'development_gate_failed'}
 if any(derived.get(k)!=v for k,v in expected.items()):raise RuntimeError('Derived analysis content does not prove the declared exploratory gate')
 resultdir=ROOT/'amendments/A1_posthoc/results';summary=resultdir/'summary.json';provenance=resultdir/'manifest.json';inputs=resultdir/'input_sha256.json'
 for name,path in [('posthoc_summary_sha256',summary),('posthoc_manifest_sha256',provenance),('posthoc_input_manifest_sha256',inputs)]:
  if a.get(name)!=file_sha(path):raise RuntimeError('Derived provenance differs: '+name)
 sd=read(summary);man=read(provenance)
 if sd.get('analysis_label')!='posthoc_exploratory' or sd.get('original_frozen_sha256')!=file_sha(ROOT/'protocol/frozen.json') or sd.get('derived_transport_accepted')!=80 or sd.get('planned_p0')!=80 or sd.get('original_gate_status')!='technical_block':raise RuntimeError('Derived summary inconsistent')
 if man.get('analysis_label')!='posthoc_exploratory' or man.get('original_frozen_sha256')!=file_sha(ROOT/'protocol/frozen.json') or man['outputs_sha256'].get('threshold_diagnostic.json')!=file_sha(ROOT/rel) or man['outputs_sha256'].get('summary.json')!=file_sha(summary) or man['outputs_sha256'].get('input_sha256.json')!=file_sha(inputs):raise RuntimeError('Derived manifest inconsistent')
 hashes=read(inputs)
 if len(hashes)<500 or hashes.get('analysis/decision_gate.json')!=file_sha(ROOT/'analysis/decision_gate.json') or hashes.get('protocol/frozen.json')!=file_sha(ROOT/'protocol/frozen.json'):raise RuntimeError('Derived input inventory incomplete')
 for name,digest in hashes.items():
  q=Path(name)
  if q.is_absolute() or '..' in q.parts or file_sha(ROOT/q)!=digest:raise RuntimeError('Derived input changed: '+name)
 if a.get('posthoc_gate_result')!='development_gate_failed':raise RuntimeError('Requires explicit posthoc gate failure')
 if a.get('jobs')!=schedule() or a.get('diagnostic_allowlist')!=list(DIAGNOSTICS):raise RuntimeError('Authorized job list or diagnostic scope differs')
 return a

def manifest():
 baseline_check();authorization_check()
 return {'version':1,'phase':'independent_authored_draft_exploration','created_utc':now(),
   'posthoc_exploratory':True,'strict_original_gate_override':False,
   'first_origin':'authored_fixed_draft','original_frozen_sha256':file_sha(ROOT/'protocol/frozen.json'),
   'original_gate_sha256':file_sha(ROOT/'analysis/decision_gate.json'),
   'authorization_sha256':file_sha(AMENDMENT),'driver_sha256':file_sha(Path(__file__)),
   'inputs':{str(p.relative_to(ROOT)):file_sha(p) for p in [ROOT/'prompts/challenge_items.json',ROOT/'keys/challenge_keys.json',ROOT/'protocol/prompts.json',ROOT/'protocol/output_schema.json',ROOT/'harness/runner.py',ROOT/'harness/integrity.py']},
   'diagnostic_allowlist':list(DIAGNOSTICS),'event_sequence':EXPECTED_SEQUENCE,
   'model':original.MODEL,'effort':original.EFFORT,'flags':original.FLAGS,'max_workers':12,'max_attempts':1,'original_max_attempts':2,'retry_policy':'Conservative: at most one attempt per task; on failure stop and require manual audit, no automatic retries.','timeout_seconds':600,'jobs':schedule()}

def verify():
 f=read(FROZEN);current=manifest()
 try:created=datetime.datetime.fromisoformat(f['created_utc'])
 except (KeyError,TypeError,ValueError):raise RuntimeError('Invalid challenge freeze timestamp')
 if created.tzinfo is None or created.utcoffset() is None or created>datetime.datetime.now(datetime.timezone.utc):raise RuntimeError('Challenge freeze timestamp must be timezone-aware and not in the future')
 for k in set(current)-{'created_utc'}:
  if f.get(k)!=current[k]:raise RuntimeError('Frozen challenge identity mismatch: '+k)
 return f

def classify(stdout,output,code,stderr=""):
 """Narrow allowlist; all unknown/error/tool/lifecycle/final disagreements fail closed."""
 try:
  if stderr and not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z  WARN codex_http_client::native_roots: encountered errors while loading native root certificates native_root_error_count=2\n?',stderr):raise ValueError('unrecognized stderr')
  ev=[json.loads(line) for line in stdout.splitlines() if line.strip()]
  if [x.get('type') for x in ev]!=EXPECTED_SEQUENCE:raise ValueError('unexpected event sequence')
  expected_keys=[{'type','thread_id'},{'type','item'},{'type','item'},{'type'},{'type','item'},{'type','item'},{'type','usage'}]
  if any(set(event)!=keys for event,keys in zip(ev,expected_keys)):raise ValueError('unexpected top-level event payload')
  if type(code) is not int:raise ValueError('invalid return code type')
  if any('item' in ev[i] for i in (0,3,6)):raise ValueError('unexpected item in lifecycle event')
  if not isinstance(ev[0].get('thread_id'),str) or not ev[0]['thread_id'].strip():raise ValueError('invalid thread')
  for i in (1,2,4):
   item=ev[i].get('item',{})
   if set(item)!= {'id','type','message'} or item['type']!='error' or not isinstance(item['id'],str):raise ValueError('invalid diagnostic item')
  item=ev[5].get('item',{})
  if set(item)!={'id','type','text'} or item.get('type')!='agent_message' or not isinstance(item.get('id'),str):raise ValueError('invalid final item')
  errors=[x.get('item',{}).get('message') for x in ev if x.get('item',{}).get('type')=='error']
  if tuple(errors)!=DIAGNOSTICS:raise ValueError('unrecognized diagnostics')
  if any(x.get('item',{}).get('type') not in ('error','agent_message') for x in ev if x.get('type')=='item.completed'):raise ValueError('unknown or tool item')
  msgs=[x['item'].get('text') for x in ev if x.get('item',{}).get('type')=='agent_message']
  if code!=0 or len(msgs)!=1 or output is None or msgs[0]!=output:raise ValueError('failed command or final source disagreement')
  parsed=json.loads(output);jsonschema.validate(parsed,original.SCHEMA)
  return {'status':'complete','parsed':parsed,'thread_id':ev[0]['thread_id'],'usage':ev[-1].get('usage'),'errors':errors,'problem':None}
 except Exception as e:
  return {'status':'technical_or_protocol_failure','parsed':None,'thread_id':None,'usage':None,'errors':[],'problem':str(e)}

def prompt_for(job):
 item=items()[job['item_id']]
 return original.build_prompt(job,item,item['draft_text'])

def check_task_dir(job, frozen_hash):
 d=RUNS/job['group_id']/job['procedure'];rec=d/'record.json'
 if not d.exists():return None
 if d.is_symlink() or any(p.is_symlink() for p in d.rglob('*')):raise RuntimeError('Symlink in run tree')
 if not any(d.iterdir()):return None
 if not rec.exists():raise RuntimeError('Unsealed task exists; manual audit required: '+str(d))
 r=read(rec);p=prompt_for(job);a=d/'attempt_01'
 if r['job']!=job or r['challenge_frozen_sha256']!=frozen_hash or r['prompt_sha256']!=sha(p) or r['first_sha256']!=sha(items()[job['item_id']]['draft_text']) or r.get('first_origin')!='authored_fixed_draft' or r.get('posthoc_exploratory') is not True or r.get('original_strict_gate_status')!='technical_block':raise RuntimeError('Record identity differs')
 if type(r.get('has_response')) is not bool or r['has_response']!=(a/'response.json').is_file():raise RuntimeError('Response existence differs from sealed metadata')
 if set(r['artifact_sha256'])!=({'attempt_started.json','events.jsonl','stderr.txt','response.json'} if r['has_response'] else {'attempt_started.json','events.jsonl','stderr.txt'}):raise RuntimeError('Unexpected artifact set')
 marker=read(a/'attempt_started.json')
 if marker['job']!=job or marker['challenge_frozen_sha256']!=frozen_hash or marker['prompt_sha256']!=sha(p) or marker['first_sha256']!=r['first_sha256'] or marker.get('phase')!='independent_authored_draft_exploration' or marker.get('first_origin')!='authored_fixed_draft' or marker.get('posthoc_exploratory') is not True or marker.get('original_gate_authorizes_run') is not False or marker.get('attempt')!=1:raise RuntimeError('Marker identity differs')
 if datetime.datetime.fromisoformat(marker['started_utc']) < datetime.datetime.fromisoformat(read(FROZEN)['created_utc']) or datetime.datetime.fromisoformat(marker['started_utc']) > datetime.datetime.fromisoformat(r['finished_utc']):raise RuntimeError('Invalid task timing')
 for name,h in r['artifact_sha256'].items():
  if file_sha(a/name)!=h:raise RuntimeError('Run artifact changed: '+str(a/name))
 if (d/'prompt.txt').read_text()!=p:raise RuntimeError('Prompt changed')
 stdout=(a/'events.jsonl').read_text();output=(a/'response.json').read_text() if (a/'response.json').exists() else None
 c=classify(stdout,output,r['returncode'],(a/'stderr.txt').read_text())
 if c!=r['classification']:raise RuntimeError('Record does not rederive from events')
 return r

def ensure_runtime_empty():
 empty=HERE/'runtime_empty'
 if HERE.is_symlink() or empty.is_symlink():raise RuntimeError('Unsafe runtime directory symlink')
 empty.mkdir(exist_ok=True)
 if not empty.is_dir() or empty.resolve()!=HERE.resolve()/'runtime_empty' or any(empty.iterdir()):raise RuntimeError('Unsafe or nonempty runtime directory')
 return empty

def one(job,frozen_hash):
 old=check_task_dir(job,frozen_hash)
 if old is not None:return old
 empty=ensure_runtime_empty()
 item=items()[job['item_id']];d=RUNS/job['group_id']/job['procedure'];a=d/'attempt_01';a.mkdir(parents=True,exist_ok=False)
 prompt=prompt_for(job);seal_text(d/'prompt.txt',prompt)
 marker={'job':job,'phase':'independent_authored_draft_exploration','first_origin':'authored_fixed_draft','posthoc_exploratory':True,'original_gate_authorizes_run':False,'original_gate_binding':'technical_block; separate exploratory amendment', 'first_sha256':sha(item['draft_text']),'challenge_frozen_sha256':frozen_hash,'prompt_sha256':sha(prompt),'attempt':1,'started_utc':now()}
 seal(a/'attempt_started.json',marker)
 env=os.environ.copy()
 for k in ['OPENAI_API_KEY','OPENAI_BASE_URL','AZURE_OPENAI_API_KEY','CODEX_THREAD_ID']:env.pop(k,None)
 if ensure_runtime_empty()!=empty:raise RuntimeError('Runtime directory changed')
 cmd=[original.CLI,'exec',*original.FLAGS,'-C',str(empty),'--output-schema',str(ROOT/'protocol/output_schema.json'),'-o',str(a/'response.json'),'-']
 t=time.monotonic()
 try:
  cp=subprocess.run(cmd,input=prompt,text=True,capture_output=True,env=env,timeout=600);stdout,stderr,code=cp.stdout,cp.stderr,cp.returncode
 except (OSError,subprocess.TimeoutExpired) as e:
  stdout=e.stdout or '' if isinstance(e,subprocess.TimeoutExpired) else '';stderr=e.stderr or '' if isinstance(e,subprocess.TimeoutExpired) else str(e);code=None
  if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
  if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
 seal_text(a/'events.jsonl',stdout);seal_text(a/'stderr.txt',stderr)
 output=(a/'response.json').read_text() if (a/'response.json').exists() else None
 c=classify(stdout,output,code,stderr)
 fs=['attempt_started.json','events.jsonl','stderr.txt']+(['response.json'] if output is not None else [])
 record={'job':job,'first_origin':'authored_fixed_draft','posthoc_exploratory':True,'original_strict_gate_status':'technical_block','challenge_frozen_sha256':frozen_hash,'prompt_sha256':sha(prompt),'first_sha256':sha(item['draft_text']),'returncode':code,'has_response':output is not None,'finished_utc':now(),'seconds':time.monotonic()-t,'artifact_sha256':{n:file_sha(a/n) for n in fs},'classification':c}
 seal(d/'record.json',record);return record

def inventory(jobs):
 allowed={(j['group_id'],j['procedure']) for j in jobs}
 if not RUNS.exists():return
 if RUNS.is_symlink() or not RUNS.is_dir():raise RuntimeError('Unsafe run root')
 for p in RUNS.rglob('*'):
  parts=p.relative_to(RUNS).parts
  if p.is_symlink():raise RuntimeError('Symlink in run inventory')
  if len(parts)==1:
   ok=(parts[0]=='.integrity.lock' and p.is_file()) or (any(g==parts[0] for g,_ in allowed) and p.is_dir())
  elif len(parts)==2:ok=(parts[0],parts[1]) in allowed and p.is_dir()
  elif len(parts)==3:ok=(parts[0],parts[1]) in allowed and ((parts[2] in ('record.json','prompt.txt') and p.is_file()) or (parts[2]=='attempt_01' and p.is_dir()))
  elif len(parts)==4:ok=(parts[0],parts[1]) in allowed and parts[2]=='attempt_01' and parts[3] in ('attempt_started.json','events.jsonl','stderr.txt','response.json') and p.is_file()
  else:ok=False
  if not ok:raise RuntimeError('Unplanned artifact: '+str(p))

def run():
 for p in [ROOT/'amendments', ROOT/'amendments/A1_posthoc', HERE, RUNS]:
  if p.is_symlink():raise RuntimeError('Symlink in challenge path: '+str(p))
 RUNS.mkdir(parents=True,exist_ok=True)
 with DirectoryLock(RUNS):
  f=verify();h=file_sha(FROZEN);jobs=f['jobs'];inventory(jobs)
  # Verify every existing result, including session uniqueness, before calls.
  p0=[read(ROOT/path) for path in read(ROOT/'analysis/decision_gate.json')['p0_record_sha256']]
  source_threads=[t for record in p0 for attempt in record['attempts'] for t in attempt.get('thread_ids',[])]
  if len(source_threads)!=80 or len(set(source_threads))!=80:raise RuntimeError('Original P0 session identities invalid')
  seen=set(source_threads);pending=[]
  for j in jobs:
   existing=check_task_dir(j,h)
   if existing is None:pending.append(j);continue
   c=existing['classification']
   if c['status']!='complete':raise RuntimeError('Prior failure requires manual audit; no dispatch')
   if c['thread_id'] in seen:raise RuntimeError('Duplicate prior session')
   seen.add(c['thread_id'])
  futures={};it=iter(pending);stopped=False
  with ThreadPoolExecutor(max_workers=12) as pool:
   while True:
    while not stopped and len(futures)<12:
     try:j=next(it)
     except StopIteration:break
     futures[pool.submit(one,j,h)]=j
    if not futures:break
    done,_=wait(futures,return_when=FIRST_COMPLETED)
    for future in done:
     j=futures.pop(future)
     try:r=future.result()
     except Exception as e:stopped=True;print(json.dumps({'event':'task_exception','job':j,'error':str(e)}),flush=True);continue
     print(json.dumps({'event':'task_result','job':j,'status':r['classification']['status']}),flush=True)
     c=r['classification']
     if c['status']!='complete':stopped=True
     elif c['thread_id'] in seen:
      stopped=True;print(json.dumps({'event':'duplicate_session','thread_id':c['thread_id']}),flush=True)
     else:seen.add(c['thread_id'])
  if stopped:raise SystemExit(75)
  print(json.dumps({'event':'invocation_complete','planned':128,'posthoc_exploratory':True}),flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--freeze',action='store_true');a.add_argument('--verify',action='store_true');a.add_argument('--run',action='store_true');args=a.parse_args()
 if sum([args.freeze,args.verify,args.run])!=1:a.error('Choose one action')
 if args.freeze:
  with DirectoryLock(HERE):
   seal(FROZEN,manifest());print(json.dumps({'frozen_sha256':file_sha(FROZEN)}))
 elif args.verify:verify();print('Verified; no calls')
 else:run()
