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
curves). When a learner does worse after a cue is removed, three explanations
compete:

- **Guidance-contingent performance:** performance holds with the guidance
  and not without it, so the deficit lasts while the guidance stays off. This
  covers two mechanisms that an immediate test cannot separate:
  - **dependency:** the learner relied on the guidance instead of
    internalising the skill;
  - **ongoing benefit:** the cue's information still helps.

  For a fading rule both mean the same thing: the cue was withdrawn before
  unguided performance met the criterion, i.e. **prematurely**.
- **Withdrawal as an intervention:** removing the cue is itself an event
  (surprise, a shift of attention), so performance dips briefly and recovers.
- **Regression to the mean under selection:** the rule removes a cue right after a
  run of good passes, so the following passes are worse on average even if the
  guidance did nothing.

A rule that reads only cue-on performance cannot separate them. TRACE separates
the third from the first two with a learning-plus-noise null; that separation
is conditional on the null's noise model (§5). It separates the first from the
second, partly, by the deficit's time course (§4).


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
- **A 15-lap training block** (ended on lap count), then, with no delay, a
  **4-lap unassisted block** (all cues and KR off). Both it and the 2-lap probe
  are **immediate, within-session no-feedback tests**, not delayed retention
  tests (§4).
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
  - **Censoring (decided).** A probe still running when the 15-lap block ends
    is **excluded** from both P_obs and the simulated P_null (same rule, same
    lap budget). The censored count is reported per element. Counting censored
    probes as passes, or as failures, is reported as a sensitivity analysis.
    - In simulation, 12–20% of braking probes are censored; corner speed has
      none.
    - Every rule was unbiased against its own true Δ (|bias| ≤ 0.02) when
      applied identically to both sides. The rules change Δ's scale, not its
      validity: at the same dependency, the true Δ is 0.37 when censored
      probes are excluded, 0.27 when they count as passes and 0.34 when they
      count as failures (`kit/tools/nulldecision.py`).
  - P_null: the same rate from **simulated learners with learning (practice
    trend) and lap-to-lap noise, whose performance does not change when the
    guidance is withdrawn**, run through the
    same controller, lap budget and corners.
  - The **probe-failure excess** is Δ = P_obs − P_null. That is the measured
    quantity. The null excludes regression to the mean and practice. It does
    **not** exclude a withdrawal transient, so Δ has two readings. A
    pre-specified time profile decides which one the data support:
    - **Guidance-contingent performance** (cue plus KR, withdrawn together)
      is a **sustained** deficit. By construction it includes the loss of any
      benefit the guidance gave while it was on, so it covers dependency and
      ongoing benefit alike (§1). An immediate test cannot separate the two.
      - That is the construct the research question needs: either way, a
        guided-performance rule faded the element before unguided performance
        met the criterion. So a sustained excess reads as a **premature
        fade**.
      - **Guidance dependency** proper is discussed only as one candidate
        mechanism, never as a reading of Δ (renamed 2026-11-01, review round
        2, NEW-1).
      - It shows as a positive **late level** L.
    - **Withdrawal as an intervention** is a **transient** deficit that fades
      within the first laps of a withdrawal. It shows as probe decay T_p: the
      first probe lap worse than the second, with L at zero.
    - **The statistics and the test (decided 2026-11-01, review round 2, R8;
      `kit/tools/nullprofile.py`).** All are standardised residuals against
      the primary null, each with a one-sided t-test over participants at
      α = 0.05.
      - **T_p** is the first probe lap minus the second.
      - **For braking, L is the mean of unassisted laps 3–4** (L_u34). It was
        laps 2–4 until round 2.
      - **For corner speed, L is the second probe lap** (L_p). Too few
        participants still have the element visible when training ends for
        an unassisted statistic.
    - **The reading rule, with both cases covered:**
      - **sustained** if L is significant, whatever T_p shows (a decay on top
        of a persisting deficit is still a persisting deficit);
      - **decaying** if T_p is significant and L is not;
      - **neither** otherwise.
    - **The horizon. This is a stated limit, not a parameter.** The profile
      separates a transient from a sustained deficit only if the transient is
      short enough:
      - **Braking: up to 2 laps.** Under the old laps 2–4 statistic, a 2-lap
        transient was read as sustained in 76% of studies. Under laps 3–4 the
        figure is 5%, and detection of a sustained 0.25-band deficit drops
        only from 0.93 to 0.90. A transient of 3 laps or more is read as
        sustained (86%): inside a 4-lap block nothing can tell the two apart.
      - **Corner speed: 1 lap.** A 2-lap probe sees all of a 2-lap transient,
        so L_p reads it as sustained (100%).
    - **Block to probe, an assumption made explicit.** The braking reading
      comes from the unassisted block, while Δ is made of probes. The reading
      transfers to Δ on one assumption: a withdrawal of the same element in
      the same session, scored against the same null, reflects the same
      mechanism. L_p is reported beside it as probe-level corroboration. It
      detects a sustained braking deficit as often (0.93), but its horizon is
      1 lap.
    - **The reading is asymmetric.** A sustained profile argues against a pure
      transient. A decaying profile fits a transient, but it also fits a
      dependency the learner quickly re-acquires without guidance. So it is
      reported as "transient or fast re-acquisition", never as "no dependency".
    - **Simulated readings under the adopted rule** (`kit/tools/nullprofile.py`,
      1000 studies per scenario, n = 15, effects varying between drivers).
      Each cell gives the share of studies read as sustained / decaying /
      neither:

      | scenario | braking (L_u34) | corner speed (L_p) |
      |---|---|---|
      | no deficit | 0.08 / 0.06 / 0.86 | 0.06 / 0.05 / 0.89 |
      | sustained, 0.25 band | 0.90 / 0.01 / 0.09 | 0.99 / 0.00 / 0.01 |
      | sustained, 0.5 band | 1.00 / 0.00 / 0.00 | 1.00 / 0.00 / 0.00 |
      | 1-lap transient, 0.25 band | 0.06 / 0.73 / 0.21 | 0.04 / 0.93 / 0.02 |
      | 1-lap transient, 0.5 band | 0.06 / 0.91 / 0.04 | 0.06 / 0.94 / 0.00 |
      | 2-lap transient, 0.5 band | 0.05 / 0.06 / 0.90 | 1.00 / 0.00 / 0.00 |
      | 3-lap transient, 0.5 band | 0.86 / 0.01 / 0.14 | 1.00 / 0.00 / 0.00 |

      A 2-lap braking transient reads as "neither", not "decaying". The probe
      is 2 laps long, so both of its laps are affected and T_p is zero. That
      errs toward no construct reading, which is the safe direction.
    - **Apex:** no reading, because the apex null is biased (§5).
    - Neither reading is causal. Without a randomised arm, the profile
      discriminates; it does not identify.
  - **Both readings are performance-level, not learning-level.** In the
    motor-learning literature, dependency is judged on a **delayed**
    no-feedback retention or transfer test, once the transient effects of the
    feedback schedule have worn off, and against a group trained with less
    feedback (Salmoni et al. 1984; Winstein & Schmidt 1990). That is the
    learning–performance distinction (Kantak & Winstein 2012).
    - TRACE's probe and unassisted block are **immediate** tests inside the
      session, and the comparison is a simulated learner, not a group.
    - So the sustained reading is **immediate guidance-contingent
      performance**: a deficit that persists across the immediate no-feedback window
      (4 laps, about 5 minutes). It says nothing about what the learner would
      retain after a delay.
    - "Sustained" in this brief always means sustained within that window.
    - A delayed retention test was considered and not adopted (author decision,
      2026-10-30). It would add rig time to the single sitting, and it would
      still compare with the null rather than with a lower-feedback group.
