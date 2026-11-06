"""Repair and damage analysis for branching runs (all procedures review the same first answer).

Usage (from mechanism_study):
  python analysis/branch_report.py results/<dir>/scored_runs.csv --cases cases/<dir> [--out results/<dir>/branch_report.md]

For each review procedure, on evidence-present items:
  repair rate = share of incorrect first answers (P0) that the review makes correct
  damage rate = share of correct first answers that the review makes incorrect
Paired contrasts compare two procedures on the same incorrect (or correct) first answers:
discordant pairs are tested with an exact two-sided sign test; family-level counts show whether a
difference holds across families or comes from one.
"""
import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY.parent / ".claude" / "skills" / "verification-case-builder" / "scripts"))
import caselib as cl  # noqa: E402
sys.path.insert(0, str(STUDY / "harness"))
from scorer import load_verified_branch_rows  # noqa: E402
from branch_integrity import IntegrityError  # noqa: E402

CONTRASTS = [("P5", "P3", "item 5 removed from source verification"),
             ("P6", "P2", "item 5 removed from generic checklist"),
             ("P3", "P1", "source verification vs free re-check"),
             ("P3", "P2", "source verification vs generic checklist"),
             ("P3", "P4", "source verification vs cue only")]


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - h) / d), min(1.0, (c + h) / d)


def sign_test(a, b):
    """Exact two-sided binomial test of a successes vs b failures among discordant pairs."""
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scored")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    cases = Path(args.cases) if Path(args.cases).is_absolute() else STUDY / args.cases
    fams = {f["family_id"]: f for f in cl.load_dir(cases)}
    rows = load_verified_branch_rows(args.scored, cases)
    key = lambda r: (r["family_id"], r["state"], r["advice"], r["repeat"], r.get("source_run", ""))  # noqa: E731
    first = {key(r): r for r in rows if r["procedure"] == "P0"}
    review = defaultdict(dict)
    for r in rows:
        if r["procedure"] != "P0":
            review[r["procedure"]][key(r)] = r
            if (r["branch_id"], r["first_text_sha256"]) != (first[key(r)]["branch_id"], first[key(r)]["first_text_sha256"]):
                raise IntegrityError("Branch or full first-answer hash differs")
    procs = sorted(review)
    if not first or any(k not in review[q] for q in procs for k in first):
        raise IntegrityError("No complete, consistently paired branch groups to analyze")
    out = []
    w = out.append
    w(f"# Branching analysis: {Path(args.scored).parent.name}\n")
    w(f"Families: {', '.join(sorted({k[0] for k in first}))}; shared first answers: {len(first)}; "
      f"review procedures: {', '.join(procs)}\n")

    present = [k for k, r in first.items() if r["evidence"] == "present"]
    fw = [k for k in present if first[k]["correct"] == "0"]
    fr = [k for k in present if first[k]["correct"] == "1"]
    kinds = Counter()
    for k in fw:
        r, fam = first[k], fams[k[0]]
        if r["advice"] == "flawed" and r["followed_advice"] == "1":
            kinds["followed flawed advice"] += 1
        elif r["action"] == fam["escalate_option"]:
            kinds["escalated where action was due"] += 1
        else:
            kinds["other substantive action"] += 1
    w("## First answers (P0), evidence present\n")
    w(f"- correct {len(fr)}/{len(present)}; incorrect {len(fw)}: " + "; ".join(f"{k} {v}" for k, v in kinds.items()))
    by_fam = Counter(k[0] for k in fw)
    w("- incorrect first answers by family: " + ", ".join(f"{f} {n}" for f, n in sorted(by_fam.items())) + "\n")

    w("## Repair and damage by procedure (evidence present, pooled)\n")
    w("| procedure | repaired / first wrong | repair rate [95% CI] | damaged / first right | damage rate [95% CI] |")
    w("|---|---|---|---|---|")
    for p in procs:
        rep = sum(review[p][k]["correct"] == "1" for k in fw)
        dam = sum(review[p][k]["correct"] == "0" for k in fr)
        rl, rh = wilson(rep, len(fw))
        dl, dh = wilson(dam, len(fr))
        w(f"| {p} | {rep}/{len(fw)} | {rep / max(1, len(fw)):.2f} [{rl:.2f}, {rh:.2f}] | {dam}/{len(fr)} | "
          f"{dam / max(1, len(fr)):.2f} [{dl:.2f}, {dh:.2f}] |")
    w("")
    w("## Repairs by family\n")
    fams_with_errors = sorted(by_fam)
    w("| procedure | " + " | ".join(fams_with_errors) + " |")
    w("|---|" + "---|" * len(fams_with_errors))
    for p in procs:
        cells = []
        for f in fams_with_errors:
            ks = [k for k in fw if k[0] == f]
            cells.append(f"{sum(review[p][k]['correct'] == '1' for k in ks)}/{len(ks)}")
        w(f"| {p} | " + " | ".join(cells) + " |")
    w("")
    w("## Paired contrasts on the same incorrect first answers\n")
    w("| contrast | meaning | only A repairs | only B repairs | both | neither | sign test p | families A > B / A < B |")
    w("|---|---|---|---|---|---|---|---|")
    for a, b, meaning in CONTRASTS:
        if a not in review or b not in review:
            continue
        oa = sum(review[a][k]["correct"] == "1" and review[b][k]["correct"] == "0" for k in fw)
        ob = sum(review[b][k]["correct"] == "1" and review[a][k]["correct"] == "0" for k in fw)
        both = sum(review[a][k]["correct"] == "1" and review[b][k]["correct"] == "1" for k in fw)
        nei = len(fw) - oa - ob - both
        fa = fb = 0
        for f in fams_with_errors:
            ks = [k for k in fw if k[0] == f]
            ra = sum(review[a][k]["correct"] == "1" for k in ks)
            rb = sum(review[b][k]["correct"] == "1" for k in ks)
            fa += ra > rb
            fb += ra < rb
        w(f"| {a} vs {b} | {meaning} | {oa} | {ob} | {both} | {nei} | {sign_test(oa, ob):.3f} | {fa} / {fb} |")
    w("")
    miss = [k for k, r in first.items() if r["state"] == "missing"]
    w("## Missing-evidence state (key = escalate)\n")
    w(f"- P0 correct {sum(first[k]['correct'] == '1' for k in miss)}/{len(miss)}; after review: " +
      ", ".join(f"{p} {sum(review[p][k]['correct'] == '1' for k in miss)}/{len(miss)}" for p in procs))
    w("")
    w("Note: small numbers of incorrect first answers make every contrast imprecise; treat development "
      "results as leads for the frozen confirmation set, not as tests of H1.")
    text = "\n".join(out)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)


if __name__ == "__main__":
    main()
