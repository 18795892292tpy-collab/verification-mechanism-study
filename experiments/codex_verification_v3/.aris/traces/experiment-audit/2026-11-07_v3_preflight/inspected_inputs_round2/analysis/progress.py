from pathlib import Path
from collections import Counter
import json,datetime
R=Path(__file__).resolve().parents[1]
result={'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phases':{}}
for phase,n in [('p0',80),('challenge',128)]:
 root=R/'runs'/phase;records=[json.loads(p.read_text()) for p in root.glob('*/*/record.json')]
 started=list(root.glob('*/*/attempt_*/attempt_started.json'));sealed=list(root.glob('*/*/attempt_*/meta.json'))
 result['phases'][phase]={'planned':n,'terminal':len(records),'status_counts':dict(Counter(r['status'] for r in records)),
                          'started_attempts':len(started),'sealed_attempts':len(sealed),'active_or_unsealed':len(started)-len(sealed)}
print(json.dumps(result))
