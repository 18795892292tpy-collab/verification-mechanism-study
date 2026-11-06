"""Shared case-family utilities: load, apply state edits, render items.

The experiment harness imports this module, so the text that is checked here is the
text that models (and later people) see. Standard library only.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

STATES = ["base", "decisive_change", "irrelevant_change", "paraphrase", "missing"]
ADVICE = ["aligned", "flawed"]
DOMAINS = {"budget_procurement", "student_data", "evidence_adoption",
           "policy_compliance", "safety_operations"}
MISMATCH_TYPES = {"applicable_population", "time_version", "authorization_scope"}
DIFFICULTIES = {"explicit", "implicit", "incomplete", "hard"}
SPLITS = {"dev", "confirm"}
# Difficulty levers for the hard tier (see references/hard_tier.md).
LEVERS = {"long_dossier", "version_chain", "calculation", "multi_hop", "authority_chain", "persuasive_precedent"}


def load_family(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        fam = json.load(fh)
    fam["_path"] = str(path)
    return fam


def load_dir(folder: str | Path) -> list[dict]:
    return [load_family(p) for p in sorted(Path(folder).glob("*.json"))]


def evidence_status(state: str) -> str:
    return "absent" if state == "missing" else "present"


def state_sources(fam: dict, state: str) -> list[dict]:
    """Apply a state's edits to the base sources, in order."""
    sources = copy.deepcopy(fam["sources"])
    for edit in fam["states"][state].get("edits", []):
        op = edit["op"]
        if op == "replace":
            for s in sources:
                if s["id"] == edit["source_id"]:
                    s["text"] = edit["text"]
                    if "title" in edit:
                        s["title"] = edit["title"]
                    break
            else:
                raise KeyError(f"replace: no source {edit['source_id']}")
        elif op == "remove":
            before = len(sources)
            sources = [s for s in sources if s["id"] != edit["source_id"]]
            if len(sources) == before:
                raise KeyError(f"remove: no source {edit['source_id']}")
        elif op == "add":
            sources.append(copy.deepcopy(edit["source"]))
        elif op == "reorder":
            by_id = {s["id"]: s for s in sources}
            if sorted(edit["order"]) != sorted(by_id):
                raise ValueError("reorder: order must list every remaining source id once")
            sources = [by_id[i] for i in edit["order"]]
        elif op == "replace_all":
            sources = copy.deepcopy(edit["sources"])
        else:
            raise ValueError(f"unknown edit op {op}")
    return sources


def state_view(fam: dict, state: str) -> dict:
    st = fam["states"][state]
    return {
        "context": st.get("context", fam["context"]),
        "decision_question": st.get("decision_question", fam["decision_question"]),
        "options": st.get("options", fam["options"]),
        "sources": state_sources(fam, state),
    }


def render_item(fam: dict, state: str, advice: str) -> str:
    """Text shown to the decision maker: context, sources, advice memo, options.

    Contains no family id, state name, advice label, or other condition codes.
    """
    view = state_view(fam, state)
    memo = fam["states"][state]["advice"][advice]["text"]
    lines = ["【决策背景】", view["context"], "", "【需要决定的问题】", view["decision_question"], "",
             "【档案材料】"]
    for s in view["sources"]:
        lines.append(f"[{s['id']}] {s['title']}")
        lines.append(s["text"])
        lines.append("")
    lines += ["【AI 助手的建议备忘录】", memo, "", "【可选行动】"]
    for letter in sorted(view["options"]):
        lines.append(f"{letter}. {view['options'][letter]}")
    return "\n".join(lines)


def items(fam: dict):
    """Yield (state, advice) pairs for one family, in a fixed order."""
    for state in STATES:
        for advice in ADVICE:
            yield state, advice


def key_of(fam: dict, state: str) -> str:
    return fam["states"][state]["key_action"]


def advised_of(fam: dict, state: str, advice: str) -> str:
    return fam["states"][state]["advice"][advice]["recommends"]
