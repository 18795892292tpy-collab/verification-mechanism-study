#!/usr/bin/env python3
"""Reproducible post-hoc summary of two independently authored blinded reviews."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib,json,random,re,socket
R=Path(__file__).resolve().parents[1]; E=R/'evidence_review'; V=R.parent/'codex_verification_v2'
assert socket.gethostname()=='liekkas' and str(R)=='/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3'
read=lambda p:json.loads(p.read_text()); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=read(E/'protocol.json');f=read(E/'review_freeze.json');mapping=read(E/'private_mapping.json');packet=read(E/'blind_packet.json')
assert Path(f['source_root'])==V and sha(V/'protocol/frozen.json')==f['source_frozen_sha256']
for name,digest in f['sha256'].items():assert sha(E/name)==digest,name
for name,digest in f['source_record_sha256'].items():assert sha(V/name)==digest,name
byid={r['response_id']:(case,r['answer']) for case in packet for r in case['responses']}
assert len(byid)==80==len(mapping)==f['sampled_responses'] and len(packet)==16==f['groups']
assert len({m['response_id'] for m in mapping})==80 and set(byid)=={m['response_id'] for m in mapping}
items={x['item_id']:x for x in read(V/'prompts/dev_items.json')}
assert len({m['group_id'] for m in mapping})==16 and len({m['family_id'] for m in mapping})==8
families=sorted({m['family_id'] for m in mapping});states=['base','decisive_change','irrelevant','paraphrase','missing']
for i,fam in enumerate(families):
 subset=[m for m in mapping if m['family_id']==fam]
 assert len(subset)==10 and len({m['group_id'] for m in subset})==2
 assert {(m['advice'],m['state']) for m in subset}=={('aligned',states[i%5]),('flawed',states[(i+2)%5])}
for m in mapping:
 case,answer=byid[m['response_id']]; source=Path(m['record_path'])
 assert source==V/'runs/dev'/m['group_id']/m['procedure']/'record.json' and sha(source)==m['record_sha256']
 rec=read(source); item=items[m['item_id']]; assert rec['parsed']==answer and item['public_text']==case['public_text']
 assert all(item[k]==m[k] for k in ['family_id','state','advice'])
 assert m['repeat']==1+int(hashlib.sha256((m['item_id']+p['sample_seed']).encode()).hexdigest(),16)%2
 assert m['group_id']==m['item_id']+'_r'+str(m['repeat'])
for gid in {m['group_id'] for m in mapping}:
 assert {m['procedure'] for m in mapping if m['group_id']==gid}=={'P0','P1','P3','P7','P8'}
expected=[]
for i,fam in enumerate(families):
 for adv,offset in [('aligned',0),('flawed',2)]:
  matches=[x for x in items.values() if x['family_id']==fam and x['state']==states[(i+offset)%5] and x['advice']==adv]
  assert len(matches)==1;item=matches[0];rep=1+int(hashlib.sha256((item['item_id']+p['sample_seed']).encode()).hexdigest(),16)%2
  expected.append(item['item_id']+'_r'+str(rep))
random.Random(2026110703).shuffle(expected)
for n,case in enumerate(packet,1):
 assert case['case_id']==f'C{n:02d}'
 entries=[next(m for m in mapping if m['response_id']==x['response_id']) for x in case['responses']]
 assert {m['group_id'] for m in entries}=={expected[n-1]}
 ordered=['P0','P1','P3','P7','P8'];random.Random(2026110703+n).shuffle(ordered)
 assert [m['procedure'] for m in entries]==ordered
 assert [x['response_id'] for x in case['responses']]==[f'C{n:02d}A{j}' for j in range(1,6)]
ratings={}; citation_note_flags=[]
for label in ['A','B']:
 data=read(E/f'ratings_{label}.json'); assert data['reviewer_class']=='same-family/provisional' and data['protocol_version']==p['version']
 assert datetime.fromisoformat(data['reviewed_utc'])>=datetime.fromisoformat(f['frozen_utc'])
 rows=data['ratings']; assert len(rows)==80 and len({r['response_id'] for r in rows})==80
 ratings[label]={r['response_id']:r for r in rows};assert set(ratings[label])==set(byid)
 for row in rows:
  case,answer=byid[row['response_id']]; assert all(k in row for k in p['required_row_fields'])
  for k,allowed in p['rubric'].items():assert row[k] in allowed,(label,row['response_id'],k)
  assert row['answer_quote'] and row['answer_quote'] in answer['brief_justification']
  assert row['evidence_note'].strip()
  sourceids=set(re.findall(r'\[(S\d+)\]',case['public_text']))
  assert isinstance(row['source_ids'],list) and set(row['source_ids'])<=sourceids
  for fragment in re.findall('“([^”]+)”',row['evidence_note']):
   if fragment not in case['public_text'] and fragment not in answer['brief_justification']:
    citation_note_flags.append({'reviewer':label,'response_id':row['response_id'],'fragment':fragment,'explanation':'文字非连续原文；若含省略号按概述而非逐字引文理解，未自动改写原始评审。'})
metrics={}; disagreements=[]
for field,categories in p['rubric'].items():
 count={label:dict(Counter(row[field] for row in data.values())) for label,data in ratings.items()}
 same=sum(ratings['A'][rid][field]==ratings['B'][rid][field] for rid in byid)
 pe=sum(count['A'].get(c,0)*count['B'].get(c,0) for c in categories)/(80*80)
 kappa=(same/80-pe)/(1-pe) if pe<1 else None
 metrics[field]={'reviewer_counts':count,'exact_agreement_n':same,'exact_agreement_denominator':80,'exact_agreement_rate':same/80,'cohen_kappa':kappa,'kappa_note':'NA: both reviewers used a single category on all items' if kappa is None else 'Descriptive only; observations clustered by family/group.'}
 for rid in byid:
  if ratings['A'][rid][field]!=ratings['B'][rid][field]:disagreements.append({'response_id':rid,'field':field,'A':ratings['A'][rid][field],'B':ratings['B'][rid][field]})
result={'created_utc':datetime.now(timezone.utc).isoformat(),'evaluation_type':'post-hoc exploratory semantic review','review_independence':'same-family/provisional','actual_backend_identity':'not independently attested','target_host':socket.gethostname(),'v2_canonical_root':str(V),'v3_root':str(R),'sampling':{'sampled_responses':80,'sampled_groups':16,'families':8,'per_procedure':dict(Counter(m['procedure'] for m in mapping)),'group_state':dict(Counter(m['state'] for m in mapping if m['procedure']=='P0')),'group_advice':dict(Counter(m['advice'] for m in mapping if m['procedure']=='P0')),'source_population':800,'sample_is_probability_sample':False},'validation':{'frozen_packet_hashes':'PASS','v2_frozen_hash':'PASS','80_source_record_hashes':'PASS','packet_to_source_text_and_answer':'PASS','sampling_and_pairing':'PASS','rater_id_and_enum_coverage':'PASS','all_answer_quotes_substrings':'PASS','all_source_ids_exist_in_dossier':'PASS','rating_after_review_freeze':'PASS','rater_evidence_notes_nonempty':'PASS','semantic_claims_independently_verified_by_aggregator':False},'metrics':metrics,'disagreements':disagreements,'nonverbatim_quoted_fragments':citation_note_flags,'limitations':['This is 80 selected answers, not an audit of all800 answers.','Post-hoc rubric and small nonrandom within-family sample; no inference of prevalence, program superiority, equivalence, or human performance.','Reviewers are internal same-family agents; actual model backend is not independently attested; no external educational expert.','Review labels assess only visible brief text and cited dossier, not hidden model reasoning; self-reports of prior reasoning are not independently validated.','All single-category ratings make chance-adjusted kappa mathematically undefined, not perfect reliability.','Automatic checks establish quote/source existence, not semantic correctness; no independent adjudication of unanimous labels.'],'input_sha256':{n:sha(E/n) for n in ['protocol.json','review_freeze.json','private_mapping.json','blind_packet.json','ratings_A.json','ratings_B.json','summarize_ratings.py']}}
(E/'SUMMARY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
md=f'''# V2 既有回答依据质量审查（V3 事后探索）\n\n审核对象是 V2 的 16 组题目及重复，每组五程序，共 80 条已保存回答；覆盖8个家族、每程序16条。抽样是事先固定的分层便利抽样，非随机概率样本。评审前冻结题目包和量表；本分析发生在 V2 实验之后，不改变原 V2 的行动正确率，也不评估全部800条。没有重新调用被试模型。\n\n两名内部评审均判断：80/80 条未发现明确事实矛盾，80/80 条可见决定依据充分，80/80 条引用支持可见核心理由。三项逐条一致均为80/80；两位评审在每项都只使用了一个类别，Cohen κ 分母为零，记 NA，不能解释成经过机会校正的完美可靠性。不存在标签分歧。\n\n复核脚本核验了冻结包、原V2冻结哈希及80条源记录哈希、公开档案和回答的逐字绑定、抽样规则、评级ID和枚举、答案引文为原文子串、所列来源编号存在，以及评级时间晚于审核冻结。自动检查只核对这些形式条件，不能单独证明每条语义判定正确。\n\n共有 {len(citation_note_flags)} 个证据说明中的引号片段不连续出现在原文；原评审 A 的 C05A1 使用省略号（“U3…计数页未归档”），应理解为概述，不是逐字引文，原记录保留不改。\n\n审查者为同模型家族内部代理，后端具体模型身份无法独立核验；并非独立教育领域专家。短理由有长度限制，审核仅针对可见文字及引用，不证明模型隐藏推理、回答生成过程或真实学校决策。16组是家族聚类样本，本结果不能推断全部800条的质量比例，也不能证明复核程序更好或等价。\n\n完整统计、三项定义、样本分布、输入SHA-256和逐条分歧见 [SUMMARY.json](SUMMARY.json)；两位原始评分保留在 ratings_A.json 和 ratings_B.json。可在原主机运行 `python evidence_review/summarize_ratings.py` 复算（会覆盖本汇总文件，不会修改冻结输入和原始评分）。\n'''
(E/'SUMMARY_中文.md').write_text(md)
print(json.dumps({'records':80,'groups':16,'agreement':{k:v['exact_agreement_n'] for k,v in metrics.items()},'disagreements':len(disagreements),'quote_flags':len(citation_note_flags)},ensure_ascii=False))
