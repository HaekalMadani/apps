# CLAUDE.md

Guidance for working in this repository. Read this before writing code.

## What this is

The implementation for a thesis: **telemetry-driven adaptive UI fading for novice
sim racing in Assetto Corsa**. The system reads real-time driving telemetry and
decides, independently for each piece of informational UI, when to fade that
scaffold out for a learner. It commits a fade only after a short **cue-off
probe**, and restores the scaffold if performance regresses (probe-and-revert).
The **system and its design decisions are a first-class contribution**, not just
plumbing for a study.

**The current framing is `thesis_framing_v9.md`** (2026-10-30; it supersedes v6,
whose novelty did not survive: "too common in learning-science engineering").
`implementation_plan_v2.md` and `evaluation_plan_v2.md` remain the build and
evaluation references, but where they still describe v6's design (adaptive vs
static, two pairs) **v9 and this file win**. Re-read v9 before each chunk of work:
drift toward overclaiming and toward sprawl is the documented #1 failure mode, and
v6 was lost to a novelty check run too late.

**`thesis_framing_v6.md` was DELETED on 2026-10-30.** Read it with
`git show 110156e:thesis_framing_v6.md`. Its last uncommitted edits (the
2026-10-14 `[CORRECTED …]` brackets) are preserved as
`novelty_audit/logs/thesis_framing_v6_uncommitted_edits_20261030.patch`. About 35
files still cite "framing v6 §N", including code comments, schemas, and the
**hash-pinned** `configs/simulation/simulation_report.json` and golden traces.
**Those citations are historical: do not edit hash-pinned artefacts to remove
them.** A "framing v6 §N" citation means "the v6 text at that commit".

**What the thesis may claim is fixed by `novelty_audit/CLAIMS_SHEET_v9.md`.** It is
built from a four-step prior-art audit (`novelty_audit/`, starting from its `README.md`).
Read the sheet before writing any comment, docstring or report text that names a
contribution, and **run a prior-art check before building toward any new claimed
contribution**. See **Thesis framing v9 — what binds** below.

Two companion documents to this one: **`MILESTONE_LOG.md`** is the full build
record (which block found which fault, what was measured, what was tried and
abandoned) and **`BAND_CALIBRATION_BRIEF.md`** holds the band-calibration
question *and its answer* (2026-10-14) — the literature has **no rule** for
setting a tolerance band for novices, so the floors are set by a standard-setting
method instead; its reply document is
`TRACE_tolerance-calibration_lit-review_v1.0.md`. Read that answer section before
touching a band, a floor, the EVM or the qualification window. This file keeps
what binds current work; the log keeps why.

## Thesis framing v9 — what binds (2026-10-30)

The research question moved from "does adaptive fading help?" (v6, an adaptive vs
static contrast) to **"how often does a guided-performance rule fade a cue
prematurely, and how much of that is guidance dependency rather than lap-to-lap
variability?"** TRACE is both the engineered system and the **measuring
instrument**: its probes are the observations.

- **RQ1, within-session reliability:** per-element, per-corner ICC / SEM / MDC
  for novices, **detrended**. It is a finding in its own right (TRACK 2026 names
  it as the missing "first rung") and the null's calibration input. It is also the
  result that survives a study in which nobody reaches a probe.
- **RQ2, decision accuracy (core):** the **probe-failure excess**
  Δ = P_obs − P_null per element.
  - **Construct boundary (author decision 2026-10-30, ARS roadmap R8):**
    - **Guidance dependency** is a **sustained** withdrawal deficit, read from
      the late-unassisted residual level.
    - A deficit confined to the first withdrawn lap is the **withdrawal-transient
      rival**, read from probe decay (first probe lap − second).
    - The profile is pre-specified and asymmetric: a decay is also consistent
      with fast re-acquisition. Simulated separation is in
      `kit/tools/nulltransient.py`. Apex gets no reading.
  - **Immediate, not learning-level (author decision 2026-10-30, ARS roadmap
    R9).** The probe and the unassisted block are **immediate, within-session
    no-feedback tests**. The field judges dependency on a DELAYED retention or
    transfer test (Salmoni et al. 1984; Winstein & Schmidt 1990; the
    learning–performance distinction, Kantak & Winstein 2012).
    - The construct is therefore **immediate guidance dependency**: a deficit
      sustained across the ~4-lap no-feedback window. Never claim it is
      dependency in the learning sense.
    - A delayed retention block was considered and not adopted.
    - **Terminology:** older prose, code comments, tests and one integrity
      message call the probe "the retention test". Read that as "the immediate
      no-feedback test". The KR-suppression argument it carries is unchanged,
      because any no-feedback test with feedback running measures
      performance-with-feedback. Do not churn code or tests over the word; use
      "immediate no-feedback test" in new writing.
  - **Naming (author decision):** the measured quantity is the *probe-failure
    excess*; **guidance dependency** is its *interpretation*. "Guidance" means the
    cue **and its KR**, because both are withdrawn during a probe. Never write
    "cue dependency", and never present the interpretation as the measurement.
  - **The null** is a synthetic learner with **learning (practice trend) and
    lap-to-lap noise but no guidance dependency**, run through the real
    controller under the same lap budget and selection rule.
  - **Fit the primary null on FULL-SALIENCE laps only; report the cue-off null
    as a lower bound** (decided 2026-10-30, ARS roadmap R5; this **reverses**
    the council rule "fit on cue-off laps").
    - Reduced salience is excluded because it is a partial withdrawal. When half
      the dependency appears there, a full + reduced fit absorbs 11–26% of
      braking Δ, and the full-only fit does not (1.01–1.11). The full-only fit
      costs 0.003 RMSE (0.032 vs 0.029).
    - **Definition (author decision):** a mean shift on withdrawal and a
      variance increase on withdrawal **both** count as guidance dependency.
      So the null that excludes dependency by definition is the one fitted on
      guided laps. Δ therefore includes the loss of any benefit the guidance
      gave while it was on. **State that in the RQ2 construct text (R8/R9).**
    - **Measured** (`kit/tools/nullabsorption.py`, tables in
      `kit/tools/README.md`): for braking and corner speed the cue-on null has
      attenuation 1.00–1.04, so it is unbiased. Its braking recovery RMSE is
      0.027. The cue-off null hides 20–80% of a real braking dependency (~75% of
      a pure variance increase). Leaving each driver's own probes out barely
      helps, and an all-laps trend is worst at a mean shift.
    - The council's worry ("a cue-on σ is biased low") is now part of the
      definition rather than a bias.
  - The null must pass a pre-specified model check, or Δ is not reported as a
    dependency estimate (v9 §7.3 step 5; Käser & Alexandron 2023 found that
    half of simulated-learner studies never validate their simulator).
    **Resolved 2026-10-30 (methodology W2):** the null is fitted on guided laps,
    so "reproduce cue-on statistics" would be in-sample, and a cue-off check
    would reject it exactly when dependency exists. The check uses three
    guided-lap features the fit does not target:
    1. leave-one-lap-out predictive coverage;
    2. the post-qualification criterion pass rate while the cue is still on;
    3. lag-1 residual autocorrelation.

    Each must fall inside the central 98.3% of the fitted null's simulated
    distribution (95% Bonferroni-adjusted over the three checks).
    - **Escalation before abandoning:** a failed check 1 refits the noise as
      Student-t and a failed check 3 as AR(1), then all three re-run. Check 2
      has no escalation.
    - **A trend-form agreement GATE was simulated and REJECTED.** It discarded
      69% of correct nulls. The power-law trend is a sensitivity analysis only.
    - **Measured** (`kit/tools/nullcheck.py`): false alarm ~5%, and after
      escalation braking Δ is kept for 95% of correct and 88% of autocorrelated
      truths. A wrong trend form is caught in only ~40–50% of studies, which is a
      stated limitation.
    - Full text: `novelty_audit/review/CONCEPT_BRIEF_v9.md` §5.
- **RQ3, the system:** parity, real time and live behaviour. It is the system
  chapter's evidence, not a research contribution.
- **RQ4 (desynchrony): cut**, or moved to an appendix. Nothing in the audit makes
  it novel.

**Decisions that bind code and analysis:**
- **Decisions per element, analysis per corner.** v9 §5.2's "per element ×
  corner" controller was **priced and ruled out** (`kit/tools/percornerscan.py`,
  `kit/tools/README.md`). It quadruples probes by fading on noise: 79% of
  non-improvers end with a cue faded, and 5.5% have a cue removed despite
  regression. That fails both G1 bounds at every window from 2-of-3 to 5-of-5.
  The per-corner breakdown instead uses the **8 cue-off corner passes each
  element-wide probe yields**. v9 §5.2 is wrong here; **this file is right**.
- **Single condition: TRACE adaptive only** (v9 §6). There is no static arm, so
  the between-subjects contrast and the RQ2 Bayesian condition model described
  further down are **superseded**. The `static` and `off` modes stay in the code
  as config values for review and dev blocks. **The condition stays a config
  field, never a code path.**
- **Pre-register the per-element prediction before data.** Under the committed
  model the noise-only probe-failure rates are **corner speed 0.00, braking 0.16,
  apex 0.53**. So:
  - apex is *uninformative by design*;
  - braking is the element where an excess is identifiable, but at n = 15 only
    one of about 0.4 or more is likely to be resolved (R6);
  - corner speed carries no claim until the pilot replaces the **assumed**
    speed sigma.
- **Precision.** About 2.8 probes per typical participant gives ~42 at n ≈ 15,
  **clustered**. Analyse with a participant cluster bootstrap. The pooled ±0.12
  is optimistic, and per element the interval is ±0.2 or wider.
- **Decision rule and censoring (author decisions 2026-10-30, ARS roadmap R6
  and R7).** Per element, a 90% participant cluster bootstrap on Δ̂:
  - **excess:** the lower bound is above 0;
  - **no excess:** the upper bound is below the **minimum Δ of interest
    0.10**, tied to G1's ≤ 10% false-pass bound;
  - **indeterminate:** anything else.

  **Censored probes are EXCLUDED** from P_obs and P_null alike, with the
  censored count reported. As-pass and as-fail are sensitivity analyses.
- **Outcome-by-outcome reporting (author decision 2026-10-30, ARS roadmap
  R1).** The table is in `novelty_audit/review/CONCEPT_BRIEF_v9.md` §6.
  - The gates run in order: ineligible, too few probes, check failed, excess,
    no excess, indeterminate.
  - **The headline contribution is the attribution method, validated in
    simulation before data**, so it stands whatever Δ's verdict.
  - RQ1 is the second result. The empirical Δ is an application with
    pre-stated precision.

  Measured (`kit/tools/nulldecision.py`):
  - every censoring rule is unbiased when applied identically (|bias| ≤ 0.02);
  - braking false "excess" 4%, detection 45% at Δ 0.24 and 67% at Δ 0.37, so
    80% needs Δ ≳ 0.4;
  - with no dependency the braking verdict is indeterminate 67% of the time;
  - corner speed resolves better (P_null ≈ 0) but rests on the assumed σ.
- **The randomised probe-timing arm (v9 §7.4) is out of reach.** It needs ~80
  probes, i.e. ~28 typical participants, so Δ stays model-based. Do not build it.
- **The published-rule audit ("C-lite") is dropped as a contribution.** Ye et al.
  2016 already calibrate mastery rules, including M-in-a-row, on simulated
  perpetual non-learners. If it is run, it is positioning only.
- **The brake and speed lap-to-lap sigmas in `simulate.MODEL` are assumptions**
  (only apex is measured). Gate G2's pilot must measure them, and must measure
  them on **cue-off** laps, before the null is frozen.

**v9's own text is stale on repo facts.** The repo wins:
- v9 §5.2 quotes 3-of-4 and a 3-lap probe; the frozen config is 2-of-3 and 2
  laps (`frozen-g1b`).
- v9 §5.1 and §6 say two tracks; pair 2 is descoped.
- v9 says "12–15 laps"; it is a 15-lap block ended on a lap count.
- **v9 omits the 4-lap unassisted block, NASA-TLX and the interview.** The block
  stays: the null now depends on it. Whether the TLX and interview stay is an
  **open author decision**, so the apparatus notes below that mention an
  interview are kept.

**Open v9 flags:**
- F1, F2, F4 (N), F5 and F6 (noise-model form; pooled vs per-driver residual).
  **F5/F6 now have evidence (ARS roadmap R2, 2026-10-30,
  `kit/tools/nullrecovery.py`; tables in `kit/tools/README.md`).** This is a
  parameter-recovery study on synthetic participants through the real
  controller. The pre-stated criterion was braking RMSE(P̂_null − P_true) ≤ 0.045.
  At ≤ 1× the committed sigmas it is met by the **cue-off fit only with an
  exponential trend whose rate is POOLED across drivers, plus per-driver
  amplitudes and per-driver σ** (worst 0.043). The all-laps-trend /
  cue-off-σ fit also meets it (0.035), but it touches R5. Every
  unassisted-only fit fails. Per-driver σ beats pooled σ. At 2× noise nothing
  recovers, because braking then becomes as uninformative as apex
  (P_null ≈ 0.53). The apex σ needs a non-Gaussian form, since a Gaussian
  recovers ~0.6× of it.
  **R2 and R5 CLOSED by author decision (2026-10-30). R5 superseded R2's
  primary:**
  - **Primary null:** a per-driver exponential trend and per-driver σ, fitted on
    **full-salience** laps. It meets R2's criterion with braking RMSE 0.032.
  - **Lower bound:** R2's cue-off null, which is an exponential trend with one
    rate pooled across drivers, per-driver amplitudes and per-driver σ (RMSE
    0.043). Report Δ against it beside the primary, with the measured
    attenuation.
  - **Pilot gate:** if G2's measured braking σ exceeds **4 m** (1× the
    committed value, the highest level that recovered), braking Δ is not
    reported as a dependency estimate, and that is stated as a limitation. The
    region between 1× and 2× is untested, and so is the cue-on null at 2×.
  - **Still open:**
    - the apex noise form (the cue-on apex null overstates Δ by 1.2–1.9×);
    - **the apex noise form:** a G2 decision from the pilot's apex distribution.
      The simulator's own apex noise is an artefact, so it cannot settle it.
