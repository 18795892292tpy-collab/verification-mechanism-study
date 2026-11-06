"""Score runner output against the case keys.

Usage (from D:\\lunweng\\mechanism_study):
  python harness/scorer.py results/dev_mock --cases cases/dev

Writes <run_dir>/scored_runs.csv (columns fixed; see COLUMNS) and prints a short summary.
Rule-based only: action, advice following, escalation, citation completeness, cost.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY.parent / ".claude" / "skills" / "verification-case-builder" / "scripts"))
import caselib as cl  # noqa: E402

if not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COLUMNS = ["run_id", "model", "procedure", "family_id", "domain", "mismatch_type", "state", "evidence",
           "advice", "repeat", "key_action", "advised_action", "action", "parse_ok", "correct",
           "followed_advice", "escalated", "citation_complete", "first_action", "changed_after_review",
           "input_tokens", "output_tokens", "latency_s", "n_calls", "cited_sources",
           "reasoning_tokens", "truncated"]

JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)
BARE_OBJ = re.compile(r"\{[^{}]*\"action\"[^{}]*\}", re.S)


def parse_answer(text: str, letters: set[str]) -> dict | None:
    cands = JSON_BLOCK.findall(text or "") or BARE_OBJ.findall(text or "")
    for raw in reversed(cands):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            try:
                obj = json.loads(re.sub(r",\s*}", "}", raw.replace("'", '"')))
            except json.JSONDecodeError:
                continue
        act = str(obj.get("action", "")).strip().upper()[:1]
        if act in letters:
            cites = obj.get("cited_sources") or []
            if isinstance(cites, str):
                cites = [cites]
            norm = sorted({m.upper().replace(" ", "") for c in cites for m in re.findall(r"[Ss]\s*\d+", str(c))})
            return {"action": act, "cited": norm}
    return None


def latest_ok(resp_path: Path) -> dict:
    recs = {}
    with open(resp_path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("status") == "ok":
                recs[rec["run_id"]] = rec
    return recs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cases", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir) if Path(args.run_dir).is_absolute() else STUDY / args.run_dir
    cases_dir = Path(args.cases) if Path(args.cases).is_absolute() else STUDY / args.cases
    fams = {f["family_id"]: f for f in cl.load_dir(cases_dir)}
    with open(run_dir / "plan.csv", encoding="utf-8", newline="") as fh:
        plan = list(csv.DictReader(fh))
    recs = latest_ok(run_dir / "responses.jsonl")
    manifests = sorted(run_dir.glob("manifest_*.json"))
    model = json.loads(manifests[-1].read_text(encoding="utf-8"))["params"]["model"] if manifests else ""

    rows, n_missing = [], 0
    for p in plan:
        rec = recs.get(p["run_id"])
        if rec is None:
            n_missing += 1
            continue
        fam = fams[p["family_id"]]
        st, adv = p["state"], p["advice"]
        letters = set(cl.state_view(fam, st)["options"])
        key = cl.key_of(fam, st)
        advised = cl.advised_of(fam, st, adv)
        required = set(fam["states"][st]["required_sources"])
        final = parse_answer(rec["calls"][-1].get("text", ""), letters)
        first = parse_answer(rec["calls"][0].get("text", ""), letters) if len(rec["calls"]) > 1 else None
        usage = [c.get("usage") or {} for c in rec["calls"]]
        row = {
            "run_id": p["run_id"], "model": rec["calls"][0].get("model_returned") or model,
            "procedure": p["procedure"], "family_id": p["family_id"], "domain": fam["domain"],
            "mismatch_type": fam["mismatch_type"], "state": st, "evidence": cl.evidence_status(st),
            "advice": adv, "repeat": p["repeat"], "key_action": key, "advised_action": advised,
            "action": final["action"] if final else "", "parse_ok": int(final is not None),
            "correct": int(bool(final) and final["action"] == key),
            "followed_advice": int(bool(final) and final["action"] == advised),
            "escalated": int(bool(final) and final["action"] == fam["escalate_option"]),
            "citation_complete": int(bool(final) and required <= set(final["cited"])),
            "first_action": first["action"] if first else "",
            "changed_after_review": (int(first["action"] != final["action"]) if (first and final) else ""),
            "input_tokens": sum(int(u.get("prompt_tokens") or 0) for u in usage),
            "output_tokens": sum(int(u.get("completion_tokens") or 0) for u in usage),
            "latency_s": round(sum(float(c.get("latency_s") or 0) for c in rec["calls"]), 3),
            "n_calls": len(rec["calls"]),
            "cited_sources": ";".join(final["cited"]) if final else "",
            # Reasoning ("thinking") mode shows up as reasoning tokens; requesting deepseek-flash by
            # name enabled it, while the deepseek-chat alias did not. Truncation = hit the output cap.
            "reasoning_tokens": sum(int(((u.get("completion_tokens_details") or {}).get("reasoning_tokens")) or 0)
                                    for u in usage),
            "truncated": int(any(c.get("finish_reason") == "length" for c in rec["calls"])),
        }
        rows.append(row)

    out = run_dir / "scored_runs.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"Scored {len(rows)} runs ({n_missing} planned runs without an ok response) -> {out}")
    n_reason = sum(r["reasoning_tokens"] > 0 for r in rows)
    n_trunc = sum(r["truncated"] for r in rows)
    if n_reason:
        print(f"WARNING: {n_reason} responses used reasoning tokens (reasoning mode is on); "
              "this is a different condition from the non-reasoning runs.")
    if n_trunc:
        print(f"WARNING: {n_trunc} responses hit the output cap; their answers may be missing.")

    # Short summary by procedure.
    agg = defaultdict(lambda: defaultdict(list))
    for r in rows:
        a = agg[r["procedure"]]
        a["parse_ok"].append(r["parse_ok"])
        if r["evidence"] == "present" and r["advice"] == "flawed":
            a["flawed_correction"].append(r["correct"])
        if r["evidence"] == "present" and r["advice"] == "aligned":
            a["aligned_overturn"].append(1 - r["correct"])
        if r["state"] == "missing":
            a["pause_appropriate"].append(r["escalated"])
        if r["evidence"] == "present":
            a["unnecessary_escalation"].append(r["escalated"])
        a["output_tokens"].append(r["output_tokens"])
    cols = ["parse_ok", "flawed_correction", "aligned_overturn", "pause_appropriate",
            "unnecessary_escalation", "output_tokens"]
    print("procedure  " + "  ".join(f"{c:>22}" for c in cols))
    for proc in sorted(agg):
        vals = []
        for c in cols:
            v = agg[proc][c]
            vals.append(f"{(sum(v) / len(v)) if v else float('nan'):>22.3f}" if c != "output_tokens"
                        else f"{(sum(v) / len(v)) if v else float('nan'):>22.1f}")
        print(f"{proc:<10} " + "  ".join(vals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
