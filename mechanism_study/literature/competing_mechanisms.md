# Competing mechanisms for a source-verification advantage (literature-and-theory line)

**Round question.** Does the benefit of source verification come from checking the decisive evidence, or only from spending more computation / thinking one more time?

**Status.** Narrative review, single reviewer (AI-assisted), searches run 2026-11-05. Labels: **[PR]** peer reviewed; **[PP]** preprint, not peer reviewed; **[V]** metadata and the claim used here checked against Crossref, arXiv or the publisher page; **[P]** partly verified (see Section g). Skills followed: `literature-review` (question first, on-demand channels, search log, gap claims tied to searches) and `scientific-critical-thinking` (rival explanations, data versus interpretation).

**Procedure labels follow this round**, not v3 §3.3.5: P0 strong single-call baseline; P1 free re-check (2 calls); P2 generic checklist re-check (2 calls); P3 source-applicability re-check (2 calls: population/scope, time version/effective dates, authorization scope, whether the evidence supports the decision). Cell notation: **F/A** = flawed/aligned advice; **E+/E−** = decisive evidence present/absent; **DC/IC/PP** = decisive change / irrelevant change / paraphrase state.

---

## 0. Framing: four points from the literature that shape every prediction

1. **P1–P3 are all "intrinsic" self-correction.** Huang et al. (2024) define intrinsic self-correction as revision "without the crutch of external feedback"; Kamoi et al. (2024) separate it from correction with external tools, knowledge, oracles or fine-tuning. The second call in P1–P3 gets no information the first call did not already have, because the dossier was already in context. The prior from this literature is pessimistic. Without external feedback, self-correction on reasoning benchmarks seldom helps and often turns correct answers into incorrect ones (Huang et al., 2024; Stechly et al., 2023, 2025; Zhang et al., 2025 [PP]). Kamoi et al. name the exception: tasks in which "verification is clearly easier than generation", such as decomposable answers. P3 is a bet on that exception. Checking whether a notice's effective date covers the decision date is easier than producing the decision, and the decisive fact is already in context.
2. **The flawed advice is itself a suggested answer.** Assistants move toward answers the user suggests, and they drop correct answers when asked "Are you sure?" (Sharma et al., 2024; Laban et al., 2024 [PP]). Biasing features in the input change answers without being mentioned in the chain of thought (Turpin et al., 2023). So P0's likely failure on flawed advice is deference, and any re-check that weakens deference will raise correction whether or not it checks evidence.
3. **Naming the error types tells the model where the error is.** Tyen et al. (2024) found that LLMs are poor at finding reasoning errors but correct them well once given the location. Huang et al. (2024) showed that some reported self-correction gains came from feedback prompts carrying information the initial prompt lacked. When the requirement was added to the initial prompt, standard prompting scored 81.8 and self-correction lowered it to 75.1. P3's list of scope, version and authorization is that kind of information, so instruction cueing (M4) is the strongest rival to M1. Comparing P1–P3 alone cannot separate the two.
3a. **The order of operations matters.** In Chain-of-Verification, verification that was conditioned on the draft repeated the draft's hallucinations. Answering the verification questions independently of the draft worked better (Dhuliawala et al., 2024). Re-reading the input also improves reasoning on its own (Xu et al., 2024).
4. **Precondition.** Procedure differences can only show if P0 is off the ceiling on F·E+ items. The value of test-time compute depends on item difficulty (Snell et al., 2025), and more calls can help easy items while hurting hard ones (Chen et al., 2024 [PP]). The pilot hit the ceiling everywhere (v3 §2.3.4).

---

## (a) Mechanism table

