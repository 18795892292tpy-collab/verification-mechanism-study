# Summary tables

Source: `results/dev_strong/scored_runs.csv`  
Rows: 800; families: 8; models: 1; repeats: 2; procedures: P0, P1, P2, P3, P4  
Estimates are family-weighted means (percentage points); 95% CIs are t-based on family-level values unless labelled bootstrap (family cluster bootstrap, B = 2000).

## 1. Primary contrasts (Holm, FWER .05, two-sided)

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) | p_holm |
|---|---|---|---|---|---|---|
| C1: P3 - P1 flawed_correction | 8 | -1.6 [-5.3, 2.1] | [-4.7, 0.0] | 0.3506 | 1.0000 | 1.0000 |
| C2: P3 - P2 flawed_correction | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 | 1.0000 |
| C3: [escalation P3-P1, absent] - [P3-P1, present] | 8 | -1.6 [-5.3, 2.1] | [-4.7, 0.0] | 0.3506 | 1.0000 | 1.0000 |

## 2. Non-inferiority (95% CI bound vs margin; decision rows use P0)

| contrast | role | estimate [95% CI] | margin | bound | bootstrap-t bound | passes |
|---|---|---|---|---|---|---|
| NI1: P3 - P0 aligned_overturn | decision | 3.1 [-1.7, 8.0] | 5.0 | 8.0 | 5.2 | False |
| NI2: P3 - P0 irrelevant_stability given base correct | decision | 0.0 [0.0, 0.0] | -5.0 | 0.0 |  | True |
| NI1: P3 - P1 aligned_overturn | reported | 0.0 [0.0, 0.0] | 5.0 | 0.0 |  | True |
| NI2: P3 - P1 irrelevant_stability given base correct | reported | 0.0 [0.0, 0.0] | -5.0 | 0.0 |  | True |

## 3. Pre-specified decision rule

- REVISE/DROP P3: non-inferiority not shown (NI1: P3 - P0 aligned_overturn). P3 is not adopted whatever C1 shows; report the harm estimate.

## 4. Outcomes by procedure (%, family-bootstrap 95% CI)

| outcome | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| flawed_correction | 96.9 [90.6, 100.0] | 100.0 [100.0, 100.0] | 98.4 [95.3, 100.0] | 98.4 [95.3, 100.0] | 98.4 [95.3, 100.0] |
| aligned_overturn | 1.6 [0.0, 4.7] | 4.7 [0.0, 10.9] | 4.7 [0.0, 10.9] | 4.7 [0.0, 10.9] | 1.6 [0.0, 4.7] |
| pause_appropriate | 93.8 [81.2, 100.0] | 90.6 [71.9, 100.0] | 87.5 [62.5, 100.0] | 90.6 [71.9, 100.0] | 90.6 [71.9, 100.0] |
| unnecessary_escalation | 1.6 [0.0, 4.7] | 1.6 [0.0, 3.9] | 3.1 [0.0, 7.8] | 3.1 [0.0, 7.8] | 1.6 [0.0, 4.7] |
| follow_flawed | 1.2 [0.0, 3.8] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| accuracy | 96.9 [93.1, 100.0] | 96.2 [92.5, 99.4] | 95.0 [90.0, 98.8] | 95.6 [91.2, 99.4] | 96.9 [92.5, 100.0] |
| citation | 92.5 [81.2, 100.0] | 94.4 [84.4, 100.0] | 95.6 [89.4, 100.0] | 96.2 [88.8, 100.0] | 93.1 [80.6, 100.0] |
| parse_failure | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| counterfactual_success | 90.6 [71.9, 100.0] | 90.6 [78.1, 100.0] | 93.8 [81.2, 100.0] | 87.5 [68.8, 100.0] | 93.8 [81.2, 100.0] |
| irrelevant_stability | 100.0 [100.0, 100.0] | 96.9 [90.6, 100.0] | 96.9 [90.6, 100.0] | 96.9 [90.6, 100.0] | 100.0 [100.0, 100.0] |
| irrelevant_stability_aligned | 100.0 [100.0, 100.0] | 93.8 [81.2, 100.0] | 93.8 [81.2, 100.0] | 93.8 [81.2, 100.0] | 100.0 [100.0, 100.0] |
| paraphrase_stability | 100.0 [100.0, 100.0] | 96.9 [90.6, 100.0] | 96.9 [90.6, 100.0] | 96.9 [90.6, 100.0] | 100.0 [100.0, 100.0] |
| irrelevant_flip | 0.0 [0.0, 0.0] | 3.1 [0.0, 9.4] | 3.1 [0.0, 9.4] | 3.1 [0.0, 9.4] | 0.0 [0.0, 0.0] |
| paraphrase_flip | 0.0 [0.0, 0.0] | 3.1 [0.0, 9.4] | 3.1 [0.0, 9.4] | 3.1 [0.0, 9.4] | 0.0 [0.0, 0.0] |
| irrelevant_stability_given_base_correct | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 96.9 [90.6, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |

## 5. By evidence x advice (%, bootstrap CI)

| evidence | advice | outcome | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|---|
| absent | aligned | correct | 100.0 [100.0, 100.0] | 93.8 [81.2, 100.0] | 87.5 [62.5, 100.0] | 93.8 [81.2, 100.0] | 93.8 [81.2, 100.0] |
| absent | aligned | escalated | 100.0 [100.0, 100.0] | 93.8 [81.2, 100.0] | 87.5 [62.5, 100.0] | 93.8 [81.2, 100.0] | 93.8 [81.2, 100.0] |
| absent | aligned | followed_advice | 100.0 [100.0, 100.0] | 93.8 [81.2, 100.0] | 87.5 [62.5, 100.0] | 93.8 [81.2, 100.0] | 93.8 [81.2, 100.0] |
| absent | flawed | correct | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] |
| absent | flawed | escalated | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] | 87.5 [62.5, 100.0] |
| absent | flawed | followed_advice | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| present | aligned | correct | 98.4 [95.3, 100.0] | 95.3 [89.1, 100.0] | 95.3 [89.1, 100.0] | 95.3 [89.1, 100.0] | 98.4 [95.3, 100.0] |
| present | aligned | escalated | 1.6 [0.0, 4.7] | 3.1 [0.0, 7.8] | 4.7 [0.0, 10.9] | 4.7 [0.0, 10.9] | 1.6 [0.0, 4.7] |
| present | aligned | followed_advice | 98.4 [95.3, 100.0] | 95.3 [89.1, 100.0] | 95.3 [89.1, 100.0] | 95.3 [89.1, 100.0] | 98.4 [95.3, 100.0] |
| present | flawed | correct | 96.9 [90.6, 100.0] | 100.0 [100.0, 100.0] | 98.4 [95.3, 100.0] | 98.4 [95.3, 100.0] | 98.4 [95.3, 100.0] |
| present | flawed | escalated | 1.6 [0.0, 4.7] | 0.0 [0.0, 0.0] | 1.6 [0.0, 4.7] | 1.6 [0.0, 4.7] | 1.6 [0.0, 4.7] |
| present | flawed | followed_advice | 1.6 [0.0, 4.7] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |

## 6. Accuracy by state x advice (%, point estimates; CIs in CSV)

| state | advice | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| base | aligned | 100.0 | 93.8 | 100.0 | 93.8 | 100.0 |
| base | flawed | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| decisive_change | aligned | 93.8 | 87.5 | 93.8 | 87.5 | 93.8 |
| decisive_change | flawed | 87.5 | 100.0 | 93.8 | 93.8 | 93.8 |
| irrelevant_change | aligned | 100.0 | 100.0 | 93.8 | 100.0 | 100.0 |
| irrelevant_change | flawed | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| missing | aligned | 100.0 | 93.8 | 87.5 | 93.8 | 93.8 |
| missing | flawed | 87.5 | 87.5 | 87.5 | 87.5 | 87.5 |
| paraphrase | aligned | 100.0 | 100.0 | 93.8 | 100.0 | 100.0 |
| paraphrase | flawed | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

## 7. Secondary / exploratory contrasts (unadjusted; P4 contrasts exploratory)

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) |
|---|---|---|---|---|---|
| E1: P3 - P4 flawed_correction (source checking vs cue naming) | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 |
| E2: P4 - P1 flawed_correction (cue naming vs free re-check) | 8 | -1.6 [-5.3, 2.1] | [-4.7, 0.0] | 0.3506 | 1.0000 |
| P3 - P0 flawed_correction | 8 | 1.6 [-2.1, 5.3] | [0.0, 4.7] | 0.3506 | 1.0000 |
| P2 - P1 flawed_correction | 8 | -1.6 [-5.3, 2.1] | [-4.7, 0.0] | 0.3506 | 1.0000 |
| P1 - P0 flawed_correction | 8 | 3.1 [-4.3, 10.5] | [0.0, 9.4] | 0.3506 | 1.0000 |
| C3 analogue with P4: [esc P3-P4, absent] - [P3-P4, present] | 8 | -1.6 [-4.0, 0.9] | [-3.9, 0.0] | 0.1705 | 0.5000 |
| advice x procedure: (P3-P1, flawed) - (P3-P1, aligned), correct | 8 | -1.6 [-5.3, 2.1] | [-4.7, 0.0] | 0.3506 | 1.0000 |
| P3 - P1 pause_appropriate | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 |
| P3 - P1 unnecessary_escalation | 8 | 1.6 [-2.1, 5.3] | [0.0, 4.7] | 0.3506 | 1.0000 |
| P3 - P1 counterfactual_success | 8 | -3.1 [-10.5, 4.3] | [-9.4, 0.0] | 0.3506 | 1.0000 |
| P3 - P1 paraphrase_stability | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 |
| P3 - P1 irrelevant_flip | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 |
| P3 - P1 citation | 8 | 1.9 [-1.2, 5.0] | [0.0, 4.4] | 0.1970 | 0.5000 |
| P3 - P1 follow_flawed | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 |
| P3 - P1 irrelevant_stability | 8 | 0.0 [0.0, 0.0] | [0.0, 0.0] | 1.0000 | 1.0000 |

