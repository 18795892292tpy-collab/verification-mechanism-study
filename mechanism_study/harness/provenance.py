"""Offline identity checks shared by scoring, resume and pooled analysis.

Only bundled, hash-matched semantic source files are loaded. A runner.py hash is
provenance, not a semantic lock: integrity-only runner fixes remain compatible.
"""
from __future__ import annotations

import hashlib
import json
import runpy
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASELIB = HERE.parents[1] / ".claude/skills/verification-case-builder/scripts/caselib.py"


def matching_bytes(data, expected):
    """Match exact bytes or an explicitly reconstructible LF/CRLF representation."""
    if hashlib.sha256(data).hexdigest() == expected:
        return "exact"
    lf = data.replace(b"\r\n", b"\n")
    if b"\r" in lf:
        return None
    for label, candidate in (("reconstructed_LF", lf), ("reconstructed_CRLF", lf.replace(b"\n", b"\r\n"))):
        if hashlib.sha256(candidate).hexdigest() == expected:
            return label
    return None


def semantic_sources(manifest, error):
    """Resolve recorded source hashes to reviewed local sources, never arbitrary paths."""
    catalog = {"procedures.py": [HERE / "procedures.py", HERE / "legacy_sources/procedures_p0_p4.py"],
               "caselib.py": [CASELIB]}
    namespaces, hashes, evidence = {}, {}, {}
    for name, paths in catalog.items():
        expected = manifest.get("code_files", {}).get(name)
        if not isinstance(expected, str):
            raise error(f"Missing semantic source identity: code_files.{name}")
        for path in paths:
            data = path.read_bytes()
            match = matching_bytes(data, expected)
            if match:
                namespaces[name] = runpy.run_path(str(path))
                hashes[name] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
                evidence[name] = {"source": path.name, "recorded_sha256": expected, "matching": match}
                break
        else:
            raise error(f"Unverifiable semantic source {name}: no bundled source matches its recorded SHA-256")
    return namespaces, hashes, evidence


def condition_identity(manifest, error):
    """Comparable request/prompt/semantic-code condition, excluding case and runner hashes."""
    sources, hashes, evidence = semantic_sources(manifest, error)
    procedures = manifest.get("procedures")
    code = sources["procedures.py"]
    if not procedures or not set(procedures) <= set(code["N_CALLS"]):
        raise error("Manifest procedures are unsupported by its recorded semantic source")
    system = manifest.get("system")
    if system not in code["SYSTEMS"] or manifest.get("system_text") != code["SYSTEMS"][system]:
        raise error("Manifest system text does not match its recorded semantic source")
    review_chars = manifest.get("review_prompt_chars")
    if not isinstance(review_chars, dict):
        raise error("Missing review_prompt_chars; prompt condition cannot be verified")
    reviews = code["REVIEW"]
    for proc, length in review_chars.items():
        if proc not in reviews or length != len(reviews[proc]):
            raise error(f"review_prompt_chars differs from recorded source for {proc}")
    required = set(procedures) - {"P0"}
    if not required <= review_chars.keys():
        raise error("Missing planned review lengths in manifest")
    recorded = manifest.get("review_text_sha256")
    if recorded is not None:
        if not isinstance(recorded, dict) or not required <= recorded.keys():
            raise error("Incomplete review_text_sha256 in manifest")
        for proc, sha in recorded.items():
            if proc not in reviews or hashlib.sha256(reviews[proc].encode()).hexdigest() != sha:
                raise error(f"review_text_sha256 differs from recorded source for {proc}")
    identity = {k: manifest.get(k) for k in ("backend", "base_url", "params", "system", "system_text", "branching", "procedures")}
    identity.update(semantic_code_sha256=hashes,
                    review_text_sha256={p: hashlib.sha256(reviews[p].encode()).hexdigest() for p in sorted(required)},
                    review_prompt_chars={p: len(reviews[p]) for p in sorted(required)})
    return identity, sources, evidence


def normalized_plan(plan, error):
    """Use exactly the runner's read_plan integer normalization before hashing."""
    try:
        return [dict(row, repeat=int(row["repeat"]), order=int(row["order"])) for row in plan]
    except (KeyError, TypeError, ValueError) as exc:
        raise error("Plan lacks valid repeat/order integers") from exc


