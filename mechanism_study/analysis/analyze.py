"""Pre-specified analysis of scored_runs.csv (mechanism study, computational line).

Unit of inference = case family. Every outcome is first averaged within
family x procedure x model (over items and repeats), then over models (equal
weights), giving one value per family and procedure. Contrasts are paired
family-level differences: t-test (primary), sign-flip permutation and family
cluster bootstrap (robustness), plus a GEE with bias-reduced SEs.

Usage:
  python analyze.py path/to/scored_runs.csv [--out DIR] [--boot 2000] [--seed 1]
Outputs (in --out): summary_tables.md and CSV tables.
"""
from __future__ import annotations

import argparse
import itertools
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

PROCS_ALL = ["P0", "P1", "P2", "P3", "P4"]
MARGIN_AO = 0.05      # NI1: P3 - P0 aligned_overturn must be < +5 points (upper 95% bound)
MARGIN_ST = 0.05      # NI2: P3 - P0 conditional irrelevant stability must be > -5 points (lower bound)
SESOI = 0.10          # smallest effect of interest for C1/C2 (planning, decision rules)
NEGLIGIBLE = 0.05     # upper CI bound below this => effect "negligible" (drop rule)
COMPUTE_MATCH = (0.80, 1.25)   # acceptable P3/P1 (and P2, P4) output-token ratio

REQUIRED = ["run_id", "model", "procedure", "family_id", "domain", "mismatch_type", "state",
            "evidence", "advice", "repeat", "key_action", "advised_action", "action",
            "parse_ok", "correct", "followed_advice", "escalated", "citation_complete",
            "first_action", "changed_after_review", "input_tokens", "output_tokens",
            "latency_s", "n_calls"]
STR_COLS = ["run_id", "model", "procedure", "family_id", "domain", "mismatch_type", "state",
            "evidence", "advice", "key_action", "advised_action", "action", "first_action"]
KEYS_PAIR = ["model", "procedure", "family_id", "advice", "repeat"]


