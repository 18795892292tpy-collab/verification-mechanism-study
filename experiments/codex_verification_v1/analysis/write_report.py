"""Report only after full evaluation; no fabricated placeholder results."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import csv,json,hashlib
R=Path(__file__).resolve().parents[1]
s=json.loads((R/'analysis/dev/summary.json').read_text())
t=json.loads((R/'analysis/toy/summary.json').read_text())
assert s['planned_tasks']==200 and s['complete_tasks']==200 and s['passed_integrity']
rows=list(csv.DictReader((R/'analysis/dev/scored_runs.csv').open()))
first=[r for r in rows if r['procedure']=='P0']
wrong=[r for r in first if r['state']!='missing' and r['correct']=='0']
rule_flawed_wrong=[r for r in wrong if r['error_type']=='rule' and r['advice']=='flawed']
rule_error_families=sorted({r['family_id'] for r in rule_flawed_wrong})
gate={'evaluated_utc':datetime.now(timezone.utc).isoformat(),'present_P0_errors':len(wrong),
 'rule_families_with_present_flawed_P0_errors':rule_error_families,
 'criteria':'At least two rule families with present/flawed P0 errors and at least four present P0 errors; no unresolved ambiguity or contamination. No review contrast enters gate.',
 'eligible_to_expand':len(rule_error_families)>=2 and len(wrong)>=4,'based_on_P0_only':True,
 'decision':'EXPANSION_ELIGIBLE' if len(rule_error_families)>=2 and len(wrong)>=4 else 'STOP_DEVELOPMENT_EXPANSION',
 'note':'A resource allocation rule, not a statistical proof or a superiority decision.'}
(R/'audits/development_gate.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n')
metas=[]
for phase in ['toy','dev']:
 metas.extend(json.loads(p.read_text()) for p in (R/'runs'/phase).glob('*/*/attempt_*/meta.json'))
times=[(datetime.fromisoformat(m['started_utc']),datetime.fromisoformat(m['finished_utc'])) for m in metas]
wall=(max(y for x,y in times)-min(x for x,y in times)).total_seconds()
byproc=s['procedures']
def pct(x,n):return f'{x}/{n}（{100*x/n:.1f}%）' if n else 'NA（分母为0）'
parts=['# Codex 来源与条款核验：首批开发实验报告','',
 '研究条件：同机 Codex CLI 0.166.0，显式请求 gpt-6-astra / ultra；每次新临时会话。合成规则任务，非真人研究。',
 '','## 原目标','',
 '检验增加条款触发条件核验（P7），相较原来源核验（P3）与等长通用复核（P8），是否改善错误建议下的决定。首先检验运行可靠性和任务是否有足够自然错误。',
 '','## 方法','',
 '4个新开发家族（材料适用2个、条款条件2个）；每族5状态×2建议，合计40题。每题生成一次P0，再由P1/P3/P7/P8各自在新会话中复核同一个首轮文本。每题1次重复，共200个开发任务；另有10个toy校准任务。没有保留集实验。',
 '','P7与P8新增指令正文（不含分隔换行）分别为43、44字符，相差2.3%；含分隔换行分别为44、45字符。不据此声称隐藏推理计算量相同。正确率只按action选项是否符合固定规则答案评分，不代表理由或引用质量得分；失败按全计划分母保留。本批仅2个条款家族，不进行人群推广的显著性或等价结论。',
 '','准备阶段：193项案例规则/结构检查、42题同模型内部盲审与答案键一致；32项离线工具链测试通过。独立人类专家尚未验证题库。旧DeepSeek数据未修改、未续跑、未混合。',
 '','## 结果','',
 f"开发任务完成{s['complete_tasks']}/200，校准完成{t['complete_tasks']}/10；开发独立会话{s['unique_sessions']}个，原始日志审计通过。",'',
 '| 程序 | 全部题目正确 | 证据在场且建议错误时正确 | 证据缺失时正确 | 修复自然首轮错误 | 将正确首轮改错 |',
 '|---|---:|---:|---:|---:|---:|']
for p,v in byproc.items():
 repair='—' if p=='P0' else pct(v['repaired'],v['natural_first_errors'])
 damage='—' if p=='P0' else pct(v['damaged'],v['first_correct_present'])
 parts.append(f"| {p} | {pct(v['correct'],v['planned'])} | {pct(v['present_flawed_correct'],v['present_flawed_n'])} | {pct(v['missing_correct'],v['missing_n'])} | {repair} | {damage} |")
parts+=['','### 家族层面的主要对比（描述性）','','| 家族 | P7−P3 | P7−P8 |','|---|---:|---:|']
family={}
for r in s['family_results']:family[(r['family_id'],r['procedure'])]=r
for fid in sorted({r['family_id'] for r in rows if r['error_type']=='rule'}):
 rates={p:family[(fid,p)]['present_flawed_correct']/family[(fid,p)]['present_flawed_n'] for p in ['P3','P7','P8']}
 parts.append(f"| {fid} | {100*(rates['P7']-rates['P3']):+.1f} 个百分点 | {100*(rates['P7']-rates['P8']):+.1f} 个百分点 |")
parts+=['','### 实际资源记录','','| 程序 | 本次调用输入token | 本次调用输出token | 完成任务 |','|---|---:|---:|---:|']
for p,v in byproc.items():parts.append(f"| {p} | {v['input_tokens']:,} | {v['output_tokens']:,} | {v['complete']} |")
parts += ['',f"开发输入合计{s['sum_input_tokens']:,}、输出{s['sum_output_tokens']:,}；校准另计输入{t['sum_input_tokens']:,}、输出{t['sum_output_tokens']:,}。首轮P0只计一次，复核行仅计自己的调用，不重复分摊首轮。",'',
 f'从第一项校准开始到最后一个开发任务完成的墙钟跨度约{wall/60:.1f}分钟，包含两阶段之间的审计和调度间隔。token是客户端返回的资源记录，不等于精确算力或现金费用。隐藏模型权重快照与采样seed不可见。',
 '', '上述token合计仅统计被试式作答与复核任务。案例起草、内部盲审、工具开发、协调和图表审查属于管理开销，其完整token计量不可得，未包含在合计中；不能据此声称这是整个研究的全部资源消耗。',
 '','## 解释','']
if not wrong:
 parts+=['本批所有证据在场的首轮答案均正确，没有可供复核修复的自然首轮错误。因此修复率不可估计（NA），不能填写为0%，也不能据此断言核验无效。',
 '','主对比反映该开发题库上的观测差异；不支持“P7具有优势”或“方法等价”。样本只有4个题库家族，全部题目具有明确合成规则，同一模型也参与了内部审查，外部教育效度未验证。']
else:parts += [f'观察到{len(wrong)}个证据在场的自然首轮错误，分布于{len({r["family_id"] for r in wrong})}个家族。修复、改错和差异仅作开发期描述，不支持确认性结论。']
parts+=['','## 下一步','',
 ('按结果产生前固定的P0门槛，停止扩大这一开发矩阵，不启动候选2,400任务保留集。可以另立新版本做更复杂但答案明确的开发题，或单独设计固定错误草稿挑战；不能将人工植入错误与本批自然决定混合。' if not gate['eligible_to_expand'] else 'P0预设扩展门槛达到；可进入尚未执行的6家族×2重复开发扩展。扩展不依据P7是否领先，必须先准备新增家族和记录变更。'),
 '','## 主张—证据表','','| 主张 | 本批证据 | 可支持范围 |','|---|---|---|',
 '| 工具链能维持共享首轮与独立复核 | 原始prompt、首轮哈希、会话、事件与输出逐项审计 | 本批运行完整性 |',
 f"| P0在当前开发题上的正确性 | {byproc['P0']['correct']}/40 | 4个合成家族的描述性表现 |",
 '| 条款条件核验有独特优势 | 见家族对比；未开展独立保留集 | 不作确认性结论 |',
 '| 真人管理者工作负担改善 | 无真人样本与测量 | 本研究不能回答 |',
 '','图表与技能来源见 FIGURE_PROVENANCE.md。所有输出可由保存的原始模型记录重新评分生成。','']
(R/'report/DEV_REPORT.md').write_text('\n'.join(parts))
print(json.dumps({'report':str(R/'report/DEV_REPORT.md'),'gate':gate,'wall_minutes':wall/60},ensure_ascii=False))
