#!/usr/bin/env python3
"""Read-only publication check against the independent raw-event audit."""
import hashlib
import json
from pathlib import Path
import socket

R = Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3')
assert socket.gethostname() == 'liekkas' and R.resolve() == R
read = lambda rel: json.loads((R / rel).read_text())
sha = lambda rel: hashlib.sha256((R / rel).read_bytes()).hexdigest()

def check():
    a = read('audits/FINAL_EXPERIMENT_AUDIT.json')
    s = read('analysis/v3_report_summary.json')
    m = read('figures/v3_figure_manifest.json')
    tracked = dict(a['source_hashes'])
    for field in ['inputs_sha256', 'challenge_raw_sha256', 'outputs_sha256']:
        for rel, digest in m[field].items():
            assert rel not in tracked or tracked[rel] == digest, ('conflicting source hash', rel)
            tracked[rel] = digest
    tracked['figures/visual_review.json'] = m['visual_review_evidence_sha256']
    tracked['figures/v3_figure_manifest.json'] = sha('figures/v3_figure_manifest.json')
    tracked['audits/FINAL_EXPERIMENT_AUDIT.json'] = sha('audits/FINAL_EXPERIMENT_AUDIT.json')
    assert all(sha(rel) == digest for rel, digest in tracked.items()), 'source/publication drift before comparison'
    assert s['original_gate'] == {'status': 'technical_block', 'challenge_allowed': False}
    assert s['strict_p0'] == {'planned': 80, 'complete': 0, 'attempts': 80, 'status_counts': {'technical_failure': 80}}
    assert s['a1_p0'] == {'accepted': 80, 'correct': 80, 'planned': 80, 'attempts': 80, 'hypothetical_gate': 'development_gate_failed', 'not_a_run_gate': True}
    c = s['challenge']; x = a['extra_C']
    for pub, aud in [('planned','planned_tasks'), ('terminal','terminal_tasks'), ('complete','complete_tasks'), ('actual_attempts','attempts'), ('status_counts','status_counts')]:
        assert c[pub] == x[aud], (pub, c[pub], x[aud])
    assert c['unique_complete_sessions'] == 127
    ar = {(r['group_id'], r['procedure']): r for r in a['extra_C_rows']}
    sr = {(r['group_id'], r['procedure']): r for r in s['rows']}
    assert len(sr) == len(ar) == len(s['rows']) == 128 and sr.keys() == ar.keys()
    for key, r in sr.items():
        q = ar[key]
        for field in ['group_id','item_id','procedure','family_id','error_type','state','draft_condition','status','correct']:
            assert r[field] == q[field], (key, field)
        assert len(q['attempts']) == 1
        for field in ['input_tokens','output_tokens','seconds']:
            assert r[field] == q['attempts'][0][field], (key, field)
    for proc, v in c['procedures'].items():
        w = x['procedures'][proc]
        assert v['planned'] == w['planned']
        assert v['complete'] == sum(r['status']=='complete' for r in sr.values() if r['procedure']==proc)
        for condition in ['error', 'correct']:
            for pub, aud in [('planned','planned'), ('retained_correct','final_correct'), ('not_correct','not_retained'), ('failures','failed_tasks')]:
                assert v[condition][pub] == w[condition][aud], (proc,condition,pub)
    af = {(f['family_id'], f['procedure'], f['condition']): f for f in x['family_results']}
    assert len(c['family_results']) == len(af) == 64
    for f in c['family_results']:
        q = af[f['family_id'], f['procedure'], f['draft_condition']]
        for pub, aud in [('error_type','type'),('n','planned'),('correct','correct'),('accuracy','rate')]:
            assert f[pub] == q[aud]
    for key, v in c['contrasts'].items():
        contrast, condition = key.split(':'); q = x['contrasts'][contrast][condition]
        assert v['type_means'] == q['type_means'] and v['interaction_rule_minus_material'] == q['interaction_rule_minus_material']
        assert [(f['family_id'],f['error_type'],f['difference']) for f in v['families']] == [(f['family'],f['type'],f['difference']) for f in q['families']]
    resources=c['resources']
    assert resources['input_tokens'] == x['sum_input_tokens'] == 2380276
    assert resources['output_tokens'] == x['sum_output_tokens'] == 69329
    assert resources['input_missing'] == resources['output_missing'] == 0
    assert abs(resources['summed_attempt_seconds']-sum(r['attempts'][0]['seconds'] for r in ar.values())) < 1e-6
    failed=[r for r in sr.values() if r['status'] != 'complete']
    assert len(failed)==1 and failed[0]['group_id']=='R05_decisive_change_draft_error_r1' and failed[0]['procedure']=='P8'
    assert failed[0]['correct']==0 and failed[0]['problem']=='unrecognized stderr'
    assert s['raw_sources_sha256']==m['challenge_raw_sha256']
    assert all(sha(rel)==digest for rel,digest in tracked.items()), 'source/publication drift after comparison'
    return {'status':'PASS','raw_source_files_rechecked':len(a['source_hashes']), 'publication_input_hashes_checked':len(m['inputs_sha256']), 'publication_raw_hashes_checked':len(m['challenge_raw_sha256']), 'publication_outputs_checked':len(m['outputs_sha256']), 'total_unique_files_stable':len(tracked), 'rows_compared':128, 'family_cells_compared':64, 'contrasts_compared':len(c['contrasts']), 'failures_retained':1, 'real_model_calls':0, 'stable_sha256':tracked}

if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False, indent=2))
