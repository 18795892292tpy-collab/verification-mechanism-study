# Verification mechanism study (round after draft v3)

Question: does source verification help because it checks the decisive evidence, or only
because it adds one more round of computation?

| Folder | Contents |
|---|---|
| `literature/` | competing mechanisms, distinguishing predictions, verified references |
| `cases/dev/` | development case families (AI drafts, expert review pending) |
| `cases/` | review packet and blind answer sheet for independent reviewers |
| `harness/` | `procedures.py` (P0-P6 prompts), `runner.py`, `scorer.py`, `screen_report.py` |
| `analysis/` | analysis plan, analysis script, power simulations |
| `results/` | raw responses, scored runs, summary tables (one folder per run) |
| `report/` | measured report and pilot re-check |

## Procedures

| | Calls | Second-call instruction |
|---|---|---|
| P0 strong baseline | 1 | none |
| P1 free re-check | 2 | think the decision through again from scratch |
| P2 generic checklist | 2 | completeness, reasoning, assumptions, consistency, information sufficiency |
| P3 source applicability | 2 | applicable population, time version, authorization scope, evidence support, information sufficiency |
| P4 cue-only control (exploratory) | 2 | P1 plus one sentence naming the three mismatch types, no checking asked |
| P5 (exploratory) | 2 | P3 without item 5 (information sufficiency) |
| P6 (exploratory) | 2 | P2 without item 5 |

Same system prompt, item text, answer format, and output cap (4,000 tokens per call; raised from 1,500 after the harness pilot showed 4-18% of review calls truncated before the answer) for all.
Review prompts P1-P4 are 228-257 Chinese characters long (P5 228, P6 199), so length is roughly matched. P4 was added
after the literature line showed that without it a P3 advantage cannot be separated from
instruction cueing (P3's wording names the error types).

## Running (from this folder, with `..\.venv\Scripts\python.exe`)

```bash
python harness/runner.py --cases cases/dev --out results/dev_mock --backend mock --repeats 2
python harness/runner.py --cases cases/dev --out results/dev_deepseek --repeats 2 --limit 8
python harness/runner.py --cases cases/dev --out results/dev_deepseek --repeats 2
python harness/scorer.py results/dev_deepseek --cases cases/dev
python analysis/analyze.py results/dev_deepseek/scored_runs.csv --out results/dev_deepseek/analysis
```

Model: keep `LLM_MODEL=deepseek-chat` in `.env`. On DeepSeek that alias returns deepseek-flash with
reasoning off, the condition every comparable run used. Requesting `deepseek-flash` by name turns
reasoning on, which is a different condition and overruns the 4,000-token cap; the scorer warns when
responses contain reasoning tokens or were truncated. For a reasoning-mode run use a separate output
folder and `--model deepseek-flash --max-tokens 32000 --timeout 400`: with the 4,000 cap, 77 of 80 P3
reviews in `results/probe_thinking_H04` were cut off before the answer.

Add `--branching` (recommended for every comparison of procedures) so that each item x repeat gets
one shared first call: its answer is P0, and P1-P4 each review that same answer. This removes
first-pass sampling noise and needs 5 calls per item x repeat instead of 9.
Difficulty screen of new development families: `--procedures P0 --repeats 2`, then
`python harness/screen_report.py results/<dir> --cases cases/<dir>`.

The second command is a smoke test of 8 runs. Re-running the same command resumes and retries
failed runs. Credentials: copy `.env.example` to `.env` and fill in one provider.

Confirmation runs need frozen, expert-approved families and `--confirm-manifest`.

Local open-weight model (discontinued on 2026-11-06: the study uses DeepSeek flash only; kept here to document the P0 screen in report section 8): Ollama 0.40.15 (installed in `D:\Claude\Ollama`, models in `D:\Claude\ollama-models` via the OLLAMA_MODELS user variable; start the app from the Start menu or with `explorer.exe`, since a server started by the app from a sandboxed shell exits at once) with `qwen2.5:7b-instruct` and a 16k context
(`harness/local_models/qwen2.5-7b-instruct-ctx16k.Modelfile`; create it with `ollama create`). Point the
runner at it with environment variables, which override `.env` without touching the DeepSeek settings:

```bash
LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama-local LLM_MODEL=qwen2.5-7b-instruct-ctx16k \
  python harness/runner.py --cases cases/dev --out results/<dir> --procedures P0 --repeats 2 --concurrency 1
```
