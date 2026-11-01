# Editorial Decision Package

## Calibration Resolution

`calibration_status: NOT_CALIBRATED`

[Current runtime boundary: do not upgrade this package from a candidate or prose-named profile. `PROFILE_MEASURED` remains unavailable until a closed profile artifact and replay validator bind the exact target fields to the actual completed-panel `execution_topology_sha256`.]

Binding: unbound run. All five Phase 2 cards run without a criteria manifest (the EIC card states `criteria_binding_unavailable`; no target venue is bound). This package makes no venue-alignment claim, and none of its content is a claim about fit to any specific venue.

### Contract arithmetic (v3.6.2 Sprint Contract Synthesizer Protocol)

Contract `reviewer/reviewer_full/v2`, panel_size 5. Usable Phase 2 cards: 5 of 5 (eic, methodology, domain, perspective, da). Every card passed `check_phase_conformance.py`. No `[PANEL-SHRUNK]`.

**Step 1: role-scoped scoring matrix.** Only eligible seats are counted. Ineligible `not_assessed` values are excluded. No eligible seat abstained.

| Dim | Name | Priority | Eligible seats | Assessed scores | Verdict (worst) |
|---|---|---|---|---|---|
| D1 | methodology_rigor | mandatory | methodology | methodology=block (repairable) | block |
| D2 | domain_accuracy | mandatory | domain | domain=warn | warn |
| D3 | argumentative_coherence | mandatory | da, methodology | da=block (repairable); methodology=warn | block |
| D4 | cross_disciplinary_relevance | high | perspective | perspective=warn | warn |
| D5 | writing_and_structure | normal | eic | eic=warn | warn |
| D6 | venue_fit_and_contribution | mandatory | eic | eic=warn | warn |

No seat declared a fatal block, so no dimension is `block(fatal)`.

**Step 2: failure conditions.**

| Condition | Expression | Quantifier | Evaluation | Fired |
|---|---|---|---|---|
| F1 (95) | any mandatory dimension has a fatal block | any | No fatal block on D1/D2/D3/D6 | false |
| F2 (90) | any mandatory dimension scores 'block' | any | D1: methodology=block; D3: da=block | **true** |
| F3 (70) | two or more mandatory dimensions score 'warn' or worse | majority | D1 n=1, owner seat block → true; D2 n=1, warn → true; D3 n=2, both seats warn-or-worse → true; D6 n=1, warn → true. 4 ≥ 2 | **true** |
| F4 (60) | any high-priority dimension scores 'block' | any | D4 = warn | false |
| F5 (40) | any dimension scores 'warn' or worse | any | D1–D6 all warn-or-worse | **true** |
| F0 (10) | every dimension scores 'pass' | all | No dimension passes | false |

**Step 3: precedence.** Fired: F2 (90), F3 (70), F5 (40). F2 has the highest severity, and its action is `editorial_decision=major_revision`.

dimension_verdicts: [D1=block, D2=warn, D3=block, D4=warn, D5=warn, D6=warn]
fired_conditions: [F2, F3, F5]
da_critical_adjudications: [C1=VALIDATED]
editorial_decision=major_revision

No DA CRITICAL is REJECTED, so no rejection rationale line is required. The decision is not `accept`, so no `[DA-CRITICAL-VS-ACCEPT]` marker applies. `ARS_CROSS_MODEL` was not invoked for this round, so no cross-model checkpoint was run.

---

## Part 1: Editorial Decision Letter

Dear Author,

Thank you for submitting "TRACE v9 — concept brief for methodological review", a pre-data research-design brief for a thesis. No target venue is bound, so I judge the brief as a design document at a generic thesis level. I make no claim about fit to any specific venue. The brief was reviewed by five role-separated seats: a Journal-Fit Reviewer (eic), a methodology reviewer (R1), a domain reviewer (R2), a perspective reviewer (R3) and a Devil's Advocate (DA).

### Review Panel Provenance

The typed `review-panel-provenance/1.0` artifact **could not be built** for this round, so none exists. The cause is infrastructure: the installed plugin stores its contract file with CRLF line endings, so the builder's raw-byte pin check fails. The LF-normalised content matches the pinned hash. The execution facts are stated plainly instead:

- **Model family:** all five seats ran on one model family (claude).
- **Provider:** all five seats ran through one provider (anthropic).
- **Context:** each seat ran in its own subagent context.
- **Peer-output visibility:** unrecorded, so unknown. Seats were told not to read peer files, but they shared a working directory and their reads were not audited.
- **Human reviewer:** none.

**Correlated-error disclosure.** All five seats share one model family and one provider, so their errors may be correlated. Separating roles is not independent review. Agreement across seats below is agreement among same-family role prompts. It is not corroboration by independent reviewers, and it should be weighed accordingly.

### Decision: Major Revision

### Consensus Analysis

Consensus is counted per sub-claim over the four non-DA seats (eic, R1, R2, R3). The full inventory is in Part 3. No sub-claim is disputed by any seat, so there is **no SPLIT** and no Journal-Fit arbitration was needed. Remedies differ between seats in places, but they are compatible and are recorded as alternatives.

#### Points of Agreement

- **[CONSENSUS-3] SC-10: fitting the null on cue-off laps biases Δ toward zero** (R1 W3, R2 W2, R3 W6; eic silent; same as DA C1). Dependency, if present, would raise error and variability on probe and unassisted laps. Those are the laps the null is fitted on, so P_null rises and Δ shrinks. The three seats agree on the direction of the bias and that a null Δ is then uninterpretable. Their remedies are compatible alternatives: leave-own-probes-out or unassisted-only fits (R1), bracketing Δ between cue-on-fitted and cue-off-fitted σ (R2), and estimating a cue-on/cue-off variance ratio (R3).
- **[CONSENSUS-3] SC-5: full bibliographic references are missing** for TRACK 2026, Eneano et al. 2026, Linden 2026, Ye et al. 2016 and ARRS (eic W4, R2 W6, R3 W7; R1 silent). R2 notes that, without the references, the novelty positioning in §7 cannot be checked against the works it relies on.

