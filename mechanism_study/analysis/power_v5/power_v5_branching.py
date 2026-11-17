"""Simulation-based power for Phase 3 of proposal v5 (branching design, one model, two modes).

Every procedure reviews the same first answer, so the simulation draws first answers once and
then the review outcome of each procedure on those answers. Inputs come from
params_from_dev.json (estimate_params.py); values that development could not estimate are
scenario assumptions and are labelled as such in the output.

Hypotheses simulated (as written in v5, Section 3.7.3):
  H1  crossover on the hard tier: family-level repair difference P5 - P3 in rule-condition
      families minus the same difference in source-applicability families, two-sided exact or
      Monte Carlo permutation test over error-type labels, alpha .05; families without an
      incorrect first answer do not contribute. Tested only if a testability rule is met.
      Also on authored drafts (every family contributes, no gate).
  H3  non-inferiority of P3 and P5 to P0 on overturning aligned advice, all families:
      one-sided 95% t upper bound of the family-level difference < 0.05 for both.
  H4  boundary on the standard tier: for each of P1-P5, one-sided 95% t upper bound of the
      family-level gain over P0 (flawed advice, evidence present) < 0.10; holds only if all do.
  H2  escalation interaction (P3 - P1 when missing minus when present), all families, two-sided
      t-test on family-level interactions, alpha .05.

Usage: python power_v5_branching.py [--nsim 1000] [--seed 20261109]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ALPHA = 0.05
STATES_PRESENT = 4          # base, decisive change, irrelevant change, paraphrase
ADVICE_MISSING = 2          # aligned and flawed advice in the missing-evidence state
PROCS = ["P1", "P2", "P3", "P4", "P5"]


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ----------------------------------------------------------------------------- inputs
def dev_inputs():
    par = json.loads((HERE / "params_from_dev.json").read_text(encoding="utf-8"))
    nr = par["nonreasoning"]
    hard = nr["hard_family_errors"]
    others = {k: v for k, v in hard.items() if k != "H04"}
    p_low = sum(v["errors"] for v in others.values()) / sum(v["n"] for v in others.values())
    h04 = nr["h04_family_errors"]["H04"]
    p_high = h04["errors"] / h04["n"]
    rho = nr["h04_clustering"]["rho"]
    rep = nr["h04_branching_flawed"]
    r_rule = {k: v["repaired"] / v["first_wrong"] for k, v in rep.items() if v["first_wrong"]}
    std = nr["standard_family_errors"]
    std_err = sum(v["errors"] for v in std.values()) / sum(v["n"] for v in std.values())
    std_hi = max(v["errors"] / v["n"] for v in std.values())
    damage_obs = [0, 0]
    for blk in (nr["standard_branching"], nr["h04_branching_all"], par["reasoning"]["branching"]):
        for v in blk.values():
            damage_obs[0] += v["damaged"]
            damage_obs[1] += v["first_right"]
    esc = nr["standard_overturn_pause"]["P0"]["missing_escalated"]
    return {"p_low": p_low, "p_high": p_high, "pi_dev": 1 / len(hard), "rho": rho,
            "r_rule": r_rule, "std_err": std_err, "std_hi": std_hi,
            "damage_obs": damage_obs, "esc_missing_p0": esc[0] / esc[1]}


# ----------------------------------------------------------------------------- helpers
def beta_items(rng, p, rho, shape):
    """Item-level error probabilities around family rate p with intraclass correlation rho."""
    if rho is None or rho <= 0:
        return np.broadcast_to(p, shape).copy()
    k = 1 / rho - 1
    a = np.maximum(p * k, 1e-6)
    b = np.maximum((1 - p) * k, 1e-6)
    return rng.beta(np.broadcast_to(a, shape), np.broadcast_to(b, shape))


_perm_cache: dict = {}


def perm_matrix(n, n1, rng, b=2000):
    key = (n, n1)
    if key not in _perm_cache:
        total = math.comb(n, n1)
        if total <= 5000:
            m = np.zeros((total, n))
            for i, c in enumerate(itertools.combinations(range(n), n1)):
                m[i, list(c)] = 1
        else:
            m = np.zeros((b, n))
            for i in range(b):
                m[i, rng.choice(n, n1, replace=False)] = 1
        _perm_cache[key] = m
    return _perm_cache[key]


def perm_p(d, is_rule, rng):
    n1, n = int(is_rule.sum()), len(d)
    if n1 == 0 or n1 == n:
        return 1.0
    n2 = n - n1
    obs = d[is_rule].mean() - d[~is_rule].mean()
    m = perm_matrix(n, n1, rng)
    s1 = m @ d
    stat = s1 / n1 - (d.sum() - s1) / n2
    # Observed labelling is one of the enumerated ones; for Monte Carlo add it explicitly.
    if m.shape[0] < math.comb(n, n1):
        return (np.sum(np.abs(stat) >= abs(obs) - 1e-12) + 1) / (m.shape[0] + 1)
    return np.mean(np.abs(stat) >= abs(obs) - 1e-12)


def upper_bound(x, axis=1):
    """One-sided 95% t upper bound of the mean along axis (rows = simulations)."""
    n = x.shape[axis]
    m = x.mean(axis=axis)
    s = x.std(axis=axis, ddof=1)
    return m + stats.t.ppf(0.95, n - 1) * s / np.sqrt(n)


# ----------------------------------------------------------------------------- H1
REPAIR_SCENARIOS = {
    # (type, procedure) -> repair probability of an incorrect first answer.
    # Rule-condition values for P1-P4 are the H04 estimates; everything else is assumed.
    "strong crossover": {"rule": {"P3": None, "P5": "P1"}, "src": {"P3": 0.62, "P5": 0.08}},
    "moderate crossover": {"rule": {"P3": 0.20, "P5": 0.50}, "src": {"P3": 0.50, "P5": 0.20}},
    "rule-side only": {"rule": {"P3": None, "P5": "P1"}, "src": {"P3": 0.35, "P5": 0.35}},
    "no crossover": {"rule": {"P3": 0.35, "P5": 0.35}, "src": {"P3": 0.35, "P5": 0.35}},
}


def resolve(scn, r_rule):
    out = {}
    for t in ("rule", "src"):
        out[t] = {}
        for k, v in scn[t].items():
            if v is None:
                out[t][k] = r_rule[k]          # H04 estimate for this procedure
            elif isinstance(v, str):
                out[t][k] = r_rule[v]          # borrow another procedure's H04 estimate
            else:
                out[t][k] = v
    return out


def sim_h1(rng, nsim, n_type, reps, pi, p_high, p_low, rho, rates, sd_fam=0.5, sd_proc=0.3,
           draft_reps=3, draft_rates=None):
    n = 2 * n_type
    is_rule = np.r_[np.ones(n_type, bool), np.zeros(n_type, bool)]
    high = rng.random((nsim, n)) < pi
    p_fam = np.where(high, p_high, p_low)
    p_item = beta_items(rng, p_fam[:, :, None], rho, (nsim, n, STATES_PRESENT))
    errs = rng.binomial(reps, p_item).sum(axis=2)                     # (nsim, n)
    u = rng.normal(0, sd_fam, (nsim, n))

    def repairs(n_trials, proc, rates_):
        base = np.where(is_rule, rates_["rule"][proc], rates_["src"][proc])
        r = expit(logit(base)[None, :] + u + rng.normal(0, sd_proc, (nsim, n)))
        return rng.binomial(n_trials, r)

    rep3, rep5 = repairs(errs, "P3", rates), repairs(errs, "P5", rates)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = (rep5 - rep3) / errs
    out = {
        "E_rule": errs[:, is_rule].sum(1), "E_src": errs[:, ~is_rule].sum(1),
        "C1_rule": (errs[:, is_rule] >= 1).sum(1), "C1_src": (errs[:, ~is_rule] >= 1).sum(1),
        "C2_rule": (errs[:, is_rule] >= 2).sum(1), "C2_src": (errs[:, ~is_rule] >= 2).sum(1),
    }
    p = np.ones(nsim)
    for i in range(nsim):
        keep = errs[i] >= 1
        if keep[is_rule].sum() >= 2 and keep[~is_rule].sum() >= 2:
            p[i] = perm_p(d[i, keep], is_rule[keep], rng)
    out["p"] = p
    # Authored drafts: every family has STATES_PRESENT error drafts, reviewed draft_reps times.
    dr = draft_rates or rates
    nd = STATES_PRESENT * draft_reps
    a3, a5 = repairs(np.full((nsim, n), nd), "P3", dr), repairs(np.full((nsim, n), nd), "P5", dr)
    da = (a5 - a3) / nd
    pd_ = np.ones(nsim)
    for i in range(nsim):
        pd_[i] = perm_p(da[i], is_rule, rng)
    out["p_draft"] = pd_
    return out


TESTABILITY = {
    "A: >=20 errors and >=5 families per type": lambda o: (o["E_rule"] >= 20) & (o["E_src"] >= 20) & (o["C1_rule"] >= 5) & (o["C1_src"] >= 5),
    "B: >=5 families with >=2 errors per type": lambda o: (o["C2_rule"] >= 5) & (o["C2_src"] >= 5),
    "C: >=4 families with >=2 errors per type": lambda o: (o["C2_rule"] >= 4) & (o["C2_src"] >= 4),
    "D: >=4 families with >=1 error per type": lambda o: (o["C1_rule"] >= 4) & (o["C1_src"] >= 4),
}


# ----------------------------------------------------------------------------- H3, H4, H2
def sim_h3(rng, nsim, n_fam, reps, o0, d, r_al=0.3, sd=0.5):
    """Overturning of aligned advice: review minus baseline, family level, for P3 and P5."""
    n_items = STATES_PRESENT * reps
    first_over = rng.binomial(n_items, np.broadcast_to(o0, (nsim, n_fam)))
    ok = []
    for _ in ("P3", "P5"):
        dfam = expit(logit(max(d, 1e-6)) + rng.normal(0, sd, (nsim, n_fam))) if d > 0 else np.zeros((nsim, n_fam))
        damaged = rng.binomial(n_items - first_over, dfam)
        repaired = rng.binomial(first_over, r_al)
        diff = (damaged - repaired) / n_items
        ok.append(upper_bound(diff) < 0.05)
    return ok[0] & ok[1]


def sim_h4(rng, nsim, n_fam, reps, pi_hi, p_hi, p_lo, repair, d=0.0, sd=0.5):
    """Standard tier: H4 holds if every procedure's upper bound of gain over P0 is < 0.10."""
    n_items = STATES_PRESENT * reps
    p_fam = np.where(rng.random((nsim, n_fam)) < pi_hi, p_hi, p_lo)
    wrong = rng.binomial(n_items, p_fam)
    u = rng.normal(0, sd, (nsim, n_fam))
    holds = np.ones(nsim, bool)
    gains = {}
    for proc, r in repair.items():
        rf = expit(logit(r) + u)
        rep = rng.binomial(wrong, rf)
        dam = rng.binomial(n_items - wrong, d) if d > 0 else 0
        g = (rep - dam) / n_items
        gains[proc] = g.mean()
        holds &= upper_bound(g) < 0.10
    return holds, gains


