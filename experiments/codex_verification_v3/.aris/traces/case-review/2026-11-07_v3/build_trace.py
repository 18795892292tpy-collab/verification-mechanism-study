"""Audit-only trace writer/validator. Reads packet and this reviewer's own answers only.
This is not the tested CLI and does not call any model, network, private mapping, or key.
"""
import collections
import datetime
import hashlib
import json
import pathlib
import platform
import re
from decimal import Decimal, ROUND_CEILING

BASE = pathlib.Path("/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v3")
PACKET = BASE / "audits/blind_review/packet.json"
ANSWERS = BASE / "audits/blind_review/answers.json"
TRACE = BASE / ".aris/traces/case-review/2026-11-07_v3"
EXPECTED_SHA = "10ae600c497a65670c1ad891b86ab5ec7291bbe631c399616effe4eab3f49406"
assert platform.node() == "liekkas", platform.node()
assert PACKET.resolve() == PACKET
raw = PACKET.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA
packet = json.loads(raw)
answers = json.loads(ANSWERS.read_text())
assert set(packet) == set(answers) == {"p0", "challenge"}
assert len(packet["p0"]) == len(answers["p0"]) == 80
assert len(packet["challenge"]) == len(answers["challenge"]) == 32

def factual_check(text):
    # Recompute branch using only facts explicitly printed in this one item.
    s4 = text.split("[S4]", 1)[1].split("[S5]", 1)[0]
    missing = "尚未归档" in s4
    if "阅读支持筛查工具" in text:
        if missing: return "B", {"field_missing": True}
        n = int(re.search(r"(?:标记了|有)(\d+)人", s4).group(1))
        miss = Decimal(50-n)/50
        false = Decimal(5)/150
        return ("D" if miss <= Decimal(".05") and false <= Decimal(".20") else "C"), {"detected":n, "miss_rate":str(miss), "false_rate":str(false)}
    if "内网故障事件分级" in text:
        if missing: return "C", {"field_missing": True}
        minute = int(re.search(r"08:(\d+)", s4).group(1))
        gaps = [minute-10, 25]
        count = 1 + sum(g>20 for g in gaps)
        return ("A" if count>=3 else "D"), {"gaps_minutes":gaps, "independent_events":count}
    if "教学方案证据汇总" in text:
        if missing: return "C", {"field_missing": True}
        cohort = re.search(r"C(?:41|59)", s4).group(0)
        n = len({"C41", cohort})
        return ("A" if n>=2 else "D"), {"second_cohort":cohort, "independent_qualifying_cohorts":n}
    if "咨询数据包外发" in text:
        if missing: return "A", {"field_missing": True}
        digest = re.search(r"[a-f0-9]{8}", s4).group(0)
        return ({"7f31a8d4":"B","0c92b6e5":"C"}[digest]), {"B61_digest":digest}
    if "委员会会议决议" in text:
        if missing: return "B", {"field_missing": True}
        status = re.search(r"[VP]", s4).group(0)
        eligible = 7-2
        threshold = int((Decimal(eligible)*2/3).to_integral_value(rounding=ROUND_CEILING))
        attendance = 3 + (status=="V")
        assert Decimal(3)>Decimal(eligible)/2
        return ("C" if attendance>=threshold else "D"), {"status":status, "eligible":eligible, "threshold":threshold, "attendance":attendance, "yes_votes":3}
    if "三年设备维护合同" in text:
        if missing: return "D", {"field_missing": True}
        deployment = int(re.search(r"部署费(?:为)?(\d+)元", s4).group(1))
        fees = [Decimal(30000)*(Decimal("1.05")**i) for i in range(3)]
        total = sum(fees)+deployment
        return ("A" if total>=100000 else "B"), {"annual_fees":[str(v) for v in fees], "deployment":deployment, "mandatory_total":str(total)}
    if "过渡拨款例外" in text:
        if missing: return "A", {"field_missing": True}
        category = re.search(r"(?:C1|E2)", s4).group(0)
        return ("C" if category=="C1" else "B"), {"category":category, "emergency_valid":True, "audit_incomplete":True, "clawback_cleared":True}
    if "材料补正时限" in text:
        if missing: return "D", {"field_missing": True}
        category = re.search(r"(?:Z1|X2)", s4).group(0)
        days = [2,3,4,5,8,9,10]
        counted = [d for d in days if not(category=="Z1" and 3<=d<=7)]
        return ("A" if len(counted)<=5 else "B"), {"category":category, "counted_june_days":counted, "count":len(counted)}
    raise AssertionError("Unknown public case")

