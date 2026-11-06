"""Synthetic scored_runs.csv generator for the mechanism study (computational line).

Purpose: test the analysis pipeline (analyze.py) and provide the data-generating
model used by power_confirmation.py before any real model responses exist.

Data-generating model (per model m, family f, item i = state x advice,
procedure p, repeat k). Two independent latent logit processes:

  escalate      ~ Bernoulli(expit(eta_esc))                 (all items)
  correct | not escalated ~ Bernoulli(expit(eta_cne))       (evidence-present items)

  eta = mu[p, i] + beta_m + b_f + u_{f,p} + c_{m,f} + v_{f,i} + w_{f,i,p}
        + z_{m,f,i} + e_{m,f,i,p}

  b_f        family random intercept          SD sd_family
  u_{f,p}    procedure-by-family slope        SD sd_slope (P0 = reference, 0)
Procedures: P0 baseline; P1 free re-check; P2 generic checklist; P3 source-
applicability verification; P4 (exploratory) free re-check + one sentence naming
the three mismatch types, no instruction to check sources.
  c_{m,f}    model-by-family                  SD sd_model_family
  v_{f,i}    item within family               SD sd_item
  w_{f,i,p}  item-by-procedure                SD sd_item_proc
  z_{m,f,i}  model-by-item                    SD sd_model_item
  e_{m,f,i,p} model-by-item-by-procedure      SD sd_cell (shared by repeats;
                                              this is what makes repeats redundant)
  irrelevant_change and paraphrase items share v, w, z, e with the base item
  of the same advice at correlation rho_variant (near-duplicates).

mu[p, i] is calibrated numerically so that the MARGINAL rate (averaged over all
random effects and the included models) equals the target rate, so effects are
risk differences in percentage points, i.e. the estimand of the analysis plan.

Usage:
  python simulate_synthetic.py --out synthetic/scored_runs.csv \
      --families 8 --models 3 --repeats 3 --effect 0.10 --interaction 0.15
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

PROCS = ["P0", "P1", "P2", "P3", "P4"]   # P4 = exploratory cue-only re-check
NP = len(PROCS)
STATES = ["base", "decisive_change", "irrelevant_change", "paraphrase", "missing"]
ADVICE = ["aligned", "flawed"]
ITEMS = [(s, a) for s in STATES for a in ADVICE]          # 10 items, index = 2*s + a
I_PF = [1, 3, 5, 7]        # evidence present, flawed advice
I_PA = [0, 2, 4, 6]        # evidence present, aligned advice
I_PRESENT = list(range(8))
I_ABSENT = [8, 9]          # missing state (aligned, flawed)
I_BASE_AL, I_IRR_AL = 0, 4
VARIANT_OF = {4: 0, 5: 1, 6: 0, 7: 1}   # irrelevant/paraphrase item -> base item
DOMAINS = ["budgeting_procurement", "student_data_privacy", "programme_adoption",
           "policy_compliance_dates", "safety_operations"]
MISMATCH = ["authority", "scope", "version", "effective_date", "cost_completeness",
            "data_permission", "evidence_strength"]
MODEL_EFFECTS = [0.0, -0.4, 0.4]   # fixed logit shifts for up to 3 models

# ----------------------------------------------------------------------------
# Default assumptions (planning values; replace with development estimates)
# Rates are marginal probabilities. P3 values are derived from the effects.
# ----------------------------------------------------------------------------
DEFAULTS = {
    "correct_present_flawed": {"P0": 0.50, "P1": 0.55, "P2": 0.57},   # P3 = P1 + effect; P4 = P1 + cue_effect
    "correct_present_aligned": {"P0": 0.96, "P1": 0.94, "P2": 0.94, "P3": 0.95, "P4": 0.94},
    "esc_present": {"P0": 0.03, "P1": 0.04, "P2": 0.05, "P4": 0.04},  # P3 = P1 + esc_present_shift
    "esc_absent_aligned": {"P0": 0.70, "P1": 0.72, "P2": 0.74},       # P3 = P1 + interaction + shift
    "esc_absent_flawed": {"P0": 0.30, "P1": 0.35, "P2": 0.38},        # P4 = P1 + cue_interaction
    "effect": 0.10,              # P3 - P1 on flawed_correction (evidence present)
    "interaction": 0.10,         # [esc_abs(P3)-esc_abs(P1)] - [esc_pres(P3)-esc_pres(P1)]
    "esc_present_shift": 0.0,
    "cue_effect": 0.03,          # P4 - P1 on flawed_correction (naming the mismatch types only)
    "cue_interaction": 0.03,     # P4 - P1 on escalation when evidence is absent    # P3 - P1 unnecessary escalation ("generic caution")
    "irr_penalty_P3": 0.0,       # extra P3 error on irrelevant_change items (prob. points)
    "sd_family": 1.0,
    "sd_slope": 0.5,
    "sd_model_family": 0.4,
    "sd_item": 0.8,
    "sd_item_proc": 0.4,
    "sd_model_item": 2.0,        # main source of repeat-to-repeat determinism
    "sd_cell": 1.0,
    "rho_variant": 0.8,
    "follow_prob": 0.80,         # P(choose advised action | wrong, flawed advice)
    "anchor": 0.80,              # P(review keeps the first-pass answer) where marginals allow
}

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(64)
_GH_W = _GH_W / np.sqrt(2 * np.pi)


def params_with(**kw) -> dict:
    p = copy.deepcopy(DEFAULTS)
    for k, v in kw.items():
        if k not in p:
            raise KeyError(f"unknown parameter {k}")
        p[k] = v
    return p


def target_table(par: dict) -> dict[str, np.ndarray]:
    """Marginal targets (P x I) for the two processes: esc and correct (unconditional)."""
    esc = np.zeros((NP, 10))
    cor = np.full((NP, 10), np.nan)
    e = par["effect"]
    cpf = dict(par["correct_present_flawed"]); cpf["P3"] = cpf["P1"] + e
    cpf["P4"] = cpf["P1"] + par["cue_effect"]
    cpa = dict(par["correct_present_aligned"])
    ep = dict(par["esc_present"]); ep["P3"] = ep["P1"] + par["esc_present_shift"]
    eaa = dict(par["esc_absent_aligned"]); eaf = dict(par["esc_absent_flawed"])
    eaa["P3"] = eaa["P1"] + par["interaction"] + par["esc_present_shift"]
    eaf["P3"] = eaf["P1"] + par["interaction"] + par["esc_present_shift"]
    eaa["P4"] = eaa["P1"] + par["cue_interaction"]
    eaf["P4"] = eaf["P1"] + par["cue_interaction"]
    for pi, p in enumerate(PROCS):
        for i in I_PRESENT:
            esc[pi, i] = ep[p]
            cor[pi, i] = cpf[p] if i in I_PF else cpa[p]
            if p == "P3" and ITEMS[i][0] == "irrelevant_change":
                cor[pi, i] -= par["irr_penalty_P3"]
        esc[pi, 8] = eaa[p]
        esc[pi, 9] = eaf[p]
    esc = np.clip(esc, 0.005, 0.995)
    cor = np.clip(cor, 0.005, 0.995)
    bad = cor[:, I_PRESENT] + esc[:, I_PRESENT] > 0.998
    if bad.any():
        raise ValueError("correct + unnecessary escalation targets exceed 1")
    cne = cor.copy()
    cne[:, I_PRESENT] = cor[:, I_PRESENT] / (1 - esc[:, I_PRESENT])
    return {"esc": esc, "cne": np.clip(cne, 0.005, 0.995), "correct": cor}


def total_sd(par: dict, proc_index: int) -> float:
    v = (par["sd_family"] ** 2 + par["sd_model_family"] ** 2 + par["sd_item"] ** 2
         + par["sd_item_proc"] ** 2 + par["sd_model_item"] ** 2 + par["sd_cell"] ** 2)
    if proc_index > 0:
        v += par["sd_slope"] ** 2
    return float(np.sqrt(v))


def calibrate_mu(target: float, sd: float, model_effects) -> float:
    beta = np.asarray(model_effects, float)

    def f(mu):
        x = mu + beta[:, None] + sd * _GH_X[None, :]
        return float((expit(x) @ _GH_W).mean() - target)

    return brentq(f, -25, 25, xtol=1e-8)


def calibrated_mus(par: dict, n_models: int) -> dict[str, np.ndarray]:
    tt = target_table(par)
    beta = MODEL_EFFECTS[:n_models]
    out = {}
    for proc in ("esc", "cne"):
        mu = np.zeros((NP, 10))
        for pi in range(NP):
            sd = total_sd(par, pi)
            for i in range(10):
                t = tt[proc][pi, i]
                mu[pi, i] = calibrate_mu(t, sd, beta) if np.isfinite(t) else 0.0
        out[proc] = mu
    return out


def _variant_mix(x: np.ndarray, rho: float, item_axis: int) -> np.ndarray:
    """Make irrelevant/paraphrase items correlate with their base item."""
    x = np.moveaxis(x, item_axis, -1).copy()
    s = np.sqrt(1 - rho ** 2)
    for i, b in VARIANT_OF.items():
        x[..., i] = rho * x[..., b] + s * x[..., i]
    return np.moveaxis(x, -1, item_axis)


def draw_latent_probs(par: dict, mus: dict, n_sims: int, n_models: int, n_fam: int,
                      rng: np.random.Generator, procs=None) -> dict[str, np.ndarray]:
    """Return probabilities with shape (S, M, F, I, P) for 'esc' and 'cne'.
    procs: optional list of procedure indices to simulate (default all)."""
    procs = list(range(NP)) if procs is None else list(procs)
    S, M, F, I, P = n_sims, n_models, n_fam, 10, len(procs)
    beta = np.asarray(MODEL_EFFECTS[:M]).reshape(1, M, 1, 1, 1)
    rho = par["rho_variant"]
    out = {}
    for proc in ("esc", "cne"):
        eta = mus[proc][procs].T.reshape(1, 1, 1, I, P) + beta
        eta = eta + par["sd_family"] * rng.standard_normal((S, 1, F, 1, 1))
        u = par["sd_slope"] * rng.standard_normal((S, 1, F, 1, P))
        if 0 in procs:
            u[..., procs.index(0)] = 0.0
        eta = eta + u
        eta = eta + par["sd_model_family"] * rng.standard_normal((S, M, F, 1, 1))
        for sd, shape in ((par["sd_item"], (S, 1, F, I, 1)),
                          (par["sd_item_proc"], (S, 1, F, I, P)),
                          (par["sd_model_item"], (S, M, F, I, 1)),
                          (par["sd_cell"], (S, M, F, I, P))):
            if sd > 0:
                eta = eta + sd * _variant_mix(rng.standard_normal(shape), rho, 3)
        out[proc] = expit(eta)
    return out


# ----------------------------------------------------------------------------
# Full response-level synthetic data
# ----------------------------------------------------------------------------
def build_design(n_fam: int, rng: np.random.Generator, prefix: str = "F") -> pd.DataFrame:
    rows = []
    letters = ["A", "B", "C", "D"]
    for f in range(n_fam):
        fid = f"{prefix}{f + 1:03d}"
        base_key = rng.choice(letters)
        dec_key = rng.choice([x for x in letters if x != base_key])
        for i, (s, a) in enumerate(ITEMS):
            if s == "missing":
                key = "E"
                adv = "E" if a == "aligned" else base_key
            elif s == "decisive_change":
                key = dec_key
                adv = key if a == "aligned" else base_key
            else:
                key = base_key
                adv = key if a == "aligned" else dec_key
            rows.append(dict(family_id=fid, domain=DOMAINS[f % len(DOMAINS)],
                             mismatch_type=MISMATCH[f % len(MISMATCH)], item=i, state=s,
                             evidence="absent" if s == "missing" else "present",
                             advice=a, key_action=key, advised_action=adv))
    return pd.DataFrame(rows)


def simulate_rows(par: dict, n_fam: int, n_models: int, n_rep: int,
                  rng: np.random.Generator, parse_fail=None, family_prefix="F") -> pd.DataFrame:
    parse_fail = parse_fail or {"P0": 0.01, "P1": 0.01, "P2": 0.015, "P3": 0.015, "P4": 0.01}
    mus = calibrated_mus(par, n_models)
    pr = draw_latent_probs(par, mus, 1, n_models, n_fam, rng)
    pe, pc = pr["esc"][0], pr["cne"][0]                 # (M, F, I, P)
    design = build_design(n_fam, rng, family_prefix)
    letters = np.array(["A", "B", "C", "D"])
    kappa = par.get("anchor", 0.8)   # P(final keeps first-pass answer), before marginal constraint
    cite = {"P0": 0.55, "P1": 0.58, "P2": 0.65, "P3": 0.80, "P4": 0.60}
    second_out = {"P1": 300, "P2": 360, "P3": 370, "P4": 310}
    extra_in = {"P1": 60, "P2": 150, "P3": 250, "P4": 90}
    cap = 600
    fam_in = rng.normal(2400, 300, n_fam).clip(1200)

    def cat_probs(m, f, i, p_idx):
        """Category probabilities: E escalate, K key action, A advised wrong action, O other wrong."""
        d = design.iloc[f * 10 + i]
        e, c, phi = pe[m, f, i, p_idx], pc[m, f, i, p_idx], par["follow_prob"]
        if d.evidence == "present":
            if d.advice == "flawed":
                return np.array([e, (1 - e) * c, (1 - e) * (1 - c) * phi, (1 - e) * (1 - c) * (1 - phi)])
            return np.array([e, (1 - e) * c, 0.0, (1 - e) * (1 - c)])
        if d.advice == "flawed":
            return np.array([e, 0.0, (1 - e) * phi, (1 - e) * (1 - phi)])
        return np.array([e, 0.0, 0.0, 1 - e])

    def letter(cat, d):
        if cat == 0:
            return "E"
        if cat == 1:
            return d.key_action
        if cat == 2:
            return d.advised_action
        others = [x for x in letters if x not in (d.key_action, d.advised_action)]
        return str(rng.choice(others))

    def draw_pair(m, f, i, p_idx):
        """Final action (marginal = procedure p) and first-pass action (marginal = P0).
        Exact-marginal coupling: final = first with prob k, else drawn from the residual
        distribution g = (q - k*f)/(1 - k), with k <= min(q/f) so g >= 0."""
        d = design.iloc[f * 10 + i]
        q = cat_probs(m, f, i, p_idx)
        if p_idx == 0:
            return letter(rng.choice(4, p=q / q.sum()), d), ""
        f0 = cat_probs(m, f, i, 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            kmax = np.nanmin(np.where(f0 > 0, q / f0, np.inf))
        k = min(kappa, kmax, 0.999)
        c1 = rng.choice(4, p=f0 / f0.sum())
        first = letter(c1, d)
        if rng.random() < k:
            return first, first
        g = np.clip(q - k * f0, 0, None)
        return letter(rng.choice(4, p=g / g.sum()), d), first

    out = []
    rid = 0
    for m in range(n_models):
        model = f"model_{m + 1}"
        for f in range(n_fam):
            for i in range(10):
                d = design.iloc[f * 10 + i]
                for p_idx, p in enumerate(PROCS):
                    for k in range(1, n_rep + 1):
                        rid += 1
                        act, first = draw_pair(m, f, i, p_idx)
                        parse_ok = int(rng.random() >= parse_fail[p])
                        if not parse_ok:
                            act = ""
                        corr = int(parse_ok and act == d.key_action)
                        out1 = float(rng.lognormal(np.log(320), 0.35))
                        if p == "P0":
                            n_calls, out_tok = 1, out1
                            in_tok = fam_in[f] + rng.normal(0, 80)
                        else:
                            n_calls = 2
                            out2 = min(cap, float(rng.lognormal(np.log(second_out[p]), 0.35)))
                            out_tok = out1 + out2
                            in_tok = 2 * fam_in[f] + out1 + extra_in[p] + rng.normal(0, 120)
                        lat = 0.8 * n_calls + out_tok / 60 + abs(rng.normal(0, 0.8))
                        cprob = cite[p] * (1.0 if corr else 0.6)
                        out.append(dict(
                            run_id=f"R{rid:07d}", model=model, procedure=p,
                            family_id=d.family_id, domain=d.domain,
                            mismatch_type=d.mismatch_type, state=d.state,
                            evidence=d.evidence, advice=d.advice, repeat=k,
                            key_action=d.key_action, advised_action=d.advised_action,
                            action=act, parse_ok=parse_ok, correct=corr,
                            followed_advice=int(parse_ok and act == d.advised_action),
                            escalated=int(parse_ok and act == "E"),
                            citation_complete=int(parse_ok and rng.random() < cprob),
                            first_action=first,
                            changed_after_review="" if p == "P0" else int(first != act),
                            input_tokens=int(round(in_tok)), output_tokens=int(round(out_tok)),
                            latency_s=round(lat, 2), n_calls=n_calls))
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).parent / "synthetic" / "scored_runs.csv"))
    ap.add_argument("--families", type=int, default=8)
    ap.add_argument("--models", type=int, default=3, choices=[1, 2, 3])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--effect", type=float, default=DEFAULTS["effect"])
    ap.add_argument("--interaction", type=float, default=DEFAULTS["interaction"])
    ap.add_argument("--esc-present-shift", type=float, default=0.0)
    ap.add_argument("--irr-penalty", type=float, default=0.0)
    ap.add_argument("--cue-effect", type=float, default=DEFAULTS["cue_effect"])
    ap.add_argument("--sd-family", type=float, default=DEFAULTS["sd_family"])
    ap.add_argument("--sd-slope", type=float, default=DEFAULTS["sd_slope"])
    ap.add_argument("--sd-cell", type=float, default=DEFAULTS["sd_cell"])
    ap.add_argument("--family-prefix", default="F")
    ap.add_argument("--seed", type=int, default=20261105)
    a = ap.parse_args()
    par = params_with(effect=a.effect, interaction=a.interaction,
                      esc_present_shift=a.esc_present_shift, irr_penalty_P3=a.irr_penalty,
                      cue_effect=a.cue_effect,
                      sd_family=a.sd_family, sd_slope=a.sd_slope, sd_cell=a.sd_cell)
    rng = np.random.default_rng(a.seed)
    df = simulate_rows(par, a.families, a.models, a.repeats, rng, family_prefix=a.family_prefix)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows ({a.families} families x 10 items x {NP} procedures x "
          f"{a.models} models x {a.repeats} repeats) -> {out}")
    g = df[(df.evidence == "present") & (df.advice == "flawed")].groupby("procedure").correct.mean()
    print("flawed_correction by procedure (sample):", g.round(3).to_dict())
    g = df[df.state == "missing"].groupby("procedure").escalated.mean()
    print("pause_appropriate by procedure (sample):", g.round(3).to_dict())


if __name__ == "__main__":
    main()
