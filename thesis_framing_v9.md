# TRACE — Thesis Framing v9

**Date:** 2026-10-23
**Status:** Draft. Supersedes v8.
**Basis:** reframe brief v3, plus two edits proposed on 2026-10-23 and applied here pending confirmation (F1, F2).

> **Interpretive edits applied — please confirm:**
> - **F1** `[CONFIRM]` "Measurement noise" is renamed to **lap-to-lap variability** (driver inconsistency + instrument error) throughout.
> - **F2** `[CONFIRM]` "Premature fade" is defined as **failing TRACE's own probe criterion**. It does *not* mean harm to learning (§4.3).

---

## 0. Open flags

| ID | Flag | Why it matters |
|---|---|---|
| F1 | `[CONFIRM]` Terminology: "lap-to-lap variability" | Avoids implying the variation is only instrument error |
| F2 | `[CONFIRM]` Definition of "premature" (§4.3) | Pre-empts the desirable-difficulty objection |
| F3 | `[CONFIRM]` Power-simulation threshold for running the randomised arm (proposal: ≥ 40 qualification events per arm) | Decides whether RQ2 has a causal component |
| F4 | `[CONFIRM]` Target participant count N | Set from the power simulation |
| F5 | `[CONFIRM]` Noise-model form: driver random effect + practice trend + residual (§7.2) | The null is only as good as this model |
| F6 | `[CONFIRM]` Residual variability pooled across drivers vs. per driver | Few laps per driver limits per-driver estimates |
| F7 | `[OPEN]` Were existing MDC analyses computed on cue-on laps? | If yes, they partly cover RQ1 already |
| F8 | `[VERIFY]` Controller parameters in §5.2 against `controller-rules.md` / `controller_config.json` | Values below are from earlier framing versions |
| F9 | `[VERIFY]` Bugeja et al. 2017: does TeAR fade or revert? | v7 used it as the probe-and-revert precedent |
| F10 | `[VERIFY]` Nickl et al. 2024: findings, and whether it is still needed | Earlier framing relied on a Hsieh–Nickl tension |
| F11 | `[VERIFY]` No prior system uses cue-off probe performance as the fading *decision* | Core of the gap statement (§3) |
| F12 | `[VERIFY]` Full bibliographic details for Salmoni et al. 1984 and Klasnja et al. 2015 | Currently written from memory |

---

## 1. One-line framing

Adaptive guidance systems decide when to remove a cue from performance measured while the cue is still on. TRACE is a real-time sim racing system that fades each on-track cue independently per corner, and commits a fade only after a short cue-off probe. Using its probes and a calibrated noise-only simulation, the thesis measures how often a guided-performance rule would remove a cue prematurely, and how much of that is real cue dependency rather than lap-to-lap variability.

---

## 2. Problem and motivation

### 2.1 Background (established; cited, not claimed)

- Performance during training is an unreliable index of learning. In particular, performance *with* guidance overstates performance *without* it (Salmoni, Schmidt & Walter 1984; Soderstrom & Bjork 2015).
- Concurrent visual feedback is especially prone to dependency, with performance dropping when it is removed (specificity-of-practice literature; Dyer et al. 2017; Bernardo et al. 2023).
- Fading guidance as skill develops is the standard response (faded / bandwidth KR; assist-as-needed).

### 2.2 How current systems decide to fade

Current adaptive guidance systems decide fading from **guided performance**. Where they collect unguided trials at all, they use them only for assessment:

| System | Fading decision based on | Unguided trials used for |
|---|---|---|
| Hsieh et al., CHI 2026 (VR piano ghost instructor) | Real-time performance with ghost visible | Retention assessment after practice |
| Shen et al., Cyber Racing Coach (haptic racing) | Racing score earned with assistance active | Pre/post tests |
| RL-based assist-as-needed (IEEE TNSRE 2025) | Recent performance under assistance | Catch trials for analysis |
| Kinesthetic-CPR (2026) | Performance stabilising under guidance | — |

### 2.3 Premature fading is a known risk, handled heuristically and never measured

Designers already guard against fading too early:
- Cyber Racing Coach uses a lower-bound curve to prevent sudden drops in assistance after high guided scores. Its own data shows performance at high assistance did not hold at lower assistance.
- Hsieh et al. recommend "recover after slips".
- In Forza Motorsport 4 telemetry, players repeatedly re-enable assists they had turned off (Debeauvais et al. 2014).

