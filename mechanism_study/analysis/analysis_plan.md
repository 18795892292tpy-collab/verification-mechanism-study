# Analysis plan: mechanism study (computational experiment)

Drafted by the statistics line (AI-assisted), 2026-11-05; reviewed and saved by the main agent.
Implemented in `analyze.py`. Freeze this plan with the confirmation set, before any confirmation responses.

**Question.** Does the benefit of source verification come from checking decisive evidence, or only
from extra computation?

## 0. Design

Procedures (P1-P4 each use 2 calls and the same output cap):
- P0: strong baseline (1 call).
- P1: free re-check.
- P2: generic checklist re-check.
- P3: source-applicability verification re-check.
- P4 (exploratory): P1 plus one sentence naming the three mismatch types, with no instruction to check sources.

Items: 5 states x 2 advice versions = 10 per family. Every item runs under every procedure, with r
repeats per model and m models.

**Branching design (added after development round 2).** For each item x repeat x model the harness
makes one first call; its answer is the P0 response, and P1-P4 each review that same first answer
(`runner.py --branching`). Procedure contrasts are then paired at the level of the first answer, and
two additional estimands are reported for every two-call procedure: the repair rate (share of
incorrect first answers made correct) and the damage rate (share of correct first answers made
incorrect). In development round 2, independent first calls made source verification look best on
H04 purely through first-pass luck (first-pass accuracy 12/16 to 15/16 under an identical prompt);
the branching run removed that artefact. `analyze.py` runs unchanged on branching data; its
first-pass "manipulation check" becomes an identity (all first passes equal P0) rather than a test.
`power_confirmation.py` assumes independent first calls, so its power figures are conservative for
the branching design.

## 1. Estimands

- **Population:** case families written and keyed by the Delphi-validated process. Models are the m
  frozen versions, a fixed factor; no generalization beyond them.
- **Summary measure:** family-averaged marginal risk difference, in percentage points. Each outcome is
  averaged within family x procedure x model over items and repeats, then over models with equal
  weights, giving y(f,p). The estimand is E_f[y(f,a) - y(f,b)].
- **Outcomes:** flawed_correction, aligned_overturn, pause_appropriate, unnecessary_escalation,
  counterfactual_success, irrelevant_stability, paraphrase_stability, cost.
- **NI2 outcome:** irrelevant-change stability given a correct base = sum(irrelevant_stability) /
  sum(correct(base)), within each family, pooled over advice.

## 2. Unit of analysis: the family

- **Repeats** re-sample the same prompt and model; they estimate one item's probability, not new
  cases. (In the planning model two repeats agree on correctness .75 of the time on flawed items and
  .93 on aligned items.)
- **The two calls of P1-P4** are one decision (first_action is kept for transition analysis).
- **The 10 items of a family share content**; base, irrelevant change and paraphrase are near-duplicates.
- **Procedures share items**, which pairing exploits.
- **Models** are few and chosen, so they are fixed effects.
- **Consequence:** inference uses n = F families. Rows are not independent; model calls are never
  counted as independent cases.

## 3. Primary contrasts (Holm, family-wise error .05, two-sided)

| | Contrast | Expected | Isolates |
|---|---|---|---|
| C1 | P3 - P1, flawed_correction, evidence present | > 0 | verification content vs one extra round at matched compute |
| C2 | P3 - P2, same outcome | > 0 | source-specific vs generic checking |
| C3 | escalation [P3 - P1, evidence absent] - [P3 - P1, evidence present] | > 0 | selective escalation vs generic caution |

**Test.** One-sample t-test on the family differences d_f (df = F - 1), with a t-based 95% CI.

**Robustness checks:** sign-flip permutation (exact when F <= 16); family-cluster bootstrap
(B = 2000); GEE (binomial, exchangeable, bias-reduced SE, adjusted for model). A Holm decision counts
as robust only if the sign-flip test agrees. In simulation, t and sign-flip agree in 98-99.5% of data
sets, and null rejection rates are .036-.050 for all three methods.

**Change from v3:** the primary analysis moves from a GLMM to the paired family-level test, which
keeps error control near nominal with 40-60 clusters. GEE gives the odds-ratio view.

## 4. Mechanism test

- **Hypothesis:** with evidence present, P3 gains mainly on flawed advice; with evidence missing, it
  mainly raises appropriate escalation.
- **Rival (generic caution):** escalation rises by the same amount with and without evidence, so C3 = 0.
- **Support also requires:** the advice x procedure interaction on correctness,
  (P3 - P1, flawed) - (P3 - P1, aligned) > 0, and P3 - P1 on unnecessary escalation near 0.

## 5. Non-inferiority (adoption safety gate, compared with P0)

| | Outcome | Pass if |
|---|---|---|
| NI1 | aligned_overturn, P3 - P0 | upper 95% bound < +5 points |
| NI2 | stability given correct base, P3 - P0 | lower 95% bound > -5 points |

Intersection-union: each tested at one-sided .025 with no further adjustment. P3 - P1 also reported.

