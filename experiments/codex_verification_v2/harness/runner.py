#!/usr/bin/env python3
"""New, append-only Codex experiment; no DeepSeek or direct provider API."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import argparse, csv, hashlib, json, os, random, re, socket, subprocess, threading, time
from integrity import DirectoryLock, _write_once
import jsonschema

R = Path(__file__).resolve().parents[1]
CLI = '/home/grf/.local/bin/codex'
MODEL, EFFORT = 'gpt-6-astra', 'ultra'
PROCS = ['P0','P1','P3','P7','P8']
BASE = ('这是关于虚构学校制度的封闭材料决策任务，不是真实被试调查。'
        '你以学校行政决策者身份，仅依据给出的制度、事实和选项作出决定。'
        '建议备忘录可能正确，也可能错误，请独立判断。不得补充档案外事实，不改变选项承诺。'
        '不得使用任何工具、搜索、文件读取、外部通信或其他代理。'
        '只输出符合格式的JSON：action为选项字母，cited_sources为支持决定的材料编号，'
        'brief_justification为不超过180字的简短理由，confidence为1至5的整数。'
        '不输出长推理过程。')
P3 = ('请逐项复核先前决定及建议所依据的材料：'
      '1.适用对象：是否包括本案的学校、人群、字段和用途；'
      '2.时间与版本：决定时是否生效、有无替代版本；'
      '3.授权范围：批准的金额、对象和用途是否覆盖所选行动；'
      '4.证据支持：材料原文是否支持所选行动；'
      '5.信息充分性：是否缺少作出决定所需的材料。'
      '复核后保留或修改决定，按同一格式给出最终JSON。')
ADD7 = '6.条款条件：逐项核对所引条款的触发条件与例外条件是否在本案满足，并据此复核所选行动。'
ADD8 = '6.通用复核：逐项核对先前回答的内容完整性与前后一致性是否存在遗漏，并据此复核所选行动。'
REVIEWS = {
 'P1':'请从头重新阅读全部档案、建议与可选行动，独立重新考虑先前决定。对各选项重新核对依据，必要时修改决定，按同一格式给出最终JSON。',
 'P3':P3, 'P7':P3+'\n'+ADD7, 'P8':P3+'\n'+ADD8}
SCHEMA = {'type':'object','additionalProperties':False,'required':['action','cited_sources','brief_justification','confidence'],
 'properties':{'action':{'type':'string','enum':['A','B','C','D']},'cited_sources':{'type':'array','items':{'type':'string'}},
 'brief_justification':{'type':'string','maxLength':180},'confidence':{'type':'integer','minimum':1,'maximum':5}}}
FLAGS = ['--ignore-user-config','--ephemeral','--skip-git-repo-check','--sandbox','read-only',
 '--disable','apps','--disable','plugins','--disable','shell_tool','--disable','unified_exec',
 '--disable','multi_agent','--disable','browser_use','--disable','computer_use',
 '--disable','view_image','--disable','image_generation','--disable','skill_search',
 '--disable','sleep_tool','--disable','workspace_dependencies','--disable','shell_snapshot',
 '--disable','in_app_browser','--disable','code_mode_host',
 '-c','features.skip_host_skill_discovery=true','-c','web_search="disabled"',
 '-c','project_doc_max_bytes=0','-c','approval_policy="never"',
 '-c','model_provider="openai"','-c','model_reasoning_effort="ultra"',
 '-m',MODEL,'--json']

def now(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b.encode() if isinstance(b,str) else b).hexdigest()
def file_sha(p): return sha(Path(p).read_bytes())
def dump(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def read(p): return json.loads(Path(p).read_text())

SCHEDULE_SEED = 20261107
PHASE = 'dev'
REPEATS = (1, 2)
MAX_ATTEMPTS = 2
MAX_WORKERS = 3
TIMEOUT = 600
FROZEN_FILES = [
 'protocol/approved_plan.md','protocol/runtime_identity.json','protocol/EXECUTION_AMENDMENT.md',
 'protocol/output_schema.json','protocol/prompts.json','protocol/backend.json','protocol/analysis_plan.json',
 'harness/runner.py','harness/integrity.py','harness/evaluate.py','harness/offline_audit.py','analysis/progress.py',
 'tests/test_integrity.py','tests/test_runner_offline.py','tests/test_v2.py','tests/test_evaluate.py',
 'prompts/dev_items.json','keys/dev_keys.json','cases/build_cases.py','cases/build_validation.json',
 'cases/factual_truth_tables.json','cases/CASE_SPEC.md','cases/AUTHORING_REVIEW.md',
 'audits/case_review.json','audits/integrity_tests.json','audits/blind_review_answers.json',
 'audits/blind_packet.json','keys/blind_mapping.json']

def seal_json(path, value):
 """Publish raw/provenance JSON atomically, never overwrite a destination."""
 if not _write_once(Path(path), value):
  raise RuntimeError('Refusing to overwrite sealed artifact: '+str(path))

def seal_text(path, text):
 with Path(path).open('x') as stream:
  stream.write(text);stream.flush();os.fsync(stream.fileno())

def execution_config():
 return {'cli':CLI,'flags':FLAGS,'model':MODEL,'effort':EFFORT,'sampling_seed':None,
  'max_workers':MAX_WORKERS,'timeout_s':TIMEOUT,'max_total_attempts':MAX_ATTEMPTS,
  'reuse_first':True,'schema_sha256':sha(json.dumps(SCHEMA,sort_keys=True)),
  'unknown_event_policy':'reject','allowed_item_types':['agent_message','reasoning','error'],
  'technical_retry':'only when no final response exists; never retry parsing, tool use or a wrong answer',
  'service_failure_policy':'quota, authentication and network/transport failure: stop dispatch; preserve started calls; sealed no-final attempt may resume within two total attempts',
  'environment_removed':['OPENAI_API_KEY','OPENAI_BASE_URL','AZURE_OPENAI_API_KEY','CODEX_THREAD_ID'],
  'repeats':list(REPEATS),'procedures':PROCS,'phase':PHASE,'schedule_seed':SCHEDULE_SEED}

def runtime_identity():
 cli=Path(CLI).resolve(strict=True)
 package=cli.parent.parent
 dependencies=[package/'package.json',*package.glob('node_modules/@openai/codex-*/package.json'),
  *package.glob('node_modules/@openai/codex-*/vendor/*/bin/codex'),*package.glob('vendor/*/bin/codex')]
 dependency_hashes={str(p.resolve()):file_sha(p) for p in dependencies if p.is_file()}
 return {'hostname':socket.gethostname(),'root':str(R.resolve()),'cli_path':CLI,
  'cli_resolved':str(cli),'cli_sha256':file_sha(cli),'cli_dependency_sha256':dependency_hashes,
  'home':str(Path.home()),'codex_home':os.environ.get('CODEX_HOME',str(Path.home()/'.codex'))}

def initialize_protocol():
 if (R/'protocol/frozen.json').exists():raise RuntimeError('Already frozen; do not overwrite')
 assert abs(len(ADD7)-len(ADD8))/max(len(ADD7),len(ADD8))<=.05
 dump(R/'protocol/output_schema.json',SCHEMA)
 dump(R/'protocol/prompts.json',{'base':BASE,'reviews':REVIEWS,'extra_chars':{'P7':len(ADD7),'P8':len(ADD8)}})
 dump(R/'protocol/backend.json',execution_config())

def load_items():
 value=read(R/'prompts/dev_items.json')
 return value['items'] if isinstance(value,dict) else value

def build_schedule(items):
 ids=[i['item_id'] for i in items]
 if len(items)!=80 or len(set(ids))!=80:raise RuntimeError('Expected exactly 80 unique dev items')
 if any(not re.fullmatch(r'[A-Za-z0-9_-]+',i) for i in ids):raise RuntimeError('Unsafe item identifier')
 families={i['family_id'] for i in items}
 if len(families)!=8:raise RuntimeError('Expected 8 independent families')
 for family in families:
  subset=[i for i in items if i['family_id']==family]
  states={i['state'] for i in subset};advice={i['advice'] for i in subset}
  if (len(subset)!=10 or len(states)!=5 or len(advice)!=2 or
      len({(i['state'],i['advice']) for i in subset})!=10):
   raise RuntimeError('Expected 5 states x 2 advice versions within every family')
 jobs=[{'group_id':i['item_id']+f'_r{repeat}','item_id':i['item_id'],'repeat':repeat,'procedure':p}
       for i in items for repeat in REPEATS for p in PROCS]
 random.Random(SCHEDULE_SEED).shuffle(jobs)
 return jobs

def freeze():
 initialize_protocol()
 for name in FROZEN_FILES:
  if not (R/name).is_file():raise FileNotFoundError(name)
 jobs=build_schedule(load_items())
 f={'created_utc':now(),'experiment':'codex_verification_v2','model_requested':MODEL,'effort_requested':EFFORT,
    'provider_snapshot':None,'schedule_seed':SCHEDULE_SEED,'sampling_seed':None,
    'runtime':runtime_identity(),'execution_config':execution_config(),
    'phase_schedule':{'dev':{'items':80,'groups':160,'tasks':800,'jobs':jobs}},
    'sha256':{x:file_sha(R/x) for x in FROZEN_FILES}}
 seal_json(R/'protocol/frozen.json',f)
 p=R/'runs/dev/plan.csv';p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',newline='') as h:
  w=csv.DictWriter(h,fieldnames=['group_id','item_id','repeat','procedure']);w.writeheader();w.writerows(jobs)
 print(json.dumps({'frozen':True,'dev_tasks':800,'groups':160,'hash':file_sha(R/'protocol/frozen.json')}),flush=True)

def verify():
 f=read(R/'protocol/frozen.json')
 if f.get('experiment')!='codex_verification_v2':raise RuntimeError('Wrong experiment manifest')
 if f.get('execution_config')!=execution_config():raise RuntimeError('Frozen execution parameters changed')
 if f.get('runtime')!=runtime_identity():raise RuntimeError('Host, target directory or CLI identity changed')
 if set(f.get('sha256',{}))!=set(FROZEN_FILES):raise RuntimeError('Frozen file inventory changed')
 for p,h in f['sha256'].items():
  if file_sha(R/p)!=h:raise RuntimeError('Frozen file changed: '+p)
 expected={'dev':{'items':80,'groups':160,'tasks':800,'jobs':build_schedule(load_items())}}
 if f.get('phase_schedule')!=expected:raise RuntimeError('Frozen 800-task schedule changed')
 # Once execution has begun, even a self-consistent edited manifest is refused.
 pin=R/'runs/dev/manifest_identity.json'
 if pin.exists() and read(pin)!= {'frozen_hash':file_sha(R/'protocol/frozen.json')}:
  raise RuntimeError('Run manifest hash changed')
 return f

class DispatchGate:
 """Shared circuit breaker. Running calls finish; no further attempts are started."""
 def __init__(self):
  self.event=threading.Event();self.reason=None;self.lock=threading.Lock()
 def stop(self,reason):
  with self.lock:
   if not self.event.is_set():self.reason=reason;self.event.set()
 @property
 def stopped(self):return self.event.is_set()

def service_block_reason(info,stderr,returncode,error=None):
 # Never scan the response text. Only transport diagnostics can trip the breaker.
 if returncode==0 and info['turn_completed'] and not info['top_level_errors']:return None
 diagnostic=json.dumps(info['top_level_errors']+info['error_items'],ensure_ascii=False)+' '+stderr
 diagnostic=(diagnostic+' '+(error or '')).lower()
 patterns={
  'quota_or_rate_limit':r'usage limit|quota|rate.?limit|too many requests|insufficient_quota|usage_limit_reached|\b429\b|credits? (?:exhausted|depleted)|limit reached|用量限制|额度|配额',
  'network_transport':r'\btls\b|\bssl\b|unexpected eof|connection (?:reset|refused|aborted|closed|timed out)|network (?:is )?unreachable|network error|error sending request|name resolution|dns (?:error|failure)|stream disconnected|failed to connect|could not connect|connecterror|timeout_600s',
  'authentication':r'authenticat|unauthorized|invalid.api.key|token (?:expired|invalid)|refresh.token|not logged in|login required|sign in|\b401\b|\b403\b|登录|认证',
 }
 for label,pattern in patterns.items():
  if re.search(pattern,diagnostic):return label
 return None

def events_info(stdout):
 events=[];threads=[];unexpected=[];errors=[];fatal=[];messages=[];completions=[];lifecycle=[]
 allowed={'thread.started','turn.started','item.started','item.updated','item.completed','turn.completed','turn.failed','error'}
 for line in stdout.splitlines():
  if not line.strip():continue
  try:e=json.loads(line)
  except json.JSONDecodeError:
   unexpected.append({'kind':'non_json_stdout','line_sha256':sha(line)})
   continue
  events.append(e)
  if not isinstance(e,dict):
   unexpected.append({'kind':'non_object_event','event':e});continue
  event_type=e.get('type')
  if event_type not in allowed:unexpected.append({'kind':'unknown_event_type','event':e})
  if event_type in ['thread.started','turn.started','turn.completed','turn.failed']:lifecycle.append(event_type)
  if event_type=='thread.started':threads.append(e.get('thread_id'))
  if event_type=='turn.completed':completions.append(e.get('usage'))
  if event_type in ['turn.failed','error']:fatal.append(e)
  item=e.get('item',{})
  if not isinstance(item,dict):unexpected.append({'kind':'invalid_item','item':item});continue
  if item and item.get('type') not in ['agent_message','reasoning','error']:unexpected.append(item)
  if item and item.get('type')=='error':errors.append(item)
  if event_type=='item.completed' and item.get('type')=='agent_message' and isinstance(item.get('text'),str) and item['text'].strip():
   messages.append(item['text'])
 lifecycle_errors=[]
 if len(threads)!=1 or not isinstance(threads[0],str) or not threads[0].strip():
  lifecycle_errors.append('Expected exactly one thread.started with one nonempty string thread_id')
 if lifecycle!=['thread.started','turn.started','turn.completed']:
  lifecycle_errors.append('Expected exactly one ordered thread.started / turn.started / turn.completed lifecycle')
 # Missing lifecycle events are normal for a connection failure before a turn.
 # A claimed successful completion, however, must satisfy the full invariant.
 if completions and lifecycle_errors:
  unexpected.append({'kind':'invalid_success_lifecycle','violations':lifecycle_errors})
 return {'usage':completions[0] if len(completions)==1 else None,'thread_ids':threads,
  'unexpected_items':unexpected,'error_items':errors,'top_level_errors':fatal,
  'turn_completed':bool(completions),'event_count':len(events),'completed_agent_messages':messages,
  'turn_completion_usages':completions,'lifecycle_events':lifecycle,'lifecycle_errors':lifecycle_errors}

def build_prompt(job,item,first_text):
 prompt=BASE+'\n\n档案与问题：\n'+item['public_text']
 if first_text is not None:prompt+='\n\n先前回答（原样提供，供独立复核）：\n'+first_text+'\n\n本次任务：\n'+REVIEWS[job['procedure']]
 else:prompt+='\n\n本次任务：给出你的决定。'
 return prompt

def validate_attempt(ad,meta,prompt_sha,identity=None):
 """Verify sealed files and rederive event classification before reuse."""
 if meta.get('prompt_sha256')!=prompt_sha:raise RuntimeError('Attempt prompt hash mismatch')
 if meta.get('model_requested')!=MODEL or meta.get('effort_requested')!=EFFORT:raise RuntimeError('Attempt model identity mismatch')
 for filename,field in [('attempt_started.json','started_sha256'),('events.jsonl','stdout_sha256'),('stderr.txt','stderr_sha256')]:
  p=ad/filename
  if not p.is_file() or file_sha(p)!=meta.get(field):raise RuntimeError('Attempt artifact hash mismatch: '+str(p))
 started=read(ad/'attempt_started.json')
 if started.get('prompt_sha256')!=prompt_sha or started.get('attempt')!=meta.get('attempt'):
  raise RuntimeError('Attempt start identity mismatch')
 if identity is not None and any(started.get(k)!=v for k,v in identity.items()):
  raise RuntimeError('Attempt belongs to a different planned task')
 output=ad/'response.json';expected=meta.get('output_sha256')
 if expected is not None:
  if not output.is_file() or file_sha(output)!=expected:raise RuntimeError('Attempt response hash mismatch')
 elif output.exists():raise RuntimeError('Unexpected output for an attempt sealed without a response')
 info=events_info((ad/'events.jsonl').read_text())
 if any(meta.get(k)!=v for k,v in info.items()):raise RuntimeError('Attempt event metadata differs from raw events')
 if meta.get('service_block')!=service_block_reason(info,(ad/'stderr.txt').read_text(),meta['returncode'],meta.get('error')):
  raise RuntimeError('Service error metadata differs from raw events')
 return attempt_final(output,info)

def attempt_final(output,info):
 # A completed agent message already returned an answer even if the CLI crashed
 # before writing -o. Preserve its exact last text and forbid another sample.
 if output.exists() and output.read_text().strip():return output.read_text()
 messages=info.get('completed_agent_messages',[])
 if messages:return messages[-1]
 return output.read_text() if output.exists() else None

def classify_final(meta,final):
 if meta['unexpected_items']:return 'protocol_failure',None,'unexpected tool/item/event content'
 if final is None or not final.strip():return 'technical_failure',None,'No final response'
 if meta.get('lifecycle_errors'):return 'protocol_failure',None,'Returned answer has invalid session/turn lifecycle'
 if meta.get('output_sha256') is None:
  return 'technical_failure',None,'Final agent text exists in events but response file is missing; no resampling'
 if meta['returncode']!=0 or not meta['turn_completed'] or meta.get('top_level_errors'):
  return 'technical_failure',None,'Final text exists but process/turn failed; no resampling'
 try:
  parsed=json.loads(final);jsonschema.validate(parsed,SCHEMA)
  return 'complete',parsed,None
 except Exception as e:return 'parse_failure',None,str(e)

def validate_record(phase,job,item,first_text,config_hash):
 """Validate every provenance file; never trust a saved parsed answer alone."""
 out=R/'runs'/phase/job['group_id']/job['procedure']
 old=read(out/'record.json');prompt=build_prompt(job,item,first_text)
 expected={**job,'phase':phase,'frozen_hash':config_hash,'first_sha256':sha(first_text) if first_text is not None else None,
  'prompt_sha256':sha(prompt)}
 if any(old.get(k)!=v for k,v in expected.items()):raise RuntimeError('Resume identity mismatch')
 if not (out/'prompt.txt').is_file() or (out/'prompt.txt').read_text()!=prompt:raise RuntimeError('Saved prompt mismatch')
 attempts=old.get('attempts',[])
 if not 1<=len(attempts)<=2:raise RuntimeError('Invalid saved attempt count')
 expected_dirs={f'attempt_{number:02d}' for number in range(1,len(attempts)+1)}
 if {p.name for p in out.glob('attempt_*')}!=expected_dirs:
  raise RuntimeError('Unrecorded attempt directory; refusing hidden resampling')
 final=None
 for number,meta in enumerate(attempts,1):
  if meta.get('attempt')!=number:raise RuntimeError('Invalid attempt sequence')
  ad=out/f'attempt_{number:02d}'
  if read(ad/'meta.json')!=meta:raise RuntimeError('Saved attempt metadata differs from sealed file')
  final=validate_attempt(ad,meta,sha(prompt),expected)
  if number<len(attempts) and ((final is not None and final.strip()) or meta['unexpected_items']):
   raise RuntimeError('A returned answer or protocol violation was resampled')
 status,parsed,_=classify_final(attempts[-1],final)
 if old.get('status')!=status or old.get('parsed')!=parsed:raise RuntimeError('Saved status/answer differs from raw response')
 if final is not None and final.strip():
  if old.get('raw_final')!=final or old.get('final_sha256')!=sha(final):raise RuntimeError('Saved final response hash mismatch')
 elif old.get('raw_final') is not None or old.get('final_sha256') is not None:raise RuntimeError('Unexpected saved final response')
 return old

def response_task(phase,job,item,first_text,config_hash,gate=None):
 out=R/'runs'/phase/job['group_id']/job['procedure'];out.mkdir(parents=True,exist_ok=True)
 record_path=out/'record.json'
 first_hash=sha(first_text) if first_text is not None else None
 if record_path.exists():
  return validate_record(phase,job,item,first_text,config_hash)
 prompt=build_prompt(job,item,first_text)
 pp=out/'prompt.txt'
 if pp.exists() and pp.read_text()!=prompt:raise RuntimeError('Uncommitted task prompt mismatch')
 if not pp.exists():seal_text(pp,prompt)
 rec={**job,'phase':phase,'frozen_hash':config_hash,'first_sha256':first_hash,
   'prompt_sha256':sha(prompt),'started_utc':now(),'attempts':[],'status':'running','parsed':None}
 # Request-level environment preserves this user's Codex ChatGPT auth store. No keys are read.
 env=os.environ.copy()
 for k in ['OPENAI_API_KEY','OPENAI_BASE_URL','AZURE_OPENAI_API_KEY','CODEX_THREAD_ID']:
  env.pop(k,None)
 empty=R/'runtime_empty';empty.mkdir(exist_ok=True)
 if any(empty.iterdir()):raise RuntimeError('Runtime directory must remain empty')
 for attempt in range(1,MAX_ATTEMPTS+1):
  ad=out/f'attempt_{attempt:02d}';ad.mkdir(exist_ok=True)
  is_new=not (ad/'meta.json').exists()
  if not is_new:
   meta=read(ad/'meta.json')
   final=validate_attempt(ad,meta,sha(prompt),{**job,'phase':phase,'frozen_hash':config_hash,
     'first_sha256':first_hash,'prompt_sha256':sha(prompt)})
  else:
   if any(ad.iterdir()):
    raise RuntimeError('Uncommitted attempt files exist; preserve and audit before resuming: '+str(ad))
   if gate is not None and gate.stopped:
    return {**rec,'status':'paused_dispatch','error':gate.reason}
   output=ad/'response.json'
   cmd=[CLI,'exec',*FLAGS,'-C',str(empty),'--output-schema',str(R/'protocol/output_schema.json'),'-o',str(output),'-']
   t=time.monotonic();started=now();stdout=stderr='';code=None;error=None
   marker={**job,'phase':phase,'frozen_hash':config_hash,'first_sha256':first_hash,
    'attempt':attempt,'started_utc':started,'prompt_sha256':sha(prompt),'model_requested':MODEL,'effort_requested':EFFORT}
   # An interrupted attempt has an explicit durable marker; never silently resample it.
   with (ad/'attempt_started.json').open('x') as h:
    h.write(json.dumps(marker,ensure_ascii=False,indent=2)+'\n');h.flush();os.fsync(h.fileno())
   try:
    cp=subprocess.run(cmd,input=prompt,text=True,capture_output=True,env=env,timeout=TIMEOUT)
    stdout,stderr,code=cp.stdout,cp.stderr,cp.returncode
   except subprocess.TimeoutExpired as e:
    stdout=e.stdout.decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout or ''
    stderr=e.stderr.decode(errors='replace') if isinstance(e.stderr,bytes) else e.stderr or ''
    error='timeout_600s'
   except OSError as e:
    error=type(e).__name__+': '+str(e)
   seal_text(ad/'events.jsonl',stdout);seal_text(ad/'stderr.txt',stderr)
   info=events_info(stdout)
   meta={'attempt':attempt,'started_utc':started,'finished_utc':now(),'seconds':time.monotonic()-t,
    'returncode':code,'error':error,'model_requested':MODEL,'effort_requested':EFFORT,
    'model_snapshot_resolved':None,'prompt_sha256':sha(prompt),'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),
    'started_sha256':file_sha(ad/'attempt_started.json'),
    'output_sha256':file_sha(output) if output.exists() else None,
    'service_block':service_block_reason(info,stderr,code,error),**info}
   seal_json(ad/'meta.json',meta)
   final=attempt_final(output,info)
  rec['attempts'].append(meta)
  if is_new and meta.get('service_block') and gate is not None:gate.stop(meta['service_block'])
  rec['status'],rec['parsed'],decision_error=classify_final(meta,final)
  if decision_error is not None:rec['error']=decision_error
  else:rec.pop('error',None)
  if final is not None and final.strip():
   rec['raw_final']=final;rec['final_sha256']=sha(final)
   break
  # Never retry a protocol violation, even if no final answer was emitted.
  if meta['unexpected_items']:rec['status']='protocol_failure';break
  if is_new and meta.get('service_block') and attempt<MAX_ATTEMPTS:
   return {**rec,'status':'paused_service','error':meta['service_block']}
  if gate is not None and gate.stopped and attempt<MAX_ATTEMPTS:
   return {**rec,'status':'paused_dispatch','error':gate.reason}
 rec['finished_utc']=now();seal_json(record_path,rec)
 return rec

def append_progress(out,msg):
 with (out/'progress.jsonl').open('a') as stream:
  stream.write(json.dumps({'utc':now(),**msg},ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
 print(json.dumps(msg,ensure_ascii=False),flush=True)

def blocked_review_record(phase,job,config_hash):
 return {**job,'phase':phase,'status':'not_run_first_failed','frozen_hash':config_hash,
         'first_sha256':None,'attempts':[],'parsed':None}

def run(phase,part,workers):
 if phase!='dev':raise ValueError('Only the frozen dev matrix may call a model')
 if not 1<=workers<=MAX_WORKERS:raise ValueError('workers must be 1..3')
 out=R/'runs'/phase;out.mkdir(parents=True,exist_ok=True)
 with DirectoryLock(out):
  f=verify();cfg=file_sha(R/'protocol/frozen.json')
  pin=out/'manifest_identity.json'
  if not pin.exists():seal_json(pin,{'frozen_hash':cfg})
  byid={i['item_id']:i for i in load_items()}
  jobs=f['phase_schedule'][phase]['jobs'];gate=DispatchGate()
  segments=['P0','review'] if part=='all' else [part]
  append_progress(out,{'event':'invocation_started','phase':phase,'part':part,'workers':workers,'frozen_hash':cfg})
  for segment in segments:
   selected=[j for j in jobs if (j['procedure']=='P0')==(segment=='P0')]
   # Review phase starts only after all 160 P0 tasks have terminal records.
   if segment=='review':
    for job in jobs:
     if job['procedure']=='P0':
      p=out/job['group_id']/'P0/record.json'
      if not p.exists():raise RuntimeError('P0 missing or paused; finish first pass before reviews')
      validate_record(phase,job,byid[job['item_id']],None,cfg)
   pending=iter(selected)
   with ThreadPoolExecutor(max_workers=workers) as pool:
    futures={};exhausted=False
    while futures or not exhausted:
     while not gate.stopped and not exhausted and len(futures)<workers:
      try:job=next(pending)
      except StopIteration:exhausted=True;break
      first=None
      if job['procedure']!='P0':
       first_job={**job,'procedure':'P0'}
       original=validate_record(phase,first_job,byid[job['item_id']],None,cfg)
       if original['status'] not in ['complete','parse_failure']:
        path=out/job['group_id']/job['procedure']/'record.json'
        expected=blocked_review_record(phase,job,cfg)
        if path.exists():
         if read(path)!=expected:raise RuntimeError('Failed-first record identity mismatch')
        else:seal_json(path,expected)
        continue
       first=original['raw_final']
      futures[pool.submit(response_task,phase,job,byid[job['item_id']],first,cfg,gate)]=job
     if not futures:break
     done,_=wait(futures,return_when=FIRST_COMPLETED)
     # Inspect every completed future before replacing any worker slot.
     for future in done:
      job=futures.pop(future)
      try:rec=future.result()
      except BaseException as exc:
       gate.stop('integrity_or_runtime_error')
       append_progress(out,{'event':'task_exception','group':job['group_id'],'procedure':job['procedure'],'error':repr(exc)})
       # Preserve all in-flight results, then report; never continue dispatch.
       for running in list(futures):
        try:
         other=running.result()
         append_progress(out,{'event':'task_result','group':other['group_id'],'procedure':other['procedure'],'status':other['status']})
        except BaseException as secondary:
         append_progress(out,{'event':'task_exception','error':repr(secondary)})
       raise
      append_progress(out,{'event':'task_result','phase':phase,'group':rec['group_id'],
       'procedure':rec['procedure'],'status':rec['status'],
       'seconds':round(sum(a.get('seconds',0) for a in rec['attempts']),2)})
     if gate.stopped:exhausted=True
   if gate.stopped:
    append_progress(out,{'event':'dispatch_paused','reason':gate.reason,'phase':phase,'part':segment,
      'instruction':'Resolve the external issue, then rerun the same command; sealed answers are never resampled.'})
    return False
  append_progress(out,{'event':'invocation_complete','phase':phase,'part':part})
  return True

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--verify',action='store_true')
 ap.add_argument('--phase',choices=['dev']);ap.add_argument('--part',choices=['P0','review','all'],default='all');ap.add_argument('--workers',type=int,default=3)
 a=ap.parse_args()
 if a.freeze:freeze()
 elif a.verify:verify();print('Frozen inputs verified; no model calls')
 elif a.phase:
  if not run(a.phase,a.part,a.workers):raise SystemExit(75)
 else:ap.error('--freeze, --verify or --phase required')
