# TRACE v9 — concept brief for methodological review

**Date:** 2026-10-30. **What this is:** the current research design of a CS/HCI
thesis, assembled for a methodology review. It is not thesis prose. **Sources:**
`thesis_framing_v9.md` (where it is current), `novelty_audit/CLAIMS_SHEET_v9.md`,
and CLAUDE.md "Thesis framing v9 — what binds". Where v9's text is stale (3-of-4
window, two tracks, per-corner controller), this brief uses the repository's
settled values.

## 1. The problem

Adaptive guidance systems (VR training, motor-skill coaches, tutoring systems)
decide when to remove a cue from performance measured **while the cue is still
on**. Performance with guidance is not performance without it (the guidance
hypothesis; Salmoni et al. 1984). So these systems can remove a cue prematurely.
Designers guard against that with heuristics (opacity floors, lower-bound
curves). When a learner does worse after a cue is removed, two explanations
compete:

- **Guidance dependency:** the learner was relying on the guidance.
- **Regression to the mean under selection:** the rule removes a cue right after a
  run of good passes, so the following passes are worse on average even if the
  guidance did nothing.

A rule that reads only cue-on performance cannot separate the two.

## 2. The system (built and working)

- **TRACE** runs in a racing simulator (Assetto Corsa). Novices see three
  world-anchored cues per corner: a brake-point marker, a corner-speed readout and
  an apex marker. They also get **bandwidth knowledge of results (KR)**: a short
  error message shown only when a pass falls outside the tolerance band.
- **Each cue element fades independently:** full → reduced salience → **probe**
  → removed.
  - During a probe, the cue **and its KR** are hidden for **2 laps**.
  - Measurement continues throughout.
  - If the evidence collapses, the element reverts one stage. At most 2
    reversions per element per block.
- **Per-pass criteria:** each corner pass yields a boolean per element (brake
  point within a band of an AI expert reference; minimum corner speed not more
  than a band below it; apex RMS deviation within a band).
- **Per-corner qualification:** 2 of the last 3 passes meet the criterion.
- **Stage transitions per element on a quorum** across the 4 corners: advance at
  ≥ 75% qualified, revert below 50%. Evidence is reset on every advance.
- A synthetic-learner simulator gated the configuration:
  - false fade for a non-improving learner: 8.5% (bound ≤ 10%);
  - removal despite regression: 0% (bound ≤ 2%).
- **Controller decisions are per element.** A per-corner controller was simulated
  and rejected: it faded cues for 79% of non-improvers.

## 3. Study design

- **n ≈ 15 novices**, one ~33-minute sitting each, **one condition** (TRACE
  adaptive; no static arm).
- **One car, one track** (Silverstone National, 4 corners).
- **A 15-lap training block** (ended on lap count), then a **4-lap unassisted
  block** (all cues and KR off).
- Everything is logged per pass and per element: metric values, cue and KR state,
  qualification events, probe start / end and outcome, reversions, censoring.

## 4. Research questions

- **RQ1, within-session reliability.** For each element and corner: lap-to-lap SD,
  SEM, ICC and MDC of the metrics, for novices, **after removing each driver's
  practice trend**. A recent sim-racing paper (TRACK 2026) names within-day
  repeatability as an unmeasured "first rung". RQ1 is also the calibration input
  for RQ2.
- **RQ2, decision accuracy (core).** Per element:
  - P_obs: the probe-failure rate over all guided-qualification events.
  - P_null: the same rate from **simulated learners with learning (practice
    trend) and lap-to-lap noise but no guidance dependency**, run through the
    same controller, lap budget and corners.
  - The **probe-failure excess** is Δ = P_obs − P_null. It is *interpreted* as
    **guidance dependency** (cue plus KR, withdrawn together); it is not measured
    as such.
- **RQ3, the system:** Lua/Python parity, real-time cost, live behaviour.
  Supporting evidence, not a research contribution.

## 5. The null (the load-bearing part)

- **Noise model** per element (form still open: F5/F6):
  - a driver random intercept;
  - a practice trend (per-driver slope or saturating curve);
  - residual lap-to-lap variability, pooled or per driver.
- **Fitted on cue-off laps** (probe laps plus the unassisted block). The reason:
  concurrent feedback reduces movement variability while it is on, so a cue-on σ
  is plausibly biased low, which would deflate P_null and inflate Δ.
- **Model check:** the null must reproduce observed cue-on statistics (lap-to-lap
  SD, qualification rate, timing of first qualification). Otherwise Δ is not
  reported as a dependency estimate.
- **Uncertainty:** a participant cluster bootstrap for P_obs; simulation plus
  parameter uncertainty for P_null.

## 6. Feasibility, from simulation (committed novice model)

- About **2.8 probes per typical participant**, so ~42 at n = 15, clustered.
  Per element ~16 / 15 / 11 (braking / corner speed / apex).
- **Noise-only probe-failure rates** under the committed model:

  | Element | P_null | Reading |
  |---|---|---|
  | corner speed | **0.00** | rests on an *assumed* speed sigma |
  | braking | **0.16** | the element where Δ is identifiable |
  | apex | **0.53** | the null swamps any plausible Δ |

- Only the apex noise parameters are measured from real data (n = 1, the
  researcher); the brake and speed sigmas are assumptions. A pilot will measure
  them.
- A randomised probe-timing arm (micro-randomised, probe now vs N laps later)
  would validate the null causally. It needs ~80 probes (~28 participants), so it
  is not run, and **Δ is model-based**.
- **Planned pre-registered predictions:** apex uninformative by design; braking
  the candidate for a detectable excess; corner speed no claim until the pilot.

## 7. Claimed novelty (after a four-step prior-art audit)

- **Claimed:** the first use, among works found, of a calibrated
  learning-plus-noise null to **attribute post-withdrawal (probe) failures** in an
  adaptive guidance system.
- **Explicitly not claimed as new:** simulated nulls, Type I error under a null,
  regression-to-the-mean corrections (LC-CUSUM / Biau 2008; Ye et al. 2016;
  Linden 2026), probe-gated withdrawal as an idea (Eneano et al. 2026 propose it;
  ARRS implements it for cognitive skills), and catch trials.
- **Never claimed:** statistical significance, a learning or retention benefit,
  optimal thresholds, a causal dependency estimate, dependency on the cue alone,
  or generalisation beyond one car, one track and this population. Nor that a
  probe failure harms learning (desirable difficulty).

## 8. Known open questions (for the reviewers to press on)

1. **Probe as intervention (v9 threat 6).** Removing a cue may itself change
   behaviour (surprise, attention shift), apart from dependency.
2. **Calibration circularity.** The null is fitted on cue-off laps from the same
   participants whose probe failures it judges.
3. **What "premature" means (F2).** v9 defines it relative to the system's own
   probe criterion: decision accuracy, not harm.
4. **Separating learning from noise in 15 laps** (F5/F6; v9 threat 2).
5. **Whether a group-level excess from ~40 clustered probes can support the
   interpretation**, and how censored blocks (ending mid-probe) enter P_obs.
6. **KR is withdrawn with the cue during a probe**, so the construct is
   "guidance", not "cue".