None of these report **how often** premature fades happen, or **why**.

### 2.4 Two explanations a guided rule cannot separate

1. **Cue dependency.** The driver performs well only because the cue is present.
2. **Regression to the mean.** Qualification selects the driver's good laps on a variable metric, so some later decline is expected by chance alone. This is a known property of cutoff-selected single-arm designs (Barnett et al. 2005; arXiv 2609.27919, 2026). Per-lap racing metrics vary substantially within a session (TRACK, 2026).

Within-session repeatability of per-corner racing metrics has not been measured. TRACK identifies it as the missing first step of its own analysis.

---

## 3. Gap statement

Adaptive guidance systems fade cues based on performance measured while the cue is on. Their designers guard against premature removal with hand-tuned heuristics, but the frequency of premature fades, and the share caused by real cue dependency rather than lap-to-lap variability, has not been measured. No system we found uses cue-off probe performance as the fading decision itself `[VERIFY: F11]`. In sim racing specifically, the within-session reliability of the per-corner metrics such decisions depend on is also unmeasured.

TRACE addresses this with:
- a real-time, per-element, per-corner, probe-gated fading controller for world-anchored cues;
- a verified simulator that generates a noise-only null calibrated from live data.

Together these measure how often, and why, a guided-performance rule would fade prematurely.

---

## 4. Research questions and definitions

### 4.1 Research questions

- **RQ1 — Within-session reliability (engineering).** How reliable are per-element, per-corner sub-skill metrics lap to lap within a single novice session? *(Calibrates the noise model.)*
- **RQ2 — Decision accuracy (core).** At each guided-qualification event, how often does the cue-off probe fail, and how much of that failure rate exceeds a simulated null with no cue dependency? Does the excess differ by cue element and corner type?
- **RQ3 — System correctness and behaviour.** Is the controller logically identical across implementations and real-time capable? How does it behave in live sessions?
- **RQ4 — Granularity (secondary).** Do sub-skills reach qualification at different times within and across corners?

### 4.2 Terms

| Term | Meaning |
|---|---|
| **Element** | One cue and its metric: braking marker ↔ braking-point error; apex marker ↔ apex error (windowed RMS); corner-speed indicator ↔ corner-speed error |
| **Guided qualification** | An element at a corner meets the fade criterion while its cue is on. This is the moment a guided-performance rule would fade the cue. |
| **Probe** | The cue is removed for the probe window, with bandwidth KR also off |
| **Probe failure** | The element does not meet the criterion during the probe |
| **Lap-to-lap variability** | Variation in a metric between laps not explained by the driver's skill trend: driver inconsistency + instrument error |
| **Noise-only null** | Expected probe-failure rate if removing the cue had no effect on performance |
| **Excess failure** | Observed probe-failure rate − noise-only null. This is the dependency estimate. |

### 4.3 What "premature" means

A fade is **premature** when the driver fails TRACE's probe criterion after guided qualification. This is a statement about **decision accuracy relative to the system's own criterion**. It does **not** claim that the drop in performance harms learning. Some struggle without guidance may be beneficial (desirable difficulty), and without a retention test we cannot tell.

---

## 5. System

### 5.1 Architecture

- **trace-rt** (CSP Lua, in Assetto Corsa):
  - real-time metric extraction per corner;
  - controller;
  - world-anchored rendering of three cue types via the CSP render API;
  - bandwidth KR.
- **trace-kit** (Python, offline):
  - identical controller logic;
  - golden-trace parity suite;
  - noise-model fitting;
  - null simulation;
  - power simulation;
  - analysis.
- **Interface:** no IPC; versioned, hashed files.
- **Corners:** manually annotated on normalised track-spline positions; two short tracks.
- **Tolerances:** derived from AI reference laps, inflated by the Expertise Variance Multiplier (EVM).

### 5.2 Controller (per element × per corner)

Parameters below are from earlier framing versions; `[VERIFY: F8]` against `controller-rules.md`.

- **Fade criterion:** 3-of-4 recent laps within tolerance (2-of-3 under consideration, pending MDC analysis).
- **Qualification quorum:** element-level thresholds of 75% / 50%.
- **Asymmetric hysteresis** between fade and re-show.
- **Probe-and-revert:** on qualification, a probe of 3 laps with the cue off and KR off. The fade commits if the probe holds, otherwise the cue reverts.
- **Reversion cap:** 2 per element × corner.
- **Censoring semantics** for elements that never qualify within the session.
- *(Conditional)* **Randomised probe timing** (§7.4).

