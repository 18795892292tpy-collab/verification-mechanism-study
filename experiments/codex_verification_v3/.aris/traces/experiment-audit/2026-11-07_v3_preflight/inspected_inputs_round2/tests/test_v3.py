"""Runner fault tests: subprocess is ALWAYS mocked, no model task is executed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import time
import threading
import io
import contextlib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
import runner
sys.path.insert(0,str(ROOT/"analysis"))
import evaluate

VALID = json.dumps({"action": "A", "cited_sources": ["S1"],
                    "brief_justification": "依据给定规则", "confidence": 3}, ensure_ascii=False)


def fake_call(final=VALID, extra_events=(), returncode=0):
    def invoke(cmd, **kwargs):
        output = Path(cmd[cmd.index("-o") + 1])
        # Start marker must be persisted before a call is allowed to start.
        assert (output.parent / "attempt_started.json").is_file()
        if final is not None:
            output.write_text(final)
        events = [{"type": "thread.started", "thread_id": "test-session"},
                  {"type": "turn.started"}, *extra_events,
                  *([{"type": "item.completed", "item": {"type": "agent_message", "text": final}}] if final is not None else []),
                  {"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 9}}]
        return subprocess.CompletedProcess(cmd, returncode, "\n".join(json.dumps(e) for e in events), "")
    return invoke


class RunnerOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch_r = patch.object(runner, "R", self.root)
        self.patch_r.start()
        self.job = {"group_id": "item_r1", "item_id": "item", "repeat": 1, "procedure": "P0"}
        self.item = {"public_text": "虚构规则：选 A。"}

    def tearDown(self):
        self.patch_r.stop()
        self.tmp.cleanup()

    @property
    def out(self):
        return self.root / "runs" / "p0" / self.job["group_id"] / self.job["procedure"]

    def execute(self, side_effect=None, first=None):
        with patch.object(runner.subprocess, "run", side_effect=side_effect or fake_call()) as mocked:
            result = runner.response_task("p0", self.job, self.item, first, "frozen")
        return result, mocked.call_count

    def test_completed_task_resumes_without_call_and_keeps_exact_text(self):
        first, calls = self.execute()
        self.assertEqual(calls, 1)
        self.assertEqual(first["status"], "complete")
        again, calls = self.execute()
        self.assertEqual(calls, 0)
        self.assertEqual(first, again)
        self.assertEqual(again["raw_final"], VALID)

    def test_interrupted_attempt_is_not_silently_resampled(self):
        ad = self.out / "attempt_01"
        ad.mkdir(parents=True)
        (ad / "attempt_started.json").write_text("{}")
        (ad / "response.json").write_text(VALID)
        with patch.object(runner.subprocess, "run", side_effect=AssertionError("must not call")) as mocked:
            with self.assertRaisesRegex(RuntimeError, "Uncommitted attempt"):
                runner.response_task("p0", self.job, self.item, None, "frozen")
        mocked.assert_not_called()
        self.assertEqual((ad / "response.json").read_text(), VALID)

    def test_marker_without_any_output_is_also_uncommitted(self):
        ad = self.out / "attempt_01"
        ad.mkdir(parents=True)
        (ad / "attempt_started.json").write_text("{}")
        with patch.object(runner.subprocess, "run") as mocked:
            with self.assertRaisesRegex(RuntimeError, "Uncommitted attempt"):
                runner.response_task("p0", self.job, self.item, None, "frozen")
        mocked.assert_not_called()

    def test_later_partial_final_blocks_calls_before_attempt_one(self):
        ad=self.out/'attempt_02';ad.mkdir(parents=True)
        (ad/'attempt_started.json').write_text('{}');(ad/'response.json').write_text(VALID)
        with patch.object(runner.subprocess,'run') as calls:
            with self.assertRaisesRegex(RuntimeError,'Noncontiguous'):
                runner.response_task('p0',self.job,self.item,None,'frozen')
        calls.assert_not_called();self.assertEqual((ad/'response.json').read_text(),VALID)
        self.assertFalse((self.out/'attempt_01').exists())

    def test_later_unsealed_attempt_blocks_earlier_technical_retry(self):
        self.execute(fake_call(final=None,returncode=1))
        (self.out/'record.json').unlink()
        (self.out/'attempt_02/meta.json').unlink()
        (self.out/'attempt_02/response.json').write_text(VALID)
        with patch.object(runner.subprocess,'run') as calls:
            with self.assertRaisesRegex(RuntimeError,'Uncommitted attempt'):
                runner.response_task('p0',self.job,self.item,None,'frozen')
        calls.assert_not_called()

    def test_existing_attempt_after_final_is_rejected_before_resume(self):
        self.execute();(self.out/'record.json').unlink();(self.out/'attempt_02').mkdir()
        with patch.object(runner.subprocess,'run') as calls:
            with self.assertRaisesRegex(RuntimeError,'after returned final'):
                runner.response_task('p0',self.job,self.item,None,'frozen')
        calls.assert_not_called()

    def test_response_event_conflict_retained_as_failure_without_resampling(self):
        def conflict(cmd,**kwargs):
            cp=fake_call()(cmd,**kwargs)
            # Event JSON has the message JSON escaped inside its text field.
            events=[json.loads(line) for line in cp.stdout.splitlines()]
            events[-2]['item']['text']=VALID.replace('"A"','"B"')
            cp.stdout='\n'.join(json.dumps(e) for e in events)
            return cp
        result,calls=self.execute(conflict)
        self.assertEqual(calls,1);self.assertEqual(result['status'],'protocol_failure')
        self.assertIsNone(result['parsed']);self.assertEqual(result['raw_final'],VALID)
        self.assertEqual(result['attempts'][0]['completed_agent_messages'][-1],VALID.replace('"A"','"B"'))
        again,calls=self.execute();self.assertEqual(calls,0);self.assertEqual(again,result)

    def test_empty_response_file_cannot_override_nonempty_event_final(self):
        def blank_output(cmd,**kwargs):
            cp=fake_call()(cmd,**kwargs);Path(cmd[cmd.index('-o')+1]).write_text('');return cp
        result,calls=self.execute(blank_output)
        self.assertEqual(result['status'],'protocol_failure');self.assertEqual(calls,1)
        self.assertEqual(self.execute()[1],0)

    def test_error_item_with_success_turn_is_technical_failure_and_stops_dispatch(self):
        result,calls=self.execute(fake_call(extra_events=[{'type':'item.completed','item':{'type':'error','message':'fatal response transport failed'}}]))
        self.assertEqual(result['status'],'technical_failure');self.assertEqual(calls,1)
        self.assertEqual(result['attempts'][0]['service_block'],'network_transport')
        again,calls=self.execute();self.assertEqual(calls,0);self.assertEqual(again,result)

    def test_tampered_saved_raw_answer_rejected(self):
        result, _ = self.execute()
        result["raw_final"] = VALID.replace('"A"', '"B"')
        (self.out / "record.json").write_text(json.dumps(result))
        with self.assertRaisesRegex(RuntimeError, "final response hash"):
            self.execute()

    def test_tampered_parsed_answer_rejected(self):
        result, _ = self.execute()
        result["parsed"]["action"] = "B"
        (self.out / "record.json").write_text(json.dumps(result))
        with self.assertRaisesRegex(RuntimeError, "status/answer"):
            self.execute()

    def test_tampered_prompt_rejected(self):
        self.execute()
        (self.out / "prompt.txt").write_text("changed")
        with self.assertRaisesRegex(RuntimeError, "prompt mismatch"):
            self.execute()

    def test_tampered_event_log_rejected(self):
        self.execute()
        with (self.out / "attempt_01" / "events.jsonl").open("a") as stream:
            stream.write('\n{"type":"tool.called"}')
        with self.assertRaisesRegex(RuntimeError, "artifact hash"):
            self.execute()

    def test_sealed_attempt_response_checked_even_without_record(self):
        self.execute()
        (self.out / "record.json").unlink()
        (self.out / "attempt_01" / "response.json").write_text("changed")
        with patch.object(runner.subprocess, "run") as mocked:
            with self.assertRaisesRegex(RuntimeError, "response hash"):
                runner.response_task("p0", self.job, self.item, None, "frozen")
        mocked.assert_not_called()

    def test_sealed_attempt_recovers_record_without_resampling(self):
        original, _ = self.execute()
        (self.out / "record.json").unlink()
        recovered, calls = self.execute()
        self.assertEqual(calls, 0)
        self.assertEqual(recovered["raw_final"], original["raw_final"])
        self.assertEqual(recovered["attempts"], original["attempts"])

    def test_unknown_top_event_is_protocol_failure_no_retry(self):
        result, calls = self.execute(fake_call(extra_events=[{"type": "tool.called", "name": "exec"}]))
        self.assertEqual(result["status"], "protocol_failure")
        self.assertEqual(calls, 1)

    def test_unknown_item_is_protocol_failure_no_retry(self):
        result, calls = self.execute(fake_call(extra_events=[{"type": "item.completed", "item": {"type": "command_execution"}}]))
        self.assertEqual(result["status"], "protocol_failure")
        self.assertEqual(calls, 1)

    def test_non_json_stdout_is_not_ignored(self):
        info = runner.events_info('not-json\n{"type":"turn.completed","usage":{}}')
        self.assertTrue(any(x.get("kind") == "non_json_stdout" for x in info["unexpected_items"]))

    def test_parse_failure_is_final_and_not_retried(self):
        result, calls = self.execute(fake_call(final="not-json"))
        self.assertEqual(result["status"], "parse_failure")
        self.assertEqual(calls, 1)
        resumed, calls = self.execute()
        self.assertEqual(resumed["status"], "parse_failure")
        self.assertEqual(calls, 0)

    def test_no_response_can_retry_at_most_twice(self):
        result, calls = self.execute(fake_call(final=None, returncode=1))
        self.assertEqual(calls, 2)
        self.assertEqual(result["status"], "technical_failure")
        _, calls = self.execute()
        self.assertEqual(calls, 0)

    def test_review_resume_refuses_a_different_first(self):
        self.job["procedure"] = "P3"
        first, calls = self.execute(first="same first A")
        self.assertEqual(first["first_sha256"], runner.sha("same first A"))
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            self.execute(first="another first A")


class V3ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patches=[patch.object(runner,'R',self.root),patch.object(evaluate,'R',self.root),patch.object(runner,'runtime_identity',return_value={'host':'mock','root':str(self.root)})]
        for p in self.patches:p.start()
        self.items=[];self.drafts=[];self.keys=[];self.draftkeys=[]
        for kind,prefix in [('material','M'),('rule','R')]:
            for f in range(5,9):
                family=f'{prefix}{f:02}'
                for state in ['base','decisive_change','irrelevant','paraphrase','missing']:
                    for advice in ['aligned','flawed']:
                        item={'item_id':f'{family}_{state}_{advice}','family_id':family,'error_type':kind,'state':state,'advice':advice,'public_text':'规则固定选择A。'}
                        self.items.append(item);self.keys.append({**item,'correct_action':'A'})
                for state in ['base','decisive_change']:
                    for condition in ['correct','error']:
                        draft={**json.loads(VALID),'action':'A' if condition=='correct' else 'B'}
                        item={'item_id':f'{family}_{state}_{condition}','family_id':family,'error_type':kind,'state':state,'draft_condition':condition,'public_text':'规则固定选择A。','draft_text':json.dumps(draft,ensure_ascii=False)}
                        self.drafts.append(item);self.draftkeys.append({**item,'correct_action':'A'})
        for name in runner.FROZEN_FILES:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
        for name,items in [('prompts/p0_items.json',self.items),('keys/p0_keys.json',self.keys),('prompts/challenge_items.json',self.drafts),('keys/challenge_keys.json',self.draftkeys)]:runner.dump(self.root/name,items)
        runner.dump(self.root/'audits/case_review.json',{'status':'passed_internal'});runner.dump(self.root/'audits/harness_tests.json',{'passed':True})
        with contextlib.redirect_stdout(io.StringIO()):runner.freeze()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def fake(self,cmd,**kwargs):
        call=fake_call();result=call(cmd,**kwargs)
        result.stdout=result.stdout.replace('test-session',uuid.uuid4().hex)
        return result
    def run_p0(self):
        with patch.object(runner.subprocess,'run',side_effect=self.fake) as calls,contextlib.redirect_stdout(io.StringIO()):runner.run('p0',12)
        return calls.call_count
    def gate(self):
        with contextlib.redirect_stdout(io.StringIO()):evaluate.run('p0',True)
        return runner.read(self.root/'analysis/decision_gate.json')
    def test_exact_schedules(self):
        f=runner.verify();self.assertEqual(f['phase_schedule']['p0']['tasks'],80);self.assertEqual(f['phase_schedule']['challenge']['tasks'],128)
    def test_freeze_rejects_source_change(self):
        (self.root/'protocol/analysis_plan.json').write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'Frozen file changed'):runner.verify()
    def test_runtime_change_rejected(self):
        with patch.object(runner,'runtime_identity',return_value={'host':'other'}):
            with self.assertRaisesRegex(RuntimeError,'Host, target'):runner.verify()
    def test_plan_csv_change_rejected(self):
        (self.root/'runs/p0/plan.csv').write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'plan.csv'):runner.verify()
    def test_unknown_run_artifact_rejected(self):
        (self.root/'runs/p0/unknown.txt').write_text('x')
        with self.assertRaisesRegex(RuntimeError,'Unplanned'):runner.verify()
    def test_symlink_rejected(self):
        (self.root/'runs/p0/symlink').symlink_to('/tmp')
        with self.assertRaisesRegex(RuntimeError,'Unplanned'):runner.verify()
    def test_writer_lock_competition(self):
        with runner.DirectoryLock(self.root/'runs'):
            with self.assertRaises(Exception):runner.run('p0',12)
    def test_writer_lock_refuses_symlink_without_mutation(self):
        target=self.root/'sentinel';target.write_text('retain me')
        (self.root/'runs/.integrity.lock').symlink_to(target)
        with self.assertRaises(OSError):
            with runner.DirectoryLock(self.root/'runs'):self.fail('symlink acquired')
        self.assertEqual(target.read_text(),'retain me')
    def test_writer_lock_refuses_special_file_and_hard_link(self):
        lockpath=self.root/'runs/.integrity.lock';os.mkfifo(lockpath)
        with self.assertRaises(RuntimeError):
            with runner.DirectoryLock(self.root/'runs'):self.fail('FIFO acquired')
        lockpath.unlink();target=self.root/'sentinel';target.write_text('retain me');os.link(target,lockpath)
        with self.assertRaises(RuntimeError):
            with runner.DirectoryLock(self.root/'runs'):self.fail('hard link acquired')
        self.assertEqual(target.read_text(),'retain me')
    def test_writer_lock_refuses_symlinked_directory(self):
        linked=self.root/'linked_runs';linked.symlink_to(self.root/'runs')
        with self.assertRaises(OSError):
            with runner.DirectoryLock(linked):self.fail('symlinked directory acquired')
        self.assertFalse((self.root/'runs/.integrity.lock').exists())
    def test_final_source_conflict_blocks_integrity_and_gate(self):
        calls=0
        def conflicting_first(cmd,**kwargs):
            nonlocal calls
            cp=self.fake(cmd,**kwargs);calls+=1
            if calls==1:
                events=[json.loads(line) for line in cp.stdout.splitlines()]
                events[-2]['item']['text']=VALID.replace('"A"','"B"')
                cp.stdout='\n'.join(json.dumps(e) for e in events)
            return cp
        with patch.object(runner.subprocess,'run',side_effect=conflicting_first),contextlib.redirect_stdout(io.StringIO()):runner.run('p0',1)
        _,summary,audit=evaluate.collect_phase('p0')
        self.assertEqual(calls,80);self.assertEqual(summary['complete_tasks'],79)
        self.assertEqual(summary['status_counts']['protocol_failure'],1)
        self.assertFalse(summary['passed_integrity']);self.assertEqual(len(audit['final_source_conflicts']),1)
        self.assertFalse(evaluate.make_gate(summary)['challenge_allowed'])
    def test_pre_gate_cross_phase_unsealed_attempt_blocks_p0_gate(self):
        self.run_p0();job=runner.verify()['phase_schedule']['challenge']['jobs'][0]
        ad=self.root/'runs/challenge'/job['group_id']/job['procedure']/'attempt_01';ad.mkdir(parents=True)
        (ad/'attempt_started.json').write_text('{}');(ad/'response.json').write_text(VALID)
        _,summary,audit=evaluate.collect_phase('p0')
        self.assertFalse(summary['passed_integrity']);self.assertFalse(evaluate.make_gate(summary)['challenge_allowed'])
        self.assertEqual(audit['unsealed_attempts'],[str(ad.relative_to(self.root))])
        self.assertEqual(summary['actual_cli_attempts'],80)
        with self.assertRaisesRegex(RuntimeError,'Integrity audit failed'):self.gate()
        self.assertFalse((self.root/'analysis/decision_gate.json').exists())
    def test_post_gate_cross_phase_unsealed_attempt_blocks_gate_revalidation(self):
        self.run_p0();self.gate();job=runner.verify()['phase_schedule']['challenge']['jobs'][0]
        ad=self.root/'runs/challenge'/job['group_id']/job['procedure']/'attempt_01';ad.mkdir(parents=True)
        (ad/'attempt_started.json').write_text('{}')
        _,summary,audit=evaluate.collect_phase('p0')
        self.assertFalse(summary['passed_integrity']);self.assertTrue(audit['unsealed_attempts'])
        with self.assertRaisesRegex(RuntimeError,'gate does not match'):runner.check_challenge_gate()
    def test_cross_phase_sealed_final_without_record_is_audited(self):
        self.run_p0();self.gate();f=runner.verify();job=f['phase_schedule']['challenge']['jobs'][0]
        item=next(i for i in self.drafts if i['item_id']==job['item_id'])
        with patch.object(runner.subprocess,'run',side_effect=self.fake):
            runner.response_task('challenge',job,item,item['draft_text'],runner.file_sha(self.root/'protocol/frozen.json'))
        task=self.root/'runs/challenge'/job['group_id']/job['procedure'];(task/'record.json').unlink()
        _,summary,audit=evaluate.collect_phase('p0')
        self.assertTrue(summary['passed_integrity']);self.assertFalse(audit['record_errors'])
        (task/'attempt_01/response.json').write_text('changed')
        with self.assertRaisesRegex(RuntimeError,'response hash'):evaluate.collect_phase('p0')
    def test_global_precheck_blocks_all_dispatch_for_late_partial_final(self):
        job=runner.verify()['phase_schedule']['p0']['jobs'][-1]
        ad=self.root/'runs/p0'/job['group_id']/job['procedure']/'attempt_02';ad.mkdir(parents=True)
        (ad/'attempt_started.json').write_text('{}');(ad/'response.json').write_text(VALID)
        with patch.object(runner.subprocess,'run') as calls:
            with self.assertRaisesRegex(RuntimeError,'Noncontiguous'):runner.run('p0',12)
        calls.assert_not_called()
    def test_incomplete_p0_cannot_gate_or_challenge(self):
        with self.assertRaisesRegex(RuntimeError,'all80 terminal'):self.gate()
        with self.assertRaisesRegex(RuntimeError,'all80 terminal'):runner.run('challenge',12)
    def test_full_mock_resume_and_authored_identity(self):
        self.assertEqual(self.run_p0(),80);self.assertEqual(self.run_p0(),0)
        before={str(p):runner.file_sha(p) for p in (self.root/'runs/p0').glob('*/*/record.json')}
        gate=self.gate();self.assertTrue(gate['challenge_allowed']);self.assertEqual(gate['status'],'development_gate_failed')
        with patch.object(runner.subprocess,'run',side_effect=self.fake) as calls,contextlib.redirect_stdout(io.StringIO()):runner.run('challenge',12)
        self.assertEqual(calls.call_count,128)
        with contextlib.redirect_stdout(io.StringIO()):summary=evaluate.run('challenge')
        self.assertEqual(summary['complete_tasks'],128);self.assertTrue(summary['passed_integrity'])
        for proc in ['P1','P3','P7','P8']:
            self.assertEqual(summary['procedures'][proc]['authored_error_planned'],16)
            self.assertEqual(summary['procedures'][proc]['authored_correct_planned'],16)
        for p in (self.root/'runs/challenge').glob('*/*/record.json'):
            rec=runner.read(p);self.assertEqual(rec['first_origin'],'authored_fixed_draft');self.assertIsNotNone(rec['first_sha256'])
        recovery_record=next((self.root/'runs/challenge').glob('*/*/record.json'))
        saved=runner.read(recovery_record);recovery_record.unlink()
        with patch.object(runner.subprocess,'run',side_effect=self.fake) as calls,contextlib.redirect_stdout(io.StringIO()):runner.run('challenge',12)
        self.assertEqual(calls.call_count,0);self.assertEqual(before,{str(p):runner.file_sha(p) for p in (self.root/'runs/p0').glob('*/*/record.json')})
        self.assertEqual(runner.read(recovery_record)['raw_final'],saved['raw_final'])
        self.assertEqual(runner.read(recovery_record)['attempts'],saved['attempts'])
    def test_gate_tamper_rejected(self):
        self.run_p0();self.gate();p=self.root/'analysis/decision_gate.json';d=runner.read(p);d['complete_p0_observed']=79;runner.dump(p,d)
        with self.assertRaisesRegex(RuntimeError,'gate does not match'):runner.run('challenge',12)
    def test_p3_minus_p1_contrast_uses_its_own_treatment_and_family_denominator(self):
        rows=[]
        for item in self.drafts:
            for proc in ['P1','P3','P7','P8']:
                wrong=item['family_id']=='M05' and item['draft_condition']=='error' and proc=='P3'
                rows.append({**item,'group_id':item['item_id']+'_r1','procedure':proc,'status':'complete','correct':int(not wrong),
                             'input_tokens':0,'output_tokens':0,'seconds':0})
        s=evaluate.summarize(rows,'challenge')
        self.assertEqual(set(s['contrasts']),{'P7-P8','P7-P3','P3-P1'})
        c=s['contrasts']['P3-P1']['error']
        self.assertEqual(c['type_means'],{'material':-.25,'rule':0.0})
        self.assertEqual(c['interaction_rule_minus_material'],.25)
        self.assertEqual(c['family_results'][0]['paired_drafts'],2)
        self.assertEqual(c['family_results'][0]['difference'],-1.0)
        self.assertEqual(s['contrasts']['P7-P8']['error']['interaction_rule_minus_material'],0.0)
        self.assertEqual(s['contrasts']['P3-P1']['correct']['interaction_rule_minus_material'],0.0)
    def test_gate_timestamp_before_p0_rejected(self):
        self.run_p0();self.gate();p=self.root/'analysis/decision_gate.json';d=runner.read(p);d['created_utc']='2000-01-01T00:00:00+00:00';runner.dump(p,d)
        with self.assertRaisesRegex(RuntimeError,'predates completed P0'):runner.run('challenge',12)
    def test_gate_hash_pinned_before_first_challenge_attempt(self):
        self.run_p0();self.gate();runner.seal_json(self.root/'runs/challenge/manifest_identity.json',runner.phase_pin('challenge',runner.file_sha(self.root/'protocol/frozen.json')))
        p=self.root/'analysis/decision_gate.json';d=runner.read(p);d['created_utc']=runner.now();runner.dump(p,d)
        with self.assertRaisesRegex(RuntimeError,'Gate changed'):runner.verify()
    def test_peak_concurrency_twelve(self):
        lock=threading.Lock();active=0;peak=0
        def delayed(cmd,**kwargs):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            time.sleep(.03)
            result=self.fake(cmd,**kwargs)
            with lock:active-=1
            return result
        with patch.object(runner.subprocess,'run',side_effect=delayed),contextlib.redirect_stdout(io.StringIO()):runner.run('p0',12)
        self.assertEqual(peak,12)
    def test_usage_missing_is_not_zero(self):
        self.assertIsNone(evaluate.usage_totals([{'usage':{'input_tokens':0}}])['sum_output_tokens'])
        self.assertIsNone(evaluate.usage_totals([{'usage':{'input_tokens':True,'output_tokens':-1}}])['sum_input_tokens'])
        self.assertEqual(evaluate.usage_totals([{'usage':{'input_tokens':0,'output_tokens':0}}])['sum_input_tokens'],0)
    def test_invalid_success_lifecycle(self):
        info=runner.events_info(json.dumps({'type':'turn.completed','usage':{}}))
        self.assertTrue(info['unexpected_items'])
    def test_gate_pass_requires_both_types_and_coverage(self):
        self.run_p0();_,summary,_=evaluate.collect_phase('p0')
        for kind in ['material','rule']:
            d=summary['difficulty_diagnostic'][kind];d['natural_errors']=4;d['error_families']=['A','B','C']
        self.assertFalse(evaluate.make_gate(summary)['challenge_allowed']);self.assertEqual(evaluate.make_gate(summary)['status'],'eligible_for_independent_holdout')
        summary['difficulty_diagnostic']['rule']['error_families']=['A','B']
        self.assertTrue(evaluate.make_gate(summary)['challenge_allowed'])
        summary['complete_tasks']=79
        self.assertFalse(evaluate.make_gate(summary)['challenge_allowed']);self.assertEqual(evaluate.make_gate(summary)['status'],'technical_block')
    def test_quota_stops_dispatch(self):
        info=runner.events_info(json.dumps({'type':'error','message':'usage limit reached'}))
        self.assertEqual(runner.service_block_reason(info,'',1),'quota_or_rate_limit')

if __name__=='__main__':unittest.main(verbosity=2)
