"""Run case items under procedures P0-P3 against an OpenAI-compatible chat API (or a mock).

Usage (from D:\\lunweng\\mechanism_study):
  python harness/runner.py --cases cases/dev --out results/dev_mock --backend mock --repeats 2
  python harness/runner.py --cases cases/dev --out results/dev_deepseek --repeats 2

Credentials come from mechanism_study/.env (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL) or the
environment. The key is never printed or logged. Requests carry only chat messages: no case,
state, advice, or procedure codes. Re-running the same command resumes unfinished runs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SKILL_SCRIPTS = STUDY.parent / ".claude" / "skills" / "verification-case-builder" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
sys.path.insert(0, str(HERE))
import caselib as cl  # noqa: E402
import procedures as pr  # noqa: E402
from branch_integrity import DirectoryLock, IntegrityError, digest, select_run, validate_resume  # noqa: E402
from provenance import verify_case_binding  # noqa: E402

if not sys.stdout.isatty():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PLAN_FIELDS = ["run_id", "order", "family_id", "state", "advice", "procedure", "repeat"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


# ---------------------------------------------------------------- backends
class OpenAICompatible:
    def __init__(self, base_url: str, api_key: str, model: str, max_tokens: int,
                 temperature: float, timeout: float = 180.0):
        import requests  # installed in the project venv
        self.requests = requests
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.model, self.max_tokens, self.temperature, self.timeout = model, max_tokens, temperature, timeout

    def params(self) -> dict:
        return {"model": self.model, "max_tokens": self.max_tokens, "temperature": self.temperature}

    def chat(self, messages: list[dict]) -> dict:
        body = {"model": self.model, "messages": messages, "max_tokens": self.max_tokens,
                "temperature": self.temperature, "stream": False}
        delay = 2.0
        for attempt in range(6):
            t0 = time.perf_counter()
            try:
                r = self.requests.post(self.url, headers=self.headers, json=body, timeout=self.timeout)
                latency = time.perf_counter() - t0
                if r.status_code == 200:
                    data = r.json()
                    choice = data["choices"][0]
                    usage = data.get("usage") or {}
                    return {"ok": True, "text": choice["message"].get("content") or "",
                            "finish_reason": choice.get("finish_reason"),
                            "model_returned": data.get("model"), "usage": usage,
                            "latency_s": round(latency, 3), "attempts": attempt + 1}
                retryable = r.status_code in (408, 409, 429) or r.status_code >= 500
                err = f"HTTP {r.status_code}: {r.text[:300]}"
            except (self.requests.Timeout, self.requests.ConnectionError) as exc:
                retryable, err = True, f"{type(exc).__name__}: {str(exc)[:200]}"
            if not retryable or attempt == 5:
                return {"ok": False, "error": err, "attempts": attempt + 1}
            time.sleep(delay + random.random())
            delay = min(delay * 2, 60)
        return {"ok": False, "error": "unreachable"}


class Mock:
    """Offline stand-in for pipeline tests. Its answers mean nothing."""

    def __init__(self, max_tokens: int, seed: int = 0):
        self.max_tokens = max_tokens
        self.rng = random.Random(seed)
        self.lock = threading.Lock()

    def params(self) -> dict:
        return {"model": "mock", "max_tokens": self.max_tokens, "temperature": None}

    def chat(self, messages: list[dict]) -> dict:
        user = messages[1]["content"]
        letters = re.findall(r"^([A-E])\. ", user, flags=re.M)
        memo = re.search(r"建议：选择 ([A-E])", user)
        with self.lock:
            r = self.rng.random()
            if memo and r < 0.55:
                act = memo.group(1)
            else:
                act = self.rng.choice(letters or ["A"])
            cites = sorted(set(re.findall(r"\[(S\d+)\]", user)))[:3]
            out_tokens = self.rng.randint(200, 700)
        text = ("模拟分析。\n```json\n" + json.dumps(
            {"action": act, "follow_advice": bool(memo and memo.group(1) == act), "cited_sources": cites,
             "rationale": "模拟", "confidence": 3}, ensure_ascii=False) + "\n```")
        return {"ok": True, "text": text, "finish_reason": "stop", "model_returned": "mock",
                "usage": {"prompt_tokens": len(user) // 2, "completion_tokens": out_tokens},
                "latency_s": 0.0, "attempts": 1}


# ---------------------------------------------------------------- plan
def build_plan(fams, procedures, repeats, seed) -> list[dict]:
    rows = []
    for fam in fams:
        for state, advice in cl.items(fam):
            for proc in procedures:
                for rep in range(1, repeats + 1):
                    rows.append({"run_id": uuid.uuid4().hex[:12], "family_id": fam["family_id"],
                                 "state": state, "advice": advice, "procedure": proc, "repeat": rep})
    random.Random(seed).shuffle(rows)
    for i, r in enumerate(rows):
        r["order"] = i
    return rows


def read_plan(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return [dict(r, repeat=int(r["repeat"]), order=int(r["order"])) for r in csv.DictReader(fh)]


# ---------------------------------------------------------------- execution
def execute(row, fams_by_id, backend, system="strong") -> dict:
    fam = fams_by_id[row["family_id"]]
    item = cl.render_item(fam, row["state"], row["advice"])
    msgs = pr.first_messages(item, system)
    rec = {"run_id": row["run_id"], "started": now(), "calls": []}
    c1 = backend.chat(msgs)
    rec["calls"].append({"messages": msgs, **c1})
    if not c1["ok"]:
        rec.update(status="error", finished=now())
        return rec
    if pr.N_CALLS[row["procedure"]] == 2:
        msgs2 = pr.review_messages(msgs, c1["text"], row["procedure"])
        c2 = backend.chat(msgs2)
        # Store only the new turn for call 2; the full context is call 1 + this turn.
        rec["calls"].append({"messages_appended": msgs2[len(msgs):], **c2})
        if not c2["ok"]:
            rec.update(status="error", finished=now())
            return rec
    rec.update(status="ok", finished=now())
    return rec


def execute_branch(group, fams_by_id, backend, system="strong") -> list[dict]:
    """Branching design: one shared first call; P0 is that answer, and every two-call
    procedure reviews the same first answer. Procedure differences are then purely the effect
    of the review call (repair or damage), with first-pass sampling noise removed."""
    row0 = group[0]
    fam = fams_by_id[row0["family_id"]]
    msgs = pr.first_messages(cl.render_item(fam, row0["state"], row0["advice"]), system)
    branch_id = uuid.uuid4().hex[:12]
    started = now()
    c1 = backend.chat(msgs)
    first = {"messages": msgs, **c1}
    recs = []
    for row in sorted(group, key=lambda r: r["procedure"]):
        rec = {"run_id": row["run_id"], "branch_id": branch_id, "started": started, "calls": [first]}
        if not c1["ok"]:
            rec.update(status="error", finished=now())
        elif pr.N_CALLS[row["procedure"]] == 2:
            msgs2 = pr.review_messages(msgs, c1["text"], row["procedure"])
            c2 = backend.chat(msgs2)
            rec["calls"].append({"messages_appended": msgs2[len(msgs):], **c2})
            rec.update(status="ok" if c2["ok"] else "error", finished=now())
        else:
            rec.update(status="ok", finished=now())
        recs.append(rec)
    return recs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", choices=["openai", "mock"], default="openai")
    ap.add_argument("--procedures", default="P0,P1,P2,P3,P4")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--families", help="comma-separated subset of family ids")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--limit", type=int, help="run only the first N planned runs (smoke test)")
    ap.add_argument("--confirm-manifest", help="required for confirmation-split cases")
    ap.add_argument("--model", help="override LLM_MODEL")
    ap.add_argument("--timeout", type=float, default=180.0,
                    help="seconds per request; raise it for reasoning mode with a high --max-tokens")
    ap.add_argument("--system", choices=sorted(pr.SYSTEMS), default="strong",
                    help="system prompt: strong (default comparator) or plain (secondary factor)")
    ap.add_argument("--branching", action="store_true",
                    help="share one first call per item x repeat across all procedures (P0 = that answer)")
    args = ap.parse_args()

    cases_dir = (STUDY / args.cases) if not Path(args.cases).is_absolute() else Path(args.cases)
    out = (STUDY / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    try:
        with DirectoryLock(out):
            return run_locked(args, cases_dir, out)
    except IntegrityError as exc:
        print(f"Integrity check failed: {exc}")
        return 3


def run_locked(args, cases_dir, out):
    """All plan/manifest/response writes happen while the directory lock is held."""
    fams = cl.load_dir(cases_dir)
    if args.families:
        keep = set(args.families.split(","))
        fams = [f for f in fams if f["family_id"] in keep]
    if not fams:
        print("No families to run.")
        return 1
    if any(f["split"] == "confirm" for f in fams):
        if not args.confirm_manifest:
            print("Confirmation cases need --confirm-manifest (frozen hashes).")
            return 1
        man = json.loads(Path(args.confirm_manifest).read_text(encoding="utf-8"))
        for f in fams:
            name = Path(f["_path"]).name
            if man["files"].get(name) != sha256_file(Path(f["_path"])):
                print(f"Frozen hash mismatch for {name}; refusing to run.")
                return 1
    from check_cases import check_family
    bad = {f["family_id"]: check_family(f)[0] for f in fams}
    bad = {k: v for k, v in bad.items() if v}
    if bad:
        print(f"Checker errors in {sorted(bad)}; fix them before running.")
        return 1

    if args.backend == "mock":
        backend = Mock(args.max_tokens, seed=args.seed)
    else:
        env = load_env(STUDY / ".env")
        missing = [k for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL") if not env.get(k) and not (k == "LLM_MODEL" and args.model)]
        if missing:
            print(f"Missing {missing}. Create {STUDY / '.env'} from .env.example.")
            return 1
        backend = OpenAICompatible(env["LLM_BASE_URL"], env["LLM_API_KEY"], args.model or env["LLM_MODEL"],
                                   args.max_tokens, args.temperature, timeout=args.timeout)

    procedures = args.procedures.split(",")
    if len(set(procedures)) != len(procedures) or not set(procedures) <= set(pr.N_CALLS):
        raise IntegrityError("Unknown or duplicate procedures")
    if args.branching and "P0" not in procedures:
        raise IntegrityError("Branching plan must contain its shared P0 answer")
    if args.repeats < 1 or args.concurrency < 1 or (args.limit is not None and args.limit < 1):
        raise IntegrityError("Repeats, concurrency and limit must be positive")
    plan_path, resp_path = out / "plan.csv", out / "responses.jsonl"
    resuming = plan_path.exists()
    if not resuming and (resp_path.exists() or list(out.glob("manifest_*.json"))):
        raise IntegrityError("Output has responses/manifests but no plan")
    if resuming:
        plan = read_plan(plan_path)
        print(f"Resuming plan with {len(plan)} runs")
    else:
        plan = build_plan(fams, procedures, args.repeats, args.seed)
    manifest = {
        "created": now(), "backend": args.backend, "params": backend.params(),
        "base_url": (load_env(STUDY / ".env").get("LLM_BASE_URL") if args.backend == "openai" else None),
        "procedures": procedures, "repeats": args.repeats, "seed": args.seed,
        "system": args.system, "system_text": pr.SYSTEMS[args.system], "branching": args.branching,
        "case_files": {Path(f["_path"]).name: sha256_file(Path(f["_path"])) for f in fams},
        "code_files": {p.name: sha256_file(p) for p in [HERE / "runner.py", HERE / "procedures.py",
                                                       SKILL_SCRIPTS / "caselib.py"]},
        "review_prompt_chars": {k: len(v) for k, v in pr.REVIEW.items()},
        "python": sys.version.split()[0],
        "integrity_version": 1,
        "review_text_sha256": {k: digest(v) for k, v in pr.REVIEW.items()},
        "plan_sha256": digest(plan),
    }
    if resuming:
        validate_resume(out, manifest, plan, build_plan(fams, procedures, args.repeats, args.seed))
        _, selected, audit, records, manifests = select_run(out)
        if audit["malformed_json_lines"] or audit.get("unknown_run_id_lines"):
            raise IntegrityError("Malformed or unknown response records; audit before resuming")
        verify_case_binding(plan, records, manifests, {f["family_id"]: f for f in fams}, IntegrityError)
        finished = set(selected)
    else:
        finished = set()
        with open(plan_path, "x", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=PLAN_FIELDS)
            w.writeheader()
            w.writerows(plan)
    # Use exclusive creation and microseconds: quick restarts must not overwrite provenance.
    with (out / f"manifest_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json").open("x", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    todo = [r for r in sorted(plan, key=lambda r: r["order"]) if r["run_id"] not in finished]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(finished)} done, {len(todo)} to run, backend={args.backend}, model={backend.params()['model']}")
    fams_by_id = {f["family_id"]: f for f in fams}
    lock = threading.Lock()
    n_ok = n_err = 0
    t0 = time.time()
    if args.branching:
        # Retry the whole group only when no complete successful branch exists.
        # Scoring uses that same atomic branch selection, never per-procedure latest_ok.
        groups = {}
        for r in sorted(plan, key=lambda r: r["order"]):
            groups.setdefault((r["family_id"], r["state"], r["advice"], r["repeat"]), []).append(r)
        jobs = [g for g in groups.values() if any(r["run_id"] not in finished for r in g)]
        if args.limit:
            jobs = jobs[: args.limit]
        print(f"branching: {len(jobs)} item x repeat groups to run")
    else:
        jobs = [[r] for r in todo]
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool, open(resp_path, "a", encoding="utf-8") as fh:
        if args.branching:
            futs = {pool.submit(execute_branch, g, fams_by_id, backend, args.system): g for g in jobs}
        else:
            futs = {pool.submit(lambda r: [execute(r, fams_by_id, backend, args.system)], g[0]): g for g in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            recs = fut.result()
            with lock:
                for rec in recs:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
            n_ok += sum(rec["status"] == "ok" for rec in recs)
            n_err += sum(rec["status"] != "ok" for rec in recs)
            if i % 25 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} jobs, records ok={n_ok} err={n_err} elapsed={time.time() - t0:.0f}s", flush=True)
    print(f"Finished: ok={n_ok} err={n_err}. Re-run the same command to retry errors.")
    return 0 if n_err == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
