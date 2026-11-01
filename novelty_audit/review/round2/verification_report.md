[LEGACY-NO-CONTRACT]

# Verification Review Report

**Manuscript:** TRACE v9 concept brief for methodological review (`novelty_audit/review/CONCEPT_BRIEF_v9.md`), re-reviewed against the round 1 roadmap (`round2/roadmap_round1.md`).

## Judge Record (#539)

- **Verification judge:** claude, Opus 5.5 (`claude-opus-5-5`). This is the session's own model. **It is the same model family that produced the revisions.**
- **Round-1 panel provenance:** status invalid, all six axes unknown.
  - Reason: no `review-panel-provenance/1.0` artifact exists. Round 1 could not build one; the cause was a CRLF pin-check failure, recorded in synthesis.md under "Review Panel Provenance".
  - Execution facts stated in round 1: one model family (claude) and one provider (anthropic) for all five seats; peer-output visibility unknown; no human reviewer.
- **Blind cross-model pass:** not_configured.
- **Pre-committed criteria:** none (legacy — no contract). The per-item operational criteria were fixed in Phase 2A (`round2/phase2a_verdicts.md`) before the response letter was read.
- **Prompt/rubric surfaces:** `academic-paper-reviewer/references/re_review_mode_protocol.md` (3.24.0), applied by hand, with no checker run. Sections used:
  - Three-Gate Orchestration (Phase 2A/2B);
  - Decision Derivation (B1–B6);
  - New-Issue Attribution;
  - Verifier Routing;
  - Re-Review Output Format.
- **Reviewer configuration:** round1_cards_reused.
- **Routing:** card_mapped. Each item goes to the first non-DA label in its Source column. consider and DA-only items go to EIC.
- **Apply-report chain:** not_run_no_reports. The change summaries come from a direct comparison of `round1/manuscript.md` with the revised brief.
- **Evidence seen by the judge:**
  - **Phase 2A:**
    - the revised manuscript and the original manuscript;
    - the roadmap, synthesis.md lines 1–125, and the cards;
    - the five p2 findings files;
    - `kit/tools/README.md` §§ nullrecovery–nullyield;
    - spot reads of `nullcheck.py` and `nullabsorption.py`;
    - `CLAIMS_SHEET_v9.md` and `G1_REVIEW.md` lines 1–30.
  - **Phase 2B:** in addition, the Response to Reviewers and synthesis.md lines 169–200.
  - No simulations were run.
- **Judging budget:** about 25 tool calls in one context, across Phase 2A and Phase 2B. No calls were spent on generation.

This verification round ran on the same model family that drove the revisions; over-optimization to this judge's latent biases is possible (Ren et al. 2026, arXiv:2607.13104 §8.1.2).

## Decision

**Major Revision.** Rule **B3** fired: two new issues introduced by the revision (NEW-1 and NEW-2) are graded **major**. `reject_recommended: false`.

## Adjustments

None. Wherever the letter's claim differed from a Phase 2A verdict, I re-read the manuscript. Each time, the manuscript supported the Phase 2A verdict, so every final verdict equals its Phase 2A verdict.

## Revision Response Checklist

### must_fix — Required Revisions