- **F7, answered here:** the existing MDC / ICC analysis (`kit/tools/mdc.py`) is
  already detrended, but it pools **mixed cue states**. Of its seven
  `_blocks.PAIR1_HUMAN_NATIONAL` blocks, two are `off` (cues and KR hidden), one
  is `static`, and four are `adaptive` blocks in which nothing faded (cue-on).
  All are **n = 1, the researcher**, and pre-KR. So it is a method prototype for
  RQ1, not RQ1. The null's calibration needs a **cue-off-only split** (the two
  `off` blocks now; probe and unassisted laps later), reported beside the
  cue-on split. That split is also the first direct check of the cue-on-σ bias.
- Resolved: F3 (out of reach), F8 (use the repo values), F9 (Bugeja, see item 6
  below), F10 (Nickl verified), F11 (narrowed), F12 (citations verified).

## Roadmap & progress (TRACE)

Build order from `implementation_plan_v2.md` §4 (full detail there — don't
duplicate it here). **Standing rule: update this section whenever a milestone's
status changes; never start Mn+1 before Mn's exit test passes.**

**The full build record is `MILESTONE_LOG.md`** — which block found which fault,
what was measured, what was tried and abandoned. This section keeps status, the
gates, the decisions that bind later work, and the open to-dos. Before reversing
any decision below, read its entry in the log: most were taken because something
broke in game.

| milestone | status | exit test |
|---|---|---|
| **M0** Skeleton | done 2026-06-11 | configs round-trip through validation in Lua and Python ✓ |
| **M1** Sampler + logger | done 2026-06-15 | 30-min drive → gap-free logs, integrity PASS, no frame cost ✓ |
| **M2** Annotation + pass tracking | done 2026-09-07 | one pass per annotated corner per lap, correct validity flags, both tracks ✓ |
| **M3** Reference pipeline | done 2026-09-08 · closes **G0** | G0 met; markers render at extracted coordinates ✓ |
| **M4** Controller + simulator | done 2026-09-08 · closes **G1** | parity suite green; G1 targets met; config frozen + hashed ✓ |
| **M5** Full rendering + salience | **code complete**, visual review open | scripted controller states produce the intended visuals on both tracks |
| **M6** Experimenter panel + dry run | **in progress** (started 2026-10-09) | a complete fake-participant dataset ingested by the frozen analysis scripts |
| **M7** Pilot (eval Phase 2) | not started · closes **G2** | G2 met (EVM finalised, config re-frozen); main study may begin |

Gates (from `evaluation_plan_v2.md`): **G0** reference quality — **met
2026-09-08** (`configs/references/G0_REVIEW.md`), **re-opened** by the pair-1
re-record (M6 item 5); **G1** simulation feasibility — **met 2026-10-15**
on restated targets, config re-frozen as **`frozen-g1b`** at 15-lap blocks
(`configs/simulation/G1_REVIEW.md`); **G2** pilot calibration (M7) — open, and it
owns the band floors.

**G1's TARGETS 2 AND 3 WERE RESTATED on 2026-10-15, and "MET" now means
something weaker than it did — say so when quoting it.** Both had been
zero-tolerance clauses, and both were satisfied only by the old `frozen-g1`
floors, **which satisfied them by never fading anything, for anyone** (on real
recorded passes the braking and apex elements never advanced in a single block).
*A conservatism target is trivially met by a system that never acts*, so neither
could judge a working configuration. They are now **stated rates with the
counter-rate reported** (`simulate.TARGET_RATES`; the contrasting-groups style
of `BAND_CALIBRATION_BRIEF.md` §E, and the move eval plan v2 already made once
for target 3's staggered clause):

| target | bound | measured | counter-rate |
|---|---|---|---|
| 2 false pass — a non-improver fades | ≤ **10%** | **5.75%** | false fail **28%** |
| 3 removal despite regression | ≤ **2%** | **0.75%** | latency excess over the floor |

**Both bounds are DECLARED DESIGN PARAMETERS and provisional until G2** — no
published rule exists for a tolerance of this kind, which is the review's
central finding. 10% is justified by the *ratio* (the design's asymmetry needs a
false pass rarer than a false fail; the asymmetry is asserted as well as the
bound), and 2% by the error being costlier (a late reversion costs one lap, a
removal the rest of the block) *and* by discriminating: every 3-of-4 alternative
at workable floors measures 12–26%. **Read the current hash and the per-target
table from `G1_REVIEW.md`, never from here.**

**The frozen config is re-pinned by its hash, not by trust.** Any edit to
`configs/controller_config.json` changes its SHA-256 and fails
`test_m4_simulate.py` until the Phase 1 simulation is re-run and
`configs/simulation/` regenerated. A config the simulation never saw is a config
no gate has passed. **Read the current hash from `G1_REVIEW.md`, never from
here** — this line used to carry a copy and it went stale within a month. The
same now holds for the reference tables, which `simulation_report.json` pins
individually: a reference the simulation never saw is as much a problem as a
config it never saw, and that one was learned the hard way (the committed report
described a pair-1 table the repository no longer held, silently, for days).

### Apparatus: tracks, cars, references

- **Both pairs are Silverstone layouts** — `ks_silverstone` `national` (pair 1,
  **4 corners**, all with braking) and `international` (pair 2, **5 corners**,
  all with braking). They share no tarmac in AC, so pair 2 is not pre-learned
  during pair 1. Red Bull Ring was dropped. Rationale and the quorum-granularity
  consequence: `configs/annotations/README.md`.
- **Different cars per pair** — `ks_bmw_m235i_racing` (pair 1) and
  `ks_audi_tt_cup` (pair 2). One venue makes the layout a thin separator; a
  second car pushes back on the carryover cost framing v6 §63 flags. `pair` is a
  nuisance fixed effect, so the car/layout confound costs nothing
  interpretively. A GT3 was tried and rejected: the block is time-boxed, so a
  faster car yields more laps rather than a shorter session, and its corner
  speeds are unreachable for a novice.
- **The reference is AI-only. There are no human validation laps** (2026-09-08,
  superseding "the researcher drives them"). A beginner-recorded reference is
  not a weaker expert reference but a **novice** one, which would drag the
  target toward novice performance and fade the scaffold when a participant
  drives like a beginner. Every corner keeps `source: "ai"`; `EVM_human` is
  unused. **The claim that the AI's brake points fall within a competent human's
  tolerance is NOT established — state it as a limitation.** The
  compare/substitute tooling is built and tested for the day it can be run.
- **Consequence: Gate G2 absorbs G0's lost job.** The pilot is the only
  empirical check that the reference is *reachable* by real novices, so a G2
  failure means recalibrating band floors (or revisiting the car), not tuning
  the EVM.
- **Expert reference = AC AI at a strong but sub-maximal strength, stamped per
  block** (revised 2026-10-10 from "95–100%"), 12 laps per pair, fixed setup,
  logged through this project's own pipeline. **Why sub-maximal:** at 100%
  nothing ever faded for anyone, and the deviations were systematic bias rather
  than scatter (median 14.9 m early, 9.4 km/h slow, ~85% of passes on the same
  side), so the target was wrong rather than the tolerance too tight. The same
  162 human passes come out at +8.1 m and +0.31 km/h against the 85% table. 80%
  over-corrects. **Pair 1 loads the 85% table; pair 2 still loads its 100% one,
  which is an apparatus inconsistency that must be closed before any participant
  drives.**
- **Substitution rule** (for the day a human reference exists): substitute a
  corner when `|mean_human − mean_AI| > max(σ_AI × EVM_AI, floor)` — if a
  competent human would fail the AI-anchored criterion, that criterion is not a
  usable target. **Per corner, never per element**: mixing a human brake point
  with an AI apex line describes a corner nobody drove. The same argument
  forbids mixing AI *strengths* across elements.
- **Reference tick logs are not scratch.** Both 100% reference blocks' tick logs
  were deleted, so neither table can ever be re-extracted — which is why pair 1's
  reference had to be *replaced* rather than re-extracted when the braking zones
  moved. Keep them.
- **σ_ref of exactly 0 is legal** (the AI is that repeatable); the band floors
  absorb it. The guard against a spurious σ is a minimum contributing-lap count
  in the extractor, not a schema bound.
- **G0's and G1's numeric clauses are regression-tested, not console output.**
  Lap-time CoV and per-corner contributing-lap counts live in the reference
  tables and are re-asserted against the committed files on every run; the
  committed simulation report's verdict and its config/reference hashes likewise.
  A hand-edit or a re-extraction cannot quietly drop a pair below a bar.

### Annotation

- **A missing or invalid annotation is a HARD refusal for a participant block**
  (impl plan §1) — a block that silently records no passes cannot be re-run on
  the same person. A **dev block** (explicit toggle, default off) records ticks
  only on an un-annotated track and is stamped `dev_block: true` so it can never
  be read as study data.
- **`zones.braking` is OPTIONAL**: a corner taken flat has no braking zone, no
  marker, no criterion, and is out of that element's quorum denominator. Brake
  marks are all-or-neither in the annotator, and the zero-applicable-corners
  quorum is guarded.
- **`entry`/`exit` gates are pass brackets, not driving landmarks.** Nothing is
  measured at them.
- **Config fields are constrained at the UI, not just validated offline.** A
  free-text sequence field let a typo write a schema-invalid manifest that only
  failed hours later at the integrity check; it is now an A/B/C/D/none radio
  group. Apply the same principle to any field a panel adds.
- **`annotate.py` checks geometry, not just completeness**: driving order along
  two chains (the braking zone may overlap the corner-speed window — trail
  braking), apex gates inside the corner-speed window, no overlapping pass
  brackets. Both study annotations are regression fixtures, as are both
  reference tables: they are the files the game loads and they are hand-edited.
- **Drive-and-mark braking zones are a starting point, not a contract.** They
  are captured by driving slowly and pressing a button, which put National's
  corner 1 down as "taken flat" when at racing pace it is the second-heaviest
  braking zone on the lap, and left three zones opening *after* the expert brake
  point. Always re-check a zone against the expert reference before trusting a
  brake metric.
- **Braking-zone room is budgeted in SECONDS, not metres** (2026-10-10). 60 m at
  Copse's 197 km/h is 1.1 s; the same 60 m at corner 4's 114 km/h is 1.9 s.
  Target **1.5 s early / 1.0 s late** per corner, with the arithmetic written out
  in the annotation's `notes`. The threshold in `reference.py` stays in metres
  (the reference table carries no approach speed) with the reasoning beside it.
- **The zone-fit check looks BOTH ways.** A learner braking later than the zone
  end yields a null exactly as one braking earlier than its start does, and the
  corner silently leaves the braking element's evidence either way.
- **A compound corner with two braking events is two corners** (framing v6 §107).
  National's corner 3 was split into 3 and 4 on an AI trace showing 113 m of
  acceleration between two braking events. *But a novice who does not accelerate
  between them drives it as one corner* — observed at G0, and a finding about the
  split rather than about the driver. G2 revisits it.

### Criteria and bands

See **Competency metrics** below for the full definitions. What binds:

- **Every gate produces a PER-PASS boolean.** Nothing window-level leaves the
  evaluator. Do not reintroduce v5's windowed-variance consistency gate: it
  cannot be a per-pass boolean and a variance from 3–4 samples is a coin flip.
- **Bands are floored and source-dependent**: `band = max(σ_ref × EVM_source,
  floor)`. Measured σ_ref sits far under every floor, so **the floors set every
  band** — all 27 of them, asserted as an exact count in `test_m4_evaluator.py`
  so a re-extraction or a G2 EVM change surfaces there rather than quietly
  invalidating a sentence in the thesis. Floor calibration is the load-bearing
  part of G2.
- **A null criterion is NO EVIDENCE, not a failure.** Accepted residual risk: a
  corner yielding only nulls **stalls** its element instead of fading it. Null
  counts are stamped into every pass record and shown live on the panel.
- **Invalid passes still feed the controller** (eval plan v2) — only *null*
  criteria are withheld. Off-track and wall-contact passes have real metrics.
- **The apex metric needs a LINE, not a point**: `zones.apex_window_half_m`
  (default 20 m) plus a sampled `apex.gates[].line` and `mean_rms_m`.
- **The corner-speed gate is ONE-SIDED** (`criteria.corner_speed_gate`,
  `slow_only`, 2026-10-14) and so is the apex gate: beating the reference is not
  an error. `two_sided` is kept as the comparison case. One function per language
  (`evaluator.corner_speed_ok`) knows the shape, because the live HUD colour and
  the recorded verdict must not be two rules.
- **The braking consistency gate is a VE proxy and it punishes improvement.**
  Over the laps where KR fixed this driver's brake point, the accuracy gate
  passed 13 of 16 passes and the criterion passed 3: the rolling mean still
  carried the earlier, worse passes. The gate exists to stop "reliably 30 m
  early" counting as competence, which the accuracy gate already covers. **The
  FIRST G2 item as of 2026-10-14, not the second:** `windowscan.py` measures that
  the braking element **never completes a traversal in any simulated stream** —
  0% removed, every learner type — and the gate is most of why (left-`full` goes
  4% → 51% → 84% as the ratio goes 0.5 → 1.0 → 2.0). It is not all of why: with
  the gate effectively off, removal still only reaches 2%, because σ/band for
  braking is 4.0/5.0 = 0.80. Measured options: the ratio (at ≥ 1.0 the gate stops
  binding at all), a mean over in-band passes only, or dropping it and letting
  the accuracy band bound the scatter.
- **G2 band-floor candidates, measured** (162 human pair-1 passes, 85% reference,
  real evaluator): at the frozen floors the per-pass rates are braking **6.0%**,
  corner speed **31.5%**, apex **7.4%**. At 15 m / 11 km/h / 3.0 m: 59% / 74% /
  73%. At 18 / 12 / 3.5: 71% / 80% / 78%. A 3-of-4 corner rule wants ~75%.
  Braking is the laggard because it is the AND of two gates that fail on
  *different* passes. **Do not set these yet** — and note the braking figures
  predate KR, which moved this driver inside ±3 m within three laps, so measure
  the floor *after* the §0A diagnostic rather than before it.
- **The floors are now set by a METHOD, not by a sweep** (2026-10-14, from the
  literature review — `BAND_CALIBRATION_BRIEF.md` §E). Floors become
  **contrasting-groups cut-scores** (Jørgensen, Konge & Subhi 2018) fitted to
  early-practice vs plateau distributions of the *window* statistic, with the cut
  placed at a stated theoretical false-pass rate and the false-fail rate
  reported; window length comes from **minimal detectable change** (Weir 2005),
  sized so MDC₉₅(n) falls under the improvement available. There is no published
  rule for a bandwidth width to copy — that is the review's finding, and it is
  what licenses a standard-setting method in its place. Both analyses run on data
  already recorded; both are G2 work.
- **THE APEX ELEMENT CANNOT BE FIXED BY A WIDER BAND *ON A PER-PASS CRITERION***
  (2026-10-14, tried and reverted; **narrowed the same day** — read the second
  half of this bullet before quoting the first). At `apex_m = 2.0` Gate G1 fails
  outright: non-improvers fading an element goes 0% → **100%**, and the element
  they lose is the apex one. The numbers, the per-corner table and the window
  profile are in `kit/tools/README.md` (`apexscan.py`) and `G1_REVIEW.md`. The
  reason is signal-to-noise, not threshold choice: the lap-to-lap SD within one
  corner is **1.86 m** and the whole improvement available at the apex is
  **~2.2 m**, so any band an improved pass clears, an unimproved pass clears on a
  good lap. Not the metric's shape (closest approach to the apex point has the
  same ratio) and not the apex *spatial* window's length (the deviation profile is
  flat across it, except corner 2's entry fifth, which is the one justified window
  change and needs a re-extraction). The novice model's apex parameters are known
  to be wrong by ~6× on sigma, so **G1's apex numbers are optimistic** — and
  correcting them fails G1's first target outright, because the apex element was
  carrying it (see the next bullet).
