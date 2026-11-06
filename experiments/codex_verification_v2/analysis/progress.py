#!/usr/bin/env python3
"""Read-only raw record inspection; only replaces the derived PROGRESS.json."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import json
R = Path(__file__).resolve().parents[1]
phase = R / 'runs/dev'
records = [json.loads(p.read_text()) for p in phase.glob('*/*/record.json')]
started = list(phase.glob('*/*/attempt_*/attempt_started.json'))
sealed = list(phase.glob('*/*/attempt_*/meta.json'))
paused = [p.parent.parent for p in sealed if not (p.parent.parent / 'record.json').exists()]
last_event = None
if (phase / 'progress.jsonl').exists():
    for line in (phase / 'progress.jsonl').read_text().splitlines():
        if line.strip(): last_event = json.loads(line)
out = {'updated_utc': datetime.now(timezone.utc).isoformat(), 'study': 'codex_verification_v2',
       'planned_total': 800, 'planned_P0': 160, 'planned_review': 640,
       'terminal_records': len(records), 'remaining_to_terminal': 800 - len(records),
       'status_counts': dict(Counter(r['status'] for r in records)),
       'procedure_counts': dict(Counter(r['procedure'] for r in records)),
       'started_attempts': len(started), 'sealed_attempts': len(sealed),
       'unfinalized_tasks_with_sealed_attempts': len(set(paused)),
       'unsealed_started_attempts': len(set(p.parent for p in started) - set(p.parent for p in sealed)),
       'last_event': last_event}
(R / 'PROGRESS.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False))
