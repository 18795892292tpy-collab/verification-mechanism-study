"""Pool several branching runs and compare procedures with the case family as the unit.

Usage (from mechanism_study):
  python analysis/branch_pooled.py --run results/A/scored_runs.csv cases/dev --run results/B/scored_runs.csv cases/dev_hard \
      --out results/<name>_pooled

Outputs in --out: pooled_report.md, combined_scored_runs.csv (all rows) and combined_P0_P4.csv (for analyze.py).

Branching runs only: every review procedure reviews the same first answer (P0). On evidence-present items:
  repair = an incorrect first answer becomes correct after review; damage = a correct one becomes incorrect.
Family-level contrasts use each family's repair rate (families with at least one incorrect first answer);
they are tested with a paired t-test, a Wilcoxon signed-rank test and a sign test over families. Answer-level
sign tests on discordant pairs are reported too, but they ignore clustering within families.
"""
import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from scipy import stats

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY.parent / ".claude" / "skills" / "verification-case-builder" / "scripts"))
sys.path.insert(0, str(HERE))
import caselib as cl  # noqa: E402
from branch_report import sign_test, wilson  # noqa: E402

CONTRASTS = [("P3", "P1", "C1 analogue: source verification vs free re-check"),
             ("P3", "P2", "C2 analogue: source verification vs generic checklist"),
             ("P3", "P4", "source verification vs cue only"),
             ("P4", "P1", "cue only vs free re-check"),
             ("P5", "P3", "item 5 removed from source verification"),
             ("P6", "P2", "item 5 removed from generic checklist"),
             ("P1", "P2", "free re-check vs generic checklist")]


