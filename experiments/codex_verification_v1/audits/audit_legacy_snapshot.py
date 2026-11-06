#!/usr/bin/env python3
"""Read-only remote audit of exactly three legacy result folders.

Never invokes a model, reads credentials, or modifies the source repository.
Selects the earliest completed, fully successful P0-P6 branch per planned group.
"""
from __future__ import annotations
import collections
import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
import re
import socket
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMIT = "cf8a5b64bb221882348c0091f401a0e1f4847d24"
REPO = "18795892292tpy-collab/verification-mechanism-study"
FOLDERS = ("flash_branch_dev", "flash_think_branch_dev", "flash_think_branch_hard")
PROCS = {f"P{i}" for i in range(7)}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def group_key(plan_row):
    return tuple(plan_row[k] for k in ("family_id", "state", "advice", "repeat"))

def key_object(key):
    return dict(zip(("family_id", "state", "advice", "repeat"), key))

def fetch_verified(entry):
    remote = entry["path"]
    folder, name = remote.split("/")[-2:]
    destination = ROOT / "legacy_snapshot" / folder / name
    url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{remote}"
    if destination.exists():
        data = destination.read_bytes()
        reused = True
    else:
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        reused = False
    blob_sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if blob_sha != entry["sha"] or len(data) != entry["size"]:
        raise RuntimeError(f"Remote blob identity mismatch: {remote}")
    if not reused:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as out:
            out.write(data)
    return {"remote_path": remote, "url": url, "local_path": str(destination),
            "bytes": len(data), "git_blob_sha1": blob_sha, "sha256": sha(data),
            "git_blob_identity_verified": True, "reused_existing_verified_snapshot": reused}

def parse_action(text):
    # Same structural parse rule as the referenced scorer; no answer-key scoring.
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text or "", re.S)
    candidates = candidates or re.findall(r'\{[^{}]*"action"[^{}]*\}', text or "", re.S)
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            try:
                obj = json.loads(re.sub(r",\s*}", "}", raw.replace("'", '"')))
            except json.JSONDecodeError:
                continue
        action = str(obj.get("action", "")).strip().upper()[:1]
        if action in {"A", "B", "C", "D"}:
            return action
    return None