- **RQ3, the system:** Lua/Python parity, real-time cost, live behaviour.
  Supporting evidence, not a research contribution.

## 5. The null (the load-bearing part)

- **What counts as guidance-contingent performance (decided).** Two
  withdrawal effects both count,
  if they are **sustained across the immediate no-feedback window** (§4). A deficit confined to the first withdrawn lap is the
  withdrawal-transient rival instead (§4):
  - the mean error shifting back toward the novice direction when the guidance
    is withdrawn;
  - lap-to-lap variability increasing when it is withdrawn.

  So the null that excludes them by definition is calibrated on **guided**
  performance. Δ therefore includes the loss of any benefit the guidance gave
  while it was on. That is why the construct is guidance-contingent
  performance and not dependency (§1, §4).
- **Terminology in the simulation descriptions.** The simulations below
  "inject a dependency": a sustained mean or variance shift on every
  withdrawn pass. That is the simulated instance of guidance-contingent
  performance. Read "dependency" in a simulation description as that, and
  "no-dependency" as the null's own learner.
- **Noise model, per element and per driver (F5/F6 decided):**
  - an exponential practice trend with a per-corner amplitude and a per-driver
    rate;
  - residual lap-to-lap variability, per driver (Gaussian, independent).
- **Primary null: fitted on full-salience laps only.** Reduced, probe,
  removed and unassisted laps are excluded. Reduced salience is a partial
  withdrawal, so it can carry part of the dependency.
  - In a parameter-recovery and absorption simulation (pair 1, real
    controller), a guided-lap fit returned 1.00–1.04 of an injected braking or
    corner-speed dependency.
  - When half the dependency also appeared at reduced salience, a fit that
    included reduced laps absorbed 11–26% of braking Δ. The full-only fit
    stayed at 1.01–1.11.
  - **Recovery depends on the trend form** (round 2, R2;
    `kit/tools/nullprimary.py`, 100 studies per cell, n = 15).
    - **Under an exponential truth:** braking RMSE(P̂_null − P_true) is 0.032
      at the committed σ, and R2's 0.045 criterion holds up to 5 m (1.25×).
    - **Under a power-law truth:** the RMSE is 0.051 at the committed σ, so
      the criterion **fails**. It holds only up to 3 m. Corner speed meets it
      at every σ tested, under both forms.
    - **σ is recovered** (σ̂/σ 0.99 under an exponential truth). Under a power
      law at low noise, the trend misfit is absorbed into σ (1.27 at 2 m).
    - **Extrapolation past the fit window (S6):** the fit window ends at the
      first advance, and the trend is then carried over the probe and
      unassisted laps (~5–11 laps for braking, ~13 for corner speed). The
      error there is 0.03–0.08 σ under an exponential truth and 0.24–1.35 σ
      under a power law.
    - **So the trend form is the null's main exposure, not the noise level.**
      The model check catches a wrong form only partly (below). The σ gate
      catches part of it too, because a power-law truth inflates σ̂.
  - Code and tables: `kit/tools/nullrecovery.py`, `kit/tools/nullabsorption.py`
    and `kit/tools/README.md`.
