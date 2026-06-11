# Thesis Framing Document

**Working title:** Telemetry-Driven Adaptive UI Fading for Novice Sim Racing: A Systems Study

---

## Core contribution (one sentence)

This thesis builds and characterises a system that uses real-time driving telemetry from Assetto Corsa to decide when each piece of informational UI assistance should be faded out for a novice player, and reports how that system behaves in practice with a small group of novice drivers.

## Motivation

When novices learn a complex perceptual-motor task in a simulator — driving, flying, surgical training, teleoperation — informational UI overlays are often used to scaffold performance. A common question for designers is when and how to remove that scaffolding so the learner internalises the skill rather than depending on the overlay. In practice, withdrawal is usually binary and is decided by a trainer or by the learner. There is little work on having the system itself decide, from observed performance, when a specific piece of assistance is ready to be withdrawn for a specific learner.

The thesis investigates one approach to this question in one setting. Sim racing in Assetto Corsa is chosen because it offers detailed real-time telemetry through a documented interface, supports custom in-game UI through a plugin API, and involves a continuous perceptual-motor task with low ethical and physical risk. Whether the approach transfers to other domains is a question the thesis can motivate but cannot answer.

## Theoretical grounding

Three established ideas motivate the design.

**Cognitive load theory** suggests that informational overlays reduce extraneous load early in learning, but that persistent overlays can prevent the learner from forming the internal schemas that fluent performance depends on. Scaffolding should be present while load on the underlying skill is high and removed as schemas form.

**Scaffolding theory** (the Zone of Proximal Development and its later operationalisations) holds that support should be calibrated to current competence: present when the task is beyond independent capability, withdrawn as competence grows. The original formulation assumes a human tutor making the judgement. The thesis treats telemetry-derived competency assessment as a computational substitute for that judgement.

**Expertise research in driving and related perceptual-motor domains** shows a more nuanced picture than experts simply disengaging from visual cues. In real-world driving, expertise is linked to more efficient gaze behaviour and greater reliance on internalised anticipatory models. In sim racing specifically, however, Joyce et al. (2024) found the opposite of disengagement from the display: higher-skilled racers allocated relatively less overt attention to the track and proportionally more to heads-up display features than lower-skilled racers, who fixated more heavily on the track itself. Experts therefore appear to extract more, not less, from explicit display elements while driving at speed. The implication for fading is narrower than removing visual information wholesale: what should fade is the instructional scaffolding that substitutes for a skill not yet internalised — braking markers, a racing line — rather than the telemetry that experts continue to depend on. Fading aims to encourage formation of the internal model the scaffold previously stood in for, not to strip away all on-screen information.

Taken together, these ideas motivate — but do not guarantee — a prediction: that scaffolding withdrawn contingently on demonstrated competence should support transfer better than scaffolding that is always present or never present. This prediction is not a settled consequence of scaffolding theory. The empirical record comparing fixed (always-on) and faded scaffolds is genuinely mixed: several studies report that fixed, sustained scaffolds yield better problem-solving and transfer outcomes than faded ones (Lee & Songer, 2004; Bulu & Pedersen, 2010; Jaakkola & Veermans, 2018; Tawfik et al., 2018), and a recent study of real-time adaptive scaffolding (Nickl et al., 2024) found no advantage for adaptive scaffolding over static or absent scaffolding. The direction of the effect is therefore an open empirical question rather than a logical certainty — which is what makes the comparison in RQ2 worth running. The theory also does not specify how contingency should be computed. The thesis contributes one mechanism — a multi-stage state machine with probe-and-revert behaviour — and characterises how it behaves with novice users. This design is also a direct response to a documented failure mode in prior sim-racing interventions: a telemetry-based real-time feedback system for novice drivers in Assetto Corsa (Bugeja et al., 2017) improved performance during training, but the gains dissipated as soon as the feedback was switched off — a lack of cognitive retention when drivers had to perform unassisted. Probe-and-revert fading, which withdraws assistance gradually and restores it if performance degrades, is intended as a solution to exactly that collapse rather than a re-enactment of it.

## Related work and the engineering problem