| ID | Mechanism | What the literature says (verified sources) | Core signature |
|---|---|---|---|
| **M1** | **Decisive-evidence checking** (target): P3 makes the model check the applicability properties of each cited source against the decision. | CoVe: short, fact-level questions answered independently of the draft cut hallucination (Dhuliawala et al., 2024). Self-correction works where verification is easier than generation or the feedback is reliable (Kamoi et al., 2024). Human side: explanations help when they make the AI's answer cheap to verify (Vasconcelos et al., 2023), and help mainly when they enable verification (Fok & Weld, 2024). **No study tests applicability checking of in-context documents** (Section e). | Gains concentrated in F·E+; no rise in overturning aligned advice; in E− the gain shows up as escalation, not as confident alternatives; corrections co-occur with naming the decisive source and property. |
| **M2** | **Extra computation / second pass** | More test-time compute helps on prompts of suitable difficulty (Snell et al., 2025). Compound-call performance can rise and then fall with the number of calls (Chen et al., 2024 [PP]). Longer reasoning can lower accuracy (Gema et al., 2025). Self-consistency gains come from sampling several reasoning paths (Wang et al., 2023). | P1 ≈ P2 ≈ P3 > P0; effect follows actual tokens, not prompt content. |
| **M3** | **Structured attention** (any checklist) | Multi-agent debate does not reliably beat self-consistency or ensembling (Smit et al., 2024). A single agent with a strong prompt nearly matches the best multi-agent discussion (Wang et al., 2024). Human experts: checklist-guided verification corrected more ECG errors than verification without a checklist (Sibbald et al., 2013, n = 15) [P]. | P2 ≈ P3 > P1. |
| **M4** | **Instruction cueing**: P3's wording names the error types and so supplies the error location or a "find a defect" demand. | Error location is the bottleneck (Tyen et al., 2024). Feedback-prompt content belongs in the initial prompt (Huang et al., 2024). Prompt semantics may matter less than assumed (Webson & Pavlick, 2022, older models). Human analogue: demand characteristics (Orne, 1962). | A cue-only arm ≈ P3; false alarms on "lure" items with salient but valid dates or scope; no P3 advantage for defects outside the named dimensions. |
| **M5a** | **Challenge-induced wavering** (a re-check prompt acts like "Are you sure?") | Assistants abandon correct answers under challenge (Sharma et al., 2024; Laban et al., 2024 [PP]: answers changed about 46% of the time, accuracy fell about 17%). Intrinsic self-correction causes answer wavering and prompt bias (Zhang et al., 2025 [PP]). Correct-to-incorrect changes (Huang et al., 2024). | Flips in both directions, including right → wrong; strongest in P1; lower IC/PP consistency. |
| **M5b** | **General skepticism (criterion) shift**: more rejection of advice, correct or not. | Human mirror image: explanations raised acceptance regardless of correctness (Bansal et al., 2021). Signal-detection framing separates sensitivity from criterion (Stanislaw & Todorov, 1999). | Gain in correcting flawed advice ≈ loss on aligned advice; d′ unchanged, criterion c shifts. |
| **M6** | **Escalation bias** | Baseline models under-abstain: strong models answer wrongly rather than abstain when context is insufficient (Joren et al., 2025 [P]). Reasoning fine-tuning lowers abstention (Kirichenko et al., 2025 [P]). Survey: Wen et al. (2025). So any arm that escalates more will look good on E− items. | Escalation rises in E+ and E− alike; the E−/E+ escalation gap does not change. |
| **M7** | **Re-reading / anchoring release**: the re-check makes the model re-read source passages rather than the memo or its draft. | Re-reading the input improves reasoning (Xu et al., 2024). Mid-context information is used less well (Liu et al., 2024). Conditioning verification on the draft repeats errors (Dhuliawala et al., 2024). Models adopt coherent external evidence but show confirmation bias when evidence is mixed (Xie et al., 2024). | P3 ≈ P2 when P2 also requires quoting each cited source; gains larger when the decisive passage sits mid-dossier. |
| **M8** | **Verbosity / format effects** | Format restrictions degrade reasoning (Tam et al., 2024). Formatting changes swing accuracy widely (Sclar et al., 2024). LLM judges show verbosity bias (Zheng et al., 2023). Pilot: flawed advice relabelled "revise" with no change in action (v3 Table 2.1). | Differences in labels or rationales, not in the action field; differences vanish under strict scoring of the action field; tied to output length or invalid-output rates. |
| **M9** (added) | **Resampling noise**: a second draw at T > 0 changes answers at random. | Gains in iterative prompting were traced to the correct answer appearing among sampled completions, not to the content of the critique (Stechly et al., 2023 [PP]). Sampling diversity drives self-consistency (Wang et al., 2023). | Flips symmetric and about equal to a P0 test–retest flip rate; P1 ≈ P2 ≈ P3. |
| **M10** (added) | **Role or framing of the checked text** | Moving the same erroneous claim from the model's own thought block into an external role (user, tool, memory) raised explicit correction by 23–93 points in 10 of 12 settings (Chen et al., 2026 [PP]). | An advantage appears in whichever arm presents the memo or the first answer as an external claim to audit, and disappears when role placement is identical. |
| A | **Measurement artefacts** (not a model mechanism) | Case or condition codes leaked in pilot request labels (v3 §2.3.4). LLM-judge biases (Zheng et al., 2023). | Remove with blind requests and strict deterministic action scoring. |

**Human-side analogues (for Phase 4, briefly).** Cognitive forcing (Buçinca et al., 2021) is mostly an M2/M3 manipulation: it makes people decide or slow down, not check specific evidence. It reduced over-reliance compared with simple explanations, at a cost in user ratings. Vasconcelos et al. (2023) and Fok and Weld (2024) are the human counterpart of M1: verification support helps only when the evidence makes checking cheap and decisive. Sibbald et al. (2013) is a human P1-versus-P2/P3 contrast, but its checklist was content-specific and was never compared with a generic one. Ely et al. (2011) proposed general versus specific diagnostic checklists without testing them [P]. Schemmer et al.'s (2023) two-dimension reliance measure maps onto contrast C2 below.

---

## (b) Prediction matrix

Entries give expected orderings of procedure rates (0–3 = P0–P3). "≈" means no reliable difference expected; "↑/↓" is relative to P0. Under every mechanism, PP states should behave like IC states.