- **Lower bound: the cue-off null.** It uses the probe, removed and unassisted
  laps, with one practice rate pooled across drivers. Δ is also reported against
  it.
  - It is biased toward zero by construction. In simulation it returned only
    0.22–0.82 of an injected braking dependency (about 0.25 of a pure variance
    increase).
  - So "Δ_cue-off > 0" is the conservative statement, and a near-zero
    Δ_cue-off is read through that attenuation, not as absence.
- **Model check (pre-specified, held-out).** The null is fitted on per-pass
  metric values from full-salience laps, so reproducing their summary
  statistics would be in-sample. Cue-off statistics cannot be used either: a
  dependency makes them differ from the null by definition, so a cue-off check
  would reject the null exactly when the effect exists. The check therefore uses
  features of the full-salience laps that the fit does not target but that a
  correct noise model must get right:
  1. **Out-of-sample prediction.** Refit with the laps split into 5 folds, one
     held out at a time, and score how many held-out passes fall inside the 80%
     predictive interval. This tests the trend form and σ calibration.
  2. **Post-selection performance.** The criterion pass rate on the pass after
     a corner qualifies (2 of 3) while the cue is still on. That is the
     regression to the mean the null exists to model.
  3. **Lag-1 residual autocorrelation.** The null assumes independent residuals.
     Autocorrelated noise changes post-selection regression.

  **Tolerance:** each observed statistic must fall inside the central 98.3%
  of the same statistic computed on studies simulated from the fitted null
  (same participants, lap budget and controller). That is 95% Bonferroni-
  adjusted over the three checks, so a correct null fails about 5% of the time
  per element, not ~14%.

  **Rule:**
  - **One pre-specified escalation before abandoning.** If check 3 fails, refit
    the noise as AR(1). If check 1 fails, refit it as Student-t. If both fail,
    refit as AR(1) with t innovations. ρ and ν are pooled across participants
    and corrected for the bias that detrending introduces. Then re-run all
    three checks against the escalated null.
  - **No escalation for check 2.** A null that gets post-selection regression
    wrong is wrong about what it exists to model.
  - **Outcome:** an element that still fails has its Δ reported descriptively,
    not as a dependency estimate.

  **Simulated power** (`kit/tools/nullcheck.py`, 100 studies per truth, no
  dependency), for braking:
  - **False alarm:** ~5% on a correct null.
  - **After escalation, Δ is kept** for 95% of correct, 88% of autocorrelated
    and 61% of heavy-tailed truths. Those misspecifications leave P_null within
    the 0.045 criterion. Without escalation, autocorrelated nulls were rejected
    every time.
