"""New independent probes; fixtures only, all model transport mocked."""
from pathlib import Path
from unittest.mock import patch
import contextlib,io,json,subprocess,sys,tempfile,uuid
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'harness'),str(ROOT/'analysis'),str(ROOT/'tests')]
import runner,evaluate
from test_v3 import V3ProtocolTests
RESULTS=[]
def answer(action='A'):return json.dumps({'action':action,'cited_sources':['S1'],'brief_justification':'依据制度','confidence':3},ensure_ascii=False)
def fake(cmd,output_answer='A',event_answer=None,prior=None,**kwargs):
    output=Path(cmd[cmd.index('-o')+1]);text=answer(output_answer);output.write_text(text)
    messages=([{'type':'item.completed','item':{'type':'agent_message','text':answer(prior)}}] if prior else [])
    messages.append({'type':'item.completed','item':{'type':'agent_message','text':answer(event_answer or output_answer)}})
    events=[{'type':'thread.started','thread_id':uuid.uuid4().hex},{'type':'turn.started'},*messages,{'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':5}}]
    return subprocess.CompletedProcess(cmd,0,'\n'.join(map(json.dumps,events)),'')
def record(name,passed,observed):RESULTS.append({'probe':name,'passed':bool(passed),'observed':observed})
def task(call):
    with tempfile.TemporaryDirectory() as d,patch.object(runner,'R',Path(d)),patch.object(runner.subprocess,'run',side_effect=call) as mock:
        job={'group_id':'u_r1','item_id':'u','repeat':1,'procedure':'P0'}
        r=runner.response_task('p0',job,{'public_text':'规则A。'},None,'frozen')
        r2=runner.response_task('p0',job,{'public_text':'规则A。'},None,'frozen')
        return r,mock.call_count
rec,calls=task(lambda cmd,**kwargs:fake(cmd,event_answer='B',**kwargs))
actual_event_action=json.loads(rec['attempts'][0]['completed_agent_messages'][-1])['action']
record('CORRECTED_response_A_final_event_B',rec['status']=='protocol_failure' and actual_event_action=='B' and calls==1,{'status':rec['status'],'actual_event_action':actual_event_action,'actual_response_action':json.loads(rec['raw_final'])['action'],'calls_with_resume':calls})
rec,calls=task(lambda cmd,**kwargs:fake(cmd,output_answer='B',prior='A',**kwargs))
record('earlier_agent_message_does_not_override_final',rec['status']=='complete' and rec['parsed']['action']=='B' and calls==1,{'status':rec['status'],'calls_with_resume':calls})
def empty(cmd,**kwargs):
    cp=fake(cmd,**kwargs);Path(cmd[cmd.index('-o')+1]).write_text('');return cp
rec,calls=task(empty)
record('empty_output_conflicting_with_nonempty_message',rec['status']=='protocol_failure' and calls==1,{'status':rec['status'],'calls_with_resume':calls})

case=V3ProtocolTests();case.setUp()
try:
    jobs=runner.verify()['phase_schedule']['p0']['jobs'];job=jobs[-1]
    ad=case.root/'runs/p0'/job['group_id']/job['procedure']/'attempt_02';ad.mkdir(parents=True);(ad/'response.json').write_text(answer())
    error=None
    with patch.object(runner.subprocess,'run',side_effect=AssertionError('No subject call allowed')) as mock,contextlib.redirect_stdout(io.StringIO()):
        try:runner.run('p0',12)
        except Exception as exc:error=repr(exc)
    record('late_scheduled_partial_blocks_whole_dispatch',mock.call_count==0 and error is not None,{'calls':mock.call_count,'error':error})
finally:case.tearDown()

case=V3ProtocolTests();case.setUp()
try:
    def gate_profile(cmd,**kwargs):
        group=Path(cmd[cmd.index('-o')+1]).parents[2].name
        family,state,advice=group[:3],group[4:-3].rsplit('_',1)[0],group[4:-3].rsplit('_',1)[1]
        wrong=(advice=='flawed' and ((family[1:]=='05' and state in ['base','decisive_change']) or (family[1:] in ['06','07'] and state=='base')))
        wrong=wrong or (family[1:]=='05' and advice=='aligned' and state!='missing') or (family[1:]=='05' and state=='missing')
        return fake(cmd,output_answer='B' if wrong else 'A',**kwargs)
    with patch.object(runner.subprocess,'run',side_effect=gate_profile),contextlib.redirect_stdout(io.StringIO()):runner.run('p0',12)
    _,summary,_=evaluate.collect_phase('p0');g=evaluate.make_gate(summary)
    record('raw_backed_gate_all_lower_boundaries',g['status']=='eligible_for_independent_holdout' and not g['challenge_allowed'],{'status':g['status'],'diagnostic':summary['difficulty_diagnostic']})
    with contextlib.redirect_stdout(io.StringIO()):evaluate.run('p0',True)
    error=None
    with patch.object(runner.subprocess,'run',side_effect=AssertionError('Challenge forbidden')) as mock,contextlib.redirect_stdout(io.StringIO()):
        try:runner.run('challenge',12)
        except Exception as exc:error=repr(exc)
    record('raw_gate_PASS_blocks_challenge_zero_calls',mock.call_count==0 and error is not None,{'calls':mock.call_count,'error':error})
finally:case.tearDown()

case=V3ProtocolTests();case.setUp()
try:
    with patch.object(runner.subprocess,'run',side_effect=fake),contextlib.redirect_stdout(io.StringIO()):runner.run('p0',12);evaluate.run('p0',True);runner.run('challenge',12)
    p=next((case.root/'runs/challenge').glob('*/*/record.json'));original=p.read_bytes();p.unlink()
    with patch.object(runner.subprocess,'run',side_effect=AssertionError('Recovery must use stored final')) as mock,contextlib.redirect_stdout(io.StringIO()):runner.run('challenge',12)
    record('sealed_challenge_final_recovers_without_resampling',mock.call_count==0 and p.exists() and runner.read(p)['raw_final']==json.loads(original)['raw_final'],{'calls':mock.call_count,'restored':p.exists()})
    first=next((case.root/'runs/p0').glob('*/*/record.json'));x=runner.read(first);y=runner.read(p)
    # Equal session text in raw stream is an adversarial input, independent of mutable saved summaries.
    ad=p.parent/'attempt_01';text=(ad/'events.jsonl').read_text().replace(y['attempts'][0]['thread_ids'][0],x['attempts'][0]['thread_ids'][0]);(ad/'events.jsonl').write_text(text)
    info=runner.events_info(text);y['attempts'][0].update(info);y['attempts'][0]['stdout_sha256']=runner.sha(text);runner.dump(ad/'meta.json',y['attempts'][0]);runner.dump(p,y)
    _,s,a=evaluate.collect_phase('challenge')
    record('cross_phase_duplicate_sessions_rejected',not s['passed_integrity'] and bool(a['duplicate_session_ids']),{'integrity':s['passed_integrity'],'duplicates':len(a['duplicate_session_ids'])})
finally:case.tearDown()
print(json.dumps({'real_model_calls':0,'original_probe_correction':'Original F2 text substitution did not change nested escaped JSON. This script constructs A/B sources explicitly; original evidence retained unchanged.','probes':RESULTS},ensure_ascii=False,indent=2))