def sim_h2(rng, nsim, n_fam, reps, e0, c1, c3, sd=0.5):
    """Escalation interaction; present-evidence escalation assumed unchanged by review (dev: 0)."""
    n_items = ADVICE_MISSING * reps
    not_esc = rng.binomial(n_items, 1 - e0, (nsim, n_fam))
    u = rng.normal(0, sd, (nsim, n_fam))
    conv1 = rng.binomial(not_esc, expit(logit(c1) + u))
    conv3 = rng.binomial(not_esc, expit(logit(c3) + u))
    inter = (conv3 - conv1) / n_items
    t = inter.mean(1) / (inter.std(1, ddof=1) / np.sqrt(n_fam) + 1e-12)
    p = 2 * stats.t.sf(np.abs(t), n_fam - 1)
    return (p < ALPHA) & (inter.mean(1) > 0)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsim", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261109)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    t0 = time.time()
    dev = dev_inputs()
    print("development inputs:", json.dumps(dev, indent=1))
    rows = []

    # ---------------- H1, non-reasoning mode
    designs = [(10, 3), (10, 6), (10, 8), (15, 3), (15, 6), (20, 3), (20, 6)]
    pis = [dev["pi_dev"], 0.25, 0.5, 1.0]
    for scn_name, scn in REPAIR_SCENARIOS.items():
        rates = resolve(scn, dev["r_rule"])
        for n_type, reps in designs:
            for pi in pis:
                o = sim_h1(rng, args.nsim, n_type, reps, pi, dev["p_high"], dev["p_low"], dev["rho"], rates)
                sig = o["p"] < ALPHA
                for rule, f in TESTABILITY.items():
                    tst = f(o)
                    rows.append({"hyp": "H1", "mode": "reasoning off", "scenario": scn_name,
                                 "families_per_type": n_type, "repeats": reps, "pi": round(pi, 3),
                                 "rule": rule, "p_testable": tst.mean(),
                                 "power_unconditional": (tst & sig).mean(),
                                 "power_if_testable": (tst & sig).sum() / max(tst.sum(), 1),
                                 "mean_errors_per_type": (o["E_rule"].mean() + o["E_src"].mean()) / 2,
                                 "power_authored_drafts": (o["p_draft"] < ALPHA).mean()})
        print(f"H1 {scn_name} done ({time.time() - t0:.0f}s)")

    # ---------------- H1, reasoning mode (development: 0 errors in 132 evidence-present first answers)
    rates = resolve(REPAIR_SCENARIOS["strong crossover"], dev["r_rule"])
    for n_type, reps in [(10, 3), (10, 8), (20, 6)]:
        o = sim_h1(rng, args.nsim, n_type, reps, 1.0, 0.03, 0.003, dev["rho"], rates)
        for rule, f in TESTABILITY.items():
            tst = f(o)
            rows.append({"hyp": "H1", "mode": "reasoning on", "scenario": "strong crossover",
                         "families_per_type": n_type, "repeats": reps, "pi": "all at 0.03",
                         "rule": rule, "p_testable": tst.mean(),
                         "power_unconditional": (tst & (o["p"] < ALPHA)).mean(),
                         "power_if_testable": np.nan, "mean_errors_per_type": (o["E_rule"].mean() + o["E_src"].mean()) / 2,
                         "power_authored_drafts": (o["p_draft"] < ALPHA).mean()})
    # Authored drafts at the ceiling (as with the second provider): repairs of 0.95 by every procedure.
    ceil = {"rule": {"P3": 0.95, "P5": 0.95}, "src": {"P3": 0.95, "P5": 0.95}}
    o = sim_h1(rng, args.nsim, 10, 3, 0.08, dev["p_high"], dev["p_low"], dev["rho"], rates, draft_rates=ceil)
    rows.append({"hyp": "H1", "mode": "reasoning off", "scenario": "authored drafts at ceiling (0.95 all)",
                 "families_per_type": 10, "repeats": 3, "pi": 0.08, "rule": "-", "p_testable": np.nan,
                 "power_unconditional": np.nan, "power_if_testable": np.nan, "mean_errors_per_type": np.nan,
                 "power_authored_drafts": (o["p_draft"] < ALPHA).mean()})
    print(f"H1 reasoning and ceiling done ({time.time() - t0:.0f}s)")

    # ---------------- H3 (all families; standard reps 3, hard reps as design)
    for n_fam in (30, 40, 50):
        for d in (0.0, 0.01, 0.02, 0.03, 0.04):
            ok = sim_h3(rng, args.nsim, n_fam, 3, 0.03, d)
            rows.append({"hyp": "H3", "mode": "reasoning off", "scenario": f"damage {d:.2f}",
                         "families_per_type": n_fam, "repeats": 3, "pi": "", "rule": "",
                         "p_testable": np.nan, "power_unconditional": ok.mean(),
                         "power_if_testable": np.nan, "mean_errors_per_type": np.nan, "power_authored_drafts": np.nan})
    print(f"H3 done ({time.time() - t0:.0f}s)")

    # ---------------- H4 (standard tier)
    r_dev = {"P1": dev["r_rule"]["P1"], "P2": dev["r_rule"]["P2"], "P3": dev["r_rule"]["P3"],
             "P4": dev["r_rule"]["P4"], "P5": dev["r_rule"]["P1"]}
    h4_scen = {
        "development-like (mean baseline error about 3%)": (0.125, dev["std_hi"], 0.003, r_dev),
        "true gain about 10 points for P1 and P5": (1.0, 0.16, 0.16, r_dev),
        "true gain about 5 points for P1 and P5": (1.0, 0.08, 0.08, r_dev),
    }
    for n_fam in (10, 20, 30):
        for name, (pih, ph, pl, rep) in h4_scen.items():
            holds, gains = sim_h4(rng, args.nsim, n_fam, 3, pih, ph, pl, rep)
            rows.append({"hyp": "H4", "mode": "reasoning off", "scenario": name, "families_per_type": n_fam,
                         "repeats": 3, "pi": "", "rule": f"mean gain P1 {gains['P1']:.3f}",
                         "p_testable": np.nan, "power_unconditional": holds.mean(), "power_if_testable": np.nan,
                         "mean_errors_per_type": np.nan, "power_authored_drafts": np.nan})
    print(f"H4 done ({time.time() - t0:.0f}s)")

    # ---------------- H2 (all families)
    e0 = dev["esc_missing_p0"]
    for n_fam in (40, 60):
        for c1, c3, name in ((0.3, 0.3, "no effect"), (0.3, 0.6, "P3 converts 60% vs 30% of non-pauses"),
                             (0.3, 0.9, "P3 converts 90% vs 30%")):
            pw = sim_h2(rng, args.nsim, n_fam, 3, e0, c1, c3).mean()
            rows.append({"hyp": "H2", "mode": "reasoning off", "scenario": f"{name}; baseline pauses {e0:.2f}",
                         "families_per_type": n_fam, "repeats": 3, "pi": "", "rule": "",
                         "p_testable": np.nan, "power_unconditional": pw, "power_if_testable": np.nan,
                         "mean_errors_per_type": np.nan, "power_authored_drafts": np.nan})
    print(f"H2 done ({time.time() - t0:.0f}s)")

    # ---------------- recommended design: 20 standard + 30 hard families (15 per error type);
    # hard tier 6 repeats with reasoning off, 3 with reasoning on; testability rule D.
    rec = []
    rule_d = TESTABILITY["D: >=4 families with >=1 error per type"]
    for scn_name, scn in REPAIR_SCENARIOS.items():
        rates = resolve(scn, dev["r_rule"])
        for pi in pis:
            o = sim_h1(rng, args.nsim, 15, 6, pi, dev["p_high"], dev["p_low"], dev["rho"], rates)
            tst, sig = rule_d(o), o["p"] < ALPHA
            rec.append({"hyp": "H1", "mode": "reasoning off", "scenario": scn_name, "pi": round(pi, 3),
                        "p_testable": tst.mean(), "power": (tst & sig).mean(),
                        "power_if_testable": (tst & sig).sum() / max(tst.sum(), 1),
                        "power_authored_drafts": (o["p_draft"] < ALPHA).mean()})
        o = sim_h1(rng, args.nsim, 15, 3, 1.0, 0.03, 0.003, dev["rho"], rates)
        tst, sig = rule_d(o), o["p"] < ALPHA
        rec.append({"hyp": "H1", "mode": "reasoning on (optimistic: 3% error in every family)", "scenario": scn_name,
                    "pi": "", "p_testable": tst.mean(), "power": (tst & sig).mean(),
                    "power_if_testable": (tst & sig).sum() / max(tst.sum(), 1),
                    "power_authored_drafts": (o["p_draft"] < ALPHA).mean()})
    for d in (0.0, 0.01, 0.02, 0.03):
        rec.append({"hyp": "H3", "mode": "either", "scenario": f"damage {d:.2f}", "pi": "",
                    "power": sim_h3(rng, args.nsim, 50, 3, 0.03, d).mean()})
    for name, (pih, ph, pl, rep) in h4_scen.items():
        holds, _ = sim_h4(rng, args.nsim, 20, 3, pih, ph, pl, rep)
        rec.append({"hyp": "H4", "mode": "reasoning off", "scenario": name, "pi": "", "power": holds.mean()})
    for c1, c3, name in ((0.3, 0.3, "no effect"), (0.3, 0.6, "P3 converts 60% vs 30% of non-pauses"),
                         (0.3, 0.9, "P3 converts 90% vs 30%")):
        rec.append({"hyp": "H2", "mode": "reasoning off", "scenario": name, "pi": "",
                    "power": sim_h2(rng, args.nsim, 50, 3, e0, c1, c3).mean()})
    pd.DataFrame(rec).to_csv(HERE / "power_v5_recommended.csv", index=False, encoding="utf-8")
    print(f"recommended design done ({time.time() - t0:.0f}s)")

    df = pd.DataFrame(rows)
    df.to_csv(HERE / "power_v5_results.csv", index=False, encoding="utf-8")
    (HERE / "power_v5_inputs.json").write_text(json.dumps({"nsim": args.nsim, "seed": args.seed, **dev}, indent=1), encoding="utf-8")
    print(f"wrote {len(df)} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