- **Trend form: sensitivity, not a gate.** P_null is also reported under a
  power-law trend, as a pre-registered sensitivity analysis.
  - A gate on the two forms agreeing within 0.045 was simulated and rejected.
    It discarded 69% of studies whose exponential null was correct, and it
    agreed more often under a power-law truth than under the correct one.
  - **Limitation, stated:** a wrong trend form is caught only by check 1, in
    about 40–50% of studies.
- **σ gate, re-specified (round 2, NEW-2; `kit/tools/nullprimary.py`).**
  - **What it reads:** the **main sample's** pooled full-salience residual
    SD, σ_study = √(mean over participants of σ̂²), from the primary null's
    own fits.
  - **When it is applied:** at analysis. It reads no probe outcome and no
    cue-off lap, so a withdrawal effect cannot trip it.
  - **The rule:** braking Δ is a dependency estimate only if σ_study ≤
    **4.5 m**. Corner speed's cut is **4.75 km/h**, the edge of the range
    tested; no bin failed there.
  - **How the cut was set:** by a criterion fixed before the run. Simulated
    studies, pooled over exponential and power-law truths and σ from 2 to
    8 m, were binned by their own σ_study. The cut is the upper edge of the
    last bin from below whose braking RMSE stays ≤ 0.045. So the study's
    sampling uncertainty in σ̂ is built into the cut. The 50/50 mix of trend
    forms is an assumption.
  - **The pilot (n = 2)** only forecasts eligibility for G2. It is not the
    gate. It replaces "pilot σ > 4 m", which had no estimator and would have
    tripped about half the time at a true 4 m.
- **Apex:** a Gaussian residual on an RMS metric recovers only ~0.6 of the true
  σ, and the cue-on apex null overstates Δ by 1.2–1.9×. Neither the model check
  nor escalation rescues it: P_null error stays at 0.10–0.25.
  - Simulation cannot settle the form, because the simulator's own apex noise
    (a folded Gaussian) is an artefact.
  - The form must be chosen from the pilot's apex distribution (G2), which is
    right-skewed in the recorded passes (mean 2.49 m, median 1.52 m).
  - Apex is uninformative by design anyway (§6).
