# Summary tables

Source: `synthetic/scored_runs.csv`  
Rows: 18000; families: 40; models: 3; repeats: 3; procedures: P0, P1, P2, P3, P4  
Estimates are family-weighted means (percentage points); 95% CIs are t-based on family-level values unless labelled bootstrap (family cluster bootstrap, B = 2000).

## 1. Primary contrasts (Holm, FWER .05, two-sided)

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) | p_holm |
|---|---|---|---|---|---|---|
| C1: P3 - P1 flawed_correction | 40 | 15.6 [11.4, 19.7] | [11.8, 19.6] | 0.0000 | 0.0000 | 0.0000 |
| C2: P3 - P2 flawed_correction | 40 | 10.6 [6.9, 14.3] | [7.2, 14.2] | 0.0000 | 0.0000 | 0.0000 |
| C3: [escalation P3-P1, absent] - [P3-P1, present] | 40 | 10.5 [5.3, 15.7] | [5.7, 15.3] | 0.0002 | 0.0003 | 0.0002 |

## 2. Non-inferiority (95% CI bound vs margin; decision rows use P0)

| contrast | role | estimate [95% CI] | margin | bound | bootstrap-t bound | passes |
|---|---|---|---|---|---|---|
| NI1: P3 - P0 aligned_overturn | decision | 0.4 [-1.7, 2.5] | 5.0 | 2.5 | 2.4 | True |
| NI2: P3 - P0 irrelevant_stability given base correct | decision | 0.0 [-4.2, 4.3] | -5.0 | -4.2 | -4.5 | True |
| NI1: P3 - P1 aligned_overturn | reported | -1.4 [-3.7, 0.9] | 5.0 | 0.9 | 0.5 | True |
| NI2: P3 - P1 irrelevant_stability given base correct | reported | -0.1 [-4.1, 3.9] | -5.0 | -4.1 | -4.0 | True |

## 3. Pre-specified decision rule

- ADOPT P3: source-applicability verification beats both a matched free re-check (C1) and a matched generic checklist (C2), with non-inferiority on aligned advice and irrelevant-change stability.
- Mechanism supported: P3 raises escalation selectively when decisive evidence is absent (C3).

## 4. Outcomes by procedure (%, family-bootstrap 95% CI)