def audit_folder(folder):
    directory = ROOT / "legacy_snapshot" / folder
    plan = list(csv.DictReader(io.StringIO((directory / "plan.csv").read_text())))
    plan_by_id = {r["run_id"]: r for r in plan}
    if len(plan_by_id) != len(plan):
        raise RuntimeError(f"Duplicate plan run_id: {folder}")
    planned_groups = collections.defaultdict(list)
    for row in plan:
        planned_groups[group_key(row)].append(row)
    for key, group in planned_groups.items():
        if len(group) != 7 or {r["procedure"] for r in group} != PROCS:
            raise RuntimeError(f"Malformed P0-P6 plan group: {folder} {key}")
    rows = []
    for lineno, line in enumerate((directory / "responses.jsonl").read_text().splitlines(), 1):
        if line.strip():
            rows.append((lineno, json.loads(line)))
    branch_records = collections.defaultdict(list)
    run_records = collections.defaultdict(list)
    for lineno, record in rows:
        if record["run_id"] not in plan_by_id:
            raise RuntimeError(f"Unknown response run_id: {folder} line {lineno}")
        branch_records[record["branch_id"]].append((lineno, record))
        run_records[record["run_id"]].append((lineno, record))
    eligible = collections.defaultdict(list)
    branch_checks, actual_calls = [], []
    for bid, records in branch_records.items():
        keys = {group_key(plan_by_id[r["run_id"]]) for _, r in records}
        procs = {plan_by_id[r["run_id"]]["procedure"] for _, r in records}
        first_hashes = {sha(r["calls"][0]["text"].encode()) for _, r in records if r.get("calls")}
        first_call_hashes = {sha(json.dumps(r["calls"][0], sort_keys=True, ensure_ascii=False).encode())
                             for _, r in records if r.get("calls")}
        is_complete = len(records) == 7 and len({r["run_id"] for _, r in records}) == 7 and procs == PROCS and len(keys) == 1
        all_successful = all(r.get("status") == "ok" and all(c.get("ok") for c in r.get("calls", [])) for _, r in records)
        same_first = len(first_hashes) == 1 and len(first_call_hashes) == 1
        expected_call_counts = all(len(r.get("calls", [])) == (1 if plan_by_id[r["run_id"]]["procedure"] == "P0" else 2)
                                   for _, r in records)
        check = {"branch_id": bid, "records": len(records), "complete": is_complete,
                 "all_successful": all_successful, "same_first_text_and_call": same_first,
                 "expected_call_counts": expected_call_counts,
                 "first_text_sha256": next(iter(first_hashes)) if len(first_hashes) == 1 else None,
                 "finished": max(r["finished"] for _, r in records),
                 "first_line": min(n for n, _ in records), "last_line": max(n for n, _ in records)}
        if len(keys) == 1:
            check.update(key_object(next(iter(keys))))
        branch_checks.append(check)
        if is_complete and all_successful and same_first and expected_call_counts:
            eligible[next(iter(keys))].append(check)
        if records and records[0][1].get("calls"):
            actual_calls.append(records[0][1]["calls"][0])
        for _, record in records:
            actual_calls.extend(record.get("calls", [])[1:])
    selected = []
    duplicates = []
    for key, branches in sorted(eligible.items()):
        ordered = sorted(branches, key=lambda b: (dt.datetime.fromisoformat(b["finished"]), b["first_line"], b["branch_id"]))
        selected.append(ordered[0])
        if len(ordered) > 1:
            duplicates.append({**key_object(key), "complete_successful_branches": len(ordered),
                               "selected_earliest_branch": ordered[0]["branch_id"],
                               "branches": ordered})
    selected_bids = {r["branch_id"] for r in selected}
    selected_records = [r for _, r in rows if r["branch_id"] in selected_bids]
    latest = {}
    for _, record in rows:
        if record.get("status") == "ok":
            latest[record["run_id"]] = record
    latest_groups = collections.defaultdict(list)
    for rid, record in latest.items():
        latest_groups[group_key(plan_by_id[rid])].append(record)
    mixed_latest = []
    for key, records in latest_groups.items():
        bids = {r["branch_id"] for r in records}
        hashes = {sha(r["calls"][0]["text"].encode()) for r in records}
        if len(bids) != 1 or len(hashes) != 1:
            mixed_latest.append(key_object(key))
    params = []
    for path in sorted(directory.glob("manifest*.json")):
        manifest = json.loads(path.read_text())
        params.append({"file": path.name, "created": manifest["created"], "params": manifest["params"],
                       "branching": manifest["branching"], "seed": manifest["seed"], "repeats": manifest["repeats"],
                       "code_files": manifest["code_files"]})
    return {
        "folder": folder, "planned_rows": len(plan), "planned_groups": len(planned_groups),
        "raw_response_rows": len(rows), "unique_run_ids": len(run_records),
        "raw_branch_attempts": len(branch_records),
        "complete_successful_branch_attempts": sum(len(x) for x in eligible.values()),
        "selected_unique_complete_groups": len(selected), "selected_rows": len(selected_records),
        "remaining_groups": len(planned_groups) - len(selected),
        "duplicate_group_count": len(duplicates), "duplicate_record_count": len(rows) - len(run_records),
        "duplicate_groups": duplicates, "selection_policy": "earliest_completed_fully_successful_complete_branch",
        "selected_branches": selected, "branch_checks": branch_checks,
        "status_counts": dict(collections.Counter(r.get("status") for _, r in rows)),
        "observed_unique_calls_across_all_branch_attempts": len(actual_calls),
        "call_ok_counts": dict(collections.Counter(str(c.get("ok")) for c in actual_calls)),
        "finish_reason_counts": dict(collections.Counter(c.get("finish_reason") for c in actual_calls)),
        "returned_model_counts": dict(collections.Counter(c.get("model_returned") for c in actual_calls)),
        "reasoning_positive_call_count": sum(c.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0) > 0 for c in actual_calls),
        "max_completion_tokens": max(c.get("usage", {}).get("completion_tokens", 0) for c in actual_calls),
        "max_attempts": max(c.get("attempts", 0) for c in actual_calls),
        "selected_final_action_parse_failures": sum(parse_action(r["calls"][-1]["text"]) is None for r in selected_records),
        "legacy_latest_ok_mixed_branch_groups": mixed_latest,
        "manifest_summaries": params,
        "scored_runs_or_analysis_present_in_remote_snapshot": False,
    }

