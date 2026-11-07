#!/usr/bin/env python3
"""Read-only V3 final audit: stdlib only; never imports runner/evaluate or calls a model.

Writes exclusively under audits/independent_final and the experiment-audit trace.
Run only after subject work ends: python audits/independent_recompute.py --execute-final
Pure offline checks: python audits/independent_recompute.py --self-test
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, csv, hashlib, json, os, random, socket

ROOT = Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
PHASES = ('p0', 'challenge')
PROCS = {'p0':['P0'], 'challenge':['P1','P3','P7','P8']}
REQUIRED_FROZEN = {
 'protocol/EXPERIMENT_PLAN.md','protocol/analysis_plan.json','protocol/runtime_identity.json',
 'protocol/output_schema.json','protocol/prompts.json','protocol/backend.json',
 'prompts/p0_items.json','prompts/challenge_items.json','keys/p0_keys.json','keys/challenge_keys.json',
 'cases/build_cases.py','cases/CASE_SPEC.md','cases/AUTHORING_LOG.md','cases/validation.json',
 'harness/runner.py','harness/integrity.py','harness/PROVENANCE.json',
 'analysis/evaluate.py','analysis/progress.py','tests/test_v3.py',
 'audits/case_review.json','audits/harness_tests.json'}

def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()

def file_hash(path):return digest(path.read_bytes())
def read(path):return json.loads(path.read_text())
def require(condition,message):
    if not condition:raise ValueError(message)
def stamp(value):
    parsed=datetime.fromisoformat(value)
    require(parsed.tzinfo is not None,'Timestamp missing timezone')
    return parsed
def items(path):
    value=read(path)
    return value['items'] if isinstance(value,dict) else value
def mean(values):return sum(values)/len(values) if values else None
def proportion(n,d):return n/d if d else None
def token(value):return value if type(value) is int and value>=0 else None

def schema_parse(text):
    try:
        value=json.loads(text)
        require(type(value) is dict and set(value)=={'action','cited_sources','brief_justification','confidence'},'Schema fields')
        require(value['action'] in ['A','B','C','D'],'Action')
        require(type(value['cited_sources']) is list and all(type(v) is str for v in value['cited_sources']),'Citations')
        require(type(value['brief_justification']) is str and len(value['brief_justification'])<=180,'Justification')
        # JSON Schema integer allows mathematically integral JSON numbers, but never booleans.
        require(type(value['confidence']) in (int,float) and value['confidence']==int(value['confidence']) and 1<=value['confidence']<=5,'Confidence')
        return value
    except (ValueError,TypeError,KeyError,OverflowError):return None

def parse_events(text):
    all_events=[];problems=[];messages=[];sessions=[];life=[];usages=[];errors=[]
    allowed={'thread.started','turn.started','item.started','item.updated','item.completed','turn.completed','turn.failed','error'}
    for line in text.splitlines():
        if not line.strip():continue
        try:e=json.loads(line)
        except json.JSONDecodeError:problems.append('non_json_stdout');continue
        if not isinstance(e,dict):problems.append('non_object_event');continue
        all_events.append(e);kind=e.get('type')
        if kind not in allowed:problems.append('unknown_event_type')
        if kind in ['thread.started','turn.started','turn.completed','turn.failed']:life.append(kind)
        if kind=='thread.started':sessions.append(e.get('thread_id'))
        if kind=='turn.completed':usages.append(e.get('usage'))
        if kind in ['turn.failed','error']:errors.append(e)
        item=e.get('item',{})
        if not isinstance(item,dict):problems.append('invalid_item');continue
        if item and item.get('type') not in ['agent_message','reasoning','error']:problems.append('unknown_item')
        if item and item.get('type')=='error':errors.append(item)
        if kind=='item.completed' and item.get('type')=='agent_message' and isinstance(item.get('text'),str) and item['text'].strip():messages.append(item['text'])
    valid_lifecycle=life==['thread.started','turn.started','turn.completed'] and len(sessions)==1 and isinstance(sessions[0],str) and bool(sessions[0].strip())
    return {'events':all_events,'problems':problems,'messages':messages,'sessions':sessions,'lifecycle':life,'valid_lifecycle':valid_lifecycle,'usages':usages,'errors':errors}

def usage_summary(attempts):
    vectors={key:[a.get(key) for a in attempts] for key in ['input_tokens','output_tokens']}
    output={'attempts':len(attempts)}
    for key,values in vectors.items():
        output['known_'+key]=sum(v for v in values if v is not None)
        output['sum_'+key]=None if any(v is None for v in values) else sum(values)
        output[key+'_missing_attempts']=sum(v is None for v in values)
    output['usage_missing_attempts']=sum(a.get('input_tokens') is None or a.get('output_tokens') is None for a in attempts)
    return output

def prompt_text(prompts,item,proc,phase):
    text=prompts['base']+'\n\n档案与问题：\n'+item['public_text']
    if phase=='challenge':text+='\n\n待复核草稿（作者预设，原样提供）：\n'+item['draft_text']+'\n\n本次任务：\n'+prompts['reviews'][proc]
    else:text+='\n\n本次任务：给出你的决定。'
    return text

def scheduled(items_,phase):
    jobs=[{'group_id':i['item_id']+'_r1','item_id':i['item_id'],'repeat':1,'procedure':p} for i in items_ for p in PROCS[phase]]
    random.Random(20261108+(phase=='challenge')).shuffle(jobs)
    return jobs

def validate_design(items_,keys,phase):
    require(len(items_)==(80 if phase=='p0' else 32),'Wrong item count')
    require(len({i['item_id'] for i in items_})==len(items_),'Duplicate item')
    require(len(keys)==len(items_) and set(keys)=={i['item_id'] for i in items_},'Key identity')
    families=defaultdict(list)
    for i in items_:
        families[i['family_id']].append(i);k=keys[i['item_id']]
        require(k['correct_action'] in 'ABCD' and len(k['correct_action'])==1,'Invalid key action')
        require(all(k.get(n)==i.get(n) for n in ['family_id','error_type','state','advice','draft_condition']),'Key metadata mismatch')
        require(k['public_sha256']==digest(i['public_text']),'Key public dossier hash')
        if phase=='challenge':
            draft=schema_parse(i['draft_text']);require(draft is not None,'Invalid authored draft')
            require(k['draft_sha256']==digest(i['draft_text']),'Key draft hash')
            require((draft['action']==k['correct_action'])==(i['draft_condition']=='correct'),'Authored draft label')
            require(k['draft_origin']=='preauthored_fixed_challenge_not_natural_P0','Authored key origin')
    require(len(families)==8,'Family count')
    require(Counter(next(iter(v))['error_type'] for v in families.values())=={'material':4,'rule':4},'Four families per type')
    for f,group in families.items():
        require(len({i['error_type'] for i in group})==1,'Mixed family type')
        expected={(s,a) for s in (['base','decisive_change','irrelevant','paraphrase','missing'] if phase=='p0' else ['base','decisive_change']) for a in (['aligned','flawed'] if phase=='p0' else ['correct','error'])}
        observed=[(i['state'],i['advice' if phase=='p0' else 'draft_condition']) for i in group]
        require(len(observed)==len(expected) and set(observed)==expected,'Incomplete family factorial')
        if phase=='challenge':
            for state in ['base','decisive_change']:require(len({i['public_text'] for i in group if i['state']==state})==1,'Draft controls differ in dossier')

def scan_inventory(root,plans):
    pairs={phase:{(j['group_id'],j['procedure']) for j in jobs} for phase,jobs in plans.items()}
    observed=[]
    for p in sorted((root/'runs').rglob('*')):
        parts=p.relative_to(root/'runs').parts
        require(not p.is_symlink(),'Symlink run artifact: '+str(p))
        ok=parts==('.integrity.lock',) and p.is_file()
        if parts[0] in pairs:
            phase=parts[0]
            if len(parts)==1:ok=p.is_dir()
            elif len(parts)==2:ok=(parts[1] in {'.integrity.lock','plan.csv','manifest_identity.json','progress.jsonl'} and p.is_file()) or (parts[1] in {x[0] for x in pairs[phase]} and p.is_dir())
            elif len(parts)==3:ok=tuple(parts[1:3]) in pairs[phase] and p.is_dir()
            elif len(parts)==4:ok=tuple(parts[1:3]) in pairs[phase] and ((parts[3] in ['prompt.txt','record.json'] and p.is_file()) or (parts[3] in ['attempt_01','attempt_02'] and p.is_dir()))
            elif len(parts)==5:ok=tuple(parts[1:3]) in pairs[phase] and parts[3] in ['attempt_01','attempt_02'] and parts[4] in ['attempt_started.json','response.json','meta.json','events.jsonl','stderr.txt'] and p.is_file()
            else:ok=False
        require(ok,'Unplanned run artifact: '+str(p));observed.append(str(p.relative_to(root)))
    return observed

def audit_task(root,job,item,key,phase,prompts,fhash,freeze_time,gate):
    folder=root/'runs'/phase/job['group_id']/job['procedure'];rp=folder/'record.json'
    ptext=prompt_text(prompts,item,job['procedure'],phase)
    first_hash=digest(item['draft_text']) if phase=='challenge' else None
    identity={**job,'phase':phase,'frozen_hash':fhash,'first_sha256':first_hash,'first_origin':'authored_fixed_draft' if phase=='challenge' else None,'gate_sha256':file_hash(root/'analysis/decision_gate.json') if phase=='challenge' else None,'prompt_sha256':digest(ptext)}
    base={**job,'family_id':item['family_id'],'error_type':item['error_type'],'state':item['state'],'advice':item.get('advice'),'draft_condition':item.get('draft_condition'),'first_origin':identity['first_origin'],'status':'not_executed','correct':0,'correct_action':key['correct_action'],'action':None,'attempts':[],'record_sha256':None}
    dirs=sorted(folder.glob('attempt_*'))
    if not rp.exists():
        require(not dirs,'Unfinished task has attempt artifacts: '+str(folder))
        if (folder/'prompt.txt').exists():require((folder/'prompt.txt').read_text()==ptext,'Unexecuted prompt mismatch')
        return base
    record=read(rp)
    require(all(record.get(k)==v for k,v in identity.items()),'Task identity mismatch: '+str(folder))
    require((folder/'prompt.txt').read_text()==ptext,'Prompt mismatch')
    require(1<=len(dirs)<=2 and [p.name for p in dirs]==[f'attempt_{i:02}' for i in range(1,len(dirs)+1)],'Invalid attempt directories')
    require(len(record['attempts'])==len(dirs),'Attempt count mismatch')
    final=None;last=None
    for n,ad in enumerate(dirs,1):
        meta=read(ad/'meta.json');marker=read(ad/'attempt_started.json')
        require(meta==record['attempts'][n-1],'Record/attempt metadata mismatch')
        require(meta['attempt']==n and marker['attempt']==n,'Attempt sequence')
        require(all(marker.get(k)==v for k,v in identity.items()),'Attempt identity mismatch')
        require(meta.get('first_origin')==identity['first_origin'] and meta.get('gate_sha256')==identity['gate_sha256'],'Attempt origin/gate metadata')
        require(meta.get('prompt_sha256')==digest(ptext),'Attempt prompt hash')
        require(meta.get('model_requested')==marker.get('model_requested')=='gpt-6-astra' and meta.get('effort_requested')==marker.get('effort_requested')=='ultra','Requested model/effort')
        require(stamp(marker['started_utc'])>=freeze_time,'Attempt before freeze')
        require(stamp(meta['finished_utc'])>=stamp(marker['started_utc']),'Negative attempt chronology')
        if phase=='challenge':require(gate is not None and stamp(marker['started_utc'])>=stamp(gate['created_utc']),'Challenge before gate')
        for name,field in [('attempt_started.json','started_sha256'),('events.jsonl','stdout_sha256'),('stderr.txt','stderr_sha256')]:require(file_hash(ad/name)==meta[field],'Raw artifact hash: '+str(ad/name))
        response=ad/'response.json';expected=meta.get('output_sha256')
        require((response.is_file() and file_hash(response)==expected) if expected is not None else not response.exists(),'Response hash or existence')
        ev=parse_events((ad/'events.jsonl').read_text());text=response.read_text() if response.exists() else None
        if text is not None and text.strip() and ev['messages']:require(text==ev['messages'][-1],'Response differs from final event')
        final=text if text and text.strip() else ev['messages'][-1] if ev['messages'] else text
        if n<len(dirs):require(not (final and final.strip()) and not ev['problems'] and not ev['errors'],'Resampled final or protocol failure')
        if ev['problems'] or (final and not ev['valid_lifecycle']):status='protocol_failure'
        elif not final or not final.strip():status='technical_failure'
        elif expected is None or meta['returncode']!=0 or not ev['valid_lifecycle'] or ev['errors']:status='technical_failure'
        else:status='complete' if schema_parse(final) is not None else 'parse_failure'
        raw_usage=ev['usages'][0] if len(ev['usages'])==1 and isinstance(ev['usages'][0],dict) else {}
        require(meta.get('usage')==(ev['usages'][0] if len(ev['usages'])==1 else None),'Saved usage differs from events')
        base['attempts'].append({'attempt':n,'input_tokens':token(raw_usage.get('input_tokens')),'output_tokens':token(raw_usage.get('output_tokens')),'sessions':ev['sessions'],'seconds':meta['seconds'],'raw_status':status,'raw_errors':ev['errors']})
        last=status
    require(record['status']==last,'Saved status differs from independent event classification: '+str(folder))
    parsed=schema_parse(final) if last=='complete' else None
    require(record.get('parsed')==parsed,'Saved parsed answer mismatch')
    if final and final.strip():require(record.get('raw_final')==final and record.get('final_sha256')==digest(final),'Saved final hash/text')
    else:require(record.get('raw_final') is None and record.get('final_sha256') is None,'Unexpected saved final')
    require(stamp(record['finished_utc'])>=stamp(record['attempts'][-1]['finished_utc']),'Task completion chronology')
    base.update(status=last,action=parsed['action'] if parsed else None,correct=int(last=='complete' and parsed['action']==key['correct_action']),record_sha256=file_hash(rp),finished_utc=record['finished_utc'])
    return base

def phase_stats(rows,phase):
    out={'planned_tasks':len(rows),'complete_tasks':sum(r['status']=='complete' for r in rows),'terminal_tasks':sum(r['record_sha256'] is not None for r in rows),'status_counts':dict(Counter(r['status'] for r in rows)),'procedures':{},'family_results':[],'strata':[]}
    out.update(usage_summary([a for r in rows for a in r['attempts']]))
    for proc in PROCS[phase]:
        selected=[r for r in rows if r['procedure']==proc]
        p={'planned':len(selected),'correct':sum(r['correct'] for r in selected),'accuracy':proportion(sum(r['correct'] for r in selected),len(selected))}
        if phase=='challenge':
            for condition in ['correct','error']:
                c=[r for r in selected if r['draft_condition']==condition]
                n=sum(r['correct'] for r in c)
                p[condition]={'planned':len(c),'final_correct':n,'correct_rate':proportion(n,len(c)),'not_retained':len(c)-n,'nonretention_rate':proportion(len(c)-n,len(c)),'complete_wrong':sum(r['status']=='complete' and not r['correct'] for r in c),'failed_tasks':sum(r['status']!='complete' for r in c)}
        out['procedures'][proc]=p
        for family in sorted({r['family_id'] for r in selected}):
            for condition in (['all'] if phase=='p0' else ['correct','error']):
                c=[r for r in selected if r['family_id']==family and (condition=='all' or r['draft_condition']==condition)]
                out['family_results'].append({'family_id':family,'type':c[0]['error_type'],'procedure':proc,'condition':condition,'planned':len(c),'correct':sum(r['correct'] for r in c),'rate':proportion(sum(r['correct'] for r in c),len(c))})
    if phase=='p0':
        diagnostic={}
        for kind in ['material','rule']:
            subset=[r for r in rows if r['error_type']==kind];flawed=[r for r in subset if r['state']!='missing' and r['advice']=='flawed'];aligned=[r for r in subset if r['state']!='missing' and r['advice']=='aligned'];missing=[r for r in subset if r['state']=='missing'];errors=[r for r in flawed if r['status']=='complete' and not r['correct']]
            diagnostic[kind]={'present_flawed_n':len(flawed),'present_flawed_correct':sum(r['correct'] for r in flawed),'natural_errors':len(errors),'error_families':sorted({r['family_id'] for r in errors}),'present_aligned_n':len(aligned),'present_aligned_correct':sum(r['correct'] for r in aligned),'missing_n':len(missing),'missing_correct':sum(r['correct'] for r in missing)}
        out['difficulty_diagnostic']=diagnostic
        for kind,state,advice in sorted({(r['error_type'],r['state'],r['advice']) for r in rows}):
            c=[r for r in rows if (r['error_type'],r['state'],r['advice'])==(kind,state,advice)]
            out['strata'].append({'type':kind,'state':state,'advice':advice,'planned':len(c),'correct':sum(r['correct'] for r in c),'accuracy':proportion(sum(r['correct'] for r in c),len(c))})
    else:
        pairs={}
        for a,b in [('P7','P8'),('P7','P3'),('P3','P1')]:
            pairs[a+'-'+b]={}
            for condition in ['error','correct']:
                fs=[]
                for family in sorted({r['family_id'] for r in rows}):
                    s=[r for r in rows if r['family_id']==family and r['draft_condition']==condition]
                    av=mean([r['correct'] for r in s if r['procedure']==a]);bv=mean([r['correct'] for r in s if r['procedure']==b]);fs.append({'family':family,'type':s[0]['error_type'],'difference':av-bv})
                types={k:mean([f['difference'] for f in fs if f['type']==k]) for k in ['material','rule']}
                pairs[a+'-'+b][condition]={'families':fs,'type_means':types,'interaction_rule_minus_material':types['rule']-types['material']}
        out['contrasts']=pairs
    return out

def gate_from_stats(stats):
    valid=stats['planned_tasks']==80 and stats['terminal_tasks']==80 and stats['complete_tasks']==80
    criteria={}
    for kind in ['material','rule']:
        d=stats['difficulty_diagnostic'][kind]
        criteria[kind]=4<=d['natural_errors']<=8 and len(d['error_families'])>=3 and d['present_aligned_correct']>=12 and d['missing_correct']>=6 and (d['present_flawed_n'],d['present_aligned_n'],d['missing_n'])==(16,16,8)
    eligible=valid and all(criteria.values())
    return {'status':'eligible_for_independent_holdout' if eligible else 'development_gate_failed' if valid else 'technical_block','challenge_allowed':valid and not eligible,'criteria_pass':criteria}

def execute_final():
    require(socket.gethostname()=='liekkas','Wrong host')
    require(Path(__file__).resolve().parents[1]==ROOT and ROOT.resolve()==ROOT,'Wrong canonical root')
    frozen=read(ROOT/'protocol/frozen.json');fhash=file_hash(ROOT/'protocol/frozen.json');freeze_time=stamp(frozen['created_utc'])
    require(set(frozen['sha256'])==REQUIRED_FROZEN,'Frozen inventory changed')
    for rel,expected in frozen['sha256'].items():require(not (ROOT/rel).is_symlink() and file_hash(ROOT/rel)==expected,'Frozen hash mismatch: '+rel)
    runtime=frozen['runtime'];require(runtime['hostname']=='liekkas' and runtime['root']==str(ROOT),'Frozen target mismatch')
    require(str(Path(runtime['cli_path']).resolve())==runtime['cli_resolved'] and file_hash(Path(runtime['cli_resolved']))==runtime['cli_sha256'],'CLI wrapper identity')
    for path,expected in runtime['cli_dependency_sha256'].items():require(file_hash(Path(path))==expected,'CLI native/package identity: '+path)
    require(runtime['home']==str(Path.home()) and runtime['codex_home']==os.environ.get('CODEX_HOME',str(Path.home()/'.codex')),'Runtime home identity')
    require(read(ROOT/'protocol/backend.json')==frozen['execution_config'],'Backend/frozen config mismatch')
    plan=read(ROOT/'protocol/analysis_plan.json');require(plan['p0_tasks']==80 and plan['challenge_tasks']==128 and plan['max_workers']==12 and plan['max_attempts_per_task']==2,'Analysis plan task/budget mismatch')
    prompts=read(ROOT/'protocol/prompts.json');all_items={};all_keys={};plans={}
    for phase in PHASES:
        its=items(ROOT/f'prompts/{phase}_items.json');ks=items(ROOT/f'keys/{phase}_keys.json');keys={k['item_id']:k for k in ks};require(len(keys)==len(ks),'Duplicate keys');validate_design(its,keys,phase)
        jobs=scheduled(its,phase);require(jobs==frozen['phase_schedule'][phase]['jobs'],'Frozen schedule mismatch')
        with (ROOT/'runs'/phase/'plan.csv').open(newline='') as stream:csvrows=list(csv.DictReader(stream))
        require(csvrows==[{k:str(v) for k,v in j.items()} for j in jobs],'Plan CSV mismatch')
        all_items[phase]={i['item_id']:i for i in its};all_keys[phase]=keys;plans[phase]=jobs
    inventory=scan_inventory(ROOT,plans);gate=read(ROOT/'analysis/decision_gate.json') if (ROOT/'analysis/decision_gate.json').exists() else None
    rows={};stats={};sessions=[]
    for phase in PHASES:
        pin=ROOT/'runs'/phase/'manifest_identity.json'
        if pin.exists():require(read(pin)==({'frozen_hash':fhash,'gate_sha256':file_hash(ROOT/'analysis/decision_gate.json')} if phase=='challenge' else {'frozen_hash':fhash}),'Phase identity pin')
        rows[phase]=[audit_task(ROOT,j,all_items[phase][j['item_id']],all_keys[phase][j['item_id']],phase,prompts,fhash,freeze_time,gate) for j in plans[phase]]
        stats[phase]=phase_stats(rows[phase],phase)
        sessions += [sid for r in rows[phase] for a in r['attempts'] for sid in a['sessions'] if isinstance(sid,str) and sid.strip()]
    require(not [s for s,n in Counter(sessions).items() if n>1],'Session ID reused across attempts/phases')
    require(stats['p0']['terminal_tasks']==80,'Final P0 audit requires 80 terminal records')
    independent_gate=gate_from_stats(stats['p0']);require(gate is not None,'Missing gate')
    require(gate['status']==independent_gate['status'] and gate['challenge_allowed']==independent_gate['challenge_allowed'],'Gate decision mismatch')
    require(gate['frozen_hash']==fhash and gate['complete_p0_observed']==stats['p0']['complete_tasks'],'Gate identity/count mismatch')
    expected_records={str(Path('runs/p0')/r['group_id']/r['procedure']/'record.json'):r['record_sha256'] for r in rows['p0']}
    require(gate['p0_record_sha256']==expected_records,'Gate P0 raw record hashes')
    for kind in ['material','rule']:require(gate['criteria'][kind]['observed']==stats['p0']['difficulty_diagnostic'][kind],'Gate observed metrics mismatch')
    require(all(stamp(gate['created_utc'])>=stamp(r['finished_utc']) for r in rows['p0']),'Gate predates P0 completion')
    if independent_gate['challenge_allowed']:require(stats['challenge']['terminal_tasks']==128,'Authorized challenge is incomplete')
    else:require(stats['challenge']['attempts']==0,'Challenge executed without gate permission')
    result={'audit_skill':'experiment-audit','stage':'independent-final-raw-recomputation','generated_at':datetime.now(timezone.utc).isoformat(),'review_independence':'same-family','acceptance_status':'provisional','deterministic_recomputation':'stdlib only; no runner/evaluate imports','real_model_calls':0,'frozen_hash':fhash,'raw_inventory_paths':len(inventory),'unique_session_ids':len(set(sessions)),'stats':stats,'gate':independent_gate,'rows':rows,'scientific_scope':'simulation_only, eight development families, no human/external/heldout confirmation','verified_billed_cost':None,'overhead_usage':'unknown'}
    target=ROOT/'audits/independent_final';target.mkdir(exist_ok=True)
    require(not (target/'recomputed.json').exists(),'Refusing overwrite of prior final audit')
    (target/'recomputed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'saved':str(target/'recomputed.json'),'gate':independent_gate,'p0_complete':stats['p0']['complete_tasks'],'challenge_complete':stats['challenge']['complete_tasks']},ensure_ascii=False))

def self_test():
    good=json.dumps({'action':'A','cited_sources':[],'brief_justification':'规则','confidence':3})
    require(schema_parse(good) is not None,'Valid schema fixture')
    require(schema_parse(good.replace('"confidence": 3','"confidence": true')) is None,'Boolean confidence fixture')
    u=usage_summary([{'input_tokens':5,'output_tokens':7},{'input_tokens':None,'output_tokens':3}]);require(u['sum_input_tokens'] is None and u['known_input_tokens']==5 and u['sum_output_tokens']==10,'Partial usage fixture')
    ev=parse_events('\n'.join(json.dumps(x) for x in [{'type':'thread.started','thread_id':'u'},{'type':'turn.started'},{'type':'turn.completed','usage':{}}]));require(ev['valid_lifecycle'],'Lifecycle fixture')
    require(not parse_events('{"type":"turn.completed"}')['valid_lifecycle'],'Invalid lifecycle fixture')
    print(json.dumps({'passed':True,'pure_offline_checks':5,'imports_reviewed_implementation':False,'real_model_calls':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--self-test',action='store_true');group.add_argument('--execute-final',action='store_true');args=p.parse_args()
    if args.self_test:self_test()
    else:execute_final()