Separated from the learning-science questions, the systems contribution addresses a single engineering problem: to build a controller that, in real time and independently for each UI element, infers from continuous driving telemetry whether a learner has internalised the skill a given piece of informational scaffolding stands in for, and then withdraws that scaffolding reversibly — restoring it if performance regresses — using an inspectable rule set rather than a learned policy. Prior work addresses every component of this but does not assemble them in this form.

**Telemetry-based coaching in sim racing** establishes both the need for fading and the metrics to drive it. Bugeja et al. (2017) built a telemetry-driven feedback system for Assetto Corsa and found that novice gains dissipated the moment feedback was disabled, attributing this to a lack of cognitive retention — the failure mode that motivates gradual, reversible withdrawal over a binary switch. Hojaji et al. applied machine learning to Assetto Corsa telemetry and identified the behaviours that separate fast from slow racers — trail braking, throttle-release timing, steering stability — which grounds the use of telemetry-derived competency metrics, most directly the braking-related ones. Joyce et al. (2024) showed through eye tracking that higher-skilled racers allocate proportionally less attention to the track and more to HUD elements, supporting the treatment of instructional track overlays and persistent HUD telemetry as distinct fading targets rather than a single class.

**Performance-contingent assistance** supplies the mechanical precedent for an assessment loop that drives the interface. Faber et al. built a medical-emergency simulator that toggled scaffolding from continuous interaction traces, enabling a supportive checklist when a systematicity score fell below a set threshold and surfacing procedural dialogs on tool warnings — performance-triggered support with no human in the loop. Ma et al. adapted AR-HUD driving warnings continuously from real-time vehicle kinematics using Ecological Interface Design, mapping interface changes onto skill-, rule-, and knowledge-based behaviour. Both adapt UI from system-assessed behaviour; neither withdraws scaffolding on demonstrated competence, and neither reverts.

**Automated fading in education and intelligent tutoring** is the theory-to-systems lineage and the closest analogue to the staged controller used here. Zhang et al. implemented a three-stage fade-out — selective prompts, then gap-filling, then questioning — that parallels the full-salience, reduced-form, probe-withdrawal stages. Gidalevich & Kramarski found a graduated-reduction (faded) model produced better long-term retention and autonomy than fixed scaffolding, which sits opposite the fixed-favouring findings noted under theoretical grounding and places the direction of the effect in genuine dispute — the dispute RQ2 examines. These systems all operate over discrete, problem-based interactions; none addresses a continuous perceptual-motor task.

**The choice of a discrete, inspectable state machine** over a learned policy has direct support. Chrysafiadi et al. built a rule-based adaptation mechanism and justified avoiding machine learning on the grounds that such techniques demand large training data and learning time that real-time, individual adaptation cannot supply — the same constraint that rules out a learned controller for this task and population. The same work argues against leaving withdrawal to the user, since learners are poor judges of the challenge level matching their ability; this favours automating withdrawal from objective telemetry over self-report. That concern is adjacent to dynamic difficulty adjustment, which shares the goal of avoiding overload and frustration but adjusts game challenge rather than instructional scaffolding.

**The gap:** each component exists in isolation — contingent withdrawal, continuous telemetry assessment, staged fading, rule-based adaptation, telemetry coaching in racing — but no prior system combines per-element, telemetry-derived, performance-contingent withdrawal of informational UI with reversible probe-and-revert behaviour in a continuous perceptual-motor task. The contribution is the integration and the reversibility, not any single part.

## Research questions

**RQ1.** How does the fading state machine behave when used by novice players, and what fade trajectories does it produce across individuals and across UI elements?

**RQ2.** How does adaptive fading compare to static (always-on) UI assistance in shaping learning during training and in unassisted performance afterwards?

**RQ3.** How do players experience the fading process — workload, confidence, awareness of changes — and how do those experiences line up with the objective fade events the system records?

RQ1 treats the system as a contribution in its own right. RQ2 provides effect-size estimates with credible intervals, not significance tests. RQ3 connects objective system behaviour to learner experience.

## Evaluation constraints (stated up front)

The realistic participant pool is approximately 15 people. The study uses a within-subjects design with two conditions on two different car-track pairs, counterbalanced via a Latin square. This is the maximum statistical leverage the sample size will support, and it is still not enough for confirmatory between-condition tests.

