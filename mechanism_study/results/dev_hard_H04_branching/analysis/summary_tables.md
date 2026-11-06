# Summary tables

Source: `results/dev_hard_H04_branching/scored_runs.csv`  
Rows: 400; families: 1; models: 1; repeats: 8; procedures: P0, P1, P2, P3, P4  
Estimates are family-weighted means (percentage points); 95% CIs are t-based on family-level values unless labelled bootstrap (family cluster bootstrap, B = 2000).

## 1. Primary contrasts (Holm, FWER .05, two-sided)

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) | p_holm |
|---|---|---|---|---|---|---|
| C1: P3 - P1 flawed_correction | 1 |  [, ] | [, ] |  |  | nan |
| C2: P3 - P2 flawed_correction | 1 |  [, ] | [, ] |  |  | nan |
| C3: [escalation P3-P1, absent] - [P3-P1, present] | 1 |  [, ] | [, ] |  |  | nan |

## 2. Non-inferiority (95% CI bound vs margin; decision rows use P0)

| contrast | role | estimate [95% CI] | margin | bound | bootstrap-t bound | passes |
|---|---|---|---|---|---|---|
| NI1: P3 - P0 aligned_overturn | decision |  [, ] | 5.0 |  |  | False |
| NI2: P3 - P0 irrelevant_stability given base correct | decision |  [, ] | -5.0 |  |  | False |
| NI1: P3 - P1 aligned_overturn | reported |  [, ] | 5.0 |  |  | False |
| NI2: P3 - P1 irrelevant_stability given base correct | reported |  [, ] | -5.0 |  |  | False |

## 3. Pre-specified decision rule

- REVISE/DROP P3: non-inferiority not shown (NI1: P3 - P0 aligned_overturn, NI2: P3 - P0 irrelevant_stability given base correct). P3 is not adopted whatever C1 shows; report the harm estimate.

## 4. Outcomes by procedure (%, family-bootstrap 95% CI)

| outcome | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| flawed_correction | 81.2 [81.2, 81.2] | 90.6 [90.6, 90.6] | 84.4 [84.4, 84.4] | 84.4 [84.4, 84.4] | 84.4 [84.4, 84.4] |
| aligned_overturn | 12.5 [12.5, 12.5] | 6.2 [6.2, 6.2] | 12.5 [12.5, 12.5] | 12.5 [12.5, 12.5] | 6.2 [6.2, 6.2] |
| pause_appropriate | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| unnecessary_escalation | 15.6 [15.6, 15.6] | 7.8 [7.8, 7.8] | 14.1 [14.1, 14.1] | 14.1 [14.1, 14.1] | 10.9 [10.9, 10.9] |
| follow_flawed | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| accuracy | 87.5 [87.5, 87.5] | 93.8 [93.8, 93.8] | 88.8 [88.8, 88.8] | 88.8 [88.8, 88.8] | 91.2 [91.2, 91.2] |
| citation | 81.2 [81.2, 81.2] | 92.5 [92.5, 92.5] | 87.5 [87.5, 87.5] | 90.0 [90.0, 90.0] | 91.2 [91.2, 91.2] |
| parse_failure | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| counterfactual_success | 68.8 [68.8, 68.8] | 81.2 [81.2, 81.2] | 68.8 [68.8, 68.8] | 68.8 [68.8, 68.8] | 75.0 [75.0, 75.0] |
| irrelevant_stability | 43.8 [43.8, 43.8] | 75.0 [75.0, 75.0] | 43.8 [43.8, 43.8] | 43.8 [43.8, 43.8] | 56.2 [56.2, 56.2] |
| irrelevant_stability_aligned | 50.0 [50.0, 50.0] | 75.0 [75.0, 75.0] | 50.0 [50.0, 50.0] | 50.0 [50.0, 50.0] | 75.0 [75.0, 75.0] |
| paraphrase_stability | 62.5 [62.5, 62.5] | 75.0 [75.0, 75.0] | 68.8 [68.8, 68.8] | 68.8 [68.8, 68.8] | 75.0 [75.0, 75.0] |
| irrelevant_flip | 56.2 [56.2, 56.2] | 25.0 [25.0, 25.0] | 56.2 [56.2, 56.2] | 56.2 [56.2, 56.2] | 43.8 [43.8, 43.8] |
| paraphrase_flip | 37.5 [37.5, 37.5] | 25.0 [25.0, 25.0] | 31.2 [31.2, 31.2] | 31.2 [31.2, 31.2] | 25.0 [25.0, 25.0] |
| irrelevant_stability_given_base_correct | 63.6 [63.6, 63.6] | 92.3 [92.3, 92.3] | 63.6 [63.6, 63.6] | 63.6 [63.6, 63.6] | 75.0 [75.0, 75.0] |