### 5.3 Engineering contributions

1. Online sub-skill state estimation from noisy telemetry.
2. A decision controller robust to noisy input (hysteresis, probe-and-revert, caps, censoring).
3. Real-time world-anchored rendering within the frame budget.
4. A verified dual implementation (Lua/Python) with golden-trace parity.
5. A **null-simulation engine**: synthetic drivers with measured variability and no cue dependency, run through the parity-verified controller logic.
6. *(Conditional)* Constrained randomised probe scheduling.

---

## 6. Study design

- **Participants:** novice drivers, N = `[CONFIRM: F4]`.
- **Session:** one 30-minute session, 12–15 laps, TRACE only (no static condition).
- **Tracks and car:** two short tracks; one car (fixed).
- **Guidance:** all cues on at start; faded per element × corner by TRACE.
- **KR:** bandwidth KR active during cued laps, **off during probes**.
- **Probe window = follow-up window** for all failure-rate comparisons.
- **Logging (first-class output):** per lap and per element × corner:
  - metric values;
  - cue state;
  - KR state;
  - qualification events;
  - probe start / end and outcome;
  - reversions;
  - censoring flags;
  - controller config hash.

---

## 7. Analysis

### 7.1 RQ1 — Within-session reliability

- **Data:** cue-on laps before an element's first qualification.
- **Detrending:** remove each driver's practice trend before estimating variability.
- **Outputs per element × corner type:**
  - lap-to-lap SD;
  - standard error of measurement;
  - test–retest reliability (e.g., ICC on consecutive-lap or odd/even splits);
  - MDC.
- **Sensitivity:** with and without detrending.

### 7.2 Noise-model calibration

- **Candidate model per element × corner type** `[CONFIRM: F5]`:
  - driver random intercept (baseline skill);
  - practice trend (e.g., per-driver slope or a saturating curve over laps);
  - residual lap-to-lap variability, pooled or per driver `[CONFIRM: F6]`.
- **Why the trend matters.** Novices improve within the session. A trend-free model treats improvement as variability. That inflates the noise-only null, which then understates dependency.

### 7.3 RQ2 — Decision accuracy

1. **Observed:** probe-failure rate P_obs(e), per element e (and corner type), over all guided-qualification events.
2. **Null:** generate synthetic sessions from the fitted model with the same lap budget, corners, criterion, probe length and controller logic, and **no change in performance when the cue is removed**. Run them through trace-kit and compute P_null(e).
3. **Estimate:** excess Δ(e) = P_obs(e) − P_null(e).
4. **Uncertainty:** cluster bootstrap by participant for P_obs; simulation and parameter uncertainty for P_null.
5. **Model check:** the simulation must reproduce observed cue-on statistics (lap-to-lap SD, qualification rate, timing of first qualification). If it fails, Δ is not reported as a dependency estimate.
6. **Sensitivity analyses:**
   - noise-model variants (trend / no trend; pooled / per-driver);
   - fade criterion 3-of-4 vs. 2-of-3;
   - EVM range.

### 7.4 Randomised probe timing (conditional)

- **Gate:** before data collection, a trace-kit power simulation under plausible variability and dependency values estimates qualification events per participant and the width of the Δ(e) interval.
- **Design if the gate passes** `[CONFIRM: F3]`: at each guided-qualification event, randomise
  - **A:** probe now;
  - **B:** keep the cue on for N more laps, then probe.

  Design adapted from micro-randomised trials (Klasnja et al. 2015).
- **Use:**
  - a causal estimate of dependency;
  - **validation of the noise-only null:** arm B's failure rate should match P_null if the model is right.

### 7.5 RQ3 — System

- **Parity:** decision-level agreement Lua vs. Python on golden traces (target 100%); divergence analysis.
- **Runtime:** per-frame cost and decision latency in live sessions.
- **Live behaviour:** fade timelines per element × corner, probe outcomes, reversions, cap hits, censoring rates.

### 7.6 RQ4 — Granularity

- **First-qualification lap** per element × corner (censoring-aware).
- **Within-corner spread** across elements, and **across-corner spread** per element.
- Qualification order.
- Run under both fade criteria.

---