| Transport ref | Original Review Comment | Author triage | Author's Claim | Response Status | Revision Location | Verified? | Cross-model (#539) | Quality Assessment |
|---|---|---|---|---|---|---|---|---|
| R1 | State before data what is reported under each RQ2 outcome (eic W1) | will_address | A pre-specified per-element table runs ineligible → too few → check failed → excess → no excess → indeterminate. The headline is the attribution method validated in simulation, so it stands under every outcome. RQ1 is the second result. | FULLY_ADDRESSED | §6 outcome table; §6 "What stands regardless" | ✅ Yes | not_configured | The claim matches the manuscript. |
| R2 | Show the null is identifiable from the data volume; pre-specify the form-selection rule (R1 W1, critical) | will_address | Parameter-recovery study `nullrecovery.py`. The primary null was first chosen as the cue-off pooled-rate null, then amended by R5 to the cue-on null. Braking Δ is gated on σ ≤ 4 m. The letter also says "The brief's prose still needs updating". | PARTIALLY_ADDRESSED (residual should_fix) | §5 noise model, pilot gate, trend sensitivity; §8 item 4 | ◐ Partial | not_configured | **Kept.**<br>• The evidence the letter cites, `nullrecovery.py`, tests the cue-off, hybrid and unassisted fit sets at 0.5×, 1× and 2× noise. It does not test the primary full-salience null. That null's recovery comes only from `nullabsorption.py`, at 1× noise with an exponential truth.<br>• So the brief's sentences "at twice the committed braking σ no form recovers" and "the highest noise level at which the null recovered" are not established for the primary null.<br>• Recovery of the rate and σ parameters themselves is not reported.<br>• The letter's statement that the prose is not yet updated is stale: the brief has been updated. |
| R3 | Resolve the conflict between the model check and the cue-off rationale (R1 W2, R3 W6, DA M1) | will_address | The cue-off rationale is gone and the check uses "held-out guided-lap features". A wrong trend form is caught in about 40–50% of studies. | FULLY_ADDRESSED | §5 model check | ✅ Yes | not_configured | The conflict is gone. The letter repeats two inaccuracies, which stay recorded as NEW-4 and NEW-5:<br>• only check 1 is held out;<br>• 40–50% is the detection rate before escalation, and about 35% after it. |
| R4 | Give the model check a tolerance and a match rule (R1 W2) | will_address | All three checks must fall inside the 98.3% band, with one escalation and none for check 2. The bracket was rejected. | FULLY_ADDRESSED | §5 Tolerance / Rule | ✅ Yes | not_configured | The claim matches the manuscript. |
| R5 | Address absorption of dependency into P_null (R1 W3, R2 W2, R3 W6, DA C1) | will_address | Mean shift and variance increase both count as dependency. The cue-on null is "unbiased: braking attenuation 1.01–1.04, RMSE 0.027", later narrowed to full salience (RMSE 0.032). The cue-off null is a lower bound that absorbs 20–80% of the effect. | FULLY_ADDRESSED | §5 primary null; lower bound; §8 item 2 | ✅ Yes | not_configured | The remedy is in place. The letter ties 1.01–1.04 and 0.027 to the full+reduced null. That confirms NEW-3: the brief's §6 and §8.2 assign those numbers to the full-salience primary, which measured 1.01–1.11. |
| R6 | Pre-specify the decision rule, the MDI, and the resolvable Δ for braking (R1 W5, R3 W4, DA M2) | will_address | The rule is a 90% participant cluster bootstrap with an excess / no excess (MDI 0.10) / indeterminate verdict. The design sensitivity was simulated, and 80% detection needs Δ ≳ 0.4. | PARTIALLY_ADDRESSED (residual should_fix) | §6 decision rule and sensitivity table; §5 Uncertainty | ◐ Partial | not_configured | **Kept.** The letter does not address the residual.<br>• §5 says P_null's parameter uncertainty is propagated. §6 bootstraps Δ̂ without refitting the null within each resample.<br>• The sensitivity results were computed for the §6 procedure, which the brief itself calls optimistic.<br>• The brief must commit to one procedure. |
| R7 | Pre-specify one censoring rule, applied identically (R1 W6, DA M5) | will_address | Censored probes are excluded on both sides and counted, with as-pass and as-fail as sensitivity analyses. All rules were unbiased (\|bias\| ≤ 0.02). | FULLY_ADDRESSED | §4 Censoring | ✅ Yes | not_configured | The claim matches the manuscript. |
| R8 | Scope the construct to what the null excludes; name withdrawal-as-intervention (R1 W8, R2 W1, DA M3) | will_address | Δ is reported as a probe-failure excess. Sustained means dependency and transient means the rival. A pre-specified time profile "separates them in 74–100% of studies at ~5% false alarm". The reading is asymmetric, and apex gets no reading. | PARTIALLY_ADDRESSED (residual should_fix) | §1; §4 RQ2; §7; §8 item 1 | ◐ Partial | not_configured | **Kept.** Scoping and naming the rival are done. The letter does not address three gaps:<br>• the brief states no test or α for the profile, and no rule for when both statistics are significant;<br>• "transient" is defined as one lap, and only a one-lap transient was simulated. For braking, which is visible at the end of training, a transient of two or more laps would read as dependency;<br>• the brief does not explain how a late-unassisted level measured on the block licenses a reading of the probe-level Δ. |
| R9 | Add the learning–performance distinction; the probe and the block are immediate tests (R2 W1) | will_address | Scoping only, with no protocol change. The construct is *immediate* guidance dependency, never dependency in the learning sense. A delayed block was considered and declined. | FULLY_ADDRESSED | §3; §4 RQ2; §7 | ✅ Yes | not_configured | The claim matches the manuscript. The broadening of the construct caused by the fit-set reversal is a separate problem, NEW-1. |

