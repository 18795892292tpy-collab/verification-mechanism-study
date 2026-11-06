# Case family schema (version 0.1)

One JSON file per family, UTF-8, named `<family_id>.json`.

```jsonc
{
  "schema_version": "0.1",
  "family_id": "F01",                    // unique, short; never shown to models
  "split": "dev",                        // "dev" | "confirm"
  "domain": "student_data",              // budget_procurement | student_data | evidence_adoption | policy_compliance | safety_operations
  "mismatch_type": "authorization_scope",// applicable_population | time_version | authorization_scope
  "difficulty": "implicit",              // explicit | implicit | incomplete
  "language": "zh",
  "title": "阅读测评平台请求家长手机号",
  "context": "决策背景，1-3 句，例如决定日期、决策者身份。",
  "decision_question": "需要决定的问题。",
  "options": {"A": "...", "B": "...", "C": "...", "D": "暂停并上报……"},
  "escalate_option": "D",                // the pause / escalate option letter

  "sources": [                           // base dossier, in display order
    {"id": "S1", "title": "……", "text": "……"}
  ],

  "decisive_fact": {
    "source_id": "S2",
    "base_quote": "verbatim substring of base S2",
    "changed_quote": "verbatim substring of S2 in decisive_change",
    "why_decisive": "一句话说明这个事实为什么决定行动。"
  },
  "irrelevant_facts": [
    {"source_id": "S5", "quote": "verbatim substring of base S5", "why_irrelevant": "……"}
  ],
  "pause_condition": "什么情况下信息不足、应当暂停或上报。",

  "states": {
    "base": {
      "edits": [],
      "key_action": "B",
      "required_sources": ["S1", "S2", "S3"],
      "permitted_sources": ["S1", "S2", "S3", "S4"],
      "answer_basis": "从材料推出答案的完整说明。",
      "basis_quotes": [{"source_id": "S2", "quote": "verbatim substring"}],
      "advice": {
        "aligned": {"recommends": "B", "cites": ["S1", "S2"], "text": "建议：……"},
        "flawed":  {"recommends": "A", "cites": ["S2", "S4"], "misapplied_source": "S2",
                     "how_misapplied": "把仅覆盖三项字段的批准当成覆盖全部请求字段。",
                     "text": "建议：……"}
      }
    },
    "decisive_change":   { "edits": [{"op": "replace", "source_id": "S2", "text": "……"}], "...": "same fields as base" },
    "irrelevant_change": { "edits": [{"op": "replace", "source_id": "S5", "text": "……"}, {"op": "reorder", "order": ["S1","S2","S3","S5","S4"]}] },
    "paraphrase":        { "edits": [{"op": "replace_all", "sources": [ {"id": "S1", "title": "……", "text": "……"} ]}],
                           "context": "optional reworded context", "decision_question": "optional reworded question" },
    "missing":           { "edits": [{"op": "remove", "source_id": "S2"}], "key_action": "D" }
  },

  "expert_review": {"status": "pending", "reviewers": [], "notes": ""},
  "provenance": {"drafted_by": "Claude (AI draft)", "date": "2026-11-05"},
  "revision_log": [],
  "notes": ""
}
```

## Edit operations

| op | fields | effect |
|---|---|---|
| `replace` | `source_id`, `text`, optional `title` | replace one source's text |
| `remove` | `source_id` | drop a source |
| `add` | `source` (object) | append a new source |
| `reorder` | `order` (list of ids) | display order; must list every remaining id |
| `replace_all` | `sources` (list) | paraphrase: same ids, reworded text |

Edits apply to the base sources in order. A state may also override `context`,
`decision_question`, or `options` (paraphrase only; option letters and meanings must not
change).

## Constraints checked by `check_cases.py`

Errors (must fix):
- missing fields, unknown enum values, duplicate source ids;
- key action or advice action not in `options`; escalate option missing;
- required or permitted source not present in the rendered state; required not within permitted;
- a `basis_quotes` quote, decisive quote, or irrelevant quote not found verbatim;
- `decisive_change` edits any source other than the decisive source, or its key equals the base key;
- `irrelevant_change` edits a non-irrelevant source, or its key or required sources differ from base;
- `paraphrase` changes the id set or the key;
- `missing` keeps the decisive source, or its key is not the escalate option;
- aligned advice does not recommend the key; flawed advice recommends the key;
- an advice cites no source, or cites a source absent from that state;
- flawed advice `misapplied_source` absent from that state (except `missing`, where it must be a present source);
- status-revealing words in a memo or in any text shown to the model.

Warnings (fix or justify in `notes`):
- aligned/flawed memo length ratio outside 0.75-1.33;
- fewer than 4 or more than 8 sources;
- decisive quote shares a source with the conclusion sentence of the aligned memo verbatim (answer given away);
- `expert_review.status` is not `approved` (always warned for AI drafts).