| outcome | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| flawed_correction | 45.4 [39.4, 51.2] | 49.9 [42.8, 57.0] | 54.8 [47.8, 62.2] | 65.4 [59.0, 71.8] | 57.1 [49.9, 64.2] |
| aligned_overturn | 4.9 [3.3, 6.5] | 6.7 [4.4, 9.4] | 4.9 [3.3, 6.7] | 5.3 [3.5, 7.4] | 6.2 [4.1, 8.6] |
| pause_appropriate | 43.5 [39.0, 47.6] | 47.5 [42.1, 53.1] | 47.6 [41.7, 53.5] | 57.4 [51.4, 63.2] | 47.4 [41.4, 53.6] |
| unnecessary_escalation | 2.1 [1.3, 3.0] | 2.4 [1.4, 3.5] | 2.3 [1.5, 3.2] | 1.7 [1.1, 2.3] | 2.2 [1.4, 3.1] |
| follow_flawed | 44.3 [40.1, 48.6] | 41.9 [37.1, 46.7] | 38.8 [33.6, 43.9] | 27.5 [23.3, 32.1] | 36.8 [31.9, 41.7] |
| accuracy | 64.9 [62.2, 67.7] | 66.8 [63.3, 70.3] | 69.5 [66.2, 72.8] | 75.5 [72.5, 78.6] | 69.8 [66.2, 73.6] |
| citation | 47.2 [45.3, 49.1] | 49.7 [48.0, 51.5] | 57.3 [55.6, 59.1] | 71.7 [69.8, 73.6] | 51.1 [49.5, 52.8] |
| parse_failure | 1.4 [1.0, 1.8] | 0.7 [0.4, 1.1] | 1.2 [0.8, 1.6] | 1.8 [1.4, 2.2] | 0.6 [0.4, 0.9] |
| counterfactual_success | 54.9 [51.2, 58.6] | 55.0 [49.7, 60.4] | 60.7 [55.8, 65.6] | 68.5 [63.9, 72.6] | 61.0 [56.4, 65.4] |
| irrelevant_stability | 60.1 [55.8, 64.4] | 63.6 [57.6, 69.4] | 67.2 [62.1, 72.4] | 72.4 [66.8, 77.8] | 67.2 [61.4, 73.1] |
| irrelevant_stability_aligned | 91.7 [88.3, 94.7] | 89.7 [85.6, 93.6] | 91.4 [87.5, 94.7] | 90.6 [86.4, 94.2] | 88.6 [83.9, 92.8] |
| paraphrase_stability | 58.9 [54.4, 63.5] | 61.3 [55.1, 67.2] | 66.2 [61.1, 71.3] | 71.9 [66.9, 76.9] | 66.4 [60.6, 72.4] |
| irrelevant_flip | 26.2 [22.6, 30.0] | 24.7 [20.8, 28.9] | 20.3 [17.0, 23.9] | 20.3 [16.2, 24.8] | 23.1 [19.2, 27.3] |
| paraphrase_flip | 26.0 [21.9, 30.6] | 26.1 [21.9, 30.6] | 21.5 [18.4, 24.8] | 19.8 [15.8, 23.7] | 23.5 [19.3, 28.1] |
| irrelevant_stability_given_base_correct | 87.6 [84.8, 90.5] | 87.7 [84.3, 91.1] | 87.6 [84.2, 90.7] | 87.6 [84.0, 91.0] | 87.4 [84.2, 90.3] |

## 5. By evidence x advice (%, bootstrap CI)

| evidence | advice | outcome | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|---|
| absent | aligned | correct | 65.8 [57.8, 73.3] | 65.0 [57.2, 72.2] | 66.4 [58.1, 73.9] | 75.6 [67.2, 83.1] | 67.5 [59.7, 74.7] |
| absent | aligned | escalated | 65.8 [57.8, 73.3] | 65.0 [57.2, 72.2] | 66.4 [58.1, 73.9] | 75.6 [67.2, 83.1] | 67.5 [59.7, 74.7] |
| absent | aligned | followed_advice | 65.8 [57.8, 73.3] | 65.0 [57.2, 72.2] | 66.4 [58.1, 73.9] | 75.6 [67.2, 83.1] | 67.5 [59.7, 74.7] |
| absent | flawed | correct | 21.1 [15.0, 26.9] | 30.0 [22.5, 38.1] | 28.9 [21.4, 36.4] | 39.2 [30.8, 47.2] | 27.2 [19.2, 35.8] |
| absent | flawed | escalated | 21.1 [15.0, 26.9] | 30.0 [22.5, 38.1] | 28.9 [21.4, 36.4] | 39.2 [30.8, 47.2] | 27.2 [19.2, 35.8] |
| absent | flawed | followed_advice | 62.8 [56.9, 68.6] | 54.7 [47.5, 61.7] | 56.4 [49.7, 63.1] | 41.4 [34.7, 48.1] | 58.1 [50.0, 65.6] |
| present | aligned | correct | 95.1 [93.5, 96.7] | 93.3 [90.6, 95.6] | 95.1 [93.3, 96.7] | 94.7 [92.6, 96.5] | 93.8 [91.4, 95.9] |
| present | aligned | escalated | 1.2 [0.6, 2.1] | 2.3 [1.1, 3.7] | 2.2 [1.2, 3.3] | 1.7 [0.9, 2.6] | 2.6 [1.5, 3.8] |
| present | aligned | followed_advice | 95.1 [93.5, 96.7] | 93.3 [90.6, 95.6] | 95.1 [93.3, 96.7] | 94.7 [92.6, 96.5] | 93.8 [91.4, 95.9] |
| present | flawed | correct | 45.4 [39.4, 51.2] | 49.9 [42.8, 57.0] | 54.8 [47.8, 62.2] | 65.4 [59.0, 71.8] | 57.1 [49.9, 64.2] |
| present | flawed | escalated | 3.0 [1.7, 4.5] | 2.4 [1.0, 4.4] | 2.4 [1.0, 4.0] | 1.8 [1.0, 2.8] | 1.7 [1.0, 2.7] |
| present | flawed | followed_advice | 39.7 [34.9, 44.6] | 38.7 [33.1, 44.1] | 34.4 [27.9, 40.6] | 24.0 [19.2, 29.4] | 31.5 [25.6, 37.6] |