| Mech. | Correct action, F·E+ | Overturn of aligned advice, A·E+ | Appropriate escalation, E− | Unnecessary escalation, E+ | DC pair success | IC/PP stability | P3−P1 gain: E+ vs E− |
|---|---|---|---|---|---|---|---|
| **M1** | 3 > 2 ≥ 1 ≈ 0 | 3 ≈ 0 (no rise) | 3 > 2 ≥ 1 ≈ 0 | 3 ≈ 0 | 3 > 2 ≥ 1 ≈ 0 | 3 ≈ 0 (no loss) | Correct-action gain large in E+, ≈ 0 in E−; in E− the gain is escalation only |
| **M2** | 1 ≈ 2 ≈ 3 > 0 | 1 ≈ 2 ≈ 3 (≥ 0) | 1 ≈ 2 ≈ 3 ≥ 0 | 1 ≈ 2 ≈ 3 | 1 ≈ 2 ≈ 3 ≥ 0 | 1 ≈ 2 ≈ 3 | ≈ 0 in both; gains follow tokens |
| **M3** | 2 ≈ 3 > 1 ≥ 0 | 2 ≈ 3 | 2 ≈ 3 > 1 | 2 ≈ 3 | 2 ≈ 3 > 1 | 2 ≈ 3 | P3−P2 ≈ 0 in both |
| **M4** | 3 > 2 ≈ 1; cue-only ≈ 3 | 3 > 2 on lure items | 3 > 2 ≈ 1 | 3 ↑ on items where authorization or dates are salient | 3 > others only for changes on named dimensions | 3 < 0 when the IC touches the surface of a named dimension | Gain wherever a named property is salient, decisive or not |
| **M5a** | 1 ≥ 2 ≈ 3 > 0 (small) | 1 ≥ 2 ≈ 3 > 0 | ≈ | small ↑ | ≈ or ↓ | 1, 2, 3 < 0 | none |
| **M5b** | 3 > 0 | 3 > 0, about as large as the correction gain | ↑ only if rejection maps to pausing | ↑ | ↑ when DC flips toward rejection, ↓ when toward acceptance | ≈ | none; d′ unchanged |
| **M6** | Non-adoption ↑ but correct alternative action not ↑ | ↑ (through escalation) | 3 ↑ | 3 ↑ by a similar amount | ↓ (escalates in both states) | ≈ | E−/E+ escalation gap unchanged |
| **M7** | Re-reading arms > 1; 3 ≈ 2 if P2 quotes the sources | ≈ | small ↑ | ≈ | ↑ | ≈ | Larger for mid-context or long dossiers |
| **M8** | Action ≈ across arms; labels differ | ≈ (more "revise" labels) | ↑ only through hedged answers | ↑ only through hedged answers | ≈ | ≈ (↓ with stricter format) | Vanishes under strict action-field scoring |
| **M9** | Net ≈ 0 | 1 ≈ 2 ≈ 3, symmetric | ≈ | ≈ | ≈ | slightly < 0 | none; flips ≈ P0 test–retest |
| **M10** | ↑ in the arm with external-role placement | ? | ? | ? | ? | ? | Vanishes with identical role placement |

**Bold hypothesis, stated as the M1 pattern.** On flawed-advice items, the P3 − (P1, P2) difference in correct action is positive in E+ and about zero in E−. In E−, P3 instead raises pause/escalate without raising escalation in E+. If the same E− rise shows up in E+, it is M6. If an equal E+ gain appears in P1 or P2, it is M2 or M3. If it appears in a cue-only arm, it is M4.

---

## (c) Discriminating contrasts mapped to mechanisms (★ = most diagnostic)

| ID | Contrast (cells) | Separates | Pattern supporting M1 | Rival pattern |
|---|---|---|---|---|
| ★C1 | **Procedure × evidence availability** on flawed advice: (P3−P1) and (P3−P2) in E+ vs E−, with correct action and escalation analysed separately | M1 vs M2, M3, M6 | Positive interaction: correct-action gain in E+ only; escalation gain in E− only | M2/M3: no P3-specific gain; M6: escalation gain in both E+ and E− |
| ★C2 | **Sensitivity vs criterion**: per arm, hits = flawed advice not adopted and correct action chosen; false alarms = aligned advice overturned (E+). Compute d′ and c, or A′/B″ near the ceiling, with a log-linear correction (Stanislaw & Todorov, 1999). Non-inferiority test on overturning aligned advice. | M1 vs M5b (and M5a) | d′(P3) > d′(P1), d′(P2); overturn rate within the margin | Criterion c moves, d′ flat; overturns rise in step with corrections |
| ★C3 | **Cue-only controls**: (i) P1 plus one sentence naming scope, version and authorization (2 calls, no per-source procedure); (ii) P0 with the same sentence in a single call ("pre-hoc", as in Huang et al., 2024) | M1 vs M4; also whether the second call is needed at all | P3 > both cue arms on F·E+, with no lure false alarms | Cue (i) ≈ P3: naming suffices. Cue (ii) ≈ P3: the second call adds only cost |
| ★C4 | **Transition analysis** in two-call arms: first-pass vs final action (wrong→right, right→wrong) by advice × evidence, against the flip rate between two independent P0 draws at the same settings | M1 vs M9, M5a | Asymmetric (wrong→right ≫ right→wrong), concentrated in F·E+ | M9: symmetric, ≈ P0 test–retest; M5a: right→wrong flips, largest in P1 |
| ★C5 | **Lure and off-checklist items**: (a) aligned advice citing sources with salient but valid applicability features (dates near a threshold, broad scope lists, delegated authority that does cover the case); (b) flawed advice whose defect lies outside the named dimensions (e.g., an omitted mandatory cost); (c) irrelevant changes on the surface of a named dimension (a non-governing date changes) | M1 vs M4, M5b | No false alarms on (a); stable on (c); on (b), gain only through the "does the evidence support the decision" item | M4/M5b: false alarms on (a), instability on (c), no gain on (b) |
| C6 | P3−P2 with re-reading matched (P2 also requires quoting each cited source); decisive passage position varied (early, middle, late) | M1 vs M7, M3 | P3 > P2 at every position | P3 ≈ P2; gain only when the decisive passage is mid-dossier |
| C7 | Procedure effect adjusted for actual output tokens; cost per corrected flawed item | M1 vs M2 | Effect survives the adjustment | Effect explained by tokens (dose–response) |
| C8 | Right-reason coding (blind): share of corrections that name the decisive source and property | M1 vs M5, M9 | Most P3 corrections name the defect | Corrections without the defect named. Caveat: rationales may be unfaithful (Turpin et al., 2023), so this is convergent evidence only |
| C9 | DC pair success with IC/PP non-inferiority, P3 vs P0 | M1 vs M5a, M4 | DC ↑ with no IC/PP loss | IC/PP loss (M5a); DC gains only on named dimensions (M4) |
| C10 | Escalation sensitivity, Esc(E−) − Esc(E+); and **detection vs action**: E− items where the rationale notes the missing document but the action still proceeds (Gu et al., 2026 [PP]) | M1 vs M6 | The gap widens; detection turns into action | Both escalation terms rise (M6); detection without abstention |
| C11 | Strict deterministic scoring of the action field; invalid or ambiguous output rates by arm; identical role placement of the memo and first answer in all two-call arms | M8, M10, artefacts | No change | Differences disappear under strict scoring or identical roles |

