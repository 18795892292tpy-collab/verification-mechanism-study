"""Offline branch selection, resume validation and process-level writer lock.

Selection is transport based, never answer/key based. Parse failures and truncated
successful responses remain decisions and are flagged downstream, not resampled.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


class IntegrityError(RuntimeError):
    pass


def digest(value):
    data = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def group_key(row):
    return tuple(str(row[k]) for k in ("family_id", "state", "advice", "repeat"))


def read_records(path):
    records, malformed = [], []
    if Path(path).exists():
        for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("not an object")
            except (ValueError, json.JSONDecodeError):
                malformed.append(number)
                continue
            records.append((number, record))
    return records, malformed


def select_branches(plan, records):
    """Return run_id -> record plus an audit; select whole earliest complete branches.

    Completion is max(finished); ties use first JSONL line then branch_id, matching
    the original read-only snapshot audit. Missing/invalid timestamps are rejected.
    """
    by_id = {r["run_id"]: r for r in plan}
    if len(by_id) != len(plan):
        raise IntegrityError("Duplicate run_id in plan")
    expected = defaultdict(dict)
    for row in plan:
        key, proc = group_key(row), row["procedure"]
        if proc in expected[key]:
            raise IntegrityError(f"Duplicate procedure in planned group: {key}")
        expected[key][proc] = row["run_id"]
    branches = defaultdict(list)
    unknown = []
    for lineno, rec in records:
        if rec.get("run_id") not in by_id:
            unknown.append(lineno)
        else:
            branches[rec.get("branch_id") or f"missing-branch-at-line-{lineno}"].append((lineno, rec))
    candidates, checks = defaultdict(list), []
    for bid, entries in branches.items():
        keys = {group_key(by_id[r["run_id"]]) for _, r in entries}
        key = next(iter(keys)) if len(keys) == 1 else None
        ids = [r["run_id"] for _, r in entries]
        reasons = []
        if not all(r.get("branch_id") for _, r in entries):
            reasons.append("missing_branch_id")
        if key is None or len(ids) != len(set(ids)) or set(ids) != set(expected[key].values()):
            reasons.append("incomplete_or_duplicate_membership")
        firsts = [r.get("calls", [{}])[0] if r.get("calls") else {} for _, r in entries]
        first_text_hashes = {digest(c.get("text", "")) for c in firsts}
        if len(first_text_hashes) != 1 or len({digest(c) for c in firsts}) != 1:
            reasons.append("different_first_text_or_call")
        for _, rec in entries:
            calls = rec.get("calls") or []
            proc = by_id[rec["run_id"]]["procedure"]
            if len(calls) != (1 if proc == "P0" else 2):
                reasons.append("wrong_call_count")
            if rec.get("status") != "ok" or not calls or not all(c.get("ok") is True for c in calls):
                reasons.append("transport_failure")
            if len(calls) == 2:
                replay = calls[1].get("messages_appended") or []
                if not replay or replay[0] != {"role": "assistant", "content": calls[0].get("text")}:
                    reasons.append("review_does_not_replay_full_first_text")
        try:
            times = [datetime.fromisoformat(r["finished"]) for _, r in entries]
            if any(t.tzinfo is None for t in times):
                raise ValueError("timezone missing")
            finished = max(times).astimezone(timezone.utc).isoformat()
        except (KeyError, TypeError, ValueError):
            finished = None
            reasons.append("missing_or_invalid_finished")
        check = {"branch_id": bid, "group": list(key) if key else None,
                 "eligible": not reasons, "reasons": sorted(set(reasons)),
                 "finished": finished, "first_line": min(n for n, _ in entries),
                 "rows": len(entries), "first_text_sha256": next(iter(first_text_hashes)) if len(first_text_hashes) == 1 else None}
        checks.append(check)
        if not reasons:
            candidates[key].append((check, entries))
    selected, chosen, duplicates = {}, [], []
    for key, options in sorted(candidates.items()):
        options.sort(key=lambda x: (x[0]["finished"], x[0]["first_line"], x[0]["branch_id"]))
        chosen.append(options[0][0])
        selected.update({r["run_id"]: r for _, r in options[0][1]})
        if len(options) > 1:
            duplicates.append({"group": list(key), "branches": [x[0]["branch_id"] for x in options]})
    return selected, {"selection_policy": "earliest_completed_fully_successful_complete_branch",
                      "planned_groups": len(expected), "unique_complete_groups": len(chosen),
                      "remaining_groups": len(expected) - len(chosen),
                      "complete_branch_attempts": sum(len(v) for v in candidates.values()),
                      "branch_attempts": len(branches), "duplicate_groups": duplicates,
                      "duplicate_group_count": len(duplicates),
                      "duplicate_record_count": len(records) - len({r.get('run_id') for _, r in records}),
                      "unknown_run_id_lines": unknown, "selected_branches": chosen, "branches": checks}


def select_run(run_dir):
    directory = Path(run_dir)
    with (directory / "plan.csv").open(encoding="utf-8", newline="") as f:
        plan = list(csv.DictReader(f))
    records, malformed = read_records(directory / "responses.jsonl")
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("manifest_*.json"))]
    if not manifests:
        raise IntegrityError("No manifest; cannot establish branching condition")
    branching = manifests[0].get("branching", False)
    if any(m.get("branching", False) != branching for m in manifests):
        raise IntegrityError("Conflicting branching conditions in manifests")
    if branching:
        required = set(manifests[0]["procedures"])
        planned = defaultdict(list)
        for row in plan:
            planned[group_key(row)].append(row["procedure"])
        if "P0" not in required or any(set(v) != required or len(v) != len(required) for v in planned.values()):
            raise IntegrityError("Plan groups do not contain the manifest's complete procedure set")
        selected, audit = select_branches(plan, records)
    else:
        # Preserve nonbranching historical selection; never use this for branch data.
        if any(r.get("branch_id") for _, r in records):
            raise IntegrityError("Branch records found under a nonbranching manifest")
        selected = {r["run_id"]: r for _, r in records if r.get("status") == "ok"}
        grouped = defaultdict(set)
        for row in plan:
            grouped[group_key(row)].add(row["run_id"])
        complete = sum(ids <= selected.keys() for ids in grouped.values())
        audit = {"selection_policy": "legacy_nonbranching_latest_ok", "unique_complete_groups": complete,
                 "planned_groups": len(grouped), "remaining_groups": len(grouped) - complete,
                 "duplicate_record_count": len(records) - len({r.get("run_id") for _, r in records}),
                 "duplicate_group_count": None, "complete_branch_attempts": None,
                 "note": "Nonbranching complete groups do not share a first answer; branch duplicates are NA."}
    condition_fields = ("backend", "params", "base_url", "procedures", "repeats", "seed", "system", "system_text", "case_files", "review_prompt_chars")
    conflicts = sorted({k for m in manifests[1:] for k in condition_fields if m.get(k) != manifests[0].get(k)})
    audit.update(branching=branching, malformed_json_lines=malformed, raw_response_rows=len(records), manifest_conflicts=conflicts)
    return plan, selected, audit, records, manifests


class DirectoryLock:
    """Advisory OS lock shared by independent runner processes on this filesystem.

    Kept on disk after release: deleting a lock file can split the locking inode.
    POSIX flock and Windows msvcrt are supported; network-FS locks are not promised.
    """
    def __init__(self, directory):
        self.path = Path(directory) / ".runner.lock"
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                self.file.write(b"0")
                self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            self.file = None
            raise IntegrityError(f"Output directory is locked by another writer: {self.path.parent}") from exc
        return self

    def __exit__(self, *exc):
        if self.file:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()
            self.file = None


def validate_resume(directory, manifest, plan, expected_plan):
    """Verify all earlier manifests and plan before appending any new response.

    runner.py itself may change to receive integrity fixes. Prompt rendering code
    must not change. Timeout/concurrency/limit are operational, not request fields.
    """
    fields = ("backend", "params", "base_url", "procedures", "repeats", "seed", "system", "system_text", "branching", "case_files", "review_prompt_chars")
    paths = sorted(Path(directory).glob("manifest_*.json"))
    if not paths:
        raise IntegrityError("Existing plan has no manifest; refusing unverified resume")
    for path in paths:
        old = json.loads(path.read_text(encoding="utf-8"))
        mismatches = [k for k in fields if old.get(k) != manifest.get(k)]
        for name in ("procedures.py", "caselib.py"):
            if old.get("code_files", {}).get(name) != manifest["code_files"].get(name):
                mismatches.append(f"code_files.{name}")
        for name in ("review_text_sha256", "plan_sha256"):
            if name in old and old[name] != manifest[name]:
                mismatches.append(name)
        if mismatches:
            raise IntegrityError(f"Resume configuration differs from {path.name}: {', '.join(mismatches)}")
    shape = lambda rows: Counter((group_key(r), r["procedure"]) for r in rows)
    if shape(plan) != shape(expected_plan):
        raise IntegrityError("Existing plan does not match requested cases/procedures/repeats")