## 6. Accuracy by state x advice (%, point estimates; CIs in CSV)

| state | advice | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| base | aligned | 95.8 | 92.8 | 95.3 | 96.1 | 93.1 |
| base | flawed | 41.7 | 51.7 | 57.5 | 68.1 | 59.4 |
| decisive_change | aligned | 95.3 | 94.4 | 93.3 | 96.4 | 96.4 |
| decisive_change | flawed | 46.7 | 46.4 | 53.9 | 61.7 | 51.4 |
| irrelevant_change | aligned | 95.3 | 94.7 | 96.1 | 93.1 | 93.3 |
| irrelevant_change | flawed | 49.4 | 51.9 | 55.0 | 66.9 | 60.8 |
| missing | aligned | 65.8 | 65.0 | 66.4 | 75.6 | 67.5 |
| missing | flawed | 21.1 | 30.0 | 28.9 | 39.2 | 27.2 |
| paraphrase | aligned | 94.2 | 91.4 | 95.6 | 93.3 | 92.5 |
| paraphrase | flawed | 43.9 | 49.4 | 52.8 | 65.0 | 56.7 |

## 7. Secondary / exploratory contrasts (unadjusted; P4 contrasts exploratory)

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) |
|---|---|---|---|---|---|
| E1: P3 - P4 flawed_correction (source checking vs cue naming) | 40 | 8.3 [4.6, 12.1] | [4.9, 11.9] | 0.0001 | 0.0001 |
| E2: P4 - P1 flawed_correction (cue naming vs free re-check) | 40 | 7.2 [2.9, 11.5] | [3.1, 11.2] | 0.0016 | 0.0019 |
| P3 - P0 flawed_correction | 40 | 20.0 [16.1, 23.9] | [16.4, 23.5] | 0.0000 | 0.0000 |
| P2 - P1 flawed_correction | 40 | 4.9 [0.8, 9.1] | [0.8, 8.9] | 0.0220 | 0.0256 |
| P1 - P0 flawed_correction | 40 | 4.4 [0.1, 8.8] | [0.1, 8.6] | 0.0473 | 0.0532 |
| C3 analogue with P4: [esc P3-P4, absent] - [P3-P4, present] | 40 | 10.4 [5.1, 15.7] | [5.3, 15.3] | 0.0003 | 0.0002 |
| advice x procedure: (P3-P1, flawed) - (P3-P1, aligned), correct | 40 | 14.2 [9.9, 18.4] | [10.1, 18.3] | 0.0000 | 0.0000 |
| P3 - P1 pause_appropriate | 40 | 9.9 [4.5, 15.2] | [4.9, 14.9] | 0.0006 | 0.0008 |
| P3 - P1 unnecessary_escalation | 40 | -0.6 [-1.5, 0.3] | [-1.5, 0.1] | 0.1625 | 0.1901 |
| P3 - P1 counterfactual_success | 40 | 13.5 [9.0, 17.9] | [9.3, 17.8] | 0.0000 | 0.0000 |
| P3 - P1 paraphrase_stability | 40 | 10.7 [6.2, 15.2] | [6.7, 15.3] | 0.0000 | 0.0001 |
| P3 - P1 irrelevant_flip | 40 | -4.4 [-8.7, -0.2] | [-8.7, -0.3] | 0.0401 | 0.0396 |
| P3 - P1 citation | 40 | 22.0 [19.6, 24.4] | [19.7, 24.3] | 0.0000 | 0.0000 |
| P3 - P1 follow_flawed | 40 | -14.4 [-18.1, -10.7] | [-18.1, -10.9] | 0.0000 | 0.0000 |
| P3 - P1 irrelevant_stability | 40 | 8.8 [4.3, 13.2] | [4.4, 13.1] | 0.0003 | 0.0003 |