- **Uncertainty: one procedure, a nested participant cluster bootstrap**
  (decided 2026-11-01, review round 2, R6; `kit/tools/nullinterval.py`).
  - The outer level resamples participants with their observed probes.
  - Inside it, each sampled participant contributes one of M = 20
    parametric-bootstrap refits of their own null, drawn at random. A refit
    simulates the participant's full-salience laps from their fitted trend
    and σ, refits, and drives the refit through the controller.
  - So P_null's fit uncertainty is in the interval. The point estimate uses
    the original fit.
  - **Not resampled:** the fit window ends at the element's first advance,
    which is itself selected.

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
- **Pre-registered decision rule (per element, decided).** The interval is
  the 90% nested participant cluster bootstrap of §5 on Δ̂ = P_obs − P̂_null,
  with censored probes excluded.
  - **Excess:** the lower bound is above 0.
  - **No excess:** the upper bound is below the **minimum Δ of interest, 0.10**.
    This is tied to Gate G1's false-pass bound (≤ 10%). An excess of 0.10 means
    premature fades at the rate the design already declares tolerable, so the
    threshold reuses a declared design parameter rather than introducing a new
    one.
  - **Indeterminate:** anything else.
- **Simulated design sensitivity of the adopted (nested) interval**
  (`kit/tools/nullinterval.py`: 200 studies per cell, n = 15, M = 20 refits
  × 10 blocks, B = 1000, and a sustained dependency varying between drivers).
  For braking:

  | true Δ | median 90% CI width | P(excess) | P(no excess) | P(indeterminate) |
  |---|---|---|---|---|
  | 0.00 | 0.37 | 0.015 | 0.24 | 0.745 |
  | 0.08 | 0.41 | 0.11 | 0.135 | 0.755 |
  | 0.24 | 0.50 | 0.465 | 0.02 | 0.515 |
  | 0.37 | 0.52 | 0.745 | 0.01 | 0.245 |

  - **Against the round 1 interval, on the same studies:** the round 1
    interval did not resample the null's fit. The nested one is only ~5%
    wider (0.353 → 0.372 at Δ = 0), and every verdict rate moves by ≤ 0.03.
    Fit uncertainty is small next to between-participant variation. So the
    round 1 figures (`nulldecision.py`) were not materially optimistic, and
    the conclusions below hold under either interval.

  - **Braking resolves only large excesses at n = 15.** 80% detection needs
    Δ ≳ 0.4. With no dependency the expected verdict is **indeterminate**, and
    an indeterminate result is not evidence of no dependency.
  - A rough √n extrapolation puts 80% detection at Δ ≈ 0.24 near n ≈ 36.
  - The braking probe yield in this simulated population is ~0.8 per
    participant (~12 at n = 15), not 16. The population includes slow and
    non-learners, and the yield is a model output (M6).
  - **Yield across σ (review item S20, `kit/tools/nullyield.py`).** What
    enters P_obs is the **uncensored** probe count. For braking it is 0.64 per
    participant at the committed σ (median 10 at n = 15). It falls fast as
    the noise rises: the median is 12 at 2–3 m, 7 at 5 m, 5 at 6 m and 2 at
    8 m. Corner speed (~14) and apex (~8) barely move with σ.
- **Planned pre-registered predictions** (under the rule above):
  - **Braking:** the candidate for an excess, but only an excess of about 0.4
    or more is likely to be resolved. The expected verdict under no dependency
    is indeterminate.
    - A cue that simply helps while it is on predicts Δ > 0 by itself, so the
      direction of an excess is expected. What is informative is its **size**:
      how far the guided-performance rule overstates unguided competence, in
      the controller's own decision unit.
  - **Corner speed:** its P_null is ≈ 0, so it resolves better than braking.
    The verdict is "no excess" in 94.5% of no-dependency studies, and an
    excess is detected in 88% at Δ ≈ 0.36 (nested interval). That rests on the **assumed** speed σ, so
    it carries no claim until the pilot measures that σ.
  - **Apex:** no verdict. It is uninformative by design, and its null is
    biased by +0.11 to +0.17.
