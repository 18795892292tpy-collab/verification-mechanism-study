# Phase 4 sample size: simulation re-justification

Drafted by the statistics line (AI-assisted), 2026-11-05; reviewed and saved by the main agent.
Script: `power_human.py` (about 1 minute; the MixedLM check takes about 9 minutes, and `--no-mixedlm`
reuses its saved result). Outputs: `power_out/power_human_tables.md`, `power_human_grid.csv`.
Phase 4 needs practising administrators and ethics approval; AI roles cannot stand in for participants.

## Why the v3 justification does not fit

v3 used a G*Power independent-samples t-test with d = .50, giving 64 per group (reproduced: 63.8).
- **Cases ignored.** It treats participant-level accuracy as the only source of error, but 12 cases are
  crossed with participants. If the effect of support varies by case, a participant-level t-test
  generalizes only to those 12 cases (Clark, 1973; Judd et al., 2012; Westfall et al., 2014).
- **H6 unpowered.** The under-reliance non-inferiority test was never powered.

## Design simulated

Arms balanced across lists; 12 cases per participant (6 aligned, 6 flawed advice, advice version
counterbalanced); case bank K = 12, or K = 24 (two sets of 12, four lists). Logit model with
correlated participant effects, case effects, and a case-by-treatment slope, calibrated to these
marginal rates:

| Parameter | Value | Source |
|---|---|---|
| Control flawed-advice accuracy | .40 | Assumption. Direction consistent with frequent acceptance of incorrect AI advice (Bansal et al., 2021; Buçinca et al., 2021); no number taken from these papers. |
| Effect of support | +7.5 / +10 / +12.5 / +15 points; smallest effect of interest +10 | Assumption. Forcing engagement reduces over-reliance (Buçinca et al., 2021), more so when verification is cheap (Vasconcelos et al., 2023); human-AI teams often fail to beat the better component (Vaccaro et al., 2024), so effects should be modest. Implied d = .31 / .42 / .53 / .64. |
| Control under-reliance | .10 | Assumption |
| Participant SD (logit) | .8 (sensitivity 1.2); correlation between flaw detection and following aligned advice -.3 | Assumption |
| Case SD | 1.0 / .8 | Assumption |
| Case-by-treatment SD | 0-.75 (default .5) | Assumption; Westfall et al. (2014) explain why it matters |
| Under-reliance NI margin | +5 (sensitivity +7.5) | Same net-benefit rule as the computational plan (k = 2; k = 3 gives 7.5) |

Analyses compared: (a) the v3 pooled t-test; (b) a case-aware test adding the estimated
case-by-treatment variance / K to the participant-level SE, with Satterthwaite df (the balanced-design
moment equivalent of a crossed mixed model with a by-case slope); (c) the NI test using the case-aware
upper 95% bound.

## Checks

- With case-by-treatment SD 0 the simulation reproduces analytic power (d = .527: .844 simulated vs
  .840 analytic).
- MixedLM with crossed variance components, t reference on 10 df (N = 128, K = 12, 100 simulations):
  Type I error .02 (case-aware test .03, v3 test .08); power at +10 .37 (case-aware .53, v3 .65).
  So the case-aware power figures are, if anything, optimistic.

## Type I error of the v3 t-test (generalizing over cases)

- Case-by-treatment SD .5, K = 12: .087 at N = 128, .142 at N = 256.
- SD .75: .156 and .228. With K = 24 the excess is roughly halved.
- The case-aware test stays at .04-.063.

## Case-aware power, +10 points, case-by-treatment SD .5

| N | 128 | 192 | 256 | 320 | 400 |
|---|---|---|---|---|---|
| K = 12 | .52 | .60 | .70 | .74 | .80 |
| K = 24 | .58 | .74 | .80 | .86 | .90 |

With K = 12 the number of cases caps power: at SD .75, power is .58 even with N = 400.

## N needed for 80% power (case-aware, SD .5)

| Effect | K = 12 | K = 24 |
|---|---|---|
| +7.5 | > 400 (.53) | > 400 (.73) |
| +10 | 400 | 256 |
| +12.5 (about v3's d = .5) | 192 | 128 (.81) |
| +15 | 128 (.86) | 96 (.83) |

## Under-reliance non-inferiority (true difference 0, K = 24)

Pass rate at N = 128 / 256 / 400: margin 5: .50 / .76 / .86; margin 7.5: .82 / .96 / .99.
Joint power (primary test and NI, +10): margin 5: .29 / .60 / .76; margin 7.5: .47 / .76 / .89.
A true +2-point increase in under-reliance, or a participant SD of 1.2, cuts joint power sharply.

## Verdict

N = 128 is not justified for the actual design. It works only if the true effect is about +12.5
points (d about .5), K = 24, and H6 is not treated as confirmatory.

## Recommendation

1. Use 24 cases (two sets of 12, four counterbalanced lists).
2. Primary analysis: a crossed mixed model (participant and case random effects, by-case treatment
   slope; Satterthwaite or Kenward-Roger df). Report the t-test descriptively only.
3. Analyse N = 256 (enrol about 285) to detect +10 with 80% power, using the under-reliance margin
   7.5 if the panel accepts k = 3 (joint power .76).
4. If recruitment is capped near 144, keep 128 analysed with K = 24, state that the study is powered
   for +12.5 only, and report H6 as an estimate with a CI.

## References

- Bansal, G., et al. (2021). Does the whole exceed its parts? The effect of AI explanations on
  complementary team performance. *CHI '21*. https://doi.org/10.1145/3411764.3445717
- Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). To trust or to think. *Proceedings of the ACM on
  Human-Computer Interaction, 5*(CSCW1). https://doi.org/10.1145/3449287
- Clark, H. H. (1973). The language-as-fixed-effect fallacy: A critique of language statistics in
  psychological research. *Journal of Verbal Learning and Verbal Behavior, 12*(4), 335-359.
  https://doi.org/10.1016/S0022-5371(73)80014-3
- Judd, C. M., Westfall, J., & Kenny, D. A. (2012). Treating stimuli as a random factor in social
  psychology. *Journal of Personality and Social Psychology, 103*(1), 54-69.
  https://doi.org/10.1037/a0028347
- Vaccaro, M., Almaatouq, A., & Malone, T. (2024). When combinations of humans and AI are useful.
  *Nature Human Behaviour, 8*(12), 2293-2303. https://doi.org/10.1038/s41562-024-02024-1
- Vasconcelos, H., et al. (2023). Explanations can reduce overreliance on AI systems during
  decision-making. *Proceedings of the ACM on Human-Computer Interaction, 7*(CSCW1).
  https://doi.org/10.1145/3579605
- Westfall, J., Kenny, D. A., & Judd, C. M. (2014). Statistical power and optimal design in
  experiments in which samples of participants respond to samples of stimuli. *Journal of
  Experimental Psychology: General, 143*(5), 2020-2045. https://doi.org/10.1037/xge0000014

(Clark 1973, Judd et al. 2012, Westfall et al. 2014 and Hautus 1995 verified against Crossref on
2026-11-05: authors, journal, volume, issue and pages match.)