**Minimum additions if the budget is tight:** a P0 test–retest re-run (cheap; needed for C4); cue arm (i) (keeps the call count and isolates naming); lure and off-checklist items within existing case families (C5); and a P2 that quotes sources (C6). Without C3 or C5, a P3 advantage cannot be attributed to M1 over M4.

---

## (d) Established vs contested vs untested

**Established** (several independent studies, mostly on general benchmarks rather than administrative tasks):
- Intrinsic self-correction on reasoning, QA and planning benchmarks seldom improves accuracy and can change correct answers to incorrect ones (Huang et al., 2024; Stechly et al., 2025; Kamoi et al., 2024; Zhang et al., 2025 [PP]).
- Reported gains from self-correction or debate shrink against strong initial prompts and equal-budget baselines such as self-consistency (Huang et al., 2024; Kamoi et al., 2024; Smit et al., 2024; Wang et al., 2024).
- Reliable external feedback, not critique text, is what makes iterative correction work (Stechly et al., 2023 [PP], 2025; Gou et al., 2024; Kamoi et al., 2024).
- Models defer to suggested answers and give way under challenge (Sharma et al., 2024; Laban et al., 2024 [PP]); chain-of-thought explanations can leave out what drove the answer (Turpin et al., 2023).
- Models under-abstain when context is insufficient (Joren et al., 2025; Kirichenko et al., 2025; Wen et al., 2025).
- Models are sensitive to irrelevant context and prompt format (Shi et al., 2023; Sclar et al., 2024; Gema et al., 2025).
- Human side: explanations raise acceptance whether or not the AI is correct (Bansal et al., 2021); on average, human–AI combinations do worse than the better of the two alone, with losses in decision tasks (Vaccaro et al., 2024).

**Contested or mixed:**
- Whether targeted verification beats generic re-checking at equal cost. CoVe supports it but was not compute-matched. Stechly et al. (2023) found the critique content mattered little. Tyen et al. (2024) is consistent with both M1 and M4.
- Whether more test-time compute helps. It depends on difficulty (Snell et al., 2025), is non-monotonic in the number of calls (Chen et al., 2024 [PP]) and can scale inversely (Gema et al., 2025).
- Whether models follow conflicting context or their priors. They adopt coherent evidence but show confirmation bias when evidence is mixed (Xie et al., 2024). The memos in this round cite real material credibly, which is the "coherent" case.
- Which part of a second pass helps: re-reading the input (Xu et al., 2024), or avoiding conditioning on the draft (Dhuliawala et al., 2024).
- The human verification-cost account rests on maze tasks with crowdworkers (Vasconcelos et al., 2023) and a theoretical synthesis (Fok & Weld, 2024). Expert checklist evidence is small-sample (Sibbald et al., 2013).

**Untested (no study found; see e):**
- Applicability of in-context sources (population/scope, time version, authorization) as a verification target, compared with a free and a generic re-check at matched calls and tokens.
- The evidence-availability moderation hypothesis (C1).
- Cue-only or placebo controls for verification prompts. Huang et al. (2024) moved feedback content into the initial prompt in one task, which is the closest precedent.
- Any of the above with administrative dossiers, Chinese-language materials, or school administrators.

---

## (e) Gap statement

No study was found that does any of the following:
- compares a source-applicability verification re-check with a free re-check and a generic-checklist re-check at matched call count and output budget;
- manipulates whether the decisive document is present;
- includes a cue-only control for the wording of a verification prompt.

The searches that would have found such work are D1–D4 in Section h: targeted versus generic critique at matched calls, applicability or supersession of cited documents, hint or placebo controls, and reflection versus abstention. They were complemented by the lead-specific lookups. The closest neighbours are:
- CoVe: targeted, but not compute-matched;
- Huang et al. (2024): equal-response debate versus self-consistency, plus the shift of prompt content into the initial prompt;
- Tyen et al. (2024): supplying the error location;
- Joren et al. (2025): stratifying by context sufficiency, with no verification procedure;
- Sibbald et al. (2013): checklist-guided versus unguided verification in human experts;
- Chen et al. (2026) [PP]: role relabelling.

Policy-QA benchmarks that drop superseded documents while building their datasets (D2) do not test verification procedures.

"Not studied" here means not studied in any population. The related evidence comes from different settings: math, QA, planning and RAG benchmarks, crowdworkers, and physicians reading ECGs. None of it comes from rule-bound administrative decisions.

Limits of this search:
- single reviewer, general web search plus arXiv, Crossref, ACL, PMLR and ICLR lookups;
- no database searches (ACM DL, Scopus/WoS) and no CNKI;
- no systematic forward-citation chase of Kamoi et al. (2024), Huang et al. (2024) or Dhuliawala et al. (2024).

The recommended next check is a Semantic Scholar forward-citation scan of those three papers for "compute-matched", "budget" or "placebo". A gap claim in the dissertation should cite the search dates and queries.

---

## (f) Claim checks of v3

