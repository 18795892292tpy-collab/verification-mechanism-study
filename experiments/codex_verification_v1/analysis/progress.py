from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import json
R=Path(__file__).resolve().parents[1]
out={'updated_utc':datetime.now(timezone.utc).isoformat(),'study':'codex_verification_v1','planned_total':210,'phases':{}}
for phase,total in [('toy',10),('dev',200)]:
 records=[json.loads(p.read_text()) for p in (R/'runs'/phase).glob('*/*/record.json')]
 out['phases'][phase]={'planned':total,'recorded':len(records),'status_counts':dict(Counter(r['status'] for r in records)),
  'procedure_counts':dict(Counter(r['procedure'] for r in records)),
  'started_attempts':sum(1 for p in (R/'runs'/phase).glob('*/*/attempt_*/attempt_started.json')),
  'committed_attempts':sum(len(r['attempts']) for r in records)}
(R/'PROGRESS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
