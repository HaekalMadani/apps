 # Evaluation Plan — Telemetry-Driven Adaptive UI Fading (v2, builds on Framing v6)

> **Changes from v1.** (1) Consistency gate redefined per-pass (delta from rolling mean) and the re-qualification-on-advance rule added, per Framing v6. (2) Tolerance bands floored; EVM split into EVM_AI / EVM_human. (3) G1 reversion target restated for staggered regression — the one-lap target was achievable only under perfectly synchronised regression, which only synthetic data exhibits. (4) RQ2 model corrected: pair as fixed effect (a two-level random intercept cannot support a variance estimate), crossed rather than nested condition, undefined corner-cluster term removed, fatigue limitation stated. (5) "Latin square" terminology corrected to counterbalanced 2×2 crossover. (6) Apex metric is a windowed RMS; annotation carries an apex window. (7) Pre-committed recruitment fallback added.

> **Amendments since v2 was written (2026-09-09, from running Phase 1).** Two
> substantive corrections, both recorded inline below and marked *[amended
> 2026-09-09]*. (1) Design target 3's staggered clause was stated **below its own
> arithmetic floor** and is unreachable by any threshold setting; it is restated
> as excess latency over that floor, which reproduces the original figure exactly
> for synchronised regression. (2) Gate G1 is **met**, with the frozen
> configuration and its hash recorded. Nothing else in the plan changed. These
> are amendments to a v2 document rather than a v3, so the version bump is
> deliberate if and when the author makes it.

This plan operationalises the evaluation described in the framing document. Every phase is specified as **inputs → procedure → outputs**, so that each output is an explicit dependency of a later phase. Concrete numbers (lap counts, block durations, window sizes) are stated as defaults; any change must be recorded with a reason before data collection begins.

---

## 0. Design summary

| | |
|---|---|
| Design | **Between-subjects on condition, one car-track pair (pair 1).** *[REVISED 2026-10-15 — see `SESSION_BUDGET_BRIEF.md`. Was: within-subjects, 2 conditions × 2 car-track pairs.]* |
| Conditions | **Adaptive** (fading controller active) vs **Static** (all three UI elements at full salience throughout training) |
| Counterbalancing | Condition assigned alternately at enrolment. **There is no crossover**: the 2×2 design needed two training blocks of ≥ 15 laps, which is ~37 min of driving before any instrument. |
| Sample | n ≈ 15 main participants (~7–8 per arm) + 2 pilot participants (not pooled) |
| Sessions | **One ~33-minute sitting** (15-lap training block, decided 2026-10-15), plus consent and the pre-study questionnaire beforehand and a remote follow-up call for the confidence questionnaire and the RQ3 interview. Rig time ~33 min; total participant commitment ~55-60 min. |
| Framing | Systems-and-characterisation study; effect sizes with credible intervals, no confirmatory claims |