- **What is reported under each outcome (pre-specified, decided).** These are
  evaluated per element, in this order. The first gate that applies decides.

  | # | outcome | what the thesis reports |
  |---|---|---|
  | 0 | **Element ineligible**: apex always; braking if the main sample's full-salience σ_study exceeds 4.5 m, and corner speed if it exceeds 4.75 km/h (§5) | P_obs and P_null **descriptively**, with the reason. No verdict |
  | 1 | **Too few probes**: fewer than **7** uncensored probes pooled for the element (S20, below) | No Δ. The pre-stated fallback is RQ1 reliability plus the guided-vs-unassisted contrast from the 4-lap block, which every participant drives |
  | 2 | **Model check fails** after its one escalation (§5) | Δ̂ and its interval **descriptively**, named as "not a dependency estimate", with the failed check |
  | 3 | **Excess**: the lower 90% bound is above 0 | Δ̂, its interval, and the cue-off lower bound beside it. The construct reading comes from the time profile (§4). A **sustained** profile gives *guidance-contingent performance*, i.e. a premature fade, with dependency and ongoing benefit not separated. A **decaying** one gives *withdrawal transient or fast re-acquisition*. With neither, it is an excess without a construct reading |
  | 4 | **No excess**: the upper bound is below 0.10 | That the system's probe failures are accounted for by practice and noise within the 0.10 margin, i.e. cue-on gating did not withdraw this element prematurely beyond the design's own false-pass tolerance. Not a claim that dependency is absent |
  | 5 | **Indeterminate**: anything else; the expected braking outcome at n = 15 | Δ̂ and its interval, stated as **not evidence of absence**, with the design sensitivity (§6) as the reason: at n = 15 braking resolves only Δ ≳ 0.4. Reported as a precision result, together with the n that would resolve a smaller Δ |

- **The yield floor and the pilot stopping rule (S20,
  `kit/tools/nullyield.py`).**
  - **Why a floor:** with few probes the cluster bootstrap degenerates and its
    interval is too *narrow*. The error it makes is a false **"no excess"**,
    not a false excess. Among simulated studies with a real braking excess
    (true Δ 0.23), the rule says "no excess" in 53% of studies at 0–2 pooled
    probes, 23% at 3–4, 10% at 5–6, and ≤ 3% from 7.
  - **Near the margin** (true Δ 0.13, just above the 0.10 MDI), that rate
    levels off at ~5–8% from 7 probes on and does not shrink further. This
    residual is not fit uncertainty: the nested interval moves verdict rates
    by ≤ 0.03. It is within ~2 Monte Carlo SE of the nominal 5%, plus the
    usual percentile-bootstrap undercoverage at 15 clusters.
  - The false-excess rate stays at 1–6% in every bin, so the floor guards the
    "no excess" verdict alone.
  - **The floor is 7, and it was chosen post hoc.** The criterion fixed before
    the run tested the false-excess rate and was vacuous (it returned 0).
  - **Stopping rule:** the pilot's probe count cannot carry one. At the
    committed σ, P(zero braking probes over the n = 2 pilot) = 0.16, so seeing
    none says almost nothing.
  - The σ gate (gate 0, σ_study ≤ 4.5 m) does most of the job instead.
    P(braking reaches 7 pooled probes at n = 15) is 0.93 at a true σ of 4 m,
    0.61 at 5 m and 0.27 at 6 m. σ_study sits ~0.3 m above the nominal σ,
    because drivers differ in noise, so the gate admits up to a nominal
    ~4.2 m, where P(K ≥ 7) ≈ 0.85–0.93. Gate 1 is applied to the observed
    count at analysis. The pilot's σ is the forecast.
  - Corner speed clears the floor at every σ tested (P ≥ 0.98). Apex has no
    verdict, so its floor is moot.
