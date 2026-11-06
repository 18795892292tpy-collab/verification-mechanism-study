#!/usr/bin/env python3
"""Deterministic full-plan scoring. No LLM judges, no synthesized responses."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,hashlib,json
import runner
R=runner.R

def entries(p):
 v=runner.read(p)
 if isinstance(v,list): return {x['item_id']:x for x in v}
 if 'items' in v:return {x['item_id']:x for x in v['items']}
 return v

def run(phase):
 frozen=runner.verify();fhash=runner.file_sha(R/'protocol/frozen.json')
 keys=entries(R/f'keys/{phase}_keys.json');items=entries(R/f'prompts/{phase}_items.json')
 rows=[];audit={'frozen_hash':fhash,'phase':phase,'record_errors':[],'unusual_item_types':[],'duplicate_session_ids':[]}
 sessions=[];real_attempts=[]
 for job in frozen['phase_schedule'][phase]['jobs']:
  rp=R/'runs'/phase/job['group_id']/job['procedure']/'record.json'
  rec=runner.read(rp) if rp.exists() else {'status':'not_executed','parsed':None,'attempts':[]}
  if rp.exists() and rec.get('attempts'):
   first_text=None
   if job['procedure']!='P0':
    first_job={**job,'procedure':'P0'}
    first=runner.validate_record(phase,first_job,items[job['item_id']],None,fhash)
    first_text=first['raw_final']
   rec=runner.validate_record(phase,job,items[job['item_id']],first_text,fhash)
  if rp.exists():
   for k in ['group_id','item_id','repeat','procedure']:
    if rec.get(k)!=job[k]:audit['record_errors'].append(f'{rp}:{k}')
   if rec.get('frozen_hash')!=fhash:audit['record_errors'].append(f'{rp}:frozen_hash')
   pp=rp.parent/'prompt.txt'
   if pp.exists() and rec.get('prompt_sha256')!=runner.file_sha(pp):audit['record_errors'].append(f'{rp}:prompt_sha256')
   if job['procedure']!='P0' and rec.get('raw_final') is not None:
    first=runner.read(rp.parent.parent/'P0/record.json')
    if rec.get('first_sha256')!=runner.sha(first['raw_final']):audit['record_errors'].append(f'{rp}:first_sha256')
   for a in rec['attempts']:
    ad=rp.parent/f"attempt_{a['attempt']:02d}"
    if runner.file_sha(ad/'events.jsonl')!=a['stdout_sha256']:audit['record_errors'].append(f'{ad}:events_hash')
    if a.get('output_sha256') and runner.file_sha(ad/'response.json')!=a['output_sha256']:audit['record_errors'].append(f'{ad}:output_hash')
    real_attempts.append(a);sessions+=a.get('thread_ids',[]);audit['unusual_item_types']+=a.get('unexpected_items',[])
  key=keys[job['item_id']]
  correct_action=key.get('correct_action',key.get('action',key.get('key_action')))
  if correct_action not in ['A','B','C','D']:raise ValueError('Key has no valid action: '+str(key))
  parsed=rec.get('parsed') or {};status=rec['status']
  # Non-complete rows are planned unsuccessful decisions; keep every denominator.
  correct=int(status=='complete' and parsed.get('action')==correct_action)
  meta=items[job['item_id']]
  pause_action=key.get('pause_action',key.get('escalate_option'))
  rows.append({**job,'family_id':meta['family_id'],'state':meta['state'],'advice':meta['advice'],
   'error_type':key.get('error_type',key.get('category','unknown')),'status':status,'correct_action':correct_action,
   'action':parsed.get('action',''),'correct':correct,'parse_ok':int(bool(parsed)),
   'pause_action':pause_action or '', 'first_sha256':rec.get('first_sha256') or '',
   'attempts':len(rec['attempts']),'seconds':sum(x.get('seconds',0) for x in rec['attempts']),
   'input_tokens':sum((x.get('usage') or {}).get('input_tokens',0) for x in rec['attempts']) if all(x.get('usage') is not None for x in rec['attempts']) and rec['attempts'] else '',
   'output_tokens':sum((x.get('usage') or {}).get('output_tokens',0) for x in rec['attempts']) if all(x.get('usage') is not None for x in rec['attempts']) and rec['attempts'] else ''})
 audit['duplicate_session_ids']=[k for k,v in Counter(sessions).items() if v>1]
 bygroup=defaultdict(dict)
 for r in rows:bygroup[r['group_id']][r['procedure']]=r
 summaries={}
 for p in runner.PROCS:
  rr=[r for r in rows if r['procedure']==p]; present=[r for r in rr if r['state']!='missing'];flawed=[r for r in present if r['advice']=='flawed']
  missing=[r for r in rr if r['state']=='missing'];wrong=[g for g in bygroup.values() if g['P0']['correct']==0 and g['P0']['status']=='complete' and g['P0']['state']!='missing']
  right=[g for g in bygroup.values() if g['P0']['correct']==1 and g['P0']['state']!='missing']
  repair=sum(g[p]['correct'] for g in wrong);damage=sum(1-g[p]['correct'] for g in right)
  summaries[p]={'planned':len(rr),'complete':sum(r['status']=='complete' for r in rr),'correct':sum(r['correct'] for r in rr),
    'accuracy':sum(r['correct'] for r in rr)/len(rr),'present_flawed_correct':sum(r['correct'] for r in flawed),'present_flawed_n':len(flawed),
    'missing_correct':sum(r['correct'] for r in missing),'missing_n':len(missing),
    'natural_first_errors':len(wrong),'families_with_first_errors':sorted({g['P0']['family_id'] for g in wrong}),
    'repaired':repair if p!='P0' else None,'repair_rate':repair/len(wrong) if wrong and p!='P0' else None,
    'first_correct_present':len(right),'damaged':damage if p!='P0' else None,'damage_rate':damage/len(right) if right and p!='P0' else None,
    'input_tokens':sum(r['input_tokens'] for r in rr if isinstance(r['input_tokens'],int)),
    'output_tokens':sum(r['output_tokens'] for r in rr if isinstance(r['output_tokens'],int)),
    'usage_known_tasks':sum(isinstance(r['input_tokens'],int) for r in rr),'seconds':sum(r['seconds'] for r in rr)}
 family=[]
 for fid in sorted({r['family_id'] for r in rows}):
  for p in runner.PROCS:
   rr=[r for r in rows if r['family_id']==fid and r['procedure']==p]
   fp=[r for r in rr if r['state']!='missing' and r['advice']=='flawed']
   family.append({'family_id':fid,'procedure':p,'planned':len(rr),'complete':sum(r['status']=='complete' for r in rr),'correct':sum(r['correct'] for r in rr),
    'present_flawed_n':len(fp),'present_flawed_correct':sum(r['correct'] for r in fp)})
 summary={'phase':phase,'planned_tasks':len(rows),'planned_groups':len(bygroup),'actual_cli_attempts':len(real_attempts),
   'complete_tasks':sum(r['status']=='complete' for r in rows),'status_counts':dict(Counter(r['status'] for r in rows)),
   'complete_groups':sum(all(r['status']=='complete' for r in g.values()) for g in bygroup.values()),
   'unique_sessions':len(set(sessions)),'usage_missing_attempts':sum(a.get('usage') is None for a in real_attempts),
   'sum_input_tokens':sum((a.get('usage') or {}).get('input_tokens',0) for a in real_attempts),
   'sum_output_tokens':sum((a.get('usage') or {}).get('output_tokens',0) for a in real_attempts),
   'procedures':summaries,'family_results':family,'inference':'Descriptive development experiment; no human respondents or confirmatory superiority claims.',
   'passed_integrity':not any(audit[k] for k in ['record_errors','unusual_item_types','duplicate_session_ids'])}
 out=R/'analysis'/phase;out.mkdir(parents=True,exist_ok=True)
 for name,data in [('scored_runs.csv',rows),('family_results.csv',family)]:
  with (out/name).open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 runner.dump(out/'summary.json',summary);runner.dump(out/'integrity_audit.json',audit)
 print(json.dumps({k:v for k,v in summary.items() if k not in ['procedures','family_results']},ensure_ascii=False))
 if not summary['passed_integrity']:raise RuntimeError('Integrity audit failed')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['toy','dev']);run(ap.parse_args().phase)