# ----------------------------------------------------------------------------
# Loading and derived outcomes
# ----------------------------------------------------------------------------
def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={c: str for c in STR_COLS}, keep_default_na=False,
                     na_values={"changed_after_review": [""]})
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise SystemExit(f"missing columns: {miss}")
    for c in STR_COLS:
        df[c] = df[c].fillna("").astype(str).str.strip()
    for c in ["repeat", "parse_ok", "correct", "followed_advice", "escalated",
              "citation_complete", "n_calls"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in ["input_tokens", "output_tokens", "latency_s", "changed_after_review"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    bad = set(df.procedure) - set(PROCS_ALL)
    if bad:
        raise SystemExit(f"unknown procedures: {bad}")
    # Pre-specified handling: an unparsable response is a failed decision
    # (not correct, not escalated, did not follow advice, no complete citation).
    for c in ["correct", "followed_advice", "escalated", "citation_complete"]:
        df[c] = df[c] * df.parse_ok
    df.loc[df.parse_ok == 0, "action"] = ""
    present = df.evidence.eq("present")
    flawed = df.advice.eq("flawed")
    nan = np.nan
    df["flawed_correction"] = np.where(present & flawed, df.correct, nan)
    df["aligned_overturn"] = np.where(present & ~flawed, 1 - df.correct, nan)
    df["pause_appropriate"] = np.where(df.state.eq("missing"), df.escalated, nan)
    df["unnecessary_escalation"] = np.where(present, df.escalated, nan)
    df["follow_flawed"] = np.where(flawed, df.followed_advice, nan)
    df["accuracy"] = df.correct.astype(float)
    df["citation"] = df.citation_complete.astype(float)
    df["parse_failure"] = 1.0 - df.parse_ok
    df["total_tokens"] = df.input_tokens + df.output_tokens
    return df


def pair_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    w = df.pivot_table(index=KEYS_PAIR, columns="state", values=["action", "correct", "parse_ok"],
                       aggfunc="first")
    out = pd.DataFrame(index=w.index)

    def col(v, s):
        return w[(v, s)] if (v, s) in w.columns else pd.Series(np.nan, index=w.index)

    cb, cd = col("correct", "base"), col("correct", "decisive_change")
    ab = col("action", "base")
    out["counterfactual_success"] = ((cb == 1) & (cd == 1)).astype(float).where(cb.notna() & cd.notna())
    out["base_correct"] = cb.astype(float)
    for st, name in (("irrelevant_change", "irrelevant"), ("paraphrase", "paraphrase")):
        av, pv = col("action", st), col("parse_ok", st)
        ok = av.notna() & ab.notna()
        out[f"{name}_stability"] = ((av == ab) & (cb == 1)).astype(float).where(ok)
        both = ok & (pv == 1) & (col("parse_ok", "base") == 1)
        out[f"{name}_flip"] = (av != ab).astype(float).where(both)
    out = out.reset_index()
    out["irrelevant_stability_aligned"] = out.irrelevant_stability.where(out.advice == "aligned")
    return out


# ----------------------------------------------------------------------------
# Family-level aggregation, bootstrap and contrasts
# ----------------------------------------------------------------------------
class Fam:
    def __init__(self, families, procs, B, seed):
        self.families = sorted(families)
        self.procs = procs
        rng = np.random.default_rng(seed)
        self.idx = rng.integers(0, len(self.families), size=(B, len(self.families)))
        self.rng = rng

    def table(self, d: pd.DataFrame, y: str) -> pd.DataFrame:
        """family x procedure matrix: mean over items/repeats within model, then over models."""
        g = d.dropna(subset=[y]).groupby(["family_id", "procedure", "model"], observed=True)[y].mean()
        g = g.groupby(["family_id", "procedure"]).mean().unstack("procedure")
        return g.reindex(index=self.families, columns=self.procs)

    def ratio_table(self, d: pd.DataFrame, num: str, den: str) -> pd.DataFrame:
        """family x procedure ratio of sums (pooled over models, advice, repeats)."""
        g = d.dropna(subset=[num, den]).groupby(["family_id", "procedure"])[[num, den]].sum()
        r = (g[num] / g[den].where(g[den] > 0)).unstack("procedure")
        return r.reindex(index=self.families, columns=self.procs)

    def boot_means(self, v: np.ndarray) -> np.ndarray:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(v[self.idx], axis=1)

    def summarize(self, mat: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for p in mat.columns:
            v = mat[p].to_numpy(float)
            n = int(np.isfinite(v).sum())
            if n == 0:
                continue
            bm = self.boot_means(v)
            rows.append(dict(procedure=p, estimate=np.nanmean(v), ci_lo=np.nanpercentile(bm, 2.5),
                             ci_hi=np.nanpercentile(bm, 97.5), n_families=n))
        return pd.DataFrame(rows)

    def contrast(self, d: pd.Series, name: str, n_flip: int = 20000) -> dict:
        v = d.reindex(self.families).to_numpy(float)
        bm = self.boot_means(v)
        x = v[np.isfinite(v)]
        n = len(x)
        res = dict(contrast=name, n_families=n, estimate=np.nan, se=np.nan, t=np.nan, df=n - 1,
                   p_t=np.nan, ci_lo=np.nan, ci_hi=np.nan, boot_lo=np.nan, boot_hi=np.nan,
                   p_signflip=np.nan)
        if n < 3:
            return res
        m, se = x.mean(), x.std(ddof=1) / np.sqrt(n)
        tq = stats.t.ppf(0.975, n - 1)
        t = m / se if se > 0 else (np.inf if m != 0 else 0.0)
        # bootstrap-t bounds (skewness-robust sensitivity for the NI decisions)
        xb = x[self.rng.integers(0, n, size=(len(self.idx), n))]
        sb = xb.std(axis=1, ddof=1) / np.sqrt(n)
        with np.errstate(divide="ignore", invalid="ignore"):
            tb = (xb.mean(axis=1) - m) / sb
        tb = tb[np.isfinite(tb)]
        if len(tb) > 10 and se > 0:
            res.update(boott_lo=m - np.percentile(tb, 97.5) * se, boott_hi=m - np.percentile(tb, 2.5) * se)
        res.update(estimate=m, se=se, t=t, p_t=2 * stats.t.sf(abs(t), n - 1) if se > 0 else float(m == 0),
                   ci_lo=m - tq * se, ci_hi=m + tq * se,
                   boot_lo=np.nanpercentile(bm, 2.5), boot_hi=np.nanpercentile(bm, 97.5),
                   p_signflip=signflip_p(x, self.rng, n_flip))
        return res


def signflip_p(x: np.ndarray, rng, n_flip: int) -> float:
    n, obs = len(x), abs(x.mean())
    if n <= 16:
        signs = np.array(list(itertools.product([-1, 1], repeat=n)))
        return float(np.mean(np.abs(signs @ x / n) >= obs - 1e-12))
    signs = rng.choice([-1.0, 1.0], size=(n_flip, n))
    return float((np.sum(np.abs(signs @ x / n) >= obs - 1e-12) + 1) / (n_flip + 1))


# ----------------------------------------------------------------------------
# Secondary analyses
# ----------------------------------------------------------------------------
def sdt_tables(df: pd.DataFrame, fam: Fam):
    """Per family x procedure: hits = flawed-advice correction, false alarms = aligned overturn.
    Log-linear correction (add 0.5 / 1) for extreme rates."""
    pres = df[df.evidence == "present"]
    g = pres.groupby(["family_id", "procedure", "advice"]).correct.agg(["sum", "count"]).unstack("advice")
    hits, nh = g[("sum", "flawed")], g[("count", "flawed")]
    fa = g[("count", "aligned")] - g[("sum", "aligned")]
    nfa = g[("count", "aligned")]
    H = (hits + 0.5) / (nh + 1)
    FA = (fa + 0.5) / (nfa + 1)
    zH = pd.Series(stats.norm.ppf(H), index=H.index)
    zF = pd.Series(stats.norm.ppf(FA), index=FA.index)
    dprime = (zH - zF).unstack("procedure").reindex(index=fam.families, columns=fam.procs)
    crit = (-(zH + zF) / 2).unstack("procedure").reindex(index=fam.families, columns=fam.procs)
    return dprime, crit


def flip_tables(df: pd.DataFrame, fam: Fam):
    """First-pass -> final transitions for P1-P4 versus a resampling baseline built
    from pairs of independent P0 runs of the same model x item (all ordered pairs of repeats)."""
    rows = []
    rev = df[(df.procedure != "P0") & (df.first_action != "") & (df.parse_ok == 1)].copy()
    rev["first_correct"] = (rev.first_action == rev.key_action).astype(float)
    rev["final_correct"] = rev.correct.astype(float)
    rev["flip"] = (rev.first_action != rev.action).astype(float)
    rows.append(rev[["family_id", "procedure", "model", "state", "evidence", "advice",
                     "first_correct", "final_correct", "flip"]])
    p0 = df[(df.procedure == "P0") & (df.parse_ok == 1)]
    k = ["model", "family_id", "state", "advice"]
    if p0.groupby(k).size().max() >= 2:
        a = p0[k + ["repeat", "action", "correct", "evidence"]]
        m = a.merge(a, on=k + ["evidence"], suffixes=("_1", "_2"))
        m = m[m.repeat_1 != m.repeat_2]
        base = pd.DataFrame(dict(family_id=m.family_id, procedure="P0pair", model=m.model,
                                 state=m.state, evidence=m.evidence, advice=m.advice,
                                 first_correct=m.correct_1.astype(float),
                                 final_correct=m.correct_2.astype(float),
                                 flip=(m.action_1 != m.action_2).astype(float)))
        rows.append(base)
    t = pd.concat(rows, ignore_index=True)
    t["w2r"] = ((t.first_correct == 0) & (t.final_correct == 1)).astype(float)
    t["r2w"] = ((t.first_correct == 1) & (t.final_correct == 0)).astype(float)
    t["net"] = t.w2r - t.r2w
    t["subset"] = np.where(t.evidence == "absent", "missing", "present_" + t.advice)
    return t


def gee_checks(df: pd.DataFrame) -> pd.DataFrame:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    out = []
    specs = [("C1 P3-P1 flawed_correction (logOR)", ["P1", "P3"], "flawed_correction", None),
             ("C2 P3-P2 flawed_correction (logOR)", ["P2", "P3"], "flawed_correction", None),
             ("C3 P3xabsent escalation interaction (logOR)", ["P1", "P3"], "escalated", "inter")]
    for name, procs, y, kind in specs:
        d = df[df.procedure.isin(procs)].copy()
        d["treat"] = (d.procedure == procs[1]).astype(int)
        if kind is None:
            d = d.dropna(subset=[y])
            formula, term = f"{y} ~ treat + C(model)", "treat"
        else:
            d["absent"] = (d.evidence == "absent").astype(int)
            formula, term = f"{y} ~ treat * absent + C(model)", "treat:absent"
        if d.model.nunique() == 1:
            formula = formula.replace(" + C(model)", "")
        d = d.sort_values("family_id")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = smf.gee(formula, groups="family_id", data=d, family=sm.families.Binomial(),
                            cov_struct=sm.cov_struct.Exchangeable()).fit(cov_type="bias_reduced")
            out.append(dict(model=name, coef=r.params[term], se=r.bse[term], p=r.pvalues[term],
                            n_rows=len(d), n_families=d.family_id.nunique()))
        except Exception as e:  # report, do not fail the pipeline
            out.append(dict(model=name, coef=np.nan, se=np.nan, p=np.nan, n_rows=len(d),
                            n_families=d.family_id.nunique(), error=str(e)[:120]))
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------
# Main analysis
# ----------------------------------------------------------------------------
def primary_block(df: pd.DataFrame, fam: Fam):
    pairs = pair_outcomes(df)
    FC = fam.table(df, "flawed_correction")
    PA = fam.table(df, "pause_appropriate")
    UE = fam.table(df, "unnecessary_escalation")
    AO = fam.table(df, "aligned_overturn")
    # NI2 outcome: irrelevant_stability among correctly decided base cases, pooled over advice
    ST = fam.ratio_table(pairs, "irrelevant_stability", "base_correct")
    prim = []
    if {"P1", "P3"} <= set(FC.columns):
        prim.append(fam.contrast(FC.P3 - FC.P1, "C1: P3 - P1 flawed_correction"))
    if {"P2", "P3"} <= set(FC.columns):
        prim.append(fam.contrast(FC.P3 - FC.P2, "C2: P3 - P2 flawed_correction"))
    if {"P1", "P3"} <= set(PA.columns):
        prim.append(fam.contrast((PA.P3 - PA.P1) - (UE.P3 - UE.P1),
                                 "C3: [escalation P3-P1, absent] - [P3-P1, present]"))
    prim = pd.DataFrame(prim)
    ok = prim.p_t.notna()
    prim["p_holm"] = np.nan
    if ok.any():
        prim.loc[ok, "p_holm"] = multipletests(prim.loc[ok, "p_t"], method="holm")[1]
    prim["reject_holm_05"] = prim.p_holm < 0.05
    ni = []
    for ref in ("P0", "P1"):
        role = "decision" if ref == "P0" else "reported"
        if {"P3", ref} <= set(AO.columns):
            r = fam.contrast(AO.P3 - AO[ref], f"NI1: P3 - {ref} aligned_overturn")
            r.update(margin=+MARGIN_AO, bound=r["ci_hi"], passes=bool(r["ci_hi"] < MARGIN_AO), role=role)
            ni.append(r)
        if {"P3", ref} <= set(ST.columns):
            r = fam.contrast(ST.P3 - ST[ref], f"NI2: P3 - {ref} irrelevant_stability given base correct")
            r.update(margin=-MARGIN_ST, bound=r["ci_lo"], passes=bool(r["ci_lo"] > -MARGIN_ST), role=role)
            ni.append(r)
    return prim, pd.DataFrame(ni), pairs, dict(FC=FC, PA=PA, UE=UE, AO=AO, ST=ST)


def decide(prim: pd.DataFrame, ni: pd.DataFrame, compute_ok: bool) -> list[str]:
    get = lambda pre: prim[prim.contrast.str.startswith(pre)].iloc[0] if (prim.contrast.str.startswith(pre)).any() else None
    c1, c2, c3 = get("C1"), get("C2"), get("C3")
    nid = ni[ni.role == "decision"]
    msgs = []
    if c1 is None or nid.empty:
        return ["Decision rules not evaluable (P0/P1/P3 missing)."]
    safety = bool(nid.passes.all()) and len(nid) == 2
    if not safety:
        failed = ", ".join(nid.loc[~nid.passes, "contrast"])
        msgs.append(f"REVISE/DROP P3: non-inferiority not shown ({failed}). P3 is not adopted "
                    "whatever C1 shows; report the harm estimate.")
        return msgs
    c1_sig = bool(c1.reject_holm_05 and c1.estimate > 0)
    c2_sig = c2 is not None and bool(c2.reject_holm_05 and c2.estimate > 0)
    c3_sig = c3 is not None and bool(c3.reject_holm_05 and c3.estimate > 0)
    if c1_sig and c2_sig:
        msgs.append("ADOPT P3: source-applicability verification beats both a matched free re-check "
                    "(C1) and a matched generic checklist (C2), with non-inferiority on aligned advice "
                    "and irrelevant-change stability.")
    elif c1_sig and c2 is not None and c2.ci_hi < NEGLIGIBLE:
        msgs.append("SIMPLIFY: P3 beats P1 but is not meaningfully better than the generic checklist "
                    "P2 (upper bound of C2 < 5 points); the benefit is attributable to structured "
                    "re-checking, not to source-specific content.")
    elif c1_sig:
        msgs.append("ADOPT P3 PROVISIONALLY: P3 beats the free re-check (C1), but its advantage over "
                    "the generic checklist (C2) is unresolved; do not claim source-specificity.")
    elif c1.ci_hi < NEGLIGIBLE:
        msgs.append("DROP P3 as a mechanism: upper bound of P3 - P1 < 5 points, so the benefit of "
                    "verification is explained by an extra round of computation.")
    else:
        msgs.append("INCONCLUSIVE: C1 is not significant and effects of 5+ points are not excluded. "
                    "P3 is not adopted; no unplanned extension of the confirmation set.")
    if c1_sig or c2_sig:
        if c3_sig:
            msgs.append("Mechanism supported: P3 raises escalation selectively when decisive evidence "
                        "is absent (C3).")
        else:
            msgs.append("Escalation mechanism not supported (C3 not significant): do not claim that P3 "
                        "converts missing evidence into appropriate pauses.")
    if not compute_ok:
        msgs.append("CAUTION: P3/P1 output-token ratio is outside the pre-specified compute-match band "
                    f"{COMPUTE_MATCH}; C1 is interpreted as 'verification plus extra tokens'.")
    return msgs


def fmt_pct(x, d=1):
    return "" if pd.isna(x) else f"{100 * x:.{d}f}"


def ci_str(e, lo, hi, pct=True):
    if pct:
        return f"{fmt_pct(e)} [{fmt_pct(lo)}, {fmt_pct(hi)}]"
    return f"{e:.2f} [{lo:.2f}, {hi:.2f}]"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


def contrast_md(t: pd.DataFrame, extra=()) -> str:
    rows = []
    for _, r in t.iterrows():
        d = {"contrast": r.contrast, "F": r.n_families,
             "estimate (pts) [95% CI]": ci_str(r.estimate, r.ci_lo, r.ci_hi),
             "bootstrap 95% CI": f"[{fmt_pct(r.boot_lo)}, {fmt_pct(r.boot_hi)}]",
             "p (t)": f"{r.p_t:.4f}" if pd.notna(r.p_t) else "",
             "p (sign-flip)": f"{r.p_signflip:.4f}" if pd.notna(r.p_signflip) else ""}
        for e in extra:
            v = r.get(e)
            d[e] = (f"{v:.4f}" if isinstance(v, float) else v) if v is not None else ""
        rows.append(d)
    return md_table(pd.DataFrame(rows))


def run(path: str, out: Path, B: int, seed: int):
    out.mkdir(parents=True, exist_ok=True)
    df = load(path)
    procs = [p for p in PROCS_ALL if p in set(df.procedure)]
    fam = Fam(df.family_id.unique(), procs, B, seed)
    md = [f"# Summary tables\n\nSource: `{path}`  \nRows: {len(df)}; families: {len(fam.families)}; "
          f"models: {df.model.nunique()}; repeats: {df['repeat'].nunique()}; procedures: {', '.join(procs)}  \n"
          f"Estimates are family-weighted means (percentage points); 95% CIs are t-based on family-level "
          f"values unless labelled bootstrap (family cluster bootstrap, B = {B}).\n"]

    # --- primary
    prim, ni, pairs, mats = primary_block(df, fam)
    prim.to_csv(out / "primary_contrasts.csv", index=False)
    ni.to_csv(out / "noninferiority.csv", index=False)
    md.append("## 1. Primary contrasts (Holm, FWER .05, two-sided)\n")
    md.append(contrast_md(prim, extra=("p_holm",)))
    md.append("\n## 2. Non-inferiority (95% CI bound vs margin; decision rows use P0)\n")
    nit = pd.DataFrame([{"contrast": r.contrast, "role": r.role,
                         "estimate [95% CI]": ci_str(r.estimate, r.ci_lo, r.ci_hi),
                         "margin": fmt_pct(r.margin), "bound": fmt_pct(r.bound),
                         "bootstrap-t bound": fmt_pct(r.get("boott_hi") if r.margin > 0 else r.get("boott_lo")),
                         "passes": r.passes} for _, r in ni.iterrows()])
    md.append(md_table(nit) if len(nit) else "(not evaluable)")

    # --- cost (needed for the decision rule)
    cost_rows, cmats = [], {}
    for c in ["input_tokens", "output_tokens", "total_tokens", "latency_s", "n_calls"]:
        mat = fam.table(df, c)
        cmats[c] = mat
        s = fam.summarize(mat)
        s.insert(0, "metric", c)
        cost_rows.append(s)
    cost = pd.concat(cost_rows, ignore_index=True)
    ratios = []
    for c in ["output_tokens", "total_tokens", "latency_s"]:
        mat = cmats[c]
        for ref in ("P0", "P1"):
            for p in procs:
                if p == ref or ref not in mat:
                    continue
                num, den = mat[p].to_numpy(float), mat[ref].to_numpy(float)
                bn, bd = fam.boot_means(num), fam.boot_means(den)
                ratios.append(dict(metric=c, ratio=f"{p}/{ref}", estimate=np.nanmean(num) / np.nanmean(den),
                                   ci_lo=np.nanpercentile(bn / bd, 2.5), ci_hi=np.nanpercentile(bn / bd, 97.5)))
    ratios = pd.DataFrame(ratios)
    compute_ok = True
    r31 = ratios[(ratios.metric == "output_tokens") & (ratios.ratio == "P3/P1")]
    if len(r31):
        compute_ok = COMPUTE_MATCH[0] <= r31.estimate.iloc[0] <= COMPUTE_MATCH[1]
    # incremental tokens per additional flawed-advice correction
    inc = []
    FC = mats["FC"]
    for ref in ("P0", "P1"):
        if ref in FC and "P3" in FC:
            dt = (cmats["total_tokens"]["P3"] - cmats["total_tokens"][ref]).to_numpy(float)
            dc = (FC["P3"] - FC[ref]).to_numpy(float)
            bt, bc = fam.boot_means(dt), fam.boot_means(dc)
            okb = bc > 0
            ratio = np.where(okb, bt / np.where(okb, bc, 1), np.nan)
            inc.append(dict(comparison=f"P3 vs {ref}", extra_tokens_per_response=np.nanmean(dt),
                            extra_correct_per_flawed_item=np.nanmean(dc),
                            tokens_per_extra_correction=np.nanmean(dt) / np.nanmean(dc) if np.nanmean(dc) > 0 else np.nan,
                            boot_lo=np.nanpercentile(ratio, 2.5) if okb.any() else np.nan,
                            boot_hi=np.nanpercentile(ratio, 97.5) if okb.any() else np.nan,
                            share_boot_gain_positive=okb.mean()))
    inc = pd.DataFrame(inc)
    cost.to_csv(out / "cost.csv", index=False)
    ratios.to_csv(out / "cost_ratios.csv", index=False)
    inc.to_csv(out / "cost_incremental.csv", index=False)

    md.append("\n## 3. Pre-specified decision rule\n")
    for m in decide(prim, ni, compute_ok):
        md.append(f"- {m}")

    # --- descriptive outcomes by procedure
    resp_outcomes = ["flawed_correction", "aligned_overturn", "pause_appropriate",
                     "unnecessary_escalation", "follow_flawed", "accuracy", "citation", "parse_failure"]
    pair_names = ["counterfactual_success", "irrelevant_stability", "irrelevant_stability_aligned",
                  "paraphrase_stability", "irrelevant_flip", "paraphrase_flip"]
    long = []
    for y in resp_outcomes:
        s = fam.summarize(fam.table(df, y)); s.insert(0, "outcome", y); long.append(s)
    for y in pair_names:
        s = fam.summarize(fam.table(pairs, y)); s.insert(0, "outcome", y); long.append(s)
    s = fam.summarize(mats["ST"]); s.insert(0, "outcome", "irrelevant_stability_given_base_correct"); long.append(s)
    long = pd.concat(long, ignore_index=True)
    long.to_csv(out / "outcomes_by_procedure.csv", index=False)
    wide = long.assign(v=[ci_str(e, l, h) for e, l, h in zip(long.estimate, long.ci_lo, long.ci_hi)]) \
        .pivot(index="outcome", columns="procedure", values="v").reindex(
            resp_outcomes + pair_names + ["irrelevant_stability_given_base_correct"])
    md.append("\n## 4. Outcomes by procedure (%, family-bootstrap 95% CI)\n")
    md.append(md_table(wide.reset_index()))

    # --- by evidence x advice and by state
    sub_rows = []
    for (ev, adv), d in df.groupby(["evidence", "advice"]):
        for y in ["correct", "escalated", "followed_advice"]:
            s = fam.summarize(fam.table(d, y))
            s.insert(0, "outcome", y); s.insert(0, "advice", adv); s.insert(0, "evidence", ev)
            sub_rows.append(s)
    sub = pd.concat(sub_rows, ignore_index=True)
    sub.to_csv(out / "outcomes_by_procedure_evidence_advice.csv", index=False)
    w2 = sub.assign(v=[ci_str(e, l, h) for e, l, h in zip(sub.estimate, sub.ci_lo, sub.ci_hi)]) \
        .pivot(index=["evidence", "advice", "outcome"], columns="procedure", values="v").reset_index()
    md.append("\n## 5. By evidence x advice (%, bootstrap CI)\n")
    md.append(md_table(w2))
    st_rows = []
    for (stt, adv), d in df.groupby(["state", "advice"]):
        for y in ["correct", "escalated"]:
            s = fam.summarize(fam.table(d, y))
            s.insert(0, "outcome", y); s.insert(0, "advice", adv); s.insert(0, "state", stt)
            st_rows.append(s)
    stt = pd.concat(st_rows, ignore_index=True)
    stt.to_csv(out / "outcomes_by_procedure_state_advice.csv", index=False)
    w3 = stt[stt.outcome == "correct"].assign(v=lambda x: [fmt_pct(e) for e in x.estimate]) \
        .pivot(index=["state", "advice"], columns="procedure", values="v").reset_index()
    md.append("\n## 6. Accuracy by state x advice (%, point estimates; CIs in CSV)\n")
    md.append(md_table(w3))

    # by model (descriptive) and per-model C1
    bm_rows = []
    for mname, d in df.groupby("model"):
        t = d.dropna(subset=["flawed_correction"]).groupby(["family_id", "procedure"]).flawed_correction.mean().unstack()
        t = t.reindex(index=fam.families)
        for p in procs:
            if p in t:
                bm_rows.append(dict(model=mname, procedure=p, flawed_correction=np.nanmean(t[p])))
        if {"P1", "P3"} <= set(t.columns):
            r = fam.contrast(t.P3 - t.P1, f"C1 within {mname}")
            bm_rows.append(dict(model=mname, procedure="P3-P1", flawed_correction=r["estimate"],
                                ci_lo=r["ci_lo"], ci_hi=r["ci_hi"]))
    bymodel = pd.DataFrame(bm_rows)
    bymodel.to_csv(out / "outcomes_by_model.csv", index=False)

    # --- exploratory contrasts (no multiplicity adjustment)
    FC, PA, UE, AO = mats["FC"], mats["PA"], mats["UE"], mats["AO"]
    tabs = {y: fam.table(pairs if y in pair_names else df, y) for y in
            ["counterfactual_success", "paraphrase_stability", "irrelevant_flip", "citation",
             "follow_flawed", "irrelevant_stability"]}
    ex = []

    def add(expr_ok, d, name):
        if expr_ok:
            ex.append(fam.contrast(d, name))

    have = set(FC.columns)
    add({"P3", "P4"} <= have, FC.get("P3") - FC.get("P4") if {"P3", "P4"} <= have else None,
        "E1: P3 - P4 flawed_correction (source checking vs cue naming)")
    add({"P4", "P1"} <= have, FC.get("P4") - FC.get("P1") if {"P4", "P1"} <= have else None,
        "E2: P4 - P1 flawed_correction (cue naming vs free re-check)")
    for a, b in [("P3", "P0"), ("P2", "P1"), ("P1", "P0")]:
        add({a, b} <= have, FC.get(a) - FC.get(b) if {a, b} <= have else None, f"{a} - {b} flawed_correction")
    if {"P3", "P4"} <= set(PA.columns):
        ex.append(fam.contrast((PA.P3 - PA.P4) - (UE.P3 - UE.P4),
                               "C3 analogue with P4: [esc P3-P4, absent] - [P3-P4, present]"))
    if {"P1", "P3"} <= have:
        AC = 1 - AO
        ex.append(fam.contrast((FC.P3 - FC.P1) - (AC.P3 - AC.P1),
                               "advice x procedure: (P3-P1, flawed) - (P3-P1, aligned), correct"))
        for y, m in [("pause_appropriate", PA), ("unnecessary_escalation", UE)]:
            ex.append(fam.contrast(m.P3 - m.P1, f"P3 - P1 {y}"))
        for y, m in tabs.items():
            if {"P1", "P3"} <= set(m.columns):
                ex.append(fam.contrast(m.P3 - m.P1, f"P3 - P1 {y}"))
    ex = pd.DataFrame(ex)
    ex.to_csv(out / "exploratory_contrasts.csv", index=False)
    md.append("\n## 7. Secondary / exploratory contrasts (unadjusted; P4 contrasts exploratory)\n")
    md.append(contrast_md(ex))

    # --- SDT
    dprime, crit = sdt_tables(df, fam)
    sdt = []
    for nm, mat in (("d_prime", dprime), ("criterion_c", crit)):
        s = fam.summarize(mat); s.insert(0, "measure", nm); sdt.append(s)
    sdt = pd.concat(sdt, ignore_index=True)
    sdtc = []
    for nm, mat in (("d_prime", dprime), ("criterion_c", crit)):
        for a, b in [("P3", "P1"), ("P3", "P2"), ("P3", "P4"), ("P1", "P0")]:
            if {a, b} <= set(mat.columns):
                sdtc.append(fam.contrast(mat[a] - mat[b], f"{nm}: {a} - {b}"))
    sdtc = pd.DataFrame(sdtc)
    sdt.to_csv(out / "sdt.csv", index=False)
    sdtc.to_csv(out / "sdt_contrasts.csv", index=False)
    md.append("\n## 8. Signal detection (hit = flawed-advice correction, false alarm = aligned overturn)\n")
    md.append("Per family x procedure with log-linear correction; c < 0 = more liberal overturning.\n")
    md.append(md_table(sdt.assign(v=[ci_str(e, l, h, pct=False) for e, l, h in zip(sdt.estimate, sdt.ci_lo, sdt.ci_hi)])
                       .pivot(index="measure", columns="procedure", values="v").reset_index()))
    md.append("")
    md.append(md_table(pd.DataFrame([{"contrast": r.contrast, "estimate [95% CI]": ci_str(r.estimate, r.ci_lo, r.ci_hi, pct=False),
                                      "p (t)": f"{r.p_t:.4f}"} for _, r in sdtc.iterrows()])))

    # --- flips vs resampling baseline
    ft = flip_tables(df, fam)
    flips, flipc = [], []
    for sub_name, d in ft.groupby("subset"):
        fprocs = [p for p in ["P0pair"] + procs if p in set(d.procedure)]
        for y in ["flip", "w2r", "r2w", "net"]:
            g = d.groupby(["family_id", "procedure", "model"])[y].mean().groupby(["family_id", "procedure"]).mean()
            mat = g.unstack("procedure").reindex(index=fam.families, columns=fprocs)
            s = fam.summarize(mat); s.insert(0, "measure", y); s.insert(0, "subset", sub_name)
            flips.append(s)
            if "P0pair" in mat:
                for p in [x for x in fprocs if x != "P0pair"]:
                    r = fam.contrast(mat[p] - mat["P0pair"], f"{sub_name} {y}: {p} - P0pair")
                    flipc.append(r)
    flips = pd.concat(flips, ignore_index=True)
    flipc = pd.DataFrame(flipc)
    flips.to_csv(out / "flips.csv", index=False)
    flipc.to_csv(out / "flips_vs_resampling.csv", index=False)
    md.append("\n## 9. First-pass -> final changes vs resampling baseline (two independent P0 runs)\n")
    md.append("flip = action changed; w2r = wrong->right; r2w = right->wrong; net = w2r - r2w (%).\n")
    fw = flips.assign(v=[fmt_pct(e) for e in flips.estimate]) \
        .pivot(index=["subset", "measure"], columns="procedure", values="v").reset_index()
    md.append(md_table(fw))
    if len(flipc):
        sel = flipc[flipc.contrast.str.contains("net") | flipc.contrast.str.contains("flip:")]
        md.append("")
        md.append(md_table(pd.DataFrame([{"contrast": r.contrast, "estimate [95% CI]": ci_str(r.estimate, r.ci_lo, r.ci_hi),
                                          "p (t)": f"{r.p_t:.4f}"} for _, r in sel.iterrows()])))
    fp = df[(df.procedure != "P0") & (df.first_action != "")].assign(
        first_correct=lambda x: (x.first_action == x.key_action).astype(float))
    if len(fp):
        fpm = fam.summarize(fam.table(fp, "first_correct"))
        p0acc = fam.summarize(fam.table(df[df.procedure == "P0"], "accuracy"))
        md.append("\nManipulation check - first-pass accuracy (all items): " +
                  "; ".join(f"{r.procedure} {fmt_pct(r.estimate)}" for _, r in fpm.iterrows()) +
                  (f"; P0 final {fmt_pct(p0acc.estimate.iloc[0])}" if len(p0acc) else ""))

    # --- robustness
    md.append("\n## 10. Robustness\n")
    gee = gee_checks(df)
    gee.to_csv(out / "gee_robustness.csv", index=False)
    md.append("GEE (binomial, exchangeable within family, bias-reduced SE; adjusted for model):\n")
    md.append(md_table(gee.assign(coef=gee.coef.round(3), se=gee.se.round(3), p=gee.p.round(4))))
    pf = df.groupby("procedure").parse_failure.mean()
    md.append("\nParse-failure rate by procedure (%): " + ", ".join(f"{k} {fmt_pct(v, 2)}" for k, v in pf.items()))
    dfx = load(path)
    dfx = dfx[dfx.parse_ok == 1]
    if len(dfx) < len(df):
        famx = Fam(dfx.family_id.unique(), procs, B, seed)
        px, nx, _, _ = primary_block(dfx, famx)
        px.to_csv(out / "primary_contrasts_excluding_parse_failures.csv", index=False)
        md.append("\nPrimary contrasts excluding parse failures:\n")
        md.append(contrast_md(px, extra=("p_holm",)))
        md.append("")
        md.append(md_table(pd.DataFrame([{"contrast": r.contrast, "estimate [95% CI]": ci_str(r.estimate, r.ci_lo, r.ci_hi),
                                          "passes": r.passes} for _, r in nx[nx.role == "decision"].iterrows()])))

    # --- cost
    md.append("\n## 11. Cost (means per response, family-bootstrap 95% CI)\n")
    cw = cost.assign(v=[f"{e:,.1f} [{l:,.1f}, {h:,.1f}]" for e, l, h in zip(cost.estimate, cost.ci_lo, cost.ci_hi)]) \
        .pivot(index="metric", columns="procedure", values="v").reset_index()
    md.append(md_table(cw))
    md.append("")
    md.append(md_table(ratios.assign(v=[f"{e:.2f} [{l:.2f}, {h:.2f}]" for e, l, h in
                                        zip(ratios.estimate, ratios.ci_lo, ratios.ci_hi)])[["metric", "ratio", "v"]]))
    md.append(f"\nCompute-match check (P3/P1 output tokens within {COMPUTE_MATCH}): {'OK' if compute_ok else 'FAILED'}")
    if len(inc):
        md.append("")
        md.append(md_table(inc.round(3)))
    (out / "summary_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    fam_level = []
    for k, m in mats.items():
        t = m.copy(); t["outcome"] = k; fam_level.append(t.reset_index())
    pd.concat(fam_level).to_csv(out / "family_level_outcomes.csv", index=False)
    print(f"wrote {out / 'summary_tables.md'} and CSVs")
    print(prim[["contrast", "n_families", "estimate", "ci_lo", "ci_hi", "p_t", "p_signflip", "p_holm"]]
          .round(4).to_string(index=False))
    print(ni[["contrast", "role", "estimate", "bound", "margin", "passes"]].round(4).to_string(index=False))
    for m in decide(prim, ni, compute_ok):
        print("DECISION:", m)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "results" / "analysis"))
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    run(a.csv, Path(a.out), a.boot, a.seed)


if __name__ == "__main__":
    main()
