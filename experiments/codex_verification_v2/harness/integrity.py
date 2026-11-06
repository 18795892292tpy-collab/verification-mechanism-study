"""Offline integrity primitives for the Codex verification experiment.

No model calls occur here. All persisted results are write-once. Legacy branches
are selected atomically; different first-answer attempts are never spliced.

Typical new-run usage::

    with RunLedger(output_dir, frozen_config) as ledger:
        ledger.commit_first(group_id, exact_first_reply, metadata={...})
        ledger.record_procedure(group_id, "P0", {"status": "ok", "text": exact_first_reply})
        # Each independent reviewer receives the same read_first(...)["text"].
        ledger.record_procedure(group_id, "P3", final_transport_record)

Record a procedure only after the protocol's bounded transport retries end.
Malformed or incorrect returned answers are still final records: these helpers
never retry a model or choose a response based on correctness.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


class IntegrityError(RuntimeError):
    """The stored experiment or its provenance violates a frozen invariant."""


class ConfigurationMismatch(IntegrityError):
    pass


class LockUnavailable(IntegrityError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha256_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("first-answer text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def config_hash(config: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(dict(config))).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"Cannot read integrity record: {path}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"Integrity record is not an object: {path}")
    return value


def _write_once(path: Path, value: Mapping[str, Any]) -> bool:
    """Atomically create a file without replacing an existing destination.

    Returns False on an existing destination. A same-directory temporary file
    is fsynced before the hard-link publication. No raw record is overwritten.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical_json(dict(value)) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return True
    finally:
        os.unlink(temporary)