## 5. By evidence x advice (%, bootstrap CI)

| evidence | advice | outcome | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|---|
| absent | aligned | correct | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| absent | aligned | escalated | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| absent | aligned | followed_advice | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| absent | flawed | correct | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| absent | flawed | escalated | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| absent | flawed | followed_advice | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| present | aligned | correct | 87.5 [87.5, 87.5] | 93.8 [93.8, 93.8] | 87.5 [87.5, 87.5] | 87.5 [87.5, 87.5] | 93.8 [93.8, 93.8] |
| present | aligned | escalated | 12.5 [12.5, 12.5] | 6.2 [6.2, 6.2] | 12.5 [12.5, 12.5] | 12.5 [12.5, 12.5] | 6.2 [6.2, 6.2] |
| present | aligned | followed_advice | 87.5 [87.5, 87.5] | 93.8 [93.8, 93.8] | 87.5 [87.5, 87.5] | 87.5 [87.5, 87.5] | 93.8 [93.8, 93.8] |
| present | flawed | correct | 81.2 [81.2, 81.2] | 90.6 [90.6, 90.6] | 84.4 [84.4, 84.4] | 84.4 [84.4, 84.4] | 84.4 [84.4, 84.4] |
| present | flawed | escalated | 18.8 [18.8, 18.8] | 9.4 [9.4, 9.4] | 15.6 [15.6, 15.6] | 15.6 [15.6, 15.6] | 15.6 [15.6, 15.6] |
| present | flawed | followed_advice | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |

## 6. Accuracy by state x advice (%, point estimates; CIs in CSV)

| state | advice | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| base | aligned | 62.5 | 75.0 | 62.5 | 62.5 | 75.0 |
| base | flawed | 75.0 | 87.5 | 75.0 | 75.0 | 75.0 |
| decisive_change | aligned | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| decisive_change | flawed | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| irrelevant_change | aligned | 87.5 | 100.0 | 87.5 | 87.5 | 100.0 |
| irrelevant_change | flawed | 62.5 | 87.5 | 62.5 | 62.5 | 62.5 |
| missing | aligned | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| missing | flawed | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| paraphrase | aligned | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| paraphrase | flawed | 87.5 | 87.5 | 100.0 | 100.0 | 100.0 |

## 7. Secondary / exploratory contrasts (unadjusted; P4 contrasts exploratory)

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) |
|---|---|---|---|---|---|
| E1: P3 - P4 flawed_correction (source checking vs cue naming) | 1 |  [, ] | [, ] |  |  |
| E2: P4 - P1 flawed_correction (cue naming vs free re-check) | 1 |  [, ] | [, ] |  |  |
| P3 - P0 flawed_correction | 1 |  [, ] | [, ] |  |  |
| P2 - P1 flawed_correction | 1 |  [, ] | [, ] |  |  |
| P1 - P0 flawed_correction | 1 |  [, ] | [, ] |  |  |
| C3 analogue with P4: [esc P3-P4, absent] - [P3-P4, present] | 1 |  [, ] | [, ] |  |  |
| advice x procedure: (P3-P1, flawed) - (P3-P1, aligned), correct | 1 |  [, ] | [, ] |  |  |
| P3 - P1 pause_appropriate | 1 |  [, ] | [, ] |  |  |
| P3 - P1 unnecessary_escalation | 1 |  [, ] | [, ] |  |  |
| P3 - P1 counterfactual_success | 1 |  [, ] | [, ] |  |  |
| P3 - P1 paraphrase_stability | 1 |  [, ] | [, ] |  |  |
| P3 - P1 irrelevant_flip | 1 |  [, ] | [, ] |  |  |
| P3 - P1 citation | 1 |  [, ] | [, ] |  |  |
| P3 - P1 follow_flawed | 1 |  [, ] | [, ] |  |  |
| P3 - P1 irrelevant_stability | 1 |  [, ] | [, ] |  |  |