#### Corroborated findings (two seats, no conflict)

- **SC-8: the model check contradicts the stated reason for fitting on cue-off laps** (R1 W2, R3 W6; also DA M1). If cue-on σ is biased low, a correctly fitted cue-off null should fail to reproduce cue-on SD. If it passes, the reason for fitting on cue-off laps is weakened.
- **SC-12: no pre-data decision rule or resolvable-Δ statement for braking** (R1 W5, R3 W4; also DA M2). Both seats give the same rough binomial SE of about 0.09 at roughly 16 probes and P_null ≈ 0.16, before clustering is taken into account.
- **SC-15: the "guidance dependency" reading of Δ is open to a withdrawal-transient rival** (R1 W8, R2 W1; also DA M3). Both seats recommend relabelling the construct. R1 adds a pre-specified within-probe time profile as a cheap discriminator.
- **SC-4: internal shorthand is left undecoded** (eic W4, R3 W7): F-codes, "v9 threat n", "the committed novice model".

#### Single-reviewer findings retained on their criterion and anchor

- SC-7 (R1 W1, **Critical**): the null model is not shown to be identifiable from the cue-off data volume.
- SC-1 and SC-2 (eic W1 and W2, Major): no reportable result is stated for the branches where Δ is withheld or uninformative, and the designer-facing implication is not shown.
- SC-9, SC-11, SC-13 (R1, Major): the model check has no tolerance; the calibration laps mix conditions and are timed by selection; the handling of censored probes is unspecified.
- SC-19 (R2 W1, Major): in the field, "dependency" is a retention construct, but the probe and the unassisted block are immediate, within-session tests.
- SC-23, SC-24, SC-25, SC-26 (R3, Major): the ICC form and its precision are unspecified; there is no decision-consistency index; "decision accuracy" is a consistency quantity in the measurement sense; the apex and corner-speed predictions cannot be falsified.
- Minor items: Part 2, Suggested Revisions.

#### Points of Disagreement

- **D3 scores differ between eligible seats.** DA scores block (repairable) and R1 scores warn. Under the contract the verdict is the worst eligible score (block). This is the arithmetic rule, not an arbitration. The two seats agree on substance. R1 scores the missing disconfirming outcome (SC-12) as a warn; the DA scores the estimator's contaminated reference (C1 / SC-10) as a block. R1 raises the same contamination under D1 (W3).
- **Characterisation of C1's consequence for a positive Δ.** The DA says the size of a positive Δ is "unbounded by the design". R1 and R3 describe the same bias as conservative: it pulls Δ toward zero, so it biases against detection and does not seal the result. These positions are compatible and do not conflict on whether the problem exists. **Editor's resolution:** C1 is validated as to existence and direction. The sharper claim that a positive Δ's size is unbounded has no corroboration from another seat, so the author is asked to state the direction of the bias and to quantify the absorption (see R5). The author is not asked to accept that a positive Δ is unbounded.

### DA-CRITICAL adjudication

**C1 — VALIDATED.**
- *DA's argument:* the null is fitted on cue-off laps "probe laps plus the unassisted block" (§5), which are exactly where dependency would appear. Any dependency effect is absorbed into P_null, biasing Δ toward zero, so a null Δ cannot tell "no dependency" apart from "dependency absorbed".
- *Corroboration:* three of the four non-DA seats raised the same mechanism independently of the DA card: R1 W3 (Major), R2 W2 (Major) and R3 W6 (Major, second part). The manuscript anchor was checked: §5 says "**Fitted on cue-off laps** (probe laps plus the unassisted block)", and §8 item 2 lists the circularity as open without resolving it.
- *Journal-Fit Reviewer's assessment:* the eic card does not address the null's statistics, which its configuration card names as a blind spot. The validation therefore rests on the R1/R2/R3 corroboration and on the anchor, not on an eic judgement.
- *Required author response:* address it in R5 below. The author may decline a remedy, but must respond to the finding visibly.

### Decision Rationale

The decision follows mechanically from condition F2. Two mandatory dimensions carry a repairable block. D1 is blocked because R1 finds that the core inferential quantity, P_null, rests on a null model with three per-element components and an undecided trend form, fitted to sparse cue-off data that are concentrated in time (SC-7). D3 is blocked because the DA finds that the estimator's reference distribution can absorb the effect it is meant to exclude (C1), and three non-DA seats agree (SC-10). F3 also fires, since four mandatory dimensions are at warn or worse, and its action is the same.

Every seat treats the problems as repairable before any participant drives, and none declared a fatal block. The brief's strengths are recognised across the panel. Its novelty claim is narrow and disciplined (eic S1). Regression to the mean under selection is named as the right rival (R1 S1, R2 S1). It commits in advance not to report Δ if the null fails its check (eic S3, R1 S2). Its non-claims match what the design can support (R2 S2, R3 S1). Its logging allows P_null to be recomputed offline (R1 S6). That last point matters: R1 notes that most remedies are simulation or pre-specification work on machinery that already exists, not new data collection.

What has to change is the specification of the null and its check (SC-7, SC-8, SC-9, SC-10, SC-13). The core inferential claim also needs a pre-data decision rule (SC-12) and an outcome-by-outcome statement of what will be reported (SC-1). The construct name for Δ must move from "guidance dependency" to something the design can support (SC-15, SC-19). The brief should come back for re-review after revision.

### Blocking Issues (immutable source order)

