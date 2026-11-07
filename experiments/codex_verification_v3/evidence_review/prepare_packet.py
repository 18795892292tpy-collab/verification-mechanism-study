from pathlib import Path
import hashlib,json,random,datetime,socket
R=Path(__file__).resolve().parents[1];V2=R.parent/'codex_verification_v2';out=R/'evidence_review'
assert socket.gethostname()=='liekkas' and str(R)=='/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3'
sha=lambda b:hashlib.sha256(b).hexdigest()
write=lambda n,d:(out/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert not (out/'review_freeze.json').exists()
protocol={'version':'v3-v2-evidence-audit-1','prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evaluation':'exploratory same-family semantic assessment; not a replacement for original action accuracy','scope':'80 saved V2 responses from16 paired item/repeat groups; 2 groups per8 family, all5 procedures. No new subject answer.','sampling_rule':'families sorted; for index i choose aligned state[i%5] and flawed state[(i+2)%5], states=[base,decisive_change,irrelevant,paraphrase,missing]; repeat=1+int(SHA256(item_id+fixed_seed),16)%2. All5 procedures retained. Anonymous case/answer order fixed pseudorandom seed2026110703.','sample_seed':'v3-evidence-20261107','reviewers':2,'blinding':'Hide procedure/family/state/advice labels, true key, aggregate result, original IDs; show original public dossier and exact parsed final. Public text can reveal experimental properties. Same model family cannot certify external validity.','rubric':{'factual_error':['yes','no','uncertain'],'decisive_support':['adequate','partial','unsupported','uncertain'],'citation_support':['supported','partly_supported','unsupported','no_citations','uncertain']},'definitions':{'factual_error':'yes only for explicit factual assertion contradicted by dossier, not mere omitted detail; no means no identified explicit contradiction in inspected text, not certified full reasoning.','decisive_support':'adequate if visible brief reason identifies decisive fact and applicable rule sufficiently to justify chosen action; partial if compatible but omits necessary connecting condition; unsupported if given reason cannot justify action or relies on contradicted/unprovided decisive premise. Respect short-answer format; do not require exhaustive elimination or hidden thought.','citation_support':'supported if cited sources jointly support visible decisive rationale; partly_supported if only part is substantiated or added citations have no discernible role; unsupported if no cited source supports key reason. Check IDs against original dossier; quotation text must be accurate.'},'required_row_fields':['response_id','factual_error','decisive_support','citation_support','answer_quote','source_ids','evidence_note'],'analysis':'Report both raters separately and exact agreement; unresolved disagreements retained, no executor override. No hypothesis test or superiority claim; unit family, sample exploratory. New rubric is retrospective to V2, fixed before these semantic ratings. Reviewer work/usage separate from subject calls.'}
write('protocol.json',protocol)
items=json.loads((V2/'prompts/dev_items.json').read_text());byid={x['item_id']:x for x in items};families=sorted({x['family_id'] for x in items});states=['base','decisive_change','irrelevant','paraphrase','missing'];selected=[]
for i,fam in enumerate(families):
 for adv,offset in [('aligned',0),('flawed',2)]:
  item=next(x for x in items if x['family_id']==fam and x['state']==states[(i+offset)%5] and x['advice']==adv)
  rep=1+int(sha((item['item_id']+protocol['sample_seed']).encode()),16)%2;selected.append((item,rep))
random.Random(2026110703).shuffle(selected)
packet=[];mapping=[];sources={}
for n,(item,rep) in enumerate(selected,1):
 group=item['item_id']+'_r'+str(rep);responses=[];procs=['P0','P1','P3','P7','P8'];random.Random(2026110703+n).shuffle(procs)
 for j,proc in enumerate(procs,1):
  rel=f'runs/dev/{group}/{proc}/record.json';raw=(V2/rel).read_bytes();rec=json.loads(raw);rid=f'C{n:02d}A{j}'
  responses.append({'response_id':rid,'answer':rec['parsed']});mapping.append({'response_id':rid,'item_id':item['item_id'],'group_id':group,'family_id':item['family_id'],'state':item['state'],'advice':item['advice'],'repeat':rep,'procedure':proc,'record_path':str(V2/rel),'record_sha256':sha(raw)});sources[rel]=sha(raw)
 packet.append({'case_id':f'C{n:02d}','public_text':item['public_text'],'responses':responses})
write('blind_packet.json',packet);write('private_mapping.json',mapping)
freeze={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(V2),'source_frozen_sha256':sha((V2/'protocol/frozen.json').read_bytes()),'sampled_responses':len(mapping),'groups':len(packet),'sha256':{n:sha((out/n).read_bytes()) for n in ['prepare_packet.py','protocol.json','blind_packet.json','private_mapping.json']},'source_record_sha256':sources}
write('review_freeze.json',freeze)
print(json.dumps({'responses':len(mapping),'groups':len(packet),'review_freeze_sha256':sha((out/'review_freeze.json').read_bytes())}))
