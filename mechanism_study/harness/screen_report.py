"""Summarize a P0 difficulty screen per family and classify every error.

Usage (from mechanism_study):  python harness/screen_report.py results/<screen_dir> --cases cases/<dir>

Error types:
  followed_flawed   - chose the action the flawed memo recommended (a genuine miss)
  escalated_wrongly - chose the escalate option where the key is a substantive action
  acted_not_paused  - chose a substantive action where the key is escalation
  other             - another substantive action
Verdict per family (hard_tier.md): too_easy if flawed-advice correction (evidence present) >= 90%;
check_key if most errors are escalation-type (likely an arguable key); usable otherwise.
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY.parent / ".claude" / "skills" / "verification-case-builder" / "scripts"))
import caselib as cl  # noqa: E402

if not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cases", required=True)
    args = ap.parse_args()
    run = Path(args.run_dir) if Path(args.run_dir).is_absolute() else STUDY / args.run_dir
    cases = Path(args.cases) if Path(args.cases).is_absolute() else STUDY / args.cases
    fams = {f["family_id"]: f for f in cl.load_dir(cases)}
    rows = [r for r in csv.DictReader(open(run / "scored_runs.csv", encoding="utf-8")) if r["procedure"] == "P0"]
    by = defaultdict(list)
    for r in rows:
        by[r["family_id"]].append(r)
    print(f"{'family':7}{'levers':38}{'flawedE+':>10}{'alignedE+':>11}{'missing':>9}  errors  verdict")
    tot = Counter()
    for fid in sorted(by):
        fam, rs = fams[fid], by[fid]
        esc = fam["escalate_option"]

        def rate(pred):
            v = [int(r["correct"]) for r in rs if pred(r)]
            return (sum(v), len(v))
        fe = rate(lambda r: r["evidence"] == "present" and r["advice"] == "flawed")
        ae = rate(lambda r: r["evidence"] == "present" and r["advice"] == "aligned")
        mi = rate(lambda r: r["state"] == "missing")
        err = Counter()
        for r in rs:
            if r["correct"] == "1":
                continue
            if r["advice"] == "flawed" and r["followed_advice"] == "1":
                t = "followed_flawed"
            elif r["action"] == esc:
                t = "escalated_wrongly"
            elif r["key_action"] == esc:
                t = "acted_not_paused"
            else:
                t = "other"
            err[t] += 1
            tot[t] += 1
        n_err = sum(err.values())
        if fe[1] and fe[0] / fe[1] >= 0.90:
            verdict = "too_easy"
        elif n_err and (err["escalated_wrongly"] + err["acted_not_paused"]) / n_err > 0.5:
            verdict = "check_key"
        else:
            verdict = "usable"
        levers = ",".join(fam.get("levers") or [])
        es = " ".join(f"{k}={v}" for k, v in err.items()) or "-"
        print(f"{fid:7}{levers:38}{fe[0]:>4}/{fe[1]:<5}{ae[0]:>5}/{ae[1]:<5}{mi[0]:>4}/{mi[1]:<4}  {es}  -> {verdict}")
    allfe = [int(r["correct"]) for r in rows if r["evidence"] == "present" and r["advice"] == "flawed"]
    print(f"\nAll families: flawed-advice correction (evidence present) {sum(allfe)}/{len(allfe)} = {sum(allfe) / max(1, len(allfe)):.2f}")
    print("Error types:", dict(tot))


if __name__ == "__main__":
    main()
