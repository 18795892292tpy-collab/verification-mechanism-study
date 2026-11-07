"""Independent offline probes. All subject subprocess calls are mocked."""
from pathlib import Path
from unittest.mock import patch
import contextlib, io, json, sys, tempfile, subprocess, uuid

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT/'harness'), str(ROOT/'analysis'), str(ROOT/'tests')]
import runner, evaluate
from test_v3 import V3ProtocolTests

VALID = json.dumps({'action':'A','cited_sources':['S1'],'brief_justification':'依据制度','confidence':3},ensure_ascii=False)
RESULTS = []

def record(name, observed, expected, passed):
    RESULTS.append({'probe':name,'observed':observed,'expected':expected,'passed':bool(passed)})

def fake(cmd, **kwargs):
    Path(cmd[cmd.index('-o')+1]).write_text(VALID)
    events = [{'type':'thread.started','thread_id':uuid.uuid4().hex}, {'type':'turn.started'},
              {'type':'item.completed','item':{'type':'agent_message','text':VALID}},
              {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':5}}]
    return subprocess.CompletedProcess(cmd,0,'\n'.join(map(json.dumps,events)),'')

def fresh_case():
    case = V3ProtocolTests();case.setUp();return case

def local_response(name, call):
    with tempfile.TemporaryDirectory() as d, patch.object(runner,'R',Path(d)), patch.object(runner.subprocess,'run',side_effect=call) as mocked:
        job={'group_id':'unit_r1','item_id':'unit','repeat':1,'procedure':'P0'}
        rec=runner.response_task('p0',job,{'public_text':'规则：A。'},None,'mock-frozen')
        again=runner.response_task('p0',job,{'public_text':'规则：A。'},None,'mock-frozen')
        return rec,mocked.call_count

case=fresh_case()
try:
    with patch.object(runner.subprocess,'run',side_effect=fake),contextlib.redirect_stdout(io.StringIO()):runner.run('p0',12)
    f=runner.verify();job=f['phase_schedule']['challenge']['jobs'][0]
    ad=case.root/'runs/challenge'/job['group_id']/job['procedure']/'attempt_01';ad.mkdir(parents=True)
    (ad/'attempt_started.json').write_text(json.dumps({'started_utc':'2000-01-01T00:00:00+00:00'}))
    (ad/'response.json').write_text(VALID)
    _,summary,audit=evaluate.collect_phase('p0');gate=evaluate.make_gate(summary)
    record('cross_phase_unsealed_attempt_blocks_gate',{'integrity':summary['passed_integrity'],'challenge_allowed':gate['challenge_allowed'],'unsealed':audit['unsealed_attempts'],'inventory_attempt_dirs':audit['run_inventory']['observed_attempt_directories']},'integrity false / challenge disallowed',not summary['passed_integrity'] and not gate['challenge_allowed'])
finally:case.tearDown()

def inconsistent_final(cmd,**kwargs):
    cp=fake(cmd,**kwargs);cp.stdout=cp.stdout.replace('"action": "A"','"action": "B"');return cp
rec,calls=local_response('inconsistent_final',inconsistent_final)
record('output_vs_final_event_consistency',{'status':rec['status'],'parsed':rec['parsed'],'calls_including_resume':calls},'reject conflicting completed message and response file',rec['status']!='complete' and calls==1)

def error_item(cmd,**kwargs):
    cp=fake(cmd,**kwargs);lines=cp.stdout.splitlines();lines.insert(-1,json.dumps({'type':'item.completed','item':{'type':'error','message':'fatal response transport failed'}}));cp.stdout='\n'.join(lines);return cp
rec,calls=local_response('error_item',error_item)
record('error_item_success_classification',{'status':rec['status'],'errors':rec['attempts'][0]['error_items'],'calls_including_resume':calls},'explicit failure or documented accepted-error semantics',rec['status']!='complete')

def event_final_only(cmd,**kwargs):
    cp=fake(cmd,**kwargs);Path(cmd[cmd.index('-o')+1]).unlink();return cp
rec,calls=local_response('event_final_only',event_final_only)
record('event_final_without_output_not_resampled',{'status':rec['status'],'raw_final':rec.get('raw_final'),'calls_including_resume':calls},'technical_failure and exactly one call',rec['status']=='technical_failure' and rec['raw_final']==VALID and calls==1)

def failed_with_final(cmd,**kwargs):
    cp=fake(cmd,**kwargs);cp.returncode=1;return cp
rec,calls=local_response('failed_with_final',failed_with_final)
record('process_failure_with_final_not_resampled',{'status':rec['status'],'calls_including_resume':calls},'technical_failure and exactly one call',rec['status']=='technical_failure' and calls==1)

with tempfile.TemporaryDirectory() as d, patch.object(runner,'R',Path(d)),patch.object(runner.subprocess,'run',side_effect=fake) as mocked:
    job={'group_id':'unit_r1','item_id':'unit','repeat':1,'procedure':'P0'}
    ad=Path(d)/'runs/p0/unit_r1/P0/attempt_02';ad.mkdir(parents=True)
    (ad/'attempt_started.json').write_text('{}');(ad/'response.json').write_text(VALID)
    caught=None
    try:rec=runner.response_task('p0',job,{'public_text':'规则：A。'},None,'mock-frozen')
    except Exception as exc:caught=repr(exc)
    record('later_partial_final_blocks_any_new_attempt',{'calls':mocked.call_count,'exception':caught},'zero calls before integrity failure',mocked.call_count==0)

with tempfile.TemporaryDirectory() as d:
    root=Path(d);target=root/'unrelated.txt';target.write_text('sentinel');locks=root/'runs';locks.mkdir();(locks/'.integrity.lock').symlink_to(target)
    caught=None
    try:
        with runner.DirectoryLock(locks):pass
    except Exception as exc:caught=repr(exc)
    record('directory_lock_symlink_refused_without_mutation',{'target_preserved':target.read_text()=='sentinel','exception':caught},'symlink refused; target sentinel retained',target.read_text()=='sentinel' and caught is not None)

base_summary={'phase':'p0','planned_tasks':80,'terminal_tasks':80,'complete_tasks':80,'passed_integrity':True,'frozen_hash':'mock','record_sha256':{},'difficulty_diagnostic':{}}
for kind in ['material','rule']:
    base_summary['difficulty_diagnostic'][kind]={'present_flawed_n':16,'present_aligned_n':16,'missing_n':8,'natural_errors':4,'error_families':['F1','F2','F3'],'present_aligned_correct':12,'missing_correct':6}
import copy
gate_checks=[]
for field,value,eligible in [('natural_errors',3,False),('natural_errors',4,True),('natural_errors',8,True),('natural_errors',9,False),('error_families',['F1','F2'],False),('present_aligned_correct',11,False),('missing_correct',5,False),('present_flawed_n',15,False)]:
    s=copy.deepcopy(base_summary);s['difficulty_diagnostic']['rule'][field]=value
    g=evaluate.make_gate(s);gate_checks.append((g['status']=='eligible_for_independent_holdout')==eligible)
for field,value in [('complete_tasks',79),('passed_integrity',False)]:
    s=copy.deepcopy(base_summary);s[field]=value;g=evaluate.make_gate(s);gate_checks.append(g['status']=='technical_block' and not g['challenge_allowed'])
record('gate_threshold_boundaries_and_technical_block',{'cases':len(gate_checks),'all_correct':all(gate_checks)},'all ten boundary cases',all(gate_checks))

value=evaluate.usage_totals([{'usage':{'input_tokens':5,'output_tokens':7}},{'usage':{'output_tokens':3}}])
record('partial_usage_keeps_known_subtotal_and_unknown_total',value,'input total None, known input5, output total10',value['sum_input_tokens'] is None and value['known_input_tokens']==5 and value['sum_output_tokens']==10)

case=fresh_case()
try:
    rows=[]
    # Unequal per-family success deliberately distinguishes task weighting and family weighting.
    for item in case.drafts:
        for proc in ['P1','P3','P7','P8']:
            f=int(item['family_id'][1:])-5
            correct=(proc=='P7' and (item['error_type']=='rule' or f%2==0)) or (proc=='P3' and item['state']=='base') or (proc=='P1' and item['error_type']=='material' and f==0)
            rows.append({**item,'group_id':item['item_id']+'_r1','procedure':proc,'status':'complete','correct':int(correct),'input_tokens':0,'output_tokens':0,'seconds':0})
    summary=evaluate.summarize(rows,'challenge');checks=[]
    for a,b in [('P7','P8'),('P7','P3'),('P3','P1')]:
        for condition in ['error','correct']:
            kinds={}
            for kind in ['material','rule']:
                family_values=[]
                for family in sorted({r['family_id'] for r in rows if r['error_type']==kind}):
                    rr=[r for r in rows if r['family_id']==family and r['draft_condition']==condition]
                    av=sum(r['correct'] for r in rr if r['procedure']==a)/2
                    bv=sum(r['correct'] for r in rr if r['procedure']==b)/2
                    family_values.append(av-bv)
                kinds[kind]=sum(family_values)/4
            got=summary['contrasts'][a+'-'+b][condition]
            checks.append(got['type_means']==kinds and got['interaction_rule_minus_material']==kinds['rule']-kinds['material'])
    record('independent_family_contrast_recomputation',{'comparisons':len(checks),'all_agree':all(checks)},'all six condition/contrast combinations exact',all(checks))
    for item in case.drafts:
        p=runner.build_prompt({'procedure':'P7'},item,item['draft_text'])
        assert item['item_id'] not in p and 'draft_condition' not in p
    record('challenge_private_labels_not_in_prompt',{'checked':len(case.drafts)},'32 prompts omit ID and private condition labels',True)
finally:case.tearDown()

print(json.dumps({'real_model_calls':0,'fixtures':'temporary offline roots; canonical source imported read-only','probes':RESULTS},ensure_ascii=False,indent=2))