- **BUT THE EVIDENCE WINDOW IS A SEPARATE KNOB, AND IT WAS NEVER TRIED**
  (2026-10-14, `kit/tools/windowscan.py`, after the literature review).
  Everything above was measured with `qualification.window_passes` held at the
  frozen **3-of-4**, and `SWEEP_GRID`'s own comment rules the window out as
  structural rather than calibratable. It does not survive a longer window: with
  the measured apex novice, **4-of-6 at a 1.5 m floor advances the apex element
  for 41% of typical improvers and 0% of non-improvers**, and 8-of-10 at 2.5 m
  gives 87% / 0% — dominating 3-of-4 at 2.0 m (82% / 4%) on both margins. So the
  undecidable thing is the **per-pass unit of evidence**, not the element.
  **The lap budget then caps the window, and the binding parameter is
  `required_passes`, not `window_passes`.** A traversal needs
  `2 × required_passes + max(probe.laps, required_passes) ≤ laps` — 9 laps at
  3-of-4, 12 at 4-of-6, the whole 15 at 5-of-6, impossible from 6-of-8 up. It is
  a loose lower bound (it assumes every corner qualifies on its first
  `required_passes` passes at every stage), and `_quorum_ready` gates
  `probe_to_removed` as well, so a probe cannot complete on `probe.laps` alone.
  **Consequence, measured: at a 6-pass window the apex element gets exactly ONE
  stage.** 4-of-6 at a 1.5 m floor advances 40% of typical improvers to
  `reduced`, 1% ever enter a probe, 0% complete — and every apex configuration
  that *does* complete also advances a non-improver (2.0 m: 2% removed against 4%
  false; 2.5 m: 23% against 13%). So within a 15-lap block the apex element can
  be **decided once, not traversed** — report it as a two-stage ladder in effect.
  **And the window must be PER ELEMENT, not global:** moving every element to
  4-of-6 takes corner-speed removal from 83% to 1% with 94% of blocks ending
  mid-probe, so a global change destroys the one element that works. **Until G2 says otherwise the apex floor
  stays at 0.5 m and the apex element is expected not to fade for a novice** —
  report that rather than hiding it in a 3 m band, which is one and a half car
  widths and would make the one element whose job is line accuracy decorative.
- **σ/band per element predicts which elements can traverse at all**, and it is
  the cleanest way to state the system's feasibility: corner speed 2.0/4.0 =
  **0.50** and it traverses; braking 4.0/5.0 = **0.80** and it never does; the
  apex element at the measured sigma is 1.86/0.5 = **3.7**. Gate G1 passes on the
  one element whose assumed lap-to-lap noise sits comfortably inside its band.
  This is also the literature's own argument arriving from the other side: a
  bandwidth narrower than the performer's irreducible motor noise is not a
  tolerance (`BAND_CALIBRATION_BRIEF.md` §B.3).
- **`WALL_CONTACT_DEPTH_M` is provisional at 0.05 m**, confirmed clear of kerb
  contact (21 recorded contacts, deepest 0.0362 m, none ever fired) and
  **untested against a barrier** — and it may stay that way: depth is only
  captured inside a pass bracket, and at Silverstone the barriers sit beyond
  run-off, so reaching one sets `wheels_outside` to 4 and invalidates the pass
  first. The two gates are demonstrably not redundant at low depth: 11 of those
  21 contacts were on passes with no track-limits breach at all.
- **Pit involvement is a property of the LAP, not of a corner pass.** The AI
  boxing for fuel left a corner-4 pass that was clean by every validity gate and
  braked 35 m early, which took that corner's σ_ref from 0.49 m to 10.98 m and
  would have handed it a 33 m braking band — a trivially-true criterion from a
  reference that looks fine. `reference.pit_laps` is one definition with two
  consumers so they cannot disagree.
- **Two corner-speed windows do not always contain the driver's own minimum**
  (National corner 3, International corner 2). The window is fixed and applied
  identically to the AI and the participant, so the metric stays well defined.
  G2 revisits both.

### Controller

Every rule is stated in full at the top of `controller.lua`, which is the
authoritative description, and summarised under **The fading mechanism** below.
**Quorum readiness** and **one regression, one stage** were *added* at M4 because
the machine does not work without them — write them up in the system chapter as
design decisions, not implementation details. Also binding:

- **`config_id` + the manifest SHA-256 are the config's identity, not
  `schema_version`.** M4 added required fields without bumping it: no study data
  existed, and every block records the hash of the file it loaded.
- **Eval plan v2's staggered-reversion target sits below its own arithmetic
  floor.** With onsets one lap apart across four corners a majority has not
  regressed until the third lap. Target 3 is measured as **excess latency over
  that floor**. **Correct the plan's wording; do not change the controller.**
- **What G1 says the study should expect:** no simulated learner clears all three
  elements inside 15 laps, so **partial traversal is the common case** and the
  fade-timeline figures (v9 RQ3, live behaviour) should be built for it; **~37% of typical improvers end mid-probe
  (right-censored)**, rising to **28% for erratic learners** since the one-sided
  speed gate; and the reversion cap is reached by **1 stream in 400**, so expect
  roughly no participant to reach it and treat the `erratic_cap_reached` golden
  trace as the thing that exercises it.
- **WHICH element G1 actually rests on, measured 2026-10-14** (`windowscan.py`;
  the committed report only ever gave `elements_removed` as a count). **The
  braking element never completes a traversal — 0% of streams, every learner
  type.** The typical improver's 1.565 is corner speed (83% removed) plus the
  **apex** element (74%). So G1's first target rests on the apex element, whose
  model parameters are the ones known to be wrong: substitute the measured apex
  novice and the typical improver drops to **0.828** elements removed with apex
  removal at 0%, leaving corner speed alone and **failing the target**. The gate's
  MET verdict is a verdict about the committed model, which is what the gate
  always claimed — but it may not be quoted as "the machine traverses for a
  typical learner" without that condition. G1_REVIEW's third 2026-10-14 note
  carries it; the sentence there saying braking carried the target is struck.
- **The criteria almost never hold under novice driving** (M5 in-game blocks, and
  the reason G2 exists). Over a 30-pass block: apex 3 true / 27 false, braking
  **0 true** / 28 false / 2 null, corner speed 5 true / 25 false. All three
  elements sat at `full` for every pass and the controller never had cause to
  move a stage. Not a fault — floor-set bands meeting a real novice.

### Rendering and cues

- **Everything the renderer decides is pure and happens before any `render.*`
  call**: `markers.presented_stage(mode, stage)` applies the block's condition,
  `markers.visual(stage, salience)` turns that into an alpha plus which parts
  survive, `hud.readout(...)` and `hud.layout(w, h)` do the same for the HUD.
  **The condition stays a config field, never a code path** — a check inside a
  draw function read the *panel's* current selection rather than the running
  block's, so changing a radio button mid-block would have changed what a
  participant saw. `block.condition` is captured at start.
- **The reduced-salience form is `minimal`** (`salience.reduced_form`, config so
  it is frozen and hashed — it is a post-session interview topic). Markers draw the disc
  alone; the braking trapezoid becomes the band with no cross, stalk or label;
  the corner-speed readout keeps the target number alone. Reducing salience
  should reduce what the cue *tells* the learner, not just how bright it is.
  `dimmed` is the control case for that argument.
- **The braking marker is a trapezoid covering the accuracy band**, and its width
  **is the evaluator's own band, resolved once at reference load** and carried
  into the marker list as data — so the cue on the road and the tolerance the
  criterion applies are the same number by construction. `markers` never imports
  the evaluator. It **tapers in the direction of travel** because the two edges
  mean different things: braking early costs lap time, braking late costs the
  corner. **KNOWN RISK, recorded rather than engineered away:** showing the band
  may teach aiming at its edges — and it did, measurably (mean +7.5 m, 5 of 8
  passes between +5 and +10 m, i.e. 0.3–4.7 m before the early edge every time).
  At the frozen 5 m floor the shape is only 10 m long, 0.18 s at 195 km/h, and is
  measured at the car's origin, behind the nose the driver aims with. Post-session
  interview topic and a G2 band-floor input.
