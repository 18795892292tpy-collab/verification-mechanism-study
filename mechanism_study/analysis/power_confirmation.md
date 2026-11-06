# Confirmation-set power (computational experiment)

Drafted by the statistics line (AI-assisted), 2026-11-05; reviewed and saved by the main agent.
Script: `power_confirmation.py` (about 3.5 minutes). Outputs in `power_out/` (`power_tables.md`,
`power_grid.csv`, `null_checks.csv`, `analysis_checks.csv`). 1,000 simulated data sets per scenario;
2,000 for nulls and candidate sizes. **Every rate and variance below is a planning assumption until
re-estimated from development data with `--from-dev`.**

## Data-generating model (`simulate_synthetic.py`)

Two latent logit processes: escalate, and correct-if-not-escalated. Random-effect SDs:

| Effect | SD |
|---|---|
| family | 1.0 |
| procedure x family (each procedure) | 0.5 |
| model x family | 0.4 |
| item | 0.8 |
| item x procedure | 0.4 |
| model x item | 2.0 |
| model x item x procedure | 1.0 |

Near-duplicate states correlate .8 with the base state. Planning marginal rates:

| Outcome | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| Flawed correction | .50 | .55 | .57 | P1 + effect |
| Aligned correct | .96 | .94 | .94 | .95 |
| Unnecessary escalation | .03 | .04 | .05 | .04 |
| Escalation on missing (aligned / flawed advice) | | .72 / .35 | | P1 + interaction |

The analysis is exactly that of `analyze.py`. "Adopt" means C1 and C2 Holm-significant and both NI
tests passed.

## Error-rate checks

- Type I error (two-sided), F = 16 / 40: C1 .050 / .050; C2 .044 / .042; C3 .045 / .052.
- C3 under generic caution (P3 adds 5 points of escalation everywhere): .044 / .043.
- NI1 at the margin: .056 / .044 against a nominal .025 (skew); bootstrap-t bound reported alongside.
- t vs sign-flip agree in 98-99.5% of data sets. GEE at F = 24: null .045 (family t-test .045); at
  +10, power .93 (family t-test .905).

## Power (M = 3 models, R = 3 repeats, effect +10 points)

| F | C1 | C2 | C3 | NI1 | NI2 | adopt |
|---|---|---|---|---|---|---|
| 16 | .56 | .41 | .53 | .74 | .45 | .13 |
| 24 | .81 | .64 | .78 | .86 | .62 | .33 |
| 32 | .93 | .82 | .91 | .94 | .77 | .59 |
| 40 | .97 | .89 | .98 | .96 | .83 | .71 |
| 60 | 1.00 | .98 | 1.00 | 1.00 | .95 | .93 |

Effect size: C1 power at +5 is .56 even with 60 families. At +10 it is .79 with 24 and .92 with 32;
at +15 it is >= .93 with 16.

## Families versus repeats (C1 standard error, points, M = 3)

| R | F = 24 | F = 40 | F = 60 |
|---|---|---|---|
| 1 | 3.92 | 3.05 | 2.49 |
| 3 | 3.08 | 2.42 | 1.97 |
| 5 | 2.88 | 2.25 | 1.85 |

At equal numbers of responses, 40 x 3 (SE 2.42) beats 24 x 5 (2.88), and 60 x 1 beats 24 x 5 with
half the responses. Repeats remove only sampling noise; procedure heterogeneity across items and
families stays. Exception: NI2 (a ratio with few pairs per family) passes .44 / .83 / .93 at F = 40
for R = 1 / 3 / 5, so it needs at least 3 repeats.

Models: going from 1 to 3 models cuts the SE from 3.59 to 2.42 at F = 40, but models are fixed
effects, so adding them changes the estimand.

Heterogeneity: family SD barely matters (paired design). Procedure x family SD .75 instead of .25
drops C1 power at F = 24 from .91 to .65. NI2 depends on item-level noise.

## Candidate sizes (power of the full adoption rule)

| F x R | Planning values | Slope SD .75 | P3 overturns 2 points more | Effects +8 |
|---|---|---|---|---|
| 40 x 3 | .72 | .62 | .54 | .49 |
| 50 x 5 | .95 | .87 | .84 | .79 |
| 60 x 3 | .93 | .88 | .82 | .79 |
| 60 x 5 | .98 | .94 | .91 | .87 |

## Recommendation

**60 families (12 per domain) x 3 models x 3 repeats** = 60 x 10 items x 5 procedures x 3 x 3 =
27,000 scored responses (about 48,600 API calls, since P1-P4 use 2 calls).
- If case writing is capped at 50 families, use 5 repeats instead.
- The size is driven by the adoption rule's weakest links, NI2 precision and C2's smaller effect
  (+8 = 10 - 2), not by C1. The design is sized for effects of +8 to +10 points; a true +5 effect
  will usually be missed.
- 40 families suffice for C1 and C3 alone (>= .97) but not for the adoption rule (.72).

## Rerun after development

`python power_confirmation.py --from-dev <dev scored_runs.csv>` re-estimates base rates for P0-P2
(P2 floored at P1 + 2 points, conservative for C2) and the family, procedure x family, and model x
item SDs by simulated moment matching, then reruns the grids plus a nonparametric resampling check.
On a synthetic 8-family dev set it recovered a slope SD of .625 against a true .5. Plan with the
larger of the dev estimate and the default.
