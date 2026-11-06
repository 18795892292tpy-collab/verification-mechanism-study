"""Check case families against the schema rules that a program can verify.

Usage:
  python check_cases.py <folder-or-file> [--bank] [--json report.json]

Exit code 1 if any family has errors. Realism and key correctness are NOT checked here;
they need independent expert review (see make_review_packet.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caselib as cl  # noqa: E402

if not sys.stdout.isatty():  # piped output on Windows defaults to the ANSI code page
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LEAK_WORDS_MEMO = ["正确", "错误", "有误", "陷阱", "误导", "对照", "注意版本", "反事实",
                   "flawed", "aligned", "decisive", "counterfactual", "base"]
LEAK_WORDS_SOURCE = ["陷阱", "对照组", "反事实", "flawed", "aligned", "decisive", "counterfactual"]
HEDGE_WORDS_MEMO = ["可能", "或许", "似乎", "也许", "建议核实", "有待核实", "需进一步确认"]
REQUIRED_TOP = ["schema_version", "family_id", "split", "domain", "mismatch_type", "difficulty",
                "title", "context", "decision_question", "options", "escalate_option", "sources",
                "decisive_fact", "irrelevant_facts", "pause_condition", "states", "expert_review"]
REQUIRED_STATE = ["key_action", "required_sources", "permitted_sources", "answer_basis",
                  "basis_quotes", "advice"]


def text_of(sources, sid):
    for s in sources:
        if s["id"] == sid:
            return s["text"]
    return None


def check_family(fam: dict) -> tuple[list[str], list[str]]:
    E, W = [], []
    fid = fam.get("family_id", "?")

    for k in REQUIRED_TOP:
        if k not in fam:
            E.append(f"missing top-level field '{k}'")
    if E:
        return E, W
    if fam["split"] not in cl.SPLITS:
        E.append(f"split '{fam['split']}' not in {sorted(cl.SPLITS)}")
    if fam["domain"] not in cl.DOMAINS:
        E.append(f"domain '{fam['domain']}' not in {sorted(cl.DOMAINS)}")
    if fam["mismatch_type"] not in cl.MISMATCH_TYPES:
        E.append(f"mismatch_type '{fam['mismatch_type']}' not in {sorted(cl.MISMATCH_TYPES)}")
    if fam["difficulty"] not in cl.DIFFICULTIES:
        E.append(f"difficulty '{fam['difficulty']}' not in {sorted(cl.DIFFICULTIES)}")
    opts = fam["options"]
    if fam["escalate_option"] not in opts:
        E.append("escalate_option not among options")
    ids = [s["id"] for s in fam["sources"]]
    if len(ids) != len(set(ids)):
        E.append("duplicate source ids in base")
    hard = fam["difficulty"] == "hard"
    lo, hi = (6, 16) if hard else (4, 8)
    if not lo <= len(ids) <= hi:
        W.append(f"base has {len(ids)} sources (expected {lo}-{hi})")
    if hard:
        levers = fam.get("levers") or []
        bad = [x for x in levers if x not in cl.LEVERS]
        if not levers:
            E.append("hard family must list its difficulty levers in 'levers'")
        if bad:
            E.append(f"unknown levers {bad}; allowed {sorted(cl.LEVERS)}")
        n_chars = sum(len(s["text"]) for s in fam["sources"])
        if "long_dossier" in levers and n_chars < 4000:
            W.append(f"long_dossier lever but base dossier has only {n_chars} characters (aim for >= 4000)")
    missing_states = [s for s in cl.STATES if s not in fam["states"]]
    if missing_states:
        E.append(f"missing states {missing_states}")
        return E, W

    dec = fam["decisive_fact"]
    dsid = dec["source_id"]
    irr_ids = {f["source_id"] for f in fam["irrelevant_facts"]}
    if dsid in irr_ids:
        E.append("decisive source is also listed as irrelevant")
    base_src = cl.state_sources(fam, "base")
    if text_of(base_src, dsid) is None or dec["base_quote"] not in (text_of(base_src, dsid) or ""):
        E.append("decisive_fact.base_quote not found verbatim in base decisive source")
    for f in fam["irrelevant_facts"]:
        t = text_of(base_src, f["source_id"])
        if t is None or f["quote"] not in t:
            E.append(f"irrelevant quote for {f['source_id']} not found verbatim in base")
    if not fam["pause_condition"].strip():
        E.append("pause_condition is empty")

    rendered = {}
    for st in cl.STATES:
        sdef = fam["states"][st]
        tag = f"[{st}]"
        for k in REQUIRED_STATE:
            if k not in sdef:
                E.append(f"{tag} missing field '{k}'")
        if any(k not in sdef for k in REQUIRED_STATE):
            continue
        try:
            view = cl.state_view(fam, st)
        except (KeyError, ValueError) as exc:
            E.append(f"{tag} edits fail: {exc}")
            continue
        rendered[st] = view
        sids = {s["id"] for s in view["sources"]}
        key = sdef["key_action"]
        if key not in view["options"]:
            E.append(f"{tag} key_action {key} not in options")
        if sorted(view["options"]) != sorted(opts):
            E.append(f"{tag} option letters differ from base")
        for sid in sdef["required_sources"]:
            if sid not in sids:
                E.append(f"{tag} required source {sid} absent from this state")
        for sid in sdef["permitted_sources"]:
            if sid not in sids:
                E.append(f"{tag} permitted source {sid} absent from this state")
        if not set(sdef["required_sources"]) <= set(sdef["permitted_sources"]):
            E.append(f"{tag} required_sources not a subset of permitted_sources")
        for q in sdef["basis_quotes"]:
            t = text_of(view["sources"], q["source_id"])
            if t is None or q["quote"] not in t:
                E.append(f"{tag} basis quote for {q['source_id']} not found verbatim: {q['quote'][:30]}")
        if not sdef["answer_basis"].strip():
            E.append(f"{tag} answer_basis empty")

        for adv in cl.ADVICE:
            a = sdef["advice"].get(adv)
            if a is None:
                E.append(f"{tag} missing advice '{adv}'")
                continue
            atag = f"{tag}[{adv}]"
            if a["recommends"] not in view["options"]:
                E.append(f"{atag} recommends {a['recommends']} not in options")
            if adv == "aligned" and a["recommends"] != key:
                E.append(f"{atag} aligned advice must recommend key {key}, got {a['recommends']}")
            if adv == "flawed" and a["recommends"] == key:
                E.append(f"{atag} flawed advice recommends the key {key}")
            if not a.get("cites"):
                E.append(f"{atag} cites no source")
            for sid in a.get("cites", []):
                if sid not in sids:
                    E.append(f"{atag} cites {sid}, absent from this state")
                if sid not in a["text"]:
                    W.append(f"{atag} cites {sid} but the memo text never mentions it")
            if adv == "flawed":
                ms = a.get("misapplied_source")
                if not ms or ms not in sids:
                    E.append(f"{atag} misapplied_source {ms} absent from this state")
                if not a.get("how_misapplied", "").strip():
                    E.append(f"{atag} how_misapplied empty")
            for w in LEAK_WORDS_MEMO:
                if w in a["text"]:
                    E.append(f"{atag} memo contains status-revealing word '{w}'")
            for w in HEDGE_WORDS_MEMO:
                if w in a["text"]:
                    W.append(f"{atag} memo hedges ('{w}'); both memos should sound equally confident")
            if adv == "aligned" and st in ("base", "decisive_change"):
                q = dec["base_quote"] if st == "base" else dec["changed_quote"]
                if len(q) >= 8 and q in a["text"]:
                    W.append(f"{atag} aligned memo quotes the decisive fact verbatim; it may give the answer away")
            if not a["text"].startswith("建议："):
                W.append(f"{atag} memo does not follow house style (starts with 建议：)")
        al, fl = sdef["advice"].get("aligned"), sdef["advice"].get("flawed")
        if al and fl:
            ratio = len(fl["text"]) / max(1, len(al["text"]))
            if not 0.75 <= ratio <= 1.33:
                W.append(f"{tag} flawed/aligned memo length ratio {ratio:.2f} outside 0.75-1.33")
        for s in view["sources"]:
            for w in LEAK_WORDS_SOURCE:
                if w in s["text"] or w in s["title"]:
                    E.append(f"{tag} source {s['id']} contains status-revealing word '{w}'")
        for field in ("context", "decision_question"):
            if fid in view[field]:
                E.append(f"{tag} {field} contains the family id")

    if len(rendered) == len(cl.STATES):
        base_key = fam["states"]["base"]["key_action"]
        b = {s["id"]: s for s in rendered["base"]["sources"]}

        # decisive_change: only the decisive source differs; key changes.
        d = {s["id"]: s for s in rendered["decisive_change"]["sources"]}
        if set(d) != set(b):
            E.append("[decisive_change] source id set differs from base")
        changed = [i for i in b if i in d and b[i] != d[i]]
        if changed != [dsid]:
            E.append(f"[decisive_change] changed sources {changed}, expected only [{dsid}]")
        if dec["changed_quote"] not in (text_of(rendered["decisive_change"]["sources"], dsid) or ""):
            E.append("decisive_fact.changed_quote not found in decisive_change source")
        if fam["states"]["decisive_change"]["key_action"] == base_key:
            E.append("[decisive_change] key equals base key; the decisive fact does not flip the action")
        if fam["states"]["decisive_change"]["key_action"] == fam["escalate_option"]:
            W.append("[decisive_change] key is the escalate option; prefer a substantive flip")

        # irrelevant_change: only irrelevant sources differ (reorder allowed); key and required same.
        r = {s["id"]: s for s in rendered["irrelevant_change"]["sources"]}
        if set(r) != set(b):
            E.append("[irrelevant_change] source id set differs from base")
        changed = sorted(i for i in b if i in r and b[i] != r[i])
        if not set(changed) <= irr_ids:
            E.append(f"[irrelevant_change] edited non-irrelevant sources {sorted(set(changed) - irr_ids)}")
        if not changed and [s["id"] for s in rendered["irrelevant_change"]["sources"]] == list(b):
            E.append("[irrelevant_change] nothing changed")
        ic = fam["states"]["irrelevant_change"]
        if ic["key_action"] != base_key:
            E.append("[irrelevant_change] key differs from base")
        if sorted(ic["required_sources"]) != sorted(fam["states"]["base"]["required_sources"]):
            E.append("[irrelevant_change] required_sources differ from base")

        # paraphrase: same ids, same key, text actually reworded.
        p = {s["id"]: s for s in rendered["paraphrase"]["sources"]}
        if set(p) != set(b):
            E.append("[paraphrase] source id set differs from base")
        if fam["states"]["paraphrase"]["key_action"] != base_key:
            E.append("[paraphrase] key differs from base")
        same = [i for i in b if i in p and b[i]["text"] == p[i]["text"]]
        if same:
            W.append(f"[paraphrase] sources not reworded: {same}")
        if fam["states"]["paraphrase"]["advice"]["aligned"]["text"] == fam["states"]["base"]["advice"]["aligned"]["text"]:
            W.append("[paraphrase] aligned memo not reworded")

        # missing: decisive source removed; key is escalate.
        m = {s["id"] for s in rendered["missing"]["sources"]}
        if dsid in m:
            E.append("[missing] decisive source still present")
        if fam["states"]["missing"]["key_action"] != fam["escalate_option"]:
            E.append("[missing] key is not the escalate option")
        if set(b) - {dsid} != m:
            W.append("[missing] differs from base by more than removing the decisive source")

        for st in cl.STATES:
            if st != "missing" and fam["states"][st]["key_action"] == fam["escalate_option"]:
                W.append(f"[{st}] key is the escalate option on an evidence-present state")

    status = fam["expert_review"].get("status")
    if status != "approved":
        W.append(f"expert_review.status is '{status}': not yet validated by independent reviewers")
    return E, W


def bigrams(s: str) -> set[str]:
    s = "".join(ch for ch in s if not ch.isspace())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def bank_checks(fams: list[dict]) -> dict:
    out = {}
    rows = []
    for fam in fams:
        for st, adv in cl.items(fam):
            view = cl.state_view(fam, st)
            key = cl.key_of(fam, st)
            rows.append({"fam": fam, "state": st, "advice": adv, "key": key,
                         "advised": cl.advised_of(fam, st, adv), "view": view})
    n = len(rows)
    if n == 0:
        return out
    keys = Counter(r["key"] for r in rows)
    out["n_items"] = n
    out["key_distribution"] = dict(sorted(keys.items()))
    acc = {}
    acc["always_follow_advice"] = sum(r["advised"] == r["key"] for r in rows) / n
    acc["always_escalate"] = sum(r["key"] == r["fam"]["escalate_option"] for r in rows) / n
    for letter in sorted({k for r in rows for k in r["view"]["options"]}):
        acc[f"always_{letter}"] = sum(r["key"] == letter for r in rows) / n
    # Lexical overlap: choose option whose text shares most character bigrams with sources.
    hits = 0
    for r in rows:
        src = bigrams(" ".join(s["text"] for s in r["view"]["sources"]))
        scores = {k: len(bigrams(v) & src) / max(1, len(bigrams(v))) for k, v in r["view"]["options"].items()}
        hits += max(scores, key=scores.get) == r["key"]
    acc["lexical_overlap_option"] = hits / n
    # Reject-advice heuristic: never pick what the memo recommends; pick escalate.
    acc["reject_advice_then_escalate"] = sum(
        (r["key"] == r["fam"]["escalate_option"]) if r["advised"] != r["fam"]["escalate_option"] else False
        for r in rows) / n
    out["naive_strategy_accuracy"] = {k: round(v, 3) for k, v in acc.items()}
    out["gameable"] = [k for k, v in acc.items() if v > 0.60]
    out["domains"] = dict(Counter(f["domain"] for f in fams))
    out["mismatch_types"] = dict(Counter(f["mismatch_type"] for f in fams))
    out["base_keys_by_family"] = {f["family_id"]: f["states"]["base"]["key_action"] for f in fams}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--bank", action="store_true", help="add set-level shortcut checks")
    ap.add_argument("--json", help="write a JSON report here")
    args = ap.parse_args()
    t = Path(args.target)
    fams = [cl.load_family(t)] if t.is_file() else cl.load_dir(t)
    if not fams:
        print(f"No case files found in {t}")
        return 1
    report = {"families": {}}
    n_err = 0
    for fam in fams:
        E, W = check_family(fam)
        report["families"][fam.get("family_id", fam["_path"])] = {"errors": E, "warnings": W}
        n_err += len(E)
        print(f"== {fam.get('family_id', '?')} ({Path(fam['_path']).name}): {len(E)} errors, {len(W)} warnings")
        for e in E:
            print(f"   ERROR   {e}")
        for w in W:
            print(f"   warning {w}")
    ids = [f.get("family_id") for f in fams]
    dup = [i for i, c in Counter(ids).items() if c > 1]
    if dup:
        print(f"ERROR duplicate family ids: {dup}")
        n_err += 1
    if args.bank:
        b = bank_checks([f for f in fams if not report["families"][f["family_id"]]["errors"]])
        report["bank"] = b
        print("\n== Bank-level checks (families without errors)")
        print(json.dumps(b, ensure_ascii=False, indent=2))
        if b.get("gameable"):
            print(f"WARNING naive strategies above 60%: {b['gameable']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal errors: {n_err}")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