- **The HUD is a screen overlay, not an app window** (2026-10-14,
  `manifest.ini [UI_CALLBACKS] IN_GAME = hudOverlay`). **A stimulus must not
  depend on a setup step**: the cue window was never opened in the month it
  existed, so no participant-facing element had ever been seen on screen, and its
  position and size lived in the player's imgui state rather than in this
  repository. `hud.layout` puts the geometry back in code — sizes scale with
  window height, and the block **grows downward from a fixed top** so a KR
  message appearing cannot shift the speed number under the driver's eyes.
  `[UI_CALLBACKS]` was verified by example (CSP's own Mumble app) rather than by
  the SDK reference, and is now **confirmed in game by the 2026-10-15 dry run**.
  **The fallback `cue` window is DELETED** (manifest section and `windowCue`
  both) — two draw paths for one stimulus is one too many, and with both live a
  participant sees the readout twice. The panel's `HUD overlay:` line stays as a
  regression check.
- **THE READOUT IS A COLOUR-CODED BOX AROUND THE LIVE SPEED, IN THE UPPER HALF**
  (2026-10-15, both from the dry run). Two faults, both only visible on track:
  - *The target held the big size and took the attention the live number should
    have.* The driver needs to read what they are **doing**; the target is
    reference they glance at, and the box's fill colour already carries the
    comparison. So `size_speed` is now the largest element, the box is filled
    and outlined in the in-band colour with the **current** speed centred in it,
    and the target is a small caption just outside the box's bottom edge.
  - *Centre-bottom put it in the stock HUD's strip* — speedometer, gear and
    pedal bars all live there, so the one element a participant is meant to
    stare at was competing with native instruments. `top_y` is now `0.17 ×
    height`, and a test asserts the whole block stays inside the upper half.
  **`box_w` is FIXED, not measured from the text:** a box sized to its contents
  changes width when the speed crosses 100 km/h, which is a twitch at exactly
  the moment the driver is reading it. Impl plan §7's "centre-bottom" is
  superseded.
- **The box is gated by `show_actual`, so `minimal` is unchanged by the
  redesign.** The box *is* the live-speed display and its fill is the verdict, so
  drawing it at reduced salience would hand back the comparison `minimal` exists
  to withdraw. At `minimal` the readout is still **the target number alone**.
  That matters because `salience.reduced_form` is frozen config and a post-session
  interview topic — the redesign changed the cue's *form*, not what it tells the
  learner at each stage.
- **The overlay never writes an error on the participant's screen.** The panel's
  pattern (surface a `pcall` failure as on-window text) is right for the
  experimenter's surface and wrong for this one; it goes to the panel instead,
  and the font stack is popped on the error path.
- **The corner-speed readout appears 1.5 s before its window and lingers 2.0 s,
  in seconds of travel.** It was 300 m / 80 m flat, which against the real
  National annotation put it on screen **76% of every lap** — furniture, not a
  cue, and withdrawing furniture at `reduced` changes the whole screen. Now
  ~36%, of which 18% is the zones themselves. **The lookahead is deliberately not
  zero**: inside the zone the car is already at its minimum, so an in-corner-only
  readout could report but not guide, and `lib/kr` does reporting properly.
- **A window's draw function stops being called when the window is closed**, so
  per-frame state (the HUD's running minimum, the KR hold timer) lives in
  `draw3d`, which always runs.
- **The `draw cues` review toggle suppresses drawing only.** The controller, the
  evaluator and the HUD's running minimum keep going underneath — the same
  distinction the probe rests on.
- **The review stage override is cleared by `start_block`**, like the abort arm:
  a block that started with an element pinned by hand would render something the
  controller never asked for while logging as though it had.
- **Anything flat built from logged car positions needs vertical lift**
  (`MARKER_DISC_LIFT_M`). `car.position` sits at the model origin, which on the
  M235i is coplanar with the tarmac and on the TT Cup is not. **A claim verified
  on one car is not a constant.**
- **AND A VERTICAL DATUM VERIFIED FOR ONE PRIMITIVE IS NOT VERIFIED FOR
  ANOTHER** (2026-10-15 dry run). The braking trapezoid **floated above the
  track** because `band_quad_for` shifted the shape onto the marker in X and Z
  and left Y alone: the sampled points come from
  `ac.trackProgressToWorldCoordinate`, which carries the AI **fast_lane's**
  vertical datum, while the marker sits at the recorded reference **car
  position**. So the disc and the trapezoid — two halves of one cue — drew at
  two different heights, and only the disc had ever been checked on track. Fixed
  by offsetting Y by the mid-point delta, which keeps the per-vertex spline
  heights *relative* to the marker so the quad still follows elevation and
  camber. `markers.band_quad` was correct throughout and passes Y straight
  through; the fault was in what the caller handed it, and the caller needs
  `ac.*`, so **no headless test could have caught it.**
- **A THROWAWAY WITH A RENDER CALLBACK MUST BE DELETED, NOT LEFT UNOPENED**
  (2026-10-15 dry run, and it was apparatus contamination). The stray "BRAKE"
  cue just past the start line was `lua/projspike_lua/` **still rendering** — it
  freezes an anchor 25 m ahead of the car on its first 3D frame and draws a
  disc, cross, stalk and the text `BRAKE` there. `[CORE] LAZY = 0` plus
  `[RENDER_CALLBACKS] TRANSPARENT = draw3d` means CSP calls `draw3d` every frame
  once the app is enabled, **whether or not its window is open** — the exact
  inverse of the window-function rule above, and why it went unnoticed for four
  months. A participant would have seen a cue the controller never asked for,
  possibly in a `static` or `off` block, with nothing about it in any log. Its
  `manifest.ini` and `.lua` are deleted (git `5464f14`; the README stays as the
  record). **`lua/trace_rt/manifest.ini` is now the only manifest in the repo
  with a render callback — checked, not assumed. Before a participant drives,
  audit every `TRANSPARENT` callback on the machine and confirm on track:
  deleting a manifest stops CSP finding the app, but an install that already
  enabled it keeps the entry in its own config.**

### Bandwidth knowledge of results (`lib/kr.lua`)

The full rationale and the eight numbered rules are at the top of `lib/kr.lua`,
which is authoritative the way `controller.lua` is. Why it exists: TRACE's three
elements are all **prescriptive, concurrent guidance**, and the tolerance bands
were modelled on **bandwidth KR** (Sherwood 1988; Lee & Carnahan 1990) — a
paradigm whose whole mechanism is quantitative error outside the band and silence
inside it. TRACE had the band and never fired the signal.

- **KR is NOT a fourth UI element** — it is an **apparatus property**: identical
  in every condition mode, never on the fading ladder, invisible to the
  controller and the evaluator. This is also why the three-element scope rule does
  not delete it. (v9 runs adaptive only, so the old adaptive-vs-static
  manipulation is gone; the code keeps both modes.)
- **KR is withdrawn with the scaffold, never with the measurement.** Suppressed
  exactly when the element is hidden (`probe`, `removed`, the whole `off`
  condition), because a no-feedback test with feedback running measures
  performance-WITH-feedback (Winstein & Schmidt 1990).
  - The probe is an **immediate** no-feedback test, not a delayed retention
    test (see R9 under Thesis framing v9). Implemented as **one rule,
  not a second condition check**: `lib/kr` is handed the per-element salience
  level `lib/markers` already computed, so KR visibility is derived from cue
  visibility and cannot drift from it. Suppression is decided **after** the
  controller step, on the stage in force at delivery.
- **KR does not fade.** At `reduced` the cue drops parts of itself; the message is
  byte-identical.
- **CONFOUND, stated rather than engineered away:** a probe withdraws the cue
  **and** its KR, so a probe failure measures dependency on *guidance* (cue plus
  KR), never on the cue alone. **That is why v9's RQ2 says "guidance
  dependency".** Keeping KR through probes would make the probe a transfer test
  instead of a no-feedback test. (Under v6's design the same fact was a
  between-arms confound: an adaptive participant got less total feedback than a
  static one.) Pinned by
  `test_a_faded_element_loses_its_kr_and_a_static_one_does_not`. **State it in
  the methods chapter.**
- **Bandwidth delivery, and the silence is logged.** A message fires only outside
  the band — the same band the criterion used, resolved once by `lib/evaluator`.
  Every pass records a per-element outcome: `delivered` / `inside_band` /
  `withdrawn` / `not_measured` / `clamped` / `capped` / `off`. Five are silences
  and the §0A diagnostic turns entirely on telling them apart.
- **KR mirrors the criterion's SHAPE, not just its band.** Under a one-sided gate
  a fast pass gets the same silence as an on-target one, and
  `CARRIED n km/h fast` is unreachable. Otherwise the apparatus would tell a
  participant they were wrong about a pass it just recorded as right.
- **One message per pass, in the corner's causal order.** `kr.elements` is an
  ordered priority list (braking → corner speed → apex) because the brake point
  sets the entry speed which sets the line; `kr.max_messages` caps delivery at 1,
  because per-component KR on a multi-part task can overload the learner. The
  element that gets the channel is whichever one the learner is currently worst
  at, which is the behaviour the order was designed for.
- **EVERY MESSAGE OPENS WITH A PAST-TENSE VERB** — `BRAKED 6 m early`,
  `CARRIED 9 km/h slow`, `RAN 0.9 m off line`. The text was a bare magnitude
  under an imperative label (`6 m early` / `BRAKE 2`) and the first person to see
  it at speed read it as *"brake 6 m earlier"*, the exact inverse. **A
  bandwidth-KR manipulation whose sign a participant may invert measures
  nothing.** All three elements, because mixed tense inside one channel would be
  worse. Pinned per element by a test. *A cue's wording is part of the
  instrument, and it cannot be reviewed headlessly.*
- **A null metric produces no message** (rule 7), and **a clamped one produces
  none either** (rule 8). A brake initiation clamped to its zone's opening is a
  **floor, not a measurement** — "at least 83 m early" — so the magnitude is
  logged and nothing is said. Detected from the brake trace rather than a
  distance threshold, so it needs no second constant. The **criterion is
  deliberately unchanged**: the driver really did brake at least that early, and
  turning the pass into a null would withhold real evidence from the controller.
  The flag governs what may be **said** and what may be **averaged**. A clamped
  element passes the channel on, exactly as a null does; **withdrawal still beats
  a clamp**.
- **The braking CONSISTENCY gate is deliberately not reported.** "You were 3 m
  from your own rolling mean" is a statement about the learner's recent passes,
  not knowledge of results about this corner.
- **Apex KR is unsigned** (an RMS has no direction) and reports the excess over
  the reference's own `mean_rms_m`, which is what the criterion gates on.
- **The corner-speed HUD already delivered something KR-like and still does** —
  the `settled` phase lingers past a zone showing the achieved minimum, coloured
  by band membership. Not bandwidth-gated, and for one element only, so **the
  asymmetry across elements is a confound to state**.
- **`kr` is the one pass-record field that differs between conditions**, because
  the conditions differ in exactly what the participant was told. The "static and
  adaptive log identically" test compares with `kr` stripped and asserts the
  difference separately.
- **`hold_s` (3.0 s) and the one-message cap are in-game unverified.**
  Legibility at speed and whether a message overlaps the next corner's approach
  are review items.

### What the in-game KR blocks established (2026-10-14)

Three blocks, pair 1, National. Full record in `MILESTONE_LOG.md`.

- **The §0A diagnostic answered, and it answered the good way.** Braking bias
  collapsed within three laps of the driver being told the error: CE **+10.56 m**
  over laps 0–2 → **+2.37 m** over laps 3–6, in-band 1/11 → 13/16, and the next
  block ran a median error of **0.6 m** with 19 of 26 passes in band. The no-KR
  baseline on the same car and track was **CE +15.06 m**. So the 85% reference
  change is now justified non-circularly on the braking element, and **every
  per-pass rate measured before KR describes a system with no error signal.**
  *Caveats: n=1, the driver knows the hypothesis, 6-lap dev blocks, and VE did
  not improve.* Re-run it as the real item-0 diagnostic before writing it up.
- **A ~1.4 m systematic bias toward "early", from a sampling asymmetry.**
  `reference.brake_initiation` returns the first **20 Hz logged row** at or above
  the threshold, so the reference lands up to a full tick late, while the
  participant is sampled **per frame**. Measured on the 85% recording: mean
  +1.13 / +1.61 / +1.41 / +0.80 m by corner, max 2.64 m — **16–32% of a 5 m band,
  one-directional**. The parity test cannot see it because it hands the *same row
  list* to both detectors. **Fix by interpolating the crossing in the
  extractor**; it forces a re-extraction, so it rides with item 5. *Two
  implementations agreeing on a rule is not the same as two measurements being
  comparable.*
- **The trapezoid and the measurement are correctly aligned** — the first
  suspicion, and it was wrong. Longitudinal agreement −0.25 / +0.94 / +0.22 /
  +0.04 m on corners 1–4.
- **The corner-speed gate was faulting the driver for being FASTER** — 15 of 24
  measured failures. That is what made it one-sided; the evidence is in
  `schemas/controller_config.schema.json` under `criteria.corner_speed_gate`.
- **A one-sided speed gate most helps the ERRATIC learner** (simulated: any fade
  52% → 88.5%): a noisy learner oscillates about the target and only the slow
  half of that oscillation now fails.

### Logging, blocks and data hygiene

- **Three manifest markers, all `const: true` and present only when true**, so no
  reader needs a third `false` state: `dev_block`, `aborted`, `dry_run`. Any of
  them excludes a block from participant data.
- **A dry-run block is a FULL study block** (both gates pass, the controller
  runs), so without the flag the only thing separating the rehearsal dataset from
  participant data would be a participant-id convention — and the M2 lesson is
  that a convention is not a constraint. **It owes every questionnaire**; a dev
  or aborted block owes none.
- **An abort discards the BLOCK, never the record of what happened.** It runs the
  entire normal stop path — streams closed and flushed, open passes closed
  `incomplete`, mid-probe elements censored — and only then stamps the manifest.
  **Two clicks, never one**, because a block cannot be re-run on the same person;
  arming reveals the reason list, so an abort can never be recorded without one.
  `abort_reason` is a closed enum chosen as a radio group, with the Lua list and
  the schema enum asserted equal. **An abort excuses emptiness, never
  corruption:** schema validity and stream well-formedness still apply, or an
  abort would be a way to launder a broken log past the integrity check. Aborted
  blocks stay in the apparatus-drift check — they really did run on the
  apparatus.
- **`probe_remaining` is deliberately NOT in `snapshot`.** The golden traces pin
  the snapshot field for field, so adding a panel-only reader would churn the G1
  parity corpus to display a number. A test asserts it stays out.
- **`partial_lap` is a fifth lap-validity reason** beyond the eval plan's four:
  the final lap's tick span is cut off at the stop, so its lap time measures when
  the experimenter pressed the button. **State it in the methods chapter.**
- **Lap-level wall contact is only partly detectable, structurally.** The tick log
  has no collision column, so a wall contact on a straight is invisible to
  `lap_validity`. At Silverstone the barriers sit beyond run-off so it almost
  always trips `wheels_outside` first — "almost always" is a **limitation to
  state**. A test pins it so it surfaces if the tick schema ever gains the column.
- **Hiding the experimenter panel during a block is safe** — verified, not
  assumed: sampling runs from `script.update` and markers from `draw3d`, neither
  of which is a window function. The protocol is: start with the panel open, hide
  it, drive, show it again to stop.

### Analysis

- **The RQ2 analysis is deliberately NOT built yet, and it is no longer the
  Bayesian condition model.** v9 replaced the adaptive-vs-static contrast with
  the **probe-failure excess**: observed probe-failure rate vs the null's,
  per element, with a participant cluster bootstrap, the null's model check,
  and the pre-registered per-element predictions (see **Thesis framing v9**).
  The rule that survives from eval plan Phase 4: **the analysis, the noise-model
  form (F5/F6), the censoring rule for blocks ending mid-probe, and the
  per-element predictions are written and frozen before any pilot data is
  analysed.** Freezing them now would fix a specification whose only test was
  simulated data. Ingestion still emits the lap-level table and a test asserts
  it.
- **A disabled element is not a never-fade.** Zero applicable corners means
  pinned-and-never-evaluated, so the fade descriptives (v9 RQ3, live behaviour)
  and RQ2's probe denominators exclude it rather than counting it among the
  elements that failed to fade. Counting it would inflate the most-quoted
  number.
- **CE/VE vocabulary is adopted for REPORTING, and the criterion is NOT changed.**
  `trace_kit.analysis kr` reports constant error (bias), variable error (scatter)
  and absolute error per corner, which is what makes the two failure modes
  separately visible. The review's proposal to *gate* on windowed CE/VE is
  **rejected**: framing v6 withdrew window-level gating in favour of a per-pass
  boolean, and an SD from 3–4 passes is noise. Its learner-σ band is also not
  adopted — one weak precedent, and it would need session-1 state carried across
  blocks against the block-scoped rule.
- **Clamped brake initiations are excluded from every CE/VE average** and counted
  in `clamped_excluded`; the raw `series` keeps the recorded value as the audit
  trail. Averaging a floor turns a braking zone's geometry into an apparent
  change in bias, in the one report whose job is to say whether bias moved.
- **The exclusion rules live in `load_dataset`, applied once, centrally.**

### The adopted calibration — `frozen-g1b` (2026-10-15)

Full justification and the alternatives it beat: `SESSION_BUDGET_BRIEF.md` § K
and `configs/simulation/G1_REVIEW.md`. Read the hash from `G1_REVIEW.md`.

- **Band floors are 12 m / 9 km/h / 1.5 m**, qualification is **2-of-3**,
  `probe.laps` is **2**, and a training block is **15 laps**. The previous
  5/4/0.5 at 3-of-4 is superseded, and so is every per-pass rate quoted against
  it elsewhere in this file.
- **The floors, not the window, were why nothing faded.** At 5/4/0.5 the
  braking and apex elements never advanced in ANY real recorded block, at either
  window, and `share_traversing_2_of_3` was 0.000 at every window and lap count.
  Widening the floors is what makes the criterion reachable; the window only
  decides whether the ladder can be *completed* in the budget. Measured by
  replaying real passes through the real evaluator and controller
  (`kit/tools/feasible.py`).
- **15 laps, not 12, and it is a LAP COUNT not a time box.** Target 1 scores
  0.430 at 12 laps and 0.720 at 15, so three laps — about 3.5 min of session
  time — is what moves it from failing to passing. A participant who spins twice
  inside a 17.5-minute box lands at 12–13 laps and fails the gate silently.
- **The apex floor stays at 1.5 m and goes no higher.** At 2.0 m Gate G1 fails
  outright on the committed model. This supersedes "the apex floor stays at
  0.5 m" above.
- **`simulate.MODEL`'s apex parameters are now MEASURED** (2.49 m / 1.86 m from
  `apexscan.py`, 227 real passes) rather than the assumed 1.2 / 0.30. It
  reversed a verdict, not just a number: at a 1.5 m apex floor the assumed
  novice's apex excess is *contained by the band*, giving a 68% non-improver
  fade rate against 5.75% for the measured one.
- **ACCEPTED COST — the alternating-corner pathology INVERTED.** A corner
  meeting its criterion every *other* pass yields ⌈n/2⌉ of n: 2 of 4 **stalled**
  under 3-of-4, and 2 of 3 **QUALIFIES** under 2-of-3. A driver who is right half
  the time at a corner is now counted as competent there. Only
  `required_passes = 3` excludes an alternating pattern and that costs a 9-lap
  traversal floor against 6 — **you cannot have both a 6-lap ladder and
  alternating-rejection**, which is derivable rather than tuned. Accepted
  knowingly; `dequalify_consecutive_failures = 1` was measured as a fix and
  rejected (it does not stop the corner qualifying and takes
  removed-despite-regression from 0.75% to 27%). **Write it up as a limitation
  and state the direction it moved:** "conservative on purpose — premature
  withdrawal is worse than delayed" is weaker at a 3-pass window than at 4.
- **ACCEPTED COST — a 12 m braking band silences KR on the measured bias.** The
  +8.1 m mean bias over 162 human passes is now *inside* the band, so bandwidth
  KR says nothing about it; only the untreated +15.06 m no-KR baseline bias still
  speaks. Widening the floor to make the criterion reachable also withdrew the
  error signal for the most common error. Pinned by
  `test_kr_fires_on_the_committed_reference_at_the_no_kr_baseline_bias`, and a
  limitation to state beside the band itself.
- **The researcher is NOT a representative novice.** Best lap 63.60 s against
  the 85% AI's 62.30 (**+2.1%**), and 8 s clear of the 80% AI. So the floors
  derived from these passes are a **lower bound** — a true novice needs wider,
  not narrower. Re-check after the first pilot participant rather than treating
  12/9/1.5 as settled. (`_blocks.py` calls the driver a novice; the lap times
  disagree, and the direction of the discrepancy is what matters here.)
- **Tests that pin calibration now DERIVE it.** Roughly 27 assertions across
  five files were written against the old floors and window; they are rewritten
  to compute from `controller_config.json` rather than quote numbers, so the
  next G2 recalibration does not churn them. The same applies to
  `golden_traces/generate.py`, where three cases had silently stopped testing
  what their names said — see `golden_traces/README.md`.

### Protocol and session budget

The question and its answer are `SESSION_BUDGET_BRIEF.md` (2026-10-15); the
measured tables are `kit/tools/README.md` § `lapbudget.py`. What binds:

- **The whole study is ONE ~33-minute sitting per participant** — not 3 h 15
  across three sessions. **Shape B adopted, at 15 laps (2026-10-15):** pair 1
  only, a **15-lap training block**, a **4-lap unassisted block** (3 valid), and
  NASA-TLX in the room. **Everything else is outside the timed sitting and that
  is settled**: the ethics process, consent, the information sheet and the
  pre-study questionnaire beforehand; the confidence questionnaire and the
  interview as a remote call afterwards. So **~32.9 min is RIG TIME, not
  participant burden** — the real commitment is ~55–60 min, and both figures
  belong in the methods chapter.
- **15 laps, not 12, and the 3 extra minutes were the cheap option.** G1's
  first target scores **0.72 at 15 laps and 0.43 at 12**. Buying the same
  traversal rate by widening floors instead (15/11/1.5) takes the false-pass
  rate 5.8% → 8.0% and removal-despite-regression 0.75% → 13.8%. The sitting
  runs ~33 min; that is the decision, not a tension.
- **SUPERSEDED by v9 (2026-10-30): there is ONE condition, TRACE adaptive.**
  The between-subjects adaptive vs static design of 2026-10-15 (~7–8 per arm,
  "RQ2 keeps its form, not its substance") is gone along with v6's RQ2. All
  ~15 participants drive the adaptive condition, and every probe is an
  observation for RQ2. The **4-lap unassisted block stays**: it is the cue-off
  data every participant yields, whether or not they reach a probe, so the null
  is calibrated on it and it is RQ2's zero-probe fallback contrast.
- **The eval plan's lap budget rested on a "~2-minute circuit" and both layouts
  run 70–80 s.** Measured wall clock over every real block: national 62–76 s,
  international 71–98 s. A 15-lap block is ~17.5 min of driving, not 30 — the
  195 min booked was padded against a lap time nearly 2× too slow. Correct the
  premise wherever it appears, including `simulate.BLOCK_LAPS`'s comment.
- **The block must end on a LAP COUNT, never a time box.** At 70 s/lap a
  participant who spins twice inside a 17.5-minute box lands at 12–13 laps,
  where target 1 fails (0.43 at 12), and nothing about the block would look
  wrong. The panel must refuse to stop before 15 laps and record the reason if
  it is stopped anyway. For reference: at ≤ 10 laps nothing traverses at any
  window setting, and 12 laps works only with `2-of-3` (0.003 at 3-of-4).
- **Shortening the probe is not a lever.** `traversal_floor = 2 ×
  required_passes + max(probe.laps, required_passes)`, and `_quorum_ready` is
  keyed on `required_passes` and gates `probe_to_removed` too — so at 3-of-4,
  `probe.laps` 3 → 2 → 1 leaves the floor at **9 laps, unchanged**. It is worth
  exactly one lap, and only once `required_passes` has come down.
- **The MDC analysis RAN (2026-10-15, `kit/tools/mdc.py`) and it returned
  "neither".** It was promoted to the protocol's blocker and then undercut the
  **frozen** window too: at a 4-pass window only **1 of 4** corners can resolve
  the available braking improvement (8.19 m — corners 3 and 4 need n ≥ 6, corner
  1 needs n ≥ 19) and 1 of 4 the apex one (2.20 m), while the quorum needs 3 of
  4. **So 3-of-4 was never licensed at its own value, and 2-of-3 does not cross
  a line it stayed behind** — MDC₉₅ grows by only √(4/3) = 15% between them. The
  window is therefore a **stated limitation of the design, not a discriminator
  between protocol shapes**, and the config edit is no longer blocked on item
  8a. What licenses it is **item 8b** (contrasting-groups ROC, cut at a stated
  false-pass rate) — §E's own ordering — plus the missing anchor below. MDC₉₅ is
  the strict reading and the design does not claim it: these gates are *a
  heuristic trigger for running a probe, not a measurement of learning*. A
  window **median** is ~1.25× worse than a mean, so every `needs n` is
  optimistic for the statistic actually used.
- **"Neither" was a statement about 95%, not about the data.** At **80%**
  confidence braking clears a 3-of-4 corner quorum at a **3-pass** window
  (quorum 3/4 at both n=3 and n=4) and apex clears it at n=4. The same sigmas
  license opposite answers and nothing in the data picks the z — so the right
  conclusion is **MDC alone cannot decide the window**, and item 8b decides it
  by stating a false-pass rate instead of letting a conventional z imply one.
  That is also the design's own currency: *premature withdrawal is worse than
  delayed* is a claim about false passes.
- **No method decides proficiency from 3–4 observations** (checked 2026-10-15).
  The sequential family — SPRT, LC-CUSUM, already considered-and-rejected in
  `BAND_CALIBRATION_BRIEF.md` §E on engineering cost rather than validity — puts
  published competence decisions at **13–56** procedures. **Generalizability
  theory** (G-study → D-study on Φ) is the one framework the project lacks and
  the best fit for its crossed corner × lap design, but Φ needs **several
  drivers**, so it is G2 pilot work. **The structural point beats both:** a
  12-lap block yields **4 × 12 = 48 corner passes per element**, inside that
  13–56 range — the architecture just never looks at more than `window_passes`
  of them per corner before voting across corners. **The sample is adequate; the
  per-corner-then-quorum structure is what spends it.** That is a different
  argument for the sequential family than the one §E rejected, and acting on it
  would be a controller rewrite.
- **NEW CRITICAL PATH: nothing measures the improvement available on CORNER
  SPEED**, which is the one element that traverses (`windowscan.py`: 83%
  removal) and therefore the element Gate G1 rests on. The 85% re-reference
  removed the *bias* (+0.31 km/h); that is a different quantity. Until that
  anchor exists, **neither item 8a nor 8b can speak to the element the system's
  feasibility depends on.** Measurable from data already recorded — an
  early-vs-plateau split over the seven `_blocks.py` blocks plus the three
  2026-10-14 KR blocks.
- **`2-of-3` is NOT adopted and the frozen config is untouched.** The lapbudget
  tables *point at* it and cannot license it: `non_improver.share_with_any_fade`
  is **0.000 at every window length**, because that model learner sits far
  outside the band by construction, so no simulated learner type can price the
  real cost — discriminability near the band edge. A shorter window also worsens
  the repeated-looks inflation of correction item 8.
- **ICC(1,1) is 0.454 braking / 0.116 corner speed / 0.099 apex**, so almost all
  variance in the latter two is lap-to-lap noise rather than stable corner-level
  state — the σ/band argument arriving from measurement theory. **The quorum
  survives the analysis even though the window does not:** between-corner
  residual correlation is median **−0.12 / +0.27 / −0.07**, so requiring 3 of 4
  corners really is four looks at the driver rather than one wearing four hats.
- **Prefer pair 1, and pair 2 is DESCOPED rather than deferred.** Per-pair
  corner-speed removal at 15 laps is pair 1 **88%** vs pair 2 **78%**, a quorum
  granularity effect: 4 corners makes `advance_threshold = 0.75` an exact 3-of-4
  while 5 corners rounds up to 4-of-5 = 0.80. Pair 1 is also the only pair whose
  reference table is settled. So pair 2's 100%-table inconsistency stops gating
  the first participant (M6 item 5) — but the thesis then rests on **one car and
  one layout**, which narrows the generalisation claim. Say the second apparatus
  was descoped; do not leave it half-finished and unmentioned.
- **Probe-and-revert will appear in much less of the data.** At 2-of-3 probe 2,
  `n_staggered_reversions` falls **799 → 227** — the element is often already
  removed before a staggered onset arrives. G1's safety clause still holds
  (`share_removed_despite_regression` = 0.000 in every configuration measured),
  but the mechanism the thesis is *about* is observed less often, and a 2-lap
  probe is 8 unassisted corner passes per element. Both are limitations on the
  construct, not on the schedule.

### Open work

**M5 — the on-track visual review.** *[2026-10-15: the dry run covered items
1–3 on pair 1 and found two rendering faults, both now fixed — the braking
trapezoid floated above the track (wrong vertical datum) and a stray "BRAKE" cue
near the start line was the projection spike still rendering. See the Rendering
notes above and `MILESTONE_LOG.md`. **Re-check both on track before item 4**,
because a fix verified only headlessly is exactly what produced the first fault.
Pair 2 is descoped, so "both tracks" below now means pair 1 only.]*

(originally: both tracks, using the panel's salience
override to script the stages). Deferred on 2026-10-09 to let M6 start; **hard
deadline: before the first pilot participant drives.** A participant must not be
the first person to see these visuals, and a `reduced` form that renders wrong
would invalidate the post-session interview data that asks about it.
1. Each element at `full`, `reduced`, `probe` — the marker really is disc-only at
   reduced and really is gone at probe, and the three elements can differ from
   each other on screen at once.
2. The corner-speed readout: legible at speed, positioned in the **upper half**
   (centre-bottom superseded 2026-10-15), and its
   three phases (approach / in_zone / settled) read correctly through a corner.
3. A `static` block and an `off` block: constant-full and nothing-at-all.
4. An adaptive block driven far enough for **the controller itself to move a
   stage**. The controller demonstrably runs in game; what is still unseen is a
   *stage transition on screen*. At `frozen-g1` floors this may be unreachable by
   the researcher's own driving, so it needs a deliberately loosened dev config
   (then restore — `test_m4_simulate.py` fails until the hash matches again,
   which is the guardrail working) or a post-G2 re-run.

**M6 — still to do:**
0. **Run the real §0A diagnostic blocks.** Dev blocks on pair 1 with KR visible,
   then `python -m trace_kit.analysis kr "<trace_data>" --include dev`, against
   the committed no-KR baseline (block `m5_tst_...20260909_003201`, 28 braking
   passes, **CE +15.06 m, VE 4.68 m**). *Compare like with like — re-score with
   `kit/tools/rescore.py` rather than against the new table by eye.* The 2026-10-14
   blocks are a strong preliminary answer (see above) but are 6-lap dev blocks
   driven by the person who built the system. **This must precede the band-floor
   work in item 5.**
1. **The protocol dry run on yourself** — now **one ~30-min sitting**, not three
   sessions (revised 2026-10-15; the protocol is `evaluation_plan_v2.md` Phase 3
   and `SESSION_BUDGET_BRIEF.md` Shape B). Pair 1 only: 1 familiarisation lap,
   a **15-lap** training block, a 4-lap unassisted block, NASA-TLX, with the
   `dry run` toggle on and the questionnaires filled in as JSON. Then the
   integrity checker, then `trace_kit.analysis rq1 --include dry_run` must ingest
   the result with no manual fixes — that is the exit test. **15 laps**, matching
   the protocol and the frozen config; time the phases with a stopwatch, because
   every non-driving figure in the ~32.9-min budget is an estimate and the dry
   run is the only thing that measures them.
2. M5 visual review items 1–3 ride along with the dry run. At the `frozen-g1b`
   floors a stage transition is now reachable by real driving (item 4's
   deliberately-loosened dev config may no longer be needed — check before
   building one).
3. **Consent form + participant information sheet** — not draftable from this
   repo; the wording comes from the ethics committee. **The two protocol
   questions that rode with it are SETTLED (2026-10-15): the ethics process,
   consent and the pre-study questionnaire all happen OUTSIDE the timed
   sitting**, as does the post-session interview. So the ~32.9 min is *rig time*; total
   participant commitment is ~55–60 min and both figures should be reported.
4. **Data hygiene:** the pre-M2 recordings (participants `0`, `1`, `Test1`) are
   not flagged `dev_block`, so every checker reads them as study blocks. **Add
   `shortHUDtest` and `test14-10` (2026-10-14), both recorded with the `dev
   block` toggle OFF** — `KRtest` the same morning was stamped correctly, so the
   toggle is being missed rather than broken, and it has to be set after every
   app reload. Stamp them or move them out of the live directory before the dry
   run, so a FAIL in that report means something again.
5. **Close out the reference change — PAIR 1 ONLY** (narrowed 2026-10-15 by the
   Shape B protocol decision; see **Protocol and session budget** above). Pair 2
   is **descoped, not deferred**: one pair is driven per participant, so its
   100% table no longer gates the first participant and "replicate to pair 2 in
   one pass" is cancelled. Say in the thesis that the second apparatus was
   descoped and that the study rests on one car and one layout. Remaining, all
   pair 1: re-record at the settled strength with **fuel for 12+ laps** (8 clean
   laps is below the protocol, so **Gate G0 is re-opened**), **interpolate the
   brake crossing in the extractor** (the ~1.4 m sampling asymmetry), **narrow
   corner 2's apex window**, re-extract, re-review G0, set the band floors from
   the residuals, re-freeze the config and **re-run the Phase 1 simulation at
   `BLOCK_LAPS = 15` (the adopted lap count; `simulate.BLOCK_LAPS` already
  holds it) and re-review G1**. International's braking zones are no
   longer re-derived.
6. **See the trapezoid on track.** Headless-tested as geometry only; that CSP
   projects the quad onto the tarmac, that it reads at speed, and that it does
   not spill off a narrow part of the circuit are in-game checks. Judge the shape
   again after the G2 floors.
7. **The participant HUD overlay — CONFIRMED and the fallback deleted**
   (2026-10-15 dry run). `[UI_CALLBACKS] IN_GAME` *is* honoured for a user app;
   the `cue` window and `windowCue` are gone. The dry run also produced the
   redesign recorded under **Rendering and cues** above: a colour-coded box
   around the live speed, target as a caption below it, moved to the upper half
   away from AC's own bottom-strip instruments.
   **Still unverified in game, and it needs one more block:**
   - the redesign itself — is the box legible at speed, is the live number
     readable against a moving background, does the fill colour read as a
     verdict rather than as decoration, and is `box_w` wide enough for three
     digits at the real font (the test bounds it by arithmetic, not by DWrite);
   - `top_y = 0.17 × height` against AC's own top-centre widgets and the line of
     sight — it was moved off the bottom strip, so confirm it has not landed
     under something else;
   - whether `hold_s = 3.0` holds a KR message into the next corner's approach,
     and whether the readout and a message coexist without either moving.
8. **Ground the band calibration in the literature** — *opened and answered
   2026-10-14; the remaining work is the two analyses below.* The question was
   whether the EVM, the floors, the 0.5 consistency ratio and the 3-of-4 window
   have a published basis. **They do not: there is no principled, published rule
   for setting a bandwidth width for novices.** Widths in the paradigm are
   conventionally a percentage of the movement *goal*, inherited rather than
   derived (two full-text sources say so), and width-as-IV studies contradict
   each other. The full record — what came back, what came back **empty**, where
   the review was wrong, and what was measured in response — is the final section
   of `BAND_CALIBRATION_BRIEF.md`; the reply itself is
   `TRACE_tolerance-calibration_lit-review_v1.0.md`. **Adopted:** floors become
   contrasting-groups cut-scores (Jørgensen et al. 2018), window length comes
   from MDC (Weir 2005), the EVM is reported as inoperative, and the sequential
   alternatives (EWMA, LC-CUSUM, SPRT) are recorded as **considered and
   rejected** — they would rewrite both controllers and churn the golden-trace
   corpus to be validated by the same simulation whose learner model is the thing
   in question. **Still to run, both on data already recorded, both G2:**
   (a) σ_within on *detrended* residuals, ICC, and MDC₉₅(n) for n = 1…10 per
   metric, plus the between-corner residual correlation that decides whether the
   quorum adds protection — this is what replaces the 3-of-4 justification.
   **RUN 2026-10-15 (`kit/tools/mdc.py`) — it licenses NEITHER 2-of-3 nor the
   frozen 3-of-4**, so the window is a stated limitation rather than a
   discriminator, and (b) plus the missing corner-speed anchor are what remain.
   See **Protocol and session budget** above and `kit/tools/README.md` § `mdc.py`;
   (b) contrasting-groups ROC/AUC of the **window** statistic, early laps vs
   plateau laps, with the cut at a stated false-pass rate and the false-fail rate
   reported. Use a window **median**, not a mean: the apex distribution is
   right-skewed (mean 2.49 m vs median 1.52 m).

### Repo layout note

`novelty_audit/` holds the v6 → v9 transition record. **Start at its
`README.md`**; `CLAIMS_SHEET_v9.md` there is binding. Its `papers_txt/` and the
top-level `Academic Papers/` are copyrighted full texts and are **git-ignored on
purpose**. `.gitignore` is an allowlist, so name any new top-level file there or
git never sees it: that is how the whole v9 audit sat unversioned until
2026-10-30. The llm-council skill (`.claude/skills/`) is untracked because its
source has no licence; copy it in by hand on a fresh clone.

`kit/` at repo root is the **offline Python toolkit** (`trace-kit`): modern
Python, conda env `ac_dev`, *not* subject to the Python-3.3 constraints below —
those apply only to in-game apps under `python/`. `kit/` must never be moved
under `python/`, because AC scans `apps/python/` for loadable in-game apps.
Shared data contracts live in `schemas/` (JSON Schema) with example fixtures in
`configs/`; the in-game runtime is `lua/trace_rt/`. `golden_traces/` at repo root
is the **controller parity corpus** — the only state the runtime and the
simulator share besides `controller_config.json` (impl plan §3), and the thing
that keeps Gate G1 honest. Read `golden_traces/README.md` before touching either
controller. `kit/tools/` is **not** part of `trace_kit`: it holds the one-off
analysis scripts that produced numbers now asserted in prose here and in
`G0_REVIEW.md`, kept only so those numbers can be recomputed — see
`kit/tools/README.md`, which records each figure they reproduce.

## Two runtimes, two sets of hard constraints

This project spans two embedded interpreters. Code for one must never be written
in the idiom of the other or of modern desktop development.

### 1. In-game Python — **Python 3.3** (`python/`)
Assetto Corsa boots its own bundled **Python 3.3** and injects `ac` / `acsys`.
There is no pip/conda at runtime.
- **No f-strings.** Use `"...{}".format(x)` or `%`.
- **No type hints**, no `pathlib`-isms, no modern-stdlib-only features.
- `ac` and `acsys` exist only in-game. Locally they are faked by `dev_stubs/`
  for autocomplete/linting — **never ship `dev_stubs/` on `sys.path` in-game**,
  it would shadow the real modules.
- App folder ids can't contain spaces (AC imports by folder name). The display
  name is set via `ac.newApp` / `ac.setTitle`.
- **Split logic from the AC boundary.** Pure, `ac`-free logic goes in a `*_core`
  module that runs and is unit-tested locally; the entry module
  (`acMain`/`acUpdate`/`acShutdown`) only wires `ac` to that core. See
  `python/GRApp/` for the pattern (`GRApp.py` + `GRApp_core.py` + `tests/`).

### 2. Rendering — **CSP Lua** (`lua/`)
World-anchored markers are drawn with the **Custom Shaders Patch (CSP) Lua
`render` API**, which draws primitives directly in 3D world space — the engine
projects them with the real scene camera in the transparent pass, so markers are
frame-perfect at speed and depth-tested (occluded by geometry) for free.
- This was the project's highest technical risk; the throwaway spike in
  `lua/projspike_lua/` **passed** and settled the approach. The stock AC Python
  app API has **no** usable world-to-screen transform — do not try to revive it.
- CSP is a **documented required dependency** of the apparatus, held at a fixed
  version across all participants.
- Fading is implemented by modulating a marker's `rgbm` alpha (and, from M5, by
  dropping parts of the cue) as a function of the controller stage. **Keep
  rendering swappable and fading independent of it** — that principle is what
  made the Python→Lua swap cheap. Marker world positions are precomputed once per
  corner from the expert reference; at run time the controller only sets a stage.
