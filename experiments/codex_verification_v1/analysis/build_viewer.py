from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]
s=json.loads((R/'analysis/dev/summary.json').read_text())
assert s['complete_tasks']==200 and s['passed_integrity']
items=json.loads((R/'prompts/dev_items.json').read_text())
keys={x['item_id']:x for x in json.loads((R/'keys/dev_keys.json').read_text())}
data=[]
for i in items:
 records={p:json.loads((R/'runs/dev'/(i['item_id']+'_r1')/p/'record.json').read_text()) for p in ['P0','P1','P3','P7','P8']}
 data.append({'id':i['item_id'],'family':i['family_id'],'state':i['state'],'advice':i['advice'],'text':i['public_text'],
 'key':keys[i['item_id']]['correct_action'],'records':{p:{'status':r['status'],'answer':r['parsed'],'first_hash':r['first_sha256'],'session':r['attempts'][-1]['thread_ids']} for p,r in records.items()}})
payload=json.dumps(data,ensure_ascii=False).replace('</','<\\/')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Codex 核验实验 · 原始作答回放</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f2ed;color:#202a34;font:16px/1.65 system-ui,sans-serif}header{padding:28px 5vw;background:#142d3b;color:white}h1{margin:0;font-size:26px}header p{margin:8px 0 0;color:#c8d9df}main{padding:24px 5vw;max-width:1600px;margin:auto}select{padding:10px;max-width:100%;font:inherit;border:1px solid #b7c6ce;border-radius:7px;background:white}.grid{display:grid;grid-template-columns:minmax(300px,1fr) minmax(400px,1.25fr);gap:22px;margin-top:22px}.paper,.response{background:white;border:1px solid #dce1e1;border-radius:10px;padding:22px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;margin:0}.responses{display:grid;gap:12px}.response h2{font-size:18px;margin:0 0 8px}.meta{font-size:12px;color:#62717c;overflow-wrap:anywhere}.badge{padding:3px 8px;background:#e3f3e9;color:#146145;border-radius:5px}.warning{padding:12px 16px;background:#fff3ce;border-left:4px solid #b58316;margin:16px 0}.result{font-weight:650}a{color:#32679c}@media(max-width:850px){.grid{grid-template-columns:1fr}.paper,.response{padding:16px}main{padding:18px}header{padding:22px}}
</style><header><h1>来源与条款核验 · 开发实验回放</h1><p>4 个合成案例家族 · 40 道题 · 200 次真实 Codex 作答 · 同一首轮，四种独立复核</p></header><main>
<div class="warning">这里展示合成规则任务的模型回答，没有真人参与。选择案例可核对原始材料、规则答案和每个程序的输出。修复率为 NA 时，表示没有可修复的自然首轮错误。</div>
<label>选择题目 <select id="case"></select></label><span id="key" style="margin-left:15px"></span>
<div class="grid"><article class="paper"><h2 style="margin-top:0">公开档案</h2><pre id="dossier"></pre></article><section class="responses" id="responses"></section></div>
<p class="meta">模型配置：gpt-6-astra / ultra（请求配置）；CLI 0.166.0；底层权重快照未知。此文件包含固定结果，可离线查看，不会再次调用模型。</p></main>
<script id="data" type="application/json">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent);const menu=document.getElementById('case');
const names={P0:'基础决定',P1:'自由复核',P3:'来源核验',P7:'条款条件核验',P8:'等长通用复核'};
for(const [n,x] of data.entries()){const o=document.createElement('option');o.value=n;o.textContent=x.id;menu.append(o)}
function show(){const x=data[Number(menu.value)];document.getElementById('dossier').textContent=x.text;document.getElementById('key').textContent='规则答案：'+x.key;const host=document.getElementById('responses');host.replaceChildren();
for(const [p,r] of Object.entries(x.records)){const card=document.createElement('article');card.className='response';const h=document.createElement('h2');h.textContent=p+' · '+names[p];card.append(h);const a=document.createElement('p');a.className='result';a.textContent='选择 '+r.answer.action+' · '+(r.answer.action===x.key?'符合规则答案':'不符合规则答案')+' · 自报信心 '+r.answer.confidence+'/5';card.append(a);const b=document.createElement('p');b.textContent=r.answer.brief_justification;card.append(b);const c=document.createElement('p');c.textContent='引用：'+r.answer.cited_sources.join('、');card.append(c);const m=document.createElement('p');m.className='meta';m.textContent='状态：'+r.status+' | 会话：'+r.session.join(', ')+(r.first_hash?' | 共享首轮SHA256：'+r.first_hash:'');card.append(m);host.append(card)}}
menu.addEventListener('change',show);show();</script></html>'''.replace('PAYLOAD',payload)
(R/'viewer.html').write_text(page)
print(json.dumps({'viewer':str(R/'viewer.html'),'items':len(data),'responses':sum(len(x['records']) for x in data)},ensure_ascii=False))
