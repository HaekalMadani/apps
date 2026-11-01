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

- **Guidance dependency:** the learner was relying on the guidance, so the
  deficit lasts while the guidance stays off.
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
    trend) and lap-to-lap noise but no guidance dependency**, run through the
    same controller, lap budget and corners.
  - The **probe-failure excess** is Δ = P_obs − P_null. That is the measured
    quantity. The null excludes regression to the mean and practice. It does
    **not** exclude a withdrawal transient, so Δ has two readings. A
    pre-specified time profile decides which one the data support:
    - **Guidance dependency** (cue plus KR, withdrawn together) is a
      **sustained** deficit. It includes the loss of any benefit the guidance
      gave while it was on. It shows as a positive late-unassisted level: the
      residual on unassisted laps 2–4 against the null.
    - **Withdrawal as an intervention** is a **transient** deficit confined to
      the first withdrawn lap. It shows as probe decay: the first probe lap
      worse than the second, with the late-unassisted level at zero.
    - **The reading is asymmetric.** A sustained profile argues against a pure
      transient. A decaying profile fits a transient, but it also fits a
      dependency the learner quickly re-acquires without guidance. So it is
      reported as "transient or fast re-acquisition", never as "no dependency".
    - **Simulated separation for braking** (`kit/tools/nulltransient.py`, 1000
      studies per scenario, n = 15, driver-heterogeneous effects):
      - a sustained deficit of 0.25–0.5 band raises the late level in 94–100%
        of studies and leaves probe decay at its 5% false-alarm rate;
      - a one-lap transient raises probe decay in 74–96% and leaves the late
        level at 5–6%.
    - **Corner speed:** probe decay is usable (96–100%), but the late level
      detects a sustained deficit only at 0.5 band (82%). This is because few
      participants still have that element visible when training ends.
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
    - So the dependency reading is **immediate guidance dependency**: a
      performance deficit that persists across the immediate no-feedback window
      (4 laps, about 5 minutes). It says nothing about what the learner would
      retain after a delay.
    - "Sustained" in this brief always means sustained within that window.
    - A delayed retention test was considered and not adopted (author decision,
      2026-10-30). It would add rig time to the single sitting, and it would
      still compare with the null rather than with a lower-feedback group.
- **RQ3, the system:** Lua/Python parity, real-time cost, live behaviour.
  Supporting evidence, not a research contribution.

## 5. The null (the load-bearing part)

- **What counts as dependency (decided).** Two withdrawal effects both count,
  if they are **sustained across the immediate no-feedback window** (§4). A deficit confined to the first withdrawn lap is the
  withdrawal-transient rival instead (§4):
  - the mean error shifting back toward the novice direction when the guidance
    is withdrawn;
  - lap-to-lap variability increasing when it is withdrawn.

  So the null that contains no dependency, by definition, is calibrated on
  **guided** performance. Δ therefore includes the loss of any benefit the
  guidance gave while it was on.
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
  - Its braking recovery RMSE is 0.032 (0.027 when reduced laps are included).
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
- **Pilot gate:** if the pilot's measured braking σ exceeds 4 m (the committed
  value, the highest noise level at which the null recovered), braking Δ is not
  reported as a dependency estimate. At 2× that noise no null form recovers, and
  braking becomes as uninformative as apex.
- **Apex:** a Gaussian residual on an RMS metric recovers only ~0.6 of the true
  σ, and the cue-on apex null overstates Δ by 1.2–1.9×. Neither the model check
  nor escalation rescues it: P_null error stays at 0.10–0.25.
  - Simulation cannot settle the form, because the simulator's own apex noise
    (a folded Gaussian) is an artefact.
  - The form must be chosen from the pilot's apex distribution (G2), which is
    right-skewed in the recorded passes (mean 2.49 m, median 1.52 m).
  - Apex is uninformative by design anyway (§6).
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
- **Pre-registered decision rule (per element, decided).** The interval is a
  90% participant cluster bootstrap on Δ̂ = P_obs − P̂_null, with censored
  probes excluded.
  - **Excess:** the lower bound is above 0.
  - **No excess:** the upper bound is below the **minimum Δ of interest, 0.10**.
    This is tied to Gate G1's false-pass bound (≤ 10%). An excess of 0.10 means
    premature fades at the rate the design already declares tolerable, so the
    threshold reuses a declared design parameter rather than introducing a new
    one.
  - **Indeterminate:** anything else.
