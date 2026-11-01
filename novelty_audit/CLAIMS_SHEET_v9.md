# Claims sheet: what thesis v9 may and may not claim

**Date:** 2026-10-30 · **Built from:**
- `NOVELTY_AUDIT_v9.md` (pass 2)
- `STEP2_directions.md`
- the council verdict
- `STEP4_results.md`
- `kit/tools/README.md` § `percornerscan.py`

Evidence for the author, not chapter prose. The "may say" column gives the
*scope* of each claim, not its wording. Search coverage behind every
"not found": OpenAlex, web, and citation chasing. Semantic Scholar was mostly
rate-limited, and Scopus/WoS were not searched, so **"not found" never means
"does not exist."**

## 0. Terms (author decisions)

- **Probe-failure excess:** the measured quantity, P_obs − P_null.
- **Guidance dependency:** its *interpretation*. "Guidance" = the cue and its
  bandwidth KR, which are withdrawn together during a probe.
  - **Narrowed 2026-10-30 (ARS R8/R9):** the construct is *immediate*
    guidance dependency, a deficit sustained across the immediate no-feedback
    window. It is performance-level, not learning-level.
  - It is read only where the pre-specified time profile is sustained. A
    transient deficit is the withdrawal-as-intervention rival.
- **The null:** a learner with **learning (practice trend) and lap-to-lap noise,
  but no guidance dependency**.
  - **REVERSED 2026-10-30 (ARS R5):** it is fitted on **full-salience (cue-on)
    laps**, and the cue-off fit is reported as a lower bound.
  - The reason: the cue-off fit absorbs 20–80% of a real dependency, and the
    full-salience fit is unbiased (`kit/tools/nullabsorption.py`).
- **Direction:** B (the null method leads, RQ1 is its calibration input, RQ4 is
  cut, RQ3 goes into the system chapter). C-lite is dropped.

## 1. Contribution claims

| # | Claim | Status | May say (scope) | Must NOT say | Cite as |
|---|---|---|---|---|---|
| **K1** | Attributing post-withdrawal failures with a calibrated null | **Survives (step 4)**: the load-bearing novelty | The first use, among works found, of a calibrated learning-plus-noise null to attribute **post-withdrawal (probe) failures** in an adaptive guidance system, separating a probe-failure excess (read as *immediate* guidance dependency where the time profile is sustained) from regression to the mean under the system's own selection rule. **Headline contribution (2026-10-30, ARS R1):** the method is validated in simulation before data (recovery, unbiasedness under injected dependency, model-check power, decision calibration), so it stands whatever the empirical Δ verdict | That a simulated null, a Type I error under a null, or an RTM correction is new. All three are standard | **Lineage:** Biau et al. 2008 (LC-CUSUM; observes the post-signal dip, never attributes it); Ye et al. 2016 (non-learner-calibrated detection); Linden 2026 (closed-form single-cutoff case); Goldenholz et al. 2023 (simulated RTM under trial cutoffs). **Validity standard:** Käser & Alexandron 2023 |
| **K2** | Within-session reliability of per-corner sim-racing metrics (RQ1) | **Survives, gap confirmed** | Per-element ICC / SEM / MDC across corners, for novices, for brake point, apex line RMS and minimum corner speed, **detrended**. Fills the "first rung" TRACK names | "Sim-racing reliability has never been measured" | **Precedent:** Irwin, Mollica & Desbrow 2019 (t-test plus CV, one corner, unreliable); Irwin et al. 2013 (ICC, road driving). **Gap:** Çangırılı & Kurt 2026 (TRACK), §6. *Not* Hojaji 2025 (cross-track KPI consistency, not test-retest) |
| **K3** | Probe-gated fading (C1) | **Narrowed: the idea is taken** | The first **implemented, real-time, per-element** probe-gated fading of **concurrent visual cues in a motor task**, within one session | "No system uses cue-off performance to decide fading." **Do not lead with this claim** (council: the weakest kind of novelty) | **Idea:** Eneano et al. 2026 (preprint; proposed, unimplemented). **Cognitive analogue:** ARRS (Li 2013). **Revert-on-cue-off-degradation:** Kinesthetic-CPR (Dong et al. 2026). **Post-removal readiness:** Debeauvais et al. 2014 |
| **K4** | The system itself | Engineering contribution; not novelty-tested | A verified real-time controller with Lua/Python parity, world-anchored cues and bandwidth KR | That parity or real-time operation is a research finding | — |
| ~~K5~~ | ~~False-fade rates of published rules under a non-learner (C-lite)~~ | **Pre-empted for ITS** | Positioning only, if run at all | That pricing a rule under a non-learner is new | Ye et al. 2016; Biau 2008; Sims et al. 2013 |

## 2. Context claims (no novelty asserted)