The within-subjects design also carries a known cost: the skills being trained — braking discipline, apex awareness, corner-speed control — are largely track-general for novices, so generic improvement carries over into whichever car-track pair a participant drives second, regardless of condition. This is in tension with the thesis's own premise that these skills transfer. The Latin square balances order in expectation, but at n≈15 the imbalance in any individual cell is real and is not fully absorbed by a baseline covariate. The design therefore trades participant efficiency for condition contamination; the analysis models order explicitly rather than assuming it away (see Analysis), and the limitation is reported rather than hidden.

The thesis therefore frames itself as a **systems-and-characterisation study**:

- It can describe how the mechanism behaves in practice and produce per-participant trajectories.
- It can produce effect-size estimates with credible intervals for future powered work.
- It cannot make confirmatory claims that adaptive fading outperforms static assistance, and it does not try to.

This constraint is stated here rather than buried later because it shapes every downstream choice in the methodology.

## The system

The system has three loosely coupled parts: a telemetry-ingestion layer reading Assetto Corsa's shared-memory interface, a competency-assessment and fading-controller layer, and an in-game UI rendering layer.

### UI elements (three, deliberately scoped down)

- A world-anchored braking-point marker, projected onto the track surface at the expert braking point for each corner.
- A corner-speed indicator in the HUD.
- A world-anchored apex marker, projected onto the track at each corner's apex.

A dynamic racing line, a gear-shift indicator, and the delta-time bar carried in an earlier version of this design were considered and dropped. The racing line because rendering a continuously camera-tracking world-anchored line — hundreds of connected points redrawn every frame — is the most complex piece of UI work in the project, and its contribution overlaps with the braking-point and apex markers; the gear-shift indicator because it offers limited learning signal at the chosen vehicle and track difficulty; the delta-time bar because it is an expert feedback instrument rather than a scaffold a novice internalises and then sheds, which makes it a poor fit for a fading study. The braking-point and apex markers are world-anchored but discrete — each is a single projected point, not a continuous line — which keeps their rendering cheap where the racing line was not.

### World-anchored rendering (de-risked by a technical spike — resolved)

World-anchored rendering was the project's highest technical risk, because two of the three UI elements depend on it. It was therefore built first, as a throwaway spike, before any study infrastructure. **The spike passed**, but it overturned the rendering approach this document originally assumed, so the design is recorded here in its corrected form.

**What the spike disproved.** The original design assumed Assetto Corsa's legacy Python app API exposed a usable world-to-screen camera transform that could be read each frame and used to project a marker's world coordinate to screen pixels by hand. This is false. Stock AC Python has no such transform — it was a never-shipped feature request. The Custom Shaders Patch (CSP) extension does expose the camera matrices to Python, but the bindings proved fragile: matrices arrive column-major (transposed from the textbook layout), and under AC's bundled Python 3.3 the matrix elements are a custom numeric type whose `__float__` and `__repr__` raise on a single element, so the only reliable extraction was to `repr()` the whole tuple and parse the numbers back out. Worse, even when working, the Python path is a depth-less 2D overlay: it draws over intervening geometry and has to be manually culled once its world point passes behind the camera, and it can never be correctly occluded by hills, walls, or track furniture.

**What the spike adopted.** The marker is instead drawn with CSP's **Lua `render` API**, which draws primitives directly in 3D world space. World coordinates are handed to the engine, which projects them with the real scene camera during the transparent render pass. This inverts every Python problem at once:

- **No camera transform to fetch, parse, or transpose** — projection is engine-side.
- **Frame-staleness is impossible by construction** — the marker is drawn from the same camera, in the same pass, as the scene itself, so the "no lag to accumulate" property is now a structural guarantee rather than a hopeful prediction.
- **Lock at speed holds** — confirmed driving at a fixed anchor at 200+ km/h and swerving through it; the marker stays glued to its world point because it is part of the same render.
- **Depth testing and occlusion are free** — `render.setDepthMode(Normal)` gives true depth-buffered drawing, so markers are correctly hidden behind geometry with no manual culling. The depth-less-overlay limitation noted in the original design is gone, with no material override or extra toolchain.
- **Per-frame cost is negligible** — a handful of `render.*` calls per marker.