### should_fix — Suggested Revisions

No author response was given for S1–S19.

| # | Original Review Comment | Response Status | Notes |
|---|---|---|---|
| S1 | Link each Δ outcome to a designer implication (eic W2) | PARTIALLY_ADDRESSED (residual should_fix) | Author's claim: none. §6 row 4 gives an implication for "no excess". The excess and indeterminate outcomes get none. |
| S3 | Expand internal labels (eic W4, R3 W7) | **MADE_WORSE** | Author's claim: none. No label is expanded. New undecoded labels were added: G1, G2, M6, "pair 1", "review item S20". |
| S4 | Full references for TRACK 2026, Eneano, Linden, Ye, ARRS | NOT_ADDRESSED | Author's claim: none. There is still no reference list, and the newly added citations also lack entries. |
| S6 | Condition indicator; trend extrapolation; selection timing in the recovery study (R1 W4) | PARTIALLY_ADDRESSED (residual should_fix) | Author's claim: none. Selection timing is covered, because the recovery runs through the real controller. Still missing:<br>• how the trend is extrapolated forward from a full-salience fit window that ends at the first advance;<br>• whether the cue-off lower-bound null carries a condition indicator. |
| S7 | Unit of P_obs's denominator (R1 W7) | PARTIALLY_ADDRESSED (residual should_fix) | Author's claim: none. The unit is implied by the censoring rule and gate 1, but the §4 definition is unchanged. |
| S9 | Stream counts, seed and MC intervals for the §2 figures (R1 W10) | NOT_ADDRESSED | Author's claim: none. §2 is unchanged. |
| S11 | Re-categorise LC-CUSUM (R2 W3) | NOT_ADDRESSED | Author's claim: none. |
| S12 | State the guidance hypothesis in full (R2 W4) | NOT_ADDRESSED | Author's claim: none. The §1 gloss is unchanged. |
| S13 | Cite the variability premise; cue plus KR (R2 W5) | PARTIALLY_ADDRESSED (residual consider) | Author's claim: none. The premise no longer justifies a design choice. The variance-increase mode that the brief counts as dependency is still uncited. |
| S14 | ICC form, facets, df, CIs (R3 W1) | NOT_ADDRESSED | Author's claim: none. |
| S15 | Decision-consistency index p₀, κ (R3 W2) | NOT_ADDRESSED | Author's claim: none. |
| S16 | Relabel "decision accuracy" (R3 W3) | NOT_ADDRESSED | Author's claim: none. |
| S17 | Falsifiability; equivalence region (R3 W4) | PARTIALLY_ADDRESSED (residual should_fix) | Author's claim: none. The equivalence region is added. The braking prediction is still non-directional. |
| S19 | Make the separation model-conditional in §1 and §7 (DA M4) | PARTIALLY_ADDRESSED (residual consider) | Author's claim: none. §1 is done. §7's "Claimed" bullet is unchanged. |
| S20 | Probe yield across σ; pilot stopping rule (DA M6) | FULLY_ADDRESSED | Author's claim: yield across σ 2–8 m, a post hoc floor of 7, and the σ ≤ 4 m gate serving as the yield rule. This matches §6. The gate's own definition is a separate problem, NEW-2. |

**should_fix_addressed_rate** = 7/15 = **46.7%** (S1, S6, S7, S13, S17, S19, S20). That is below the 80% threshold.

### consider — Nice to Fix

| # | Original Review Comment | Response Status |
|---|---|---|
| S2 | Frame the controller as the design rationale for the audit | NOT_ADDRESSED |
| S5 | Per-figure source tags | PARTIALLY_ADDRESSED |
| S8 | Mark the corner-speed P_null as a boundary value; the apex prediction is conditional on n = 1 | NOT_ADDRESSED |
| S10 | State RQ1's lap subset and how it feeds P_null | NOT_ADDRESSED |
| S18 | G-theory as a considered alternative | NOT_ADDRESSED |