- **Everything the renderer decides is pure and happens before any `render.*`
  call**: `markers.presented_stage(mode, stage)` applies the block's condition
  (adaptive → the controller's stage, static → pinned full, off → hidden) and
  `markers.visual(stage, salience)` turns that into an alpha plus which parts
  survive. The draw calls only execute the result, which is why the staging layer
  is headless-testable and why **the condition stays a config field, never a code
  path** (impl plan §5). Do not add a condition check inside a draw function —
  one was there until M5 and it read the *panel's* current selection rather than
  the running block's.
- **The reduced-salience form is `minimal`** (`salience.reduced_form`): markers
  draw the disc alone, the corner-speed readout keeps the target number alone.
  Reducing salience should reduce what the cue *tells* the learner, not just how
  bright it is. `intermediate` and `dimmed` are the alternatives; `dimmed` is the
  control case for that argument. It is a post-session interview topic, so it is config —
  frozen and hashed — rather than a literal.
- **A window's draw function stops being called when the window is closed.** Any
  state that must advance per frame (the corner-speed HUD's running minimum)
  belongs in the `draw3d` render callback, not in a window function.
- Only call `render.*` / `ac.*` functions that exist in CSP's shipped Lua SDK
  (`extension/internal/lua-sdk`; `ac_apps/lib.lua` is the context TRACE runs in).
  When unsure, verify against the SDK rather than assuming an API exists.
  `lua/trace_rt/SDK_NOTES.md` caches the verified signatures TRACE already uses
  (plus the runtime quirks) — read it first, then grep the SDK for anything new
  and record it there.
- **CSP-runtime gotcha (confirmed M0): do not store functions as table fields
  and dispatch them via `t.fn(...)`.** A combinator-style validator that kept
  `{ check = <function> }` entries and called `spec.check(...)` passed headless
  (lupa LuaJIT 2.1) but crashed in-game with *"attempt to call field 'check' (a
  number value)"* — CSP returns the stored closure as a number. Write Lua logic
  with helper functions called **directly**, not closures-in-tables. This bites
  the M4 controller (also Lua) too. See `lua/trace_rt/lib/validate.lua`.
- **Defensive in-game UI:** CSP draws app windows in immediate mode, so an
  uncaught error mid-`windowMain` silently abandons the rest of that frame's
  draw — the window goes half-blank with no message. Wrap fallible work in
  `pcall` and surface the error as on-window text (pattern in `trace_rt.lua`).

## Architecture (three loosely coupled layers)

1. **Telemetry ingestion** — reads AC's shared-memory interface.
2. **Competency assessment + fading controller** — the inspectable core.
3. **UI rendering** — the three CSP Lua overlays.

## Scope — fixed at three UI elements. Resist scope creep.

Only these three (all three exist as of M5):
- **Braking-point marker** (world-anchored) — `render.*` in `draw3d`.
- **Corner-speed indicator** (HUD) — a screen overlay drawn from
  `[UI_CALLBACKS] IN_GAME` (**not** an app window, from 2026-10-14), logic and
  layout in `lib/hud.lua`.
- **Apex marker** (world-anchored) — `render.*` in `draw3d`.

A racing line, gear-shift indicator, and delta-time bar were **considered and
deliberately dropped**. Do not add them back. "A working system on three
elements is better than a half-working system on five."

**Bandwidth KR (`lib/kr.lua`, added 2026-10-10) is not a fourth element and must
not be deleted as scope creep.** The three elements above are the *scaffolds* —
the things that fade, and the thing the two conditions differ in. KR is an
**apparatus property**: terminal error information, delivered identically in both
conditions, never on the fading ladder, and invisible to the controller and the
evaluator. It does not add a cue to learn from; it closes the hole that TRACE's
tolerance bands were *modelled* on bandwidth KR (Sherwood 1988) and never
delivered the KR half of it. The full argument is at the top of `lib/kr.lua` and
in the M6 notes above.

## The fading mechanism

Per element, independently: **full salience → reduced salience → probe
withdrawal**. Transitions move **one stage at a time, in either direction** —
forward on demonstrated competence, backward on regression.
- **Evidence is per corner-pass, not per lap.** Two tiers. **Per corner:** a
  corner *qualifies* for an element when its criterion holds in **2 of the last 3
  passes** (rolling window; `frozen-g1b`, 2026-10-15 — was 3-of-4, and the
  alternating-corner cost of the change is under **The adopted calibration**)
  and *de-qualifies* on **2 consecutive failures**.
  **Per element:** a stage transition fires on a quorum across applicable corners
  — advance at **≥ 75%** qualified, revert below **50%**. Window sizes and
  thresholds are the controller's free parameters, fixed by the Phase 1
  simulation (`controller_config.json`). Do not reintroduce consecutive-lap
  gating — it was abandoned as too brittle for noisy novice driving.
- **Re-qualification on advance (structural rule, not a tuned parameter).** On
  every stage *advance*, all corner qualification states and evidence windows for
  that element reset to unqualified — quorum must be rebuilt from passes driven
  *under the new salience level* before the next advance. Without this the
  machine is degenerate (the quorum that triggered full→reduced still holds, so
  it would advance again immediately). Stage *reversions* do **not** reset
  qualification.
- **Quorum readiness (added at M4 — the machine does not work without it).** An
  element's quorum is **not evaluated at all** until every applicable corner
  holds at least `required_passes` of evidence in its *current* window. The
  re-qualification reset drops the qualified share to zero on every advance,
  which is below the revert threshold, so without this the pass right after an
  advance would revert it. It applies symmetrically to advances and reversions,
  errs conservative, and is what makes the probe's "`probe.laps` laps with
  quorum maintained" a verdict on real evidence rather than an empty one.
- **One regression, one stage (added at M4 — same reason).** After a
  *reversion* the revert check is **disarmed** until the qualified share recovers
  to the revert threshold; after an *advance* it stays armed. Without it a
  reversion left the element one stage down holding the same sub-threshold share
  that caused it, so the next pass reverted it again — a deep collapse cascaded
  two stages in two passes and the reversion cap could never be reached. Leaving
  it armed after an advance is what still lets a *premature* advance be undone,
  which is the point of probe-and-revert.
- **A null criterion is NO EVIDENCE, not a failure (M4).** A pass with no
  measurable metric (no sustained braking found in the zone, an apex window the
  pass did not cover, a pass cut short at block end) does not enter that
  element's window at all and cannot contribute a consecutive failure. Scoring
  nulls as failures would punish a learner for an annotation-zone fit problem.
  Accepted residual risk, stated rather than engineered away: a corner yielding
  only nulls **stalls** its element at full salience instead of fading it. Null
  counts are stamped into every pass record and shown live on the panel.
  *Invalid* passes (off-track, wall contact) are **not** nulls — their metrics
  are real and they feed the controller normally, per eval plan v2.
- **Probe rules:** a probe lasts **2 full laps** (`probe.laps`; 3 until
  `frozen-g1b`) with the element hidden
  (qualification still evaluated throughout — withdrawal removes the scaffold,
  never the measurement); reverts one stage if qualified share drops below 50%;
  **at most 2 reversion cycles per element per block**, after which it stays at
  reduced salience *and is pinned in both directions*; permanence is
  **block-scoped** (every block starts at full salience, no state carries across
  blocks/sessions); a block ending mid-probe is logged as **incomplete /
  right-censored**. Probe completion is counted from the entry *pass*, not the
  next lap boundary, which gives every applicable corner exactly `probe.laps`
  passes driven with the element hidden. **Bandwidth KR for that element is
  suppressed for the whole probe too** (added 2026-10-10): the probe is the
  immediate no-feedback test, and a no-feedback test with feedback still
  running measures performance-with-feedback (Winstein & Schmidt 1990). The *measurement* keeps
  running, as it always did — withdrawal removes the scaffold, never the
  measurement. See `lib/kr.lua` rule 4 and the confound it costs, recorded in the
  M6 notes.
- **Zero applicable corners → the element is DISABLED**: pinned at full salience,
  never evaluated, recorded in the manifest's `disabled_elements` (never in the
  fade log — a fade record with a zero denominator would be a fiction).
