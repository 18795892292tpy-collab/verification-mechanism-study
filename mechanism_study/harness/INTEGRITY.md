# Legacy runner integrity repair (Issue #2, task 1)

This repair makes no model calls and does not authorize resuming DeepSeek. It is
separate from the Codex experimental batch. Historical raw records remain intact.

## Selection and analysis

For branching runs, scorer, reports and runner resume use the same selector:
one **earliest completed, fully successful, complete branch** per planned
family/state/advice/repeat group. Completion is the maximum timezone-aware
`finished` timestamp; ties use first JSONL line and then branch ID. All planned
procedures must appear exactly once, calls must succeed, the full shared first
text and first-call object must match, and each review must replay that exact text.
Partial/failed branches cannot be combined into a synthetic successful group.

Selection never examines the answer key. A returned parse failure or truncated
successful call remains a scored decision and is flagged; it is not resampled to
obtain a better answer. Transport failures may require a whole-group retry.

New scored CSVs add `branch_id`, `first_text_sha256`, and `selection_policy`.
Reports recompute canonical rows from sibling raw files and compare the CSV.
Old CSVs remain usable when their rows match; stale latest-per-procedure CSVs are
explicitly rejected and must be rescored. A CSV alone cannot prove full-text
identity, so detached CSV analysis is intentionally refused. `scorer --out`
can write a separate CSV for inspection without overwriting historical outputs.
Nonbranching historical scoring retains its legacy selection and cannot be used
in branching reports. Pooling checks model/request/procedure conditions and
rejects repeated copies of the same raw data. Overlapping planned groups across
folders are refused so exported CSVs cannot confuse independent repeat batches.

## Resume and process locking

The runner acquires `.runner.lock` before any plan, manifest or response write.
It uses POSIX `flock` (tested) or Windows `msvcrt` (implemented, not tested here).
The lock file remains after release; its presence does not mean a process owns it.
Do not delete the file to bypass a live writer. This is an advisory local-filesystem
lock; unmodified legacy runners, external writers and unreliable network mounts
are outside its protection.

Resume validates all previous manifests: backend, base URL, model and request
parameters, procedures, repeats, seed, system text, case hashes, review lengths,
and the `procedures.py`/`caselib.py` hashes. New manifests additionally record
exact review text and plan hashes. `runner.py` itself may change for this repair;
its hash is still recorded. Timeout, concurrency and limit may change because they
do not alter request contents. Conflicting settings, a malformed tail, unknown
response IDs, or a plan without manifests are refused before appending data.
Legacy manifests with the original fields are supported without rewriting them.
Manifest creation is exclusive and includes microseconds to avoid collisions.

## Read-only audit and verification

From `mechanism_study/`:

```bash
python harness/audit_results.py results/flash_branch_dev results/flash_think_branch_dev results/flash_think_branch_hard --out /tmp/legacy-audit.json
python -m unittest discover -s tests -v
```

The audit counts unique complete groups, duplicates, transport failures,
truncations and recorded tokens. A shared first call is counted once per branch,
including duplicate branches that genuinely consumed calls. Missing usage fields
are reported as missing, rather than silently presented as measured zero.
`cost.total: null` means **NA**. Optional `--pricing` requires explicit applicable
rates, currency and source; it never fetches or guesses prices. It reports a
known-call subtotal separately, and refuses a complete expense claim when tokens,
rates or unlogged transport retries leave cost unknown. A price fixture is used
only in offline tests and is not a provider quote.

The executable tests use only `Mock`, cover complete/partial/retried branches,
same-action different-text contamination, exact review replay, malformed tails,
parameter and plan conflicts, legacy manifests/CSVs, cost availability, and two
independent processes competing for the output lock.