**The design consequence.** World-anchored rendering is implemented as a **CSP Lua app, and CSP is therefore a documented dependency of the study apparatus.** The thesis contribution — the *fading* of the cue — is unaffected by this change and lives in the same layer: fading is implemented by modulating the marker's `rgbm` alpha (and optionally its radius) as a function of the controller's stage, and the rendering call is identical whether the marker is at full salience, reduced salience, or withdrawn. The original design principle — keep the *rendering* swappable and the *fading* independent of it — is what made the Python-to-Lua swap cheap, and it still holds. Each marker's world position is precomputed once per corner from the expert reference (see Method); at run time the controller only sets alpha.

### The fading mechanism

For each UI element independently, a three-stage state machine: full salience → reduced salience (lower opacity or simpler form) → probe withdrawal (element removed, with reversion if performance degrades, or permanent removal if it holds).

**Evaluation is per corner-pass, not per lap.** An earlier version of this design gated each stage transition on the competency criterion being met across three *consecutive laps*. This was abandoned for two reasons: a mid-length circuit yields only one evidence event per lap, so a full traversal of the machine would need roughly nine-plus clean laps per element — likely more laps than a novice completes in a training block — and a single bad pass resets the whole consecutive-lap count to zero, which is far too brittle for noisy novice driving. Instead, each corner is an evidence event, and a stage transition fires when the element's criterion is satisfied in **8 of the last 10 passes** of the relevant corner (a rolling window). A mid-length circuit has 10–15 corners, so a single lap now generates 10–15 evidence events rather than one, and an isolated mistake degrades the rolling proportion instead of erasing accumulated evidence. The rule remains conservative on purpose — premature withdrawal is more harmful than delayed withdrawal — but it is now conservative in a way a real training block can actually satisfy.

**Lap-budget feasibility is checked by simulation before any participant is run.** A small simulation generates synthetic novice metric streams (noisy early, improving along a plausible learning curve, with lap-to-lap noise) and runs them through the state machine. The window size and thresholds are tuned so that a *typical improving novice* traverses the full machine within a realistic training block while a *non-improving novice* does not. This serves two purposes: it confirms the lap budget closes before any participant time is spent, and the resulting figure documents that the controller's behaviour is designed rather than accidental.

### Competency metrics

Each element has one or more telemetry-derived metrics targeting the skill it scaffolds, all defined relative to an expert reference built from multiple recorded laps (a tolerance band, not a point target):

- **Braking-point marker — a two-gate criterion.** The marker fades only when both an *accuracy* gate and a *consistency* gate are satisfied over the rolling window: mean brake-initiation distance within a tolerance band of the expert braking point (accuracy), **and** variance in brake-initiation distance below threshold (consistency), supported by brake-pressure modulation. Consistency alone is insufficient on purpose — a learner who brakes reliably 30 m too early is consistent but wrong, and a consistency-only gate would withdraw the marker from exactly the person who has internalised the *wrong* braking point. Requiring accuracy *and* consistency makes the fade certify "has internalised the correct braking point," which is the claim the withdrawal is supposed to stand for.
- **Corner-speed indicator** — minimum corner-speed deviation from the expert speed envelope.
- **Apex marker** — lateral distance from the expert apex line through the corner.

The metrics are kept deliberately distinct — longitudinal control for the braking point, a target value for corner speed, lateral path accuracy for the apex — so the three elements can in principle fade on independent trajectories rather than moving together.

### Why a discrete state machine rather than a learned policy

Training a continuous probabilistic controller (MDP, POMDP, knowledge tracing) would require data that doesn't exist for this task and population. A discrete state machine is also inspectable, which matters because the design choices themselves are part of the contribution; a learned policy would hide them.

## Method summary

**Participants.** Approximately 15 novice sim racers (under 20 hours of sim racing across any title, no league participation). Pre-study questionnaire records driving history and game experience as potential moderators.

**Expert reference.** The competency thresholds and the markers' world coordinates are both derived from a **competent, consistent reference — not an optimal one.** The reference is built from the Assetto Corsa AI driver run at 95–100% strength for 10–15 laps on each car-track pair, in the same fixed setup participants use, logged through the study's own telemetry pipeline. This choice is deliberate: public internet hotlaps are alien-tier laps on unknown, optimised setups, so tolerance bands anchored to them would never admit a novice and nothing would ever fade; they also typically provide a single lap, which cannot supply the variance estimate a tolerance band needs. The AI reference is reproducible, fully documented ("AC AI, strength X%, n laps, fixed setup"), consistent by construction across multiple laps, and the AI line conveniently also supplies the per-corner world coordinates for the markers. Logging it doubles as an end-to-end test of the telemetry pipeline. If the AI's line is unrealistic in a particular corner, it is supplemented with laps from one experienced sim racer driving the same fixed setup — an evening's work, and explicitly *not* a study participant, so it does not consume the pool of 15.

