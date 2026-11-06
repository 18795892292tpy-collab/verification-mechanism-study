"""Simulation-based power for the Phase 4 human decision experiment.

Design simulated (as in the draft): participants randomised between subjects to
verification support (T) or standard advice (C); each sees 12 cases, 6 with aligned
and 6 with flawed advice (advice version counterbalanced across lists, so every case
appears in both versions across participants). Case bank K = 12 (everyone sees the
same 12 cases, 2 lists) or K = 24 (two sets of 12, 4 lists).

Generator (logit scale, crossed random effects):
  flawed trial  correct  = expit(muF + dF*x + pF_s + aF_c + bF_c*x)
  aligned trial followed = expit(muA + dA*x + pA_s + aA_c + bA_c*x)
  (pF, pA) participant effects, SDs sd_p, correlation rho_p (skeptics catch more flaws
  but reject more correct advice); aF, aA case effects; bF, bA case-by-treatment slopes.
  mu, d are calibrated so the MARGINAL rates equal the targets (risk-difference effects).

Analyses compared on each simulated data set:
  v3      pooled two-sample t-test on participant flawed-advice accuracy (G*Power plan)
  crossed case-aware test: participant-level variance + case-by-treatment variance
          (balanced-design method-of-moments equivalent of a mixed model with crossed
          participant and case effects and a by-case treatment slope; Satterthwaite df)
  NI      under-reliance (not following aligned advice): T - C upper 95% bound < margin,
          case-aware SE (and the v3-style participant-only bound for comparison)
A statsmodels MixedLM fit with crossed variance components checks the case-aware test
on a subset.

Usage: python power_human.py [--nsim 1000] [--out DIR] [--no-mixedlm]
"""
from __future__ import annotations

import argparse
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import brentq
from scipy.special import expit

HERE = Path(__file__).resolve().parent
ALPHA = 0.05
MARGIN_U = 0.05
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(48)
GH_W = GH_W / np.sqrt(2 * np.pi)

DEFAULTS = dict(
    pC_flawed=0.40,     # control accuracy on flawed-advice cases (assumption)
    delta=0.10,         # verification-support gain on flawed-advice accuracy
    pC_under=0.10,      # control under-reliance on aligned-advice cases (assumption)
    delta_under=0.0,    # true increase in under-reliance under support
    sd_p=0.8, rho_p=-0.3, sd_case_f=1.0, sd_case_a=0.8, sd_slope=0.5,
)


def calib(target, sd):
    f = lambda mu: float(expit(mu + sd * GH_X) @ GH_W - target)
    return brentq(f, -20, 20)