## New Issues (Discovered During Revision)

These records were frozen at the Phase 2A commit and are copied here without change. The letter cannot remove any of them. Where the letter concedes or repeats one, that is noted after the table.

| # | Attribution | Severity | Location | Description |
|---|---|---|---|---|
| NEW-1 | regression | **major** | §5 "calibrated on **guided** performance. Δ therefore includes the loss of any benefit the guidance gave while it was on."; §6 row 3 | The reversed fit set makes a sustained positive Δ the expected result for any cue that simply helps while it is visible. The brief then labels that result "immediate guidance dependency". The cost is disclosed in §5 and §8.2, but it is not carried into §1, §6 row 3, §7, the RQ2 question, or the braking prediction. |
| NEW-2 | regression | **major** | §5 "Pilot gate"; §6 "n = 2 pilot" | The braking σ gate is not operationally defined:<br>• it does not say which laps σ is measured on, which estimator is used, or how uncertainty is handled;<br>• its threshold equals the committed value, so at the design point it trips about half the time;<br>• if σ is measured on cue-off laps, it trips exactly when a variance dependency exists;<br>• "highest level recovered" is unshown for the primary null;<br>• the same gate is also the yield rule, and corner speed has no σ threshold. |
| NEW-3 | regression | minor | §6 "Unbiasedness … 1.01–1.04"; §8.2 "1.00–1.04"; §5 "0.22–0.82" | Numbers are attributed to the wrong null:<br>• the primary full-salience null measured 1.01–1.11; the ranges the brief quotes belong to the full+reduced null;<br>• the lower bound's maximum, 0.82, comes from the lopo column;<br>• the RMSEs quoted are drawn from two different runs. |
| NEW-4 | regression | minor | §5 "caught only by check 1, in about 40–50% of studies" | After escalation, a wrong trend is caught in about 35% of studies. The check-1 escalation fits heavier tails, not a corrected trend, and so it leaves a harmful misspecification in place. |
| NEW-5 | regression | minor | §5 "Model check (pre-specified, held-out)"; check 2 | Only check 1 is held out. "While the cue is still on" is ambiguous about reduced salience; the code restricts the check to full salience. The power simulation used \|z\| > 2.39 at M = 60, not the specified 98.3% empirical interval. |
| NEW-6 | regression | minor | §4 "late-unassisted level … laps 2–4" | The statistic that licenses the dependency reading (the late-unassisted level) is the farthest trend extrapolation. It was simulated only under a correctly specified null. |
| NEW-7 | regression | minor | §6 "tied to Gate G1's false-pass bound" | The MDI equates a per-stream false-fade rate with a per-probe excess. |
| NEW-8 | regression | minor | §6 yields | §6 gives three braking yields (16, about 12, median 10) and two apex yields (11, about 8), and does not reconcile them. |
| NEW-9 | regression | minor | §6 "attribution method, validated in simulation" | What the simulation shows is self-consistency under the simulator's own model, not validation against real data. "Verified under the simulator's model" would be accurate. This is within the scope of CLAIMS_SHEET K1. |
| NEW-10 | previously_missed | minor | §2 "8.5%", "0%" (both versions) | These do not match the 5.75% and 0.75% in G1_REVIEW. They may be an unlabelled pair-1 split. |

**What the letter concedes or repeats:**
- **R5:** it ties 1.01–1.04 and RMSE 0.027 to the full+reduced null. That concedes the factual basis of NEW-3.
- **R3:** it repeats "held-out" and "40–50%" (NEW-4, NEW-5).
- **R6:** it cites the "G1 ≤ 10% false-pass bound" link as an author decision (NEW-7).
- **R5:** it says the construct text "under R8/R9" needs updating to state that Δ now includes the on-guidance benefit. The brief added that sentence to §5 only, which leaves NEW-1 open.
- None of these concessions changes a record.

## Decision Rationale

The rules were applied by hand.