def verify_run_identity(plan, records, manifests, error):
    canonical = normalized_plan(plan, error)
    current_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    identities, source_sets, source_evidence = [], [], []
    for manifest in manifests:
        if "integrity_version" in manifest:
            if manifest["integrity_version"] != 1 or not {"plan_sha256", "review_text_sha256"} <= manifest.keys():
                raise error("Incomplete or unsupported versioned integrity manifest; refusing a silent legacy downgrade")
        if "plan_sha256" in manifest and manifest["plan_sha256"] != current_hash:
            raise error("plan_sha256 mismatch: stored plan labels, order or run IDs have changed")
        identity, sources, evidence = condition_identity(manifest, error)
        identities.append(identity)
        source_sets.append(sources)
        source_evidence.append(evidence)
    if any(identity != identities[0] for identity in identities[1:]):
        raise error("Conflicting prompt/request/semantic-code conditions in manifests")
    by_id = {row["run_id"]: row for row in plan}
    if len(by_id) != len(plan):
        raise error("Duplicate run_id in plan")
    code = source_sets[0]["procedures.py"]
    for line, record in records:
        row = by_id.get(record.get("run_id"))
        if row is None:
            continue  # The branch audit explicitly reports unknown record IDs.
        calls = record.get("calls") or []
        messages = calls[0].get("messages") if calls else None
        if not isinstance(messages, list) or len(messages) != 2 or messages[0] != {"role": "system", "content": identities[0]["system_text"]}:
            raise error(f"Raw system message does not match manifest at line {line}")
        if len(calls) > 1:
            proc = row["procedure"]
            if proc not in code["REVIEW"]:
                raise error(f"Unexpected review call for {proc} at line {line}")
            expected = [{"role": "assistant", "content": calls[0].get("text")},
                        {"role": "user", "content": code["REVIEW"][proc]}]
            if calls[1].get("messages_appended") != expected:
                raise error(f"Raw review text/procedure identity mismatch at line {line}")
    return {"plan_sha256": current_hash,
            "manifests_with_plan_hash": sum("plan_sha256" in m for m in manifests),
            "legacy_manifests_without_plan_hash": sum("plan_sha256" not in m for m in manifests),
            "condition": identities[0], "semantic_source_evidence": source_evidence,
            "case_binding": "not_verified_without_case_files",
            "legacy_plan_limit": "Raw messages can bind family/state/advice/procedure; legacy repeat/order identifiers were not in messages and cannot be independently recovered without a recorded plan hash."}


def verify_case_binding(plan, records, manifests, families, error):
    """Bind every recorded first prompt to its plan labels and the frozen case bytes."""
    sources, _, _ = semantic_sources(manifests[0], error)
    code, case = sources["procedures.py"], sources["caselib.py"]
    planned_families = {row["family_id"] for row in plan}
    declared_files = manifests[0].get("case_files")
    if not isinstance(declared_files, dict) or not declared_files:
        raise error("Missing frozen case-file identities in manifest")
    by_name = {Path(family["_path"]).name: family_id for family_id, family in families.items()}
    if not declared_files.keys() <= by_name.keys():
        raise error("Manifest case files are missing from scoring cases")
    declared_families = {by_name[name] for name in declared_files}
    if planned_families != declared_families:
        raise error("Plan family membership differs from manifest case_files")
    repeats = manifests[0].get("repeats")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise error("Missing or invalid manifest repeats; full plan membership cannot be verified")
    canonical = normalized_plan(plan, error)
    actual_shape = Counter((r["family_id"], r["state"], r["advice"], r["procedure"], r["repeat"]) for r in canonical)
    expected_shape = Counter((family_id, state, advice, proc, repeat)
        for family_id in declared_families
        for state, advice in case["items"](families[family_id])
        for proc in manifests[0]["procedures"] for repeat in range(1, repeats + 1))
    if actual_shape != expected_shape or sorted(r["order"] for r in canonical) != list(range(len(canonical))):
        raise error("Plan membership/order is inconsistent with frozen cases, procedures and repeats")
    evidence, prompts, labels_by_prompt = {}, {}, defaultdict(set)
    for family_id in planned_families:
        if family_id not in families:
            raise error(f"Planned family {family_id} is absent from scoring cases")
        path = Path(families[family_id]["_path"])
        data = path.read_bytes()
        matches = []
        for manifest in manifests:
            expected = manifest.get("case_files", {}).get(path.name)
            match = matching_bytes(data, expected)
            if not match:
                raise error(f"Case file identity mismatch or missing manifest membership: {family_id}/{path.name}")
            matches.append(match)
        evidence[family_id] = {"file": path.name, "matching": matches,
                               "scoring_file_sha256": hashlib.sha256(data).hexdigest()}
    for row in plan:
        try:
            rendered = case["render_item"](families[row["family_id"]], row["state"], row["advice"])
            prompts[row["run_id"]] = code["first_messages"](rendered, manifests[0]["system"])
            labels_by_prompt[json.dumps(prompts[row["run_id"]], sort_keys=True, ensure_ascii=False)].add(
                (row["family_id"], row["state"], row["advice"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise error(f"Invalid case/state/advice binding for run {row['run_id']}") from exc
    for line, record in records:
        if record.get("run_id") not in prompts:
            continue
        calls = record.get("calls") or []
        if not calls or calls[0].get("messages") != prompts[record["run_id"]]:
            raise error(f"Raw first prompt disagrees with plan family/state/advice at line {line}")
        if any("plan_sha256" not in m for m in manifests):
            key = json.dumps(prompts[record["run_id"]], sort_keys=True, ensure_ascii=False)
            if len(labels_by_prompt[key]) != 1:
                raise error(f"Ambiguous legacy prompt-to-label identity at line {line}; no recorded plan hash")
    return evidence
