 # Evaluation Plan — Telemetry-Driven Adaptive UI Fading (v1, builds on Framing v5)

This plan operationalises the evaluation described in the framing document. Every phase is specified as **inputs → procedure → outputs**, so that each output is an explicit dependency of a later phase. Concrete numbers (lap counts, block durations, window sizes) are stated as defaults; any change must be recorded with a reason before data collection begins.

---

## 0. Design summary

| | |
|---|---|
| Design | Within-subjects, 2 conditions × 2 car-track pairs |
| Conditions | **Adaptive** (fading controller active) vs **Static** (all three UI elements at full salience throughout training) |
| Counterbalancing | Latin square over condition order × pair order (4 sequences) |
| Sample | n ≈ 15 main participants + 2 pilot participants (not pooled) |
| Sessions | 3 per participant (+ optional exploratory retention probe, day 5–7) |
| Framing | Systems-and-characterisation study; effect sizes with credible intervals, no confirmatory claims |

**Latin-square sequences** (participants assigned round-robin at enrolment):

| Seq | Session 2, block 1 | Session 2, block 2 |
|---|---|---|
| A | Pair 1 / Adaptive | Pair 2 / Static |
| B | Pair 1 / Static | Pair 2 / Adaptive |
| C | Pair 2 / Adaptive | Pair 1 / Static |
| D | Pair 2 / Static | Pair 1 / Adaptive |

With n = 15: sequences receive 4/4/4/3 participants.

---

## Phase 0 — Reference acquisition

**Inputs.** Two selected car-track pairs; one fixed vehicle setup per pair; AC AI driver; the study telemetry pipeline (this phase doubles as its end-to-end test).

**Procedure.** Before any reference laps are processed, each track is **manually annotated**: a version-controlled file per track defines corner IDs, entry/exit gates as normalized track-spline positions, corner-type tags, and per-element evaluation zones (braking zone, apex gate, corner-speed zone). Compound sections — chicanes or linked corners sharing a single braking event — are annotated explicitly as compound corners (one braking zone, multiple apex gates where appropriate). All downstream per-corner processing — reference extraction, marker placement, runtime evidence — consumes this file. Then run the AI at 95–100% strength for 12 laps per pair under the fixed setup, logging per-tick telemetry through the same pipeline participants will use. As a **planned validation step, not a contingency**, additionally record 12 laps per pair from one experienced sim racer (not a study participant) on the same fixed setup, and produce a per-corner comparison of AI versus human brake points, apex lines, and speed envelopes. Corners where the AI diverges materially — it is known to brake conservatively and not trail brake — substitute the human reference; all other corners keep the AI reference for reproducibility.

**Outputs.**
- **Corner annotation files** (one per track, version-controlled): corner IDs, spline-position gates, type tags, per-element evaluation zones; published with the dataset.
- `reference_laps/` — per-tick telemetry, 12 AI laps + 12 human validation laps × 2 pairs.
- **Per-corner reference table** (one row per annotated corner per pair): brake-initiation world coordinate, apex world coordinate, minimum-corner-speed envelope (mean ± band), apex lateral-line band, and the source of each corner's reference (AI or human-substituted).
- **AI-vs-human validation report**: per-corner comparison and the list of substituted corners.
- Reference quality report: lap-time coefficient of variation across the 12 laps.

**Gate G0.** Annotation files reviewed against a driven lap (every gate and evaluation zone visually checked on track), reference lap-time CoV < 1% per pair, visually sane lines in all corners, and the AI-vs-human comparison reviewed with all substitution decisions recorded; otherwise re-annotate or re-record before proceeding.

---

## Phase 1 — Threshold calibration by simulation

**Inputs.** Per-corner reference table (Phase 0); state-machine implementation; assumed novice behaviour model (initial offset and variance per metric, learning-rate range, lap-to-lap noise — parameters documented in the simulation script).

**Procedure.** Generate ≥ 1,000 synthetic participant streams across a grid of learner types (fast improver, slow improver, non-improver, erratic). Run each stream through the controller. Tune the controller parameters and per-metric tolerance bands until the design targets below hold. Defaults under tune: per-corner qualification window (**3 of last 4 passes**), de-qualification rule (**2 consecutive failures**), element-level quorum (advance at **≥ 75%** of applicable corners qualified, revert below **50%**), probe length (**3 laps**), reversion cap (**2 cycles per element per block**).

**Expertise Variance Multiplier (EVM).** Tolerance bands are defined as `band_m = σ_ref,m × EVM`, where `σ_ref,m` is the reference laps' standard deviation for metric *m*. The multiplier exists because the AI reference lacks the inherent motor noise that persists even in expert human performance (Cohen & Sternad, 2009); bands taken from raw AI variance would be impossibly narrow for any human driver. **Provisional default: EVM = 3.0**, used to generate the synthetic learner streams. The EVM is an explicitly named free parameter of the controller configuration — the precedent is the named, empirically set `tolerance` parameters in Bugeja et al. (2017) — and its final value is fixed in Phase 2.

**Design targets.**
- A *typical improver* fully traverses the machine (full → reduced → probe → removed) for ≥ 2 of 3 elements within one training block (~13–15 laps); the default arithmetic is ~3–4 laps to broad qualification, ~3–4 at reduced salience, then the 3-lap probe.
- A *non-improver* never leaves full salience.
- Probe reversion triggers on simulated broad regression (qualified share dropping below 50%) within one lap of its onset, and the reversion cap prevents oscillation in the *erratic* learner type.

**Outputs.**
- Frozen controller configuration file (window sizes, thresholds, EVM, probe/reversion rules) — placed under version control; hash recorded.
- Feasibility figure: simulated fade trajectories by learner type (becomes a thesis figure).