| v3 location | v3 wording (abridged) | Verdict | Corrected wording |
|---|---|---|---|
| §1.1.1; Table 2.2; H5 rationale | Explanations reduce over-reliance "mainly when they lower the cost of checking" (Vasconcelos et al., 2023) | **Overgeneralised.** Five Prolific studies, N = 731, maze task with a simulated AI. Explanations reduced over-reliance only on hard mazes. Easy-to-parse highlight explanations beat written step-by-step ones. A larger bonus also reduced over-reliance. The cost–benefit framework is the authors' interpretation, not evidence that verification cost is "the main" moderator. | "In maze-solving experiments with online participants, explanations reduced over-reliance when the task was hard and the explanation was easy to check, and larger rewards for accuracy also reduced over-reliance. The authors interpret this through a cost–benefit account in which people engage with explanations when verifying the AI is cheaper than solving the task (Vasconcelos et al., 2023)." §2.1.5 already has the accurate form; use it everywhere. Mark the H5 rationale as an inference. |
| §1.1.1, §2.1.6, H3, §2.3.3 | Without external feedback, LLMs often fail to self-correct and sometimes get worse; they can abandon correct answers (Huang et al., 2024) | **Accurate.** Two additions matter for this round. (1) Their definition makes P1–P3 all intrinsic. (2) Two findings to cite explicitly: on GSM8K, debate underperformed self-consistency at equal numbers of responses (6: 83.2 vs 85.3; 9: 83.0 vs 88.2); and when the initial prompt carried what the feedback prompt implied, self-correction lowered performance (81.8 → 75.1). Benchmarks were GSM8K, CommonSenseQA and HotpotQA. | Add "intrinsic" and the benchmark scope. Add the URL https://arxiv.org/abs/2310.01798 (the reference has none). |
| H1 rationale; §2.3.3 | "Verification appears most effective when it targets specific, checkable facts (Dhuliawala et al., 2024)" | **Overreach.** CoVe was not compared with a generic or compute-matched re-check. Baselines were few-shot, zero-shot and CoT prompting of Llama models, and CoT did not help. CoVe showed that answering short verification questions independently of the draft (factored) reduced hallucination on list QA, closed-book MultiSpanQA and biographies. Joint verification conditioned on the draft repeated errors, and yes/no questions did worse than open questions in the factored variant. Its errors come from parametric recall, not from the applicability of in-context documents. | "Chain-of-Verification reduced hallucinations when a model planned short verification questions and answered them independently of its draft (Dhuliawala et al., 2024). This suggests, but does not establish, that targeted checks outperform generic re-checking, because CoVe was not compared with a compute-matched generic re-check." Design implication: phrase P3 items as open questions ("Which population does S3 cover?"), not yes/no. |
| §2.3.3 | "Comparisons … should use strong comparison conditions and matched computational budgets" | **Sound but uncited**, and presented as if it followed from CoVe, Du et al. and Huang et al. | Cite Kamoi et al. (2024): their checklist asks for "sufficiently strong" initial prompts and baselines of comparable computational cost. Also cite Huang et al. (2024), Smit et al. (2024) and Wang et al. (2024). Define the budget (calls plus output-token cap) and report actual tokens and latency. |
| §3.3.5, §3.7.3 (consistency) | P1 general reflection, P2 source-verification instruction, P3 structured checklist; exploratory "P2 versus P1" | **Label clash** with this round. As written, v3 P1–P3 are single-call instructions, so P1–P3 are not budget-matched (only P4/P5 are). | Relabel to this round's P0–P3 and state the two-call matching. |
| §2.1.5 | Bansal et al. (2021): explanations "did not produce complementary team performance" | **Misstatement.** AI assistance did produce complementary improvements; explanations did not increase them, and they raised acceptance regardless of correctness. | "Explanations did not increase the complementary gains from AI assistance and instead increased acceptance of AI recommendations whether or not they were correct (Bansal et al., 2021)." |
| References | Vaccaro et al. 8, 2293–2303; Vasconcelos et al. Article 129; Buçinca et al. Article 188; Zheng et al. NeurIPS 36 | **Minor.** Crossref gives Vaccaro et al. issue 12. Crossref lists pages 1–38 and 1–21 for the two ACM articles but no article numbers, so check those in the ACM DL. Zheng et al. is in the Datasets and Benchmarks Track. | Add "(12)"; confirm the article numbers; add the track. |

---

## (g) References (APA 7)

Status: **V** = verified (metadata plus the claim used, from Crossref, arXiv or the publisher). **P** = partly verified (detail given in the entry). No reference was taken from memory without a lookup.