- Conservative on purpose: premature withdrawal is worse than delayed.
- Lap-budget feasibility is validated by a synthetic-novice simulation **before**
  any participant is run. ✓ **Done at M4; Gate G1 met** —
  `configs/simulation/G1_REVIEW.md`.
- The acknowledged alternating pass/fail pathology is encoded as a golden trace
  (`golden_traces/alternating_corner.json`): the corner never hits 2
  *consecutive* failures so it never de-qualifies. **Its direction inverted at
  `frozen-g1b`:** alternating yields ⌈n/2⌉ of n, so it stalled at 2 of 4 under
  3-of-4 and now **qualifies** at 2 of 3 — an accepted cost (see **The adopted
  calibration**). Recorded honestly there: at a
  four-corner denominator the other three still carry exactly the 0.75 advance
  threshold, so one permanently-failing corner is inside the design's tolerance.

**The controller is implemented twice** — `lua/trace_rt/lib/controller.lua`
(runtime) and `kit/trace_kit/controller.py` (simulator). They are kept identical
by `golden_traces/`; read its README before touching either. Every rule above is
stated in full at the top of `controller.lua`, which is the authoritative
description.

## Competency metrics (relative to an expert reference, tolerance bands)

All gates produce a **per-pass boolean** — that is the unit the controller's
rolling-window rule (2-of-3 under `frozen-g1b`) consumes; nothing window-level leaves the evaluator.
- **Braking-point marker — two-gate, per pass**: brake-initiation distance within
  a tolerance band of the expert point (**accuracy**) **and** within a named
  *consistency delta* of the rolling mean of that corner's recent passes
  (**consistency**). Consistency alone is insufficient by design (a learner who
  brakes reliably 30 m early is consistent but inaccurate, so the marker stays).
  **Do not reintroduce a windowed-variance consistency gate** — v5's "variance
  below threshold" definition was withdrawn in v6: it is incompatible with a
  per-pass boolean and meaningless at 3–4 samples. The consistency delta is a
  config constant (`criteria.consistency_delta_ratio`, 0.5 × the accuracy band),
  and the rolling mean is over the corner's *prior* passes in the window — the
  pass is never in its own mean. On a corner's first pass the gate is vacuously
  met, so the criterion reduces to accuracy there.