class DirectoryLock:
    """Nonblocking POSIX advisory lock; lock-file presence is not lock state."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self._fd: int | None = None

    def __enter__(self):
        if self._fd is not None:
            raise IntegrityError("A lock instance cannot be entered twice")
        self.directory.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.directory / ".integrity.lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(fd)
            raise LockUnavailable(f"Another writer owns {self.directory}") from exc
        except BaseException:
            os.close(fd)
            raise
        self._fd = fd
        os.ftruncate(fd, 0)
        os.write(fd, canonical_json({"pid": os.getpid(), "acquired_utc": _now()}))
        os.fsync(fd)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


def freeze_config(directory: str | Path, config: Mapping[str, Any]) -> dict:
    """Create/verify an immutable config, including every caller-supplied field."""
    path = Path(directory) / "config_frozen.json"
    expected = {"schema_version": 1, "config": dict(config), "config_sha256": config_hash(config)}
    if _write_once(path, expected):
        return expected
    saved = _read(path)
    if saved.get("config_sha256") != config_hash(saved.get("config", {})):
        raise IntegrityError("Stored config hash does not match its content")
    if canonical_json(saved) != canonical_json(expected):
        raise ConfigurationMismatch("Refusing to resume with a different frozen configuration")
    return saved


class RunLedger:
    """Locked, write-once first-answer and procedure ledger for a new study.

    The caller must include model settings, system/review prompt hashes, case
    hashes, schema and runtime identity in config. Unknown parameters should be
    None, not guessed. The ledger verifies exactly the fields it is supplied.
    """

    def __init__(self, directory: str | Path, config: Mapping[str, Any]):
        self.directory = Path(directory)
        self.config = dict(config)
        self._lock = DirectoryLock(self.directory)
        self._active = False
        self.frozen: dict | None = None

    def __enter__(self):
        self._lock.__enter__()
        try:
            self.frozen = freeze_config(self.directory, self.config)
        except BaseException:
            self._lock.__exit__(None, None, None)
            raise
        self._active = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self._active = False
        self._lock.__exit__(exc_type, exc, tb)

    def _assert_active(self):
        if not self._active:
            raise IntegrityError("RunLedger writes/reads require its directory lock")
        # Detect in-process mutation of the config after entry as well.
        if config_hash(self.config) != self.frozen["config_sha256"]:
            raise ConfigurationMismatch("Configuration changed during a locked run")

    def _group_path(self, group_id: str) -> Path:
        if not isinstance(group_id, str) or not group_id:
            raise IntegrityError("group_id must be a nonempty string")
        return self.directory / "ledger" / sha256_text(group_id)

    def commit_first(self, group_id: str, text: str, metadata: Mapping[str, Any] | None = None) -> dict:
        self._assert_active()
        record = {"schema_version": 1, "group_id": group_id, "text": text,
                  "first_sha256": sha256_text(text), "config_sha256": self.frozen["config_sha256"],
                  "metadata": dict(metadata or {}), "recorded_utc": _now()}
        path = self._group_path(group_id) / "first.json"
        if _write_once(path, record):
            return record
        saved = self.read_first(group_id)
        if saved["text"] != text:
            raise IntegrityError("A first answer is already frozen; resampling is forbidden")
        if saved.get("metadata", {}) != dict(metadata or {}):
            raise IntegrityError("Frozen first-answer metadata cannot be replaced")
        return saved

    def read_first(self, group_id: str) -> dict:
        self._assert_active()
        saved = _read(self._group_path(group_id) / "first.json")
        if saved.get("group_id") != group_id or saved.get("first_sha256") != sha256_text(saved.get("text", "")):
            raise IntegrityError("First answer identity or content hash mismatch")
        if saved.get("config_sha256") != self.frozen["config_sha256"]:
            raise ConfigurationMismatch("First answer belongs to another configuration")
        return saved

    def record_procedure(self, group_id: str, procedure: str, record: Mapping[str, Any]) -> dict:
        self._assert_active()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", procedure):
            raise IntegrityError("Unsafe procedure identifier")
        first = self.read_first(group_id)
        result = dict(record)
        if result.get("status") not in {"ok", "error", "not_run"}:
            raise IntegrityError("A procedure must have an explicit terminal transport status")
        supplied = result.get("first_sha256", first["first_sha256"])
        if supplied != first["first_sha256"]:
            raise IntegrityError("Reviewer received a different first answer")
        if procedure == "P0" and result.get("status") == "ok" and result.get("text") != first["text"]:
            raise IntegrityError("P0 must be the exact frozen first answer")
        wrapped = {"schema_version": 1, "group_id": group_id, "procedure": procedure,
                   "first_sha256": first["first_sha256"], "config_sha256": self.frozen["config_sha256"],
                   "record": result, "recorded_utc": _now()}
        path = self._group_path(group_id) / f"{procedure}.json"
        if _write_once(path, wrapped):
            return wrapped
        saved = _read(path)
        for field in ("group_id", "procedure", "first_sha256", "config_sha256", "record"):
            if saved.get(field) != wrapped[field]:
                raise IntegrityError("A final procedure record already exists; it cannot be replaced")
        return saved


def group_key(plan_row: Mapping[str, Any]) -> tuple:
    return (str(plan_row.get("item_id", "")), str(plan_row["family_id"]), str(plan_row["state"]),
            str(plan_row["advice"]), int(plan_row["repeat"]))


def _finish_timestamp(record: Mapping[str, Any]) -> float:
    value = record.get("finished")
    if not isinstance(value, str):
        raise IntegrityError("Cannot establish earliest completion without a finished timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timezone absent")
        return stamp.timestamp()
    except ValueError as exc:
        raise IntegrityError(f"Invalid finished timestamp: {value}") from exc


def _legacy_first_text(record: Mapping[str, Any]) -> str | None:
    calls = record.get("calls") or []
    text = calls[0].get("text") if calls else record.get("first_text")
    if text is not None and not isinstance(text, str):
        raise IntegrityError("Legacy first text is not a string")
    if record.get("status") == "ok" and text is None:
        raise IntegrityError("Successful record lacks its first answer")
    if text is not None and record.get("first_sha256", sha256_text(text)) != sha256_text(text):
        raise IntegrityError("Legacy first-answer hash mismatch")
    return text


def select_legacy_branches(records: Iterable[Mapping[str, Any]], plan: Iterable[Mapping[str, Any]],
                           expected_procedures: Iterable[str]) -> dict:
    """Select the earliest complete successful branch per planned group.

    'Successful' is transport status, not correctness or JSON parse success.
    All other complete branches are duplicates; incomplete/error attempts remain
    in the audit. Returned selected records are never rewritten on disk.
    """
    expected = set(expected_procedures)
    if not expected or "P0" not in expected:
        raise IntegrityError("Expected procedures must include P0")
    plan_by_id, group_plan = {}, defaultdict(dict)
    for row in plan:
        rid = row["run_id"]
        if rid in plan_by_id:
            raise IntegrityError("Duplicate run_id in plan")
        key = group_key(row)
        proc = row["procedure"]
        if proc in group_plan[key]:
            raise IntegrityError("Duplicate procedure in a planned group")
        plan_by_id[rid] = dict(row)
        group_plan[key][proc] = rid
    if any(set(procs) != expected for procs in group_plan.values()):
        raise IntegrityError("Planned groups do not have the expected procedure set")
    branches, branch_groups = defaultdict(dict), {}
    repeated_identical_records = 0
    for record0 in records:
        record = dict(record0)
        rid, bid = record.get("run_id"), record.get("branch_id")
        if rid not in plan_by_id or not isinstance(bid, str) or not bid:
            raise IntegrityError("Legacy record lacks a known run_id or branch_id")
        row = plan_by_id[rid]
        key, proc = group_key(row), row["procedure"]
        if bid in branch_groups and branch_groups[bid] != key:
            raise IntegrityError("A branch_id is reused for different planned groups")
        branch_groups[bid] = key
        bucket = branches[(key, bid)]
        if proc in bucket:
            if canonical_json(bucket[proc]) != canonical_json(record):
                raise IntegrityError("Conflicting records for one procedure within a branch")
            repeated_identical_records += 1
        else:
            bucket[proc] = record
    complete_by_group = defaultdict(list)
    incomplete = []
    for (key, bid), proc_records in branches.items():
        texts = {_legacy_first_text(rec) for rec in proc_records.values()}
        texts.discard(None)
        if len(texts) > 1:
            raise IntegrityError(f"Branch {bid} contains different first answers")
        successes = {p for p, rec in proc_records.items() if rec.get("status") == "ok"}
        for rec in proc_records.values():
            if rec.get("status") == "ok" and any(c.get("ok") is False for c in rec.get("calls", [])):
                raise IntegrityError("Successful record contains a failed model call")
        audit = {"group": list(key), "branch_id": bid,
                 "present_procedures": sorted(proc_records), "successful_procedures": sorted(successes),
                 "missing_procedures": sorted(expected - set(proc_records)),
                 "failed_procedures": sorted(set(proc_records) - successes),
                 "first_sha256": sha256_text(next(iter(texts))) if texts else None}
        if set(proc_records) == expected and successes == expected:
            audit["completed_timestamp"] = max(_finish_timestamp(r) for r in proc_records.values())
            complete_by_group[key].append((audit, proc_records))
        else:
            incomplete.append(audit)
    selected, chosen, duplicates, uncompleted = {}, [], [], []
    for key in sorted(group_plan):
        candidates = sorted(complete_by_group[key], key=lambda x: (x[0]["completed_timestamp"], x[0]["branch_id"]))
        if not candidates:
            uncompleted.append(list(key))
            continue
        audit, proc_records = candidates[0]
        chosen.append(audit)
        selected.update({rec["run_id"]: rec for rec in proc_records.values()})
        duplicates.extend(a for a, _ in candidates[1:])
    return {"selected": selected, "selected_branches": chosen, "duplicate_branches": duplicates,
            "incomplete_branches": incomplete, "uncompleted_groups": uncompleted,
            "counts": {"planned_groups": len(group_plan), "unique_complete_groups": len(chosen),
                       "complete_branch_attempts": len(chosen) + len(duplicates),
                       "duplicate_complete_branches": len(duplicates), "incomplete_branches": len(incomplete),
                       "uncompleted_groups": len(uncompleted), "identical_repeated_records": repeated_identical_records}}


def planned_outcomes(plan: Iterable[Mapping[str, Any]], scored_by_run_id: Mapping[str, Mapping[str, Any]]) -> list[dict]:
    """Keep the full plan denominator; the caller supplies already scored answers.

    Inputs per run may contain status, parse_ok and correct. Missing/technical
    failure/parse failure receives primary_correct=0, with its reason retained.
    """
    output = []
    seen = set()
    for planned in plan:
        rid = planned["run_id"]
        if rid in seen:
            raise IntegrityError("Duplicate run_id in denominator plan")
        seen.add(rid)
        value = scored_by_run_id.get(rid)
        if value is None:
            status, correct = "not_run", 0
        elif value.get("status") != "ok":
            status, correct = "transport_error", 0
        elif not value.get("parse_ok"):
            status, correct = "parse_error", 0
        else:
            status, correct = "completed", int(bool(value.get("correct")))
        output.append({**dict(planned), "outcome_status": status, "primary_correct": correct})
    extras = set(scored_by_run_id) - seen
    if extras:
        raise IntegrityError("Scored records contain unplanned run IDs")
    return output


def rate_or_none(numerator: int, denominator: int) -> float | None:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("Invalid count ratio")
    return numerator / denominator if denominator else None
