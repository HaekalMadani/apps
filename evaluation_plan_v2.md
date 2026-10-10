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
| Design | Within-subjects, 2 conditions × 2 car-track pairs |
| Conditions | **Adaptive** (fading controller active) vs **Static** (all three UI elements at full salience throughout training) |
| Counterbalancing | 2×2 crossover, counterbalanced over the full factorial of pair order × condition coupling (4 sequences) |
| Sample | n ≈ 15 main participants + 2 pilot participants (not pooled) |
| Sessions | 3 per participant (+ optional exploratory retention probe, day 5–7) |
| Framing | Systems-and-characterisation study; effect sizes with credible intervals, no confirmatory claims |

**Crossover sequences** (participants assigned round-robin at enrolment; note this is the full set of four sequences, not a Latin square — the earlier label was incorrect):

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

**Procedure.** Before any reference laps are processed, each track is **manually annotated**: a version-controlled file per track defines corner IDs, entry/exit gates as normalized track-spline positions, corner-type tags, and per-element evaluation zones (braking zone, apex window — a spline window centred on the apex gate, half-width recorded per corner — and corner-speed zone). Compound sections — chicanes or linked corners sharing a single braking event — are annotated explicitly as compound corners (one braking zone, multiple apex windows where appropriate). All downstream per-corner processing — reference extraction, marker placement, runtime evidence — consumes this file. Then run the AI at 95–100% strength for 12 laps per pair under the fixed setup, logging per-tick telemetry through the same pipeline participants will use (autopilot on the *player* car, so reference laps share the participant's car and setup; the manifest records `autopilot` and `ai_level_pct`). A human validation step was planned — 12 laps per pair from one experienced sim racer, with a per-corner comparison of AI versus human brake points, apex lines and speed envelopes, substituting the human reference wherever the AI diverged materially. **It was not carried out: no experienced sim racer was available, and a beginner-recorded reference would be a *novice* reference, not a weaker expert one — substituting it would drag the target toward novice performance and defeat the intervention.** The reference is therefore AI-sourced at every corner (`source: "ai"` throughout; `EVM_human` goes unused), and the absence of the human bound is carried as a stated limitation into Gate G2 and the methods chapter. The comparison-and-substitution tooling is built and tested, so the step is a re-run if an experienced driver becomes available before the main study.

**Outputs.**
- **Corner annotation files** (one per track, version-controlled): corner IDs, spline-position gates, type tags, per-element evaluation zones; published with the dataset.
- `reference_laps/` — per-tick telemetry, 12 AI laps + 12 human validation laps × 2 pairs.
- **Per-corner reference table** (one row per annotated corner per pair): brake-initiation world coordinate, apex world coordinate, minimum-corner-speed envelope (mean ± band), apex lateral-line band, and the source of each corner's reference (AI or human-substituted).
- ~~**AI-vs-human validation report**~~: not produced — see the procedure above. The tooling (`trace_kit.reference compare`) remains available; its absence is recorded as a limitation, not silently dropped.
- Reference quality report: lap-time coefficient of variation across the 12 laps, plus the per-corner count of contributing laps.

**Gate G0** (restated, since the AI-vs-human clause can no longer be met). Annotation files reviewed against a driven lap (every gate and evaluation zone visually checked on track); reference lap-time CoV < 1% per pair; visually sane lines in all corners, confirmed by standing the extracted markers on track and checking each sits where a competent driver would brake and apex; every corner contributing at least the extractor's minimum lap count; and the **absence of human validation recorded as a limitation** in the dataset README and the methods chapter. Otherwise re-annotate or re-record before proceeding.

Because the human bound is gone, **Gate G2 absorbs the work it would have done**: the pilot is now the only empirical check that the reference is reachable by real novices. A G2 failure here means recalibrating the band floors (and, if that is not enough, revisiting the car choice), not merely tuning the EVM — the AI's σ is far below the floors, so the floors, not the multiplier, set every band.

---

## Phase 1 — Threshold calibration by simulation

**Inputs.** Per-corner reference table (Phase 0); state-machine implementation; assumed novice behaviour model (initial offset and variance per metric, learning-rate range, lap-to-lap noise — parameters documented in the simulation script).

**Procedure.** Generate ≥ 1,000 synthetic participant streams across a grid of learner types (fast improver, slow improver, non-improver, erratic, **staggered regressor** — regression onset spread across corners over several laps, since real regression is not synchronised). Run each stream through the controller. Tune the controller parameters and per-metric tolerance bands until the design targets below hold. Defaults under tune: per-corner qualification window (**3 of last 4 passes**), de-qualification rule (**2 consecutive failures**), element-level quorum (advance at **≥ 75%** of applicable corners qualified, revert below **50%**), probe length (**3 laps**), reversion cap (**2 cycles per element per block**), per-pass **consistency delta** for the braking criterion (default **0.5 × accuracy band**), and per-metric **band floors**. The **re-qualification-on-advance rule** (all corner qualification states reset on every stage advance; see Framing v6) is a fixed structural rule, not a tuned parameter, and the simulation must run with it active.

**Expertise Variance Multiplier (EVM).** Tolerance bands are defined as `band_m = max(σ_ref,m × EVM_source, floor_m)`, where `σ_ref,m` is the reference laps' standard deviation for metric *m*. The multiplier exists because the AI reference lacks the inherent motor noise that persists even in expert human performance (Cohen & Sternad, 2009); bands taken from raw AI variance would be impossibly narrow for any human driver. Two structural guards: the **absolute per-metric floor** prevents the band being hostage to a near-zero baseline (the AI is consistent by construction, so σ_ref can be arbitrarily small at some corners), and the multiplier is **source-dependent** — **EVM_AI, provisional default 3.0**, for AI-sourced corners; **EVM_human, provisional default 1.25**, for human-substituted corners, whose σ_ref already contains human motor variability and would otherwise be inflated twice. Both multipliers and the floors are explicitly named free parameters of the controller configuration — the precedent is the named, empirically set `tolerance` parameters in Bugeja et al. (2017) — and their final values are fixed in Phase 2. EVM_AI = 3.0 is used to generate the synthetic learner streams.

**Design targets.**
- A *typical improver* fully traverses the machine (full → reduced → probe → removed) for ≥ 2 of 3 elements within one training block (~13–15 laps); the default arithmetic is ~3–4 laps to broad qualification at full salience, ~3–4 laps to *re-qualify* at reduced salience (the dwell enforced by the re-qualification rule), then the 3-lap probe.
- A *non-improver* never leaves full salience.
- Probe reversion triggers on simulated broad regression (qualified share dropping below 50%) **at the earliest lap the evidence can support it, plus at most one lap**, and broad regression is **never answered by removal**. The staggered-regressor stream exists to keep the simulation honest about this, and the reversion cap must still prevent oscillation in the *erratic* learner type.

  *[amended 2026-09-09]* This target previously read "within **one lap of onset when regression is synchronised across corners, and within two laps when it is staggered**". The two-lap staggered figure is **not reachable by any threshold setting**, and the simulation found it immediately. Reversion latency has a floor set by two rules acting together: a corner cannot de-qualify before its second consecutive failure, and the element cannot revert until *enough corners have de-qualified to put the qualified share below the threshold* — which, for onsets one lap apart across four corners, is not the first corner's onset but the **third**. The measured median lag from the first onset is therefore 3 laps, and no configuration in the 144-candidate sweep changed that. Measuring instead against the arithmetic floor separates the part the controller is responsible for from the part the design's own rules fix in advance; it is met at **zero excess** for both synchronised and staggered streams, and it collapses to the original one-lap figure exactly when regression is synchronised. The added "never answered by removal" clause is the safety property the latency was always a proxy for: a late reversion costs a lap of unscaffolded driving, whereas a removal costs the rest of the block. It is read strictly (0 tolerated failures) and counts only removals occurring once the regression could already have been detected — an element removed before that point was removed on evidence that was still good, and block-scoped permanence then correctly keeps it removed.

**Outputs.** *[all produced 2026-09-08; see `configs/simulation/G1_REVIEW.md`]*
- Frozen controller configuration file (window sizes, thresholds, EVM_AI/EVM_human, band floors, consistency delta, probe/reversion rules, re-qualification rule flag) — placed under version control; hash recorded. → `configs/controller_config.json`, `config_id: frozen-g1`, SHA-256 `c10fadc8ad8518902d4a7e3db1a581afbc003598a95fd47d0d07dbf30b345650`.
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

**Procedure.** Each pilot participant completes a compressed version of one full session sequence (abbreviated baseline, one training block per condition, short unassisted block). Pilots may fall outside the main recruitment criteria; their data are never pooled with the main sample. A specific purpose of the pilot is to **empirically justify and calibrate both EVM multipliers and the band floors**, mirroring the empirical-observation approach of Bugeja et al. (2017).

**Outputs.**
- Distribution comparison: real novice per-corner metrics vs the synthetic streams from Phase 1.
- **EVM calibration:** real pilot per-metric variance compared against the AI baseline variance (and against the human-reference variance for substituted corners); the finalised EVM_AI, EVM_human, and floors recorded in the controller configuration before the main study. If any finalised value differs from its default, the Phase 1 simulation is re-run with the final values before Gate G2 closes.
- Controller event log audit: every fade event manually checked against raw telemetry for misfires.
- Protocol timing measurements (does the session fit the booked slot?).

**Gate G2.** (a) Real metric distributions fall within the envelope the simulation was tuned against, (b) zero unexplained controller transitions, (c) ≥ 1 fade event observed per pilot, (d) EVM_AI, EVM_human, and floors finalised and the configuration re-frozen (with re-run simulation if any value changed). Any failure → recalibrate (return to Phase 1) before the main study.

---

## Phase 3 — Main study (n ≈ 15)

### Session 1 — Intake and baseline (~60 min)

**Inputs.** Consent form; pre-study questionnaire; both car-track pairs, no UI elements active.

**Procedure.** Consent → questionnaire (driving history, gaming/sim hours, league check against inclusion criteria) → seating/wheel calibration (settings logged) → per pair: 3 familiarisation laps (discarded) + laps until **5 valid baseline laps** are recorded.

**Outputs.** Participant record (moderators); apparatus calibration log; 5 valid baseline laps × 2 pairs (baseline covariate = mean valid baseline lap time per pair).

### Session 2 — Training (~75 min)

**Inputs.** Crossover sequence assignment; frozen controller config; per-corner reference table.

**Procedure.** Two training blocks of **30 minutes driving time** each (expected 13–15 laps on a ~2-minute circuit), one per pair, condition per the assigned sequence; 10-minute break between blocks. Adaptive blocks run the controller live; static blocks render all three elements at full salience. **NASA-TLX immediately after each block.**

**Outputs (per block).**
- Per-tick telemetry (shared-memory read, logged at 20 Hz minimum; fields: world position, speed, brake/throttle/steer inputs, gear, lap/sector markers, off-track flags).
- **Per-corner-pass records** — one row per corner pass (corner boundaries per the annotation files): corner id, lap, brake-initiation distance to reference point, distance to the corner's rolling brake-initiation mean (the consistency-gate input), brake-pressure modulation summary (descriptive, not gated), minimum corner speed and envelope deviation, RMS lateral deviation over the apex window, validity flag, per-element per-pass criterion booleans (accuracy and consistency gates separately for braking), per-element corner qualification state, element-level controller stage.
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

- **Model:** Bayesian mixed-effects regression on lap-level observations; condition is *crossed* with participant (the earlier "lap nested in condition nested in participant" description was incorrect). Unassisted lap time ~ condition + baseline lap time (per pair, standardised) + **pair (fixed effect — two levels cannot support a group-level variance estimate, so the earlier `(1 | pair)` term is removed)** + condition order + pair order + (1 + condition | participant). The earlier `(1 | corner-cluster)` term is removed as undefined for a lap-time outcome; corner-level structure belongs to the secondary sector-level analyses, not the primary model. Secondary model with lap-time variability (per-participant SD of valid unassisted laps) as outcome.
- **Priors:** weakly informative — Normal(0, 1) on standardised coefficients, Exponential(1) on group-level SDs; stated in full in the methods chapter and frozen with the analysis scripts.
- **Known confound, stated:** both training blocks share a session, so the order terms absorb mean fatigue, but a fatigue × condition interaction is unidentifiable at n ≈ 15; it is reported as a limitation, not modelled.
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
- Reference quality → Gate G0. The human-substitution fallback is **no longer available** (Phase 0); the residual risk that the AI reference is unreachable by novices is carried to Gate G2, where the band floors are calibrated against real pilot distributions.
- Analysis flexibility → scripts and priors frozen before main data collection ends.
- Carryover → order terms in the model; reported, not assumed away.
- Recruitment / scheduling shortfall (the realistic long pole: ~45+ booked sessions) → **pre-committed degraded fallback, recorded now so a crisis becomes a documented contingency rather than an improvised one**: first drop the optional retention probe; then accept n = 10 as the minimum main sample (the Bayesian estimation framing degrades gracefully — intervals widen, the design does not break); the within-subjects structure and all gates are retained at every fallback level. Any invocation of the fallback is logged with date and reason in the dataset README.