def main():
    for name in ("legacy_audit.json", "legacy_audit.md"):
        if (ROOT / name).exists():
            raise SystemExit(f"Refusing to overwrite existing audit: {ROOT / name}")
    metadata = json.loads((ROOT / "legacy_remote_tree.json").read_text())
    if metadata["commit"] != COMMIT or metadata["truncated"]:
        raise SystemExit("Incorrect or truncated remote tree")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        provenance = list(pool.map(fetch_verified, metadata["files"]))
    audits = [audit_folder(folder) for folder in FOLDERS]
    expected = [(31, 160, 0), (49, 160, 3), (39, 240, 0)]
    for audit, (complete, planned, duplicates) in zip(audits, expected):
        assert (audit["selected_unique_complete_groups"], audit["planned_groups"], audit["duplicate_group_count"]) == (complete, planned, duplicates)
        assert all(b["same_first_text_and_call"] for b in audit["branch_checks"])
        assert not audit["legacy_latest_ok_mixed_branch_groups"]
        assert audit["selected_final_action_parse_failures"] == 0
    result = {
        "audit_schema": "legacy-three-folder-branch-audit/v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "host": socket.gethostname(),
        "local_audit_root": str(ROOT), "repository": REPO, "commit": COMMIT,
        "scope": list(FOLDERS),
        "scope_note": "Only these three partially completed result folders were audited. This is not a full historical experiment audit or a recomputation of prior H04 results. No model APIs or credentials were accessed.",
        "selection_policy": "Select the earliest completed fully successful complete P0-P6 branch for each planned family/state/advice/repeat. Completion is max(finished) over seven rows; ties break by first JSONL line, then branch_id. Do not select individual rows by latest_ok.",
        "provenance": provenance, "folders": audits,
        "reasoning_totals": {"planned_groups": 400, "unique_complete_groups": 88, "remaining_groups": 312,
                             "minimum_remaining_model_calls_at_seven_calls_per_group": 2184},
        "conclusion": "Reported 52/160 reasoning-development progress counts execution attempts; the unique completed count is 49/160. All three duplicate groups were whole successful branches. Earliest-complete selection retains within-group shared-first-answer consistency; no mixed group is observed under the legacy latest_ok rule in this specific snapshot either.",
    }
    with (ROOT / "legacy_audit.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    rows = "\n".join(f"| `{a['folder']}` | {a['planned_groups']} | {a['raw_branch_attempts']} | {a['selected_unique_complete_groups']} | {a['duplicate_group_count']} | {a['remaining_groups']} |" for a in audits)
    md = f"""# 旧实验三个结果目录的分支计数审计

固定仓库：`{REPO}`，提交：`{COMMIT}`。本地机器：`{socket.gethostname()}`。

## 范围与方法

本次只审计下表三个部分完成目录，**不代表全历史实验审计，也没有复算此前 H04 的研究结果**。未调用任何模型 API，未读取密钥，未修改远端或原研究文件。10 个远端文件以原始字节追加保存到 `legacy_snapshot/`；每个文件均核对 Git blob SHA-1 和字节数与固定提交的 GitHub 树一致，并记录 SHA-256。

每个计划组为“案例家族 × 状态 × 建议 × 重复”，要求 P0–P6 七条记录完整、全部调用成功且共享首轮全文及首轮调用元数据。重复执行时选择**最早完成的完整成功分支**，按该分支七条记录中最晚 `finished` 排序；相同时按首个 JSONL 行号、再按 `branch_id`。不以答案正确与否选择，也不逐行执行 `latest_ok` 选择。完整分支和选择清单见 JSON。

## 计数

| 目录 | 计划组 | 已保存执行分支 | 唯一完整组 | 重复组 | 剩余组 |
|---|---:|---:|---:|---:|---:|
{rows}

`flash_think_branch_dev` 的 364 条响应只有 343 个唯一 `run_id`；52 是保存的分支执行次数，正确唯一完成数为 **49/160**。三个完整组各执行两次：

- F07 / decisive_change / aligned / repeat 1
- F07 / decisive_change / aligned / repeat 2
- F06 / missing / aligned / repeat 1

两个推理目录合计完成 **88/400** 个唯一组，余 **312 组**，按每组七次调用至少还需 **2,184 次新调用**，不含未来失败或重试。非推理目录单独保留，未与推理数据合并。

## 完整性

- 每个保存分支及每个入选分支的 P0–P6 首轮文本 SHA-256 与首轮调用元数据一致。
- 三个目录保存的实际调用数依次为 217、364、273；全部 `ok=true`、`finish_reason=stop`，每次仅一次请求尝试。
- 非推理目录推理 token 为零；两个推理目录每次调用均有推理 token。
- 入选响应的最终 action 均可按现有评分器接受的 JSON 结构解析；本审计没有按答案键计算正确率。
- 额外检查旧评分器 `latest_ok` 规则在这批具体数据上的输出，也未发现跨首轮混组；这不能证明该规则在失败重试等其他情形下安全。
- 三个远端目录在该提交中均无 `scored_runs.csv` 或分析输出。
- 两份相邻 manifest 和重复记录只说明多次启动及重复执行；本审计不推断它们发生的原因。

## 交付文件

- `legacy_audit.json`：计数、逐分支核查、确定的入选分支及文件校验值。
- `legacy_remote_tree.json`：固定提交的相关 GitHub 树条目。
- `legacy_snapshot/`：10 个经 Git blob 校验的只读原始快照。
- `audit_legacy_snapshot.py`：可复核的审计脚本；默认拒绝覆盖既有审计报告。
"""
    with (ROOT / "legacy_audit.md").open("x", encoding="utf-8") as f:
        f.write(md)
    print(json.dumps({"json": str(ROOT / "legacy_audit.json"), "markdown": str(ROOT / "legacy_audit.md"),
                      "verified_snapshots": len(provenance), "groups": [a["selected_unique_complete_groups"] for a in audits],
                      "remaining_reasoning_groups": 312}, ensure_ascii=False))

if __name__ == "__main__":
    main()
