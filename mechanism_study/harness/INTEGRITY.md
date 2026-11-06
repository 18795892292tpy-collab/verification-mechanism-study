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

The shared reader verifies every recorded `plan_sha256` using the runner's exact
integer normalization of `repeat` and `order`. A versioned integrity manifest
cannot silently downgrade by dropping its hashes. Scoring binds **all** planned
families to `case_files`, reconstructs the complete planned membership from the
verified case renderer, procedures and repeats, then compares every recorded
first user message against the frozen family/state/advice text. Changing only an
answer key is also rejected by the case-file hash, even if no visible text changes.
The same raw-to-case binding is checked before resume writes anything.

Prompt identity includes the exact review text, review lengths, system text, and
`procedures.py`/`caselib.py` source identity. Both within-directory checks and
cross-directory pooling use this same verified condition. Recorded new review
hashes must match the verified source and raw review messages. For old manifests
without review hashes, the exact source and recorded review messages supply that
evidence. Only bundled, hash-matched semantic sources are supported; unknown or
missing sources are explicitly refused. `runner.py` hash changes remain allowed.

Two narrow legacy compatibility rules are recorded in each audit:

- Exact LF/CRLF reconstruction is allowed when its byte SHA-256 matches the
  original recorded hash. JSON rewriting or other semantic equivalence is not.
- `legacy_sources/procedures_p0_p4.py` reproduces the first H04 source exactly:
  SHA-256 `c88beeedef76b33356471108a520e1c51c7082880308fda04b4ddd49a85a2362`.
  It was reconstructed by removing the later P5/P6 block and its two procedure
  entries, then matched to the original manifest. No original source is rewritten.

Old manifests have no plan hash. Raw prompts can verify family/state/advice and
procedure labels, and the manifest verifies full membership and repeat counts;
ambiguous identical prompts are refused. However, original repeat/order labels
were not included in requests, so those historical assignments cannot be
independently recovered from messages. The fixed snapshot audit additionally
checks plan bytes against its recorded Git commit; a generic imported legacy run
does not gain that historical anchor merely by passing shape checks.

Reports show `NA` for a rate with a zero denominator or a repair effect with no
incorrect first answers. A sign test without discordant pairs and a Wilcoxon
test with no nonzero differences are also `NA`. Equal observed repair rates are
still reported when defined, and valid numerical p-values remain visible when
there are informative pairs. None of these empty-data cases implies equivalence.

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
python harness/audit_results.py results/flash_branch_dev results/flash_think_branch_dev results/flash_think_branch_hard --cases cases/dev cases/dev cases/dev_hard --out /tmp/legacy-audit.json
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
Supplying `--cases` enables frozen-case, label and denominator verification.
Without it, the audit explicitly reports `case_binding` as unverified; structural
counts from such an audit do not establish that a legacy plan's labels are intact.

The executable tests use only `Mock`, cover complete/partial/retried branches,
same-action different-text contamination, exact review replay, malformed tails,
parameter and plan conflicts, legacy manifests/CSVs, cost availability, and two
independent processes competing for the output lock.
With scipy installed, five additional CLI integration regressions execute both
report entry points on deterministic mock fixtures, including zero-error and
missing-evidence-only runs. These tests explicitly skip if scipy is unavailable;
the full validated environment uses Python 3.12.13 and SciPy 1.18.1.
Additional provenance regressions cover plan hash/order changes, legacy label
swaps and dropped groups, hidden answer-key changes, review/code conflicts,
the safe runner-hash exception, exact CRLF compatibility, missing evidence,
and rejection of two individually valid but different semantic source versions.