- Bansal, G., Wu, T., Zhou, J., Fok, R., Nushi, B., Kamar, E., Ribeiro, M. T., & Weld, D. (2021). Does the whole exceed its parts? The effect of AI explanations on complementary team performance. In *Proceedings of the 2021 CHI Conference on Human Factors in Computing Systems* (pp. 1–16). ACM. https://doi.org/10.1145/3411764.3445717 — **V** [PR]
- Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). To trust or to think: Cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making. *Proceedings of the ACM on Human-Computer Interaction, 5*(CSCW1), 1–21. https://doi.org/10.1145/3449287 — **V** [PR]
- Chen, K.-Y., Su, F.-Y., Lin, S.-Y., Li, B., & Chiang, J.-H. (2026). *The self-correction illusion: Role relabeling gates explicit error flagging in large language models* (Version 2) [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2606.05976 — **V** [PP]
- Chen, L., Davis, J. Q., Hanin, B., Bailis, P., Stoica, I., Zaharia, M., & Zou, J. (2024). *Are more LLM calls all you need? Towards scaling laws of compound inference systems* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2403.02419 — **V** [PP]; publication venue not checked.
- Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., & Weston, J. (2024). Chain-of-verification reduces hallucination in large language models. In *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 3563–3578). https://doi.org/10.18653/v1/2024.findings-acl.212 — **V** [PR]
- Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2024). Improving factuality and reasoning in language models through multiagent debate. In *Proceedings of the 41st International Conference on Machine Learning* (PMLR 235, pp. 11733–11763). https://proceedings.mlr.press/v235/du24e.html — **V** [PR]
- Ely, J. W., Graber, M. L., & Croskerry, P. (2011). Checklists to reduce diagnostic errors. *Academic Medicine, 86*(3), 307–313. https://doi.org/10.1097/ACM.0b013e31820824cd — **P** (metadata from Crossref; content from secondary summaries) [PR]
- Fok, R., & Weld, D. S. (2024). In search of verifiability: Explanations rarely enable complementary performance in AI-advised decision making. *AI Magazine, 45*(3), 317–332. https://doi.org/10.1002/aaai.12182 — **V** [PR]
- Gardner, M., Artzi, Y., Basmov, V., Berant, J., Bogin, B., Chen, S., Dasigi, P., Dua, D., Elazar, Y., Gottumukkala, A., Gupta, N., Hajishirzi, H., Ilharco, G., Khashabi, D., Lin, K., Liu, J., Liu, N. F., Mulcaire, P., Ning, Q., … Zhou, B. (2020). Evaluating models' local decision boundaries via contrast sets. In *Findings of the Association for Computational Linguistics: EMNLP 2020* (pp. 1307–1323). https://doi.org/10.18653/v1/2020.findings-emnlp.117 — **V** (metadata) [PR]
- Gema, A. P., Hägele, A., Chen, R., Arditi, A., Goldman-Wetzler, J., Fraser-Taliente, K., Sleight, H., Petrini, L., Michael, J., Alex, B., Minervini, P., Chen, Y., Benton, J., & Perez, E. (2025). Inverse scaling in test-time compute. *Transactions on Machine Learning Research*. https://arxiv.org/abs/2507.14417 — **P** (TMLR stated on the arXiv record; TMLR page not checked) [PR]
- Gou, Z., Shao, Z., Gong, Y., Shen, Y., Yang, Y., Duan, N., & Chen, W. (2024). CRITIC: Large language models can self-correct with tool-interactive critiquing. In *The Twelfth International Conference on Learning Representations*. https://arxiv.org/abs/2305.11738 — **V** [PR]
- Gu, R., Li, J., Wang, Y., Yue, Y., Xiao, H., Chen, Y., Wang, Y., Guo, C., Wei, P., Gu, J., & Cao, Y. (2026). *Bridging the detection-to-abstention gap in reasoning models under insufficient information* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2605.28070 — **V** [PP]
- Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., & Zhou, D. (2024). Large language models cannot self-correct reasoning yet. In *The Twelfth International Conference on Learning Representations*. https://arxiv.org/abs/2310.01798 — **V** (definition and the numbers above from the full text) [PR]
- Joren, H., Zhang, J., Ferng, C.-S., Juan, D.-C., Taly, A., & Rashtchian, C. (2025). Sufficient context: A new lens on retrieval augmented generation systems. In *The Thirteenth International Conference on Learning Representations*. https://arxiv.org/abs/2411.06037 — **P** (arXiv verified; ICLR 2025 venue from a DBLP listing only) [PR]
- Kamoi, R., Zhang, Y., Zhang, N., Han, J., & Zhang, R. (2024). When can LLMs actually correct their own mistakes? A critical survey of self-correction of LLMs. *Transactions of the Association for Computational Linguistics, 12*, 1417–1440. https://doi.org/10.1162/tacl_a_00713 — **V** (including the checklist items) [PR]
- Kirichenko, P., Ibrahim, M., Chaudhuri, K., & Bell, S. J. (2025). *AbstentionBench: Reasoning LLMs fail on unanswerable questions* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2506.09038 — **P** (arXiv verified; listed as a NeurIPS 2025 poster, proceedings not checked)
- Laban, P., Murakhovs'ka, L., Xiong, C., & Wu, C.-S. (2024). *"Are you sure?" Challenging LLMs leads to performance drops in the FlipFlop experiment* (Version 2) [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2311.08596 — **V** [PP]
- Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2024). Lost in the middle: How language models use long contexts. *Transactions of the Association for Computational Linguistics, 12*, 157–173. https://doi.org/10.1162/tacl_a_00638 — **V** [PR]
- Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N., Prabhumoye, S., Yang, Y., Gupta, S., Majumder, B. P., Hermann, K., Welleck, S., Yazdanbakhsh, A., & Clark, P. (2023). Self-Refine: Iterative refinement with self-feedback. In *Advances in Neural Information Processing Systems, 36*. https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html — **V** [PR]
- Orne, M. T. (1962). On the social psychology of the psychological experiment: With particular reference to demand characteristics and their implications. *American Psychologist, 17*(11), 776–783. https://doi.org/10.1037/h0043424 — **V** (metadata) [PR]
- Ribeiro, M. T., Wu, T., Guestrin, C., & Singh, S. (2020). Beyond accuracy: Behavioral testing of NLP models with CheckList. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 4902–4912). https://doi.org/10.18653/v1/2020.acl-main.442 — **V** (metadata) [PR]
- Schemmer, M., Kühl, N., Benz, C., Bartos, A., & Satzger, G. (2023). Appropriate reliance on AI advice: Conceptualization and the effect of explanations. In *Proceedings of the 28th International Conference on Intelligent User Interfaces* (pp. 410–422). ACM. https://doi.org/10.1145/3581641.3584066 — **V** [PR]
- Sclar, M., Choi, Y., Tsvetkov, Y., & Suhr, A. (2024). Quantifying language models' sensitivity to spurious features in prompt design or: How I learned to start worrying about prompt formatting. In *The Twelfth International Conference on Learning Representations*. https://arxiv.org/abs/2310.11324 — **V** [PR]
- Sharma, M., Tong, M., Korbak, T., Duvenaud, D., Askell, A., Bowman, S. R., Cheng, N., Durmus, E., Hatfield-Dodds, Z., Johnston, S. R., Kravec, S., Maxwell, T., McCandlish, S., Ndousse, K., Rausch, O., Schiefer, N., Yan, D., Zhang, M., & Perez, E. (2024). Towards understanding sycophancy in language models. In *The Twelfth International Conference on Learning Representations*. https://proceedings.iclr.cc/paper_files/paper/2024/hash/0105f7972202c1d4fb817da9f21a9663-Abstract-Conference.html — **V** [PR]
- Shi, F., Chen, X., Misra, K., Scales, N., Dohan, D., Chi, E., Schärli, N., & Zhou, D. (2023). Large language models can be easily distracted by irrelevant context. In *Proceedings of the 40th International Conference on Machine Learning* (PMLR 202). https://arxiv.org/abs/2302.00093 — **P** (arXiv verified; PMLR pages not checked) [PR]
- Sibbald, M., de Bruin, A. B. H., & van Merrienboer, J. J. G. (2013). Checklists improve experts' diagnostic decisions. *Medical Education, 47*(3), 301–308. https://doi.org/10.1111/medu.12080 — **P** (metadata from Crossref; findings from abstract excerpts) [PR]
- Smit, A. P., Grinsztajn, N., Duckworth, P., Barrett, T. D., & Pretorius, A. (2024). Should we be going MAD? A look at multi-agent debate strategies for LLMs. In *Proceedings of the 41st International Conference on Machine Learning* (PMLR 235, pp. 45883–45905). https://proceedings.mlr.press/v235/smit24a.html — **V** [PR]
- Snell, C., Lee, J., Xu, K., & Kumar, A. (2025). Scaling LLM test-time compute optimally can be more effective than scaling parameters for reasoning. In *The Thirteenth International Conference on Learning Representations*. https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b623663fd9b874366f3ce019fdfdd44-Abstract-Conference.html — **V** [PR]. The arXiv title ends "…than scaling model parameters".
- Stanislaw, H., & Todorov, N. (1999). Calculation of signal detection theory measures. *Behavior Research Methods, Instruments, & Computers, 31*(1), 137–149. https://doi.org/10.3758/BF03207704 — **V** (metadata) [PR]
- Stechly, K., Marquez, M., & Kambhampati, S. (2023). *GPT-4 doesn't know it's wrong: An analysis of iterative prompting for reasoning problems* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2310.12397 — **V** [PP]
- Stechly, K., Valmeekam, K., & Kambhampati, S. (2025). On the self-verification limitations of large language models on reasoning and planning tasks. In *The Thirteenth International Conference on Learning Representations*. https://arxiv.org/abs/2402.08115 — **P** (arXiv verified; ICLR 2025 from the iclr.cc listing in search results) [PR]
- Tam, Z. R., Wu, C.-K., Tsai, Y.-L., Lin, C.-Y., Lee, H.-y., & Chen, Y.-N. (2024). Let me speak freely? A study on the impact of format restrictions on large language model performance. In *Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing: Industry Track* (pp. 1218–1236). https://doi.org/10.18653/v1/2024.emnlp-industry.91 — **V** [PR]
- Turpin, M., Michael, J., Perez, E., & Bowman, S. R. (2023). Language models don't always say what they think: Unfaithful explanations in chain-of-thought prompting. In *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2305.04388 — **V** [PR]
- Tyen, G., Mansoor, H., Cărbune, V., Chen, P., & Mak, T. (2024). LLMs cannot find reasoning errors, but can correct them given the error location. In *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 13894–13908). https://doi.org/10.18653/v1/2024.findings-acl.826 — **V** [PR]
- Vaccaro, M., Almaatouq, A., & Malone, T. (2024). When combinations of humans and AI are useful: A systematic review and meta-analysis. *Nature Human Behaviour, 8*(12), 2293–2303. https://doi.org/10.1038/s41562-024-02024-1 — **V** [PR]
- Vasconcelos, H., Jörke, M., Grunde-McLaughlin, M., Gerstenberg, T., Bernstein, M. S., & Krishna, R. (2023). Explanations can reduce overreliance on AI systems during decision-making. *Proceedings of the ACM on Human-Computer Interaction, 7*(CSCW1), 1–38. https://doi.org/10.1145/3579605 — **V** (study-level results from the ar5iv full text) [PR]
- Wang, Q., Wang, Z., Su, Y., Tong, H., & Song, Y. (2024). Rethinking the bounds of LLM reasoning: Are multi-agent discussions the key? In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 6106–6131). https://doi.org/10.18653/v1/2024.acl-long.331 — **V** [PR]
- Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023). Self-consistency improves chain of thought reasoning in language models. In *The Eleventh International Conference on Learning Representations*. https://arxiv.org/abs/2203.11171 — **V** [PR]
- Webson, A., & Pavlick, E. (2022). Do prompt-based models really understand the meaning of their prompts? In *Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies* (pp. 2300–2344). https://doi.org/10.18653/v1/2022.naacl-main.167 — **V** [PR]
- Wen, B., Yao, J., Feng, S., Xu, C., Tsvetkov, Y., Howe, B., & Wang, L. L. (2025). Know your limits: A survey of abstention in large language models. *Transactions of the Association for Computational Linguistics, 13*, 529–556. https://doi.org/10.1162/tacl_a_00754 — **V** [PR]
- Xie, J., Zhang, K., Chen, J., Lou, R., & Su, Y. (2024). Adaptive chameleon or stubborn sloth: Revealing the behavior of large language models in knowledge conflicts. In *The Twelfth International Conference on Learning Representations*. https://arxiv.org/abs/2305.13300 — **V** [PR]
- Xu, X., Tao, C., Shen, T., Xu, C., Xu, H., Long, G., Lou, J.-G., & Ma, S. (2024). Re-reading improves reasoning in large language models. In *Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing* (pp. 15549–15575). https://doi.org/10.18653/v1/2024.emnlp-main.871 — **V** [PR]
- Zhang, Q., Wang, D., Qian, H., Li, Y., Zhang, T., Huang, M., Xu, K., Li, H., Liu, Y., & Qiu, H. (2025). *Understanding the dark side of LLMs' intrinsic self-correction* (Version 2) [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2412.14959 — **V** [PP]
- Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. In *Advances in Neural Information Processing Systems, 36* (Datasets and Benchmarks Track). https://arxiv.org/abs/2306.05685 — **V** [PR]