## 8. Signal detection (hit = flawed-advice correction, false alarm = aligned overturn)

Per family x procedure with log-linear correction; c < 0 = more liberal overturning.

| measure | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| criterion_c | 0.90 [0.81, 1.00] | 0.80 [0.70, 0.89] | 0.77 [0.66, 0.89] | 0.61 [0.50, 0.71] | 0.71 [0.59, 0.82] |
| d_prime | 1.52 [1.28, 1.75] | 1.58 [1.26, 1.86] | 1.80 [1.54, 2.05] | 2.09 [1.85, 2.31] | 1.81 [1.52, 2.10] |

| contrast | estimate [95% CI] | p (t) |
|---|---|---|
| d_prime: P3 - P1 | 0.51 [0.28, 0.73] | 0.0000 |
| d_prime: P3 - P2 | 0.29 [0.11, 0.47] | 0.0028 |
| d_prime: P3 - P4 | 0.27 [0.05, 0.50] | 0.0180 |
| d_prime: P1 - P0 | 0.06 [-0.13, 0.26] | 0.5220 |
| criterion_c: P3 - P1 | -0.19 [-0.27, -0.11] | 0.0000 |
| criterion_c: P3 - P2 | -0.17 [-0.25, -0.09] | 0.0001 |
| criterion_c: P3 - P4 | -0.10 [-0.19, -0.01] | 0.0268 |
| criterion_c: P1 - P0 | -0.11 [-0.21, -0.01] | 0.0393 |

## 9. First-pass -> final changes vs resampling baseline (two independent P0 runs)

flip = action changed; w2r = wrong->right; r2w = right->wrong; net = w2r - r2w (%).

| subset | measure | P0pair | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| missing | flip | 41.6 | 19.0 | 19.4 | 23.5 | 19.5 |
| missing | net | 0.0 | 5.5 | 4.3 | 16.5 | 4.5 |
| missing | r2w | 11.6 | 3.6 | 5.0 | 1.9 | 5.2 |
| missing | w2r | 11.6 | 9.1 | 9.3 | 18.3 | 9.7 |
| present_aligned | flip | 5.2 | 5.4 | 3.7 | 2.7 | 5.6 |
| present_aligned | net | 0.0 | -1.9 | 0.4 | 0.6 | -1.7 |
| present_aligned | r2w | 2.3 | 3.4 | 1.5 | 0.9 | 3.5 |
| present_aligned | w2r | 2.3 | 1.5 | 2.0 | 1.5 | 1.8 |
| present_flawed | flip | 41.2 | 24.4 | 22.8 | 31.3 | 26.4 |
| present_flawed | net | 0.0 | 4.8 | 8.9 | 20.0 | 10.2 |
| present_flawed | r2w | 13.2 | 6.9 | 4.5 | 3.6 | 5.5 |
| present_flawed | w2r | 13.2 | 11.7 | 13.4 | 23.6 | 15.7 |