**Gate G1.** All three design targets met; otherwise revise window/thresholds (or block length) and re-run.

---

## Phase 2 — Pilot (n = 2)

**Inputs.** Frozen controller config; full apparatus; session protocol scripts.

**Procedure.** Each pilot participant completes a compressed version of one full session sequence (abbreviated baseline, one training block per condition, short unassisted block). Pilots may fall outside the main recruitment criteria; their data are never pooled with the main sample. A specific purpose of the pilot is to **empirically justify and calibrate the EVM**, mirroring the empirical-observation approach of Bugeja et al. (2017).

**Outputs.**
- Distribution comparison: real novice per-corner metrics vs the synthetic streams from Phase 1.
- **EVM calibration:** real pilot per-metric variance compared against the AI baseline variance; the finalised EVM recorded in the controller configuration before the main study. If the finalised value differs from the 3.0 default, the Phase 1 simulation is re-run with the final value before Gate G2 closes.
- Controller event log audit: every fade event manually checked against raw telemetry for misfires.
- Protocol timing measurements (does the session fit the booked slot?).

**Gate G2.** (a) Real metric distributions fall within the envelope the simulation was tuned against, (b) zero unexplained controller transitions, (c) ≥ 1 fade event observed per pilot, (d) EVM finalised and the configuration re-frozen (with re-run simulation if the value changed). Any failure → recalibrate (return to Phase 1) before the main study.

---

## Phase 3 — Main study (n ≈ 15)

### Session 1 — Intake and baseline (~60 min)

**Inputs.** Consent form; pre-study questionnaire; both car-track pairs, no UI elements active.

**Procedure.** Consent → questionnaire (driving history, gaming/sim hours, league check against inclusion criteria) → seating/wheel calibration (settings logged) → per pair: 3 familiarisation laps (discarded) + laps until **5 valid baseline laps** are recorded.

**Outputs.** Participant record (moderators); apparatus calibration log; 5 valid baseline laps × 2 pairs (baseline covariate = mean valid baseline lap time per pair).

### Session 2 — Training (~75 min)

**Inputs.** Latin-square assignment; frozen controller config; per-corner reference table.

**Procedure.** Two training blocks of **30 minutes driving time** each (expected 13–15 laps on a ~2-minute circuit), one per pair, condition per the assigned sequence; 10-minute break between blocks. Adaptive blocks run the controller live; static blocks render all three elements at full salience. **NASA-TLX immediately after each block.**

**Outputs (per block).**
- Per-tick telemetry (shared-memory read, logged at 20 Hz minimum; fields: world position, speed, brake/throttle/steer inputs, gear, lap/sector markers, off-track flags).
- **Per-corner-pass records** — one row per corner pass (corner boundaries per the annotation files): corner id, lap, brake-initiation distance to reference point, brake-pressure modulation summary, minimum corner speed and envelope deviation, lateral distance at apex, validity flag, per-element criterion booleans, per-element corner qualification state, element-level controller stage.
- **Fade-event log** (adaptive blocks): timestamp, lap, element, transition type (full→reduced, reduced→probe, probe→removed, probe→revert, block-end probe-incomplete/censored), and the triggering quorum statistics (qualified share, which corners flipped).
- TLX scores × 2.

### Session 3 — Unassisted performance (~60 min)

**Inputs.** Both pairs, **no UI elements in either condition's block**. (Terminology note: this block is a retention / unassisted-performance test on the trained corners, deliberately *not* called "transfer"; transfer to novel corners or tracks is out of scope.)

**Procedure.** Per pair: 1 warm-up lap (discarded) + laps until **8 valid unassisted laps** are recorded. Then the confidence and perceived-dependence questionnaire, then a 10–15 minute semi-structured interview (audio recorded; guide covers workload, confidence, and awareness of fading — including whether the participant noticed elements disappearing and when).

**Outputs.** 8 valid unassisted laps × 2 pairs (per-tick + per-corner records); questionnaire scores; interview audio + notes.

### Optional retention probe (day 5–7, exploratory)

5 valid unassisted laps per pair for whichever participants return. Reported descriptively only; excluded from the primary model.

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

- **Model:** Bayesian mixed-effects regression. Unassisted lap time ~ condition + baseline lap time (per pair, standardised) + condition order + pair order + (1 + condition | participant) + (1 | pair) + (1 | corner-cluster where applicable). Secondary model with lap-time variability (per-participant SD of valid unassisted laps) as outcome.
- **Priors:** weakly informative — Normal(0, 1) on standardised coefficients, Exponential(1) on group-level SDs; stated in full in the methods chapter and frozen with the analysis scripts.
- **Output:** posterior distribution of the adaptive-minus-static difference with 95% credible interval, per pair and pooled; posterior predictive checks; order-term posteriors reported to document carryover handling. No significance language anywhere.

### RQ3 — Experience and alignment (thematic + alignment analysis)

- Thematic summary of interviews under predefined themes (workload, confidence, awareness of fading) plus emergent themes appearing in ≥ 3 participants. Single coder; full double-coded analysis explicitly out of scope.
- TLX compared descriptively between conditions per participant.
- **Alignment analysis:** for each participant, reported awareness of element disappearance is matched against the objective fade-event log (did they notice? when relative to the actual event?). Output: alignment table — the bridge between RQ3 and RQ1.

### Exclusion and missing-data rules (pre-committed)

- A participant is excluded entirely only for: failure to complete Session 3, discovered violation of inclusion criteria, or hardware failure corrupting > 30% of their data. Partial data otherwise retained and modelled (Bayesian models tolerate unbalanced data).
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
- Reference quality → Gate G0 with substitution fallback.
- Analysis flexibility → scripts and priors frozen before main data collection ends.
- Carryover → order terms in the model; reported, not assumed away.