def p(path):
    return Path(path) if Path(path).is_absolute() else STUDY / path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs=2, action="append", metavar=("SCORED_CSV", "CASES_DIR"), required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = p(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, fams = [], {}
    for scored, cases in args.run:
        rows += list(csv.DictReader(open(p(scored), encoding="utf-8")))
        fams.update({f["family_id"]: f for f in cl.load_dir(p(cases))})
    with open(out / "combined_scored_runs.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(out / "combined_P0_P4.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(r for r in rows if r["procedure"] in {"P0", "P1", "P2", "P3", "P4"})

    key = lambda r: (r["family_id"], r["state"], r["advice"], r["repeat"])  # noqa: E731
    first = {key(r): r for r in rows if r["procedure"] == "P0"}
    review = defaultdict(dict)
    for r in rows:
        if r["procedure"] != "P0":
            review[r["procedure"]][key(r)] = r
            assert r["first_action"] == first[key(r)]["action"], "not a branching run"
    procs = sorted(review)
    complete = all(k in review[q] for q in procs for k in first)
    present = [k for k, r in first.items() if r["evidence"] == "present"]
    fw = [k for k in present if first[k]["correct"] == "0"]
    fr = [k for k in present if first[k]["correct"] == "1"]
    fam_ids = sorted({k[0] for k in first})

    def kind(k):
        r, fam = first[k], fams[k[0]]
        if r["advice"] == "flawed" and r["followed_advice"] == "1":
            return "followed flawed advice"
        if r["action"] == fam["escalate_option"]:
            return "escalated where action was due"
        return "other substantive error"

    L = []
    w = L.append
    w(f"# Pooled branching analysis ({out.name})\n")
    w(f"Model(s): {', '.join(sorted({r['model'] for r in rows}))}. Families: {len(fam_ids)} ({', '.join(fam_ids)}). "
      f"Shared first answers: {len(first)}; review procedures: {', '.join(procs)}; every review present: {complete}.\n")
    trunc = sum(r.get("truncated") == "1" for r in rows)
    reas = sum(int(r.get("reasoning_tokens") or 0) > 0 for r in rows)
    parse = sum(r["parse_ok"] == "1" for r in rows)
    w(f"Parsed answers {parse}/{len(rows)}; truncated responses {trunc}; responses with reasoning tokens {reas}.\n")

    w("## First answers (P0), evidence present\n")
    w(f"- correct {len(fr)}/{len(present)}; incorrect {len(fw)}: " +
      "; ".join(f"{k} {v}" for k, v in Counter(kind(k) for k in fw).most_common()))
    fl = [k for k in present if k[2] == "flawed"]
    al = [k for k in present if k[2] == "aligned"]
    w(f"- flawed advice corrected {sum(first[k]['correct'] == '1' for k in fl)}/{len(fl)}; "
      f"aligned advice correct {sum(first[k]['correct'] == '1' for k in al)}/{len(al)}\n")

    w("## Final accuracy by procedure (evidence present)\n")
    w("| procedure | flawed advice corrected | aligned advice kept correct | output tokens per item |")
    w("|---|---|---|---|")
    tok = defaultdict(list)
    for r in rows:
        tok[r["procedure"]].append(int(r["output_tokens"]))
    for q in ["P0"] + procs:
        src = first if q == "P0" else review[q]
        a = sum(src[k]["correct"] == "1" for k in fl)
        b = sum(src[k]["correct"] == "1" for k in al)
        w(f"| {q} | {a}/{len(fl)} = {a / len(fl):.2f} | {b}/{len(al)} = {b / len(al):.2f} | "
          f"{sum(tok[q]) / len(tok[q]):.0f} |")
    w("")

    w("## Repair and damage (pooled over answers)\n")
    w("| procedure | repaired / first wrong | repair rate [95% CI] | damaged / first right | damage rate [95% CI] |")
    w("|---|---|---|---|---|")
    for q in procs:
        rep = sum(review[q][k]["correct"] == "1" for k in fw)
        dam = sum(review[q][k]["correct"] == "0" for k in fr)
        rl, rh = wilson(rep, len(fw))
        dl, dh = wilson(dam, len(fr))
        w(f"| {q} | {rep}/{len(fw)} | {rep / max(1, len(fw)):.2f} [{rl:.2f}, {rh:.2f}] | {dam}/{len(fr)} | "
          f"{dam / max(1, len(fr)):.2f} [{dl:.2f}, {dh:.2f}] |")
    w("")

    w("## Repair rate by type of first-answer error\n")
    kinds = [k for k, _ in Counter(kind(k) for k in fw).most_common()]
    w("| procedure | " + " | ".join(kinds) + " |")
    w("|---|" + "---|" * len(kinds))
    for q in procs:
        cells = []
        for kd in kinds:
            ks = [k for k in fw if kind(k) == kd]
            cells.append(f"{sum(review[q][k]['correct'] == '1' for k in ks)}/{len(ks)}")
        w(f"| {q} | " + " | ".join(cells) + " |")
    w("")

    w("## Repair rate by mismatch type\n")
    mts = sorted({fams[k[0]]["mismatch_type"] for k in fw})
    w("| procedure | " + " | ".join(mts) + " |")
    w("|---|" + "---|" * len(mts))
    for q in procs:
        cells = []
        for m in mts:
            ks = [k for k in fw if fams[k[0]]["mismatch_type"] == m]
            cells.append(f"{sum(review[q][k]['correct'] == '1' for k in ks)}/{len(ks)}")
        w(f"| {q} | " + " | ".join(cells) + " |")
    w("")

    fam_err = [f for f in fam_ids if any(k[0] == f for k in fw)]

    def frate(q, f):
        ks = [k for k in fw if k[0] == f]
        return sum(review[q][k]["correct"] == "1" for k in ks) / len(ks)

    w(f"## Paired contrasts on repair rate (families with an incorrect first answer: {len(fam_err)})\n")
    w("| contrast | meaning | mean family difference [95% CI] | t-test p | Wilcoxon p | families A > B / A < B / tie | "
      "answers only A : only B (sign p) |")
    w("|---|---|---|---|---|---|---|")
    for a, b, meaning in CONTRASTS:
        if a not in review or b not in review:
            continue
        d = [frate(a, f) - frate(b, f) for f in fam_err]
        n = len(d)
        mean = sum(d) / n
        sd = (sum((x - mean) ** 2 for x in d) / (n - 1)) ** 0.5 if n > 1 else float("nan")
        se = sd / math.sqrt(n) if n > 1 else float("nan")
        tcrit = stats.t.ppf(0.975, n - 1) if n > 1 else float("nan")
        tp = stats.ttest_1samp(d, 0).pvalue if n > 1 and sd > 0 else float("nan")
        try:
            wp = stats.wilcoxon(d).pvalue if any(x != 0 for x in d) else 1.0
        except ValueError:
            wp = float("nan")
        gt, lt = sum(x > 0 for x in d), sum(x < 0 for x in d)
        oa = sum(review[a][k]["correct"] == "1" and review[b][k]["correct"] == "0" for k in fw)
        ob = sum(review[b][k]["correct"] == "1" and review[a][k]["correct"] == "0" for k in fw)
        w(f"| {a} vs {b} | {meaning} | {mean:+.3f} [{mean - tcrit * se:+.3f}, {mean + tcrit * se:+.3f}] | {tp:.3f} | "
          f"{wp:.3f} | {gt} / {lt} / {n - gt - lt} (sign p {sign_test(gt, lt):.3f}) | {oa} : {ob} ({sign_test(oa, ob):.3f}) |")
    w("")

    w("## Repairs by family\n")
    w("| family | mismatch | first wrong | " + " | ".join(procs) + " |")
    w("|---|---|---|" + "---|" * len(procs))
    for f in fam_err:
        ks = [k for k in fw if k[0] == f]
        w(f"| {f} | {fams[f]['mismatch_type']} | {len(ks)} | " +
          " | ".join(str(sum(review[q][k]['correct'] == '1' for k in ks)) for q in procs) + " |")
    w("")

    miss = [k for k, r in first.items() if r["state"] == "missing"]
    w("## Missing-evidence state (key = pause or escalate)\n")
    w(f"- P0 correct {sum(first[k]['correct'] == '1' for k in miss)}/{len(miss)}; after review: " +
      ", ".join(f"{q} {sum(review[q][k]['correct'] == '1' for k in miss)}/{len(miss)}" for q in procs))
    w("- unnecessary escalation with evidence present: P0 "
      f"{sum(first[k]['escalated'] == '1' for k in present)}/{len(present)}; " +
      ", ".join(f"{q} {sum(review[q][k]['escalated'] == '1' for k in present)}/{len(present)}" for q in procs))
    w("")
    w("Development data: the families were not reviewed by independent experts, and the contrasts are exploratory. "
      "Answer-level p values ignore clustering; the family-level tests are the ones that match the analysis plan.")
    text = "\n".join(L)
    (out / "pooled_report.md").write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)


if __name__ == "__main__":
    main()
