"""Read-only folder audit; no credentials, network, model calls or guessed prices.

python harness/audit_results.py results/flash_think_branch_dev [--out audit.json]
Optional --pricing JSON: currency, source, and models.<returned model> containing
prompt_uncached_per_million, prompt_cached_per_million, completion_per_million.
Prices must apply to every audited call (including its time band); otherwise omit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from branch_integrity import digest, select_run


def audit_folder(directory, pricing=None):
    directory = Path(directory)
    plan, selected, audit, records, manifests = select_run(directory)
    calls, seen = [], set()
    for line, record in records:
        for index, call in enumerate(record.get("calls") or []):
            # The runner copies its shared first-call object into every procedure.
            key = (record.get("branch_id"), digest(call))
            if audit["branching"] and index == 0 and record.get("branch_id"):
                if key in seen:
                    continue
                seen.add(key)
            calls.append(call)
    usage = [c.get("usage") or {} for c in calls]
    token_fields = ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
    tokens = {k: {"recorded_sum": sum(u[k] for u in usage if isinstance(u.get(k), int)),
                  "missing_calls": sum(not isinstance(u.get(k), int) for u in usage)} for k in token_fields}
    reasoning = [(u.get("completion_tokens_details") or {}).get("reasoning_tokens") for u in usage]
    recorded_cost, priced_calls = 0.0, 0
    if pricing and (not pricing.get("currency") or not pricing.get("source")):
        raise ValueError("Pricing requires currency and a verifiable source")
    for call, u in zip(calls, usage):
        rates = (pricing or {}).get("models", {}).get(call.get("model_returned"))
        if not rates or not isinstance(u.get("prompt_tokens"), int) or not isinstance(u.get("completion_tokens"), int):
            continue
        cached = u.get("prompt_cache_hit_tokens", (u.get("prompt_tokens_details") or {}).get("cached_tokens"))
        if not isinstance(cached, int):
            continue
        required = ("prompt_uncached_per_million", "prompt_cached_per_million", "completion_per_million")
        if not all(isinstance(rates.get(k), (float, int)) and rates[k] >= 0 for k in required):
            raise ValueError("Incomplete or invalid pricing rates")
        if not 0 <= cached <= u["prompt_tokens"]:
            raise ValueError("Invalid cache token accounting")
        recorded_cost += ((u["prompt_tokens"] - cached) * rates[required[0]] + cached * rates[required[1]]
                          + u["completion_tokens"] * rates[required[2]]) / 1_000_000
        priced_calls += 1
    hidden_attempts = sum(max(0, int(c.get("attempts") or 1) - 1) for c in calls)
    ambiguous = bool(audit["malformed_json_lines"] or audit.get("unknown_run_id_lines") or audit["manifest_conflicts"])
    ambiguous = ambiguous or any("incomplete_or_duplicate_membership" in b["reasons"] for b in audit.get("branches", []))
    cost_complete = bool(calls) and priced_calls == len(calls) and hidden_attempts == 0 and not ambiguous
    audit.update({
        "folder": directory.name, "planned_rows": len(plan), "selected_rows": len(selected),
        "status_counts": dict(Counter(r.get("status") for _, r in records)),
        "failed_records": sum(r.get("status") != "ok" for _, r in records),
        "observed_unique_calls": len(calls),
        "failed_calls": sum(c.get("ok") is not True for c in calls),
        "truncated_calls": sum(c.get("finish_reason") == "length" for c in calls),
        "reasoning_tokens": {"recorded_sum": sum(n for n in reasoning if isinstance(n, int)),
                             "positive_calls": sum(isinstance(n, int) and n > 0 for n in reasoning),
                             "missing_calls": sum(not isinstance(n, int) for n in reasoning)},
        "tokens": tokens, "unlogged_transport_retry_attempts": hidden_attempts,
        "cost": {"total": round(recorded_cost, 8) if cost_complete else None,
                 "recorded_call_subtotal": round(recorded_cost, 8) if priced_calls else None,
                 "priced_calls": priced_calls, "currency": (pricing or {}).get("currency"),
                 "source": (pricing or {}).get("source"),
                 "note": "null = NA; no inferred prices or token counts. Shared first calls counted once per branch. Unlogged retries or ambiguous record integrity prevent a complete expense claim."},
        "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [directory / "plan.csv", directory / "responses.jsonl", *sorted(directory.glob('manifest_*.json'))] if p.exists()},
        "manifest_params": [m["params"] for m in manifests],
    })
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+")
    parser.add_argument("--pricing")
    parser.add_argument("--out", help="new audit JSON path (never overwrites an existing file)")
    args = parser.parse_args()
    study = Path(__file__).resolve().parents[1]
    pricing = json.loads(Path(args.pricing).read_text()) if args.pricing else None
    output = {"schema": "legacy-folder-audit/v1", "folders": [audit_folder(Path(p) if Path(p).is_absolute() else study / p, pricing) for p in args.run_dirs]}
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.out:
        with Path(args.out).open("x", encoding="utf-8") as f:
            f.write(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
