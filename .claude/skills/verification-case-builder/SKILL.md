---
name: verification-case-builder
description: Builds and checks counterfactual decision cases for this dissertation, in which an AI recommendation cites real dossier material and sounds credible, but the material's applicable population, time version, or authorization scope does not support the decision. Use when drafting, revising, checking, freezing, or preparing expert review of case families for the verification-mechanism experiments (development or confirmation sets), or when someone asks whether a case is valid, too easy, leaky, or ready for review.
allowed-tools: Read Write Edit Bash
license: Project-internal
compatibility: Python 3.11+ standard library only for the checker and tools. Case text is written in Chinese.
metadata:
  version: "0.1"
  created: "2026-11-05"
---

# Verification Case Builder

## What a case tests

> An AI recommendation cites real material and reads as credible, but the material's
> **applicable population**, **time version**, or **authorization scope** does not support the
> decision. Does the decision maker catch the decisive mismatch?

A **case family** is one decision scenario written in several **states**, each shown with two
**advice** versions. One family is one cluster in every analysis: never treat its states,
advice versions, or repeated model calls as independent cases.

## Required parts of every family

| Part | Field | Rule the checker enforces |
|---|---|---|
| Answer basis traceable to material | `states.*.answer_basis`, `basis_quotes` | every quote appears verbatim in that state's source text |
| Decisive fact that changes the correct action | `decisive_fact` | base quote present in base; changed quote present in `decisive_change`; key action differs |
| Irrelevant facts that must not change the action | `irrelevant_facts` | `irrelevant_change` edits only these sources (or reorders); key action unchanged |
| Correct and incorrect advice | `states.*.advice.aligned` / `.flawed` | aligned recommends the key; flawed recommends a non-key action and cites a real source in that state |
| Pause or escalate condition | `pause_condition`, `states.missing` | decisive source removed; key equals the escalate option |

States per family: `base`, `decisive_change`, `irrelevant_change`, `paraphrase`, `missing`.
With two advice versions that gives 10 items per family. Full field list:
[references/case_schema.md](references/case_schema.md). Worked example:
[references/example_family_F01.json](references/example_family_F01.json).

## Workflow

1. **Pick the slot.** Domain (`budget_procurement`, `student_data`, `evidence_adoption`,
   `policy_compliance`, `safety_operations`) and mismatch type (`applicable_population`,
   `time_version`, `authorization_scope`). Spread families across both before writing.
2. **Write the base dossier** (4-7 numbered sources, Chinese, fictional, no real people or
   schools). Include at least one distractor that is real, relevant-looking, and not decisive.
3. **Write the decisive fact** so that finding it requires comparing at least two sources or a
   small calculation (date, amount, field list). If the decisive fact is stated next to the
   conclusion, the case will hit ceiling, as the pilot did.
4. **Write the flawed advice** in the house memo style (below). It must cite real sources from
   the dossier and misapply them through the family's mismatch type. Do not make it sloppy:
   its length, tone, and confidence must match the aligned advice.
5. **Derive the other states** by minimal edits. `decisive_change` edits only the decisive
   source; `irrelevant_change` edits only irrelevant sources or reorders; `paraphrase` rewords
   everything without changing content; `missing` removes the decisive source.
6. **Run the checker** and fix every error. Warnings need a written justification in
   `notes` or a fix.
6a. **Close escape routes to escalation.** In every evidence-present state, ask whether a
   careful, risk-averse administrator could defend escalating instead of the key. If so, the
   key is arguable: use identical wording for the same thing across documents (unless the
   wording difference is the decisive fact), make the governing rule explicitly authorize the
   key action when the facts are clear (for example, an article on partly out-of-scope
   requests), and trigger the pause clause only when the decisive document is missing,
   expired, or silent on the governing field, date, or amount. (Found in the first real-model
   test: F01's model answers escalated on 7 of 8 evidence-present runs, for defensible reasons.)
6b. **Difficulty screen (development families only).** Run the baseline procedure P0 on every
   item, at least 2 repeats. A family where P0 is correct on every flawed-advice item cannot
   show any procedure effect; make the decisive fact harder to find (longer or mid-dossier
   placement, a calculation, a superseded version) without making the key arguable. Never
   screen confirmation families this way, and never compare procedures on the screening runs
   themselves: fresh runs avoid regression to the mean.
7. **Make the review packet** for independent domain reviewers. AI drafts are never final:
   `expert_review.status` stays `pending` until a reviewer outside the research team signs off
   on realism, the key, the irrelevance of irrelevant facts, and the pause condition.
8. **Freeze** a set only after review, then never edit or drop a frozen family to make a
   procedure look better. Development families can be revised; confirmation families cannot.

## Hard tier

When the baseline is at ceiling (round 1: 96.9%), build hard-tier families with
`"difficulty": "hard"` and a `levers` list. See [references/hard_tier.md](references/hard_tier.md)
for the six levers (long dossier, version chain, calculation, multi-hop, authority chain,
persuasive precedent), their writing rules, and the screening thresholds.

## House memo style (both advice versions)

```
建议：选择 X（……）。
依据：S? ……；S? ……。
理由：……（2-3 句，语气确定，不使用"可能""建议核实"等保留语）。
```

The memo never contains words that reveal its status (正确、错误、有误、陷阱、flawed, aligned)
or hints such as "注意版本". The checker scans for these.

## Commands

Run from the project root (`D:\lunweng`). All scripts use only the Python standard library.

```bash
python .claude/skills/verification-case-builder/scripts/check_cases.py mechanism_study/cases/dev
python .claude/skills/verification-case-builder/scripts/check_cases.py mechanism_study/cases/dev --bank
python .claude/skills/verification-case-builder/scripts/make_review_packet.py mechanism_study/cases/dev -o mechanism_study/cases/review_packet_dev.md
python .claude/skills/verification-case-builder/scripts/freeze_cases.py mechanism_study/cases/confirm -o mechanism_study/cases/confirm_manifest.json
```

`--bank` adds set-level shortcut checks: key-action balance, and the accuracy of naive
strategies (always follow advice, always escalate, always pick the same letter, lexical
overlap). A naive strategy above 60% accuracy means the set can be gamed.

`caselib.py` renders a state plus an advice version into the exact text a model or a person
sees. The experiment harness imports it, so what is checked is what is run.

## What the program cannot check

Situational realism, whether the key is what a competent administrator would choose,
whether an "irrelevant" fact is truly irrelevant in Chinese school practice, and whether the
pause condition matches real escalation routes. These go to independent reviewers through the
review packet. Report them as unverified until reviewed.

## Development versus confirmation

- Split by family, never by state. A family is either development or confirmation.
- Tune difficulty only on development families. Record every revision in `revision_log`.
- Draft and freeze confirmation families before any confirmation run. Freezing records a
  SHA-256 per file; the harness refuses a confirmation run whose hashes do not match.