- **Corner-speed indicator**: minimum corner-speed deviation from the expert
  speed envelope, **one-sided on the slow side** (`criteria.corner_speed_gate`,
  `slow_only` from 2026-10-14; `two_sided` kept as the comparison case). A pass
  fails only when the minimum is more than a band BELOW the reference: carrying
  more speed than the expert is not an error, the same argument the apex gate has
  always rested on. The metric is a MINIMUM over the window, so an entry too hot
  to sustain shows up as a *lower* minimum later in that same window — the only
  way to post a high minimum is to have carried the speed through. The full
  argument and the measured evidence are in the schema's own description of
  `criteria.corner_speed_gate`. **Residual risk, stated:** a driver who sustains
  an over-the-limit minimum and ruins the EXIT is caught only by the apex element
  and the pass's track-limits flags. **Consequence for calibration:** with no
  upper edge the reference's STRENGTH is the whole target on this element, so the
  gate shape and the reference strength are one Gate G2 decision, not two.
- **Apex marker**: **RMS lateral deviation from the expert line over a short
  spline window centred on the apex gate** (half-width a per-corner annotation
  constant) — *not* a single-point sample at the gate, which is noisy and
  gameable. One-sided: driving closer to the expert line than the AI managed is
  not an error. **Its floor cannot be widened** — see the roadmap; a 2.0 m floor
  fails Gate G1 outright, and the reason is that novice apex scatter is the size
  of the whole available improvement.

Any gate whose metric could not be measured on a pass yields **null**, which the
controller treats as no evidence (see the fading mechanism above) — never as a
failure.

These gates are a **heuristic trigger for when to run an unassisted probe, not a
measurement of learning** — the probe stage is the actual (immediate)
no-feedback test. Don't
write code or comments claiming the gates "certify internalisation."

**Each band is also what the learner is TOLD about** (`lib/kr.lua`, 2026-10-10):
bandwidth KR fires with the signed error whenever a pass falls outside the band
and is silent inside it, reading the same band out of `lib/evaluator` that the
criterion gated on — so the tolerance the learner hears about and the tolerance
the fading decision applied are the same number by construction, not by two code
paths agreeing. Before that the bands were a threshold the learner never saw,
which is half of bandwidth KR and the half that does not work.

**Vocabulary (adopt in the thesis):** the braking criterion's "accuracy" gate is
a per-pass **absolute error (AE)** — it mixes bias and scatter — and its
"consistency" gate is a **variable error (VE)** proxy. The textbook
**CE / VE / AE** decomposition is reported per corner by
`trace_kit.analysis kr`; it is deliberately **not** what the controller gates on
(a windowed SD cannot be a per-pass boolean, and from 3–4 samples it is noise).

**Expert reference** = AC AI driver at a **strong but sub-maximal strength,
stamped per block** (revised 2026-10-10 from "95–100%"), 12 laps per car-track
pair, fixed setup, logged through this project's own telemetry pipeline (not
internet hotlaps). It yields both the tolerance bands and the per-corner marker
world coordinates. **There are no human reference laps** — that step was dropped
at M3 and the limitation it costs is stated there; the substitution tooling is
built and tested for the day it can be run.

**Why sub-maximal (2026-10-10, pair 1 only so far).** At 100% strength nothing
ever faded, for anyone, in any block. The deviations were **systematic bias, not
scatter** — against the 100% table the researcher braked a median 14.9 m early
and ran 9.4 km/h slow, 89% and 83% of passes on the same side — so the design was
behaving exactly as specified, and **the target was wrong rather than the
tolerance too tight**. Re-recording at 85% centres it: the same 162 human passes
come out at +0.31 km/h and +8.1 m of bias, leaving variance rather than offset as
the residual. 80% was recorded too and over-corrects. `pair1` now loads the 85%
table; **pair 2 still loads its 100% one, which is an apparatus inconsistency
that must be closed before any participant drives.** The full record, including
what this costs at Gate G0, is the re-opening note at the top of
`configs/references/G0_REVIEW.md`. Framing v6 §177 and evaluation plan Phase 0
still say 95–100% and must be corrected.

**Thesis-document corrections now outstanding (the repo is ahead of the prose).**
Items 1–9 were written against framing v6 and the eval plan. The edits v9 itself
needs are listed section by section in `novelty_audit/CLAIMS_SHEET_v9.md` §5.
1. Framing v6 §177 / eval plan Phase 0 — "95–100% strength" → *strong but
   sub-maximal, stamped per block*, with the reachability evidence as the reason.
2. Framing v6 and the eval plan **do not mention bandwidth KR at all**, which is
   now part of the apparatus in every condition mode and part of the theoretical
   argument (the bands were modelled on bandwidth KR and delivered none of it).
   The condition descriptions, the probe's definition as an immediate
   no-feedback test (not a delayed retention test; R9), and
   the confound that a faded element loses its KR all need writing up.
3. The methods chapter still owes the **AI-only reference limitation** (G0 clause
   5, repo side done) and the **`partial_lap`** lap-validity reason.
