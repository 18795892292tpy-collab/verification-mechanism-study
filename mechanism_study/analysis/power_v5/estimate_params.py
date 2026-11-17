"""Estimate the inputs of the v5 Phase 3 power simulation from the development runs.

Reads scored_runs.csv files (one row per procedure x item x repeat) and prints, by condition:
  - baseline (P0) error rates on evidence-present flawed-advice items, by family
  - item-level clustering of baseline errors (how often repeats of one item fail together)
  - repair and damage rates of each review procedure under the branching design
  - overturning of aligned advice and pausing on missing-evidence items
Writes everything to params_from_dev.json next to this script.

Usage: python estimate_params.py <results dir> [<extra results dir> ...]
The first directory is searched first for each run folder; later ones fill gaps (for runs whose
scored_runs.csv exists only in a scratch copy).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent

NONREASONING = {
    "standard_independent": ["dev_strong"],            # F01-F08, P0-P4, independent first calls
    "standard_branching": ["flash_branch_dev"],         # F01-F08, branching, 31 groups
    "hard_screens": ["screen_hard_a", "screen_hard_b", "screen_hard_c"],  # H01-H12, P0 only
    "h04_branching": ["dev_hard_H04_branching", "dev_r3_H04_branching"],
}
REASONING = {
    "reasoning_branching": ["flash_think_branch_dev", "flash_think_branch_hard"],
    "reasoning_h04_p0": ["probe_thinking_H04"],
}


def load(dirs, name):
    for d in dirs:
        p = Path(d) / name / "scored_runs.csv"
        if p.exists():
            s = pd.read_csv(p)
            s["run"] = name
            return s
    raise FileNotFoundError(name)


def p0_flawed_present(s):
    return s[(s.procedure == "P0") & (s.evidence == "present") & (s.advice == "flawed")]


def family_error_rates(s):
    ep = p0_flawed_present(s)
    g = ep.groupby("family_id").correct.agg(["sum", "count"])
    return {f: {"errors": int(r["count"] - r["sum"]), "n": int(r["count"])} for f, r in g.iterrows()}


def item_clustering(s):
    """Beta-binomial concentration of P0 errors across repeats of the same item (flawed, present).

    Method of moments on items with at least 2 repeats: if item error probabilities vary around
    the family mean with Beta(mu*k, (1-mu)*k), the variance of item means exceeds the binomial one.
    Returns the intraclass correlation rho = 1/(k+1) and the per-item error counts.
    """
    ep = p0_flawed_present(s).copy()
    ep["item"] = ep.run + "|" + ep.family_id + "|" + ep.state
    g = ep.groupby("item").correct.agg(["sum", "count"])
    g = g[g["count"] >= 2]
    err = (g["count"] - g["sum"]).astype(float)
    n = g["count"].astype(float)
    mu = err.sum() / n.sum()
    if mu in (0, 1) or len(g) < 2:
        return {"rho": None, "items": {k: [int(e), int(c)] for k, e, c in zip(g.index, err, n)}}
    # ANOVA-type estimator of ICC for binary data with unequal cluster sizes.
    N, K = n.sum(), len(g)
    n0 = (N - (n ** 2).sum() / N) / (K - 1)
    msb = ((err - n * mu) ** 2 / n).sum() / (K - 1)
    msw = (err - err ** 2 / n).sum() / (N - K)
    rho = (msb - msw) / (msb + (n0 - 1) * msw)
    return {"rho": float(rho), "mean_error": float(mu),
            "items": {k: [int(e), int(c)] for k, e, c in zip(g.index, err, n)}}


def branching_rates(s, advice=None):
    """Repair and damage per review procedure, evidence present, using the shared first answer."""
    r = s[(s.evidence == "present") & (s.procedure != "P0")].copy()
    if advice:
        r = r[r.advice == advice]
    r["first_correct"] = (r.first_action == r.key_action).astype(int)
    out = {}
    for proc, g in r.groupby("procedure"):
        wrong, right = g[g.first_correct == 0], g[g.first_correct == 1]
        out[proc] = {"repaired": int(wrong.correct.sum()), "first_wrong": int(len(wrong)),
                     "damaged": int((1 - right.correct).sum()), "first_right": int(len(right))}
    return out


def overturn_and_pause(s):
    al = s[(s.evidence == "present") & (s.advice == "aligned")]
    ms = s[s.evidence == "absent"]
    out = {}
    for proc in sorted(s.procedure.unique()):
        a, m = al[al.procedure == proc], ms[ms.procedure == proc]
        out[proc] = {"aligned_overturn": [int((1 - a.followed_advice).sum()), int(len(a))],
                     "missing_escalated": [int(m.escalated.sum()), int(len(m))]}
    return out


def main():
    dirs = sys.argv[1:] or [str(HERE.parent.parent / "results")]
    res = {"nonreasoning": {}, "reasoning": {}}
    std = pd.concat([load(dirs, n) for n in NONREASONING["standard_independent"]])
    res["nonreasoning"]["standard_family_errors"] = family_error_rates(std)
    res["nonreasoning"]["standard_clustering"] = item_clustering(std)
    res["nonreasoning"]["standard_overturn_pause"] = overturn_and_pause(std)
    stb = pd.concat([load(dirs, n) for n in NONREASONING["standard_branching"]])
    res["nonreasoning"]["standard_branching"] = branching_rates(stb)
    hs = pd.concat([load(dirs, n) for n in NONREASONING["hard_screens"]])
    res["nonreasoning"]["hard_family_errors"] = family_error_rates(hs)
    h4 = pd.concat([load(dirs, n) for n in NONREASONING["h04_branching"]])
    res["nonreasoning"]["h04_family_errors"] = family_error_rates(h4)
    res["nonreasoning"]["h04_clustering"] = item_clustering(h4)
    res["nonreasoning"]["h04_branching_flawed"] = branching_rates(h4, "flawed")
    res["nonreasoning"]["h04_branching_all"] = branching_rates(h4)
    res["nonreasoning"]["h04_overturn_pause"] = overturn_and_pause(h4)
    rb = pd.concat([load(dirs, n) for n in REASONING["reasoning_branching"]])
    res["reasoning"]["family_errors"] = family_error_rates(rb)
    res["reasoning"]["branching"] = branching_rates(rb)
    res["reasoning"]["overturn_pause"] = overturn_and_pause(rb)
    rh = pd.concat([load(dirs, n) for n in REASONING["reasoning_h04_p0"]])
    res["reasoning"]["h04_p0_family_errors"] = family_error_rates(rh)
    out = HERE / "params_from_dev.json"
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    def show(title, d):
        print(f"\n## {title}")
        for k, v in d.items():
            print(f"  {k}: {v}")

    nr, rs = res["nonreasoning"], res["reasoning"]
    show("non-reasoning standard families, P0 errors on flawed/present", nr["standard_family_errors"])
    print("  clustering rho:", nr["standard_clustering"]["rho"])
    show("non-reasoning standard, branching repair/damage", nr["standard_branching"])
    show("non-reasoning standard, overturn and pause (independent runs)", nr["standard_overturn_pause"])
    show("non-reasoning hard screens H01-H12, P0 errors on flawed/present", nr["hard_family_errors"])
    show("non-reasoning H04 branching, P0 errors", nr["h04_family_errors"])
    print("  H04 clustering rho:", nr["h04_clustering"]["rho"], " items:", nr["h04_clustering"]["items"])
    show("non-reasoning H04 branching repair/damage (flawed advice)", nr["h04_branching_flawed"])
    show("non-reasoning H04 branching repair/damage (all evidence-present)", nr["h04_branching_all"])
    show("non-reasoning H04 overturn and pause", nr["h04_overturn_pause"])
    show("reasoning branching, P0 errors on flawed/present", rs["family_errors"])
    show("reasoning branching repair/damage", rs["branching"])
    show("reasoning overturn and pause", rs["overturn_pause"])
    show("reasoning H04 P0 probe", rs["h04_p0_family_errors"])
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