- **What stands regardless of the outcome.** The headline contribution is the
  **attribution method, validated in simulation** before any data (author
  decision, 2026-10-30), so it does not depend on Δ's sign or verdict. It was
  run through the real controller (`kit/tools/` and `README.md`):
  - **Recovery:** the no-dependency rate is recovered with RMSE 0.032 under
    an exponential truth. Under a power-law truth it is 0.051, which fails the
    0.045 criterion.
  - **Unbiasedness:** an injected dependency is returned at 1.01–1.04 of its
    size.
  - **Model check:** false alarm ~5%, and harmless misspecifications are kept
    after escalation.
  - **Decision rule:** a false excess in 4% of studies.
  - **Time profile:** it separates a transient of up to 2 laps from a
    sustained deficit for braking, and one of 1 lap for corner speed.
  - **Second result:** RQ1 reliability, which survives a study in which nobody
    reaches a probe.
  - **Not claimed:** the empirical Δ adds an application whose precision is
    stated in advance. It is not the contribution.

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
- **Never claimed:** dependency in the learning sense, i.e. on a delayed
  retention test. The probe and unassisted block are immediate tests, so the
  construct is *immediate* guidance-contingent performance (§4).
- **Never claimed:** that a sustained excess is **dependency rather than
  ongoing benefit** of the cue. An immediate test cannot separate them, and
  guidance dependency is discussed only as a candidate mechanism.
- **Not claimed without the time profile:** that Δ is guidance-contingent
  performance rather than a withdrawal transient. Δ is reported as a
  probe-failure excess. The sustained reading is made only where the
  pre-specified profile supports it (§4), and never for apex.

## 8. Known open questions (for the reviewers to press on)

1. **Probe as intervention (v9 threat 6): partly addressed.** Removing a cue
   may itself change behaviour (surprise, attention shift), apart from
   dependency. The null cannot exclude this, and there is no randomised arm.
   - The design's answer is the pre-specified time profile (§4): a transient
     is separated from a sustained deficit if it lasts at most 2 laps
     (braking) or 1 lap (corner speed).
   - **Residual:** a decaying profile cannot tell a transient from a dependency
     that is quickly re-acquired, and no profile identifies either causally.
     A transient longer than the horizon is read as sustained.
2. **Calibration circularity (addressed; residual stated).** The primary null is
   fitted on the same participants' **guided** laps, not the cue-off laps whose
   failures it judges. So the probe outcomes and unassisted laps never calibrate
   it, and an injected dependency is not absorbed (simulated: 1.00–1.04 of it
   returned for braking).

   What remains is by design, not circular: each driver's own guided laps set
   that driver's null. The cost is a broader construct, because Δ includes any
   on-guidance benefit that is lost at withdrawal (§5).

   The cue-off null, which *is* fitted on the judged laps, is kept only as a
   lower bound with its measured attenuation (0.22–0.82).
3. **What "premature" means (F2).** v9 defines it relative to the system's own
   probe criterion: decision accuracy, not harm.
4. **Separating learning from noise in 15 laps** (F5/F6; v9 threat 2). This is
   now answered by a parameter-recovery simulation for the forms and noise
   levels tested (§5):
   - The primary null, fitted on each driver's full-salience laps, recovers the
     no-dependency braking rate with RMSE 0.032 at the committed noise under an
     exponential truth (criterion met up to 5 m). Under a power-law truth it
     gives 0.051, which fails (criterion met only up to 3 m).
   - Fits on cue-off data alone (the 4-lap unassisted block, with or without
     probe laps) do worse: RMSE 0.043–0.12. An unassisted-only fit extrapolates
     the trend back over the guided laps with errors of ~5σ.
   - **What stays open:** the trend form. A power-law truth breaks recovery at
     the committed σ. The model check catches a wrong form in only ~35–50% of
     studies, and the σ gate (§5) catches part of the rest. Above ~5 m no form
     recovers, hence the gate. Only exponential and power-law truths were
     tested.
5. **Whether a group-level excess from ~40 clustered probes can support the
   interpretation: answered (§6).**
   - Censored probes are excluded from both sides and counted (§4). This was
     shown unbiased.
   - The decision rule and its simulated sensitivity show that braking
     resolves only Δ ≳ 0.4 at n = 15, and an indeterminate verdict is the
     expected outcome under no dependency.
   - **Open:** n itself (F4).
6. **KR is withdrawn with the cue during a probe**, so the construct is
   "guidance", not "cue".