## 8. Signal detection (hit = flawed-advice correction, false alarm = aligned overturn)

Per family x procedure with log-linear correction; c < 0 = more liberal overturning.

| measure | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| criterion_c | 0.12 [0.12, 0.12] | 0.09 [0.09, 0.09] | 0.06 [0.06, 0.06] | 0.06 [0.06, 0.06] | 0.23 [0.23, 0.23] |
| d_prime | 1.95 [1.95, 1.95] | 2.68 [2.68, 2.68] | 2.06 [2.06, 2.06] | 2.06 [2.06, 2.06] | 2.40 [2.40, 2.40] |

| contrast | estimate [95% CI] | p (t) |
|---|---|---|
| d_prime: P3 - P1 | nan [nan, nan] | nan |
| d_prime: P3 - P2 | nan [nan, nan] | nan |
| d_prime: P3 - P4 | nan [nan, nan] | nan |
| d_prime: P1 - P0 | nan [nan, nan] | nan |
| criterion_c: P3 - P1 | nan [nan, nan] | nan |
| criterion_c: P3 - P2 | nan [nan, nan] | nan |
| criterion_c: P3 - P4 | nan [nan, nan] | nan |
| criterion_c: P1 - P0 | nan [nan, nan] | nan |

## 9. First-pass -> final changes vs resampling baseline (two independent P0 runs)

flip = action changed; w2r = wrong->right; r2w = right->wrong; net = w2r - r2w (%).

| subset | measure | P0pair | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| missing | flip | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| missing | net | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| missing | r2w | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| missing | w2r | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| present_aligned | flip | 19.6 | 6.2 | 0.0 | 0.0 | 6.2 |
| present_aligned | net | 0.0 | 6.2 | 0.0 | 0.0 | 6.2 |
| present_aligned | r2w | 9.8 | 0.0 | 0.0 | 0.0 | 0.0 |
| present_aligned | w2r | 9.8 | 6.2 | 0.0 | 0.0 | 6.2 |
| present_flawed | flip | 30.4 | 9.4 | 3.1 | 3.1 | 3.1 |
| present_flawed | net | 0.0 | 9.4 | 3.1 | 3.1 | 3.1 |
| present_flawed | r2w | 15.2 | 0.0 | 0.0 | 0.0 | 0.0 |
| present_flawed | w2r | 15.2 | 9.4 | 3.1 | 3.1 | 3.1 |

| contrast | estimate [95% CI] | p (t) |
|---|---|---|
| missing flip: P1 - P0pair |  [, ] | nan |
| missing flip: P2 - P0pair |  [, ] | nan |
| missing flip: P3 - P0pair |  [, ] | nan |
| missing flip: P4 - P0pair |  [, ] | nan |
| missing net: P1 - P0pair |  [, ] | nan |
| missing net: P2 - P0pair |  [, ] | nan |
| missing net: P3 - P0pair |  [, ] | nan |
| missing net: P4 - P0pair |  [, ] | nan |
| present_aligned flip: P1 - P0pair |  [, ] | nan |
| present_aligned flip: P2 - P0pair |  [, ] | nan |
| present_aligned flip: P3 - P0pair |  [, ] | nan |
| present_aligned flip: P4 - P0pair |  [, ] | nan |
| present_aligned net: P1 - P0pair |  [, ] | nan |
| present_aligned net: P2 - P0pair |  [, ] | nan |
| present_aligned net: P3 - P0pair |  [, ] | nan |
| present_aligned net: P4 - P0pair |  [, ] | nan |
| present_flawed flip: P1 - P0pair |  [, ] | nan |
| present_flawed flip: P2 - P0pair |  [, ] | nan |
| present_flawed flip: P3 - P0pair |  [, ] | nan |
| present_flawed flip: P4 - P0pair |  [, ] | nan |
| present_flawed net: P1 - P0pair |  [, ] | nan |
| present_flawed net: P2 - P0pair |  [, ] | nan |
| present_flawed net: P3 - P0pair |  [, ] | nan |
| present_flawed net: P4 - P0pair |  [, ] | nan |

Manipulation check - first-pass accuracy (all items): P1 87.5; P2 87.5; P3 87.5; P4 87.5; P0 final 87.5

## 10. Robustness

