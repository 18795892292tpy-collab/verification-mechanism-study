# Independent final audit preparation — not an experiment result

Prepared on 2026-11-07 for the original target `liekkas`:
`/home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2`.

Status: **PREPARATION_ONLY**. No final integrity verdict, performance conclusion,
or final audit report has been issued. The fixed batch was still running during
preparation. The final-audit readiness guard was tested and refused to proceed
because terminal records and the four analysis artifacts were incomplete.

Reviewer route: fresh reviewer `/root/v2_final_audit`, **same-family**,
**provisional**. The exact inherited reviewer model/reasoning configuration is
not independently exposed here and is not asserted as an external reviewer.
Instructions applied: `experiment-audit/SKILL.md`,
`shared-references/reviewer-independence.md`,
`shared-references/experiment-integrity.md`, and
`shared-references/review-tracing.md`, read from `/home/grf/.codex/skills/`.

## Primary evidence and independent implementation

The reviewer directly read the frozen plan, execution amendment, analysis plan,
backend and frozen manifest; public items, answer keys and factual truth tables;
the full runner and evaluator; and representative original raw run files. No
executor result summary was accepted as evidence. The original approved plan's
extra screening proposal is superseded by the pre-answer execution amendment:
800 fixed tasks, 160 P0 groups, no result-dependent case selection.

`audits/independent_final_audit.py` uses Python's standard library only. It does
not import or invoke `runner`, `evaluate`, `summarize`, any case builder or any
model/API/CLI. It makes no network request. It never rewrites a frozen source,
analysis artifact, record, attempt or raw response.

The eight public rule systems were read before coding the oracle. Rule constants
are explicitly transcribed in that independent implementation. Decisive facts
are extracted from public S3/S4 text, and option letters are obtained from public
option wording. `state`, advice direction, supplied `correct_action`, and model
answers do not determine the oracle answer. The script then compares the
independently reconstructed facts/action with all 80 keys and 40 truth tables,
checks source-document equality, advice alignment, changed counterfactuals,
unchanged irrelevant/paraphrase variants and explicit missing-evidence pauses.
This is an oracle scoped to these frozen fictional rules, not a general natural
language theorem prover or independent education-domain expert endorsement.

The independently pinned frozen manifest SHA-256 is:
`f5f73d297f3cc6b3f4049770dc6688a2ddc72ca66a784a89fd712d9c243afaf1`.
All manifest-listed source hashes and the run's manifest identity are rechecked.

## Final checks prepared

- Exact 8 × 5 × 2 × 2 × 5 matrix, 800 unique planned tasks, 160 P0 groups and
  frozen `plan.csv` ordering; 800 terminal records are required for final audit.
- All `runs/` paths are allowlisted, including failures and both allowed attempt
  directories. Raw task/attempt evidence elsewhere in the project is rejected;
  the subject's `runtime_empty` directory must remain empty if present.
- Every attempt is reconstructed from its own raw events, response, stderr and
  durable start marker. Source/prompt/manifest hashes, raw artifact hashes,
  requested backend identity, lifecycle, session uniqueness, elapsed times and
  terminal-final hashes are checked. A returned answer or protocol violation
  cannot be followed by a retry. Failed attempts and their actual logs remain
  visible. No observed tool/unknown event is accepted.
- Every review prompt must contain the exact same group's complete P0 text and
  hash, with its own procedure instruction. Reviews cannot begin before all
  160 P0 terminal records exist. The four reviews do not share each other's text.
- Every planned row is independently scored from raw final JSON and the public
  rule oracle. All row fields and all 40 family rows are compared with the
  original CSVs. Accuracy retains technical/format failures in its planned
  denominator; natural repair only includes complete, wrong, evidence-present
  P0 decisions. Missing-evidence decisions are separately counted. Zero repair
  or damage denominators remain `null`/NA.
- I78 and I73 are calculated from within-family paired differences and then
  equal-weight type means, with four designed families per type. P3−P1,
  within-type contrasts, all/aligned/missing strata, complete-pair sensitivity,
  and the P0 difficulty diagnostics are independently recomputed and compared.
- Token usage is reconstructed from each attempt's raw `turn.completed` usage.
  Known subtotals and unknown attempt counts are separate; a missing total is
  `null`, never fabricated as zero. Actual attempt counts and task counts differ
  when retries or blocked reviews occur. Verified billed cost remains unknown.
- The original `integrity_audit.json` and complete analysis summary are checked
  against the independent reconstruction. Before/after hashes reject a moving
  input tree; run completion alone is insufficient if analysis is still writing.

## Preparation validation performed

The read-only `--prepare-check` succeeded for the pinned sources and 80 public
oracles. An offline probe validated the script syntax, independent imports,
unknown-usage handling, JSON schema boundaries and one real completed raw
attempt's provenance. In-memory synthetic arrays checked denominator/NA and
family-interaction arithmetic; those arrays were never written as experiment
results. The readiness guard refused the incomplete final matrix and created no
final audit file. No model calls were made. No long polling or waiting for the
batch to complete was performed.

## Running the later real audit

On the original host and exact target, after execution and original analysis
have finished:

```bash
python /home/grf/Desktop/Codex_Verification_Experiment_2026-11-07/codex_verification_v2/audits/independent_final_audit.py --final
```