## 8. Contributions

1. **System (engineering):** TRACE, a verified real-time controller that estimates per-element, per-corner sub-skill state from simulator telemetry and gates each cue fade on cue-off performance, with world-anchored rendering and Lua/Python parity.
2. **Method:** a calibrated null-simulation approach that separates cue dependency from lap-to-lap variability when evaluating threshold-based fading decisions, built on the parity-verified simulator. It is reusable for other adaptive guidance systems.
3. **Findings:**
   - within-session reliability of per-corner sim racing metrics (unmeasured in prior work);
   - how often a guided-performance rule would fade prematurely, beyond what variability predicts, per cue element;
   - whether sub-skills desynchronise.

---

## 9. Claims

**We claim:**
- TRACE works in real time and is logically identical across implementations;
- per-element, per-corner metric reliability within a session;
- the rate of guided-rule premature fades, and the excess over a noise-only null, per element;
- desynchrony (or its absence) in this setting.

**We do not claim:**
- novelty of the learning–performance distinction, catch trials, reversible fading, or fading in racing;
- that TRACE or probe-gating improves learning or retention;
- that premature fades harm learning (§4.3);
- a causal dependency effect, unless the randomised arm runs. Without it, Δ is a model-based estimate.

**Wording discipline:**
- Use: "measure", "estimate", "decision accuracy", "excess over a noise-only null".
- Avoid: "improves learning", "first", "novel fading approach".

---

## 10. Threats to validity

1. **Noise-model misspecification.** Δ depends on the null. Mitigations: model checking (§7.3 step 5), sensitivity to model form, and arm-B validation if run.
2. **Practice trend vs. variability.** Separating them with 12–15 laps is hard. Mitigations: sensitivity analyses; report both.
3. **Few qualification events.** This limits precision per element × corner type. Mitigations: power simulation; pooling across corners within type.
4. **Within-session scope.** Dependency here is short-term. Long-term dependency is out of scope.
5. **Desirable difficulty.** A probe failure is not necessarily harmful (§4.3).
6. **Probe as intervention.** Removing a cue may itself change behaviour (surprise, attention shift). This is stated as part of what "cue-off performance" means.
7. **Small N, two tracks, one car.** Generalisation is limited.
8. **Related-work naming.** TRACK (2026) is similar in name. Cite and position against it explicitly.

---

## 11. Related work positioning

| Area | Works | Role in this thesis |
|---|---|---|
| Learning vs. performance; guidance hypothesis | Salmoni et al. 1984; Soderstrom & Bjork 2015; Dyer et al. 2017; Bernardo et al. 2023 | Theoretical motivation (§2.1) |
| Adaptive guidance (fading on guided performance) | Hsieh et al. 2026; Shen et al. (Cyber Racing Coach); Marchal-Crespo & Reinkensmeyer 2008; RL-AAN (TNSRE 2025); Kinesthetic-CPR 2026 | Systems whose decision rule is analysed (§2.2) |
| Premature-removal evidence | Cyber Racing Coach lower bound; Hsieh "recover after slips"; Debeauvais et al. 2014 | Shows the risk is known but unmeasured (§2.3) |
| Unassisted probes / slacking | Rehab catch trials; slacking literature | Credit for probe-as-measurement; our step is probe-as-decision |
| Assistance dilemma | Koedinger & Aleven 2007 | Positions the question within ITS |
| Regression to the mean | Barnett et al. 2005; arXiv 2609.27919 (2026); Tversky & Kahneman 1974 | Justifies the noise-only null |
| Sim racing telemetry analysis | TRACK 2026; Hojaji et al. 2023/2024; Bugeja et al. 2017 `[VERIFY: F9]` | Domain context; reliability gap; corner segmentation |
| Micro-randomised trials | Klasnja et al. 2015; Liao et al. | Conditional randomised arm |
| `[VERIFY: F10]` | Nickl et al. 2024 | Keep only if still relevant after checking |

---

## 12. Planned figures

Each as a separate, clean paper-style diagram:

1. TRACE architecture (trace-rt / trace-kit / files / parity suite).
2. Per-element × corner state machine (qualify → probe → commit / revert; caps; censoring).
3. Decision timeline for one corner: cue state, metric, qualification, probe outcome.
4. Analysis pipeline: live data → reliability → noise model → null simulation → Δ(e).
5. Results: observed vs. null probe-failure rate per element, with intervals.

