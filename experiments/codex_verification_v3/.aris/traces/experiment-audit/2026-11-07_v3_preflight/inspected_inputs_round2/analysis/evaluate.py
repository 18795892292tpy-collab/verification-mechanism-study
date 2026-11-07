#!/usr/bin/env python3
"""V3 scoring and frozen diagnostic gate. No model calls; no P0 reuse for challenge."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'harness'))
import runner
R=runner.R

def entries(path):
    value = runner.read(path)
    if isinstance(value, list):
        return {x['item_id']: x for x in value}
    if 'items' in value:
        return {x['item_id']: x for x in value['items']}
    return value


def rate(n, d):
    return n / d if d else None


def mean(values):
    return sum(values) / len(values) if values else None


def valid_token_count(value):
    return type(value) is int and value >= 0


def usage_value(attempt, field):
    usage = attempt.get('usage')
    value = usage.get(field) if isinstance(usage, dict) else None
    return value if valid_token_count(value) else None


def usage_totals(attempts):
    inputs = [usage_value(a, 'input_tokens') for a in attempts]
    outputs = [usage_value(a, 'output_tokens') for a in attempts]
    input_missing = sum(v is None for v in inputs)
    output_missing = sum(v is None for v in outputs)
    known_input = sum(v for v in inputs if v is not None)
    known_output = sum(v for v in outputs if v is not None)
    return {'sum_input_tokens': None if input_missing else known_input,
            'sum_output_tokens': None if output_missing else known_output,
            'known_input_tokens': known_input, 'known_output_tokens': known_output,
            'input_usage_missing_attempts': input_missing, 'output_usage_missing_attempts': output_missing,
            'usage_missing_attempts': sum(i is None or o is None for i, o in zip(inputs, outputs))}


def row_usage_totals(rows):
    # Actual scored rows carry missing-attempt counts and known subtotals, so a
    # partially observed retry cannot disappear inside a row with unknown total.
    inputs = sum(r.get('input_usage_missing_attempts', int(not valid_token_count(r['input_tokens']))) for r in rows)
    outputs = sum(r.get('output_usage_missing_attempts', int(not valid_token_count(r['output_tokens']))) for r in rows)
    known_input = sum(r.get('known_input_tokens', r['input_tokens'] if valid_token_count(r['input_tokens']) else 0) for r in rows)
    known_output = sum(r.get('known_output_tokens', r['output_tokens'] if valid_token_count(r['output_tokens']) else 0) for r in rows)
    return {'sum_input_tokens': None if inputs else known_input, 'sum_output_tokens': None if outputs else known_output,
            'known_input_tokens': known_input, 'known_output_tokens': known_output,
            'input_usage_missing_attempts': inputs, 'output_usage_missing_attempts': outputs,
            'usage_missing_attempts': sum(r.get('usage_missing_attempts', int(not valid_token_count(r['input_tokens']) or not valid_token_count(r['output_tokens']))) for r in rows),
            'usage_known_tasks': sum(valid_token_count(r['input_tokens']) and valid_token_count(r['output_tokens']) for r in rows)}


def inventory_runs(frozen):
    """Account for the entire run tree before reading any planned result.

    Unknown phases/groups/procedures, extra attempts, extra raw files and
    symlinks all fail closed. Counts include unplanned artifacts as evidence.
    """
    base = R / 'runs'
    allowed = {}
    for phase, schedule in frozen['phase_schedule'].items():
        allowed[phase] = {(j['group_id'], j['procedure']) for j in schedule['jobs']}
    phase_files = {'.integrity.lock', 'plan.csv', 'manifest_identity.json', 'progress.jsonl'}
    task_files = {'prompt.txt', 'record.json'}
    raw_files = {'attempt_started.json', 'events.jsonl', 'stderr.txt', 'response.json', 'meta.json'}
    paths = sorted(base.rglob('*')) if base.exists() else []
    unplanned = []
    for path in paths:
        relative = path.relative_to(base)
        parts = relative.parts
        if parts == ('.integrity.lock',) and path.is_file() and not path.is_symlink():continue
        ok = not path.is_symlink() and parts[0] in allowed
        if ok:
            pairs = allowed[parts[0]]
            if len(parts) == 1:
                ok = path.is_dir()
            elif len(parts) == 2:
                ok = (parts[1] in phase_files and path.is_file()) or (parts[1] in {g for g, _ in pairs} and path.is_dir())
            elif len(parts) == 3:
                ok = (parts[1], parts[2]) in pairs and path.is_dir()
            elif len(parts) == 4:
                ok = (parts[1], parts[2]) in pairs and ((parts[3] in task_files and path.is_file()) or
                     (parts[3] in {'attempt_01', 'attempt_02'} and path.is_dir()))
            elif len(parts) == 5:
                ok = ((parts[1], parts[2]) in pairs and parts[3] in {'attempt_01', 'attempt_02'} and
                      parts[4] in raw_files and path.is_file())
            else:
                ok = False
        if not ok:
            unplanned.append({'path': str(Path('runs') / relative),
                              'kind': 'symlink' if path.is_symlink() else 'directory' if path.is_dir() else 'file'})
    return {'observed_paths': len(paths),
            'observed_record_files': sum(p.name == 'record.json' for p in paths),
            'observed_attempt_directories': sum(p.is_dir() and p.name.startswith('attempt_') for p in paths),
            'observed_started_attempt_files': sum(p.name == 'attempt_started.json' for p in paths),
            'observed_sealed_attempt_files': sum(p.name == 'meta.json' for p in paths),
            'unplanned_artifacts': unplanned}


def summarize(rows,phase):
    procedures={};families=[]
    for proc in sorted({r['procedure'] for r in rows}):
        part=[r for r in rows if r['procedure']==proc]
        value={'planned':len(part),'complete':sum(r['status']=='complete' for r in part),
               'correct':sum(r['correct'] for r in part),'accuracy':rate(sum(r['correct'] for r in part),len(part)),
               **row_usage_totals(part),'seconds':sum(r['seconds'] for r in part)}
        if phase=='challenge':
            error=[r for r in part if r['draft_condition']=='error'];correct=[r for r in part if r['draft_condition']=='correct']
            value.update({'authored_error_planned':len(error),'authored_error_repaired':sum(r['correct'] for r in error),
                          'authored_error_repair_rate':rate(sum(r['correct'] for r in error),len(error)),
                          'authored_correct_planned':len(correct),'authored_correct_not_retained':sum(not r['correct'] for r in correct),
                          'authored_correct_damage_rate':rate(sum(not r['correct'] for r in correct),len(correct))})
        procedures[proc]=value
        for family in sorted({r['family_id'] for r in part}):
            subset=[r for r in part if r['family_id']==family]
            for condition in (['all'] if phase=='p0' else ['correct','error']):
                selected=[r for r in subset if condition=='all' or r['draft_condition']==condition]
                families.append({'family_id':family,'error_type':subset[0]['error_type'],'procedure':proc,'draft_condition':condition,
                                 'planned':len(selected),'complete':sum(r['status']=='complete' for r in selected),
                                 'correct':sum(r['correct'] for r in selected),'accuracy':rate(sum(r['correct'] for r in selected),len(selected))})
    result={'procedures':procedures,'family_results':families}
    if phase=='p0':
        diagnostic={}
        for kind in ['material','rule']:
            selected=[r for r in rows if r['error_type']==kind]
            flawed=[r for r in selected if r['state']!='missing' and r['advice']=='flawed']
            aligned=[r for r in selected if r['state']!='missing' and r['advice']=='aligned']
            missing=[r for r in selected if r['state']=='missing']
            errors=[r for r in flawed if r['status']=='complete' and not r['correct']]
            diagnostic[kind]={'present_flawed_n':len(flawed),'present_flawed_correct':sum(r['correct'] for r in flawed),
                              'natural_errors':len(errors),'error_families':sorted({r['family_id'] for r in errors}),
                              'present_aligned_n':len(aligned),'present_aligned_correct':sum(r['correct'] for r in aligned),
                              'missing_n':len(missing),'missing_correct':sum(r['correct'] for r in missing)}
        result['difficulty_diagnostic']=diagnostic
    else:
        groups=defaultdict(dict)
        for row in rows:groups[row['group_id']][row['procedure']]=row
        contrasts={}
        for treatment,comparator in [('P7','P8'),('P7','P3'),('P3','P1')]:
            strata={}
            for condition in ['error','correct']:
                values=defaultdict(list);kinds={}
                for group in groups.values():
                    a,b=group[treatment],group[comparator]
                    if a['draft_condition']!=condition:continue
                    values[a['family_id']].append(a['correct']-b['correct']);kinds[a['family_id']]=a['error_type']
                family=[{'family_id':f,'error_type':kinds[f],'paired_drafts':len(v),'difference':mean(v)} for f,v in sorted(values.items())]
                means={k:mean([r['difference'] for r in family if r['error_type']==k]) for k in ['material','rule']}
                strata[condition]={'family_results':family,'type_means':means,'interaction_rule_minus_material':means['rule']-means['material'],
                                   'inference':'Descriptive authored-draft challenge; 4 constructed families/type, no confirmatory p value or natural-error claim.'}
            contrasts[treatment+'-'+comparator]=strata
        result['contrasts']=contrasts
    return result


def collect_phase(phase):
    if phase not in runner.PHASES:raise ValueError('Unknown phase')
    frozen=runner.verify();fhash=runner.file_sha(R/'protocol/frozen.json')
    inventory=inventory_runs(frozen)
    if inventory['unplanned_artifacts']:raise RuntimeError('Unplanned run artifacts')
    items=entries(R/f'prompts/{phase}_items.json');keys=entries(R/f'keys/{phase}_keys.json')
    rows=[];attempts_all=[];sessions=[];record_hashes={}
    audit={'phase':phase,'frozen_hash':fhash,'run_inventory':inventory,'unsealed_attempts':[],
           'unusual_item_types':[],'lifecycle_errors':[],'record_errors':[],'final_source_conflicts':[],'duplicate_session_ids':[]}
    for job in frozen['phase_schedule'][phase]['jobs']:
        item=items[job['item_id']];task=R/'runs'/phase/job['group_id']/job['procedure'];rp=task/'record.json'
        first=item['draft_text'] if phase=='challenge' else None
        prompt=runner.build_prompt(job,item,first)
        identity={**job,'phase':phase,'frozen_hash':fhash,'first_sha256':runner.sha(first) if first is not None else None,
                  'first_origin':'authored_fixed_draft' if phase=='challenge' else None,'gate_sha256':runner.gate_hash(phase),'prompt_sha256':runner.sha(prompt)}
        if rp.exists():
            rec=runner.validate_record(phase,job,item,first,fhash);record_hashes[str(rp.relative_to(R))]=runner.file_sha(rp)
        else:
            rec={'status':'not_executed','parsed':None,'attempts':[]}
            if (task/'prompt.txt').exists() and (task/'prompt.txt').read_text()!=prompt:raise RuntimeError('Paused prompt differs from planned prompt')
            for number,ad in enumerate(sorted(task.glob('attempt_*')),1):
                if ad.name!=f'attempt_{number:02d}':raise RuntimeError('Noncontiguous unfinished attempts')
                if not (ad/'meta.json').exists():
                    if list(ad.iterdir()):audit['unsealed_attempts'].append(str(ad.relative_to(R)))
                    continue
                meta=runner.read(ad/'meta.json');final=runner.validate_attempt(ad,meta,runner.sha(prompt),identity)
                if meta.get('attempt')!=number:raise RuntimeError('Unfinished attempt identity mismatch')
                if final is not None and final.strip():audit['record_errors'].append('Sealed final lacks terminal record: '+str(ad.relative_to(R)))
                rec['attempts'].append(meta)
            if rec['attempts']:rec['status']='paused_unfinalized'
        for attempt in rec['attempts']:
            attempts_all.append(attempt);sessions += [sid for sid in attempt.get('thread_ids',[]) if isinstance(sid,str) and sid.strip()]
            final=runner.validate_attempt(task/f"attempt_{attempt['attempt']:02d}",attempt,runner.sha(prompt),identity)
            if runner.final_sources_disagree(attempt):audit['final_source_conflicts'].append(str((task/f"attempt_{attempt['attempt']:02d}").relative_to(R)))
            if attempt.get('lifecycle_errors') and (attempt.get('turn_completed') or bool(final and final.strip())):audit['lifecycle_errors'].append({'group':job['group_id'],'procedure':job['procedure'],'attempt':attempt['attempt']})
            audit['unusual_item_types']+=attempt.get('unexpected_items',[])
        parsed=rec.get('parsed') or {};resource=usage_totals(rec['attempts']);key=keys[job['item_id']]
        rows.append({**job,'family_id':item['family_id'],'error_type':item['error_type'],'state':item['state'],
                     'advice':item.get('advice',''),'draft_condition':item.get('draft_condition',''),
                     'first_origin':rec.get('first_origin'),'first_sha256':rec.get('first_sha256'),
                     'correct_action':key['correct_action'],'action':parsed.get('action',''),'status':rec['status'],
                     'correct':int(rec['status']=='complete' and parsed.get('action')==key['correct_action']),
                     'attempts':len(rec['attempts']),'seconds':sum(a.get('seconds',0) for a in rec['attempts']),**resource,
                     'input_tokens':resource['sum_input_tokens'] if rec['attempts'] and resource['sum_input_tokens'] is not None else '',
                     'output_tokens':resource['sum_output_tokens'] if rec['attempts'] and resource['sum_output_tokens'] is not None else ''})
    # Audit ALL observed tasks across phases, including tasks without record.json.
    # Cross-phase data are used only for integrity/session checks, never scores or
    # resource totals. In particular, a pre-gate challenge attempt cannot disappear
    # merely because it was interrupted before sealing its terminal record.
    cross_sessions=list(sessions)
    for other in runner.PHASES:
        if other==phase:continue
        other_items=entries(R/f'prompts/{other}_items.json')
        for job in frozen['phase_schedule'][other]['jobs']:
            task=R/'runs'/other/job['group_id']/job['procedure'];rp=task/'record.json'
            directories=sorted(task.glob('attempt_*'))
            if not rp.exists() and not directories and not (task/'prompt.txt').exists():continue
            if other=='challenge' and not (R/'analysis/decision_gate.json').is_file():
                audit['record_errors'].append('Challenge artifacts exist before diagnostic gate: '+str(task.relative_to(R)))
                for ad in directories:
                    if not (ad/'meta.json').exists() and list(ad.iterdir()):audit['unsealed_attempts'].append(str(ad.relative_to(R)))
                continue
            item=other_items[job['item_id']];first=item['draft_text'] if other=='challenge' else None
            prompt=runner.build_prompt(job,item,first)
            identity={**job,'phase':other,'frozen_hash':fhash,'first_sha256':runner.sha(first) if first is not None else None,
                      'first_origin':'authored_fixed_draft' if other=='challenge' else None,'gate_sha256':runner.gate_hash(other),'prompt_sha256':runner.sha(prompt)}
            if rp.exists():record=runner.validate_record(other,job,item,first,fhash)
            else:
                record={'attempts':[]}
                if (task/'prompt.txt').exists() and (task/'prompt.txt').read_text()!=prompt:raise RuntimeError('Cross-phase paused prompt differs from planned prompt')
                terminal_seen=False
                for number,ad in enumerate(directories,1):
                    if ad.name!=f'attempt_{number:02d}':raise RuntimeError('Noncontiguous cross-phase unfinished attempts')
                    if terminal_seen:audit['record_errors'].append('Cross-phase attempt follows a returned final or protocol violation: '+str(ad.relative_to(R)))
                    if not (ad/'meta.json').exists():
                        if list(ad.iterdir()):audit['unsealed_attempts'].append(str(ad.relative_to(R)))
                        continue
                    meta=runner.read(ad/'meta.json');final=runner.validate_attempt(ad,meta,runner.sha(prompt),identity)
                    if meta.get('attempt')!=number:raise RuntimeError('Cross-phase unfinished attempt identity mismatch')
                    # A sealed, validated final may be restored to record.json with
                    # zero model calls. Missing record alone is not a raw conflict.
                    terminal_seen=bool(final and final.strip()) or runner.classify_final(meta,final)[0]=='protocol_failure'
                    record['attempts'].append(meta)
            for attempt in record['attempts']:
                cross_sessions += [sid for sid in attempt['thread_ids'] if isinstance(sid,str) and sid.strip()]
                final=runner.validate_attempt(task/f"attempt_{attempt['attempt']:02d}",attempt,runner.sha(prompt),identity)
                if runner.final_sources_disagree(attempt):audit['final_source_conflicts'].append(str((task/f"attempt_{attempt['attempt']:02d}").relative_to(R)))
                if attempt.get('lifecycle_errors') and (attempt.get('turn_completed') or bool(final and final.strip())):
                    audit['lifecycle_errors'].append({'phase':other,'group':job['group_id'],'procedure':job['procedure'],'attempt':attempt['attempt']})
                audit['unusual_item_types']+=attempt.get('unexpected_items',[])
    audit['duplicate_session_ids']=[sid for sid,n in Counter(cross_sessions).items() if n>1]
    passed=not any(audit[k] for k in ['unsealed_attempts','unusual_item_types','lifecycle_errors','record_errors','final_source_conflicts','duplicate_session_ids'])
    summary={'phase':phase,'planned_tasks':len(rows),'complete_tasks':sum(r['status']=='complete' for r in rows),
             'terminal_tasks':len(record_hashes),'actual_cli_attempts':len(attempts_all),'unique_sessions':len(set(sessions)),
             'status_counts':dict(Counter(r['status'] for r in rows)),**usage_totals(attempts_all),
             **summarize(rows,phase),'passed_integrity':passed,'frozen_hash':fhash,'record_sha256':record_hashes,
             'resource_scope':'Subject CLI attempts only; management/authoring/review overhead unknown; monetary cost NA.',
             'verified_billed_cost':None,'evaluation_type':'simulation_only',
             'inference':'Development-only families; no real humans/external expert/heldout confirmation. Authored challenge never mixed with natural P0 errors.'}
    return rows,summary,audit


def make_gate(summary):
    if summary['phase']!='p0' or summary['planned_tasks']!=80:raise RuntimeError('Gate requires exact80 P0 plan')
    if summary['terminal_tasks']!=80:raise RuntimeError('Gate requires all80 terminal P0 records')
    passed=summary['passed_integrity'] and summary['complete_tasks']==80
    details={}
    for kind in ['material','rule']:
        d=summary['difficulty_diagnostic'][kind]
        details[kind]={'observed':d,'natural_error_window':4<=d['natural_errors']<=8,
                       'error_family_coverage':len(d['error_families'])>=3,
                       'aligned_accuracy_floor':d['present_aligned_correct']>=12,
                       'missing_accuracy_floor':d['missing_correct']>=6,
                       'expected_denominators':(d['present_flawed_n'],d['present_aligned_n'],d['missing_n'])==(16,16,8)}
    eligible=passed and all(all(v for k,v in d.items() if k!='observed') for d in details.values())
    return {'protocol_version':'v3-development-diagnostic-only','frozen_hash':summary['frozen_hash'],
            'p0_record_sha256':summary['record_sha256'],'complete_p0_required':80,'complete_p0_observed':summary['complete_tasks'],
            'integrity_passed':summary['passed_integrity'],'criteria':details,
            'status':'eligible_for_independent_holdout' if eligible else 'development_gate_failed' if passed else 'technical_block',
            'challenge_allowed':bool(passed and not eligible),
            'next_action':'Prepare new independent family holdout; do not compare on screening P0' if eligible else 'Run frozen authored-draft challenge separately' if passed else 'No fallback; preserve technical failures and diagnose',
            'gate_is_not':'Not power analysis, confirmatory evidence, or selection based on P7 advantage.'}


def run(phase,write_gate=False):
    rows,summary,audit=collect_phase(phase)
    out=R/'analysis'/phase;out.mkdir(parents=True,exist_ok=True)
    for name,data in [('scored_runs.csv',rows),('family_results.csv',summary['family_results'])]:
        with (out/name).open('w',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    runner.dump(out/'summary.json',summary);runner.dump(out/'integrity_audit.json',audit)
    if not summary['passed_integrity']:raise RuntimeError('Integrity audit failed')
    if write_gate:
        if phase!='p0':raise ValueError('Only P0 writes diagnostic gate')
        gate=make_gate(summary);p=R/'analysis/decision_gate.json'
        if p.exists():
            if {k:v for k,v in runner.read(p).items() if k!='created_utc'}!=gate:raise RuntimeError('Refusing to replace sealed decision gate')
        else:runner.seal_json(p,{**gate,'created_utc':runner.now()})
    print(json.dumps({k:summary[k] for k in ['phase','planned_tasks','complete_tasks','terminal_tasks','actual_cli_attempts','passed_integrity']},ensure_ascii=False))
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=list(runner.PHASES));ap.add_argument('--write-gate',action='store_true')
    args=ap.parse_args();run(args.phase,args.write_gate)