## 8. Signal detection (hit = flawed-advice correction, false alarm = aligned overturn)

Per family x procedure with log-linear correction; c < 0 = more liberal overturning.

| measure | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| criterion_c | 0.02 [0.00, 0.07] | -0.10 [-0.24, 0.00] | -0.06 [-0.19, 0.00] | -0.06 [-0.15, 0.00] | 0.00 [0.00, 0.00] |
| d_prime | 2.98 [2.58, 3.19] | 2.98 [2.70, 3.19] | 2.90 [2.56, 3.19] | 2.90 [2.50, 3.19] | 3.03 [2.72, 3.19] |

| contrast | estimate [95% CI] | p (t) |
|---|---|---|
| d_prime: P3 - P1 | -0.08 [-0.26, 0.11] | 0.3506 |
| d_prime: P3 - P2 | -0.00 [-0.17, 0.17] | 1.0000 |
| d_prime: P3 - P4 | -0.13 [-0.33, 0.08] | 0.1853 |
| d_prime: P1 - P0 | -0.00 [-0.28, 0.28] | 1.0000 |
| criterion_c: P3 - P1 | 0.04 [-0.05, 0.13] | 0.3506 |
| criterion_c: P3 - P2 | 0.00 [-0.08, 0.08] | 1.0000 |
| criterion_c: P3 - P4 | -0.06 [-0.16, 0.04] | 0.1853 |
| criterion_c: P1 - P0 | -0.13 [-0.34, 0.09] | 0.2040 |

## 9. First-pass -> final changes vs resampling baseline (two independent P0 runs)

flip = action changed; w2r = wrong->right; r2w = right->wrong; net = w2r - r2w (%).

| subset | measure | P0pair | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| missing | flip | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| missing | net | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| missing | r2w | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| missing | w2r | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| present_aligned | flip | 3.1 | 1.6 | 1.6 | 0.0 | 0.0 |
| present_aligned | net | 0.0 | 0.0 | 1.6 | 0.0 | 0.0 |
| present_aligned | r2w | 1.6 | 0.0 | 0.0 | 0.0 | 0.0 |
| present_aligned | w2r | 1.6 | 0.0 | 1.6 | 0.0 | 0.0 |
| present_flawed | flip | 3.1 | 0.0 | 1.6 | 0.0 | 1.6 |
| present_flawed | net | 0.0 | 0.0 | -1.6 | 0.0 | 0.0 |
| present_flawed | r2w | 0.0 | 0.0 | 1.6 | 0.0 | 0.0 |
| present_flawed | w2r | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

| contrast | estimate [95% CI] | p (t) |
|---|---|---|
| missing flip: P1 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing flip: P2 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing flip: P3 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing flip: P4 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing net: P1 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing net: P2 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing net: P3 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| missing net: P4 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| present_aligned flip: P1 - P0pair | -1.6 [-5.3, 2.1] | 0.3506 |
| present_aligned flip: P2 - P0pair | -1.6 [-10.3, 7.2] | 0.6845 |
| present_aligned flip: P3 - P0pair | -3.1 [-10.5, 4.3] | 0.3506 |
| present_aligned flip: P4 - P0pair | -3.1 [-10.5, 4.3] | 0.3506 |
| present_aligned net: P1 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| present_aligned net: P2 - P0pair | 1.6 [-2.1, 5.3] | 0.3506 |
| present_aligned net: P3 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| present_aligned net: P4 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| present_flawed flip: P1 - P0pair | -3.1 [-10.5, 4.3] | 0.3506 |
| present_flawed flip: P2 - P0pair | -1.6 [-5.3, 2.1] | 0.3506 |
| present_flawed flip: P3 - P0pair | -3.1 [-10.5, 4.3] | 0.3506 |
| present_flawed flip: P4 - P0pair | -1.6 [-5.3, 2.1] | 0.3506 |
| present_flawed net: P1 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| present_flawed net: P2 - P0pair | -1.6 [-5.3, 2.1] | 0.3506 |
| present_flawed net: P3 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |
| present_flawed net: P4 - P0pair | 0.0 [0.0, 0.0] | 1.0000 |

