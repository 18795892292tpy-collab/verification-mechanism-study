# Independent final review

**Deterministic verdict:** PASS
**Semantic review:** same-family / provisional. No model calls were made by this audit.

Verified target: `liekkas:/home/grf/Desktop/Codex_Verification_Experiment_2026-11-06/codex_verification_v1`.
Frozen manifest: `d24e2ecc0aafe67c566a0afcd0c88b3d44db8e00d28340beac858765154f2d64`; 24 source files checked.
Checks: 19,217; issues: 0.

The script independently reads saved files and recomputes scoring; it does not import the runner, oracle, integrity checker, or evaluator.

P7/P8 added instruction bodies have 43/44 characters; the complete appended prompt strings including the separator newline have 44/45. The reviewed report distinguishes these conventions.

| Phase | Families | Variants | Completed | Sessions | Input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|---:|
| toy | 2 | 2 | 10 | 10 | 181,149 | 4,140 |
| dev | 4 | 40 | 200 | 200 | 3,700,892 | 91,081 |

## Verified evidence

- Frozen inputs, task coverage and identity, literal shared P0 text in all four reviews, raw response/event/metadata hashes and parsed answers.
- A fresh session ID for each completed attempt; no tool-item or unknown event types.
- Independent rescoring against pre-frozen fictional-rule keys, CSV/summary/family agreement, denominators, actual usage and extension gate.
- Manual report reading plus exact table/resource checks; synthetic scope and inference limits are explicit.

## Nonfatal CLI warnings

These are saved `item.type=error` events. They are not discarded, and they are not mislabeled as returned-answer failures.

- **unstable_skip_host_skill_discovery: 210.** Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /home/grf/.codex/config.toml.

- **disabled_code_mode_host: 210.** Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.

- **skills_context_budget_removed: 210.** Exceeded skills context budget. All skill descriptions were removed and 144 additional skills were not included in the model-visible skills list.

## Interpretation limits

The development data comprise four synthetic case families and forty variants, with one first answer and four independent-session reviews per variant. There are no human participants. The fixed ground truth comes from authored case rules, not from the tested responses.

For this batch, a zero natural-error denominator must remain NA/null for repair. Observed zero damage has a nonzero denominator and is a separate statistic. Equal observed answers do not establish equivalence, superiority, or real-world management benefit.

The audit is a same-family provisional review. Token totals are CLI-reported experiment calls only; management overhead and hidden provider sampling details are not known.

## Issues

None found in the checks performed.

Reviewed report SHA-256: `047a8063f6cfe859e416897e2f313caa4681b0fc597d968cabf3b354e8600725`.

Full evidence hashes and recomputed tables: `audits/final_review.json`.
