#!/usr/bin/env python3
"""Independent, offline V2 audit. No harness imports, subprocesses or model calls.

--prepare-check validates frozen inputs and a public-document rule oracle only.
--final requires 800 terminal records and the four original analysis artifacts.
--write additionally saves NEW independent audit outputs, never raw records.
--archive-root PATH explicitly selects a downloaded archive for evidence-only
recomputation. It never represents restored execution on the original machine.
The sole declared archive omission is runs/dev/.integrity.lock, a process lock;
its absence is reconciled only against the pinned original final audit manifest.
This is a same-family/provisional semantic audit, not external expert validation.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import argparse
import csv
import hashlib
import json
import math
import re
import socket

ROOT = Path('/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2')
ORIGINAL_ROOT = ROOT
ARCHIVE_MODE = False
ORIGINAL_FINAL_AUDIT_SHA256 = '24905c6012661ac485a037d8dea216b3d183adf8cce343adcf2b35f961f7bd3a'
DECLARED_ARCHIVE_OMISSION = 'runs/dev/.integrity.lock'
PREPARATION_FROZEN_SHA256 = 'f5f73d297f3cc6b3f4049770dc6688a2ddc72ca66a784a89fd712d9c243afaf1'
# Independently inspected during-run amendment; baseline's 28 source hashes stay
# unchanged. These pins are additional evidence, not a replacement freeze.
CONCURRENCY_PINS = {
    'protocol/CONCURRENCY_AMENDMENT_2026-11-07.json': 'db685add1b3f1467816e4c5e72d58bab66e92d938678a624204918ac1cfd448c',
    'harness/run_concurrency_override.py': '15adc3074c13d6322c1e1373701488502335a9fc9745a3a022ed3d61fb12d41c',
    'audits/concurrency_stop_request.json': '30987fd01119d1607b28e6ca3ad87150c75346a60dea1fcea4058fbfa39b776b',
    'audits/concurrency_override_tests.json': 'e4e86163590ecf486253ae45d66bafee2c45ab48328b441bd1c55071ec30936b',
}
ORIGINAL_PROGRESS_PREFIX_BYTES = 119354
ORIGINAL_PROGRESS_PREFIX_SHA256 = 'dbe3a9d40d252bae5376e7be037d15156f7b14f9401c733288948da4eed887ff'
PROCS = ('P0', 'P1', 'P3', 'P7', 'P8')
STATES = ('base', 'decisive_change', 'irrelevant', 'paraphrase', 'missing')
FAMILIES = tuple(f'{kind}{i:02d}' for kind in ('M', 'R') for i in range(1, 5))
TERMINAL = {'complete', 'parse_failure', 'technical_failure', 'protocol_failure', 'not_run_first_failed'}
REQUIRED_ANALYSIS = ('summary.json', 'scored_runs.csv', 'family_results.csv', 'integrity_audit.json')
LIMITS = [
    'simulation_only: author-constructed closed fictional school rules, not human behavior or policy effectiveness.',
    'Four designed families per type (n=4/type); repeats and transformations are not independent families.',
    'No independent education-administration expert validation; same-family semantic checks remain provisional.',
    'Requested gpt-6-astra/ultra and CLI/events are observable; hidden weight snapshot and desktop-context equality are not.',
    'No observed tool events is an observable-log claim; service-side hidden context cannot be certified by these artifacts.',
    'Usage covers subject CLI attempts only; authoring/review/management overhead and verified billed cost are unknown.',
]


def read(p):
    return json.loads(Path(p).read_text())


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def filehash(p):
    return digest(Path(p).read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rate(a, b):
    return a / b if b else None


def average(values):
    return sum(values) / len(values) if values else None


def load_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def documents(public):
    before_options = public.split('可选行动：', 1)[0]
    matches = re.findall(r'\[(S[1-8])\] ([^\n]+)\n(.*?)(?=\n\n\[S[1-8]\]|\Z)', before_options, re.S)
    require(len(matches) == 8 and len({m[0] for m in matches}) == 8, 'Expected exactly eight public documents')
    return {sid: {'source_id': sid, 'title': title, 'text': body.rstrip()} for sid, title, body in matches}


# These option meanings were read directly in the public options, not taken from
# correct_action/semantic_action/option_analysis in the supplied answer keys.
OPTION_SIGNATURES = {
    'M01': {'direct': '单部门采购路径', 'joint': '联合会签采购路径', 'pause': '暂停 Q26', 'cancel': '撤销 Q26'},
    'M02': {'reject': '驳回全部三处', 'limited': '将 L3 从本次', 'full': 'L1、L2、L3 三处', 'pause': '暂停本单凭单'},
    'M03': {'pause': '暂停 T9', 'full': '长期常规方案', 'retain': '保留现行备课方案', 'pilot': '有期限的新方案试用'},
    'M04': {'routine': '登记为常规跟踪', 'pause': '暂停支持等级登记', 'comprehensive': '登记为全面支持', 'targeted': '登记为定向支持'},
    'R01': {'normal': '保持常规在线导入', 'manual': '切换为应急手工暂记', 'pause': '暂停本批工作模式', 'cancel': '取消本批学籍导入'},
    'R02': {'shrink': '当场缩减为十五名', 'postpone': '推迟整班', 'depart': '按三十名学生和现有两名成人', 'pause': '补取吴老师证书有效状态'},
    'R03': {'pause': '暂停本单入校路径', 'unescorted': '自行入校', 'escort': '由已指定人员全程陪同', 'deny': '不准本次按预约时点'},
    'R04': {'release': '批准本批全部物资', 'pause': '暂停判断本批是否达标', 'partial': '仅发放本批中', 'complete': '退回补齐未达标班级'},
}


def public_oracle(item):
    """Use only family ID and public documents/options; never use state or advice.

    Fixed constants below are transcribed from each family's explicit rules;
    variable decisive facts are extracted from the public source documents.
    This is a scoped oracle for this frozen corpus, not a general text reasoner.
    """
    family, public = item['family_id'], item['public_text']
    docs = documents(public)
    s = {k: v['text'] for k, v in docs.items()}
    opt_text = public.split('可选行动：', 1)[1].split('随件分析备忘录', 1)[0]
    opts = dict(re.findall(r'^([A-D])．([^\n]+)$', opt_text, re.M))
    require(set(opts) == set('ABCD'), f'{item["item_id"]}: malformed public options')
    mapping = {}
    for meaning, signature in OPTION_SIGNATURES[family].items():
        found = [letter for letter, text in opts.items() if signature in text]
        require(len(found) == 1, f'{item["item_id"]}: ambiguous option {meaning}')
        mapping[meaning] = found[0]
    require(len(set(mapping.values())) == 4, 'Option mapping is not one-to-one')
    decisive_source = 'S3' if family == 'M03' else 'S4'
    evidence = s[decisive_source]
    missing = '未归档' in evidence or '未随名册归档' in evidence
    if family == 'M01':
        require('八万元' in s['S1'] and '六万元' in s['S1'] and '九月十五日零时' in s['S2'], 'M01 rule constants')
        require('七万二千元' in s['S3'] and 'E47' in s['S3'], 'M01 amount/link')
        m = re.search(r'E47 的服务器确认时间为 (\d+) 月 (\d+) 日 (\d+):(\d+)', evidence)
        require(bool(m) != missing, 'M01 decisive fact must be known or explicitly absent')
        accepted = None if missing else datetime(2026, *map(int, m.groups()))
        facts = {'amount': 72000, 'cutover': '2026-09-15 00:00', 'accepted_at': accepted.strftime('%Y-%m-%d %H:%M') if accepted else None, 'old_threshold': 80000, 'new_threshold': 60000}
        semantic = 'pause' if missing else ('direct' if 72000 < (80000 if accepted < datetime(2026, 9, 15) else 60000) else 'joint')
    elif family == 'M02':
        m = re.search(r'委托附件列明的可签场地为 ([L123、]+)。', evidence)
        require(bool(m) != missing, 'M02 decisive fact')
        delegated = None if missing else m[1].split('、')
        require('L1' in s['S2'] and 'L2' in s['S2'] and 'L3' in s['S2'] and 'W6' in s['S3'], 'M02 request/link')
        facts = {'requested': ['L1', 'L2', 'L3'], 'delegated': delegated, 'signer': '周主任', 'master_scope': ['L1', 'L2', 'L3']}
        semantic = 'pause' if missing else ('full' if set(delegated) >= {'L1', 'L2', 'L3'} else 'limited' if set(delegated) & {'L1', 'L2', 'L3'} else 'reject')
    elif family == 'M03':
        m = re.search(r'本次 T9 培训名册的资格代码为 ([NE])。', evidence)
        require(bool(m) != missing, 'M03 decisive fact')
        require(all(t in s['S4'] for t in ['八十二', '八十四', '九十一', '百分之九十四']), 'M03 evidence values')
        require('五分' in s['S1'] and '百分之八十五' in s['S1'] and '两项' in s['S1'], 'M03 rule constants')
        code = None if missing else m[1]
        facts = {'target_group': code, 'gains': {'N': 84-82, 'E': 91-84}, 'completion': 94, 'studies': 1, 'min_gain': 5, 'min_completion': 85}
        qualifying = 0 if missing else int(facts['gains'][code] >= 5 and 94 >= 85)
        semantic = 'pause' if missing else 'pilot' if qualifying == 1 else 'full' if qualifying >= 2 else 'retain'
    elif family == 'M04':
        m = re.search(r'核准免到记录共([八十])块，每块五个人日。', evidence)
        require(bool(m) != missing, 'M04 decisive fact')
        require('八百' in s['S2'] and '七百二十' in s['S3'] and '九十六' in s['S1'] and '九十二' in s['S1'], 'M04 constants')
        blocks = None if missing else {'八': 8, '十': 10}[m[1]]
        facts = {'planned': 800, 'present': 720, 'exempt_blocks': blocks, 'block_size': 5, 'routine_min': 96, 'targeted_min': 92}
        ratio = None if missing else Fraction(720, 800-blocks*5)
        semantic = 'pause' if missing else 'routine' if ratio >= Fraction(96,100) else 'targeted' if ratio >= Fraction(92,100) else 'comprehensive'
    elif family == 'R01':
        m = re.search(r'认证节点恢复记录的时间为 (\d+):(\d+)', evidence)
        require(bool(m) != missing and '08:10' in evidence and '三小时' in s['S1'], 'R01 decisive fact/constants')
        end = None if missing else 60*int(m[1])+int(m[2])
        facts = {'outage_start': '2026-10-12 08:10', 'outage_end': None if missing else f'2026-10-12 {int(m[1]):02d}:{int(m[2]):02d}', 'trigger_minutes': 180, 'correction_due_hours': 24}
        semantic = 'pause' if missing else 'manual' if end-(8*60+10) >= 180 else 'normal'
    elif family == 'R02':
        good = '吴老师证书已续期生效，有效期覆盖本次出发日。' in evidence
        bad = '吴老师证书在本次出发日前已到期，续证尚未通过。' in evidence
        require(sum((missing, good, bad)) == 1, 'R02 credential states must be exclusive')
        require('三十' in s['S2'] and '十五' in s['S1'] and ('至少两' in s['S1']), 'R02 constants')
        valid = None if missing else 2 if good else 1
        facts = {'participants': 30, 'consents': 30, 'adults': 2, 'valid_escorts': valid, 'second_valid': None if missing else good, 'minimum_escorts': 2, 'ratio_max': 15}
        semantic = 'pause' if missing else 'depart' if valid >= 2 and 30 <= valid*15 else 'postpone'
    elif family == 'R03':
        m = re.search(r'值班审批员签署的事件分类代码为 (E3|N1)。', evidence)
        require(bool(m) != missing and '二十四小时' in s['S1'] and '四小时' in s['S3'], 'R03 decisive fact/constants')
        require('全程陪同' in s['S5'] and ('核验完成' in s['S5'] or '均已核验' in s['S5']), 'R03 identity/escort')
        code = None if missing else m[1]
        facts = {'class_code': code, 'hours_notice': 4, 'identity_verified': True, 'escort_ready': True}
        semantic = 'pause' if missing else 'escort' if code == 'E3' else 'deny'
    else:
        m = re.search(r'U3 的有效签收确认数为(十七|十八)份。', evidence)
        require(bool(m) != missing and '二十' in s['S2'] and 'U1' in s['S2'] and 'U3' in s['S2'], 'R04 decisive fact/constants')
        n = None if missing else {'十七': 17, '十八': 18}[m[1]]
        facts = {'eligible': {'U1': 20, 'U2': 20, 'U3': 20}, 'signed': {'U1': 20, 'U2': 18, 'U3': n}, 'threshold_numerator': 9, 'threshold_denominator': 10}
        semantic = 'pause' if missing else 'release' if all(v*10 >= 20*9 for v in facts['signed'].values()) else 'complete'
    return {'action': mapping[semantic], 'semantic_action': semantic, 'pause_action': mapping['pause'], 'facts': facts, 'documents': docs, 'option_mapping': mapping}


def prepare():
    if not ARCHIVE_MODE:
        require(socket.gethostname() == 'liekkas', 'Wrong host; use explicit --archive-root only for archive evidence verification')
        require(Path(__file__).resolve().parents[1] == ROOT and ROOT.resolve() == ROOT, 'Wrong target path')
    frozen_path = ROOT/'protocol/frozen.json'
    require(filehash(frozen_path) == PREPARATION_FROZEN_SHA256, 'Frozen manifest differs from independent preparation pin')
    frozen = read(frozen_path)
    for name, expected in frozen['sha256'].items():
        p = ROOT/name
        require(p.is_file() and not p.is_symlink() and filehash(p) == expected, 'Frozen source changed/missing: '+name)
    require(read(ROOT/'runs/dev/manifest_identity.json') == {'frozen_hash': PREPARATION_FROZEN_SHA256}, 'Run manifest identity mismatch')
    backend = read(ROOT/'protocol/backend.json')
    require(backend == frozen['execution_config'], 'Backend differs from frozen execution configuration')
    require(backend['model'] == 'gpt-6-astra' and backend['effort'] == 'ultra', 'Model request identity')
    runtime = frozen['runtime']
    require(runtime['hostname'] == 'liekkas' and runtime['root'] == str(ORIGINAL_ROOT), 'Frozen historical runtime target mismatch')
    if not ARCHIVE_MODE:
        require(str(Path(runtime['cli_path']).resolve()) == runtime['cli_resolved'], 'CLI location changed')
        for path, expected in {runtime['cli_resolved']: runtime['cli_sha256'], **runtime['cli_dependency_sha256']}.items():
            require(filehash(path) == expected, 'CLI byte identity changed: '+path)
    items_list = read(ROOT/'prompts/dev_items.json')
    keys_list = read(ROOT/'keys/dev_keys.json')
    tables = read(ROOT/'cases/factual_truth_tables.json')
    items = {i['item_id']: i for i in items_list}
    keys = {k['item_id']: k for k in keys_list}
    truth = {(t['family_id'], t['state']): t for t in tables}
    expected_ids = {f'{f}_{s}_{a}' for f in FAMILIES for s in STATES for a in ('aligned', 'flawed')}
    require(len(items_list) == len(keys_list) == 80 and set(items) == set(keys) == expected_ids, '80-item factorial identity')
    require(len(tables) == len(truth) == 40, '40 unique family/state truth tables')
    oracles = {}
    for iid, item in items.items():
        o = public_oracle(item)
        key, table = keys[iid], truth[(item['family_id'], item['state'])]
        for field in ('family_id', 'state', 'advice'):
            require(key[field] == item[field], iid+': key/public label mismatch')
        require(key['error_type'] == ('material' if item['family_id'][0] == 'M' else 'rule'), iid+': type mismatch')
        require(key['public_text_sha256'] == digest(item['public_text']), iid+': public source hash')
        require(o['facts'] == key['facts'] == table['facts'], iid+': independently extracted facts disagree')
        require(o['action'] == key['action'] == key['correct_action'] == table['correct_action'], iid+': rule oracle/key disagreement')
        require(o['semantic_action'] == key['semantic_action'] == table['semantic_action'], iid+': semantic key disagreement')
        require(o['pause_action'] == key['pause_action'] == key['escalate_action'], iid+': pause option')
        require(o['documents'] == {d['source_id']: d for d in table['source_documents']}, iid+': public/truth document mismatch')
        advised = re.search(r'建议：选择 ([ABCD])。', item['public_text'])
        require(advised and advised[1] == key['advised_action'], iid+': advice letter mismatch')
        require((advised[1] == o['action']) == (item['advice'] == 'aligned'), iid+': advice alignment mismatch')
        require((o['semantic_action'] == 'pause') == (item['state'] == 'missing'), iid+': missing/known distinction')
        oracles[iid] = o
    for f in FAMILIES:
        for a in ('aligned', 'flawed'):
            b = oracles[f'{f}_base_{a}']['action']
            require(oracles[f'{f}_decisive_change_{a}']['action'] != b, f+': counterfactual does not change action')
            require(all(oracles[f'{f}_{s}_{a}']['action'] == b for s in ('irrelevant','paraphrase')), f+': invariant transformation changes action')
    jobs = frozen['phase_schedule']['dev']['jobs']
    expected = {(iid+f'_r{r}', iid, r, p) for iid in expected_ids for r in (1,2) for p in PROCS}
    actual = [(j['group_id'], j['item_id'], j['repeat'], j['procedure']) for j in jobs]
    require(len(actual) == 800 and len(set(actual)) == 800 and set(actual) == expected, 'Frozen 800-task matrix mismatch')
    plan = load_csv(ROOT/'runs/dev/plan.csv')
    require(plan == [{k: str(v) for k, v in j.items()} for j in jobs], 'plan.csv differs from frozen order/identity')
    require(set(frozen['phase_schedule']) == {'dev'}, 'Unexpected phase')
    ap = read(ROOT/'protocol/analysis_plan.json')
    require(ap['planned_tasks'] == 800 and ap['planned_p0'] == 160 and ap['family_count'] == 8 and ap['evaluation_type'] == 'simulation_only', 'Analysis design mismatch')
    return frozen, items, keys, oracles, jobs


def audit_concurrency_amendment(jobs, final=False):
    """Read-only verification of the explicitly disclosed 3 -> 12 amendment.

    Never import/execute the override driver or its author-supplied test source.
    A pending operational amendment is not mistaken for an applied one. During
    preparation, an invocation may still be active; final mode requires its
    progress lifecycle and all attempts to have closed.
    """
    for name, expected in CONCURRENCY_PINS.items():
        path = ROOT/name
        require(path.is_file() and not path.is_symlink() and filehash(path)==expected, 'Concurrency amendment evidence changed/missing: '+name)
    require({str(p.relative_to(ROOT)) for p in (ROOT/'protocol').glob('CONCURRENCY_AMENDMENT*')} == {'protocol/CONCURRENCY_AMENDMENT_2026-11-07.json'}, 'Additional unaudited concurrency amendment')
    amendment = read(ROOT/'protocol/CONCURRENCY_AMENDMENT_2026-11-07.json')
    stop = read(ROOT/'audits/concurrency_stop_request.json')
    tests = read(ROOT/'audits/concurrency_override_tests.json')
    created = datetime.fromisoformat(amendment['created_utc'])
    stopped = datetime.fromisoformat(stop['requested_utc'])
    require(stopped < created, 'Concurrency stop request must precede amendment snapshot')
    require(stop['host']=='liekkas' and stop['root']==str(ORIGINAL_ROOT), 'Stop request historical target mismatch')
    require(stop['command']==['python','-u','harness/runner.py','--phase','dev','--part','all','--workers','3'], 'Unexpected original dispatcher command')
    require('parent only' in stop['signal'] and amendment['prior_runner_exit_code']==130, 'Stop provenance is not the reviewed parent-only SIGINT')
    require(amendment['baseline_frozen_sha256']==PREPARATION_FROZEN_SHA256 and amendment['driver_sha256']==CONCURRENCY_PINS['harness/run_concurrency_override.py'], 'Amendment baseline/driver identity')
    require(amendment['schema_version']==1 and amendment['kind']=='dispatch_concurrency_only' and amendment['from_max_workers']==3 and amendment['to_max_workers']==amendment['workers']==12, 'Amendment scope differs from reviewed 3-to-12 change')
    require(tests['driver_sha256']==amendment['driver_sha256'] and tests['offline_only'] is True and tests['real_model_calls']==0, 'Author test artifact scope/driver mismatch')
    require(tests['passed'] is True and tests['tests_run']==5 and tests['errors']==tests['failures']==0, 'Author offline test report records a failure')
    require(datetime.fromisoformat(tests['utc'])<=created, 'Driver test artifact postdates amendment')
    # This checks the author report and its immutable bytes, not an assertion
    # that the independent reviewer reran those harness-importing tests.
    prior = amendment['prior_terminal_records']
    planned = {f"runs/dev/{j['group_id']}/{j['procedure']}/record.json":j for j in jobs}
    require(len(prior)==667 and set(prior)<=set(planned), 'Prior terminal snapshot must contain the reviewed 667 planned tasks')
    require(all(name in prior for name,j in planned.items() if j['procedure']=='P0'), 'All 160 P0 records must predate concurrency change')
    prior_records = {}
    for name, expected in prior.items():
        require(filehash(ROOT/name)==expected, 'Pre-amendment terminal record changed: '+name)
        record = read(ROOT/name)
        require(record['status'] in TERMINAL and record['frozen_hash']==PREPARATION_FROZEN_SHA256, 'Invalid pre-amendment terminal '+name)
        require(datetime.fromisoformat(record['finished_utc'])<=created, 'Snapshot record postdates amendment '+name)
        prior_records[name] = record
    progress_bytes = (ROOT/'runs/dev/progress.jsonl').read_bytes()
    prefix = progress_bytes[:ORIGINAL_PROGRESS_PREFIX_BYTES]
    require(digest(prefix)==ORIGINAL_PROGRESS_PREFIX_SHA256 and prefix.endswith(b'\n'), 'Original pre-amendment progress history was edited')
    # A partial last append can be visible during live preparation. Do not infer
    # completion from it, and never silently ignore it in a final audit.
    lines = progress_bytes.splitlines(keepends=True)
    partial_tail = bool(lines and not lines[-1].endswith(b'\n'))
    require(not final or not partial_tail, 'Progress has an unsealed final line')
    progress = [json.loads(line) for line in (lines[:-1] if partial_tail else lines)]
    times = [datetime.fromisoformat(e['utc']) for e in progress]
    require(times==sorted(times), 'Progress timestamps are out of order')
    allowed_events = {'invocation_started','task_result','task_exception','dispatch_paused','invocation_complete','concurrency_amendment_invocation'}
    require(all(e.get('event') in allowed_events for e in progress), 'Unknown progress event')
    original_events = [json.loads(line) for line in prefix.splitlines()]
    original_logged = {(e['group'],e['procedure']) for e in original_events if e.get('event')=='task_result'}
    omitted = []
    for name, record in prior_records.items():
        if (record['group_id'],record['procedure']) in original_logged: continue
        require(record['attempts'], 'Unlogged pre-amendment task has no raw attempt')
        last = record['attempts'][-1]
        require(datetime.fromisoformat(last['started_utc'])<=stopped<datetime.fromisoformat(last['finished_utc']), 'Unlogged original task was not in flight at parent SIGINT: '+name)
        omitted.append(name)
    require(len(omitted)==3, 'Original progress omission set differs from the three documented in-flight tasks')
    applied_path = ROOT/'audits/concurrency_amendment_applied.json'
    applied = applied_path.exists()
    if applied:
        require(not applied_path.is_symlink() and read(applied_path)=={'amendment_sha256':CONCURRENCY_PINS['protocol/CONCURRENCY_AMENDMENT_2026-11-07.json'],'amendment':amendment}, 'Applied amendment differs from independently pinned amendment')
    invocation_dir = ROOT/'audits/concurrency_invocations'
    invocation_files = sorted(invocation_dir.iterdir()) if invocation_dir.exists() else []
    require(all(p.is_file() and not p.is_symlink() and re.fullmatch(r'[0-9a-f]{32}\.json',p.name) for p in invocation_files), 'Unknown invocation artifact')
    invocations = [read(p) for p in invocation_files]
    marker_events = [(n,e) for n,e in enumerate(progress) if e['event']=='concurrency_amendment_invocation']
    require(len(invocations)==len(marker_events), 'Invocation artifact/progress marker count differs (or live append not yet sealed)')
    require(len({e['utc'] for e in invocations})==len(invocations), 'Duplicate amendment invocation identity')
    for invocation in invocations:
        require(set(invocation)=={'utc','event','amendment_sha256','baseline_frozen_sha256','baseline_max_workers','actual_workers','part','scientific_configuration_changed'}, 'Invocation schema changed')
        require(invocation['event']=='concurrency_amendment_invocation' and invocation['amendment_sha256']==CONCURRENCY_PINS['protocol/CONCURRENCY_AMENDMENT_2026-11-07.json'], 'Invocation amendment hash')
        require(invocation['baseline_frozen_sha256']==PREPARATION_FROZEN_SHA256 and invocation['baseline_max_workers']==3 and invocation['actual_workers']==12 and invocation['scientific_configuration_changed'] is False, 'Invocation changes beyond allowed dispatcher concurrency')
        require(datetime.fromisoformat(invocation['utc'])>=created and invocation['part'] in ('all','P0','review'), 'Invocation time/part')
        matches = [n for n,e in marker_events if e==invocation]
        require(len(matches)==1, 'Invocation lacks a unique exact progress marker')
        next_index = matches[0]+1
        if next_index==len(progress) and not final: continue
        require(next_index<len(progress), 'Amendment marker lacks actual dispatcher start')
        started_event = progress[next_index]
        require(started_event['event']=='invocation_started' and started_event.get('workers')==12 and started_event.get('part')==invocation['part'], 'Invocation marker not followed by matching 12-worker dispatcher')
    starts = [(n,e) for n,e in enumerate(progress) if e['event']=='invocation_started']
    require(starts and starts[0][1]['workers']==3, 'Missing original three-worker invocation')
    for n,e in starts:
        require(e.get('phase')=='dev' and e.get('frozen_hash')==PREPARATION_FROZEN_SHA256, 'Dispatcher progress identity mismatch')
        if e['workers']==3:
            require(datetime.fromisoformat(e['utc'])<stopped, 'Original dispatcher restarted after concurrency stop')
        else:
            require(e['workers']==12 and applied and n>0 and progress[n-1]['event']=='concurrency_amendment_invocation', 'Unrecorded concurrency override')
    require(applied or not invocations, 'Invocation exists without applied amendment evidence')
    if final: require(applied and invocations, 'Final audit requires evidence that the operational amendment was applied')
    marks = sorted((ROOT/'runs/dev').glob('*/*/attempt_*/attempt_started.json'))
    intervals = defaultdict(list)
    new_attempts = 0
    now = datetime.now(timezone.utc)
    for marker_path in marks:
        marker = read(marker_path); ad = marker_path.parent
        started = datetime.fromisoformat(marker['started_utc'])
        name = str((ad.parent/'record.json').relative_to(ROOT))
        require(name in planned, 'Unplanned attempt in amended schedule')
        require(marker['frozen_hash']==PREPARATION_FROZEN_SHA256, 'Attempt switched scientific manifest')
        if started<created:
            require(name in prior and started<=stopped, 'Pre-amendment attempt missing from sealed snapshot or started after stop')
        else:
            new_attempts += 1
            require(name not in prior, 'Pre-amendment terminal task was sampled again')
            require(applied and invocations, 'Post-amendment attempt without application evidence')
        eligible = [(n,e) for n,e in starts if datetime.fromisoformat(e['utc'])<=started]
        require(eligible, 'Attempt predates all dispatcher invocations')
        invocation_index, dispatcher = eligible[-1]
        require((dispatcher['workers']==3)==(started<created), 'Attempt assigned to wrong concurrency phase')
        part = dispatcher['part']
        require(part=='all' or (part=='P0')==(marker['procedure']=='P0'), 'Attempt procedure outside invocation part')
        meta_path = ad/'meta.json'
        if meta_path.exists():
            finished = datetime.fromisoformat(read(meta_path)['finished_utc'])
        else:
            require(not final, 'Final amendment audit found an unsealed attempt')
            finished = now
        require(finished>=started, 'Negative attempt interval')
        intervals[invocation_index].append((started,finished))
    peaks = []
    for n,dispatcher in starts:
        sweep = sorted((time,delta) for begin,end in intervals[n] for time,delta in ((begin,1),(end,-1)))
        active=peak=0
        for _,delta in sweep:
            active+=delta; peak=max(peak,active)
        require(active==0 and peak<=dispatcher['workers'], 'Actual attempt overlap exceeds declared dispatcher workers')
        end_index = next((i for i,_ in starts if i>n),len(progress))
        if end_index<len(progress):
            next_start = datetime.fromisoformat(progress[end_index]['utc'])
            require(all(end<=next_start for _,end in intervals[n]), 'Dispatcher invocations overlap in raw attempt intervals')
        segment = progress[n:end_index]
        closed = any(e['event'] in ('invocation_complete','dispatch_paused','task_exception') for e in segment)
        if final and dispatcher['workers']==12: require(closed, 'Amended dispatcher has no completion/pause/exception provenance')
        peaks.append({'started_utc':dispatcher['utc'],'declared_workers':dispatcher['workers'],'observed_peak_attempts':peak,'attempts':len(intervals[n]),'progress_closed':closed,'original_parent_sigint_exit':dispatcher['workers']==3 and not closed})
    for e in progress:
        if e['event']!='task_result': continue
        name=f"runs/dev/{e.get('group')}/{e.get('procedure')}/record.json"
        require(name in planned, 'Progress references unplanned task')
        require(e.get('status') in TERMINAL | {'paused_service','paused_dispatch'}, 'Unknown task progress status')
        if e['status'] in TERMINAL:
            record=read(ROOT/name)
            require(record['status']==e['status'], 'Task progress status differs from sealed record')
            if record.get('finished_utc'): require(datetime.fromisoformat(e['utc'])>=datetime.fromisoformat(record['finished_utc']), 'Progress result predates terminal record')
    hashes = dict(CONCURRENCY_PINS)
    if applied: hashes[str(applied_path.relative_to(ROOT))]=filehash(applied_path)
    hashes.update({str(p.relative_to(ROOT)):filehash(p) for p in invocation_files})
    return {'status':'applied_observable_evidence_checked' if applied and invocations else 'pending_application',
            'final_audit':final,'kind':'during_run_operational_amendment','baseline_max_workers':3,'amended_max_workers':12,
            'prior_terminal_snapshot_count':len(prior),'post_amendment_attempts_observed':new_attempts,'invocations':peaks,
            'original_progress_prefix_bytes':ORIGINAL_PROGRESS_PREFIX_BYTES,'original_progress_prefix_sha256':ORIGINAL_PROGRESS_PREFIX_SHA256,
            'original_sigint_inflight_tasks_without_original_task_result':sorted(omitted),
            'author_test_report':'Pinned author-supplied offline report/source inspected; not re-executed or treated as independent runtime proof.',
            'initial_stop_request_workers_note':'Stop request recorded a proposed 3-to-6 increase; later amendment explicitly superseded it with 3-to-12. No six-worker invocation is allowed by this audit.',
            'operational_limits':amendment['operational_limits'],'input_hashes':hashes,
            'interpretation':'Scientific source hash preservation does not make the concurrency change pre-registered. Timing/resource observations mix operational phases; no causal speedup or unchanged service-load claim.'}


def scan_runs(jobs):
    """Allowlist the entire runs tree, not just planned record paths."""
    allowed = {'dev'}
    allowed |= {'dev/'+n for n in ('.integrity.lock','plan.csv','manifest_identity.json','progress.jsonl')}
    for j in jobs:
        group = 'dev/'+j['group_id']; task = group+'/'+j['procedure']
        allowed |= {group, task, task+'/prompt.txt', task+'/record.json'}
        for n in (1,2):
            ad = task+f'/attempt_{n:02d}'
            allowed.add(ad)
            allowed |= {ad+'/'+f for f in ('attempt_started.json','events.jsonl','stderr.txt','response.json','meta.json')}
    paths = sorted((ROOT/'runs').rglob('*'))
    unknown = [str(p.relative_to(ROOT)) for p in paths if p.is_symlink() or str(p.relative_to(ROOT/'runs')) not in allowed]
    raw_names = {'record.json','events.jsonl','response.json','attempt_started.json'}
    trace_events = ROOT/'.aris/meta/events.jsonl'
    if trace_events.exists():
        trace_rows = [json.loads(line) for line in trace_events.read_text().splitlines() if line.strip()]
        trace_keys = {'event','skill','purpose','agent_id','trace_path','status','verdict','timestamp'}
        require(all(isinstance(e,dict) and e.get('event')=='review_trace' and set(e)<=trace_keys for e in trace_rows), 'Review-trace event file contains unexpected/raw-event content')
    outside = [str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
               if 'runs' != p.relative_to(ROOT).parts[0] and p!=trace_events and
               (p.name in raw_names or (p.is_dir() and re.fullmatch(r'attempt_\d+',p.name)))]
    require(not outside, 'Raw task/attempt evidence outside accounted runs tree: '+repr(outside))
    empty = ROOT/'runtime_empty'
    require(not empty.exists() or (empty.is_dir() and not any(empty.iterdir())), 'Subject runtime directory contains contextual files')
    require(not unknown, 'Unplanned/symlink run artifacts: '+repr(unknown))
    return {'observed_paths': len(paths), 'observed_record_files': sum(p.name == 'record.json' for p in paths),
            'observed_attempt_directories': sum(p.is_dir() and p.name.startswith('attempt_') for p in paths),
            'observed_started_attempt_files': sum(p.name == 'attempt_started.json' for p in paths),
            'observed_sealed_attempt_files': sum(p.name == 'meta.json' for p in paths), 'unplanned_artifacts': []}


def json_answer(text):
    try:
        x = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(x, dict) or set(x) != {'action','cited_sources','brief_justification','confidence'}:
        return None
    valid_number = type(x['confidence']) in (int,float) and 1 <= x['confidence'] <= 5 and int(x['confidence']) == x['confidence']
    if (x['action'] not in ('A','B','C','D') or not isinstance(x['cited_sources'],list) or
        not all(isinstance(v,str) for v in x['cited_sources']) or not isinstance(x['brief_justification'],str) or
        len(x['brief_justification']) > 180 or not valid_number):
        return None
    return x


def event_evidence(text):
    """Rebuild observable protocol facts, with no runner/evaluator imports."""
    stream = []; unknown = []; sessions = []; turns = []; life = []; messages = []; fatal = []; error_items = []
    names = {'thread.started','turn.started','item.started','item.updated','item.completed','turn.completed','turn.failed','error'}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            unknown.append('non-JSON stdout'); continue
        stream.append(e)
        if not isinstance(e,dict):
            unknown.append('non-object event'); continue
        t = e.get('type')
        if t not in names: unknown.append('unknown event '+str(t))
        if t in ('thread.started','turn.started','turn.completed','turn.failed'): life.append(t)
        if t == 'thread.started': sessions.append(e.get('thread_id'))
        if t == 'turn.completed': turns.append(e.get('usage'))
        if t in ('error','turn.failed'): fatal.append(e)
        item = e.get('item',{})
        if not isinstance(item,dict): unknown.append('non-object item'); continue
        if item and item.get('type') not in ('agent_message','reasoning','error'): unknown.append('tool/unknown item '+str(item.get('type')))
        if item.get('type') == 'error': error_items.append(item)
        if t == 'item.completed' and item.get('type') == 'agent_message' and isinstance(item.get('text'),str) and item['text'].strip(): messages.append(item['text'])
    valid_life = len(sessions) == 1 and isinstance(sessions[0],str) and bool(sessions[0].strip()) and life == ['thread.started','turn.started','turn.completed']
    if turns and not valid_life: unknown.append('invalid success lifecycle')
    return dict(usage=turns[0] if len(turns)==1 else None, thread_ids=sessions, turn_completed=bool(turns),
                turn_completion_usages=turns, lifecycle_events=life, completed_agent_messages=messages,
                top_level_errors=fatal, error_items=error_items, event_count=len(stream), valid_lifecycle=valid_life, unexpected=unknown)


def resources(usages):
    values = {k: [(u.get(k) if isinstance(u,dict) and type(u.get(k)) is int and u[k] >= 0 else None) for u in usages] for k in ('input_tokens','output_tokens')}
    out = {}
    for field, vals in values.items():
        count = sum(v is None for v in vals)
        known = sum(v for v in vals if v is not None)
        out['sum_'+field] = None if count else known
        out['known_'+field] = known
        out[field.split('_')[0]+'_usage_missing_attempts'] = count
    out['usage_missing_attempts'] = sum(a is None or b is None for a,b in zip(values['input_tokens'],values['output_tokens']))
    return out


def independent_service_reason(meta, ev, stderr):
    """Transport-only classification; deliberately never inspect answer text."""
    if meta['returncode'] == 0 and ev['turn_completed'] and not ev['top_level_errors']:
        return None
    text = (json.dumps(ev['top_level_errors']+ev['error_items'],ensure_ascii=False)+' '+stderr+' '+(meta.get('error') or '')).lower()
    patterns = [
        ('quota_or_rate_limit',r'usage limit|quota|rate.?limit|too many requests|insufficient_quota|usage_limit_reached|\b429\b|credits? (?:exhausted|depleted)|limit reached|用量限制|额度|配额'),
        ('network_transport',r'\btls\b|\bssl\b|unexpected eof|connection (?:reset|refused|aborted|closed|timed out)|network (?:is )?unreachable|network error|error sending request|name resolution|dns (?:error|failure)|stream disconnected|failed to connect|could not connect|connecterror|timeout_600s'),
        ('authentication',r'authenticat|unauthorized|invalid.api.key|token (?:expired|invalid)|refresh.token|not logged in|login required|sign in|\b401\b|\b403\b|登录|认证'),
    ]
    return next((name for name,pattern in patterns if re.search(pattern,text)),None)


def rebuild_attempt(ad, identity, number):
    meta = read(ad/'meta.json'); start = read(ad/'attempt_started.json')
    require(meta['attempt'] == start['attempt'] == number, str(ad)+': attempt index')
    for field, value in identity.items():
        require(start.get(field) == value, str(ad)+': start identity '+field)
    for obj in (meta,start):
        require(obj['model_requested'] == 'gpt-6-astra' and obj['effort_requested'] == 'ultra' and obj['prompt_sha256'] == identity['prompt_sha256'], str(ad)+': request identity')
    for name, field in [('attempt_started.json','started_sha256'),('events.jsonl','stdout_sha256'),('stderr.txt','stderr_sha256')]:
        require(filehash(ad/name) == meta[field], str(ad)+': raw hash '+name)
    output = ad/'response.json'
    require(output.exists() == (meta.get('output_sha256') is not None), str(ad)+': response existence')
    if output.exists(): require(filehash(output) == meta['output_sha256'], str(ad)+': response hash')
    ev = event_evidence((ad/'events.jsonl').read_text())
    for field in ('usage','thread_ids','turn_completed','turn_completion_usages','lifecycle_events','completed_agent_messages','top_level_errors','error_items','event_count'):
        require(meta.get(field) == ev[field], str(ad)+': derived event metadata '+field)
    require(bool(meta.get('unexpected_items')) == bool(ev['unexpected']), str(ad)+': event anomaly classification')
    require(bool(meta.get('lifecycle_errors')) == (not ev['valid_lifecycle']), str(ad)+': lifecycle metadata')
    require(meta.get('service_block') == independent_service_reason(meta,ev,(ad/'stderr.txt').read_text()), str(ad)+': raw transport failure classification')
    raw_output = output.read_text() if output.exists() else None
    final = raw_output if raw_output and raw_output.strip() else ev['completed_agent_messages'][-1] if ev['completed_agent_messages'] else raw_output
    if output.exists() and raw_output.strip() and ev['completed_agent_messages']:
        require(raw_output.strip() == ev['completed_agent_messages'][-1].strip(), str(ad)+': file final differs from last raw agent message')
    require(not ev['unexpected'], str(ad)+': tool/event contamination '+repr(ev['unexpected']))
    if final and final.strip(): require(ev['valid_lifecycle'], str(ad)+': final has invalid session/turn lifecycle')
    parsed = None
    if not final or not final.strip(): status = 'technical_failure'
    elif meta.get('output_sha256') is None or meta['returncode'] != 0 or not ev['turn_completed'] or ev['top_level_errors']: status = 'technical_failure'
    else:
        parsed = json_answer(final)
        status = 'complete' if parsed is not None else 'parse_failure'
    started, finished = datetime.fromisoformat(meta['started_utc']), datetime.fromisoformat(meta['finished_utc'])
    require(started == datetime.fromisoformat(start['started_utc']) and finished >= started, str(ad)+': attempt times')
    require(type(meta['seconds']) in (int,float) and math.isfinite(meta['seconds']) and meta['seconds'] >= 0, str(ad)+': elapsed time')
    require(abs((finished-started).total_seconds()-meta['seconds']) < 5, str(ad)+': wall/elapsed discrepancy')
    require(started > datetime.fromisoformat(read(ROOT/'protocol/frozen.json')['created_utc']), str(ad)+': execution predates freeze')
    return {'meta': meta, 'events': ev, 'final': final, 'status': status, 'parsed': parsed, 'started': started, 'finished': finished, 'path': str(ad.relative_to(ROOT))}


def prompt_for(job, item, first, templates):
    text = templates['base']+'\n\n档案与问题：\n'+item['public_text']
    if first is None: return text+'\n\n本次任务：给出你的决定。'
    return text+'\n\n先前回答（原样提供，供独立复核）：\n'+first+'\n\n本次任务：\n'+templates['reviews'][job['procedure']]


def rebuild_tasks(items, oracles, jobs):
    templates = read(ROOT/'protocol/prompts.json')
    rows = []; evidence = {}; attempts = []; sessions = []; failure_logs = []; warning_messages = Counter()
    ordered = sorted(jobs, key=lambda j: (j['procedure'] != 'P0', j['group_id'],j['procedure']))
    for job in ordered:
        iid, gid, proc = job['item_id'], job['group_id'],job['procedure']
        path = ROOT/'runs/dev'/gid/proc; rec = read(path/'record.json')
        require(rec.get('status') in TERMINAL, str(path)+': not terminal')
        for field, value in {**job, 'phase':'dev', 'frozen_hash': PREPARATION_FROZEN_SHA256}.items(): require(rec.get(field) == value, str(path)+': record identity '+field)
        first = None if proc == 'P0' else evidence[(gid,'P0')]['final']
        first_status = None if proc == 'P0' else evidence[(gid,'P0')]['status']
        local = []
        if not rec.get('attempts'):
            require(proc != 'P0' and first_status not in ('complete','parse_failure'), str(path)+': unjustified skipped review')
            expected = {**job,'phase':'dev','status':'not_run_first_failed','frozen_hash':PREPARATION_FROZEN_SHA256,'first_sha256':None,'attempts':[],'parsed':None}
            require(rec == expected and set(p.name for p in path.iterdir()) == {'record.json'}, str(path)+': invalid no-attempt record')
            status, parsed, final = 'not_run_first_failed', None, None
        else:
            require(proc == 'P0' or first_status in ('complete','parse_failure'), str(path)+': review used failed P0')
            prompt = prompt_for(job, items[iid], first, templates)
            first_hash = None if first is None else digest(first)
            identity = {**job,'phase':'dev','frozen_hash':PREPARATION_FROZEN_SHA256,'first_sha256':first_hash,'prompt_sha256':digest(prompt)}
            require((path/'prompt.txt').read_text() == prompt, str(path)+': exact prompt mismatch')
            require(all(rec.get(k) == v for k,v in identity.items()), str(path)+': record prompt/source hash')
            require(1 <= len(rec['attempts']) <= 2, str(path)+': retry budget')
            require({p.name for p in path.glob('attempt_*')} == {f'attempt_{i:02d}' for i in range(1,len(rec['attempts'])+1)}, str(path)+': hidden or missing attempt')
            for number, recorded in enumerate(rec['attempts'], 1):
                ad = path/f'attempt_{number:02d}'
                attempt = rebuild_attempt(ad,identity,number)
                require(attempt['meta'] == recorded, str(ad)+': record/meta mismatch')
                if local:
                    prior = local[-1]
                    require(not (prior['final'] and prior['final'].strip()) and not prior['events']['unexpected'], str(ad)+': returned answer/protocol error was resampled')
                    require(attempt['started'] >= prior['finished'], str(ad)+': overlapping retries')
                local.append(attempt); attempts.append(attempt)
                sessions.extend(attempt['events']['thread_ids'])
                for w in attempt['events']['error_items']: warning_messages[w.get('message','')] += 1
                if attempt['status'] != 'complete':
                    failure_logs.append({'path':attempt['path'],'status':attempt['status'],'stderr_bytes':(ad/'stderr.txt').stat().st_size,'raw_final_present':bool(attempt['final'] and attempt['final'].strip()),'usage':attempt['events']['usage']})
            last = local[-1]; status, parsed, final = last['status'],last['parsed'],last['final']
            require(datetime.fromisoformat(rec['finished_utc']) >= last['finished'], str(path)+': terminal record predates last attempt')
            require(rec['status'] == status and rec['parsed'] == parsed, str(path)+': raw-derived terminal/answer mismatch')
            require(rec.get('raw_final') == (final if final and final.strip() else None), str(path)+': exact final differs')
            require(rec.get('final_sha256') == (digest(final) if final and final.strip() else None), str(path)+': final hash differs')
        evidence[(gid,proc)] = {'status':status,'parsed':parsed,'final':final,'attempts':local}
        u = resources([a['events']['usage'] for a in local]); oracle = oracles[iid]
        rows.append({**job,'family_id':items[iid]['family_id'],'state':items[iid]['state'],'advice':items[iid]['advice'],
                     'error_type':'material' if items[iid]['family_id'][0]=='M' else 'rule','status':status,'correct_action':oracle['action'],
                     'action':parsed['action'] if parsed else '', 'correct':int(status=='complete' and parsed['action']==oracle['action']),
                     'parse_ok':int(parsed is not None),'pause_action':oracle['pause_action'],'first_sha256':rec.get('first_sha256') or '',
                     'attempts':len(local),'seconds':sum(a['meta']['seconds'] for a in local), **u,
                     'input_tokens':u['sum_input_tokens'] if local and u['sum_input_tokens'] is not None else '',
                     'output_tokens':u['sum_output_tokens'] if local and u['sum_output_tokens'] is not None else ''})
    require(all(isinstance(s,str) and s.strip() for s in sessions), 'Invalid session ID')
    require(len(sessions) == len(set(sessions)), 'Session reused across attempts/tasks')
    p0_finished = [datetime.fromisoformat(read(ROOT/'runs/dev'/j['group_id']/'P0/record.json')['finished_utc']) for j in jobs if j['procedure']=='P0']
    review_starts = [a['started'] for (g,p),e in evidence.items() if p!='P0' for a in e['attempts']]
    require(not review_starts or min(review_starts) >= max(p0_finished), 'Reviews began before all 160 P0 terminal records')
    return rows, attempts, sessions, failure_logs, warning_messages


def selected(row, stratum):
    return stratum=='all' or (stratum=='present_flawed' and row['state']!='missing' and row['advice']=='flawed') or (stratum=='aligned' and row['advice']=='aligned') or (stratum=='missing' and row['state']=='missing')


def independent_statistics(rows, attempts, sessions):
    indexed = {(r['group_id'],r['procedure']):r for r in rows}
    groups = sorted({r['group_id'] for r in rows})
    natural = [g for g in groups if indexed[(g,'P0')]['state']!='missing' and indexed[(g,'P0')]['status']=='complete' and not indexed[(g,'P0')]['correct']]
    initially_right = [g for g in groups if indexed[(g,'P0')]['state']!='missing' and indexed[(g,'P0')]['correct']]
    family = []; procedures = {}
    for p in PROCS:
        subset = [r for r in rows if r['procedure']==p]
        u = resources([a['events']['usage'] for a in attempts if a['path'].split('/')[3]==p])
        repaired = sum(indexed[(g,p)]['correct'] for g in natural)
        damaged = sum(1-indexed[(g,p)]['correct'] for g in initially_right)
        procedures[p] = {'planned':len(subset),'complete':sum(r['status']=='complete' for r in subset),'correct':sum(r['correct'] for r in subset),
                         'accuracy':sum(r['correct'] for r in subset)/len(subset),'present_flawed_correct':sum(r['correct'] for r in subset if selected(r,'present_flawed')),
                         'present_flawed_n':sum(selected(r,'present_flawed') for r in subset),'missing_correct':sum(r['correct'] for r in subset if r['state']=='missing'),
                         'missing_n':sum(r['state']=='missing' for r in subset),'natural_first_errors':len(natural),
                         'families_with_first_errors':sorted({indexed[(g,'P0')]['family_id'] for g in natural}),
                         'repaired':repaired if p!='P0' else None,'repair_rate':rate(repaired,len(natural)) if p!='P0' else None,
                         'first_correct_present':len(initially_right),'damaged':damaged if p!='P0' else None,
                         'damage_rate':rate(damaged,len(initially_right)) if p!='P0' else None,
                         **u,'input_tokens':u['sum_input_tokens'],'output_tokens':u['sum_output_tokens'],
                         'usage_known_tasks':sum(type(r['input_tokens']) is int and type(r['output_tokens']) is int for r in subset),'seconds':sum(r['seconds'] for r in subset)}
    for f in FAMILIES:
        for p in PROCS:
            subset = [r for r in rows if r['family_id']==f and r['procedure']==p]
            family.append({'family_id':f,'error_type':'material' if f[0]=='M' else 'rule','procedure':p,'planned':len(subset),
                           'complete':sum(r['status']=='complete' for r in subset),'correct':sum(r['correct'] for r in subset),
                           'present_flawed_n':sum(selected(r,'present_flawed') for r in subset),
                           'present_flawed_correct':sum(r['correct'] for r in subset if selected(r,'present_flawed'))})
    def contrast(treat, control, stratum='present_flawed', paired=False):
        frows = []
        for f in FAMILIES:
            eligible = [g for g in groups if indexed[(g,'P0')]['family_id']==f and selected(indexed[(g,'P0')],stratum)]
            if paired: eligible = [g for g in eligible if all(indexed[(g,p)]['status']=='complete' for p in ('P0',treat,control))]
            delta = [indexed[(g,treat)]['correct']-indexed[(g,control)]['correct'] for g in eligible]
            frows.append({'family_id':f,'error_type':'material' if f[0]=='M' else 'rule','paired_groups':len(delta),'difference':average(delta)})
        values = {k:[f['difference'] for f in frows if f['error_type']==k and f['difference'] is not None] for k in ('material','rule')}
        means = {k:average(v) for k,v in values.items()}
        return {'estimate':None if None in means.values() else means['rule']-means['material'],'type_mean_difference':means,
                'available_families_by_type':{k:len(v) for k,v in values.items()},'families':frows,
                'type_family_difference_range':{k:[min(v),max(v)] if v else None for k,v in values.items()}}
    i78, i73, p31 = contrast('P7','P8'),contrast('P7','P3'),contrast('P3','P1')
    within = {name:{k:v for k,v in obj.items() if k!='estimate'} for name,obj in [('P7-P8',i78),('P7-P3',i73),('P3-P1',p31)]}
    bytype = {}
    for kind in ('material','rule'):
        first = [r for r in rows if r['procedure']=='P0' and r['error_type']==kind]
        flawed = [r for r in first if selected(r,'present_flawed')]
        aligned = [r for r in first if r['state']!='missing' and r['advice']=='aligned']
        missing = [r for r in first if r['state']=='missing']
        errors = [r for r in flawed if r['status']=='complete' and not r['correct']]
        bytype[kind] = {'present_flawed_planned':len(flawed),'present_flawed_correct':sum(r['correct'] for r in flawed),'present_flawed_completed':sum(r['status']=='complete' for r in flawed),
                        'present_flawed_natural_errors':len(errors),'error_families':sorted({r['family_id'] for r in errors}),
                        'aligned_present_planned':len(aligned),'aligned_present_correct':sum(r['correct'] for r in aligned),'missing_planned':len(missing),'missing_correct':sum(r['correct'] for r in missing)}
    first_present = [r for r in rows if r['procedure']=='P0' and r['state']!='missing']
    diagnostic = {'by_type':bytype,'P0_present_planned':len(first_present),'P0_present_completed':sum(r['status']=='complete' for r in first_present),
                  'natural_first_errors':len(natural),'families_with_first_errors':sorted({indexed[(g,'P0')]['family_id'] for g in natural}),
                  'zero_observed_natural_errors':len(natural)==0,'complete_P0_present_ceiling':all(r['status']=='complete' for r in first_present) and not natural}
    return {'planned_tasks':len(rows),'actual_cli_attempts':len(attempts),'unique_sessions':len(set(sessions)),
            'complete_tasks':sum(r['status']=='complete' for r in rows),'status_counts':dict(Counter(r['status'] for r in rows)),
            **resources([a['events']['usage'] for a in attempts]),'usage_known_tasks':sum(type(r['input_tokens']) is int and type(r['output_tokens']) is int for r in rows),
            'procedures':procedures,'family_results':family,'primary_interactions':{'I78':i78},'secondary_interaction_I73':i73,'within_type_contrasts':within,
            'complete_pair_sensitivity':{'I78':contrast('P7','P8',paired=True),'I73':contrast('P7','P3',paired=True)},
            'secondary_interactions':{s:{'I78':contrast('P7','P8',s),'I73':contrast('P7','P3',s)} for s in ('all','aligned','missing')},
            'difficulty_diagnostic':diagnostic,'planned_groups':len(groups),
            'complete_groups':sum(all(indexed[(g,p)]['status']=='complete' for p in PROCS) for g in groups),'family_counts_by_type':{'material':4,'rule':4}}


def compare(expected, actual, location='summary'):
    """Expected subset comparison permits original explanatory text, not missing metrics."""
    if isinstance(expected,dict):
        require(isinstance(actual,dict), location+': expected object')
        for k,v in expected.items():
            require(k in actual, location+': missing '+k)
            compare(v,actual[k],location+'.'+k)
    elif isinstance(expected,list):
        require(isinstance(actual,list) and len(expected)==len(actual), location+': list length')
        for n,(a,b) in enumerate(zip(expected,actual)): compare(a,b,location+f'[{n}]')
    elif type(expected) is float:
        require(type(actual) in (int,float) and math.isclose(expected,actual,rel_tol=1e-12,abs_tol=1e-12), location+': numeric mismatch')
    else:
        require(expected == actual and (expected is not None or actual is None), location+': mismatch '+repr((expected,actual)))


def compare_csv(expected_rows, path, identity):
    actual = load_csv(path)
    keyed = {tuple(r[k] for k in identity):r for r in actual}
    require(len(actual) == len(keyed) == len(expected_rows), str(path)+': row count/duplicates')
    for row in expected_rows:
        key = tuple(str(row[k]) for k in identity)
        require(key in keyed, str(path)+': missing row '+repr(key))
        require(set(row) == set(keyed[key]), str(path)+': column set differs')
        for field,value in row.items():
            got = keyed[key][field]
            if type(value) is float:
                require(math.isclose(float(got),value,rel_tol=1e-12,abs_tol=1e-12), str(path)+': number mismatch '+str((key,field)))
            else:
                require(got == ('' if value is None else str(value)), str(path)+': value mismatch '+str((key,field,value,got)))


def compare_run_inventory(inventory, original_inventory):
    """Reconcile only the declared process-lock omission in an explicit archive.

    Never adjust the observed inventory or the historical evidence in place.
    A pinned original audit supplies the complete historical runs file set and
    hashes, so an equal path count cannot conceal a substituted or missing file.
    The regular scan_runs allowlist still rejects every unknown/symlink path.
    """
    lock = ROOT/DECLARED_ARCHIVE_OMISSION
    if not ARCHIVE_MODE or lock.exists() or lock.is_symlink():
        compare(inventory,original_inventory,'integrity.run_inventory')
        return None
    reference_path = ROOT/'audits/INDEPENDENT_FINAL_AUDIT.json'
    require(filehash(reference_path) == ORIGINAL_FINAL_AUDIT_SHA256,
            'Archive lock omission requires the unchanged pinned original final audit')
    reference = read(reference_path)
    compare(original_inventory,reference['run_inventory'],'archive.historical_run_inventory')
    historical = {p:h for p,h in reference['audited_input_hashes'].items() if p.startswith('runs/')}
    require(DECLARED_ARCHIVE_OMISSION in historical, 'Pinned historical inventory lacks the declared lock')
    current = {str(p.relative_to(ROOT)):filehash(p) for p in (ROOT/'runs').rglob('*') if p.is_file()}
    require(set(historical)-set(current) == {DECLARED_ARCHIVE_OMISSION} and not set(current)-set(historical),
            'Archive omissions/additions differ from the sole declared process lock')
    require(all(historical[p] == h for p,h in current.items()), 'Archive runs bytes differ from pinned historical evidence')
    expected = dict(original_inventory)
    expected['observed_paths'] -= 1
    compare(inventory,expected,'archive.run_inventory_excluding_declared_lock')
    return {'status':'verified_declared_runtime_lock_omission',
            'declaration':'Only runs/dev/.integrity.lock may be absent in explicit archive mode',
            'omitted_paths':[DECLARED_ARCHIVE_OMISSION],
            'historical_omitted_sha256':historical[DECLARED_ARCHIVE_OMISSION],
            'historical_observed_paths':original_inventory['observed_paths'],
            'archive_observed_paths':inventory['observed_paths'],
            'historical_run_files':len(historical),'archive_run_files':len(current),
            'reference_manifest':'audits/INDEPENDENT_FINAL_AUDIT.json',
            'reference_manifest_sha256':ORIGINAL_FINAL_AUDIT_SHA256,
            'restored_experiment_execution':False}


def final_audit(prepared):
    frozen, items, keys, oracles, jobs = prepared
    missing = [str(ROOT/'runs/dev'/j['group_id']/j['procedure']/'record.json') for j in jobs if not (ROOT/'runs/dev'/j['group_id']/j['procedure']/'record.json').is_file()]
    absent = [name for name in REQUIRED_ANALYSIS if not (ROOT/'analysis/dev'/name).is_file()]
    require(not missing and not absent, f'FINAL AUDIT BLOCKED: {len(missing)} of 800 terminal records absent; missing analysis: {absent}. No final report written.')
    # Snapshot all primary inputs before/after audit; active writes invalidate it.
    amendment_paths = [ROOT/p for p in CONCURRENCY_PINS] + [ROOT/'audits/concurrency_amendment_applied.json'] + sorted((ROOT/'audits/concurrency_invocations').glob('*.json'))
    require(all(p.is_file() for p in amendment_paths), 'Final audit lacks operational amendment evidence')
    primary = sorted(p for p in (ROOT/'runs').rglob('*') if p.is_file()) + [ROOT/'analysis/dev'/n for n in REQUIRED_ANALYSIS] + amendment_paths
    before = {str(p.relative_to(ROOT)):filehash(p) for p in primary}
    operational = audit_concurrency_amendment(jobs,final=True)
    inventory = scan_runs(jobs)
    require(inventory['observed_record_files'] == 800, 'Terminal record inventory is not 800')
    rows, attempts, sessions, failure_logs, warning_messages = rebuild_tasks(items,oracles,jobs)
    require(inventory['observed_attempt_directories'] == inventory['observed_started_attempt_files'] == inventory['observed_sealed_attempt_files'] == len(attempts), 'Attempt inventory not fully accounted')
    result = independent_statistics(rows,attempts,sessions)
    compare_csv(rows,ROOT/'analysis/dev/scored_runs.csv',('group_id','procedure'))
    compare_csv(result['family_results'],ROOT/'analysis/dev/family_results.csv',('family_id','procedure'))
    original = read(ROOT/'analysis/dev/summary.json')
    compare(result,original)
    require(original.get('passed_integrity') is True and original.get('verified_billed_cost') is None, 'Original integrity/cost statement mismatch')
    integ = read(ROOT/'analysis/dev/integrity_audit.json')
    require(integ.get('frozen_hash') == PREPARATION_FROZEN_SHA256 and integ.get('phase') == 'dev', 'Original audit identity')
    for name in ('record_errors','unusual_item_types','duplicate_session_ids','paused_tasks','unsealed_attempts','lifecycle_errors'):
        require(integ.get(name) == [], 'Original audit nonempty/missing '+name)
    archive_reconciliation = compare_run_inventory(inventory,integ['run_inventory'])
    require(all(filehash(ROOT/p)==h for p,h in before.items()), 'Primary artifacts changed during audit; rerun only after execution/analysis stop')
    require(filehash(ROOT/'protocol/frozen.json') == PREPARATION_FROZEN_SHA256 and all(filehash(ROOT/p)==h for p,h in frozen['sha256'].items()), 'Frozen sources changed during audit')
    require({str(p.relative_to(ROOT)) for p in (ROOT/'runs').rglob('*') if p.is_file()} == {p for p in before if p.startswith('runs/')}, 'Run inventory changed during audit')
    require({str(p.relative_to(ROOT)) for p in (ROOT/'audits/concurrency_invocations').glob('*.json')} == {p for p in before if p.startswith('audits/concurrency_invocations/')}, 'Operational invocation inventory changed during audit')
    return {'audit_skill':'experiment-audit','review_independence':'same-family','acceptance_status':'provisional',
            'audit_status':'completed','overall_verdict':'WARN','deterministic_integrity':'PASS','evaluation_type':'simulation_only',
            'scope_limits':LIMITS,'generated_utc':datetime.now(timezone.utc).isoformat(),'root':str(ROOT),'hostname':socket.gethostname(),
            'target_mode':'archive_evidence_only' if ARCHIVE_MODE else 'original_target_read_only',
            'historical_runtime_identity':frozen['runtime'],'restored_experiment_execution':False,
            'local_cli_byte_identity_checked':not ARCHIVE_MODE,
            'frozen_sha256':PREPARATION_FROZEN_SHA256,'audited_input_hashes':{**frozen['sha256'],**before},
            'independent_oracle_items':len(oracles),'recomputed':result,'run_inventory':inventory,'retained_failure_attempts':failure_logs,
            'archive_inventory_reconciliation':archive_reconciliation,
            'operational_amendment':operational,
            'runtime_warning_counts':dict(warning_messages),'notes':['No scoring/runner code imported or executed.','Every accuracy denominator includes planned failures; repair excludes technical/format P0 failures and missing-evidence items.','Null repair/damage or unavailable usage values are not converted to zero.','No significance, equivalence, general population superiority or internal cognition claim follows from arithmetic agreement.']}


def main():
    global ROOT, ARCHIVE_MODE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-check',action='store_true')
    parser.add_argument('--final',action='store_true')
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--archive-root',type=Path,help='Explicit archive path; verify historical evidence, not original-host execution')
    args = parser.parse_args()
    if args.archive_root is not None:
        ROOT = args.archive_root.expanduser().resolve(strict=True)
        ARCHIVE_MODE = True
    require(args.prepare_check != args.final, 'Choose exactly one of --prepare-check or --final')
    require(not args.write or args.final, '--write is final-audit only')
    try:
        prepared = prepare()
        if args.prepare_check:
            operational = audit_concurrency_amendment(prepared[4],final=False)
            print(json.dumps({'status':'PREPARATION_ONLY','frozen_input_check':'verified','public_rule_oracle_items':len(prepared[3]),'planned_tasks':len(prepared[4]),'operational_amendment_status':operational['status'],'audited_root':str(ROOT),'target_mode':'archive_evidence_only' if ARCHIVE_MODE else 'original_target_read_only','local_cli_byte_identity_checked':not ARCHIVE_MODE,'restored_experiment_execution':False,'final_audit_performed':False,'model_calls':0,'review_independence':'same-family','acceptance_status':'provisional'},ensure_ascii=False))
            return
        report = final_audit(prepared)
        if args.write:
            destination = ROOT/'audits/INDEPENDENT_FINAL_AUDIT.json'
            # Never silently overwrite a previous audit; follow-up review must
            # inspect it and select a deliberate new path in a reviewed revision.
            with destination.open('x') as stream:
                json.dump(report,stream,ensure_ascii=False,indent=2); stream.write('\n')
        print(json.dumps({k:report[k] for k in ('audit_status','overall_verdict','deterministic_integrity','review_independence','acceptance_status','root','target_mode','restored_experiment_execution','archive_inventory_reconciliation')},ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'audit_status':'BLOCKED_OR_ERROR','reason':str(exc),'final_report_written':False},ensure_ascii=False))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