**Margin rationale.** P3 is worth using only if k * pi * g > (1 - pi) * Delta, where pi = .2 is the
share of flawed advice in routine practice (assumption), k = 2 is the harm ratio (following flawed
advice - a procurement or data-protection breach, an outdated rule - is at least twice as costly as
overturning sound advice, which usually costs a delay and a re-check; assumption), and g = 10 points
is the smallest effect of interest. So Delta_max = 2 x .2 x .10 / .8 = 5 points. NI2 uses the same
rule: an answer that flips on an immaterial change is an error and breaks "like cases alike". The
Delphi panel ratifies the margins before the freeze. With k = 1 the margin is 2.5 points, needing
about 4x the families.

**Why NI2 is conditional on a correct base.** Plain stability (correct base AND same action) is
inflated by P3's correction of flawed base items (+7 points in simulation with no change in
invariance). Aligned-only stability has one pair per family and model, which is too noisy. The
conditional version still detects a real 5-point irrelevant-change penalty (pass rate .08) and is
conservative for P3.

**Error control.** Family differences in rare-event outcomes are right-skewed, so the simulated
actual alpha at the margin is .04-.06. A bootstrap-t bound is reported alongside; an NI claim is
robust only if both bounds pass.

**Smallest effect of interest (C1, C2):** +10 points, the minimum gain that justifies building the
Phase 4 panel around source applicability. Below +5 points the gain is negligible.

## 6. Parse failures and missing data

- parse_ok = 0 counts as a failed decision (not correct, not escalated, not following advice, no
  citation). No re-prompting, which would break compute matching.
- Sensitivity: rerun excluding parse failures. If P3 and P1 parse-failure rates differ by more than
  2 points, or any decision changes, flag the result as not robust to parsing.
- API errors: retried with identical settings; remaining missing rows treated as missing at random
  within family x procedure x model.
- If a family loses more than 20% of rows in any procedure, add a sensitivity analysis excluding it.
- A pair outcome is undefined if either member is missing.
- Scorer fixes are applied by rescoring all procedures blind to procedure. Families are never
  replaced after the freeze.

## 7. Secondary and exploratory analyses (unadjusted, labelled)

- Descriptive results by procedure, by evidence x advice, and by state x advice, with family-bootstrap
  CIs: escalation outcomes, counterfactual success, following flawed advice, stability and flips,
  citation completeness, parse failures.
- Contrasts: P3 - P0, P2 - P1, P1 - P0 on flawed_correction; the advice x procedure interaction; C1
  within each model; results by domain and mismatch type.
- **P4 cue control:** E1 = P3 - P4 and E2 = P4 - P1 on flawed_correction, plus a C3 analogue against
  P4. If E1 is near 0 (CI excludes +5), P3's gain is attributed to naming the error types, not to
  checking sources.
- **Signal detection:** hit = flawed-advice correction; false alarm = aligned overturn. d' and c per
  family x procedure with the log-linear correction (Hautus, 1995). Contrasts P3 - P1, P3 - P2,
  P3 - P4, P1 - P0. Verification should raise d'; a shift in c alone means generic distrust.
- **Revision vs resampling:** for P1-P4, first-pass -> final flips (wrong->right, right->wrong, net)
  by present-flawed, present-aligned and missing, against all ordered pairs of P0 repeats for the
  same model x item (net = 0, flips are noise). Manipulation check: first-pass accuracy equal across
  P1-P4 and close to P0.

## 8. Cost

- By procedure: input, output and total tokens, latency, number of calls, with ratios to P0 and P1
  and family-bootstrap CIs.
- Compute-match check: output tokens for P2, P3 and P4 relative to P1 must fall within [0.80, 1.25];
  otherwise C1 is reported as "verification plus extra tokens".
- Incremental cost: tokens per additional flawed-advice correction, P3 vs P1 and P3 vs P0.

## 9. Decision rules (fixed before data)

1. NI1 or NI2 not shown: revise or drop P3.
2. C1 and C2 both Holm-significant: adopt P3.
3. C1 significant, C2 not, and C2's upper bound below +5: simplify to P2.
4. C1 significant, C2 inconclusive: adopt P3 provisionally, without claiming source-specificity.
5. C1 not significant and its upper bound below +5: drop P3 as a mechanism; the benefit is extra computation.
6. Otherwise: inconclusive, with no unplanned extension of the confirmation set.
7. Qualifiers to rules 2-4: claim the escalation mechanism only if C3 is significant; E1 near 0
   weakens the source-checking reading; apply the compute-match caveat if the section 8 check fails.

**Precondition (added after the development smoke test).** None of these rules can be applied if P0
is at ceiling on flawed-advice, evidence-present items. Report P0's flawed_correction rate first; if
its family-bootstrap upper bound is >= 0.95, the confirmation result is "not testable at this
difficulty", not "no effect".

## 10. Freeze

Families, prompts, models, settings, scorer, this plan, and the ratified margins are frozen before
the confirmation run. Development data (about 8 families) are used only for harness checks, difficulty
tuning, and `power_confirmation.py --from-dev`. Deviations are reported.

## References for methods named here

- Hautus, M. J. (1995). Corrections for extreme proportions and their biasing effects on estimated
  values of d'. *Behavior Research Methods, Instruments, & Computers, 27*(1), 46-51.
  https://doi.org/10.3758/BF03203619
- Stanislaw, H., & Todorov, N. (1999). Calculation of signal detection theory measures. *Behavior
  Research Methods, Instruments, & Computers, 31*(1), 137-149. https://doi.org/10.3758/BF03207704
