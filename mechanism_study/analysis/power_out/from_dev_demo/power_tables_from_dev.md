# Confirmation-set power: simulation tables_from_dev

Power = share of simulated confirmation sets in which the contrast is rejected by Holm (FWER .05, two-sided, correct direction); NI = share in which the 95% bound clears the margin; adopt = C1 & C2 (Holm) & NI1 & NI2.

Parameters: {"effect": 0.1, "interaction": 0.1, "sd_family": 1.625, "sd_slope": 0.625, "sd_model_family": 0.4, "sd_item": 0.8, "sd_item_proc": 0.4, "sd_model_item": 1.25, "sd_cell": 1.0, "rho_variant": 0.8}

Inputs re-estimated from `synthetic/scored_runs_dev8.csv` (F = 8, M = 3, R = 3). Observed summaries: {"rep_agree": 0.738, "sd_fam": 0.242, "sd_diff": 0.156}. Moment-matched SDs: {'sd_family': 1.625, 'sd_slope': 0.625, 'sd_model_item': 1.25}. Observed dev P3 - P1 = 0.014 (descriptive only; the assumed effects below are planning values, not the dev estimate).

Nonparametric check (resampled centred dev family differences + 10 points, one-sided-equivalent alpha .05/3, dev M and R): {"16": 0.35, "24": 0.6, "32": 0.77, "40": 0.87, "60": 0.98}

## A. Families x repeats x models (effect +10, interaction +10)

| M | R | 16 | 40 |
|---|---|---|---|
| 3 | 1 | 0.38 | 0.80 |
| 3 | 3 | 0.51 | 0.96 |

C1 SE (points) by families x repeats (M = 3):

| R | 16 | 40 |
|---|---|---|
| 1 | 4.84 | 3.10 |
| 3 | 3.89 | 2.55 |

Joint adopt (C1 & C2 & NI1 & NI2), M = 3:

| R | 16 | 40 |
|---|---|---|
| 1 | 0.02 | 0.31 |
| 3 | 0.16 | 0.68 |

All quantities, M = 3, R = 3:

| F | C1_holm | C2_holm | C3_holm | NI1_pass | NI2_pass | adopt_C1_NI | adopt_full |
|---|---|---|---|---|---|---|---|
| 16 | 0.51 | 0.41 | 0.44 | 0.57 | 0.64 | 0.24 | 0.16 |
| 40 | 0.96 | 0.86 | 0.92 | 0.86 | 0.93 | 0.77 | 0.68 |

## B. Effect size (C1 effect = C3 interaction; C2 effect = C1 - 2), M = 3, R = 3


C1_holm:

| effect | 16 | 40 |
|---|---|---|
| 0.1 | 0.52 | 0.97 |

C2_holm:

| effect | 16 | 40 |
|---|---|---|
| 0.1 | 0.37 | 0.89 |

C3_holm:

| effect | 16 | 40 |
|---|---|---|
| 0.1 | 0.43 | 0.91 |

adopt_full:

| effect | 16 | 40 |
|---|---|---|
| 0.1 | 0.12 | 0.67 |

## C. Family heterogeneity (logit SDs), effect +10, M = 3, R = 3


C1_holm:

| sd_family | sd_slope | 16 | 40 |
|---|---|---|---|
| 1.0 | 0.25 | 0.72 | 0.99 |
| 1.0 | 0.75 | 0.45 | 0.91 |

NI2_pass:

| sd_family | sd_slope | 16 | 40 |
|---|---|---|---|
| 1.0 | 0.25 | 0.69 | 0.97 |
| 1.0 | 0.75 | 0.67 | 0.97 |

adopt_full:

| sd_family | sd_slope | 16 | 40 |
|---|---|---|---|
| 1.0 | 0.25 | 0.19 | 0.84 |
| 1.0 | 0.75 | 0.09 | 0.62 |

## D. NI pass rates when P3 truly overturns more aligned advice than P0 (points)


NI1_pass:

| ao_worse | 16 | 40 |
|---|---|---|
| 0.01 | 0.53 | 0.81 |

NI2_pass:

| ao_worse | 16 | 40 |
|---|---|---|
| 0.01 | 0.59 | 0.96 |

adopt_full:

| ao_worse | 16 | 40 |
|---|---|---|
| 0.01 | 0.12 | 0.71 |

## Null and margin checks (M = 3, R = 3)

| check | F | rejection_rate | note |
|---|---|---|---|
| C1 null (P3 = P1) | 16 | 0.035 | two-sided, unadjusted alpha .05, 600 sims |
| C2 null (P3 = P2) | 16 | 0.056666666666666664 | two-sided, unadjusted alpha .05, 600 sims |
| C3 null (no interaction) | 16 | 0.05333333333333334 | two-sided, unadjusted alpha .05, 600 sims |
| C3 null, generic caution (+5 pts escalation everywhere) | 16 | 0.043333333333333335 | two-sided, unadjusted alpha .05, 600 sims |
| NI1 at margin (true P3-P0 overturn = +5) | 16 | 0.05333333333333334 | nominal one-sided .025; true diff 0.051 |
| C1 null (P3 = P1) | 40 | 0.041666666666666664 | two-sided, unadjusted alpha .05, 600 sims |
| C2 null (P3 = P2) | 40 | 0.03833333333333333 | two-sided, unadjusted alpha .05, 600 sims |
| C3 null (no interaction) | 40 | 0.056666666666666664 | two-sided, unadjusted alpha .05, 600 sims |
| C3 null, generic caution (+5 pts escalation everywhere) | 40 | 0.04 | two-sided, unadjusted alpha .05, 600 sims |
| NI1 at margin (true P3-P0 overturn = +5) | 40 | 0.03166666666666667 | nominal one-sided .025; true diff 0.050 |

## Analysis checks

| check | F | effect | nsim | reject_t | reject_signflip | agreement | reject_family_t | reject_gee | gee_failures |
|---|---|---|---|---|---|---|---|---|---|
| family t vs sign-flip (C1) | 16 | 0.0 | 1000 | 0.053 | 0.048 | 0.991 |  |  |  |
| family t vs sign-flip (C1) | 16 | 0.1 | 1000 | 0.65 | 0.628 | 0.966 |  |  |  |
| family t vs sign-flip (C1) | 24 | 0.0 | 1000 | 0.047 | 0.042 | 0.993 |  |  |  |
| family t vs sign-flip (C1) | 24 | 0.1 | 1000 | 0.843 | 0.832 | 0.985 |  |  |  |
| family t vs GEE bias-reduced (C1, F = 24) | 24 | 0.0 | 60 |  |  |  | 0.016666666666666666 | 0.016666666666666666 | 0.0 |
| family t vs GEE bias-reduced (C1, F = 24) | 24 | 0.1 | 60 |  |  |  | 0.9 | 0.9166666666666666 | 0.0 |