| Transport ref | Blocking issue | Source reviewer(s) | Evidence anchor | Resolving roadmap item |
|---|---|---|---|---|
| R2 | The null model is not shown to be identifiable from the cue-off data volume, so P_null has no demonstrated stable reference (drives D1 block) | R1 (methodology) | text: §5 "per element (form still open: F5/F6)" and "a practice trend (per-driver slope or saturating curve);" | REV-R2 |
| R5 | The null is fitted on cue-off laps where dependency would show, so Δ is biased toward zero and a null Δ is uninterpretable (drives D3 block) | DA C1; R1 W3; R2 W2; R3 W6 | text: §5 "probe laps plus the unassisted block" | REV-R5 |
| R6 | No pre-data decision rule or resolvable-Δ statement for the one element where Δ is claimed identifiable (drives D3 warn) | R1 W5; R3 W4; DA M2 | text: §6 "braking the candidate for a detectable excess; corner speed no claim until the pilot." | REV-R6 |

---

## Part 2: Revision Roadmap

> Items are in immutable source order: the eic card first, then R1 (methodology), R2 (domain) and R3 (perspective), each in finding order, with DA-only items last. Source order is not a ranking or a work order. **Transport refs `R1..R9` are roadmap references, not reviewer seats.** In the Source column, seats are written out (eic / R1-methodology / R2-domain / R3-perspective / DA) to avoid collision. No block manifest was bound, so targets are given as manuscript section locators, not block ids. The roadmap says WHAT must change and WHY. The author writes all replacement text, and nothing here drafts it.

### Required Revisions (Must Fix)