- **Step 1 (gates):** none applies. There are no silent verdict changes, because the adjustment set is empty and every final verdict equals its Phase 2A verdict. There are no dissents, no pending escalation exceptions, and no cross-model rows.
- **Step 2 (base decision):**
  - **B1 does not fire.** No must_fix item is MADE_WORSE, and no regression is critical.
  - **B2 does not fire.** No must_fix item is NOT_ADDRESSED or MADE_WORSE (0 of 9).
  - **B3 fires.** NEW-1 and NEW-2 are `regression`-attributed issues of major severity. That makes the base **Major Revision**.
  - B4 would not fire on its own, because no residual is graded must_fix.
  - The B5 conditions also hold, but they cannot change a base that B3 already sets. They are: three must_fix items PARTIAL with should_fix residuals, a should_fix_addressed_rate of 46.7%, S3 MADE_WORSE, and seven minor regressions.
- **Step 3 (floors):** there are no approved escalation exceptions, so the decision stays **Major Revision**.

**The must_fix work was substantial and mostly sound.** Six of nine items are fully addressed with simulation evidence that matches `kit/tools/README.md`, and the remaining three are close. The decision is driven by what the revision added:

1. reversing the fit set changed what Δ measures, and the construct labels were not updated to match (NEW-1);
2. the new pilot gate now decides eligibility for the one informative element, and it has no operational definition (NEW-2).

The should_fix tier was mostly left untouched (7 of 15 addressed). Its items are cheap to fix and should be cleared in round 3.

## Residual Issues (If Any)

Prioritised for round 3. Items 1–2 are what moved the decision to Major. Items 3–5 are the must_fix residuals. Items 6–8 are needed to pass the 80% should_fix rule and to make the numbers consistent.

1. **NEW-1, the construct.**
   - Carry "Δ includes the loss of on-guidance benefit" into §1: add a fourth account, "the guidance still helps".
   - Carry it into the RQ2 question, the §6 row-3 label, §7, and the braking prediction.
   - Either rename the sustained-profile reading so it does not imply reliance beyond loss of the cue's benefit, or state explicitly that an effective cue produces Δ > 0 with no dependency, and say what Δ then adds to the design question.
2. **NEW-2, the pilot gate.** Define:
   - the laps σ is measured on (full-salience, consistent with the primary null);
   - the estimator (detrended per-driver residual SD, and how two drivers are pooled);
   - an uncertainty-aware trip rule, for example a CI bound against 4 m rather than a point estimate;
   - the corner-speed equivalent.
   Then remove or support "the highest level at which the null recovered".
3. **R2, recovery of the primary null.** Run the primary full-salience null across 0.5×, 1× and 2× noise and with a power-law truth. Report recovery of the rate and σ as well as P_null. Correct §5 and §8.4 to match.
4. **R6, the interval procedure.**
   - Choose one procedure: refit the null within each bootstrap resample, or propagate parameter uncertainty some other way.
   - Make §5 and §6 agree.
   - Re-run, or bound, the design sensitivity under the chosen procedure.
5. **R8 and NEW-6, the time-profile rule.**
   - State the test and α, and what is reported when both statistics are significant.
   - Simulate transients lasting two or more laps.
   - Explain how the block-level late level licenses a reading of the probe-level Δ.
   - Test the late-unassisted statistic under a power-law misspecification.
6. **Number fidelity.**
   - Fix NEW-3 (the attenuation and RMSE attributions), NEW-4 (about 35% detection after escalation, and the limitation of the Student-t escalation), NEW-5 (the "held-out" heading and the "full-salience" wording in check 2), NEW-8 (one reconciled yield table), and NEW-10 (label or correct 8.5% / 0%).
   - Add stream counts, seeds and MC intervals to the §2 figures (S9).
7. **should_fix items left untouched, all text-only.**
   - S3 (glossary), S4 (reference list), S16 (relabel "decision accuracy"), S12 (the full guidance hypothesis), S11 (recategorise LC-CUSUM).
   - S14 (ICC form, facets, CIs, and a "descriptive" label), S7 (one-sentence unit definition), S1 (designer implication for the excess and indeterminate outcomes).
   - S17 (a directional braking hypothesis), S19 (model-conditional wording in §7), S13 (a citation).
   - S15 needs a short simulation on existing machinery.
   - S6: state the forward extrapolation of the trend and the effect of a fit window truncated by selection.
8. **Wording.**
   - NEW-7: present the MDI's link to G1 as an analogy and justify 0.10 on its own terms.
   - NEW-9: "verified under the simulator's own model" in place of "validated".
   - The consider items (S2, S5, S8, S10, S18) can be recorded as limitations.