Manipulation check - first-pass accuracy (all items): P1 96.2; P2 95.0; P3 95.6; P4 96.9; P0 final 96.9

## 10. Robustness

GEE (binomial, exchangeable within family, bias-reduced SE; adjusted for model):

| model | coef | se | p | n_rows | n_families |
|---|---|---|---|---|---|
| C1 P3-P1 flawed_correction (logOR) | -24.423 |  |  | 128 | 8 |
| C2 P3-P2 flawed_correction (logOR) | 0.0 |  |  | 128 | 8 |
| C3 P3xabsent escalation interaction (logOR) | -0.709 | 0.417 | 0.0892 | 320 | 8 |

Parse-failure rate by procedure (%): P0 0.00, P1 0.00, P2 0.00, P3 0.00, P4 0.00

## 11. Cost (means per response, family-bootstrap 95% CI)

| metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| input_tokens | 1,015.0 [954.9, 1,066.2] | 2,540.2 [2,416.7, 2,646.8] | 2,542.2 [2,410.8, 2,656.2] | 2,570.7 [2,437.1, 2,688.1] | 2,529.5 [2,399.6, 2,643.6] |
| latency_s | 3.2 [3.0, 3.4] | 11.7 [11.3, 12.2] | 9.7 [9.4, 10.1] | 11.2 [10.9, 11.6] | 11.7 [11.3, 12.2] |
| n_calls | 1.0 [1.0, 1.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] |
| output_tokens | 359.2 [324.8, 394.2] | 1,648.3 [1,557.8, 1,738.6] | 1,227.4 [1,170.3, 1,286.9] | 1,603.8 [1,535.9, 1,679.1] | 1,660.1 [1,576.8, 1,737.1] |
| total_tokens | 1,374.2 [1,302.8, 1,443.1] | 4,188.4 [4,013.2, 4,363.4] | 3,769.6 [3,605.2, 3,922.0] | 4,174.6 [3,988.9, 4,340.9] | 4,189.7 [3,984.9, 4,372.1] |

| metric | ratio | v |
|---|---|---|
| output_tokens | P1/P0 | 4.59 [4.25, 4.92] |
| output_tokens | P2/P0 | 3.42 [3.25, 3.62] |
| output_tokens | P3/P0 | 4.46 [4.22, 4.78] |
| output_tokens | P4/P0 | 4.62 [4.31, 4.99] |
| output_tokens | P0/P1 | 0.22 [0.20, 0.24] |
| output_tokens | P2/P1 | 0.74 [0.72, 0.77] |
| output_tokens | P3/P1 | 0.97 [0.93, 1.02] |
| output_tokens | P4/P1 | 1.01 [0.97, 1.05] |
| total_tokens | P1/P0 | 3.05 [2.99, 3.12] |
| total_tokens | P2/P0 | 2.74 [2.71, 2.78] |
| total_tokens | P3/P0 | 3.04 [3.00, 3.08] |
| total_tokens | P4/P0 | 3.05 [3.01, 3.09] |
| total_tokens | P0/P1 | 0.33 [0.32, 0.33] |
| total_tokens | P2/P1 | 0.90 [0.89, 0.91] |
| total_tokens | P3/P1 | 1.00 [0.98, 1.01] |
| total_tokens | P4/P1 | 1.00 [0.98, 1.02] |
| latency_s | P1/P0 | 3.62 [3.42, 3.81] |
| latency_s | P2/P0 | 3.01 [2.92, 3.12] |
| latency_s | P3/P0 | 3.49 [3.35, 3.67] |
| latency_s | P4/P0 | 3.64 [3.49, 3.81] |
| latency_s | P0/P1 | 0.28 [0.26, 0.29] |
| latency_s | P2/P1 | 0.83 [0.81, 0.86] |
| latency_s | P3/P1 | 0.96 [0.93, 1.00] |
| latency_s | P4/P1 | 1.01 [0.97, 1.04] |

Compute-match check (P3/P1 output tokens within (0.8, 1.25)): OK

| comparison | extra_tokens_per_response | extra_correct_per_flawed_item | tokens_per_extra_correction | boot_lo | boot_hi | share_boot_gain_positive |
|---|---|---|---|---|---|---|
| P3 vs P0 | 2800.362 | 0.016 | 179223.2 | 60186.96 | 184231.34 | 0.664 |
| P3 vs P1 | -13.894 | -0.016 |  |  |  | 0.0 |