**Pilot.** With the simulation and the AI-derived reference in place, the pilot's job shrinks to a sanity check: confirm that real novice telemetry behaves roughly like the synthetic streams the thresholds were tuned against, and catch gross calibration errors before the main run. Two pilot participants, one session each; they may fall outside the main recruitment criteria if needed, and are not counted in the main sample.

**Apparatus.** Fixed force-feedback wheel, pedals with load-cell brake, fixed display, identical seating across participants. Custom Shaders Patch is a required software dependency of the rendering layer (see World-anchored rendering) and is held at a fixed version across all participants.

**Cars and tracks.** Two car-track pairs of moderate handling complexity (road or touring cars on mid-length circuits with varied corner types). Distinct enough to limit skill carryover between them, similar enough that the same UI elements and metrics apply. Residual carryover is expected and is handled in analysis rather than assumed away.

**Sessions.** Three sessions per participant. Session 1: familiarisation and baseline laps on both pairs. Session 2: training under both conditions on both pairs (Latin-square assignment of condition order and pair order). Session 3: unassisted transfer block on both pairs. Optional retention probe 5–7 days later where availability permits — treated as exploratory, since it will likely yield too few participants to report as a primary result.

**Outcome measures.**

- *Primary (RQ2):* mean transfer lap time and lap-time variability in unassisted transfer.
- *System behaviour (RQ1):* per-participant fade-event timelines, probe-withdrawal outcomes per element, distribution of fade timings across participants.
- *Secondary:* sector-level performance, input smoothness, off-track count, retention performance.
- *Subjective (RQ3):* NASA-TLX after each training block, a brief confidence and perceived-dependence questionnaire, and a short semi-structured interview at the end of session 3.

**Analysis.**

- *RQ1:* descriptive presentation of per-participant fade trajectories. Aggregate patterns shown as distributions rather than as group means. Atypical cases reported individually.
- *RQ2:* Bayesian mixed-effects model with lap nested in condition nested in participant, baseline lap time as a covariate, and **condition order and pair order included as fixed effects** to absorb the carryover the within-subjects design introduces. At n≈15 the posteriors on the order terms will be wide; including them nonetheless shows the confound was modelled rather than ignored. Posterior distributions over the adaptive-versus-static difference are reported with credible intervals. Priors are stated in the methods chapter.
- *RQ3:* thematic summary of interview content, organised by predefined themes (workload, confidence, awareness of fading) plus any themes that emerge clearly across participants. Full formal thematic analysis with double coding is out of scope; the qualitative arm provides triangulation, not standalone qualitative results.

## Deliverables

- The working system: telemetry pipeline, competency-assessment and fading controller, three in-game UI overlays (CSP Lua rendering layer), logging infrastructure.
- A characterisation dataset with per-tick telemetry, lap summaries, fade events, and questionnaire responses.
- Per-participant learning trajectories (RQ1), effect-size estimates with credible intervals for the comparison (RQ2), and a thematic summary of participant experiences (RQ3).
- The written thesis, with a focused literature review, system documentation, evaluation results, and a discussion of design implications and limitations.

## What this thesis will not claim

- That adaptive telemetry-driven fading produces statistically significant improvements over static assistance.
- That findings generalise beyond the cars, tracks, and population tested.
- That the chosen thresholds, fade schedule, or UI choices are optimal.
- That the system is validated. The evaluation characterises behaviour; validation in a strong sense needs a future powered study.

---

*One main idea: telemetry-driven, reversible UI fading. Everything else serves that.*

*The system is a first-class contribution. Document the design decisions as carefully as the results.*

*Per-participant trajectories matter more than group means at this sample size.*

*A working system on three UI elements is better than a half-working system on five. Resist scope creep.*

*Re-read this document before writing each chapter. Drift toward overclaiming and toward sprawl is the most likely failure mode.*
