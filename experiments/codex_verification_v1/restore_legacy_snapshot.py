#!/usr/bin/env python3
"""Restore omitted duplicates from pinned Git objects, with SHA-256 checks."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
spec=json.loads((ROOT/"PUBLICATION_OMISSIONS.json").read_text())
for row in spec["omissions"]:
    if "source_commit" not in row:
        continue
    data=subprocess.check_output(["git","show",row["source_commit"]+":"+row["source_path"]],cwd=REPO)
    if len(data)!=row["bytes"] or hashlib.sha256(data).hexdigest()!=row["sha256"]:
        raise RuntimeError("Pinned source hash mismatch: "+row["source_path"])
    dest=REPO/row["omitted_path"]
    if dest.exists():
        if dest.read_bytes()!=data: raise RuntimeError("Refusing overwrite: "+str(dest))
    else:
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as out: out.write(data)
    print("verified",row["omitted_path"])