| Claim | Status | Correct form | Cite |
|---|---|---|---|
| Premature withdrawal is a known risk | Verified | Systems guard against it **heuristically**: Shen's lower bound "prevents sudden drops"; Hsieh's opacity is clamped to [0.08, 0.8] | Shen et al. 2025; Hsieh et al. 2026 |
| Its rate has not been measured | **Narrowed** | It has been measured *elsewhere*. **Unmeasured** for system-initiated withdrawal of motor visual cues, split into dependency vs variability. Context rates (never compared with Δ): ARRS, 18–41% wrong at the 1-week retest; Forza, 38–80% of failed assist disables re-enabled after the very next race, 80% for the brake line | Li 2013 (ARRS) Table 3.1; Debeauvais et al. 2014; Pelánek & Řihák 2017/18; Zhang et al. 2025 |
| Adaptive support needs its adaptation source validated | Verified | Frames RQ2 as auditing the decision, not the learning outcome | Nickl et al. 2024, *Learning and Instruction* 94 |
| Guided performance is circular evidence of readiness | Verified (as an argument) | Credit the argument, don't claim it | Eneano et al. 2026 |
| Catch trials are measurement only in rehab assist-as-needed control | Verified | "Probe-as-measurement exists; probe-as-decision is our step" | Li et al. 2026 (TNSRE; N = 6 subset, excluded from the LMM); Emken et al. 2007 |
| Telemetry coaching in Assetto Corsa | Verified | Bugeja's tolerances **are** empirical and tighten "as the user improves"; it neither fades nor reverts; gains dissipated when feedback was switched off | Bugeja, Spina & Buhagiar 2017 |
| Concurrent feedback lowers variability during practice | Supported | Was the reason the null was fitted on cue-off laps. **Superseded 2026-10-30 (ARS R5):** under the author's definition, losing that concurrent benefit at withdrawal counts as dependency, so the null is fitted on full-salience laps | Postural-control studies; Frontiers 2025 |

## 3. Never claim (project rules plus audit)

- Statistical significance, a learning or retention benefit, or optimal thresholds.
- That probe failure **harms** learning (desirable difficulty; v9 §4.3).
- **Causal** guidance dependency. Without the randomised arm (out of reach:
  ~28 participants needed), Δ is model-based.
- Dependency on the **cue alone**: KR is withdrawn with it.
- Generalisation beyond one car and one track (pair 2 descoped) and this
  population.
- That the gates certify internalisation. They trigger a probe; the probe is
  the test.

## 4. State as limitations (each one is where an examiner will look first)

1. **The null is model-based**, and its brake and speed lap-to-lap sigmas are
   assumptions until the pilot (M7) measures them. The corner-speed null of 0.00
   rests entirely on the speed sigma.
2. **Trend misspecification** (v9 threat 2): with 15 laps, learning and noise
   are hard to separate.
3. **Precision.** About 42 probes at n = 15 under the committed model,
   **clustered** (~2.8 per participant). The pooled ±0.12 is optimistic before
   the cluster bootstrap; per element, ±0.2 or wider.
4. **Per element, the null predicts the shape.** Pre-register it:
   - apex (null 0.53): **uninformative by design**;
   - braking (0.16): the candidate for a detectable excess. **At n = 15 only
     Δ ≳ 0.4 is likely to be resolved**, and the expected verdict under no
     dependency is indeterminate (ARS R6, `kit/tools/nulldecision.py`);
   - corner speed (0.00): no claim until the pilot sigma is measured.
5. **Right-censoring.** Rule decided 2026-10-30 (ARS R7): censored probes are
   excluded from P_obs and P_null alike, with the count reported. As-pass and
   as-fail are sensitivity analyses. Every rule was simulated as unbiased when
   applied identically.
6. **Yield risk.** If real novices reach far fewer probes than simulated, Δ is
   not estimable. The pre-stated fallback is RQ1 plus the guided-vs-unassisted
   contrast from the 4-lap block.
7. **The controller decides per element and the analysis is per corner.** A
   per-corner controller fails both G1 safety bounds at every window tried
   (`percornerscan.py`). The per-corner breakdown uses the 8 cue-off corner
   passes each probe yields.
8. **The search's coverage**, as stated at the top of this sheet.

## 5. v9 edits this implies (author's prose; listed, not drafted)

| v9 location | Change |
|---|---|
| §1 one-line framing, §3 gap | Lead with K1, not K3. Replace "no system uses cue-off probe performance as the fading decision" with K3's scope |
| §4.1 RQ2 | Name the quantity "probe-failure excess" and its interpretation "guidance dependency" |
| §4.1 RQ3, RQ4 | RQ3 → system chapter evidence; RQ4 → cut or appendix |
| §5.2 controller | Per-element decisions, per-corner analysis; parameters to `frozen-g1b` (2-of-3, 2-lap probe), flag F8 |
| §6 study design | One track, one car; a single 15-lap training block plus the 4-lap unassisted block (both used by the null) |
| §7.2 noise model | ~~Fit on cue-off laps~~ **Fit on full-salience laps** (ARS R5); exponential trend, per-driver σ; model check with escalation (`CONCEPT_BRIEF_v9.md` §5) |
| §7.3 RQ2 | Add per-element pre-registered predictions (§4 item 4), the censoring rule, the three-way decision rule (MDI 0.10) and the outcome-by-outcome reporting table (`CONCEPT_BRIEF_v9.md` §6); keep the cluster bootstrap |
| §7.4 randomised arm | State it as out of reach at n ≈ 15 (F3) |
| §11 related work | Add Eneano, ARRS, Kinesthetic-CPR, Nickl, Biau, Ye, Linden, Käser & Alexandron, Zhang 2025. Fix Dyer 2017's venue (*Front. Neurosci.* 11:463). Mark Bugeja (F9) resolved. Mark Nickl (F10) verified |
| Repo prose outside v9 | Revert the Bugeja `[CORRECTED 2026-10-14]` brackets in `evaluation_plan_v2.md` L68/L136. **Done 2026-10-30:** framing v6 deleted (its copy went with it); CLAUDE.md item 6 reversed; CLAUDE.md brought up to v9 |