| Transport ref | Revision Item | Sub-Claim(s) | Severity | Evidence Anchor | Confidence | Source | Obligation class | Cost scope | Bounded consequence |
|---|---|---|---|---|---|---|---|---|---|
| R1 | State, before data, what the thesis reports under each RQ2 outcome (Δ > 0, Δ ≈ 0, model check failed), because two of three elements are predicted uninformative and the check can withdraw Δ entirely | SC-1 | major | text: §6 "apex uninformative by design; braking the candidate for a detectable excess; corner speed no claim until the pilot." | 4 — editorial judgement of reportability | eic W1 | must_fix | section: §4 RQ2 / §6 predictions | claim_scope_unsupported → claim: RQ2 core contribution |
| R2 | Show that the null model can be identified from the stated cue-off data volume and probe timings, and pre-specify how its form is selected, because P_null is the reference for the core claim and its form is still open | SC-7 | critical | text: §5 "per element (form still open: F5/F6)" and "a practice trend (per-driver slope or saturating curve);" | 4 — random-intercept/trend and simulation-null competence; volumes read from the brief | R1-methodology W1 | must_fix | re_analysis: pre-data parameter-recovery simulation on the committed novice model (R1's minimum remedy) | evidence_gap_remains → claim: P_null as a defined reference |
| R3 | Resolve the conflict between the model check and the reason for fitting on cue-off laps, because a correctly fitted null is predicted to fail the check as written | SC-8 | major | text: §5 "the null must reproduce observed cue-on statistics (lap-to-lap SD, qualification rate, timing of first qualification)" | 4 (R1) / 3 (R3) | R1-methodology W2; R3-perspective W6; DA M1 | must_fix | section: §5 model check | interpretive_ambiguity_remains → section: §5 |
| R4 | Give the model check a stated tolerance and a rule for which statistics must match, because "reproduce" is not yet a decision rule | SC-9 | major | text: §5 "the null must reproduce observed cue-on statistics (lap-to-lap SD, qualification rate, timing of first qualification)" | 4 — internal logic | R1-methodology W2 | must_fix | section: §5 model check | acceptance_criterion_unmet → section: §5 |
| R5 | Address the absorption of any dependency effect into P_null. State the direction of the bias and either fit on data that cannot contain the effect or quantify how much a given dependency size inflates the fitted parameters | SC-10; DA C1 | major (non-DA seats); DA band CRITICAL | text: §5 "probe laps plus the unassisted block" (DA); text: §8 item 2 "The null is fitted on cue-off laps from the same participants whose probe failures it judges." (R1); text: §5 "**Fitted on cue-off laps** (probe laps plus the unassisted block)." (R2) | 4 (R1, R2, DA) / 3 (R3) | R1-methodology W3; R2-domain W2; R3-perspective W6; DA C1 | must_fix | re_analysis: alternative fit sets or an absorption simulation; seats offer compatible options | evidence_gap_remains → claim: interpretability of Δ |
| R6 | Pre-specify the inferential rule for braking Δ (excess / no excess / indeterminate), the minimum Δ of interest, and the smallest Δ resolvable at the clustered probe count, because otherwise no outcome counts against the prediction | SC-12 | major | text: §6 "braking the candidate for a detectable excess; corner speed no claim until the pilot." (R1); text: §6 "apex uninformative by design; braking" (R3) | 4 (R1, R3) | R1-methodology W5; R3-perspective W4; DA M2 | must_fix | re_analysis: simulated design-sensitivity figure, with no value asserted for the real data | acceptance_criterion_unmet → claim: pre-registered braking prediction |
| R7 | Pre-specify one rule for how censored (mid-probe) probes enter P_obs, applied identically to the simulated P_null, with sensitivity to the alternatives, because the choice shifts the numerator in a trend-dependent direction | SC-13 | major | text: §8 item 5 "how censored blocks (ending mid-probe) enter P_obs" | 4 — censoring over a fixed lap budget | R1-methodology W6; DA M5 | must_fix | section: §4 RQ2 / §5 | method_reproducibility_unresolved → claim: P_obs definition |
| R8 | Scope the construct reported for Δ to what the null excludes, and name withdrawal-as-intervention (surprise, attention, the immediate withdrawal dip) as an unexcluded rival, because the null cannot represent it and the design has no contrast that separates it | SC-15 | major | text: §8 item 1 "Removing a cue may itself change behaviour (surprise, attention shift), apart from dependency." (R1); text: §4 RQ2 "It is *interpreted* as **guidance dependency** (cue plus KR, withdrawn together); it is not measured as such." (R2) | 3 (R1) / 4 (R2) | R1-methodology W8; R2-domain W1; DA M3 | must_fix | section: §1, §4 RQ2, §7 | claim_scope_unsupported → claim: "guidance dependency" reading of Δ |
| R9 | Add the learning–performance distinction: in the field, "dependency" is judged on retention or transfer after transient effects dissipate, while the 2-lap probe and the 4-lap unassisted block are immediate, within-session tests. This is the rival account the D2 warn names | SC-19 | major | text: §4 RQ2 "It is *interpreted* as **guidance dependency** (cue plus KR, withdrawn together); it is not measured as such." | 4 — guidance-hypothesis and retention-test conventions | R2-domain W1 | must_fix | section: §1, §4 RQ2 (a delayed test is offered as a costlier option the author may choose) | claim_scope_unsupported → claim: construct label for Δ |

### Suggested Revisions (Should Fix / Consider)

| Transport ref | Revision Item | Sub-Claim(s) | Severity | Evidence Anchor | Confidence | Source | Obligation class | Cost scope | Bounded consequence |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Link each Δ outcome to a concrete design implication for fading controllers, within the §7 "Never claimed" limits | SC-2 | major | absence: §1–§8 — expected a statement of what an adaptive-system designer would change in a fading rule given a positive or a null probe-failure excess; checked §1 problem, §4 RQ2, §5 null, §6 predictions, §7 claimed novelty, §8 open questions | 4 | eic W2 | should_fix | section: §1 / §7 | claim_scope_unsupported → claim: designer significance |
| S2 | Consider framing the per-element probe-and-revert controller as what makes post-withdrawal evidence exist, so the audit reads as design rationale | SC-3 | minor | text: §4 "Supporting evidence, not a research contribution." | 3 | eic W3 | consider | section: §4 RQ3 | interpretive_ambiguity_remains → section: §4 |
| S3 | Expand internal labels (F2, F5/F6, "v9 threat n", "the committed novice model") at first use, or add a glossary | SC-4 | minor | text: §5 "form still open: F5/F6" | 5 (eic) / 3 (R3) | eic W4; R3-perspective W7 | should_fix | sentence: first use of each label | reader_traceability_reduced → manuscript |
| S4 | Give full bibliographic entries for TRACK 2026, Eneano et al. 2026, Linden 2026, Ye et al. 2016 and ARRS | SC-5 | minor | absence: manuscript reference list — expected full bibliographic entries for TRACK 2026, Eneano et al. 2026, Linden 2026, Ye et al. 2016 and ARRS; checked §1, §4, §6, §7, §8 and the document end | 3 (R2) / 5 (eic) / 3 (R3) | eic W4; R2-domain W6; R3-perspective W7 | should_fix | section: references | reporting_requirement_unmet → manuscript |
| S5 | Tag each figure with its source (repository-settled vs framing document), especially the simulator rates and the §6 counts | SC-6 | minor | text: header "Where v9's text is stale (3-of-4 window, two tracks, per-corner controller), this brief uses the repository's settled values." | 4 | eic W5 | consider | sentence: per figure | reader_traceability_reduced → section: §2, §6 |
| S6 | State whether the noise model includes a probe-vs-unassisted condition indicator and how the trend is extrapolated over cue-on laps, and include selection timing in the recovery study of R2 | SC-11 | major | text: §5 "(probe laps plus the unassisted block)" | 3 — inferred from §2 | R1-methodology W4 | should_fix | section: §5 noise model | interpretive_ambiguity_remains → section: §5 |
| S7 | State the unit of P_obs's denominator (presumably element-level probe entries) and use the same unit in P_null | SC-14 | minor | text: §4 "P_obs: the probe-failure rate over all guided-qualification events." | 3 | R1-methodology W7 | should_fix | sentence: §4 RQ2 | interpretive_ambiguity_remains → claim: P_obs definition |
| S8 | Mark corner-speed P_null = 0.00 as a boundary value (not a working null), and mark the apex prediction as model-conditional on n = 1 parameters | SC-16 | minor | text: §6 "the brake and speed sigmas are assumptions." | 4 | R1-methodology W9 | consider | section: §6 table | interpretive_ambiguity_remains → table: §6 |
| S9 | Report stream counts, seed and Monte Carlo intervals for the simulator gate figures (8.5%, 0%, 79%) | SC-17 | minor | text: §2 "false fade for a non-improving learner: 8.5% (bound ≤ 10%);" | 4 | R1-methodology W10 | should_fix | sentence: §2 | method_reproducibility_unresolved → section: §2 |
| S10 | State which laps RQ1 is computed on and which of its quantities feed P_null | SC-18 | minor | text: §4 "RQ1 is also the calibration input for RQ2." | 3 | R1-methodology W11 | consider | sentence: §4 RQ1 | interpretive_ambiguity_remains → section: §4 |
| S11 | Re-categorise LC-CUSUM (Biau 2008) as a sequential competence-declaration test, and state how attribution differs from it | SC-20 | minor | text: §7 "regression-to-the-mean corrections (LC-CUSUM / Biau 2008; Ye et al. 2016; Linden 2026)" | 3 | R2-domain W3 | should_fix | sentence: §7 | claim_scope_unsupported → claim: §7 novelty positioning |
| S12 | Restate the guidance hypothesis in full rather than as the general learning–performance gloss | SC-21 | minor | text: §1 "Performance with guidance is not performance without it (the guidance hypothesis; Salmoni et al. 1984)." | 4 | R2-domain W4 | should_fix | sentence: §1 | interpretive_ambiguity_remains → section: §1 |
| S13 | Cite the premise that concurrent feedback lowers variability, and state that cue-on σ reflects cue plus KR | SC-22 | minor | text: §5 "concurrent feedback reduces movement variability while it is on, so a cue-on σ is plausibly biased low" | 4 | R2-domain W5 | should_fix | sentence: §5 | reporting_requirement_unmet → section: §5 |
| S14 | Name the ICC form and facets and the detrending model's degrees of freedom, report coefficients with CIs, and mark per-corner ICCs at n ≈ 15 as descriptive | SC-23 | major | text: §4 RQ1 "SEM, ICC and MDC of the metrics, for novices" | 4 | R3-perspective W1 | should_fix | section: §4 RQ1 | method_reproducibility_unresolved → claim: RQ1 |
| S15 | Report simulated decision consistency (p₀, κ) of per-corner qualification and the per-element quorum, as a function of distance from the band | SC-24 | major | text: §4 RQ1 "RQ1 is also the calibration input" | 5 | R3-perspective W2 | should_fix | re_analysis: on existing simulator machinery | evidence_gap_remains → claim: RQ1–RQ2 link |
| S16 | Relabel RQ2's "decision accuracy" as a cross-condition consistency quantity, keeping "accuracy" for the simulator where the latent state is known | SC-25 | major | text: §8.3 "v9 defines it relative to the system's own" | 4 | R3-perspective W3 | should_fix | section: §4 RQ2, §8 item 3 | interpretive_ambiguity_remains → claim: RQ2 label |
| S17 | Recognise that the apex prediction follows from P_null = 0.53 and the corner-speed one makes no prediction, so neither can be falsified; consider an equivalence region so that "no excess" is reportable | SC-26 | major | text: §6 "apex uninformative by design; braking" | 4 | R3-perspective W4 | should_fix | section: §6 predictions | acceptance_criterion_unmet → claim: pre-registered predictions |
| S18 | Name generalizability theory as a considered alternative frame for the crossed driver × corner × lap design, and say why the classical per-corner coefficients were preferred | SC-27 | minor | absence: §4 RQ1 and §5 — expected a variance-components / G-study frame with driver, corner and lap facets and a D-study for the window length; checked §2, §4, §5, §6, §8 | 4 | R3-perspective W5 | consider | section: §4 RQ1 | interpretive_ambiguity_remains → section: §4 |
| S19 | Make the separation promised in §1 and §7 model-conditional throughout, carrying the §6 concession forward | — (DA-only) | DA band MAJOR | text: §1 "A rule that reads only cue-on performance cannot separate the two." | 4 | DA M4 | should_fix | section: §1, §7 | claim_scope_unsupported → claim: §1 problem statement |
| S20 | Report probe yield per element across a plausible sigma range, and state a pilot stopping rule if braking yields too few probes | — (DA-only) | DA band MAJOR | text: §6 "so ~42 at n = 15, clustered" | 3 | DA M6 | should_fix | re_analysis: yield sensitivity on the committed model | evidence_gap_remains → claim: §6 feasibility counts |

### Source-Traceability Checklist

- [x] R1 — obligation `must_fix`: outcome-by-outcome reporting statement for RQ2 (eic W1). **Resolved 2026-10-30.** A pre-specified per-element table (brief §6) runs in order: ineligible → too few probes (floor set with S20) → model check failed → excess (construct read from the R8 time profile) → no excess (< MDI 0.10) → indeterminate (expected for braking at n = 15). The fallback is decided by the author: the headline is the attribution method, validated in simulation before data (the eic's "stronger option"), so it stands under every outcome. RQ1 is the second result. The claims sheet was updated to match (K1 scope, null fit, censoring, braking resolution).
- [x] R2 — obligation `must_fix`: null-model identifiability and form-selection rule (R1-methodology W1). **Resolved 2026-10-30.** Evidence: a parameter-recovery study, `kit/tools/nullrecovery.py`, with results in `kit/tools/README.md`. Decision: the primary null is an exponential trend with a pooled rate, per-driver amplitudes and per-driver σ, fitted on cue-off laps. The all-laps-trend fit is the sensitivity analysis. Braking Δ is gated on the pilot's braking σ ≤ 4 m. *Amended the same day by R5: the primary is now the cue-on null, and this cue-off null is reported as the lower bound.* The brief's prose still needs updating by the author.
- [x] R3 — obligation `must_fix`: reconcile the model check with the cue-off rationale (R1 W2, R3 W6, DA M1). **Resolved 2026-10-30.** The cue-off rationale is gone: the primary null is fitted on guided laps (see R5). The check now uses held-out guided-lap features, never cue-off statistics, which would reject the null exactly when dependency exists. See `CONCEPT_BRIEF_v9.md` §5. Its power was simulated (`kit/tools/nullcheck.py`): false alarm ~5%, and a wrong trend form is caught in ~40–50% of studies, stated as a limitation.
- [x] R4 — obligation `must_fix`: tolerance and match rule for the model check (R1 W2). **Resolved 2026-10-30.** All three checks must pass, each inside the central 98.3% (95% Bonferroni over three) of the fitted null's simulated distribution. There is one pre-specified escalation first (AR(1) / Student-t; none for check 2). An element that still fails has its Δ reported descriptively. A trend-form agreement gate was simulated and rejected. See `CONCEPT_BRIEF_v9.md` §5.
- [x] R5 — obligation `must_fix`: absorption of dependency into P_null (R1 W3, R2 W2, R3 W6, DA C1). **Resolved 2026-10-30.** Evidence: an absorption simulation, `kit/tools/nullabsorption.py`, with results in `kit/tools/README.md`. Decisions: a mean shift and a variance increase on withdrawal both count as dependency. The primary null is fitted on cue-on laps (unbiased: braking attenuation 1.01–1.04, RMSE 0.027). It was narrowed the same day to full-salience laps only, because reduced salience is a partial withdrawal and leaks 11–26% of braking Δ into the fit (RMSE 0.032). The cue-off null is reported as a lower bound, because it absorbs 20–80% of the effect. This supersedes R2's choice of primary. The brief's §5 and §8 item 2 still need updating by the author, and so does the construct text under R8/R9.
- [x] R6 — obligation `must_fix`: pre-data decision rule and resolvable Δ for braking (R1 W5, R3 W4, DA M2). **Resolved 2026-10-30.** Rule, per element, on a 90% participant cluster bootstrap: excess if the lower bound is above 0; no excess if the upper bound is below MDI 0.10 (tied to G1's ≤ 10% false-pass bound, author decision); otherwise indeterminate. Design sensitivity was simulated (`kit/tools/nulldecision.py`), with no value asserted for real data. For braking: false excess 4%; detection 45% at Δ 0.24 and 67% at Δ 0.37 (80% needs Δ ≳ 0.4); indeterminate is the expected verdict under no dependency. Brief updated: §6, §8 item 5.
- [x] R7 — obligation `must_fix`: censoring rule for P_obs and P_null (R1 W6, DA M5). **Resolved 2026-10-30.** Censored probes are excluded from P_obs and P_null alike, the count is reported, and as-pass and as-fail are sensitivity analyses (author decision). Simulated: 12–20% of braking probes are censored, and every rule is unbiased against its own true Δ when applied identically (|bias| ≤ 0.02). The feared trend-dependent bias cancels; the rules differ only in Δ's scale. Brief updated: §4.
- [x] R8 — obligation `must_fix`: construct scope for Δ against the withdrawal-transient rival (R1 W8, R2 W1, DA M3). **Resolved 2026-10-30.** Δ is reported as a probe-failure excess. Guidance dependency is a **sustained** withdrawal deficit, and the withdrawal-as-intervention rival is a **transient** one. A pre-specified time profile decides between them: probe decay (first probe lap − second) and the late-unassisted level. Simulated (`kit/tools/nulltransient.py`): for braking it separates them in 74–100% of studies at ~5% false alarm. The reading is asymmetric (a decay is also consistent with fast re-acquisition), and apex gets no reading. Brief updated: §1, §4 RQ2, §5, §7, §8 item 1.
- [x] R9 — obligation `must_fix`: learning–performance distinction and the immediate nature of the tests (R2 W1). **Resolved 2026-10-30, by scoping, with no protocol change (author decision).** The probe and unassisted block are named as immediate, within-session no-feedback tests. The construct is *immediate* guidance dependency, i.e. a deficit sustained across the ~4-lap window. It is performance-level, and dependency in the learning sense is explicitly never claimed (Salmoni et al. 1984; Winstein & Schmidt 1990; Kantak & Winstein 2012). A delayed retention block was considered and not adopted. Brief updated: §3, §4 RQ2, §5, §7. CLAUDE.md's "retention test" wording for the probe is corrected.
- [ ] S1 — obligation `should_fix`: designer implication of each Δ outcome (eic W2)
- [ ] S2 — obligation `consider`: system as design rationale for the audit (eic W3)
- [ ] S3 — obligation `should_fix`: expand internal labels (eic W4, R3 W7)
- [ ] S4 — obligation `should_fix`: full references (eic W4, R2 W6, R3 W7)
- [ ] S5 — obligation `consider`: per-figure source tags (eic W5)
- [ ] S6 — obligation `should_fix`: condition indicator and trend extrapolation in the noise model (R1 W4)
- [ ] S7 — obligation `should_fix`: unit of P_obs's denominator (R1 W7)
- [ ] S8 — obligation `consider`: corner-speed boundary value; apex prediction conditional on n = 1 (R1 W9)
- [ ] S9 — obligation `should_fix`: simulator run size and intervals (R1 W10)
- [ ] S10 — obligation `consider`: RQ1 lap subset and its feed into P_null (R1 W11)
- [ ] S11 — obligation `should_fix`: re-categorise LC-CUSUM (R2 W3)
- [ ] S12 — obligation `should_fix`: full statement of the guidance hypothesis (R2 W4)
- [ ] S13 — obligation `should_fix`: cite the variability premise; cue plus KR (R2 W5)
- [ ] S14 — obligation `should_fix`: ICC form, facets, precision (R3 W1)
- [ ] S15 — obligation `should_fix`: decision-consistency index (R3 W2)
- [ ] S16 — obligation `should_fix`: "accuracy" vs consistency label (R3 W3)
- [ ] S17 — obligation `should_fix`: falsifiability of the apex and corner-speed predictions (R3 W4)
- [ ] S18 — obligation `consider`: G-theory as a considered alternative (R3 W5)
- [ ] S19 — obligation `should_fix`: model-conditional separation in §1/§7 (DA M4)
- [x] S20 — obligation `should_fix`: probe-yield sensitivity and pilot stopping rule (DA M6). **Resolved 2026-11-01.** Floor = 7 pooled uncensored probes (post hoc; `kit/tools/nullyield.py`). The pilot σ ≤ 4 m gate is also the yield rule (P(K ≥ 7) ≥ 0.93). Brief §6 updated.

### Response Letter Template

Respond to every item above, R1–R9 and S1–S20, using `templates/revision_response_template.md`. For each item, say whether you accepted, partly accepted or declined it, what changed and where, and give your reasoning for any decline. A declined must_fix item stays visible as unresolved at re-review. DA C1 needs an explicit response under R5 even if a remedy is declined. Author triage and display order belong in the separate author sidecar, not in this roadmap.

---

## Part 3: Reviewer Report Summary (Appendix)

### Step 1a — Reviewer Summary Matrix

| Dimension | Journal-Fit (eic) | R1 (Methodology) | R2 (Domain) | R3 (Perspective) |
|---|---|---|---|---|
| Contract scores (eligible) | D5 warn, D6 warn | D1 block (repairable), D3 warn | D2 warn | D4 warn |
| Confidence / scope disclosure | Per finding 3–5; blind spot: statistics of the null | Per finding 3–4; blind spot: psychology of probe withdrawal | Per finding 3–4; cannot verify TRACK 2026, Eneano, Linden, Ye, ARRS | Per finding 3–5; blind spot: sim-racing domain |
| Key strengths | S1 narrow novelty; S2 real confound; S3 honest gate on Δ; S4 organisation | S1 rival named correctly; S2 non-report rule; S3 Δ labelled model-based; S4 per-element unit defended; S5 cluster bootstrap; S6 offline-replayable logs | S1 framing; S2 non-claims; S3 cue+KR construct | S1 non-claims; S2 Δ as interpretation; S3 detrending; S4 unfavourable nulls reported |
| Key weaknesses | → Step 1b (W1–W5) | → Step 1b (W1–W11) | → Step 1b (W1–W6) | → Step 1b (W1–W7) |
| Critical / Major / Minor | 0 / 2 / 3 | 1 / 6 / 4 | 0 / 2 / 4 | 0 / 4 / 3 |

### Step 1b — Weakness Sub-Claim Inventory

Silent seats (`not-mentioned`) are left out of each row for brevity. The denominator for every consensus label is the four non-DA seats. No row has a `disputed` position. Severity and confidence are transported from the cards.

| sub_claim_id | parent_weakness | reviewer_id | position | evidence_pointer | severity | confidence |
|---|---|---|---|---|---|---|
| SC-1 | eic W1 reportable result | eic | raised | text: §6 "apex uninformative by design; braking the candidate…" | major | 4 |
| SC-2 | eic W2 designer implication | eic | raised | absence: §1–§8 — expected a statement of what an adaptive-system designer would change… | major | 4 |
| SC-3 | eic W3 system demoted | eic | raised | text: §4 "Supporting evidence, not a research contribution." | minor | 3 |
| SC-4 | eic W4 / R3 W7 internal shorthand | eic | raised | text: §5 "form still open: F5/F6" | minor | 5 |
| SC-4 | " | R3 | corroborated | text: §5 "form still open: F5/F6" | minor | 3 |
| SC-5 | eic W4 / R2 W6 / R3 W7 missing references | eic | raised | eic W4 body ("TRACK 2026 … not cited in full") | minor | 5 |
| SC-5 | " | R2 | corroborated | absence: manuscript reference list — expected full bibliographic entries… | minor | 3 |
| SC-5 | " | R3 | corroborated | R3 W7 body (TRACK 2026 lacks bibliographic identity) | minor | 3 |
| SC-6 | eic W5 source reconciliation | eic | raised | text: header "Where v9's text is stale…" | minor | 4 |
| SC-7 | R1 W1 null identifiability | R1 | raised | text: §5 "per element (form still open: F5/F6)"… | critical | 4 |
| SC-8 | R1 W2 / R3 W6 check contradicts rationale | R1 | raised | text: §5 "the null must reproduce observed cue-on statistics…" | major | 4 |
| SC-8 | " | R3 | corroborated | text: §5 "the null must reproduce observed cue-on statistics" | major | 3 |
| SC-9 | R1 W2 check lacks tolerance | R1 | raised | R1 W2 body ("no stated tolerance") | major | 4 |
| SC-10 | R1 W3 / R2 W2 / R3 W6 absorption bias | R1 | raised | text: §8 item 2 "The null is fitted on cue-off laps…" | major | 4 |
| SC-10 | " | R2 | corroborated | text: §5 "**Fitted on cue-off laps** (probe laps plus the unassisted block)." | major | 4 |
| SC-10 | " | R3 | corroborated | R3 W6 body ("P_null absorbs part of the effect and Δ is biased toward zero") | major | 3 |
| SC-11 | R1 W4 mixed conditions / selection timing | R1 | raised | text: §5 "(probe laps plus the unassisted block)" | major | 3 |
| SC-12 | R1 W5 / R3 W4 no decision rule for braking | R1 | raised | text: §6 "braking the candidate for a detectable excess…" | major | 4 |
| SC-12 | " | R3 | corroborated | text: §6 "apex uninformative by design; braking" | major | 4 |
| SC-13 | R1 W6 censoring | R1 | raised | text: §8 item 5 "how censored blocks (ending mid-probe) enter P_obs" | major | 4 |
| SC-14 | R1 W7 denominator unit | R1 | raised | text: §4 "P_obs: the probe-failure rate over all guided-qualification events." | minor | 3 |
| SC-15 | R1 W8 / R2 W1 withdrawal-transient rival | R1 | raised | text: §8 item 1 "Removing a cue may itself change behaviour…" | major | 3 |
| SC-15 | " | R2 | corroborated | R2 W1 body ("a temporary performance effect … is part of Δ by construction") | major | 4 |
| SC-16 | R1 W9 assumed sigmas / boundary null | R1 | raised | text: §6 "the brake and speed sigmas are assumptions." | minor | 4 |
| SC-17 | R1 W10 simulator figures lack run size | R1 | raised | text: §2 "false fade for a non-improving learner: 8.5% (bound ≤ 10%);" | minor | 4 |
| SC-18 | R1 W11 RQ1 lap subset | R1 | raised | text: §4 "RQ1 is also the calibration input for RQ2." | minor | 3 |
| SC-19 | R2 W1 dependency is a retention construct; tests are immediate | R2 | raised | text: §4 RQ2 "It is *interpreted* as **guidance dependency**…" | major | 4 |
| SC-20 | R2 W3 LC-CUSUM miscategorised | R2 | raised | text: §7 "regression-to-the-mean corrections (LC-CUSUM / Biau 2008…" | minor | 3 |
| SC-21 | R2 W4 guidance-hypothesis gloss | R2 | raised | text: §1 "Performance with guidance is not performance without it…" | minor | 4 |
| SC-22 | R2 W5 uncited variability premise; cue+KR | R2 | raised | text: §5 "concurrent feedback reduces movement variability while it is on…" | minor | 4 |
| SC-23 | R3 W1 ICC form and precision | R3 | raised | text: §4 RQ1 "SEM, ICC and MDC of the metrics, for novices" | major | 4 |
| SC-24 | R3 W2 no decision-consistency index | R3 | raised | text: §4 RQ1 "RQ1 is also the calibration input" | major | 5 |
| SC-25 | R3 W3 "accuracy" vs consistency | R3 | raised | text: §8.3 "v9 defines it relative to the system's own" | major | 4 |
| SC-26 | R3 W4 apex / corner-speed predictions unfalsifiable | R3 | raised | text: §6 "apex uninformative by design; braking" | major | 4 |
| SC-27 | R3 W5 G-theory not considered | R3 | raised | absence: §4 RQ1 and §5 — expected a variance-components / G-study frame… | minor | 4 |

Dispositions: CONSENSUS-3 for SC-5 (R1 silent) and SC-10 (eic silent). Corroborated (2/4) for SC-4, SC-8, SC-12 and SC-15. Every other sub-claim is a single-reviewer finding (1/4). There is no CONSENSUS-4 and no SPLIT. Surface-form parity check: no sub-claim was down-rated or credited for its phrasing. The one sharper wording (the DA's "unbounded" positive Δ) was set aside because no other seat corroborated it, not because of its style.

### Journal-Fit Review Report Summary (eic)
- Scores: D5 warn, D6 warn | Confidence: 3–5 per finding; null statistics declared out of scope.
- Key point: the novelty claim is narrow and defensible. The weakness is reportability: what the thesis reports when Δ is withheld or null, and what designers would do with either result, is not stated.

### Reviewer 1 (Methodology) Summary
- Scores: D1 block (repairable), D3 warn | Confidence: 3–4 per finding.
- Key point: P_null rests on a null model not shown to be identifiable from the cue-off data. Its check conflicts with its own fitting rationale, its calibration data overlap the outcome they judge, and no pre-data decision rule says what would count against the braking prediction. All of this is repairable by simulation and pre-specification. Arithmetic receipts: `no_recomputable_statistics`, and the probe counts are internally consistent.

### Reviewer 2 (Domain) Summary
- Scores: D2 warn | Confidence: 3–4 per finding.
- Key point: the vocabulary is mostly used correctly, but the learning–performance distinction is missing. An immediate within-acquisition probe decrement is labelled with a retention-based construct, and cue-off calibration takes in the spread that the guidance hypothesis predicts withdrawal will cause.

### Reviewer 3 (Perspective) Summary
- Scores: D4 warn | Confidence: 3–5 per finding.
- Key point: imported measurement terms are under-specified for n ≈ 15. The ICC form is unnamed, no decision-consistency index links RQ1 to RQ2, and "decision accuracy" is a consistency quantity in the measurement sense. The predictions are not falsifiable as stated.

### Devil's Advocate Summary
- Scores: D3 block (repairable) | Recommendation: N/A — findings only.
- Key challenge: C1 (VALIDATED) — the null is fitted on the very cue-off laps where dependency would appear, so Δ is biased toward zero and a null Δ is uninterpretable. Majors M1–M6 cover the check/rationale conflict, identifiability on braking alone, withdrawal-transient and KR rivals, model-conditional separation, censoring, and probe yield as a model output. M1, M2, M3 and M5 are corroborated by non-DA seats; M4 and M6 are DA-only and are carried as S19 and S20.

## Attachment: Suggested-Reference Check (advisory, #1001)

Suggested-reference check (script output, not a reviewer finding; #1001)
Seats read: R2, R3 (partial).
Not read:
- R2: the report has no suggested-references block.
- R3: the report has no suggested-references block.
No suggested reference could be read.

## Attachment: Reviewer Claim Check (advisory, #1002)

## Attachment: Reviewer Claim Check (advisory, #1002)

The judge answered 36 of 36 findings from 5 reviewers: it marked 0 as contradicted, and 4 cannot be checked from the manuscript alone.

The author decides what to do with each row. This check does not change the decision, the consensus counts, or the Revision Roadmap. The judge is the session model; as this judge, the #1002 contrast test passed Claude Opus 5.5 and Claude Fable 5.1 (gpt-6-astra and Gemini 4 Argon passed it in part one, through other transports); other models are untested.

## Attachment: Acronym Check (advisory, #849)

### Acronym check (advisory; no reply needed)
Coverage: body (partial)
Not in this input: English abstract, Chinese abstract.

| Scope | Line | Rule | Acronym | Uses |
|---|---|---|---|---|
| Body | 3 | Not defined | CS | 1 |
| Body | 3 | Not defined | HCI | 1 |
| Body | 6 | Not defined | CLAUDE | 1 |
| Body | 12 | Not defined | VR | 1 |
| Body | 29 | Not defined | TRACE | 2 |
| Body | 40 | Not defined | AI | 1 |
| Body | 41 | Not defined | RMS | 1 |
| Body | 63 | Not defined | RQ1 | 2 |
| Body | 64 | Not defined | ICC | 1 |
| Body | 64 | Not defined | MDC | 1 |
| Body | 64 | Not defined | SEM | 1 |
| Body | 67 | Not defined | RQ2 | 2 |
| Body | 76 | Not defined | RQ3 | 1 |
| Body | 121 | Not defined | CUSUM | 1 |
| Body | 121 | Not defined | LC | 1 |
| Body | 123 | Not defined | ARRS | 1 |
