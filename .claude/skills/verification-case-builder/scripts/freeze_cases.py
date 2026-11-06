"""Freeze a case set (SHA-256 per file) or verify a set against a manifest.

Usage:
  python freeze_cases.py <folder> -o manifest.json [--allow-unreviewed]
  python freeze_cases.py <folder> --verify manifest.json

Freezing refuses families with checker errors, and (unless --allow-unreviewed, meant for
development sets only) families whose expert_review.status is not "approved".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caselib as cl  # noqa: E402
from check_cases import check_family  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(folder: Path) -> dict:
    return {p.name: sha256(p) for p in sorted(folder.glob("*.json"))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("-o", "--out")
    ap.add_argument("--verify")
    ap.add_argument("--allow-unreviewed", action="store_true")
    args = ap.parse_args()
    folder = Path(args.folder)
    if args.verify:
        man = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        now = hashes(folder)
        bad = {k for k in set(now) | set(man["files"]) if now.get(k) != man["files"].get(k)}
        if bad:
            print(f"MISMATCH: {sorted(bad)}")
            return 1
        print(f"OK: {len(now)} files match manifest frozen at {man['frozen_at']}")
        return 0
    if not args.out:
        ap.error("-o is required when freezing")
    problems = []
    for fam in cl.load_dir(folder):
        errors, _ = check_family(fam)
        if errors:
            problems.append(f"{fam['family_id']}: {len(errors)} checker errors")
        if fam["expert_review"].get("status") != "approved" and not args.allow_unreviewed:
            problems.append(f"{fam['family_id']}: expert_review.status is not approved")
    if problems:
        print("Refusing to freeze:\n  " + "\n  ".join(problems))
        return 1
    man = {"frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "folder": str(folder), "allow_unreviewed": args.allow_unreviewed, "files": hashes(folder)}
    Path(args.out).write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"Froze {len(man['files'])} files -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