| contrast | estimate [95% CI] | p (t) |
|---|---|---|
| missing flip: P1 - P0pair | -22.6 [-28.1, -17.2] | 0.0000 |
| missing flip: P2 - P0pair | -22.2 [-28.1, -16.3] | 0.0000 |
| missing flip: P3 - P0pair | -18.1 [-23.9, -12.3] | 0.0000 |
| missing flip: P4 - P0pair | -22.1 [-27.8, -16.4] | 0.0000 |
| missing net: P1 - P0pair | 5.5 [1.7, 9.3] | 0.0060 |
| missing net: P2 - P0pair | 4.3 [-0.0, 8.7] | 0.0523 |
| missing net: P3 - P0pair | 16.5 [11.7, 21.3] | 0.0000 |
| missing net: P4 - P0pair | 4.5 [0.1, 8.8] | 0.0443 |
| present_aligned flip: P1 - P0pair | 0.2 [-1.4, 1.8] | 0.8083 |
| present_aligned flip: P2 - P0pair | -1.5 [-3.6, 0.5] | 0.1372 |
| present_aligned flip: P3 - P0pair | -2.5 [-4.5, -0.6] | 0.0116 |
| present_aligned flip: P4 - P0pair | 0.3 [-1.3, 1.9] | 0.6796 |
| present_aligned net: P1 - P0pair | -1.9 [-3.7, -0.2] | 0.0321 |
| present_aligned net: P2 - P0pair | 0.4 [-1.1, 2.0] | 0.5762 |
| present_aligned net: P3 - P0pair | 0.6 [-0.6, 1.9] | 0.3319 |
| present_aligned net: P4 - P0pair | -1.7 [-3.7, 0.3] | 0.0983 |
| present_flawed flip: P1 - P0pair | -16.8 [-21.0, -12.6] | 0.0000 |
| present_flawed flip: P2 - P0pair | -18.4 [-23.1, -13.8] | 0.0000 |
| present_flawed flip: P3 - P0pair | -9.8 [-14.5, -5.1] | 0.0001 |
| present_flawed flip: P4 - P0pair | -14.8 [-19.5, -10.0] | 0.0000 |
| present_flawed net: P1 - P0pair | 4.8 [1.2, 8.3] | 0.0093 |
| present_flawed net: P2 - P0pair | 8.9 [5.2, 12.6] | 0.0000 |
| present_flawed net: P3 - P0pair | 20.0 [16.5, 23.5] | 0.0000 |
| present_flawed net: P4 - P0pair | 10.2 [6.0, 14.4] | 0.0000 |

Manipulation check - first-pass accuracy (all items): P1 65.0; P2 65.6; P3 65.4; P4 66.0; P0 final 64.9

## 10. Robustness

GEE (binomial, exchangeable within family, bias-reduced SE; adjusted for model):

| model | coef | se | p | n_rows | n_families |
|---|---|---|---|---|---|
| C1 P3-P1 flawed_correction (logOR) | 0.645 | 0.087 | 0.0 | 2880 | 40 |
| C2 P3-P2 flawed_correction (logOR) | 0.446 | 0.077 | 0.0 | 2880 | 40 |
| C3 P3xabsent escalation interaction (logOR) | 0.707 | 0.204 | 0.0005 | 7200 | 40 |

Parse-failure rate by procedure (%): P0 1.36, P1 0.72, P2 1.17, P3 1.83, P4 0.64

Primary contrasts excluding parse failures:

| contrast | F | estimate (pts) [95% CI] | bootstrap 95% CI | p (t) | p (sign-flip) | p_holm |
|---|---|---|---|---|---|---|
| C1: P3 - P1 flawed_correction | 40 | 16.5 [12.4, 20.7] | [12.7, 20.6] | 0.0000 | 0.0000 | 0.0000 |
| C2: P3 - P2 flawed_correction | 40 | 11.4 [7.8, 15.0] | [7.9, 15.0] | 0.0000 | 0.0000 | 0.0000 |
| C3: [escalation P3-P1, absent] - [P3-P1, present] | 40 | 10.9 [5.7, 16.1] | [6.2, 15.8] | 0.0001 | 0.0002 | 0.0001 |

