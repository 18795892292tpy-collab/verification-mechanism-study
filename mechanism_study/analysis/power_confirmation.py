"""Simulation-based power for the confirmation set (computational experiment).

Data are generated with the model in simulate_synthetic.py (family, procedure-by-family,
item, model-by-item and cell random effects; marginal rates calibrated to targets) and
analysed exactly as in analyze.py: family-level paired differences, two-sided t-tests,
Holm over C1-C3, NI bounds from 95% t-intervals. Responses are aggregated with exact
binomial draws per model x item x procedure cell, which is equivalent to simulating
every repeat but much faster.

Contrasts (as in analysis_plan.md):
  C1  P3 - P1 flawed_correction (evidence present)
  C2  P3 - P2 flawed_correction
  C3  [escalation P3 - P1 | evidence absent] - [P3 - P1 | evidence present]
  NI1 P3 - P0 aligned_overturn            upper 95% bound < +0.05
  NI2 P3 - P0 irrelevant_stability | base correct (pooled over advice) lower 95% bound > -0.05

Usage:
  python power_confirmation.py [--nsim 1000] [--out DIR] [--quick]
  python power_confirmation.py --from-dev dev/scored_runs.csv   # re-estimate inputs
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simulate_synthetic as gen  # noqa: E402

ALPHA = 0.05
MARGIN_AO, MARGIN_ST = 0.05, 0.05
P_IDX = [0, 1, 2, 3]   # P4 is exploratory and outside the confirmatory family


# ----------------------------------------------------------------------------
# Fast aggregated simulation of family-level outcomes
# ----------------------------------------------------------------------------
def family_outcomes(par, F, M, R, nsim, rng, batch=250):
    mus = gen.calibrated_mus(par, M)
    acc = {k: [] for k in ("FC", "AO", "EA", "EP", "ST")}
    done = 0
    while done < nsim:
        S = min(batch, nsim - done)
        pr = gen.draw_latent_probs(par, mus, S, M, F, rng, procs=P_IDX)
        pe, pc = pr["esc"], pr["cne"]                       # (S, M, F, I, P)
        n_esc = rng.binomial(R, pe)
        n_cor = rng.binomial(R - n_esc, pc)
        acc["FC"].append(n_cor[:, :, :, gen.I_PF, :].sum(axis=(1, 3)) / (M * 4 * R))
        acc["AO"].append(1 - n_cor[:, :, :, gen.I_PA, :].sum(axis=(1, 3)) / (M * 4 * R))
        acc["EA"].append(n_esc[:, :, :, gen.I_ABSENT, :].sum(axis=(1, 3)) / (M * 2 * R))
        acc["EP"].append(n_esc[:, :, :, gen.I_PRESENT, :].sum(axis=(1, 3)) / (M * 8 * R))
        pcor = (1 - pe) * pc
        kb = rng.binomial(R, pcor[:, :, :, [0, 1], :])          # base correct (aligned, flawed)
        st = rng.binomial(kb, pcor[:, :, :, [4, 5], :])         # irrelevant also correct (= same action)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = st.sum(axis=(1, 3)) / kb.sum(axis=(1, 3))
        acc["ST"].append(np.where(np.isfinite(ratio), ratio, np.nan))
        done += S
    return {k: np.concatenate(v, axis=0) for k, v in acc.items()}   # (nsim, F, 4)


def ttest_rows(d):
    """d: (nsim, F) family-level differences -> mean, se, two-sided p, t-quantile.
    Families with an undefined value (NaN) are dropped, as in analyze.py."""
    if np.isnan(d).any():
        n = np.isfinite(d).sum(axis=1)
        m = np.nanmean(d, axis=1)
        se = np.nanstd(d, axis=1, ddof=1) / np.sqrt(n)
        F = int(np.median(n))
    else:
        F = d.shape[1]
        m = d.mean(axis=1)
        se = d.std(axis=1, ddof=1) / np.sqrt(F)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, m / se, 0.0)
    p = 2 * stats.t.sf(np.abs(t), F - 1)
    return m, se, p, stats.t.ppf(0.975, F - 1)


def holm3(p):
    """p: (nsim, 3) -> boolean rejections under Holm at ALPHA."""
    order = np.argsort(p, axis=1)
    ps = np.take_along_axis(p, order, axis=1)
    thr = ALPHA / np.array([3, 2, 1])
    ok = np.cumprod(ps < thr, axis=1).astype(bool)
    rej = np.zeros_like(ok)
    np.put_along_axis(rej, order, ok, axis=1)
    return rej


def evaluate(out):
    FC, AO, EA, EP, ST = (out[k] for k in ("FC", "AO", "EA", "EP", "ST"))
    d1 = FC[..., 3] - FC[..., 1]
    d2 = FC[..., 3] - FC[..., 2]
    d3 = (EA[..., 3] - EA[..., 1]) - (EP[..., 3] - EP[..., 1])
    n1 = AO[..., 3] - AO[..., 0]
    n2 = ST[..., 3] - ST[..., 0]
    res = {}
    ests, ps = [], []
    for name, d in (("C1", d1), ("C2", d2), ("C3", d3)):
        m, se, p, _ = ttest_rows(d)
        ests.append(m); ps.append(p)
        res[f"{name}_est"] = m.mean()
        res[f"{name}_se"] = se.mean()
        res[f"{name}_unadj"] = np.mean((p < ALPHA) & (m > 0))
        res[f"{name}_twosided"] = np.mean(p < ALPHA)
    rej = holm3(np.column_stack(ps)) & (np.column_stack(ests) > 0)
    for j, name in enumerate(("C1", "C2", "C3")):
        res[f"{name}_holm"] = rej[:, j].mean()
    m, se, _, tq = ttest_rows(n1)
    ni1 = (m + tq * se) < MARGIN_AO
    res["NI1_est"], res["NI1_se"], res["NI1_pass"] = m.mean(), se.mean(), ni1.mean()
    m, se, _, tq = ttest_rows(n2)
    ni2 = (m - tq * se) > -MARGIN_ST
    res["NI2_est"], res["NI2_se"], res["NI2_pass"] = m.mean(), se.mean(), ni2.mean()
    res["adopt_C1_NI"] = np.mean(rej[:, 0] & ni1 & ni2)          # C1 + both NI
    res["adopt_full"] = np.mean(rej[:, 0] & rej[:, 1] & ni1 & ni2)  # ADOPT rule (C1 & C2 & NI)
    return res


def run_scenario(par, F, M, R, nsim, seed):
    rng = np.random.default_rng(seed)
    r = evaluate(family_outcomes(par, F, M, R, nsim, rng))
    r.update(F=F, M=M, R=R, nsim=nsim)
    return r


# ----------------------------------------------------------------------------
# Checks: sign-flip agreement, GEE on a subset
# ----------------------------------------------------------------------------
def signflip_check(par, F, M, R, nsim, seed, n_flip=2000):
    rng = np.random.default_rng(seed)
    out = family_outcomes(par, F, M, R, nsim, rng)
    d = out["FC"][..., 3] - out["FC"][..., 1]
    _, _, p_t, _ = ttest_rows(d)
    signs = rng.choice([-1.0, 1.0], size=(n_flip, F))
    stat = np.abs(d @ signs.T) / F                      # (nsim, n_flip)
    obs = np.abs(d.mean(axis=1))[:, None]
    p_sf = ((stat >= obs - 1e-12).sum(axis=1) + 1) / (n_flip + 1)
    return dict(F=F, effect=par["effect"], nsim=nsim, reject_t=np.mean(p_t < ALPHA),
                reject_signflip=np.mean(p_sf < ALPHA), agreement=np.mean((p_t < ALPHA) == (p_sf < ALPHA)))


def gee_check(par, F, M, R, nsim, seed):
    """Response-level GEE (binomial, exchangeable within family, bias-reduced SE) for C1,
    compared with the family-level t-test on the same simulated responses."""
    import statsmodels.api as sm
    rng = np.random.default_rng(seed)
    mus = gen.calibrated_mus(par, M)
    rej_t = rej_g = fails = 0
    for _ in range(nsim):
        pr = gen.draw_latent_probs(par, mus, 1, M, F, rng, procs=[1, 3])
        pcor = ((1 - pr["esc"]) * pr["cne"])[0][:, :, gen.I_PF, :]       # (M, F, 4, 2)
        y = rng.random((R,) + pcor.shape) < pcor[None]                    # (R, M, F, 4, 2)
        Rr, Mm, Ff, Ii, Pp = y.shape
        fam = np.broadcast_to(np.arange(Ff)[None, None, :, None, None], y.shape).ravel()
        mod = np.broadcast_to(np.arange(Mm)[None, :, None, None, None], y.shape).ravel()
        trt = np.broadcast_to(np.arange(Pp)[None, None, None, None, :], y.shape).ravel()
        yy = y.ravel().astype(float)
        fm = y.mean(axis=(0, 1, 3))                                       # (F, 2)
        d = fm[:, 1] - fm[:, 0]
        p_t = stats.ttest_1samp(d, 0).pvalue
        rej_t += p_t < ALPHA
        X = np.column_stack([np.ones_like(yy), trt] + [(mod == j).astype(float) for j in range(1, Mm)])
        order = np.argsort(fam, kind="stable")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = sm.GEE(yy[order], X[order], groups=fam[order], family=sm.families.Binomial(),
                           cov_struct=sm.cov_struct.Exchangeable()).fit(cov_type="bias_reduced")
            rej_g += r.pvalues[1] < ALPHA
        except Exception:
            fails += 1
    return dict(F=F, effect=par["effect"], nsim=nsim, reject_family_t=rej_t / nsim,
                reject_gee=rej_g / nsim, gee_failures=fails)


# ----------------------------------------------------------------------------
# Development-data calibration (--from-dev)
# ----------------------------------------------------------------------------
def dev_summaries(path):
    import analyze as an
    df = an.load(path)
    df = df[df.procedure.isin(["P0", "P1", "P2", "P3"])]
    fams = sorted(df.family_id.unique())
    F, M, R = len(fams), df.model.nunique(), int(df["repeat"].max())

    def tab(d, y):
        g = d.dropna(subset=[y]).groupby(["family_id", "procedure", "model"])[y].mean()
        return g.groupby(["family_id", "procedure"]).mean().unstack()

    FC, AO = tab(df, "flawed_correction"), tab(df, "aligned_overturn")
    UE = tab(df, "unnecessary_escalation")
    miss = df[df.state == "missing"]
    EAa = tab(miss[miss.advice == "aligned"], "escalated")
    EAf = tab(miss[miss.advice == "flawed"], "escalated")
    rates = {k: t.mean().to_dict() for k, t in
             dict(FC=FC, AC=1 - AO, EP=UE, EAa=EAa, EAf=EAf).items()}
    pf = df[(df.evidence == "present") & (df.advice == "flawed")]
    g = pf.groupby(["model", "family_id", "state", "procedure"]).correct.agg(["sum", "count"])
    g = g[g["count"] >= 2]
    k, n = g["sum"], g["count"]
    agree = ((k * (k - 1) + (n - k) * (n - k - 1)) / (n * (n - 1))).mean() if len(g) else np.nan
    stats_obs = dict(
        rep_agree=float(agree),
        sd_fam=float(FC["P0"].std(ddof=1)),
        sd_diff=float(np.mean([(FC["P1"] - FC["P0"]).std(ddof=1), (FC["P2"] - FC["P1"]).std(ddof=1),
                               (FC["P3"] - FC["P1"]).std(ddof=1)])))
    dev_d1 = (FC["P3"] - FC["P1"]).to_numpy()
    return dict(F=F, M=M, R=R, rates=rates, stats=stats_obs, d1=dev_d1)


def par_from_rates(rates, base=None):
    clip = lambda x: float(np.clip(x, 0.02, 0.98))
    par = gen.params_with() if base is None else dict(base)
    par["correct_present_flawed"] = {p: clip(rates["FC"][p]) for p in ("P0", "P1", "P2")}
    # conservative for C2: never plan with P2 below P1 + 2 points (dev P1/P2 rates are noisy)
    cpf = par["correct_present_flawed"]
    cpf["P2"] = max(cpf["P2"], cpf["P1"] + 0.02)
    par["correct_present_aligned"] = {p: clip(rates["AC"][p]) for p in ("P0", "P1", "P2", "P3")}
    par["correct_present_aligned"]["P4"] = par["correct_present_aligned"]["P1"]
    par["esc_present"] = {p: clip(rates["EP"][p]) for p in ("P0", "P1", "P2")}
    par["esc_present"]["P4"] = par["esc_present"]["P1"]
    par["esc_absent_aligned"] = {p: clip(rates["EAa"][p]) for p in ("P0", "P1", "P2")}
    par["esc_absent_flawed"] = {p: clip(rates["EAf"][p]) for p in ("P0", "P1", "P2")}
    # keep correct + unnecessary escalation < 1
    for p, v in par["correct_present_aligned"].items():
        par["correct_present_aligned"][p] = min(v, 0.99 - par["esc_present"].get(p, par["esc_present"]["P1"]))
    return par


def sim_dev_stats(par, F, M, R, nsim, rng):
    mus = gen.calibrated_mus(par, M)
    pr = gen.draw_latent_probs(par, mus, nsim, M, F, rng, procs=P_IDX)
    pcor = (1 - pr["esc"]) * pr["cne"]
    pf = pcor[:, :, :, gen.I_PF, :]
    agree = float((pf ** 2 + (1 - pf) ** 2).mean())
    n_esc = rng.binomial(R, pr["esc"])
    n_cor = rng.binomial(R - n_esc, pr["cne"])
    FC = n_cor[:, :, :, gen.I_PF, :].sum(axis=(1, 3)) / (M * 4 * R)
    sd_fam = FC[..., 0].std(axis=1, ddof=1).mean()
    sd_diff = np.mean([(FC[..., 1] - FC[..., 0]).std(axis=1, ddof=1).mean(),
                       (FC[..., 2] - FC[..., 1]).std(axis=1, ddof=1).mean(),
                       (FC[..., 3] - FC[..., 1]).std(axis=1, ddof=1).mean()])
    return dict(rep_agree=agree, sd_fam=float(sd_fam), sd_diff=float(sd_diff))


def calibrate_from_dev(path, nsim=200, seed=99):
    dv = dev_summaries(path)
    F, M, R = dv["F"], dv["M"], dv["R"]
    par = par_from_rates(dv["rates"])
    par["effect"] = float(np.clip(dv["rates"]["FC"]["P3"] - dv["rates"]["FC"]["P1"], -0.3, 0.3))
    rng = np.random.default_rng(seed)
    grids = {"sd_model_item": np.arange(0.5, 3.75, 0.25),
             "sd_family": np.arange(0.25, 2.01, 0.125),
             "sd_slope": np.arange(0.0, 1.26, 0.125)}
    target = {"sd_model_item": "rep_agree", "sd_family": "sd_fam", "sd_slope": "sd_diff"}
    obs = dv["stats"]
    for _ in range(2):  # coordinate descent
        for key, grid in grids.items():
            if not np.isfinite(obs[target[key]]):
                continue
            errs = []
            for v in grid:
                pp = dict(par); pp[key] = float(v)
                s = sim_dev_stats(pp, F, M, R, nsim, rng)
                errs.append(abs(s[target[key]] - obs[target[key]]))
            par[key] = float(grid[int(np.argmin(errs))])
    par["effect"] = gen.DEFAULTS["effect"]
    return par, dv


def resampling_power(d1, F_new, delta, nsim, seed):
    """Nonparametric check: resample centred development family differences (+delta)."""
    rng = np.random.default_rng(seed)
    d = d1[np.isfinite(d1)]
    d = d - d.mean() + delta
    samp = d[rng.integers(0, len(d), size=(nsim, F_new))]
    _, _, p, _ = ttest_rows(samp)
    return float(np.mean((p < ALPHA / 3) & (samp.mean(axis=1) > 0)))


# ----------------------------------------------------------------------------
# Grids and report
# ----------------------------------------------------------------------------
FAMS = [16, 24, 32, 40, 60]


def run_grids(par0, nsim, out, label, quick=False):
    seed = 1000
    rows = []
    t0 = time.time()
    fams = [16, 40] if quick else FAMS
    # A: design (families x repeats x models)
    for F in fams:
        for R in ([1, 3] if quick else [1, 3, 5]):
            for M in ([3] if quick else [1, 2, 3]):
                seed += 1
                rows.append(dict(grid="A_design", effect=par0["effect"], interaction=par0["interaction"],
                                 sd_family=par0["sd_family"], sd_slope=par0["sd_slope"],
                                 **run_scenario(par0, F, M, R, nsim, seed)))
    # B: effect sizes
    for F in fams:
        for e in ([0.10] if quick else [0.05, 0.10, 0.15, 0.20]):
            seed += 1
            par = dict(par0); par["effect"] = e; par["interaction"] = e
            rows.append(dict(grid="B_effect", effect=e, interaction=e, sd_family=par["sd_family"],
                             sd_slope=par["sd_slope"], **run_scenario(par, F, 3, 3, nsim, seed)))
    # C: heterogeneity
    for F in fams:
        for sf in ([1.0] if quick else [0.5, 1.0, 1.5]):
            for ss in ([0.25, 0.75] if quick else [0.25, 0.5, 0.75]):
                seed += 1
                par = dict(par0); par["sd_family"] = sf; par["sd_slope"] = ss
                rows.append(dict(grid="C_heterogeneity", effect=par["effect"], interaction=par["interaction"],
                                 sd_family=sf, sd_slope=ss, **run_scenario(par, F, 3, 3, nsim, seed)))
    # D: NI sensitivity (true P3 aligned overturn worse than P0 by 0, 1, 2, 3 points)
    for F in fams:
        for worse in ([0.01] if quick else [0.0, 0.01, 0.02, 0.03]):
            seed += 1
            par = dict(par0)
            ca = dict(par["correct_present_aligned"]); ca["P3"] = ca["P0"] - worse
            par["correct_present_aligned"] = ca
            # P3 unnecessary escalation set equal to P0 so that correct + escalation <= 1
            par["esc_present_shift"] = par["esc_present"]["P0"] - par["esc_present"]["P1"]
            rows.append(dict(grid="D_ni_truth", effect=par["effect"], interaction=par["interaction"],
                             sd_family=par["sd_family"], sd_slope=par["sd_slope"], ao_worse=worse,
                             **run_scenario(par, F, 3, 3, nsim, seed)))
    # E: candidate confirmation sizes, more replicates, base and pessimistic assumptions
    if not quick:
        scen = {"base": {}, "slope_0.75": dict(sd_slope=0.75), "harm_2pts": "harm",
                "effect_8": dict(effect=0.08, interaction=0.08)}
        for F in (40, 50, 60):
            for R in (3, 5):
                for sname, kw in scen.items():
                    seed += 1
                    par = dict(par0)
                    if kw == "harm":
                        ca = dict(par["correct_present_aligned"]); ca["P3"] = ca["P0"] - 0.02
                        par["correct_present_aligned"] = ca
                        par["esc_present_shift"] = par["esc_present"]["P0"] - par["esc_present"]["P1"]
                    else:
                        par.update(kw)
                    rows.append(dict(grid="E_candidates", scenario=sname, effect=par["effect"],
                                     interaction=par["interaction"], sd_family=par["sd_family"],
                                     sd_slope=par["sd_slope"], **run_scenario(par, F, 3, R, 2 * nsim, seed)))
    grid = pd.DataFrame(rows)
    grid.to_csv(out / f"power_grid{label}.csv", index=False)
    print(f"  grids done in {time.time() - t0:.0f}s ({len(grid)} scenarios)")
    return grid


def null_checks(par0, nsim, out, label):
    rows = []
    seed = 5000
    for F in (16, 40):
        for name, kw in (("C1 null (P3 = P1)", dict(effect=0.0)),
                         ("C2 null (P3 = P2)", dict(effect=par0["correct_present_flawed"]["P2"]
                                                     - par0["correct_present_flawed"]["P1"])),
                         ("C3 null (no interaction)", dict(interaction=0.0)),
                         ("C3 null, generic caution (+5 pts escalation everywhere)",
                          dict(interaction=0.0, esc_present_shift=0.05,
                               correct_present_aligned=dict(par0["correct_present_aligned"],
                                                            P3=par0["correct_present_aligned"]["P1"] - 0.05)))):
            seed += 1
            par = dict(par0); par.update(kw)
            r = run_scenario(par, F, 3, 3, 2 * nsim, seed)
            key = name[:2]
            rows.append(dict(check=name, F=F, rejection_rate=r[f"{key}_twosided"],
                             note=f"two-sided, unadjusted alpha .05, {2 * nsim} sims"))
        # NI at the margin: true P3 - P0 = margin  -> pass rate should be <= 0.025
        seed += 1
        par = dict(par0)
        ca = dict(par["correct_present_aligned"]); ca["P3"] = ca["P0"] - MARGIN_AO
        par["correct_present_aligned"] = ca
        r = run_scenario(par, F, 3, 3, 2 * nsim, seed)
        rows.append(dict(check="NI1 at margin (true P3-P0 overturn = +5)", F=F,
                         rejection_rate=r["NI1_pass"],
                         note=f"nominal one-sided .025; true diff {r['NI1_est']:.3f}"))
    t = pd.DataFrame(rows)
    t.to_csv(out / f"null_checks{label}.csv", index=False)
    return t


def fmt(x):
    return f"{x:.2f}"


def to_md(df, index=True):
    """Minimal markdown table (avoids the optional tabulate dependency)."""
    d = df.reset_index() if index else df
    d.columns = [" / ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in d.columns]
    lines = ["| " + " | ".join(d.columns) + " |", "|" + "---|" * len(d.columns)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return chr(10).join(lines)


def report(grid, nulls, checks, out, label, par0, extra_md=""):
    md = [f"# Confirmation-set power: simulation tables{label}\n",
          "Power = share of simulated confirmation sets in which the contrast is rejected by Holm "
          "(FWER .05, two-sided, correct direction); NI = share in which the 95% bound clears the margin; "
          "adopt = C1 & C2 (Holm) & NI1 & NI2.\n",
          "Parameters: " + json.dumps({k: v for k, v in par0.items() if k.startswith("sd_") or k in
                                       ("rho_variant", "effect", "interaction")}) + "\n", extra_md]
    A = grid[grid.grid == "A_design"]
    md.append("## A. Families x repeats x models (effect +10, interaction +10)\n")
    md.append(A.pivot_table(index=["M", "R"], columns="F", values="C1_holm").map(fmt).pipe(to_md))
    md.append("\nC1 SE (points) by families x repeats (M = 3):\n")
    md.append((A[A.M == A.M.max()].pivot_table(index="R", columns="F", values="C1_se") * 100).map(fmt).pipe(to_md))
    md.append("\nJoint adopt (C1 & C2 & NI1 & NI2), M = 3:\n")
    md.append(A[A.M == A.M.max()].pivot_table(index="R", columns="F", values="adopt_full").map(fmt).pipe(to_md))
    md.append("\nAll quantities, M = 3, R = 3:\n")
    cols = ["F", "C1_holm", "C2_holm", "C3_holm", "NI1_pass", "NI2_pass", "adopt_C1_NI", "adopt_full"]
    md.append(A[(A.M == A.M.max()) & (A.R == 3)][cols].map(lambda v: fmt(v) if isinstance(v, float) else v)
              .pipe(to_md, index=False))
    B = grid[grid.grid == "B_effect"]
    if len(B):
        md.append("\n## B. Effect size (C1 effect = C3 interaction; C2 effect = C1 - 2), M = 3, R = 3\n")
        for v in ("C1_holm", "C2_holm", "C3_holm", "adopt_full"):
            md.append(f"\n{v}:\n")
            md.append(B.pivot_table(index="effect", columns="F", values=v).map(fmt).pipe(to_md))
    C = grid[grid.grid == "C_heterogeneity"]
    if len(C):
        md.append("\n## C. Family heterogeneity (logit SDs), effect +10, M = 3, R = 3\n")
        for v in ("C1_holm", "NI2_pass", "adopt_full"):
            md.append(f"\n{v}:\n")
            md.append(C.pivot_table(index=["sd_family", "sd_slope"], columns="F", values=v).map(fmt).pipe(to_md))
    D = grid[grid.grid == "D_ni_truth"]
    if len(D):
        md.append("\n## D. NI pass rates when P3 truly overturns more aligned advice than P0 (points)\n")
        for v in ("NI1_pass", "NI2_pass", "adopt_full"):
            md.append(f"\n{v}:\n")
            md.append(D.pivot_table(index="ao_worse", columns="F", values=v).map(fmt).pipe(to_md))
    E = grid[grid.grid == "E_candidates"]
    if len(E):
        md.append("\n## E. Candidate sizes (M = 3; 2x replicates). base = defaults; slope_0.75 = more "
                  "procedure-by-family heterogeneity; harm_2pts = P3 truly overturns 2 points more aligned "
                  "advice than P0; effect_8 = C1 and C3 effects +8 (C2 +6)\n")
        cols = ["scenario", "F", "R", "C1_holm", "C2_holm", "C3_holm", "NI1_pass", "NI2_pass", "adopt_full"]
        md.append(E[cols].sort_values(["scenario", "F", "R"]).map(lambda v: fmt(v) if isinstance(v, float) else v)
                  .pipe(to_md, index=False))
    md.append("\n## Null and margin checks (M = 3, R = 3)\n")
    md.append(nulls.pipe(to_md, index=False))
    if checks is not None:
        md.append("\n## Analysis checks\n")
        md.append(checks.pipe(to_md, index=False))
    (out / f"power_tables{label}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nsim", type=int, default=1000)
    ap.add_argument("--out", default=str(HERE / "power_out"))
    ap.add_argument("--from-dev", default=None, help="development scored_runs.csv to re-estimate inputs")
    ap.add_argument("--quick", action="store_true", help="reduced grid (for --from-dev demos)")
    ap.add_argument("--no-checks", action="store_true", help="skip sign-flip and GEE checks")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    label, extra = "", ""
    if a.from_dev:
        par0, dv = calibrate_from_dev(a.from_dev)
        label = "_from_dev"
        est = {k: par0[k] for k in ("sd_family", "sd_slope", "sd_model_item")}
        extra = (f"Inputs re-estimated from `{a.from_dev}` (F = {dv['F']}, M = {dv['M']}, R = {dv['R']}). "
                 f"Observed summaries: {json.dumps({k: round(v, 3) for k, v in dv['stats'].items()})}. "
                 f"Moment-matched SDs: {est}. Observed dev P3 - P1 = {np.nanmean(dv['d1']):.3f} "
                 "(descriptive only; the assumed effects below are planning values, not the dev estimate).\n")
        rs = {F: resampling_power(dv["d1"], F, 0.10, 4000, 7) for F in FAMS}
        extra += ("\nNonparametric check (resampled centred dev family differences + 10 points, "
                  f"one-sided-equivalent alpha .05/3, dev M and R): {json.dumps({k: round(v, 2) for k, v in rs.items()})}\n")
        json.dump(dict(params=par0, dev_stats=dv["stats"], dev_rates=dv["rates"]),
                  open(out / "params_from_dev.json", "w"), indent=2, default=float)
        print(extra)
    else:
        par0 = gen.params_with()
    print(f"running grids (nsim = {a.nsim}) ...")
    grid = run_grids(par0, a.nsim, out, label, quick=a.quick)
    nulls = null_checks(par0, a.nsim, out, label)
    checks = None
    if not a.no_checks:
        t0 = time.time()
        rows = []
        for F in (16, 24):
            for e in (0.0, 0.10):
                p = dict(par0); p["effect"] = e
                rows.append(signflip_check(p, F, 3, 3, 1000, 77 + F))
        sf = pd.DataFrame(rows); sf.insert(0, "check", "family t vs sign-flip (C1)")
        rows = []
        for e in (0.0, 0.10):
            p = dict(par0); p["effect"] = e
            rows.append(gee_check(p, 24, 3, 3, 200 if not a.quick else 60, 31))
        gc = pd.DataFrame(rows); gc.insert(0, "check", "family t vs GEE bias-reduced (C1, F = 24)")
        checks = pd.concat([sf, gc], ignore_index=True)
        checks.to_csv(out / f"analysis_checks{label}.csv", index=False)
        print(f"  checks done in {time.time() - t0:.0f}s")
    report(grid, nulls, checks, out, label, par0, extra)
    A = grid[(grid.grid == "A_design") & (grid.M == 3) & (grid.R == 3)]
    print(A[["F", "C1_holm", "C2_holm", "C3_holm", "NI1_pass", "NI2_pass", "adopt_full", "C1_se"]]
          .round(3).to_string(index=False))
    print(nulls.round(3).to_string(index=False))
    if checks is not None:
        print(checks.round(3).to_string(index=False))
    print(f"wrote {out / f'power_tables{label}.md'}")


if __name__ == "__main__":
    main()