def design(N, K):
    """Arm (0/1), list, flawed and aligned case indices (N x 6) for a balanced design."""
    L = 2 * (K // 12)
    cells = 2 * L
    if N % cells:
        raise ValueError(f"N must be a multiple of {cells} for K = {K}")
    arm = np.tile([0, 1], N // 2)
    lst = np.repeat(np.arange(L), 2)[np.arange(N) % cells]
    fc, ac = np.zeros((N, 6), int), np.zeros((N, 6), int)
    for s in range(N):
        li = lst[s]
        base = 12 * (li // 2)
        first, second = np.arange(base, base + 6), np.arange(base + 6, base + 12)
        fc[s], ac[s] = (first, second) if li % 2 == 0 else (second, first)
    return arm, lst, fc, ac, L


def simulate(par, N, K, nsim, rng):
    arm, lst, fc, ac, L = design(N, K)
    sp, sb = par["sd_p"], par["sd_slope"]
    sdC_f = np.hypot(sp, par["sd_case_f"]); sdT_f = np.sqrt(sdC_f ** 2 + sb ** 2)
    sdC_a = np.hypot(sp, par["sd_case_a"]); sdT_a = np.sqrt(sdC_a ** 2 + sb ** 2)
    muF = calib(par["pC_flawed"], sdC_f)
    dF = calib(par["pC_flawed"] + par["delta"], sdT_f) - muF
    muA = calib(1 - par["pC_under"], sdC_a)
    dA = calib(1 - par["pC_under"] - par["delta_under"], sdT_a) - muA
    z1, z2 = rng.standard_normal((2, nsim, N))
    pF = sp * z1
    pA = sp * (par["rho_p"] * z1 + np.sqrt(1 - par["rho_p"] ** 2) * z2)
    aF = par["sd_case_f"] * rng.standard_normal((nsim, K))
    aA = par["sd_case_a"] * rng.standard_normal((nsim, K))
    bF = sb * rng.standard_normal((nsim, K))
    bA = sb * rng.standard_normal((nsim, K))
    x = arm[None, :, None]
    etaF = muF + dF * x + pF[:, :, None] + aF[:, fc] + bF[:, fc] * x
    etaA = muA + dA * x + pA[:, :, None] + aA[:, ac] + bA[:, ac] * x
    YF = (rng.random(etaF.shape) < expit(etaF)).astype(float)       # correct on flawed
    UA = (rng.random(etaA.shape) >= expit(etaA)).astype(float)      # under-reliance on aligned
    return YF, UA, arm, lst, L, fc, ac


def v3_ttest(Y, arm):
    m = Y.mean(axis=2)
    a, b = m[:, arm == 1], m[:, arm == 0]
    na, nb = a.shape[1], b.shape[1]
    diff = a.mean(1) - b.mean(1)
    sp2 = ((na - 1) * a.var(1, ddof=1) + (nb - 1) * b.var(1, ddof=1)) / (na + nb - 2)
    se = np.sqrt(sp2 * (1 / na + 1 / nb))
    df = na + nb - 2
    with np.errstate(divide="ignore", invalid="ignore"):
        t = diff / se
    pooled_sd = np.sqrt(sp2)
    return diff, se, 2 * stats.t.sf(np.abs(t), df), df, pooled_sd


def crossed_test(Y, arm, lst, L):
    """Case-aware test of the arm difference for one trial type (vectorised over sims)."""
    S = Y.shape[0]
    D = np.zeros(S); A = np.zeros(S); sd2 = np.zeros(S); inv_n = 0.0
    ms_sum = np.zeros(S); ms_k = 0
    m = Y.mean(axis=2)
    for li in range(L):
        T, C = (lst == li) & (arm == 1), (lst == li) & (arm == 0)
        nT, nC = T.sum(), C.sum()
        D += m[:, T].mean(1) - m[:, C].mean(1)
        A += m[:, T].var(1, ddof=1) / nT + m[:, C].var(1, ddof=1) / nC
        dc = Y[:, T, :].mean(1) - Y[:, C, :].mean(1)                       # (S, 6)
        sd2 += dc.var(1, ddof=1)
        inv_n += 1 / nT + 1 / nC
        for g, n in ((T, nT), (C, nC)):
            Z = Y[:, g, :]
            R = Z - Z.mean(2, keepdims=True) - Z.mean(1, keepdims=True) + Z.mean((1, 2), keepdims=True)
            ms_sum += (R ** 2).sum((1, 2)) / ((n - 1) * 5)
            ms_k += 1
    D /= L
    A /= L ** 2
    sig_e2 = ms_sum / ms_k
    sig_b2 = np.maximum(0.0, sd2 / L - sig_e2 * inv_n / L)
    B = sig_b2 / (6 * L)
    se = np.sqrt(A + B)
    dfA, dfB = len(arm) - 2 * L, 5 * L
    with np.errstate(divide="ignore", invalid="ignore"):
        nu = np.where(B > 0, (A + B) ** 2 / (A ** 2 / dfA + B ** 2 / dfB), dfA)
        t = D / se
    return D, se, 2 * stats.t.sf(np.abs(t), nu), nu


def run_scenario(par, N, K, nsim, seed):
    rng = np.random.default_rng(seed)
    YF, UA, arm, lst, L, _, _ = simulate(par, N, K, nsim, rng)
    d1, se1, p1, df1, psd = v3_ttest(YF, arm)
    d2, se2, p2, nu2 = crossed_test(YF, arm, lst, L)
    du, seu, _, nuu = crossed_test(UA, arm, lst, L)
    ub_case = du + stats.t.ppf(0.975, nuu) * seu
    duv, seuv, _, dfv, _ = v3_ttest(UA, arm)
    ub_v3 = duv + stats.t.ppf(0.975, dfv) * seuv
    prim = (p2 < ALPHA) & (d2 > 0)
    ni = ub_case < MARGIN_U
    return dict(N=N, K=K, nsim=nsim, delta=par["delta"], sd_slope=par["sd_slope"], sd_p=par["sd_p"],
                delta_under=par["delta_under"], pC_flawed=par["pC_flawed"],
                est=d2.mean(), implied_d=np.mean(d1 / psd),
                power_v3_ttest=np.mean((p1 < ALPHA) & (d1 > 0)), power_crossed=prim.mean(),
                rej2_v3=np.mean(p1 < ALPHA), rej2_crossed=np.mean(p2 < ALPHA),
                ni_pass_crossed=ni.mean(), ni_pass_v3=np.mean(ub_v3 < MARGIN_U),
                ni_pass_crossed_m75=np.mean(ub_case < 0.075),
                joint_crossed_m75=np.mean(prim & (ub_case < 0.075)),
                joint_crossed=np.mean(prim & ni), se_v3=se1.mean(), se_crossed=se2.mean())


def mixedlm_check(par, N, K, nsim, seed):
    import statsmodels.formula.api as smf
    rng = np.random.default_rng(seed)
    YF, _, arm, lst, L, fc, _ = simulate(par, N, K, nsim, rng)
    _, _, p_x, _ = crossed_test(YF, arm, lst, L)
    _, _, p_t, _, _ = v3_ttest(YF, arm)
    rej_m = fails = 0
    for s in range(nsim):
        d = pd.DataFrame(dict(y=YF[s].ravel(), pid=np.repeat(np.arange(N), 6), case=fc.ravel(),
                              arm=np.repeat(arm, 6), one=1))
        d["caseT"] = d.case.astype(str) + "_" + d.arm.astype(str)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = smf.mixedlm("y ~ arm", d, groups="one", re_formula="0",
                                vc_formula={"pid": "0 + C(pid)", "case": "0 + C(case)",
                                            "slope": "0 + C(case):arm"}).fit(reml=True, method="lbfgs")
            # conservative small-sample reference: t with df = number of distinct flawed cases - 2
            tval = r.params["arm"] / r.bse["arm"]
            rej_m += 2 * stats.t.sf(abs(tval), 6 * L - 2) < ALPHA
        except Exception:
            fails += 1
    return dict(N=N, K=K, delta=par["delta"], sd_slope=par["sd_slope"], nsim=nsim,
                reject_v3_ttest=np.mean(p_t < ALPHA), reject_crossed=np.mean(p_x < ALPHA),
                reject_mixedlm=rej_m / nsim, mixedlm_failures=fails)


def to_md(df, index=True):
    d = df.reset_index() if index else df
    d.columns = [" / ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in d.columns]
    lines = ["| " + " | ".join(d.columns) + " |", "|" + "---|" * len(d.columns)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else (f"{v:.2f}" if isinstance(v, float) else str(v))
                                      for v in r.values) + " |")
    return chr(10).join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nsim", type=int, default=1000)
    ap.add_argument("--out", default=str(HERE / "power_out"))
    ap.add_argument("--no-mixedlm", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    Ns = [64, 96, 128, 160, 192, 256, 320, 400]
    rows, seed = [], 100
    for K in (12, 24):
        for sb in (0.0, 0.25, 0.5, 0.75):
            for dl in (0.075, 0.10, 0.125, 0.15):
                for N in Ns:
                    seed += 1
                    par = dict(DEFAULTS, delta=dl, sd_slope=sb)
                    rows.append(dict(grid="main", **run_scenario(par, N, K, a.nsim, seed)))
    # nulls: Type I error of v3 t-test vs case-aware test (generalising over cases)
    for K in (12, 24):
        for sb in (0.0, 0.5, 0.75):
            for N in (128, 256):
                seed += 1
                par = dict(DEFAULTS, delta=0.0, sd_slope=sb)
                rows.append(dict(grid="nullcheck", **run_scenario(par, N, K, 2 * a.nsim, seed)))
    # NI sensitivity: true under-reliance increase of 2 points; participant SD 1.2
    for K in (12, 24):
        for N in Ns:
            for kw in (dict(delta_under=0.02), dict(sd_p=1.2)):
                seed += 1
                par = dict(DEFAULTS, **kw)
                rows.append(dict(grid="sens_" + "_".join(f"{k}{v}" for k, v in kw.items()),
                                 **run_scenario(par, N, K, a.nsim, seed)))
    g = pd.DataFrame(rows)
    g.to_csv(out / "power_human_grid.csv", index=False)
    print(f"grid done in {time.time() - t0:.0f}s")

    md = ["# Human experiment power: simulation tables\n",
          f"nsim = {a.nsim} per cell (2x for nulls). Defaults: {DEFAULTS}. Power = two-sided alpha .05, "
          "correct direction. NI = upper 95% bound of under-reliance difference < +5 points.\n"]
    main_g = g[g.grid == "main"]
    for K in (12, 24):
        sub = main_g[(main_g.K == K) & (main_g.delta == 0.10)]
        md.append(f"\n## K = {K} cases, effect +10 points: power by N (columns) and case-by-treatment SD\n")
        md.append("Case-aware test:\n")
        md.append(to_md(sub.pivot_table(index="sd_slope", columns="N", values="power_crossed")))
        md.append("\nv3 participant-level t-test (nominal; anticonservative when sd_slope > 0):\n")
        md.append(to_md(sub.pivot_table(index="sd_slope", columns="N", values="power_v3_ttest")))
        sub5 = main_g[(main_g.K == K) & (main_g.sd_slope == 0.5)]
        md.append(f"\nCase-aware power by effect (rows) and N, sd_slope = 0.5, K = {K}:\n")
        md.append(to_md(sub5.pivot_table(index="delta", columns="N", values="power_crossed")))
        md.append(f"\nJoint (primary & under-reliance NI), sd_slope = 0.5, K = {K}:\n")
        md.append(to_md(sub5.pivot_table(index="delta", columns="N", values="joint_crossed")))
        md.append(f"\nUnder-reliance NI pass (case-aware; true difference 0), margin 5 vs 7.5 points, sd_slope = 0.5, K = {K}:\n")
        md.append(to_md(sub5[sub5.delta == 0.10].pivot_table(index="K", columns="N",
                                                              values=["ni_pass_crossed", "ni_pass_crossed_m75"])))
        md.append(f"\nJoint with margin 7.5, sd_slope = 0.5, K = {K}:\n")
        md.append(to_md(sub5.pivot_table(index="delta", columns="N", values="joint_crossed_m75")))
    md.append("\n## Implied Cohen's d (participant-level flawed accuracy) for each effect, K = 12, sd_slope = 0.5\n")
    d_tab = main_g[(main_g.K == 12) & (main_g.sd_slope == 0.5) & (main_g.N == 128)][["delta", "implied_d"]]
    md.append(to_md(d_tab, index=False))
    nul = g[g.grid == "nullcheck"]
    md.append("\n## Type I error under no effect (generalising over cases)\n")
    md.append(to_md(nul[["K", "sd_slope", "N", "rej2_v3", "rej2_crossed"]]
                    .rename(columns={"rej2_v3": "v3 t-test", "rej2_crossed": "case-aware"}), index=False))
    sens = g[g.grid.str.startswith("sens")]
    md.append("\n## Sensitivity (effect +10, sd_slope 0.5)\n")
    md.append(to_md(sens.pivot_table(index=["grid", "K"], columns="N", values="joint_crossed")))
    if not a.no_mixedlm:
        t1 = time.time()
        chk = []
        for dl in (0.0, 0.10):
            for sb in (0.5,):
                chk.append(mixedlm_check(dict(DEFAULTS, delta=dl, sd_slope=sb), 128, 12, 100, 900 + int(100 * dl) + int(10 * sb)))
        chk = pd.DataFrame(chk)
        chk.to_csv(out / "power_human_mixedlm_check.csv", index=False)
        md.append("\n## Check against a linear mixed model with crossed random effects (N = 128, K = 12, 100 sims)\n")
        md.append(to_md(chk, index=False))
        print(f"mixedlm check done in {time.time() - t1:.0f}s")
        print(chk.round(3).to_string(index=False))
    elif (out / "power_human_mixedlm_check.csv").exists():
        chk = pd.read_csv(out / "power_human_mixedlm_check.csv")
        md.append(chr(10) + "## Check against a linear mixed model with crossed random effects "
                  "(saved from a previous run; LMM uses a conservative t reference with df = cases - 2)" + chr(10))
        md.append(to_md(chk, index=False))
    (out / "power_human_tables.md").write_text(chr(10).join(md) + chr(10), encoding="utf-8")
    show = main_g[(main_g.delta == 0.10) & (main_g.sd_slope.isin([0.0, 0.5]))][
        ["K", "sd_slope", "N", "power_v3_ttest", "power_crossed", "ni_pass_crossed", "joint_crossed", "implied_d"]]
    print(show.round(3).to_string(index=False))
    print(nul[["K", "sd_slope", "N", "rej2_v3", "rej2_crossed"]].round(3).to_string(index=False))
    print(f"wrote {out / 'power_human_tables.md'}")


if __name__ == "__main__":
    main()