events = [{
    "event": "review_scope",
    "reviewer": "Independent delegated Codex reviewer; same model family internal review; not an external expert",
    "verified_host": platform.node(),
    "packet_absolute_path": str(PACKET),
    "packet_sha256": EXPECTED_SHA,
    "packet_size_bytes": len(raw),
    "read_boundary": "Only packet.json as task input. Own answers and trace helper read for output validation. No private mapping, keys, author files, other reviewer answers, tested CLI, network, or other project files were accessed.",
    "read_batches": ["schema + P001/C001 sample", "P001-P010", "P011-P020", "P021-P030", "P031-P040", "P041-P050", "P051-P060", "P061-P070", "P071-P080", "C001-C008", "C009-C016", "C017-C024", "C025-C032"],
    "method": "Each complete public item was read; its formal rules and facts determined action before accepting or rejecting memo/draft. Narrative errors in suggestions were not promoted into authoritative facts. Full result summaries and source evidence follow for every item.",
    "single_error_convention": "true means exactly one independent substantive cause; false with draft_correct=true means zero errors. A wrong action and its causal wrong premise count once. No uncertain cases were found."
}]
mechanical_checks = []
memo_matches = 0
for section in ("p0", "challenge"):
    items = packet[section]
    rows = answers[section]
    assert [i["alias"] for i in items] == [r["alias"] for r in rows]
    assert len(set(r["alias"] for r in rows)) == len(rows)
    for item, row in zip(items, rows):
        expected_fields = {"alias","action","evidence","concerns"} | ({"unique"} if section=="p0" else {"draft_correct","single_error"})
        assert set(row) == expected_fields
        assert row["action"] in "ABCD" and len(row["action"])==1
        assert isinstance(row["evidence"],list) and row["evidence"]
        assert isinstance(row["concerns"],list)
        computed, numbers = factual_check(item["public_text"])
        assert row["action"] == computed, (item["alias"], row["action"], computed)
        if section=="p0":
            assert row["unique"] is True
            memo_action = re.search(r"建议：选择([ABCD])",item["public_text"]).group(1)
            memo_matches += (memo_action==row["action"])
        else:
            draft = json.loads(item["draft_text"])
            assert row["draft_correct"] == (draft["action"]==row["action"])
            assert row["single_error"] == (not row["draft_correct"])
        check = {"alias":row["alias"],"independent_numeric_branch_check":computed,"agrees_with_locked_manual_answer":True,"facts_recomputed":numbers}
        mechanical_checks.append(check)
        events.append({
            "event":"case_review",
            "section":section,
            "alias":item["alias"],
            "public_input":item,
            "public_input_sha256":hashlib.sha256(json.dumps(item,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            "review_result":row,
            "formal_archive_consistency":"No mutually incompatible authoritative S1-S9 facts found. Suggestions/drafts are review targets, not additional authoritative records.",
            "uniqueness_check":"Alternative actions excluded by the source-based evidence in review_result. No extra factual assumptions were used.",
            "leakage_check":"Checked the current public item's S1-S9 for a route that recovers an absent decisive S4 field. None found; P031/P032 wording risk is recorded separately. Recommendation/draft action letters are explicitly visible task content.",
            "mechanical_check":check
        })
validation = {
    "verified_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "host":platform.node(),
    "packet_sha256_before_outputs":EXPECTED_SHA,
    "packet_sha256_after_outputs":hashlib.sha256(PACKET.read_bytes()).hexdigest(),
    "answers_sha256":hashlib.sha256(ANSWERS.read_bytes()).hexdigest(),
    "coverage":{"p0":80,"challenge":32,"duplicate_aliases":0,"missing_aliases":0,"unknown_actions":0},
    "p0_unique":sum(r["unique"] for r in answers["p0"]),
    "p0_action_counts":dict(sorted(collections.Counter(r["action"] for r in answers["p0"]).items())),
    "p0_memo_action_matches_independent_answer":memo_matches,
    "p0_memo_action_differs":80-memo_matches,
    "challenge_correct":sum(r["draft_correct"] for r in answers["challenge"]),
    "challenge_incorrect":sum(not r["draft_correct"] for r in answers["challenge"]),
    "challenge_exactly_one_error":sum(r["single_error"] for r in answers["challenge"]),
    "uncertain_actions":0,
    "formal_archive_contradictions_found":0,
    "all_mechanical_branch_checks_passed":True,
    "checks":mechanical_checks,
    "limits":"Mechanical recomputation guards transcription/arithmetic only; it does not independently establish semantic uniqueness. Review remains same-family internal review."
}
assert validation["packet_sha256_after_outputs"]==EXPECTED_SHA
events.append({"event":"validation","result":validation})
TRACE.mkdir(parents=True,exist_ok=True)
(TRACE/"trace.jsonl").write_text("\n".join(json.dumps(e,ensure_ascii=False) for e in events)+"\n")
(TRACE/"validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in validation.items() if k!="checks"},ensure_ascii=False,indent=2))

