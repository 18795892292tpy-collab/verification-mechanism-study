#!/usr/bin/env python3
"""Verify an explicitly downloaded V3 archive copy; never execute the experiment."""
from pathlib import Path
import csv,hashlib,json,os
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(v,m):
 if not v:raise RuntimeError(m)
meta=json.loads((R/'ARCHIVE_METADATA.json').read_text())
require(meta['manifest_sha256']==sha(R/'PUBLICATION_MANIFEST.csv'),'Manifest digest mismatch')
require(meta['verifier_sha256']==sha(R/'PUBLICATION_VERIFY.py'),'Verifier digest mismatch')
with (R/'PUBLICATION_MANIFEST.csv').open(newline='',encoding='utf8') as f:rows=list(csv.DictReader(f))
require(len(rows)==len({x['path'] for x in rows}),'Duplicate manifest paths')
for row in rows:
 rel=Path(row['path']);require(not rel.is_absolute() and '..' not in rel.parts,'Unsafe path')
 p=R/rel;require(not p.is_symlink() and p.is_file() and p.stat().st_size==int(row['bytes']) and sha(p)==row['sha256'],'Archive payload mismatch: '+str(rel))
allowed_extra={'PUBLICATION_MANIFEST.csv','PUBLICATION_VERIFY.py','ARCHIVE_METADATA.json'}
actual={p.relative_to(R).as_posix() for p in R.rglob('*') if p.is_file()}
require(actual=={x['path'] for x in rows}|allowed_extra,'Unexpected or missing archive files')
a=R/meta['audit_source_path'];require(sha(a)==meta['audit_sha256'],'Independent audit changed')
audit=json.loads(a.read_text());require(audit['integrity_status']=='pass' and audit['original_gate_status']=='technical_block','Incorrect audit/gate')
locks={'runs/.integrity.lock','amendments/A1_posthoc/challenge/runs/.integrity.lock'}
require(locks<=set(audit['source_hashes']),'Expected excluded lock evidence absent')
for rel,h in audit['source_hashes'].items():
 if rel in locks:
  require(not (R/rel).exists() and not (R/rel).is_symlink(),'Excluded runtime lock present in archive')
 else:require((R/rel).is_file() and sha(R/rel)==h,'Audited input mismatch: '+rel)
fig=json.loads((R/'figures/v3_figure_manifest.json').read_text());require(fig['visual_review']=='passed','Figure review missing')
for kind in ['inputs_sha256','challenge_raw_sha256','outputs_sha256']:
 for rel,h in fig.get(kind,{}).items():require((R/rel).is_file() and sha(R/rel)==h,'Figure input/output mismatch: '+rel)
print(json.dumps({'scope':'archive_evidence_only','root':str(R),'payload_files_verified':len(rows),'audited_inputs_verified':len(audit['source_hashes'])-len(locks),'excluded_runtime_locks':sorted(locks),'original_gate':'technical_block','does_not_reexecute_subject_tasks':True},ensure_ascii=False))
