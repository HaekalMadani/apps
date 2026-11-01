## Decision

Which thesis direction should a master's/PhD-level CS/HCI thesis commit to, given a
novelty audit that has just narrowed its claims? Options A–F below. The author
writes the prose; the system is already built.

## The project (built, works in game)

TRACE is a real-time adaptive guidance system for novice sim racing in Assetto
Corsa.
- Three on-track visual cues per corner: brake-point marker, corner-speed readout,
  apex marker.
- Bandwidth knowledge-of-results (KR): a short error message, shown only when a
  pass falls outside the tolerance band.
- Each cue fades **per element**: full → reduced → **probe** (cue AND its KR
  hidden for 2 laps; the "guidance-off" test) → removed, or reverted one stage if
  performance drops.
- Decisions use a cross-corner quorum (2-of-3 recent passes per corner; ≥ 75% of
  the 4 corners qualified).
- The controller exists in both Lua (runtime) and Python (simulator), kept
  identical by a golden-trace parity suite.
- A synthetic-learner simulator gates the configuration. Gate G1 stated bounds:
  false fade for a non-improving learner ≤ 10% (measured 8.5% on pair 1), and
  removal despite regression ≤ 2% (measured 0%).

Study constraints:
- One ~33-minute sitting per participant: a 15-lap training block plus a 4-lap
  unassisted block.
- One car and one track (a second track was descoped).
- n ≈ 15 novices.
- No claims of statistical significance, learning benefit, or optimality.

## Framing v9 (current draft)

Adaptive guidance systems decide to remove a cue using performance measured
*with the cue on*. TRACE instead gates each fade on a cue-off probe.

- **RQ1:** within-session lap-to-lap reliability (ICC / SEM / MDC) of per-corner
  metrics for novices.
- **RQ2 (core):** how often does the guidance-off probe fail after guided
  qualification, and how much of that exceeds a **simulated noise-only null**? The
  null has no guidance dependency and is calibrated on the live data, so it
  separates guidance dependency from regression to the mean. Estimate
  Δ = P_obs − P_null.
  - Author decision: this is called **"guidance dependency"**, because cue and KR
    are withdrawn together during a probe.
- **RQ3:** Lua/Python parity and real-time performance.
- **RQ4 (secondary):** do sub-skills desynchronise?
- Contributions:
  1. the system;
  2. a reusable null-simulation method;
  3. the findings.

## What the novelty audit found (full texts read)

- **C1, "no system uses a cue-off probe as the fade decision": the idea is
  taken.**
  - Eneano et al. 2026 (SSRN preprint, not peer reviewed, laparoscopy) *propose*
    an unimplemented trial. It advances one level only when two unaided probes
    meet criteria, reinstates one level on deterioration, and argues that guided
    performance is "circular evidence of readiness".
  - ASSISTments ARRS (2012) implements an unaided retest-and-relearn loop between
    sessions, for math.
  - Kinesthetic-CPR (UIST 2026) fades on a schedule but restores a visual cue
    when cue-off performance degrades.
  - What survives: the first *implemented*, real-time, per-element version for
    concurrent visual cues in a motor task.
- **C2, premature-fade rates "never measured": narrowed.**
  - Measured elsewhere: ARRS, 18–41% wrong on the 1-week retest after a
    3-in-a-row mastery; Forza 4 (Debeauvais 2014), 38–80% of failed assist
    disables switched back on after the very next race; Pelánek & Řihák
    2017/18, simulated ground truth; Zhang/Baker EDM 2025.
  - Not measured for system-initiated withdrawal of motor visual cues, split into
    dependency vs variability.
- **C3, the calibrated noise-only null: survives.** This is the load-bearing
  novelty.
  - Pelánek's simulations use learning learners as ground truth, not a null.
  - Linden 2026 gives a closed-form regression-to-the-mean correction, for a
    single cutoff only.
  - TRACK 2026 (sim racing) calibrates clustering against a null, but not
    decisions.
- **C4, within-session reliability of sim-racing metrics: the gap is
  confirmed.**
  - Irwin 2019 used only t-tests and CV, on one corner, and found the corner
    metric unreliable (CV > 50%).
  - TRACK 2026 says outright that within-day repeatability, "the first rung",
    was never measured.
- **Nickl 2024** (*Learning and Instruction*): real-time adaptive scaffolding gave
  no benefit over non-adaptive. It argues for validating the *source of
  adaptation*. RQ2 can be framed this way.

## Feasibility, just measured in simulation (committed novice model, pair 1)

- **Probes per typical participant: 2.83**, i.e. ~42 pooled at n = 15, a 95% CI of
  about ±0.12. Per element ~16 / 15 / 11 events.
- **Noise-only probe-failure rate by element:**
  - corner speed **0.00** (the element that traverses most);
  - braking **0.16**;
  - apex **0.53** (the null swamps any dependency).
- **A per element × corner controller was priced and ruled out.** It gives 4×
  more probes, but 79% of non-improvers end with a cue faded and 5.5% have a cue
  removed despite regression, failing both bounds at every window tried.
  - Alternative: keep per-element decisions; analyse per corner (each probe gives
    8 cue-off corner passes).
- **A randomised probe-timing arm** (micro-randomised, which would validate the
  null causally) needs ~80 probes, i.e. ~28 participants. Not reachable.
- Only one novice-model parameter set is measured (apex). The brake and speed
  lap-to-lap sigmas are assumptions, and the corner-speed null of 0.00 depends
  entirely on the speed sigma.
- So far all real driving data comes from n = 1 (the researcher, who is not a
  representative novice).

## The options

- **A.** v9 as written, with wording repairs: C1 becomes "first implementation";
  cite Eneano / ARRS / Kinesthetic-CPR.
- **B (step-2 recommendation).** The same RQs re-ranked so the null method
  leads:
  - RQ1 becomes its calibration input (and fills TRACK's named gap);
  - RQ2 is framed through Nickl;
  - ARRS and Forza rates are cited as context only;
  - RQ4 is cut or moved to an appendix;
  - RQ3 becomes system-chapter evidence.
- **C.** B plus a no-participant extension: run the null simulator against
  published fade rules (Hsieh CHI'26 EMA-clamped ghost opacity; Shen's
  Cyber Racing Coach assisted-score rule; TRACE's quorum). This gives each
  rule's false-fade rate under a non-learner. Not yet novelty-searched. The rules
  are re-implemented from papers.
- **D.** Reliability-first: RQ1 as the thesis. Safe and cheap, but it orphans the
  controller.
- **E.** An adaptive-vs-scheduled withdrawal outcome trial (Eneano's proposal in
  the motor domain). Rejected: underpowered, and it implies learning claims.
- **F.** Self-initiated vs system-initiated cue removal. Parked; the
  self-controlled-feedback literature has not been searched.

## What's at stake

The author already lost one direction (v6) to a late discovery that it was "too
common in learning science". A wrong pick now costs months, and the data
collection is a single sitting per participant that cannot be re-run on the same
person.