GEE (binomial, exchangeable within family, bias-reduced SE; adjusted for model):

| model | coef | se | p | n_rows | n_families |
|---|---|---|---|---|---|
| C1 P3-P1 flawed_correction (logOR) | -0.582 | 0.006 | 0.0 | 64 | 1 |
| C2 P3-P2 flawed_correction (logOR) | -0.0 | 0.902 | 1.0 | 64 | 1 |
| C3 P3xabsent escalation interaction (logOR) | -0.658 | 39944041.544 | 1.0 | 160 | 1 |

Parse-failure rate by procedure (%): P0 0.00, P1 0.00, P2 0.00, P3 0.00, P4 0.00

## 11. Cost (means per response, family-bootstrap 95% CI)

| metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| input_tokens | 1,740.9 [1,740.9, 1,740.9] | 4,014.6 [4,014.6, 4,014.6] | 4,018.6 [4,018.6, 4,018.6] | 4,041.6 [4,041.6, 4,041.6] | 4,009.6 [4,009.6, 4,009.6] |
| latency_s | 3.6 [3.6, 3.6] | 13.0 [13.0, 13.0] | 11.3 [11.3, 11.3] | 12.9 [12.9, 12.9] | 12.9 [12.9, 12.9] |
| n_calls | 1.0 [1.0, 1.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] |
| output_tokens | 392.8 [392.8, 392.8] | 1,812.2 [1,812.2, 1,812.2] | 1,445.6 [1,445.6, 1,445.6] | 1,921.3 [1,921.3, 1,921.3] | 1,804.7 [1,804.7, 1,804.7] |
| total_tokens | 2,133.7 [2,133.7, 2,133.7] | 5,826.9 [5,826.9, 5,826.9] | 5,464.2 [5,464.2, 5,464.2] | 5,962.9 [5,962.9, 5,962.9] | 5,814.4 [5,814.4, 5,814.4] |

| metric | ratio | v |
|---|---|---|
| output_tokens | P1/P0 | 4.61 [4.61, 4.61] |
| output_tokens | P2/P0 | 3.68 [3.68, 3.68] |
| output_tokens | P3/P0 | 4.89 [4.89, 4.89] |
| output_tokens | P4/P0 | 4.59 [4.59, 4.59] |
| output_tokens | P0/P1 | 0.22 [0.22, 0.22] |
| output_tokens | P2/P1 | 0.80 [0.80, 0.80] |
| output_tokens | P3/P1 | 1.06 [1.06, 1.06] |
| output_tokens | P4/P1 | 1.00 [1.00, 1.00] |
| total_tokens | P1/P0 | 2.73 [2.73, 2.73] |
| total_tokens | P2/P0 | 2.56 [2.56, 2.56] |
| total_tokens | P3/P0 | 2.79 [2.79, 2.79] |
| total_tokens | P4/P0 | 2.72 [2.72, 2.72] |
| total_tokens | P0/P1 | 0.37 [0.37, 0.37] |
| total_tokens | P2/P1 | 0.94 [0.94, 0.94] |
| total_tokens | P3/P1 | 1.02 [1.02, 1.02] |
| total_tokens | P4/P1 | 1.00 [1.00, 1.00] |
| latency_s | P1/P0 | 3.60 [3.60, 3.60] |
| latency_s | P2/P0 | 3.11 [3.11, 3.11] |
| latency_s | P3/P0 | 3.55 [3.55, 3.55] |
| latency_s | P4/P0 | 3.57 [3.57, 3.57] |
| latency_s | P0/P1 | 0.28 [0.28, 0.28] |
| latency_s | P2/P1 | 0.86 [0.86, 0.86] |
| latency_s | P3/P1 | 0.99 [0.99, 0.99] |
| latency_s | P4/P1 | 0.99 [0.99, 0.99] |

Compute-match check (P3/P1 output tokens within (0.8, 1.25)): OK

| comparison | extra_tokens_per_response | extra_correct_per_flawed_item | tokens_per_extra_correction | boot_lo | boot_hi | share_boot_gain_positive |
|---|---|---|---|---|---|---|
| P3 vs P0 | 3829.188 | 0.031 | 122534.0 | 122534.0 | 122534.0 | 1.0 |
| P3 vs P1 | 136.038 | -0.062 |  |  |  | 0.0 |