After the same reviewer inspects the outcome, `--final --write` may create
`audits/INDEPENDENT_FINAL_AUDIT.json`. It uses exclusive creation and refuses to
overwrite a previous audit. A rejected or incomplete check exits nonzero and
does not fabricate a successful report. Default mode verifies the original
host, target path and currently installed CLI byte identity without running it.

For an explicitly selected downloaded archive, use the portable evidence mode:

```bash
python /absolute/path/to/downloaded/codex_verification_v2/audits/independent_final_audit.py --archive-root /absolute/path/to/downloaded/codex_verification_v2 --final
```

This mode requires no Codex installation, account, credential or matching CLI
binary. It reports the actual audited archive path and
`target_mode: archive_evidence_only`. The original runtime identity is retained
and validated as immutable historical evidence, while
`local_cli_byte_identity_checked: false` and
`restored_experiment_execution: false` prevent confusion with real execution on
`liekkas`. An archive is not silently substituted for the user's original target;
only the explicit option selects it. `--prepare-check` is also available in
archive mode. Neither mode calls a model.

## Mandatory claim limits for the final report

The batch is a **simulation_only**, descriptive development experiment using
author-constructed closed rules. There are **four designed families per type**;
repetitions, advice conditions and transformations are not independent families.
There is **no independent education-administration expert validation**. Same-
family semantic review remains provisional even if deterministic hashes and
arithmetic agree. No human behavior, policy effectiveness, population-wide
superiority, equivalence or isolated internal cognitive mechanism is established.

Observable CLI session events and the requested `gpt-6-astra / ultra` setting do
not expose the hidden model weight snapshot or prove equality to desktop hidden
context. Raw warning items, including disabled code-mode and removed skill-list
diagnostics, will be reported; absence of tool events does not prove the absence
of all service-side hidden context. Usage excludes unknown authoring, review and
management overhead. A ceiling still leaves conditional repair undefined when
there are no natural first-pass errors.

Full preparation trace:
`.aris/traces/experiment-audit/2026-11-07_final/`.

## Follow-up preparation: during-run concurrency amendment

On the follow-up request, the reviewer directly inspected
`protocol/CONCURRENCY_AMENDMENT_2026-11-07.json`,
`harness/run_concurrency_override.py`, `audits/concurrency_override_tests.json`,
`audits/concurrency_stop_request.json`, the applied amendment and invocation
artifacts when they appeared, and the original `runs/dev/progress.jsonl`.
The 28 original frozen source hashes remain the baseline. This additional
operational amendment is explicitly **during the run**, not a retrospective
claim that 12 workers were part of the initial freeze.

The inspected driver clones the frozen `run` function with only its private
`MAX_WORKERS` guard changed to 12. Referenced `verify`, `execution_config`,
`response_task` and scoring functions retain their original module globals.
The independent audit never imports or executes this driver or its test source;
it pins the directly reviewed driver and amendment bytes, then checks the
actual records rather than accepting the author's tests as independent proof.

New checks in the audit script cover:

- Original frozen manifest and driver hashes; exact 3-to-12 scope; the parent-only
  SIGINT request and recorded exit 130; all **667 prior terminal records** still
  matching their pre-amendment snapshot hashes, including all 160 P0 records.
- The applied record embedding the exact amendment, every unique invocation
  artifact matching a progress marker, and each marker immediately followed by
  the matching 12-worker dispatcher start. An unapplied amendment is marked
  pending during preparation and is insufficient for this amended batch's final
  audit. Six-worker dispatch is not inferred from the earlier stop-request text:
  the subsequent amendment explicitly changed that proposed increase to 12.
- The immutable first 119,354 bytes of the original progress log, independently
  pinned before the new driver ran. No historical progress entries are inserted
  or rewritten by the audit.
- Raw attempt timestamps assigned to the correct dispatcher phase; no sampling
  of any already-terminal pre-amendment task; no start after the SIGINT request
  before the new phase; no unsealed attempt at final audit; actual overlap no
  greater than each declared worker limit; no cross-invocation overlap.
- Every progress task-result refers to a planned task and agrees with its sealed
  terminal status. Repeated progress entries for reused terminal records do not
  become new model calls. Actual attempt totals come from raw artifacts.
- Final checks require closed amended invocation provenance and unchanged
  amendment/application/invocation inputs across the audit snapshot.

The original progress prefix contains 664 task-result entries but the cutover
snapshot contains 667 terminal records. Direct timestamp inspection identifies
exactly these three calls as already in flight at the SIGINT request; they sealed
after the parent stopped consuming completed futures:

- `runs/dev/M04_paraphrase_aligned_r1/P1/record.json`
- `runs/dev/R01_missing_flawed_r2/P8/record.json`
- `runs/dev/M04_irrelevant_aligned_r2/P7/record.json`

Their original raw attempts and terminal records are retained. The absence of
their task-result entries in the old progress prefix is disclosed, not repaired
by fabricated historical events. A later resumed dispatcher may legitimately
log these existing records again without making new model calls.

The updated `--prepare-check` read the actual applied amendment and invocation
evidence successfully. This was an operational-evidence preparation check,
**not** a final 800-task audit or a performance conclusion. The existing
`--archive-root` mode includes these extra evidence files without installing or
calling Codex. No frozen inputs, records, original progress log or author scripts
were modified.

Final reporting must state that latency and resource observations mix the
3-worker and 12-worker phases. Source preservation does not prove identical
service load, and these observations cannot establish a causal speedup. The
development/simulation and same-family/provisional limitations above continue
to apply.
