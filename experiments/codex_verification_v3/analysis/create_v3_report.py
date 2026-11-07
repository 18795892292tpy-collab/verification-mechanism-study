#!/usr/bin/env python3
"""Create exploratory V3 report & plots from completed A1 challenge records only."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,importlib.util,json,socket,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
R=Path(__file__).resolve().parents[1]
assert socket.gethostname()=='liekkas' and R==Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
C=R/'amendments/A1_posthoc/challenge'
spec=importlib.util.spec_from_file_location('challenge_driver_report',C/'driver.py');driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)

def num(x):return type(x) is int and x>=0

def load():
 for rel in ['protocol/frozen.json','analysis/decision_gate.json','analysis/p0/summary.json','audits/DIAGNOSTIC_REVIEW.json','audits/A1_DERIVATION_REVIEW.json','amendments/A1_posthoc/results/summary.json','amendments/A1_posthoc/results/threshold_diagnostic.json','evidence_review/SUMMARY.json','prompts/challenge_items.json','keys/challenge_keys.json','amendments/A1_posthoc/challenge/authorization.json','amendments/A1_posthoc/challenge/frozen.json']:
  if not (R/rel).is_file():raise RuntimeError('Required input absent: '+rel)
 gate=read(R/'analysis/decision_gate.json');strict=read(R/'analysis/p0/summary.json');a1=read(R/'amendments/A1_posthoc/results/summary.json'); diag=read(R/'amendments/A1_posthoc/results/threshold_diagnostic.json')
 assert gate['status']=='technical_block' and gate['challenge_allowed'] is False
 assert strict['planned_tasks']==80 and sum(strict['status_counts'].values())==80
 assert a1['analysis_label']=='posthoc_exploratory' and a1['original_gate_status']=='technical_block'
 assert diag['NOT_A_RUN_GATE'] and not diag['automatic_execution_authorized']
 f=driver.verify();jobs=f['jobs'];assert len(jobs)==128 and len({(j['group_id'],j['procedure']) for j in jobs})==128
 driver.inventory(jobs)
 actual=list((C/'runs').glob('*/*/record.json')) if (C/'runs').exists() else []
 if len(actual)!=128:raise RuntimeError(f'Challenge incomplete: {len(actual)}/128 terminal; no report generated')
 items={x['item_id']:x for x in read(R/'prompts/challenge_items.json')};keys={x['item_id']:x for x in read(R/'keys/challenge_keys.json')}
 p0sessions={t for path in gate['p0_record_sha256'] for a in read(R/path)['attempts'] for t in a.get('thread_ids',[])}
 rows=[];seen=set();sources={}
 for job in jobs:
  item=items[job['item_id']];key=keys[job['item_id']];r=driver.check_task_dir(job,sha(C/'frozen.json'))
  if r is None:raise RuntimeError('Missing terminal record: '+str(job))
  classif=r['classification'];status=classif['status'];parsed=classif.get('parsed');thread=classif.get('thread_id')
  if status=='complete':
   assert thread and thread not in seen and thread not in p0sessions;seen.add(thread)
  else:assert parsed is None
  d=C/'runs'/job['group_id']/job['procedure']
  # Resource usage is distinct from validity of the answer: preserve the exact
  # completed-turn usage on a failed classification when uniquely present.
  ev=[json.loads(line) for line in (d/'attempt_01/events.jsonl').read_text().splitlines() if line.strip()]
  turns=[x for x in ev if x.get('type')=='turn.completed']
  usage=turns[0].get('usage') if len(turns)==1 and isinstance(turns[0].get('usage'),dict) else {}
  iv=usage.get('input_tokens');ov=usage.get('output_tokens')
  rows.append({'group_id':job['group_id'],'item_id':job['item_id'],'procedure':job['procedure'],'family_id':item['family_id'],'error_type':item['error_type'],'state':item['state'],'draft_condition':item['draft_condition'],'status':status,'problem':classif.get('problem'),'correct':int(status=='complete' and parsed['action']==key['correct_action']),'input_tokens':iv if num(iv) else None,'output_tokens':ov if num(ov) else None,'usage_source':'raw turn.completed' if len(turns)==1 else 'unknown','seconds':r['seconds']})
  for path in [d/'record.json',d/'prompt.txt',*(d/'attempt_01').iterdir()]:
   if path.is_file():sources[str(path.relative_to(R))]=sha(path)
 assert len(rows)==128 and len(items)==len(keys)==32
 for proc in ['P1','P3','P7','P8']:
  for condition in ['correct','error']:
   assert len([r for r in rows if r['procedure']==proc and r['draft_condition']==condition])==16
 families=[];procs={}
 for proc in ['P1','P3','P7','P8']:
  part=[r for r in rows if r['procedure']==proc];procs[proc]={'planned':len(part),'complete':sum(r['status']=='complete' for r in part)}
  for c in ['error','correct']:
   sr=[r for r in part if r['draft_condition']==c]; procs[proc][c]={'planned':len(sr),'retained_correct':sum(r['correct'] for r in sr),'not_correct':sum(not r['correct'] for r in sr),'failures':sum(r['status']!='complete' for r in sr)}
   for fam in sorted({r['family_id'] for r in sr}):
    a=[r for r in sr if r['family_id']==fam];assert len(a)==2
    families.append({'family_id':fam,'error_type':a[0]['error_type'],'procedure':proc,'draft_condition':c,'n':len(a),'correct':sum(r['correct'] for r in a),'accuracy':sum(r['correct'] for r in a)/len(a)})
 contrasts={}
 for left,right in [('P7','P8'),('P7','P3'),('P3','P1')]:
  for c in ['error','correct']:
   matched=[]
   for fam in sorted({x['family_id'] for x in families}):
    a=next(x for x in families if x['family_id']==fam and x['procedure']==left and x['draft_condition']==c);b=next(x for x in families if x['family_id']==fam and x['procedure']==right and x['draft_condition']==c)
    matched.append({'family_id':fam,'error_type':a['error_type'],'difference':a['accuracy']-b['accuracy']})
   means={k:sum(x['difference'] for x in matched if x['error_type']==k)/4 for k in ['material','rule']}
   contrasts[f'{left}-{right}:{c}']={'families':matched,'type_means':means,'interaction_rule_minus_material':means['rule']-means['material']}
 inputs=[r['input_tokens'] for r in rows];outputs=[r['output_tokens'] for r in rows]
 return {'created_utc':datetime.now(timezone.utc).isoformat(),'classification':'posthoc exploratory authored fixed draft challenge','original_gate':{'status':gate['status'],'challenge_allowed':gate['challenge_allowed']},'strict_p0':{'planned':strict['planned_tasks'],'complete':strict['complete_tasks'],'attempts':strict['actual_cli_attempts'],'status_counts':strict['status_counts']},'a1_p0':{'accepted':a1['derived_transport_accepted'],'correct':a1['derived_correct'],'planned':a1['planned_p0'],'attempts':a1['actual_cli_attempts'],'hypothetical_gate':diag['hypothetical_threshold_status'],'not_a_run_gate':True},'challenge':{'planned':128,'terminal':len(rows),'complete':sum(r['status']=='complete' for r in rows),'status_counts':dict(Counter(r['status'] for r in rows)),'actual_attempts':len(rows),'unique_complete_sessions':len(seen),'procedures':procs,'family_results':families,'contrasts':contrasts,'resources':{'input_tokens':sum(inputs) if all(num(x) for x in inputs) else None,'known_input_tokens':sum(x for x in inputs if num(x)),'input_missing':sum(not num(x) for x in inputs),'output_tokens':sum(outputs) if all(num(x) for x in outputs) else None,'known_output_tokens':sum(x for x in outputs if num(x)),'output_missing':sum(not num(x) for x in outputs),'summed_attempt_seconds':sum(r['seconds'] for r in rows),'verified_billed_cost':None}},'rows':rows,'raw_sources_sha256':sources}

def draw(result):
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
 F=R/'figures';F.mkdir(exist_ok=True)
 colors=['#32637a','#b7654b','#789851']
 fig,ax=plt.subplots(figsize=(9,4.6),layout='constrained');s=result['strict_p0'];a=result['a1_p0']
 vals=[s['complete'],a['accepted'],a['correct']];labels=['Original strict\ncomplete','A1 post-hoc\ntransport accepted','A1 post-hoc\ncorrect action'];bars=ax.bar(labels,vals,color=colors,width=.55)
 ax.bar_label(bars,labels=[f'{v}/80' for v in vals],padding=3);ax.set(ylim=(0,90),ylabel='Number of planned P0 tasks',title='P0 original policy and post-hoc sensitivity')
 fig.text(.02,-.12,'Strict technical failures are not content mistakes. A1 is post-hoc, not a replacement gate.',fontsize=9)
 for ext in ['png','svg','pdf']:fig.savefig(F/f'fig1_strict_vs_a1.{ext}',dpi=220,bbox_inches='tight')
 plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(10,4.8),sharey=True,layout='constrained');procedures=result['challenge']['procedures']
 for ax,c,title in zip(axes,['error','correct'],['Authored error: final action correct','Authored correct: initial action retained']):
  vals=[procedures[p][c]['retained_correct']/procedures[p][c]['planned'] for p in ['P1','P3','P7','P8']];bars=ax.bar(['P1','P3','P7','P8'],vals,color=['#527588','#d79145','#35866a','#876497'],width=.6)
  ax.bar_label(bars,labels=[f"{procedures[p][c]['retained_correct']}/{procedures[p][c]['planned']}" for p in ['P1','P3','P7','P8']],padding=3);ax.set(ylim=(0,1.16),title=title);ax.yaxis.set_major_formatter(PercentFormatter(1))
 axes[0].set_ylabel('Fraction of planned tasks');fig.text(.02,-.08,'Failures remain in planned denominator; non-retention can include failure. N=4 families/type.',fontsize=9)
 for ext in ['png','svg','pdf']:fig.savefig(F/f'fig2_authored_challenge.{ext}',dpi=220,bbox_inches='tight')
 plt.close(fig)

def report(d):
 p=d['challenge']['procedures'];rows=[]
 for name in ['P1','P3','P7','P8']:
  x=p[name];e=x['error'];c=x['correct'];rows.append(f"| {name} | {x['complete']}/{x['planned']} | {e['retained_correct']}/{e['planned']} | {c['not_correct']}/{c['planned']} | {e['failures']+c['failures']} |")
 c=d['challenge'];res=c['resources'];failures=[r for r in d['rows'] if r['status']!='complete'];ev=read(R/'evidence_review/SUMMARY.json')
 def u(val,known,missing):return str(val) if val is not None else f'未知（已知小计 {known}，缺失 {missing} 次）'
 fail_note='；'.join(f"{x['group_id']}/{x['procedure']}（{x['problem']}）" for x in failures) or '无'
 observed_errors=[r for r in d['rows'] if r['status']=='complete' and not r['correct']]
 interaction_note=('本批 I78 的非零值完全来自将唯一技术失败计入计划分母，不代表观察到 P8 实际给出错误行动。' if len(failures)==1 and failures[0]['procedure']=='P8' and failures[0]['error_type']=='rule' and failures[0]['draft_condition']=='error' and not observed_errors else '交互使用计划分母；须结合失败数及逐家族结果解释。')
 content=f'''# V3：新题 P0 与额外固定草稿探索\n\n## 原协议状态\n\nV3 为虚构学校制度的 `simulation_only` 开发实验。原冻结 P0 计划 {d['strict_p0']['planned']} 题，实际尝试 {d['strict_p0']['attempts']} 次；严格状态为 {d['strict_p0']['status_counts']}，完整 {d['strict_p0']['complete']} 次。原 `analysis/decision_gate.json` 保持 **technical_block / challenge_allowed=false**；严格失败计入计划分母不能解释为模型实体决定全部错误。\n\nCLI 输出包含配置诊断；原冻结规则将 error item 一律按失败处理。之后的 A1 是明确标注的**事后敏感性分析**，对精确诊断例外、事件顺序和原始回答进行核验，得到运输可接受 {d['a1_p0']['accepted']}/{d['a1_p0']['planned']}、行动正确 {d['a1_p0']['correct']}/{d['a1_p0']['planned']}。其门槛诊断为 `{d['a1_p0']['hypothetical_gate']}`，**不是原运行门槛，也不能授权原挑战**。事后例外不证明未知隐藏上下文无影响。\n\n## 额外固定草稿挑战\n\n追加挑战在原门槛技术阻断后单独冻结并执行，属于偏离原方案的 post-hoc exploratory 扩展，32 份作者预设草稿在 P0 作答前准备：8个家族×2状态×正确/错误草稿，每份由 P1/P3/P7/P8 分别复核，共 {c['planned']} 个计划任务；终态 {c['terminal']}，完成 {c['complete']}，实际尝试 {c['actual_attempts']}。原 P0 结果没有重新抽样或替换。草稿由作者预设，不能视为模型自然错误。\n\n| 程序 | 成功完成／计划 | 错误草稿最终正确／计划 | 正确草稿未保留／计划 | 失败任务 |\n|---|---:|---:|---:|---:|\n{chr(10).join(rows)}\n\n失败保留在计划分母；“未保留”同时包含失败，并非全部是观察到的主动改错。失败任务：{fail_note}。失败原因及任务保存在 `analysis/v3_report_summary.json` 的逐任务记录及原始事件中；失败任务不重抽。每类型仅4个构造家族、每个草稿条件每家族2例；各家族等权结果及交互保存在 `analysis/v3_report_summary.json`。I78（错误草稿）：{c['contrasts']['P7-P8:error']['interaction_rule_minus_material']:+.3f}；I73：{c['contrasts']['P7-P3:error']['interaction_rule_minus_material']:+.3f}。{interaction_note}这是描述性点估计，不作确认性显著性、优越性或等价主张。\n\n## 资源与 V2 依据审查\n\n额外挑战按原始事件中唯一的 turn.completed 计量，输入 {u(res['input_tokens'],res['known_input_tokens'],res['input_missing'])}、输出 {u(res['output_tokens'],res['known_output_tokens'],res['output_missing'])} tokens；包括被分类为技术失败的任务中可辨认的原始用量，是否有用量不改变其失败状态。未验证账单，金额 NA。题库编写、内部审核、调度等完整开销未知，不在上述数字内。P0资源单列于 A1 summary；并发任务时长之和不是墙钟时间。\n\n对 V2 16 组、80 条已保存回答开展后设依据审查，两个同模型家族内部评审的三项判断逐条一致 {ev['metrics']['factual_error']['exact_agreement_n']}/80；单一类别导致 κ 为 NA。该抽样并非概率样本，不能外推全部800条，不验证隐藏推理；详见 `evidence_review/SUMMARY_中文.md`。\n\n## 解释边界\n\n原冻结结果、A1事后派生及额外挑战必须分开引用。没有真人参与、外部教育行政专家或独立保留集；内部审查为 same-family / provisional。固定错误草稿的修复不能估计自然错误率、真实学校决策效果或自然净收益。\n\n图表分别为 `figures/fig1_strict_vs_a1` 和 `figures/fig2_authored_challenge`，各提供 PNG/SVG/PDF。来源哈希及图表人工审查状态见 `figures/v3_figure_manifest.json`。\n'''
 (R/'report/DEV_REPORT.md').write_text(content)

def main():
 d=load();(R/'analysis/v3_report_summary.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');draw(d);report(d)
 paths=[R/'analysis/v3_report_summary.json',R/'report/DEV_REPORT.md']+sorted((R/'figures').glob('fig[12]_*.*'))
 source=['protocol/frozen.json','analysis/decision_gate.json','analysis/p0/summary.json','audits/DIAGNOSTIC_REVIEW.json','audits/A1_DERIVATION_REVIEW.json','amendments/A1_posthoc/results/summary.json','amendments/A1_posthoc/results/threshold_diagnostic.json','evidence_review/SUMMARY.json','amendments/A1_posthoc/challenge/frozen.json','amendments/A1_posthoc/challenge/authorization.json','amendments/A1_posthoc/challenge/driver.py','prompts/challenge_items.json','keys/challenge_keys.json','analysis/create_v3_report.py']
 man={'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'posthoc exploratory; original gate remains technical_block','inputs_sha256':{x:sha(R/x) for x in source},'challenge_raw_sha256':d['raw_sources_sha256'],'outputs_sha256':{str(p.relative_to(R)):sha(p) for p in paths},'visual_review':'pending','note':'Scientific integrity review is separate.'}
 (R/'figures/v3_figure_manifest.json').write_text(json.dumps(man,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'planned':128,'complete':d['challenge']['complete'],'visual_review':'pending'}))
if __name__=='__main__':main()