**Why the crossover was dropped, and what it costs.** The ceiling on *rig
time* is about **30 minutes per participant**, against the ~3 h 15 this plan
originally booked; the sitting lands at ~33 min because Gate G1 needs a 15-lap
training block (see Phase 3). Measured lap times (62–76 s at National, 71–98 s at
International — the plan's "~2-minute circuit" is wrong by nearly 2×) make the
driving affordable; it is the *two-pair crossover* that is not, because every
phase doubles. `SESSION_BUDGET_BRIEF.md` § D costs three alternative shapes;
this is Shape B.

The cost is stated plainly rather than minimised: **RQ2 keeps its form, not its
substance.** Between subjects at ~7–8 per arm, with no unassisted baseline and
3 valid retention laps per participant, the condition contrast will not be
interpretable on its own. The thesis already declines to claim statistical
significance; this makes that decline load-bearing rather than modest. RQ1 (what
the controller did, per participant, per corner) and RQ3 (the interviews) are
unaffected and are where the contribution sits.

**Also descoped: pair 2.** One pair per participant means `ks_audi_tt_cup` /
`international` is no longer used, so its outstanding 100%-reference
inconsistency stops being a blocker. The study then rests on **one car and one
layout**, which narrows the generalisation claim it was already declining to
make. Say the second apparatus was descoped; do not leave it half-finished and
unmentioned.

---

## Phase 0 — Reference acquisition

**Inputs.** Two selected car-track pairs; one fixed vehicle setup per pair; AC AI driver; the study telemetry pipeline (this phase doubles as its end-to-end test).

**Procedure.** Before any reference laps are processed, each track is **manually annotated**: a version-controlled file per track defines corner IDs, entry/exit gates as normalized track-spline positions, corner-type tags, and per-element evaluation zones (braking zone, apex window — a spline window centred on the apex gate, half-width recorded per corner — and corner-speed zone). Compound sections — chicanes or linked corners sharing a single braking event — are annotated explicitly as compound corners (one braking zone, multiple apex windows where appropriate). All downstream per-corner processing — reference extraction, marker placement, runtime evidence — consumes this file. Then run the AI at 95–100% strength for 12 laps per pair under the fixed setup, logging per-tick telemetry through the same pipeline participants will use (autopilot on the *player* car, so reference laps share the participant's car and setup; the manifest records `autopilot` and `ai_level_pct`). A human validation step was planned — 12 laps per pair from one experienced sim racer, with a per-corner comparison of AI versus human brake points, apex lines and speed envelopes, substituting the human reference wherever the AI diverged materially. **It was not carried out: no experienced sim racer was available, and a beginner-recorded reference would be a *novice* reference, not a weaker expert one — substituting it would drag the target toward novice performance and defeat the intervention.** The reference is therefore AI-sourced at every corner (`source: "ai"` throughout; `EVM_human` goes unused), and the absence of the human bound is carried as a stated limitation into Gate G2 and the methods chapter. The comparison-and-substitution tooling is built and tested, so the step is a re-run if an experienced driver becomes available before the main study.

**Outputs.**
- **Corner annotation files** (one per track, version-controlled): corner IDs, spline-position gates, type tags, per-element evaluation zones; published with the dataset.
- `reference_laps/` — per-tick telemetry, 12 AI laps per pair. *[The human validation laps were never recorded (see Phase 0); and from 2026-10-15 only pair 1 is used in the study, so pair 2 is apparatus history rather than study material.]*
- **Per-corner reference table** (one row per annotated corner per pair): brake-initiation world coordinate, apex world coordinate, minimum-corner-speed envelope (mean ± band), apex lateral-line band, and the source of each corner's reference (AI or human-substituted).
- ~~**AI-vs-human validation report**~~: not produced — see the procedure above. The tooling (`trace_kit.reference compare`) remains available; its absence is recorded as a limitation, not silently dropped.
- Reference quality report: lap-time coefficient of variation across the 12 laps, plus the per-corner count of contributing laps.

**Gate G0** (restated, since the AI-vs-human clause can no longer be met). Annotation files reviewed against a driven lap (every gate and evaluation zone visually checked on track); reference lap-time CoV < 1% per pair; visually sane lines in all corners, confirmed by standing the extracted markers on track and checking each sits where a competent driver would brake and apex; every corner contributing at least the extractor's minimum lap count; and the **absence of human validation recorded as a limitation** in the dataset README and the methods chapter. Otherwise re-annotate or re-record before proceeding.

Because the human bound is gone, **Gate G2 absorbs the work it would have done**: the pilot is now the only empirical check that the reference is reachable by real novices. A G2 failure here means recalibrating the band floors (and, if that is not enough, revisiting the car choice), not merely tuning the EVM — the AI's σ is far below the floors, so the floors, not the multiplier, set every band.

---

## Phase 1 — Threshold calibration by simulation

**Inputs.** Per-corner reference table (Phase 0); state-machine implementation; assumed novice behaviour model (initial offset and variance per metric, learning-rate range, lap-to-lap noise — parameters documented in the simulation script).

**Procedure.** Generate ≥ 1,000 synthetic participant streams across a grid of learner types (fast improver, slow improver, non-improver, erratic, **staggered regressor** — regression onset spread across corners over several laps, since real regression is not synchronised). Run each stream through the controller. Tune the controller parameters and per-metric tolerance bands until the design targets below hold. Defaults under tune: per-corner qualification window (**3 of last 4 passes**), de-qualification rule (**2 consecutive failures**), element-level quorum (advance at **≥ 75%** of applicable corners qualified, revert below **50%**), probe length (**3 laps**), reversion cap (**2 cycles per element per block**), per-pass **consistency delta** for the braking criterion (default **0.5 × accuracy band**), and per-metric **band floors**. The **re-qualification-on-advance rule** (all corner qualification states reset on every stage advance; see Framing v6) is a fixed structural rule, not a tuned parameter, and the simulation must run with it active.

**Expertise Variance Multiplier (EVM).** Tolerance bands are defined as `band_m = max(σ_ref,m × EVM_source, floor_m)`, where `σ_ref,m` is the reference laps' standard deviation for metric *m*. The multiplier exists because the AI reference lacks the inherent motor noise that persists even in expert human performance (Cohen & Sternad, 2009); bands taken from raw AI variance would be impossibly narrow for any human driver. Two structural guards: the **absolute per-metric floor** prevents the band being hostage to a near-zero baseline (the AI is consistent by construction, so σ_ref can be arbitrarily small at some corners), and the multiplier is **source-dependent** — **EVM_AI, provisional default 3.0**, for AI-sourced corners; **EVM_human, provisional default 1.25**, for human-substituted corners, whose σ_ref already contains human motor variability and would otherwise be inflated twice. Both multipliers and the floors are explicitly named free parameters of the controller configuration, and their final values are fixed in Phase 2. **[CORRECTED 2026-10-14: the Bugeja et al. (2017) precedent cited here for "named, empirically set `tolerance` parameters" is not supported by any accessible version of that paper and is withdrawn. Phase 2 sets the floors by the contrasting-groups method (Jørgensen et al., 2018) and the window length by minimal detectable change (Weir, 2005) instead. Note also that `σ_ref × EVM` has never exceeded a floor in any run, so the EVM is specified but inoperative — see `BAND_CALIBRATION_BRIEF.md`.]** EVM_AI = 3.0 is used to generate the synthetic learner streams.

**Design targets.**
- A *typical improver* fully traverses the machine (full → reduced → probe → removed) for ≥ 2 of 3 elements within one training block. **[UPDATED 2026-10-15: the block is **15 laps** and the arithmetic is now `2 × required_passes + max(probe.laps, required_passes)`, which at `frozen-g1b` (2-of-3, 2-lap probe) is a **6-lap** floor — 2 laps to broad qualification at full salience, 2 to *re-qualify* at reduced (the dwell the re-qualification rule enforces), then a 2-lap probe that still needs a fresh evidence window because `_quorum_ready` gates `probe_to_removed` too. The old "~3–4 + ~3–4 + 3" gave a 9-lap floor. Measured at 0.72 over 15 laps; it scores 0.43 at 12 laps and fails, which is why the block is 15 and why it must be enforced as a lap count rather than a time box.]**
- A *non-improver* leaves full salience in at most **10% of streams**, and less often than a typical improver fails to traverse. **[RESTATED 2026-10-15.]** This read "*never* leaves full salience", at exactly 0.000, and that bar turned out to be satisfiable only by a system that never fades anything for anyone: at the `frozen-g1` band floors the braking and apex elements never advanced in a single **real recorded block** (`kit/tools/README.md` § `feasible.py`), and every calibration that made the machine work failed the clause. A conservatism target is trivially met by a system that never acts. It is now a stated **false-pass rate with the false-fail rate reported beside it** — the contrasting-groups style this plan already adopts for the band floors (Jørgensen et al. 2018) — and the asymmetry is asserted as well as the bound, because the design errs toward delayed withdrawal. Measured at `frozen-g1b`: false pass **5.75%**, false fail **28%**. The 10% bound is a **declared design parameter, provisional until Gate G2**, justified by that ratio rather than by any published value; see `simulate.TARGET_RATES`.
- Probe reversion triggers on simulated broad regression (qualified share dropping below 50%) **at the earliest lap the evidence can support it, plus at most one lap**, and broad regression is answered by removal in at most **2% of regressing streams**. **[RESTATED 2026-10-15: this read "never answered by removal" at exactly 0.000 — the same unsatisfiable shape as the non-improver clause above, and satisfied at `frozen-g1` only because nothing was ever removed. It is bounded an order of magnitude tighter than the false-pass rate because the error is costlier — a late reversion costs one lap driven without the cue, a removal costs the rest of the block — and because the bound must discriminate: the adopted 2-of-3 ladder measures 0.75% while every 3-of-4 alternative at workable floors measures 12–26%. Provisional until Gate G2.]** The staggered-regressor stream exists to keep the simulation honest about this, and the reversion cap must still prevent oscillation in the *erratic* learner type.

  *[amended 2026-09-09]* This target previously read "within **one lap of onset when regression is synchronised across corners, and within two laps when it is staggered**". The two-lap staggered figure is **not reachable by any threshold setting**, and the simulation found it immediately. Reversion latency has a floor set by two rules acting together: a corner cannot de-qualify before its second consecutive failure, and the element cannot revert until *enough corners have de-qualified to put the qualified share below the threshold* — which, for onsets one lap apart across four corners, is not the first corner's onset but the **third**. The measured median lag from the first onset is therefore 3 laps, and no configuration in the 144-candidate sweep changed that. Measuring instead against the arithmetic floor separates the part the controller is responsible for from the part the design's own rules fix in advance; it is met at **zero excess** for both synchronised and staggered streams, and it collapses to the original one-lap figure exactly when regression is synchronised. The added "never answered by removal" clause is the safety property the latency was always a proxy for: a late reversion costs a lap of unscaffolded driving, whereas a removal costs the rest of the block. It is read strictly (0 tolerated failures) and counts only removals occurring once the regression could already have been detected — an element removed before that point was removed on evidence that was still good, and block-scoped permanence then correctly keeps it removed.

**Outputs.** *[all produced 2026-09-08; see `configs/simulation/G1_REVIEW.md`]*
- Frozen controller configuration file (window sizes, thresholds, EVM_AI/EVM_human, band floors, consistency delta, probe/reversion rules, re-qualification rule flag) — placed under version control; hash recorded. → `configs/controller_config.json`, `config_id: frozen-g1b` (re-frozen 2026-10-15). **The hash is deliberately NOT repeated here** — a copy went stale within a month last time. Read it from `configs/simulation/G1_REVIEW.md`, which is regenerated with the report it describes.
- Feasibility figure: simulated fade trajectories by learner type (becomes a thesis figure). → `configs/simulation/feasibility_figure.svg`.
- *(added)* The design-target verdicts and the parameter sweep behind the frozen values → `configs/simulation/simulation_report.json`, `sweep_report.json`.

**Gate G1.** All three design targets met; otherwise revise window/thresholds (or block length) and re-run.

***[amended 2026-09-09] G1 is MET (2026-09-08)***, on 2,800 synthetic streams
(seven learner types × two car-track pairs × 200), run against the committed
reference tables rather than a synthetic circuit and through the same controller
and evaluator the runtime uses — both pinned to their Lua counterparts by the
golden-trace parity suite, which is what makes a simulated gate mean anything.

**Calibration moved exactly one parameter.** The sweep evaluated 144
configurations over the four free parameters and 34 met every target; the
selection rule takes the tightest, because a loose band fades a scaffold for a
learner who has not earned it. `band_floors.corner_speed_kmh` went from the
provisional **3.0 to 4.0 km/h** — it was the single binding constraint on target
1 (15% of typical improvers traversed two elements at 3.0, 38% at 3.5, 59% at
4.0). Everything else keeps its framing-v6 default, and the qualification window,
quorum thresholds and probe rules were deliberately **not** swept: they are
structural choices the framing argues for, and moving them would change the
mechanism rather than calibrate it. `EVM_AI` and `EVM_human` are unchanged and
remain provisional for Phase 2 — with every band currently floor-set, they have
no effect on any criterion at present.

**Two rules had to be added to the controller for the machine to work at all**,
both found by the golden-trace corpus rather than by the simulation: *quorum
readiness* (the re-qualification reset drops the qualified share to zero on every
advance, so without a rule the next pass would revert the advance) and *one
regression, one stage* (a reversion left the element holding the same
sub-threshold share that caused it, so a deep collapse cascaded two stages in two
passes and the reversion cap could never be reached). Both are stated in full in
`lua/trace_rt/lib/controller.lua` and belong in the methods chapter as design
decisions, not implementation details.

**Three consequences for Phase 3 that this plan should be read alongside.** No
simulated learner cleared all three elements inside a 15-lap block, so **partial
traversal is the expected case** and RQ1's trajectory figures should be built for
it. About **38% of typical improvers finished mid-probe**, which sets how large
the right-censored cell in the probe-outcome tabulation will be. And the
**reversion cap was never reached** by any of the 2,800 streams, so it remains an
untested-in-practice safeguard; a real participant reaching it is a reportable
individual case.

**What G1 does not establish.** The verdict is only as good as the synthetic
novice it was run against, and only one of that model's eight parameters has an
empirical anchor (the initial brake offset, from Gate G0's measured novice brake
points). The lap-to-lap variances in particular are stated assumptions. G1
certifies that the controller behaves as designed against a plausible learner; it
does not certify that real novices are that learner. That remains Phase 2's job,
and the return path from a G2 failure to this phase is unchanged.

---

## Phase 2 — Pilot (n = 2)

**Inputs.** Frozen controller config; full apparatus; session protocol scripts.

**Procedure.** Each pilot participant completes **the real sitting, unabridged** *[revised 2026-10-15: there is nothing left to compress — the sitting is 30 minutes and one condition, so the pilot now runs the main protocol exactly as specified in Phase 3, which also makes it the protocol-timing measurement]*. Pilots may fall outside the main recruitment criteria; their data are never pooled with the main sample. A specific purpose of the pilot is to **empirically justify and calibrate the band floors** — which from 2026-10-15 also means checking the `frozen-g1b` floors (12 m / 9 km/h / 1.5 m) against a **real novice**: they were set from the researcher’s own passes, and the researcher’s best lap is within 2.1% of the 85% AI reference, so those floors are a **lower bound** on what a true novice needs. The second pilot purpose is to resolve the 12-vs-15-lap tension recorded in Phase 3 — and to report the EVM as inoperative rather than calibrate it, since with the AI reference every band is set by its floor. **[CORRECTED 2026-10-14: "mirroring the empirical-observation approach of Bugeja et al. (2017)" is withdrawn — see the correction at the EVM definition above. The calibration follows contrasting-groups standard setting (Jørgensen et al., 2018), with the cut placed at a stated false-pass rate and the false-fail rate reported.]**

**Outputs.**
- Distribution comparison: real novice per-corner metrics vs the synthetic streams from Phase 1.
- **EVM calibration:** real pilot per-metric variance compared against the AI baseline variance (and against the human-reference variance for substituted corners); the finalised EVM_AI, EVM_human, and floors recorded in the controller configuration before the main study. If any finalised value differs from its default, the Phase 1 simulation is re-run with the final values before Gate G2 closes.
- Controller event log audit: every fade event manually checked against raw telemetry for misfires.
- Protocol timing measurements (does the session fit the booked slot?).

**Gate G2.** (a) Real metric distributions fall within the envelope the simulation was tuned against, (b) zero unexplained controller transitions, (c) ≥ 1 fade event observed per pilot, (d) EVM_AI, EVM_human, and floors finalised and the configuration re-frozen (with re-run simulation if any value changed). Any failure → recalibrate (return to Phase 1) before the main study.

---

## Phase 3 — Main study (n ≈ 15)

*[REWRITTEN 2026-10-15. This phase previously specified three sessions of
60 + 75 + 60 min against a participant-time ceiling of 30 minutes for the whole
study. The costing of the alternatives is `SESSION_BUDGET_BRIEF.md` § D; this is
Shape B. The lap-validity rules, the integrity check and everything below them
are unchanged.]*

### Before the sitting — outside the session budget (confirmed 2026-10-15)

Consent form, participant information sheet and the pre-study questionnaire
(driving history, gaming/sim hours, league check against inclusion criteria) are
read and e-signed **in advance**, and the ethics process is handled **outside
the timed sitting**. This is settled, not an assumption: it was the one
precondition that could have invalidated the whole shape, because the ~10
minutes it takes does not fit inside the sitting at any lap count.

**Consequence for reporting:** the quoted ~32.9 min is *rig time*, not total
participant burden. Consent and questionnaire beforehand, plus a 10–15 minute
remote interview afterwards, put the real per-participant commitment closer to
**55–60 minutes**. Report both figures — the sitting is what the apparatus and
the lap budget constrain; the total is what a participant is actually asked for.

### The sitting — one block, ~32.9 min (pair 1 only: `ks_bmw_m235i_racing` / `ks_silverstone` `national`)

**Inputs.** Consent and the pre-study questionnaire, both completed beforehand
(see above); pair 1 annotated and referenced; frozen controller config; assigned
condition.

**Procedure.**

| phase | min | notes |
|---|---|---|
| Welcome, seating and wheel calibration | 4.0 | settings logged |
| Task instruction — what each cue means | 3.0 | cannot be skipped for a novice; it is part of the apparatus |
| Familiarisation, 1 lap | 1.2 | discarded |
| **Training block — 15 laps** | **17.5** | condition per assignment; adaptive runs the controller live, static pins all three elements at full salience |
| **Unassisted block — 4 laps** (3 valid) | 4.7 | all elements off (`off` condition), KR withdrawn with them |
| NASA-TLX | 2.5 | immediately after the training block |
| | **32.9** | |

**15 laps, decided 2026-10-15.** The 12-lap variant that fit a 30-minute box is
**rejected**: Gate G1's first target scores **0.72 at 15 laps and 0.43 at 12**,
and the frozen configuration was certified at 15. Three laps cost ~3.5 minutes
of session time; buying the same traversal rate by widening the band floors
instead costs far more on both error margins (15/11/1.5 takes the false-pass
rate from 5.8% to 8.0% and removal-despite-regression from 0.75% to 13.8%).
**So the sitting is ~33 minutes, not 30.** Recorded here as the decision rather
than left as a tension.

**The training block ends on a LAP COUNT, not a timer.** The measured lap time
is ~70 s, so a time-boxed block containing two spins silently delivers 12–13
laps — a configuration the gate rejects, with nothing about the block looking
wrong. The experimenter panel must refuse to stop the block before 15 laps and
record the reason if it is stopped anyway.

**Outputs** (unchanged in form from the previous three-session plan, minus the
second pair):

- Per-tick telemetry (shared-memory read, logged at 20 Hz minimum; fields: world
  position, speed, brake/throttle/steer inputs, gear, lap/sector markers,
  off-track flags).
- **Per-corner-pass records** — one row per corner pass: corner id, lap,
  brake-initiation distance to reference point, distance to the corner's rolling
  brake-initiation mean (the consistency-gate input), brake-pressure modulation
  summary (descriptive, not gated), minimum corner speed and envelope deviation,
  RMS lateral deviation over the apex window, validity flag, per-element per-pass
  criterion booleans (accuracy and consistency gates separately for braking),
  per-element corner qualification state, element-level controller stage, and the
  per-element bandwidth-KR outcome.
- **Fade-event log** (adaptive blocks): timestamp, lap, element, transition type
  (full→reduced, reduced→probe, probe→removed, probe→revert, block-end
  probe-incomplete/censored), and the triggering quorum statistics.
- NASA-TLX scores.

### After the sitting — remote, same day where possible

Confidence and perceived-dependence questionnaire, then the 10–15 minute
semi-structured interview (audio recorded; guide covers workload, confidence,
and awareness of fading — including whether the participant noticed elements
disappearing and when). **Neither needs the rig**, and moving them out is what
makes the sitting fit — confirmed 2026-10-15 as being outside the session
budget, like the consent process. A delay between the drive and the interview is
a limitation to state: RQ3 asks partly about moment-to-moment experience, and
the further the interview sits from the drive the more it measures recollection.
Run it the same day wherever possible and record the gap per participant so the
limitation can be reported with a number rather than as a caveat.

### What this costs the measurement, in one place

- **No baseline block.** The pre-training baseline laps are gone. The only
  proxy is **training laps 1–2**, where nothing has faded in either condition —
  and it is measured *with* full scaffolding in both arms, so it is a covariate
  for driving skill, **not** an unassisted baseline. Say so wherever it is used.
- **3 valid unassisted laps**, against the 8 this plan previously specified.
- **No retention probe** at day 5–7; the optional exploratory probe is dropped.
- **No within-participant condition contrast**, so the fatigue confound the old
  plan carried disappears and is replaced by between-group variance at ~7–8 per
  arm.

### Lap-validity rules (applied uniformly, automated at logging time)

A lap is **invalid** if: more than two wheels leave the track surface at any point; the car contacts a wall; the lap involves a pit entry/exit; or the lap is the first of a block. Invalid laps are excluded from lap-time outcomes but their corner passes still feed the controller (with the pass-level validity flag set), since the controller must run on whatever the participant actually drives.

### Integrity check (after every session)

Automated script verifies: telemetry gaps < 0.5 s, expected lap counts present, fade-event log parses, questionnaire files saved. Failures trigger a re-run or a documented data-loss note the same day.

---

## Phase 4 — Analysis

**Inputs.** All Phase 3 outputs; frozen analysis scripts (written and dry-run against pilot + simulated data *before* the main study ends, to prevent analysis decisions being made after seeing results).

### RQ1 — System characterisation (descriptive)

- Per-participant **fade-trajectory plots**: controller stage over corner passes, one panel per element, all 15 participants.
- **Per-corner qualification heatmaps** (corner × lap, per element) as supplementary characterisation — showing *which* corners carried or blocked each quorum transition.
- Distribution of time-to-first-fade and time-to-removal per element across participants; probe outcomes tabulated (held / reverted / censored, per element), reversion-cap hits reported.
- Atypical trajectories (never-fades, repeated reverts) reported as individual cases with telemetry excerpts.
- **Output:** trajectory figure set + fade-timing distribution table.

### RQ2 — Adaptive vs static (estimation, not testing)

*[RESPECIFIED 2026-10-15. The previous model was written for a within-subjects
2×2 crossover over two car-track pairs. Shape B
(`SESSION_BUDGET_BRIEF.md`) assigns condition **between subjects** on **one**
pair, so four of the old model's terms no longer exist and one of its covariates
is not measured. The model is **still deliberately not implemented** — Phase 4
requires the analysis scripts frozen before results are seen, and writing it
earlier would freeze a specification whose only test was simulator output.]*

- **Model:** Bayesian regression on lap-level observations from the unassisted
  block. `unassisted lap time ~ condition + early-training lap time
  (standardised) + (1 | participant)`.
  - **Condition is now a between-subjects factor**, so `(1 + condition |
    participant)` is gone — a participant contributes only one condition and a
    by-participant condition slope is not identifiable. `(1 | participant)`
    remains, because each participant contributes several unassisted laps.
  - **`pair`, `condition order` and `pair order` are all removed.** One pair is
    driven, so `pair` is a constant; one block is driven, so neither order term
    exists.
  - **The baseline covariate changes meaning and must be labelled.** There is no
    pre-training baseline block. The covariate is the mean of **training laps
    1–2**, before any element can have faded — which makes it a covariate for
    *driving skill measured with full scaffolding in both arms*, **not** an
    unassisted baseline. It cannot adjust for unassisted ability, and saying so
    is part of the result.
  - Secondary model with lap-time variability (per-participant SD of valid
    unassisted laps) as outcome, same right-hand side.
- **Priors:** weakly informative — Normal(0, 1) on standardised coefficients,
  Exponential(1) on group-level SDs; stated in full in the methods chapter and
  frozen with the analysis scripts.
- **Power, stated honestly and up front.** ~7–8 participants per arm, **3 valid
  unassisted laps each**, no unassisted baseline. The posterior on the
  adaptive-minus-static difference will be dominated by the prior and by
  between-person variance. **RQ2 keeps its form, not its substance** — report the
  interval, state that it does not support a directional claim, and do not let
  it carry the thesis. RQ1 and RQ3 are where the contribution sits.
- **Confounds, stated rather than modelled:**
  - **Between-group confounding replaces the old fatigue confound.** With
    condition assigned between subjects at n ≈ 15, prior sim-racing exposure is
    not balanced by design; the pre-study questionnaire records it and group
    differences are reported descriptively. The old "both training blocks share a
    session" fatigue confound no longer applies, because there is one block.
  - **An adaptive participant who reaches a probe receives less *total* feedback
    than a static one**, not merely less guidance, because bandwidth KR is
    withdrawn with the scaffold (`lib/kr.lua` rule 4). Unchanged by the
    respecification, and still a methods-chapter item.
- **Output:** posterior distribution of the adaptive-minus-static difference with
  95% credible interval; posterior predictive checks; the group composition table
  that documents what between-subjects assignment left unbalanced. No
  significance language anywhere.

### RQ3 — Experience and alignment (thematic + alignment analysis)

- Thematic summary of interviews under predefined themes (workload, confidence, awareness of fading) plus emergent themes appearing in ≥ 3 participants. Single coder; full double-coded analysis explicitly out of scope.
- TLX compared descriptively between conditions per participant.
- **Alignment analysis:** for each participant, reported awareness of element disappearance is matched against the objective fade-event log (did they notice? when relative to the actual event?). Output: alignment table — the bridge between RQ3 and RQ1.

### Exclusion and missing-data rules (pre-committed)

- A participant is excluded entirely only for: **failure to complete the sitting** (the training block and the unassisted block; the remote interview missing is NOT an exclusion, it is missing RQ3 data) *[updated 2026-10-15 from "failure to complete Session 3"]*, discovered violation of inclusion criteria, or hardware failure corrupting > 30% of their data. Partial data otherwise retained and modelled (Bayesian models tolerate unbalanced data).
- All exclusions logged with reasons in the dataset README.

---

## 5. Output inventory (what exists when the evaluation is done)

| Artefact | Produced in | Feeds |
|---|---|---|
| Per-corner reference table | Phase 0 | Rendering, controller, all metrics |
| Frozen controller config + feasibility figure | Phase 1 | Phase 2–3; thesis methods chapter |
| Pilot audit report | Phase 2 | Go/no-go; methods chapter |
| Characterisation dataset (per-tick, per-corner, per-lap, fade events, instruments) | Phase 3 | All RQs; published with thesis |
| Fade-trajectory figures + timing distributions | Phase 4 | RQ1 chapter |
| Posterior estimates + credible intervals | Phase 4 | RQ2 chapter; power inputs for future work |
| Thematic summary + alignment table | Phase 4 | RQ3 chapter |

## 6. Schedule risks already mitigated

- Lap budget → per-corner evidence + Phase 1 simulation (Gate G1).
- Threshold miscalibration → Phase 2 pilot (Gate G2) with explicit return path to Phase 1.
- Reference quality → Gate G0. The human-substitution fallback is **no longer available** (Phase 0); the residual risk that the AI reference is unreachable by novices is carried to Gate G2, where the band floors are calibrated against real pilot distributions.
- Analysis flexibility → scripts and priors frozen before main data collection ends.
- Carryover → order terms in the model; reported, not assumed away.
- Recruitment / scheduling shortfall → **pre-committed degraded fallback**, recorded now so a crisis becomes a documented contingency rather than an improvised one. *[Updated 2026-10-15: the booking load is now ~17 single sittings of 30 min rather than ~45 sessions of an hour, which removes most of this risk — the schedule was the reason the study was compressed, and the compression paid for itself here.]* The retention probe is already dropped. Accept **n = 10** as the minimum main sample (~5 per arm; the Bayesian estimation framing degrades gracefully — intervals widen, the design does not break), and note that between-subjects assignment makes n the binding constraint in a way the old crossover did not. All gates are retained at every fallback level. Any invocation of the fallback is logged with date and reason in the dataset README.
