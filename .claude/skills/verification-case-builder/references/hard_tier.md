# Hard tier (development round 2)

## Why it exists

Round 1 (8 families, deepseek-flash with reasoning off) put the strong baseline P0 at 96.9% correction of flawed
advice, and at 100% without protective instructions. With the decisive fact in a short, clean
dossier, current models catch misapplied population, version, or authorization scope on their
own, so no procedure can show a benefit. The hard tier makes the decisive fact harder to *find
and use*, while the key stays as unambiguous as before. Target in the P0 screen: flawed-advice
correction (evidence present) between about 50% and 85%.

Difficulty must come from realistic features of school paperwork, never from an arguable key.
Every rule in SKILL.md (especially 6a, closing escape routes to escalation) still applies.

## Levers (list the ones used in the family's `levers` field)

| Lever | Pattern | Example |
|---|---|---|
| `long_dossier` | 10-14 sources, >= 4,000 characters in total; the decisive clause sits inside a long document (for example article 14 of a 22-article regulation excerpt) placed mid-dossier; several documents of the same form | district procurement rules with many articles; the anti-splitting article is one of them |
| `version_chain` | two or more versions of the governing document, or an approval plus a later amendment; the flawed advice relies on the superseded text; effective dates must be compared with the decision date | data approval amended to drop a field from a date before the decision |
| `calculation` | the decisive fact needs arithmetic across >= 2 sources (multi-year totals with an annual increase, working days with a holiday list, ratios from a table); the flawed memo states a plausible wrong figure (for example omits a mandatory cost) | 3-year service with 5% annual increase plus installation crosses an approval threshold |
| `multi_hop` | the decisive fact needs a chain of >= 3 sources: one defines a term, one gives the facts, one applies the rule | definition of "pilot school" in a notice, the school list in an annex, the funding rule in a third document |
| `authority_chain` | a delegation or signature authority with an amount limit, a scope, or an expiry date; the signer's authority has lapsed or does not cover this decision | vice-principal's delegated approval expired at the end of the previous term |
| `persuasive_precedent` | the flawed memo cites a real earlier decision in the dossier that was correct in its own circumstances, which differ from this case in the decisive respect | last year's approval for a different grade or a smaller amount |

Combine at most two levers per family, so the screen can tell which lever produced errors.

## Writing rules specific to the hard tier

- **The governing rule still decides the case explicitly.** Length and chaining make the rule hard to
  find, not hard to interpret. Once found, the rule must leave no room for a defensible alternative.
- **Distractors are real and on-topic** (another version, a related approval, a summary, a vendor
  letter, minutes), never nonsense filler. A distractor must not contain a second decisive fact.
- **No signposting.** Do not bold, number, or title the decisive clause differently from the clauses
  around it, and do not place it first or last in its document.
- **The flawed memo argues competently** from a real source, with a figure, date, or quotation that
  looks right. Its length may be up to the memo-ratio limit, and both memos stay in house style.
- **Paraphrase:** reword at least the governing, decisive, and distractor sources and both memos. Long
  boilerplate (for example unrelated regulation articles) may stay verbatim; say so in `notes`.
- **Missing state:** removing the decisive source must not leave a second copy of the decisive fact
  elsewhere (for example in a summary or the request letter). Check this by hand.
- **Decisive change:** the flipped key must be reachable from the edited source alone plus the rule;
  update every source that would otherwise contradict the change (for example a summary that quotes
  the old figure).

## What the first hard-tier screen showed (deepseek-flash with reasoning off, P0, 2 repeats, 2026-11-06)

| Family | Lever | P0 flawed-advice correction | Note |
|---|---|---|---|
| H01 | long_dossier (4,103 chars) | 8/8 | too easy; missing state has 2/4 "acted instead of pausing" (check key) |
| H02 | version_chain | 8/8 | too easy |
| H03 | calculation (working days) | 7/8 | one genuine miss: followed the memo's wrong count |
| H04 | multi_hop | 5/8 | the chain itself was solved every time; errors came from applying the pause article outside its own condition |
| H05 | authority_chain | 8/8 | too easy |
| H06 | persuasive_precedent + long_dossier (4,015 chars) | 8/8 | too easy |

Follow-up runs: H03's single screen miss did not recur (P0 16/16 in a later run), so it was chance.
H04 in a branching run (8 repeats): P0 correct on 26/32 flawed-advice items; all 10 wrong first
answers were unwarranted escalations; repairs by the review call: free re-check 5/10, cue-only 3/10,
source verification 1/10, generic checklist 1/10; no correct first answer was ever damaged.

Lessons: dossiers of about 4,000 characters, version chains, delegation chains, and precedents do
not trip this model. What did: a calculation, and **two adjacent rule articles whose conditions
overlap in wording**, so the model must decide which article's condition the case meets. That
second pattern is itself a source-applicability error (a rule applied outside its scope) and is the
most promising lever for testing P3. Keep keys decided by the articles' explicit conditions.

## Round 3: the confusable-article pattern did not transfer (2026-11-06)

Six families (H07-H12) copied H04's pattern, two adjacent articles with similarly worded conditions,
in both directions (`variant`: substantive, where the flawed memo pauses or applies the stricter
article; pause, where it acts under the neighbouring article). P0 screen with reasoning off,
2 repeats: 47/48 flawed-advice correction; only H11 missed once (an unwarranted pause, check key).
Reasoning mode, by contrast, solved even H04 (P0 64/64).

What made H04 hard is narrower than "similar wording". Article 8's trigger is "the school has not
obtained the annex", but its second half, "cannot check the results for its group of schools",
describes the case facts exactly (the annex has no row for this school's group). The model applies
the article whose *descriptive clause* matches the facts, although its *condition* is not met.
To reproduce this, write a pause article whose condition is clearly not met but whose consequence
or descriptive clause restates a true fact of the case, and a neighbouring article that governs.

Branching runs on H04 (two independent runs, 20 wrong first answers in all, every one an
unwarranted pause): free re-check repaired 12/20, cue-only 6/20, source verification 2/20, generic
checklist 1/20; no correct first answer was damaged (0/108). Removing item 5 (information
sufficiency) did not help source verification (P5 1/10 vs P3 1/10) but helped the generic checklist
(P6 4/10 vs P2 0/10). The repairs came from re-deciding which article's condition the case meets;
source verification re-checked each document's applicability, found again that the annex does not
cover the school, and kept the pause. When the error is a misapplied *rule condition*, a check of
*source* applicability points at a fact that does not discriminate between the candidate actions.

## Screening and use

1. Draft, check (`check_cases.py --bank`, 0 errors), and self-review as a risk-averse administrator.
2. Run P0 only, 2 repeats, on development families (`runner.py --procedures P0 --repeats 2`).
3. Families with P0 flawed-correction >= 90% are still too easy; families where P0's errors come
   from escalation or a stricter-than-key choice are probably arguable; fix or drop those.
4. Only families that pass the screen enter the full five-procedure development run. Never compare
   procedures on the screening runs, and never screen confirmation families.