| contrast | estimate [95% CI] | passes |
|---|---|---|
| NI1: P3 - P0 aligned_overturn | -0.1 [-1.8, 1.6] | True |
| NI2: P3 - P0 irrelevant_stability given base correct | 0.7 [-3.2, 4.6] | True |

## 11. Cost (means per response, family-bootstrap 95% CI)

| metric | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| input_tokens | 2,441.2 [2,360.7, 2,526.6] | 5,284.1 [5,124.8, 5,455.9] | 5,364.9 [5,204.7, 5,536.5] | 5,467.8 [5,304.2, 5,642.9] | 5,305.7 [5,143.3, 5,474.8] |
| latency_s | 7.1 [7.0, 7.2] | 13.2 [13.1, 13.3] | 14.1 [14.0, 14.2] | 14.3 [14.2, 14.4] | 13.3 [13.3, 13.4] |
| n_calls | 1.0 [1.0, 1.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] | 2.0 [2.0, 2.0] |
| output_tokens | 340.1 [336.4, 344.2] | 657.0 [651.3, 662.3] | 714.3 [708.5, 719.7] | 722.5 [717.3, 728.0] | 665.1 [660.5, 669.8] |
| total_tokens | 2,781.4 [2,700.4, 2,867.2] | 5,941.0 [5,783.8, 6,110.1] | 6,079.2 [5,920.7, 6,249.1] | 6,190.4 [6,027.4, 6,365.3] | 5,970.9 [5,808.4, 6,138.8] |

| metric | ratio | v |
|---|---|---|
| output_tokens | P1/P0 | 1.93 [1.91, 1.96] |
| output_tokens | P2/P0 | 2.10 [2.07, 2.13] |
| output_tokens | P3/P0 | 2.12 [2.09, 2.16] |
| output_tokens | P4/P0 | 1.96 [1.93, 1.98] |
| output_tokens | P0/P1 | 0.52 [0.51, 0.52] |
| output_tokens | P2/P1 | 1.09 [1.07, 1.10] |
| output_tokens | P3/P1 | 1.10 [1.09, 1.11] |
| output_tokens | P4/P1 | 1.01 [1.00, 1.02] |
| total_tokens | P1/P0 | 2.14 [2.13, 2.14] |
| total_tokens | P2/P0 | 2.19 [2.18, 2.19] |
| total_tokens | P3/P0 | 2.23 [2.22, 2.23] |
| total_tokens | P4/P0 | 2.15 [2.14, 2.15] |
| total_tokens | P0/P1 | 0.47 [0.47, 0.47] |
| total_tokens | P2/P1 | 1.02 [1.02, 1.03] |
| total_tokens | P3/P1 | 1.04 [1.04, 1.04] |
| total_tokens | P4/P1 | 1.01 [1.00, 1.01] |
| latency_s | P1/P0 | 1.86 [1.84, 1.87] |
| latency_s | P2/P0 | 1.99 [1.97, 2.01] |
| latency_s | P3/P0 | 2.01 [1.98, 2.03] |
| latency_s | P4/P0 | 1.88 [1.85, 1.90] |
| latency_s | P0/P1 | 0.54 [0.53, 0.54] |
| latency_s | P2/P1 | 1.07 [1.06, 1.08] |
| latency_s | P3/P1 | 1.08 [1.07, 1.09] |
| latency_s | P4/P1 | 1.01 [1.00, 1.02] |

Compute-match check (P3/P1 output tokens within (0.8, 1.25)): OK

| comparison | extra_tokens_per_response | extra_correct_per_flawed_item | tokens_per_extra_correction | boot_lo | boot_hi | share_boot_gain_positive |
|---|---|---|---|---|---|---|
| P3 vs P0 | 3409.038 | 0.2 | 17045.188 | 14490.048 | 20562.616 | 1.0 |
| P3 vs P1 | 249.345 | 0.156 | 1602.93 | 1263.428 | 2097.002 | 1.0 |