4. Eval plan v2's **staggered-reversion target** sits below its own arithmetic
   floor (M4 decision) — correct the wording, not the controller.
5. The **corner-speed criterion is one-sided** from 2026-10-14, which framing
   v6's "minimum corner-speed deviation from the expert speed envelope" does not
   say. Write up the gate shape, the argument (the metric is a minimum, so the
   fast side is not an error), the evidence, and the residual risk that a
   sustained over-the-limit minimum with a ruined exit is caught only by the
   apex element.
6. **REVERSED 2026-10-30 by the full text (novelty audit, F9). The empirical-
   tolerance use of Bugeja et al. (2017) DOES survive.** The paper says the
   braking slip-ratio "tolerance value changes as the user improves; through
   empirical observation it is initially set to 7%". The racing-line tolerance
   "is initially set to 10 metres, and is decreased as the user improves". It
   runs on **Assetto Corsa** over UDP, and gives audio feedback only when the
   driver is wrong. So framing v6 §163 was right, and the 2026-10-14
   `[CORRECTED …]` brackets at v6 §163 and eval plan L68/L136 withdraw a
   **supported** claim. **The eval plan's copies need reverting in the prose (the
   author's job).** The v6 copy went with v6's deletion.
   What still holds: it neither fades nor reverts; its tightening rule is
   unspecified; its gains dissipated when the feedback was switched off (a
   guidance-hypothesis finding). Session-3 lap time p = .029, the other sessions
   n.s. The original 2026-10-14 reasoning is kept below as the record of a
   verdict reached from the abstract alone. *A claim withdrawn without the full
   text is as unsafe as one made without it.* It was load-bearing
   in three places (framing v6 §163, eval plan L68 and L136) as the precedent for
   *empirically set `tolerance` parameters*, and framing v6 cites specific
   internals ("slip-ratio and racing-line tolerances... set by empirical
   observation"). Nothing in the accessible record — abstract, repository record,
   visible fragments — mentions slip ratio, tolerance values, or how any threshold
   was chosen; the paper describes a **heuristic** rule system. **And nothing
   visible supports reading it as a precedent for probe-and-revert either:** its
   headline result is that gains *dissipated* when feedback was switched off,
   which is a guidance-hypothesis finding, so framing v6 §42 and §48 read it
   correctly and §163 does not. Keep it for "a telemetry heuristic feedback system
   for sim racing whose gains did not survive feedback removal" and for nothing
   else, **or** obtain the full text first (UM OAR request-a-copy, handle
   `123456789/106531`; or the 2016 B.Sc. dissertation, `123456789/14720`) and
   record what it actually says. The replacement precedents for the parameters are
   in `BAND_CALIBRATION_BRIEF.md` §B.
7. **The bandwidth-KR bands are an ANALOGY and must be labelled as one**
   (2026-10-14). Published bandwidths decide when to *deliver feedback*, not when
   to *withdraw a scaffold*; no study in the paradigm uses one as a mastery
   criterion. The paradigm also assumes error inside the band is partly motor
   noise the learner cannot correct, which argues a band should be at least as
   wide as the noise — so the apex floor is narrower than the paradigm's own
   premise allows, which is a second, independent reason to report it as a
   limitation.
8. **The controller re-evaluates its quorum every lap, and that inflates the
   false-advance rate** over the per-check figure (~7% → ~37% across fifteen looks
   in the review's model). Nothing in the repo or the prose had treated repeated
   looks as a statistical property. It belongs in the limitations, and it is the
   argument for sizing the window by MDC rather than by behaviour.
9. **The EVM must not be presented as a mechanism** (2026-10-14). No precedent
   exists for inflating an artificial reference's variance, and with σ_ref ≈
   0.02 m it has never changed a decision — the floors set all 27 bands. Frame it
   as a specified-but-inoperative parameter and say the floors were the operative
   ones; if a human reference is ever recorded, Gallagher et al. (2004)'s "2 SD
   from the expert mean" is the citable form. **Patched in place 2026-10-14** at
   framing v6 §163 and eval plan L68/L136 (same `[CORRECTED …]` brackets as item
   6), and annotated where the band is computed: `kit/trace_kit/evaluator.py`
   `bands()`, `lua/trace_rt/lib/evaluator.lua` `M.bands`, and the `evm`
   description in `schemas/controller_config.schema.json`. **Still owed by the
   chapter prose:** the full write-up of items 7 and 8 above, which are arguments
   rather than single sentences.

**Reference tick logs are not scratch.** Both original 100% reference blocks'
tick logs were deleted, so neither table can ever be re-extracted — which is why
pair 1's reference had to be *replaced* rather than re-extracted when the braking
zones moved. A committed reference that cannot be rebuilt from its own recording
cannot be kept in step with an annotation that changes. Keep them.

**Tolerance bands are floored and source-dependent**, not raw reference variance:
`band_m = max(σ_ref,m × EVM_source, floor_m)`. The **Expertise Variance Multiplier
(EVM)** compensates for the AI's missing motor noise — `EVM_AI` (default 3.0) for
AI-sourced corners, `EVM_human` (default 1.25) for human-substituted ones (whose
σ_ref already contains motor noise). EVM_AI, EVM_human, and the per-metric floors
are named config parameters, finalised in the pilot (Gate G2).

**The EVM is specified but INOPERATIVE, and the prose must say so** (2026-10-14).
The literature review found **no precedent of any kind** for inflating an
artificial reference's variance, and with σ_ref ≈ 0.02 m the product
`σ_ref × 3.0` ≈ 0.06 m has never come near any floor: **the floors set all 27
bands, so the EVM has never changed a decision.** The field stays — the schema
is stable, no study data exists yet, and `EVM_human` is the branch where a
measured σ would actually exist — but it is reported as a specified parameter
that no reported run exercised, not as a mechanism. The citable form of what it
was reaching for is **Gallagher et al. (2004)**: a criterion at **2 SD from the
expert mean**, which requires a *human* expert. The nearest HCI analogue, Fitts's
**effective width** (`W_e = 4.133 σ`), likewise scales to measured *human*
spread, not to a model's.

## Controller design rule

Discrete, **inspectable** state machine — *not* a learned policy. The design
choices are part of the contribution; a learned policy would hide them and needs
data that doesn't exist for this task/population. Keep it readable and documented.

## Dev workflow

Logic tests (conda env `ac_dev`, no game needed):

    conda activate ac_dev
    cd kit
    pytest -q          # schema validation + Lua/Python parity (Lua runs via lupa/LuaJIT)
    cd ../python/GRApp
    pytest -q          # in-game Python app core logic

`conda` is not on PATH in a non-interactive shell here; the env's interpreter
is `~/anaconda3/envs/ac_dev/python.exe`, so
`~/anaconda3/envs/ac_dev/python.exe -m pytest -q` works without activation.

The kit suite executes the real runtime Lua (`lua/trace_rt/lib/`) headlessly
through `lupa.luajit21` — LuaJIT 2.1, matching CSP. Keep it that way; lupa's
default runtime is a newer Lua and does not match the game.

Check recorded blocks with
`python -m trace_kit.integrity "<Documents>/Assetto Corsa/trace_data"`: manifest
schema, tick gaps, lap reconciliation, the `passes_*.jsonl` and `fades_*.jsonl`
streams (schema, block-id match, one pass per corner per lap, and a **replay of
the fade sequence** that rejects one no state machine could have produced), the
**probe-suppression guarantee** (no element was told its error while it was
hidden, and none was silenced while it was visible — both directions, because a
quietly over-suppressed apparatus biases the KR diagnostic the same way an
under-suppressed one invalidates the probe), and the **clamped-initiation pairing**
(a brake point clamped to its braking zone's opening is a floor, not a
measurement, so it must not have been read out as a magnitude - and a `clamped`
outcome must have the metric flag that justifies it), and — over a directory of blocks —
apparatus drift in CSP/AC/app versions and track length.

Validate one hand-written file (instrument responses, a manifest, an annotation)
without running the whole integrity check — the format is guessed from the
filename:

    python -m trace_kit.validate "<file>" [--format <name>]

Ingest recorded blocks and build the fade descriptives. **The `rq1` subcommand is
named after v6's RQ1 (fade timelines), which is v9's RQ3 live behaviour.** It is
not v9's RQ1 (reliability). The name is kept because renaming a CLI breaks the M6
exit test; just don't read it as v9's RQ1.

    python -m trace_kit.analysis ingest "<trace_data>" --out <dir>
    python -m trace_kit.analysis rq1    "<trace_data>" --out <dir>

All three subcommands exclude non-participant blocks (`dev_block`, `aborted`,
`dry_run`) by default; `--include dry_run` analyses the M6 protocol rehearsal
instead, `--include dev` the development blocks. **v9's RQ2 analysis (the
probe-failure excess vs the null) is deliberately not built.** See **Analysis**
above for what must be frozen before pilot data.

Report the CE/VE decomposition and what bandwidth KR actually did — the §0A
diagnostic, and the per-corner bias/scatter split the thesis should report
alongside pass/fail:

    python -m trace_kit.analysis kr "<trace_data>" --include dev --out <dir>

CE is the signed mean (bias), VE the SD (scatter), AE the mean absolute error.
The measured novice problem is a **CE** problem — 89% of brake points on the same
side of the reference — which AE cannot show and pass/fail cannot show either.
Reported per corner, with a first-half/second-half split; the half-split is NOT
evidence of learning on its own (it cannot detect learning in a plateaued driver
by construction). `kr_outcomes` counts the five different silences, so a block
where the messages never fired is visible rather than inferred. Passes whose
brake initiation was **clamped** to a braking zone's opening are excluded from
every average and counted in `clamped_excluded`: the magnitude is a floor, and
averaging it would turn the annotation's geometry into an apparent change in
bias.

Run the Phase 1 simulation and the threshold sweep from `kit/`:

    python -m trace_kit.simulate run   --streams 200 --out ../configs/simulation
    python -m trace_kit.simulate sweep --streams 25  --out ../configs/simulation
    python -m trace_kit.simulate freeze --config-id frozen-g1 --set band_floors.corner_speed_kmh=4.0

Both are deterministic from `--seed`. `--model key=value` re-runs the whole
verdict against a different synthetic novice, which matters because only one of
that model's eight parameters has an empirical anchor. **Re-running `freeze`
means re-running `run` and re-reviewing Gate G1** — `test_m4_simulate.py` fails
if the committed report's config hash stops matching the live file.

Build a reference table from recorded reference laps with
`python -m trace_kit.reference extract ... --pair pair1 --source ai`, then
`python -m trace_kit.reference compare <ai> <human> -o <substituted>`. Full
recipe and the substitution rule: `configs/references/README.md`.

Ask whether a reference is **reachable**, and what a different band floor would
buy, without touching the frozen config:

    python kit/tools/rescore.py   "<trace_data>" configs/references/reference_pair1.json \
        '{"braking_m": 15, "corner_speed_kmh": 11, "apex_m": 3.0}' 0.5
    python kit/tools/brakescan.py "<trace_data>" configs/references/reference_pair1.json \
        configs/annotations/annotation_ks_silverstone-national.json
    python kit/tools/apexscan.py  "<trace_data>" [block-id-for-the-window-profile]
    python kit/tools/windowscan.py [streams-per-type-per-pair] [seed]

`rescore` scores real passes through the real evaluator with floors overridden in
memory only; `brakescan` finds brake initiation in a window **wider than the
annotated zone**, which is the only way censoring at a zone edge is visible;
`apexscan` gives the apex criterion's per-pass rate at a range of candidate
floors *and* the deviation profile across the apex window, which is what
separates a driver who is off the line from a window measuring turn-in and exit.
`windowscan` asks the two questions the committed Phase 1 report cannot answer —
**which element** carries the verdict (`elements_removed` is only a count), and
what a longer `qualification` window would buy (`SWEEP_GRID` excludes it by
design); it reproduces the committed report at seed `trace-g1` before splitting
it, and it never writes the config.
`percornerscan.py` (2026-10-30) prices v9 §5.2's per element × corner
controller against the frozen one, on paired streams, by running one real
`Controller` per corner. It is the source of RQ2's probe counts and
noise-only probe-failure rates.

    python kit/tools/percornerscan.py [streams-per-type] [seed] [participants]

Every figure they reproduce is tabulated in `kit/tools/README.md` — if one stops
reproducing, chase it rather than patching it.

In-game: enable the app under Settings → General → UI Modules. After editing,
**restart the session** (menu → back on track) to reload; full game restart is
safest. `print(...)` and errors go to
`Documents\Assetto Corsa\logs\py_log.txt`.

## Guiding principles (from the thesis)

- One main idea (v9): **telemetry-driven, reversible UI fading whose fade
  decisions are audited.** Each fade is gated on a cue-off probe, and the probe
  outcomes are read against a calibrated null, separating guidance dependency
  from lap-to-lap variability. Everything serves it.
- **The null is the load-bearing novelty, not the idea of a null** (step 4).
  Simulated nulls, Type I errors and RTM corrections are standard (LC-CUSUM,
  Ye et al. 2016, Linden 2026). What is claimed is their use to attribute
  **post-withdrawal** outcomes. Never write code comments or reports that call
  probe-gated fading or the null itself new.
- The system is a first-class contribution — **document design decisions as
  carefully as results.**
- **Per-participant trajectories matter more than group means** at n≈15.
- The thesis will **not** claim statistical significance, generalisation beyond
  the tested cars/tracks/population, or that the thresholds/schedule are optimal.
  Don't write code or comments that imply otherwise.