---

## 13. Changes from v8

| Area | v8 | v9 |
|---|---|---|
| Core question | Sub-skill desynchrony + offline policy replay | Decision accuracy of guided-performance fading, separated from lap-to-lap variability |
| TRACE's role | Data source + replay engine | Engineered system + measuring instrument (probes) |
| Noise handling | Not addressed | Simulated noise-only null calibrated on within-session data |
| Primary RQ | Desynchrony | Decision accuracy (RQ2); desynchrony becomes secondary (RQ4) |
| RQ1 | Desynchrony | Within-session metric reliability |
| Policy replay | Core (RQ2) | Dropped |
| KR | Kept; confound to report | Kept; off during probes |
| Randomisation | Not present | Conditional arm, gated by power simulation |
| External data | None | ACGym evaluated and rejected (track/car mismatch) |
| CS framing | Implicit | Explicit engineering contributions (§5.3) |

---

## References

- Barnett, A. G., van der Pols, J. C., & Dobson, A. J. (2005). Regression to the mean: what it is and how to deal with it. *Int. J. Epidemiology*, 34(1), 215–220.
- Bernardo, M., Blandin, Y., Casiez, G., & Scotto, C. R. (2023). Reliability of on-line visual feedback influences learning of continuous motor task of healthy young adults. *Frontiers in Psychology*.
- Bugeja, K., Spina, S., & Buhagiar, F. (2017). Telemetry-based optimisation for user training in racing simulators. *VS-Games 2017*, 31–38. `[VERIFY: F9]`
- Çangırılı, E., & Kurt, M. (2026). TRACK: Telemetry-Based Racing Analysis and Coaching Kit in Sim Racing Games. arXiv:2610.10061.
- Debeauvais, T., et al. (2014). Off With Their Assists: An Empirical Study of Driving Skill in Forza Motorsport 4. *FDG 2014*. `[VERIFY]` author list.
- Dyer, J. F., Stapleton, P., & Rodger, M. (2017). Mapping sonification for perception and action in motor skill learning. *Psychological Research*. `[VERIFY]` title.
- From Scaffolding to Internalization: Enhancing CPR Training with In-Situ Visualization and Kinesthetic Feedback. arXiv:2608.08729.
- Hojaji, F., Toth, A. J., Joyce, J. M., & Campbell, M. J. (2024). AI-enabled prediction of sim racing performance using telemetry data. *Computers in Human Behavior Reports*, 14, 100414.
- Hsieh, T.-H., Visser, C., Eisemann, E., & Marroquim, R. (2026). Skill-Adaptive Ghost Instructors. *CHI '26*. doi:10.1145/3772318.3791437
- Klasnja, P., et al. (2015). Microrandomized trials: An experimental design for developing just-in-time adaptive interventions. *Health Psychology*, 34(S). `[VERIFY: F12]`
- Koedinger, K. R., & Aleven, V. (2007). Exploring the assistance dilemma in experiments with cognitive tutors. *Educational Psychology Review*, 19(3), 239–264.
- Marchal-Crespo, L., & Reinkensmeyer, D. J. (2008). Haptic guidance can enhance motor learning of a steering task. *J. Motor Behavior*, 40(6), 545–557.
- Personalized Adaptive Assistance With Reinforcement Learning Control… *IEEE TNSRE* (2025). doi:10.1109/tnsre.2025.3650096
- Regression to the Mean-Adjusted Sample-Size Determination for Cutoff-Selected Single-Arm Pre-Post Studies. arXiv:2609.27919 (2026).
- Salmoni, A. W., Schmidt, R. A., & Walter, C. B. (1984). Knowledge of results and motor learning: A review and critical reappraisal. *Psychological Bulletin*. `[VERIFY: F12]`
- Shen, C., Yu, S., Weng, Y., Ma, H., Li, C., Yasuda, H., Dallas, J., Thompson, M., Subosits, J., & Ersal, T. Cyber Racing Coach: A Haptic Shared Control Framework for Teaching Advanced Driving Skills. arXiv:2509.20653.
- Soderstrom, N. C., & Bjork, R. A. (2015). Learning versus performance: An integrative review. *Perspectives on Psychological Science*, 10(2), 176–199.
- Tversky, A., & Kahneman, D. (1974). Judgment under uncertainty: Heuristics and biases. *Science*, 185, 1124–1131.