**Leads not verified or not used:** none of the requested leads failed verification. Valmeekam et al. (2023) on self-critiquing plans was not checked because it is covered by Stechly et al. (2025). The exact counts in Huang et al.'s Figure 1 were not extracted.

---

## (h) Search log (all dates 2026-11-05)

**Discovery searches**

| # | Channel | Query | Hits screened | Kept |
|---|---|---|---|---|
| D1 | WebSearch (extended) | `LLM self-verification targeted vs generic critique prompt ablation compute-matched "same number of calls" re-check baseline` | 10 | Chen et al. 2026 [PP]. Dropped: cross-model review of planted errors (arXiv 2610.01471, tangential); self-verification-dilemma preprint (2602.03485, reasoning-trace redundancy); small-LM verifiers paper (not needed) |
| D2 | WebSearch (extended) | `LLM evaluation superseded policy version effective date applicability scope authority of cited document recommendation verification benchmark` | 9 | None. Policy-QA benchmarks filter superseded versions only when building datasets; "Supersede" (2606.27472) concerns agent memory |
| D3 | WebSearch | `self-correction prompt "information leakage" OR "hint" feedback prompt names error type control condition LLM self-refine fair comparison placebo instruction` | 10 | Zhang et al. 2025 [PP]. A token-level localization preprint (2605.12384) was noted but not verified or kept |
| D4 | WebSearch | `LLM reflection prompt increases abstention or escalation unnecessary refusal over-conservatism after self-reflection insufficient evidence` | 10 | Gu et al. 2026 [PP]; AbstentionBench (NeurIPS 2025 listing) |
| D5 | WebSearch | `Vasconcelos 2023 "explanations can reduce overreliance" maze task difficulty explanation difficulty monetary bonus results` | 10 | Led to the ar5iv full text (study-level results) |
| D6 | WebSearch | `Fok Weld "In search of verifiability" AI Magazine 2024 doi` | 10 | DBLP listing; DOI then confirmed in Crossref |
| D7–D14 | WebSearch | Venue checks: Smit (MAD) ICML 2024; Sharma ICLR 2024; Stechly ICLR 2025; Snell ICLR 2025; Joren ICLR 2025; Huang ICLR 2024; Madaan NeurIPS 2023; Tam EMNLP Industry | about 10 each | Venue confirmations only |
| D15–D18 | WebSearch | Vaccaro 2024 abstract; Schemmer 2023 RAIR/RSR; Ely 2011 checklist types; Sibbald 2013 ECG checklist | about 10 each | Content confirmations; Ely and Sibbald added (human checklist analogue) |

