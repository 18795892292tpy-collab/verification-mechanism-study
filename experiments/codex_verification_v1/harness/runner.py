#!/usr/bin/env python3
"""New, append-only Codex experiment; no DeepSeek or direct provider API."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse, csv, fcntl, hashlib, json, os, random, subprocess, time
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

def initialize_protocol():
 if (R/'protocol/frozen.json').exists(): raise RuntimeError('Already frozen; do not overwrite')
 assert abs(len(ADD7)-len(ADD8))/max(len(ADD7),len(ADD8))<=.05
 dump(R/'protocol/output_schema.json',SCHEMA)
 dump(R/'protocol/prompts.json',{'base':BASE,'reviews':REVIEWS,'extra_chars':{'P7':len(ADD7),'P8':len(ADD8)}})
 dump(R/'protocol/backend.json',{'cli':CLI,'flags':FLAGS,'model':MODEL,'effort':EFFORT,'sampling_seed':None,
   'max_workers':3,'timeout_s':600,'max_total_attempts':2,'reuse_first':True,'unknown_event_policy':'reject',
   'allowed_item_types':['agent_message','reasoning','error'],'technical_retry':'only when no final response exists; never retry parsing, tool use or a wrong answer'})

def freeze():
 initialize_protocol()
 files=['protocol/approved_plan.md','protocol/runtime_identity.json','protocol/EXECUTION_AMENDMENT.md',
 'protocol/output_schema.json','protocol/prompts.json','protocol/backend.json','protocol/analysis_plan.json','harness/runner.py',
 'harness/integrity.py','tests/test_integrity.py','tests/test_runner_offline.py','harness/evaluate.py',
 'prompts/toy_items.json','prompts/dev_items.json','keys/toy_keys.json','keys/dev_keys.json',
 'cases/build_cases.py','cases/build_validation.json','audits/case_review.json','audits/integrity_tests.json',
 'audits/legacy_audit.json','audits/blind_review_answers.json','audits/blind_packet.json','keys/blind_mapping.json']
 for f in files:
  if not (R/f).is_file(): raise FileNotFoundError(f)
 phases={}
 for phase in ['toy','dev']:
  items=read(R/f'prompts/{phase}_items.json')
  if isinstance(items,dict): items=items['items']
  ids=[i['item_id'] for i in items];assert len(ids)==len(set(ids))
  expected=2 if phase=='toy' else 40
  assert len(items)==expected,(phase,len(items))
  jobs=[{'group_id':i['item_id']+'_r1','item_id':i['item_id'],'repeat':1,'procedure':p} for i in items for p in PROCS]
  random.Random(20261106+(phase=='dev')).shuffle(jobs)
  phases[phase]={'groups':len(items),'tasks':len(jobs),'jobs':jobs}
 f={'created_utc':now(),'experiment':'codex_verification_v1','model_requested':MODEL,'effort_requested':EFFORT,
   'provider_snapshot':None,'schedule_seed':20261106,'sampling_seed':None,
   'phase_schedule':phases,'sha256':{x:file_sha(R/x) for x in files}}
 dump(R/'protocol/frozen.json',f)
 for phase,v in phases.items():
  p=R/f'runs/{phase}/plan.csv';p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('w',newline='') as h:
   w=csv.DictWriter(h,fieldnames=['group_id','item_id','repeat','procedure']);w.writeheader();w.writerows(v['jobs'])
 print(json.dumps({'frozen':True,'toy_tasks':phases['toy']['tasks'],'dev_tasks':phases['dev']['tasks'],'hash':file_sha(R/'protocol/frozen.json')}),flush=True)

def verify():
 f=read(R/'protocol/frozen.json')
 for p,h in f['sha256'].items():
  if file_sha(R/p)!=h: raise RuntimeError('Frozen file changed: '+p)
 return f

def events_info(stdout):
 events=[];usage=None;threads=[];unexpected=[];errors=[];completed=False;fatal=[]
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
  if e.get('type') not in allowed:unexpected.append({'kind':'unknown_event_type','event':e})
  if e.get('type')=='thread.started': threads.append(e.get('thread_id'))
  if e.get('type')=='turn.completed':usage=e.get('usage');completed=True
  if e.get('type') in ['turn.failed','error']:fatal.append(e)
  item=e.get('item',{})
  if item and not isinstance(item,dict):unexpected.append({'kind':'invalid_item','item':item});continue
  if item and item.get('type') not in ['agent_message','reasoning','error']:unexpected.append(item)
  if item and item.get('type')=='error':errors.append(item)
 return {'usage':usage,'thread_ids':threads,'unexpected_items':unexpected,'error_items':errors,
  'top_level_errors':fatal,'turn_completed':completed,'event_count':len(events)}

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
 return output.read_text() if output.exists() else None

def classify_final(meta,final):
 if meta['unexpected_items']:return 'protocol_failure',None,'unexpected tool/item/event content'
 if final is None or not final.strip():return 'technical_failure',None,'No final response'
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

def response_task(phase,job,item,first_text,config_hash):
 out=R/'runs'/phase/job['group_id']/job['procedure'];out.mkdir(parents=True,exist_ok=True)
 record_path=out/'record.json'
 first_hash=sha(first_text) if first_text is not None else None
 if record_path.exists():
  return validate_record(phase,job,item,first_text,config_hash)
 prompt=build_prompt(job,item,first_text)
 pp=out/'prompt.txt'
 if pp.exists() and pp.read_text()!=prompt:raise RuntimeError('Uncommitted task prompt mismatch')
 if not pp.exists():pp.write_text(prompt)
 rec={**job,'phase':phase,'frozen_hash':config_hash,'first_sha256':first_hash,
   'prompt_sha256':sha(prompt),'started_utc':now(),'attempts':[],'status':'running','parsed':None}
 # Request-level environment preserves this user's Codex ChatGPT auth store. No keys are read.
 env=os.environ.copy()
 for k in ['OPENAI_API_KEY','OPENAI_BASE_URL','AZURE_OPENAI_API_KEY','CODEX_THREAD_ID']:
  env.pop(k,None)
 empty=R/'runtime_empty';empty.mkdir(exist_ok=True)
 for attempt in [1,2]:
  ad=out/f'attempt_{attempt:02d}';ad.mkdir(exist_ok=True)
  if (ad/'meta.json').exists():
   meta=read(ad/'meta.json')
   final=validate_attempt(ad,meta,sha(prompt),{**job,'phase':phase,'frozen_hash':config_hash,
     'first_sha256':first_hash,'prompt_sha256':sha(prompt)})
  else:
   if any(ad.iterdir()):
    raise RuntimeError('Uncommitted attempt files exist; preserve and audit before resuming: '+str(ad))
   output=ad/'response.json'
   cmd=[CLI,'exec',*FLAGS,'-C',str(empty),'--output-schema',str(R/'protocol/output_schema.json'),'-o',str(output),'-']
   t=time.monotonic();started=now();stdout=stderr='';code=None;error=None
   marker={**job,'phase':phase,'frozen_hash':config_hash,'first_sha256':first_hash,
    'attempt':attempt,'started_utc':started,'prompt_sha256':sha(prompt),'model_requested':MODEL,'effort_requested':EFFORT}
   # An interrupted attempt has an explicit durable marker; never silently resample it.
   with (ad/'attempt_started.json').open('x') as h:
    h.write(json.dumps(marker,ensure_ascii=False,indent=2)+'\n');h.flush();os.fsync(h.fileno())
   try:
    cp=subprocess.run(cmd,input=prompt,text=True,capture_output=True,env=env,timeout=600)
    stdout,stderr,code=cp.stdout,cp.stderr,cp.returncode
   except subprocess.TimeoutExpired as e:
    stdout=e.stdout.decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout or ''
    stderr=e.stderr.decode(errors='replace') if isinstance(e.stderr,bytes) else e.stderr or ''
    error='timeout_600s'
   (ad/'events.jsonl').write_text(stdout);(ad/'stderr.txt').write_text(stderr)
   info=events_info(stdout)
   meta={'attempt':attempt,'started_utc':started,'finished_utc':now(),'seconds':time.monotonic()-t,
    'returncode':code,'error':error,'model_requested':MODEL,'effort_requested':EFFORT,
    'model_snapshot_resolved':None,'prompt_sha256':sha(prompt),'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),
    'started_sha256':file_sha(ad/'attempt_started.json'),
    'output_sha256':file_sha(output) if output.exists() else None,**info}
   dump(ad/'meta.json',meta)
   final=output.read_text() if output.exists() else None
  rec['attempts'].append(meta)
  rec['status'],rec['parsed'],decision_error=classify_final(meta,final)
  if decision_error is not None:rec['error']=decision_error
  else:rec.pop('error',None)
  if final is not None and final.strip():
   rec['raw_final']=final;rec['final_sha256']=sha(final)
   break
  # Never retry a protocol violation, even if no final answer was emitted.
  if meta['unexpected_items']:rec['status']='protocol_failure';break
 rec['finished_utc']=now();dump(record_path,rec)
 return rec

def run(phase,part,workers):
 f=verify();cfg=file_sha(R/'protocol/frozen.json');assert 1<=workers<=3
 out=R/'runs'/phase;out.mkdir(parents=True,exist_ok=True)
 with (out/'.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  items=read(R/f'prompts/{phase}_items.json')
  if isinstance(items,dict):items=items['items']
  byid={i['item_id']:i for i in items}
  jobs=f['phase_schedule'][phase]['jobs']
  segments=['P0','review'] if part=='all' else [part]
  for segment in segments:
   selected=[j for j in jobs if (j['procedure']=='P0')==(segment=='P0')]
   with ThreadPoolExecutor(max_workers=workers) as pool:
    futures={}
    for job in selected:
     first=None
     if job['procedure']!='P0':
      p=out/job['group_id']/'P0/record.json'
      if not p.exists():raise RuntimeError('P0 missing; run first pass before reviews')
      p0_job={**job,'procedure':'P0'}
      r=validate_record(phase,p0_job,byid[job['item_id']],None,cfg)
      if r['status'] not in ['complete','parse_failure']:
       rp=out/job['group_id']/job['procedure']/'record.json'
       if not rp.exists():dump(rp,{**job,'phase':phase,'status':'not_run_first_failed','frozen_hash':cfg,'first_sha256':None,'attempts':[],'parsed':None})
       continue
      first=r['raw_final']
     futures[pool.submit(response_task,phase,job,byid[job['item_id']],first,cfg)]=job
    for fu in as_completed(futures):
     rec=fu.result();msg={'phase':phase,'group':rec['group_id'],'procedure':rec['procedure'],'status':rec['status'],
      'seconds':round(sum(a.get('seconds',0) for a in rec['attempts']),2)}
     with (out/'progress.jsonl').open('a') as h:h.write(json.dumps(msg)+'\n')
     print(json.dumps(msg),flush=True)
  fcntl.flock(lock,fcntl.LOCK_UN)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--verify',action='store_true')
 ap.add_argument('--phase',choices=['toy','dev']);ap.add_argument('--part',choices=['P0','review','all'],default='all');ap.add_argument('--workers',type=int,default=3)
 a=ap.parse_args()
 if a.freeze:freeze()
 elif a.verify:verify();print('Frozen inputs verified; no model calls')
 elif a.phase:run(a.phase,a.part,a.workers)
 else:ap.error('--freeze, --verify or --phase required')