- **Simulated design sensitivity** (`kit/tools/nulldecision.py`, 300 studies
  per cell, n = 15, a sustained dependency varying between drivers; the
  interval does not resample within-participant fit uncertainty, so it is
  somewhat optimistic). For braking:

  | true Δ | median 90% CI width | P(excess) | P(no excess) | P(indeterminate) |
  |---|---|---|---|---|
  | 0.00 | 0.34 | 0.04 | 0.29 | 0.67 |
  | 0.08 | 0.40 | 0.10 | 0.15 | 0.76 |
  | 0.24 | 0.49 | 0.45 | 0.03 | 0.52 |
  | 0.37 | 0.50 | 0.67 | 0.00 | 0.32 |

  - **Braking resolves only large excesses at n = 15.** 80% detection needs
    Δ ≳ 0.4. With no dependency the expected verdict is **indeterminate**, and
    an indeterminate result is not evidence of no dependency.
  - A rough √n extrapolation puts 80% detection at Δ ≈ 0.24 near n ≈ 36.
  - The braking probe yield in this simulated population is ~0.8 per
    participant (~12 at n = 15), not 16. The population includes slow and
    non-learners, and the yield is a model output (M6).
- **Planned pre-registered predictions** (under the rule above):
  - **Braking:** the candidate for an excess, but only an excess of about 0.4
    or more is likely to be resolved. The expected verdict under no dependency
    is indeterminate.
  - **Corner speed:** its P_null is ≈ 0, so it resolves better than braking.
    The verdict is "no excess" in 95% of no-dependency studies, and an excess
    is detected in 83% at Δ ≈ 0.36. That rests on the **assumed** speed σ, so
    it carries no claim until the pilot measures that σ.
  - **Apex:** no verdict. It is uninformative by design, and its null is
    biased by +0.11 to +0.17.
- **What is reported under each outcome (pre-specified, decided).** These are
  evaluated per element, in this order. The first gate that applies decides.

  | # | outcome | what the thesis reports |
  |---|---|---|
  | 0 | **Element ineligible**: apex always; braking if the pilot's braking σ exceeds 4 m (§5); corner speed if the pilot has not measured its σ | P_obs and P_null **descriptively**, with the reason. No verdict |
  | 1 | **Too few probes** (yield floor: set with the pilot stopping rule, review item S20) | No Δ. The pre-stated fallback is RQ1 reliability plus the guided-vs-unassisted contrast from the 4-lap block, which every participant drives |
  | 2 | **Model check fails** after its one escalation (§5) | Δ̂ and its interval **descriptively**, named as "not a dependency estimate", with the failed check |
  | 3 | **Excess**: the lower 90% bound is above 0 | Δ̂, its interval, and the cue-off lower bound beside it. The construct reading comes from the time profile (§4). A **sustained** profile gives *immediate guidance dependency*. A **decaying** one gives *withdrawal transient or fast re-acquisition*. With neither, it is an excess without a construct reading |
  | 4 | **No excess**: the upper bound is below 0.10 | That the system's probe failures are accounted for by practice and noise within the 0.10 margin, i.e. cue-on gating did not withdraw this element prematurely beyond the design's own false-pass tolerance. Not a claim that dependency is absent |
  | 5 | **Indeterminate**: anything else; the expected braking outcome at n = 15 | Δ̂ and its interval, stated as **not evidence of absence**, with the design sensitivity (§6) as the reason: at n = 15 braking resolves only Δ ≳ 0.4. Reported as a precision result, together with the n that would resolve a smaller Δ |

- **What stands regardless of the outcome.** The headline contribution is the
  **attribution method, validated in simulation** before any data (author
  decision, 2026-10-30), so it does not depend on Δ's sign or verdict. It was
  run through the real controller (`kit/tools/` and `README.md`):
  - **Recovery:** the no-dependency rate is recovered with RMSE 0.032.
  - **Unbiasedness:** an injected dependency is returned at 1.01–1.04 of its
    size.
  - **Model check:** false alarm ~5%, and harmless misspecifications are kept
    after escalation.
  - **Decision rule:** a false excess in 4% of studies.
  - **Time profile:** it separates a transient from a sustained deficit for
    braking.
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
  construct is *immediate* guidance dependency (§4).
- **Not claimed without the time profile:** that Δ is guidance dependency
  rather than a withdrawal transient. Δ is reported as a probe-failure excess.
  The dependency reading is made only where the pre-specified sustained profile
  supports it (§4), and never for apex.

## 8. Known open questions (for the reviewers to press on)

1. **Probe as intervention (v9 threat 6): partly addressed.** Removing a cue
   may itself change behaviour (surprise, attention shift), apart from
   dependency. The null cannot exclude this, and there is no randomised arm.
   - The design's answer is the pre-specified time profile (§4): a transient
     is separated from a sustained deficit for braking and, partly, for corner
     speed.
   - **Residual:** a decaying profile cannot tell a transient from a dependency
     that is quickly re-acquired, and no profile identifies either causally.
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
     no-dependency braking rate with RMSE 0.032 at the committed noise.
   - Fits on cue-off data alone (the 4-lap unassisted block, with or without
     probe laps) do worse: RMSE 0.043–0.12. An unassisted-only fit extrapolates
     the trend back over the guided laps with errors of ~5σ.
   - **What stays open:** at twice the committed braking σ no form recovers
     (hence the pilot gate). Only exponential and power-law truths were tested.
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