**Verification lookups**

| Channel | Targets | Result |
|---|---|---|
| Crossref REST API (`/works/{doi}`, `filter=doi:`, `query.bibliographic`) | 10.18653/v1/2024.findings-acl.212; 10.1162/tacl_a_00713; 10.1162/tacl_a_00638; 10.1162/tacl_a_00754; 10.1145/3579605; 10.1145/3449287; 10.1145/3581641.3584066; 10.1038/s41562-024-02024-1; 10.1002/aaai.12182; 10.1145/3411764.3445717; 10.18653/v1/2022.naacl-main.167; 10.1037/h0043424; 10.3758/BF03207704; 10.18653/v1/2024.findings-acl.826; 10.18653/v1/2024.acl-long.331; 10.18653/v1/2024.emnlp-main.871; 10.18653/v1/2024.emnlp-industry.91; 10.18653/v1/2020.acl-main.442; 10.18653/v1/2020.findings-emnlp.117; 10.1097/ACM.0b013e31820824cd; 10.1111/medu.12080 | All resolved with matching metadata. One HTTP 429, retried successfully |
| arXiv abs pages | 2310.01798, 2303.17651, 2310.12397, 2402.08115, 2408.03314, 2203.11171, 2310.13548, 2305.13300, 2305.04388, 2407.18418, 2311.17371, 2402.18272, 2311.08516, 2309.06275, 2302.00093, 2311.08596, 2411.06037, 2506.09038, 2403.02419, 2212.06823, 2305.07722, 2102.09692, 2006.14779, 2305.11738, 2310.11324, 2408.02442, 2412.14959, 2605.28070, 2606.05976, 2610.01471, 2507.14417, 2307.03172, 2306.05685 | All resolved; metadata and claims used here checked against the abstracts |
| Full text (ar5iv / arXiv HTML) | Huang et al. (definition; debate vs self-consistency; prompt-design critique); Kamoi et al. (categories, checklist); Dhuliawala et al. (variants, baselines, question types); Sharma et al. ("Are you sure?" task); Vasconcelos et al. (Studies 1–4) | Numbers quoted in Sections 0, (a) and (f) come from these. The ACM DL full text returned 403, and the PDFs could not be rendered (no poppler) |
| PMLR / ACL Anthology / ICLR proceedings | smit24a, du24e; NAACL 2022.167 | Confirmed |

*Prose is about 1,700 words, excluding tables and the reference list.*
