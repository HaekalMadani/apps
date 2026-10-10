# CLAUDE.md

Guidance for working in this repository. Read this before writing code.

## What this is

The implementation for a thesis: **telemetry-driven adaptive UI fading for novice
sim racing in Assetto Corsa**. The system reads real-time driving telemetry and
decides, independently for each piece of informational UI, when to fade that
scaffold out for a learner — and restores it if performance regresses
(probe-and-revert). The **system and its design decisions are a first-class
contribution**, not just plumbing for a study.

Full framing lives in `thesis_framing_v6.md` in this `apps/` folder, alongside
`implementation_plan_v2.md` and `evaluation_plan_v2.md`. Re-read them before each
chunk of work — drift toward overclaiming and toward sprawl is the documented #1
failure mode.

## Roadmap & progress (TRACE)

Build order from `implementation_plan_v2.md` §4 (full detail there — don't
duplicate it here). **Standing rule: update this section whenever a milestone's
status changes; never start Mn+1 before Mn's exit test passes.**

- [x] **M0 — Skeleton** · *done 2026-06-11 (parity suite green — 54 tests;
  trace_rt config-status window verified in-game: PASS for valid configs, FAIL
  on a broken `mode` field)*
  Exit: configs round-trip through validation in both Lua and Python. ✓
- [x] **M1 — Sampler + logger** · *done 2026-06-15 (full 30-min solo drive
  verified: block `1_s2_2_adaptive_20260615_170641` — 36,300 rows, exact
  20.0000 Hz, gap-free (worst gap 0.05 s = one tick), 25 laps reconciling,
  integrity checker PASS, SHA-256 config hashes + manifest valid).* Outputs land
  in `<Documents>/Assetto Corsa/trace_data/` (Documents may be OneDrive-
  redirected; the app prints the resolved path to `py_log.txt` on Start).
  Exit: 30-min solo drive → gap-free logs, integrity checker passes, no frame
  cost. ✓ (Includes SHA-256 config hashing into the session manifest.)
- [x] **M2 — Annotation + pass tracking** · *done 2026-09-07 (99 headless
  tests; in-game exit test PASSED on both layouts — International block
  `1_s1_1_adaptive_20260907_153248`, National block
  `1_s2_1_adaptive_20260907_154852`: exactly one pass per corner per lap,
  off-track corners `valid=false ['wheels_outside','wall_contact']` while other
  corners on the same lap stayed valid, a pass open at block end closed
  `['incomplete']`; correct per-track annotation hashes; integrity checker PASS
  on all blocks).*
  Exit: one pass per annotated corner per lap, correct validity flags, both
  tracks. ✓
  Pieces: `lua/trace_rt/lib/{pass_tracker,pass_record,annotator}.lua`,
  `kit/trace_kit/annotate.py`, annotate mode in `trace_rt.lua`.

  **Decisions from M2 that bind later work:**
  - **Tracks (2026-09-07):** both pairs are Silverstone layouts —
    `ks_silverstone` layout `national` (pair 1) and layout `international`
    (pair 2). Red Bull Ring dropped. They share no tarmac in AC, so pair 2 is
    not pre-learned during pair 1, and both fit the 30-minute block lap budget.
    *(Corner counts were revised at M3 against the AI reference: National is 4
    corners all with braking, not 3 with 2; International is 5, all with
    braking. See the M3 notes below.)*
    Rationale, the quorum-granularity consequence, and the limitation to state
    in the thesis: `configs/annotations/README.md`.
  - **Annotation gate:** missing/invalid annotation is a **HARD refusal** for a
    participant block (impl plan §1) — a block that silently records no passes
    cannot be re-run on the same person. A **dev block** (explicit toggle,
    default off) records ticks only on an un-annotated track and is stamped
    `dev_block: true` so it can never be read as study data.
  - **`zones.braking` is OPTIONAL** (2026-07-09): a corner taken flat has no
    braking zone and is not applicable to the braking-point element — no
    marker, no criterion, out of that element's quorum denominator. Brake marks
    are all-or-neither in the annotator. **M4 must still guard the
    zero-applicable-corners quorum** (impl plan §7). *(The small-denominator
    worry recorded here — "National's braking element has only 2 applicable
    corners, so ≥ 75% means 2/2" — was resolved at M3: the denominator is
    actually 4. See below.)*
  - **`entry`/`exit` gates are pass brackets, not driving landmarks.** Nothing
    is measured at them. See `configs/annotations/README.md`.
  - **Config fields are constrained at the UI, not just validated offline.**
    The sequence field was free text and a typo wrote a schema-invalid manifest
    that only failed hours later at the integrity check; it is now an
    A/B/C/D/none radio group with `start_block` re-checking. Apply the same
    principle to any field M6's panel adds.
  - `annotate.py` checks landmark **geometry**, not just completeness: driving
    order along two chains (the braking zone may overlap the corner-speed
    window — trail braking), apex gates inside the corner-speed window, and no
    overlapping pass brackets. Both study annotations are regression fixtures.
- [x] **M3 — Reference pipeline** · *done 2026-09-08 (214 headless tests; both
  reference tables recorded, extracted and committed; **Gate G0 PASSED on both
  pairs** — full clause-by-clause record and the on-track sign-off in
  `configs/references/G0_REVIEW.md`)* · closes **Gate G0**
  Record 12 AI laps at 95–100% strength per pair under a fixed setup; build the
  reference extractor and the AI-vs-human per-corner comparison. *(The human
  validation laps this originally called for were dropped — see the decision
  below. The comparison and substitution tooling is built and tested for the day
  it can be run.)*
  Exit: G0 met; markers render at extracted (not hardcoded) coordinates. ✓

  **Built:**
  - `kit/trace_kit/reference.py` — extractor (`extract`) + AI-vs-human
    comparison and substitution (`compare`), tested against synthetic laps with
    known ground truth. Its `forward_crossed` is pinned against
    `pass_tracker.lua`'s by a parity test, so the reference describes the same
    stretch of track the runtime evaluates.
  - `lua/trace_rt/lib/markers.lua` + `draw3d` — world-anchored braking/apex
    markers built from the loaded reference table; view-culled by metres of
    track length; `alpha(stage, salience)` is the fading seam (M3 draws `full`).
  - Runtime: per-pair reference load + hard gate (dev blocks opt out, which is
    how reference laps are recorded), `pair_id` as a radio group, `track_id` /
    `car_id` / `track_length_m` stamped into the manifest, reference-lap mode
    (`physics.setCarAutopilot` on the *player* car, so AI and human reference
    laps share the participant's car and setup).
  - Inherited from M2, both resolved: `config_hashes.reference` now hashes the
    per-pair file the block actually loaded (`TODO(M3)` gone), and `versions.ac`
    is detected from `<AC root>/changelog.txt` (1.16.4) instead of the literal
    `'unpinned (set at M3)'`. `trace_kit.integrity` now cross-checks versions
    and track length across blocks — which is what "pinned" actually enforces.

  **Decisions taken at M3 (they bind later work):**
  - **Cars (2026-09-07):** the two pairs use **different cars**. Both pairs are
    one venue, so the layout alone is a thin separator; a second car pushes back
    on the carryover cost framing v6 §63 flags. `pair` is a nuisance fixed
    effect, so the car/layout confound costs nothing interpretively.
  - **The reference is AI-only; there are no human validation laps**
    (revised 2026-09-08, superseding the earlier "researcher drives them"). No
    experienced sim racer was available and the researcher is a beginner — and a
    beginner-recorded reference is not a weaker *expert* reference but a
    **novice** one, which would drag the target toward novice performance and
    make the scaffold fade when a participant drives like a beginner. Recording
    it would have been worse than omitting it. Every corner keeps `source: "ai"`;
    `EVM_human` is unused. **The claim that the AI's brake points fall within a
    competent human's tolerance is NOT established — state it as a limitation.**
    Framing v6 §156, eval plan Phase 0 and Gate G0 are all updated accordingly.
    The compare/substitute tooling is kept and tested for the day it can be run.
  - **Consequence: Gate G2 absorbs G0's lost job.** The pilot is now the only
    empirical check that the reference is *reachable* by real novices, so a G2
    failure means recalibrating band floors (or revisiting the car), not tuning
    the EVM.
  - **Bands are floor-dominated in practice** (measured on the first real AI
    block): σ_ref came out at 0.005–0.015 m apex, 0.58–0.88 m braking,
    0.20–0.41 km/h corner speed, all far under the 0.5 m / 5 m / 3 km/h floors.
    EVM_AI does almost nothing against an AI this repeatable — **the floors set
    every band**, which makes floor calibration the load-bearing part of G2.
  - **Substitution rule:** substitute a corner when the human reference falls
    outside the band the AI reference would impose,
    `|mean_human − mean_AI| > max(σ_AI × EVM_AI, floor)`. Rationale: if a
    competent human would fail the AI-anchored criterion, that criterion is not
    a usable target for a learner. Per **corner**, not per element — mixing a
    human brake point with an AI apex line describes a corner nobody drove.
  - **Apex metric needs a LINE, not a point.** `annotation` gained a required
    `zones.apex_window_half_m` (metres, default 20, reviewed at G0) and
    `reference` gained a sampled `apex.gates[].line` plus `mean_rms_m`. The old
    schema could not express the windowed-RMS metric framing v6 specifies.
  - **σ_ref of exactly 0 is legal** (the AC AI is that repeatable); the band
    floors absorb it. The guard against a spurious σ is a minimum
    contributing-lap count in the extractor, not a schema bound.
  - `controller_config` gained `evm: {ai, human}` (replacing the scalar `evm`)
    and `band_floors`; provisional values, finalised at **G2**.

  **Verified in game 2026-09-07** (block `1_s2_pair1_adaptive_20260907_234553`,
  National, `dev_block: true`): autopilot recording works, the manifest carries
  `track_length_m` 2600.26, `versions.ac` 1.16.4 (self-detected) and CSP 0.2.11,
  `config_hashes.reference: null` on a pre-reference dev block, annotation hash
  matching the committed file, integrity PASS on 12,184 ticks. Extraction gives
  **lap-time CoV 0.046% over 11 laps** — G0's < 1% bar met for that block.
  That block also caught a real extractor bug (the partial FIRST lap was being
  timed as a lap, reporting 31% CoV on laps that agreed to within one tick);
  fixed, with a mid-lap-start regression test.

  **Pair 2 recorded 2026-09-08** (block `1_s2_pair1_adaptive_20260908_001510`,
  International, `ks_audi_tt_cup`, AI 100%, autopilot stamped): lap-time CoV
  **0.092% over 12 laps**, all 5 corners 13/13 passes.
  `configs/references/reference_pair2.json` is committed — **pending G0 on-track
  review.** Two real faults it exposed, both now fixed:
  - **`wall_contact` was firing on kerb grazes.** 6 of 13 corner-5 passes were
    flagged while the car never put a wheel off and lost no speed (74.5–75.1
    km/h on flagged and clean passes alike). `collisionDepth > 0` read the eval
    plan's "contacts a wall" far too literally. Now a threshold
    (`WALL_CONTACT_DEPTH_M`, provisional 0.05 m in `pass_tracker.lua`), and
    `max_collision_depth_m` + `max_wheels_outside` are stamped into every pass
    record so both validity gates are auditable from logs — the same discipline
    the brake-initiation sample already follows. Calibrate the threshold from
    observed depths at G0.
  - **The braking zones were anchored to a beginner's brake points**, because
    they were captured by driving and pressing a button. Against a 100% AI,
    corner 1's zone *ended 12.6 m before the AI braked* (no event detectable at
    all) and corner 3's *opened 1.3 m after it* (all 13 laps clamped to the zone
    start → biased-late point and a fake near-zero σ). Zones re-derived from the
    reference: each starts 60 m before the expert brake point and ends at
    turn-in; corner 1/2/3/5 entry gates moved earlier to keep the bracket open
    first. The extractor now refuses to report a clamped point silently
    (`check_braking_zone_fit`): it flags "already braking on entering the zone"
    and any zone leaving < 30 m before the expert point — **novices brake
    EARLIER than the reference**, so a tight zone silently drops that corner
    from the braking element's evidence.
  - Lesson for the remaining annotation work: **drive-and-mark braking zones are
    a starting point, not a contract.** Always re-check them against the expert
    reference before trusting a brake metric; impl plan §7 already says the
    expert reference decides where in doubt.

  **Pair 1 recorded 2026-09-08** (block `1_s2_pair1_adaptive_20260908_005132`,
  National, `ks_bmw_m235i_racing`, AI 100%): lap-time CoV **0.064% over 12 laps**,
  integrity PASS, `configs/references/reference_pair1.json` committed — **pending
  G0 on-track review.** National's annotation needed three corrections, all found
  by checking the annotation against the reference rather than by inspection:
  - **Corner 1 was annotated as taken FLAT and is not** — at racing pace it is
    the second-heaviest braking zone on the lap (205 → 146 km/h at spline 0.0436,
    12/12 laps). Drive-and-mark is done *slowly*, where that corner genuinely
    needs no brakes. It now has a braking zone.
  - **Corners 2 and 3 had the clamping fault** International had: zones opening
    18 m and 3 m *after* the expert brake point.
  - **The compound corner 3 was two corners** and is now split into corners 3
    and 4: two braking events (0.6266, 207 → 96 km/h and 0.7205, 121 → 92 km/h)
    with 113 m of acceleration between them (95 → 124 km/h) and one apex after
    each. Framing v6 §107 already says separate braking events make separate
    corners. National therefore has **4 corners, all with braking**, which lifts
    the braking element's quorum denominator from 2 to 4 — ≥ 75% is now 3/4
    rather than an all-or-nothing 2/2.

  Also added: the extractor checks that each **apex window fits inside its pass
  bracket** (a window running past the exit gate can never be covered, and would
  otherwise surface only as the opaque "apex covered by 0 of N passes"). Corner 3
  uses a 15 m apex half-window for exactly this reason.

  **Recording and review (all done):**
  1. ~~Settle the cars~~ — **done: `ks_bmw_m235i_racing` (pair 1, National) and
     `ks_audi_tt_cup` (pair 2, International).** A GT3 was tried first to buy
     laps, but the 30-min block is time-boxed, so a faster car yields more laps
     rather than a shorter session — and Silverstone National at 2.6 km already
     gives ~18–24 laps against an ~11-lap minimum traverse in any of these cars.
     The GT3 would have paid for laps nobody needed with corner-speed criteria
     (95.0 km/h ±3) a novice could never reach, and conflicts with framing v6
     §162's "road or touring cars of moderate handling complexity".
  2. ~~Record 12 AI laps per pair as dev blocks~~ — **done for both pairs.**
  3. ~~Extract per pair and commit the reference tables~~ — **done for both.**
  4. ~~G0 review~~ — **done 2026-09-08, both pairs PASS.** All five clauses met.

  **G0's numeric clauses are now regression-tested, not console output.** The
  lap-time CoV and the per-corner contributing-lap counts are persisted *in the
  reference tables* (`source_laps.lap_time_cov_pct`, `contributing_laps`), and
  `test_committed_reference_tables_meet_gate_g0_countable_clauses` re-asserts
  them against the committed files on every run — a hand-edit or a re-extraction
  cannot quietly drop a pair below the bar. The real study annotations *and*
  reference tables also joined the M0 parity corpus: they are the files the game
  loads and they are hand-edited between recordings, so they round-trip through
  both validators like the synthetic examples always did. The AI-only reference
  limitation is written up in `DATASET_README.md`; **the methods chapter still
  has to state it.**

  **What the G0 review drives established (2026-09-08, one dev block per pair,
  researcher driving — a novice, which is the point):**
  - Brake initiation was detected on **every clean racing pass** (11/11 National,
    25/25 International), nothing clamped to a zone edge. The M3 zone
    re-derivation survives real novice braking. Measured brake points ran 27.7 m
    early to 27.2 m late, well inside the 40–60 m of room each zone leaves — the
    two margins flagged before the drive (National corner 4's 40 m, International
    corner 1's 12 m late side) were never stressed.
  - **`wheels_outside` confirmed at its boundary from both sides**: 2 wheels off
    valid, 3 off invalid, 4 off invalid. Only the National drive exercised the
    3-wheel case. A pass open at block end closed `incomplete`.
  - **Two corner-speed windows do not always contain the driver's own minimum**
    — National corner 3 (1 of 3 passes, still slowing 8.2 km/h past the end edge)
    and International corner 2 (1 of 4, 4.2 km/h). Recorded as observations, not
    blockers: the window is fixed and applied identically to the AI reference and
    the participant, so the metric stays well defined. National corner 3 is the
    interesting one — **corners 3 and 4 were one corner until M3 split them** on
    an AI trace showing 113 m of acceleration between two braking events, and a
    novice who does not accelerate between them drives it as one corner. That is
    a finding about the corner split under novice driving. G2 revisits both.
  - **`WALL_CONTACT_DEPTH_M` stays provisional at 0.05 m**, confirmed clear of
    kerb contact (21 recorded contacts, deepest 0.0362 m, none ever fired) and
    **untested against a barrier**. Two structural reasons it may stay that way:
    collision depth is only captured inside a corner's pass bracket (the tick log
    has no collision column), and at Silverstone the barriers sit beyond run-off,
    so reaching one sets `wheels_outside` to 4 and invalidates the pass first.
    The two gates are demonstrably not redundant at low depth: 11 of the 21
    contacts were on passes with no track-limits breach at all.

  **Two runtime faults the review found and fixed** (both in `trace_rt.lua`):
  - **`init()` only ever ran from `windowMain`, but CSP calls `draw3d` from the
    first frame.** With the app window still closed, the lazy reference resolve
    reached a nil `references_dir` and raised — defeating the exact thing the
    lazy resolve exists for. `draw3d` now initialises too (guarded on `INPUTS`),
    and `marker_draw_error` is **cleared on a successful draw**: it was sticky,
    so a transient startup fault kept reading as a live one long after markers
    were drawing fine.
  - **The ground disc was invisible at National and visible at International.**
    `SDK_NOTES.md` claimed `car.position` sits at the model origin "≈ road level,
    so no vertical offset is needed" — that approximation is a property of the
    *car*. The M235i's origin put the disc coplanar with the tarmac and the depth
    test swallowed it; the TT Cup's cleared it. Fixed with `MARKER_DISC_LIFT_M`
    and the SDK note corrected. **Lesson: anything flat built from logged car
    positions needs lift, and a claim verified on one car is not a constant.**

- [x] **M4 — Controller + simulator** · *done 2026-09-08 (388 headless tests;
  golden-trace parity suite green over 11 traces; **Gate G1 MET** on 2,800
  simulated streams — full record in `configs/simulation/G1_REVIEW.md`)* ·
  closes **Gate G1**
  Exit: parity suite green; G1 design targets met; config frozen + hashed. ✓
  **Config frozen as `frozen-g1`,
  SHA-256 `c7f9ca964bdeb9d6337e84a2565b214e7765385d267ed74fab7d8cdcb4020ba9`.**
  Not yet verified in game — M4 is headless-complete; the in-game exit check
  rides along with M5's rendering work.

  **Built:**
  - `lua/trace_rt/lib/controller.lua` + `kit/trace_kit/controller.py` — the
    state machine, pure in both languages, pinned to each other by
    `golden_traces/` (11 traces, see its README).
  - `lua/trace_rt/lib/evaluator.lua` + `kit/trace_kit/evaluator.py` — metrics →
    per-pass criterion booleans; bands = `max(σ_ref × EVM_source, floor)`.
  - `lua/trace_rt/lib/pass_metrics.lua` — the M2 seam filled in: streaming,
    O(1)-per-sample accumulation of brake initiation, minimum corner speed and
    apex RMS, pinned against `trace_kit.reference`'s offline detectors so the
    runtime measures a participant the same way the reference was built.
  - `kit/trace_kit/simulate.py` — the Phase 1 simulator (`run` / `sweep` /
    `freeze`), the feasibility figure (hand-written SVG; the toolkit stays
    stdlib-only), and the design-target verdicts.
  - `trace_rt.lua` wiring, the `fades_<block>.jsonl` stream, live controller
    status on the panel, and `trace_kit.integrity` gaining the eval plan's
    "fade-event log parses" clause — which now also *replays* the event
    sequence and rejects one no state machine could have produced.

  **Decisions from M4 that bind later work:**
  - **Two rules had to be added for the machine to work at all**, both found by
    the golden traces, both documented in full at the top of `controller.lua`.
    They are design decisions, not implementation details — write them up in
    the system chapter.
    - **Quorum readiness.** The re-qualification reset drops the qualified share
      to zero on every advance, which is *below* the revert threshold — so
      without a rule, the pass right after an advance reverts it. Quorum is
      therefore not evaluated at all until every applicable corner holds
      `required_passes` of evidence. Conveniently this also makes the probe's
      "3 laps with quorum maintained" a verdict on real evidence.
    - **One regression, one stage.** A reversion left the element one stage down
      holding the same sub-threshold share, so the next pass reverted it *again*;
      a deep collapse cascaded two stages in two passes and the reversion cap
      could never be reached. The revert check is now disarmed after a reversion
      until the share recovers. An *advance* leaves it armed, so a premature
      advance is still undoable — which is the point of probe-and-revert.
  - **A null criterion is NO EVIDENCE, not a failure.** A pass with no
    measurable metric does not enter that element's window and cannot contribute
    a consecutive failure. Scoring nulls as failures would punish a learner for
    an annotation-zone fit problem. The accepted residual risk is the mirror
    image: a corner yielding only nulls **stalls** its element rather than fading
    it. Null counts are stamped into every pass record and shown live on the
    panel so G2 can see it happening. Golden trace: `null_criteria_stall`.
  - **Invalid passes still feed the controller** (eval plan v2) — only *null*
    criteria are withheld. Off-track and wall-contact passes have real metrics.
  - **`config_id` + the manifest SHA-256 are the config's identity, not
    `schema_version`.** M4 added `criteria.consistency_delta_ratio` and
    `qualification.requalify_on_advance` as required fields without bumping
    `schema_version`: no study data existed yet (M1–M3 are dev and reference
    recordings), and every block already records the hash of the exact file it
    loaded.
  - **Eval plan v2's staggered-reversion target sits below its own arithmetic
    floor.** "Within two laps when staggered" is unreachable by any threshold
    setting: with onsets one lap apart across four corners a *majority* has not
    regressed until the third lap, and a corner cannot de-qualify before its
    second consecutive failure. Target 3 is measured as **excess latency over
    that floor** (met at zero excess), which reproduces the plan's own one-lap
    figure exactly for synchronised regression. **The eval plan's wording should
    be corrected; the controller should not.**
  - **The corner-speed floor was the single binding parameter at G1** — 3.0 →
    **4.0 km/h**, the only value the sweep changed out of four. Everything else
    keeps its framing-v6 default. That points G2's calibration effort at the
    corner-speed distribution first.
  - **All 27 bands on the real reference tables are now floor-set**, so `EVM_AI`
    currently has no effect on any criterion. Asserted as an exact count in
    `test_m4_evaluator.py` so a re-extraction or a G2 EVM change surfaces there
    rather than quietly invalidating the sentence in the thesis.
  - **G1's numbers are regression-tested, not console output**, the same
    discipline as G0: `test_m4_simulate.py` re-asserts the committed report's
    verdict and cross-checks its recorded config hash against the live file, so
    editing `controller_config.json` without re-running the simulation fails the
    suite.

  **What G1 says the study should expect** (all in `G1_REVIEW.md`): no simulated
  learner clears all three elements inside 15 laps, so **partial traversal is the
  common case** and RQ1's figures should be built for it; **~38% of typical
  improvers end mid-probe (censored)**, which sets how much of the probe-outcome
  table is right-censored; and the reversion cap was never reached by any of the
  2,800 streams, so it remains an untested-in-practice safeguard.
- [~] **M5 — Full rendering + salience stages** · *code complete 2026-09-08
  (436 headless tests); **visual review DEFERRED to M6/M7 by decision
  2026-10-09***
  Exit: scripted controller states produce the intended visuals for all elements
  on both tracks; static blocks render constant-full while logging identically.
  The second clause is tested headless. The first is an **in-game** check and
  was **deliberately deferred on 2026-10-09** so M6 could start — see the review
  status below. **Hard deadline: it must be closed before the first pilot
  participant drives (M7 / G2).** A participant must not be the first person to
  see these visuals, and a `reduced` form that renders wrong would invalidate the
  RQ3 interview data that asks about it.

  **Built:**
  - `lua/trace_rt/lib/hud.lua` — the **corner-speed indicator**, the third UI
    element and the first that is not world-anchored. Pure: it picks the corner
    (approach / in_zone / settled), tracks the running minimum, and decides what
    to say; `trace_rt.lua` only draws it.
  - `markers.presented_stage(mode, stage)` and `markers.visual(stage, salience)`
    — the whole staging decision, pure and headless-tested, computed before any
    `render.*` call.
  - A second app window (`[WINDOW_...] ID = cue`) for the indicator, and a
    review-only stage override on the panel.

  **Decisions from M5 that bind later work:**
  - **The reduced-salience form is `minimal`** (impl plan §7's open decision,
    now `salience.reduced_form` in the config so it is frozen and hashed like
    everything else — it is an RQ3 interview topic). Markers draw the **disc
    alone**; the corner-speed readout keeps the **target number alone**. The
    argument: reducing salience should reduce what the cue *tells* you, not just
    how bright it is — a dimmer copy of the same marker still hands over the
    corner id and a precise point, so it tests less than it looks. `intermediate`
    and `dimmed` are kept as config values; `dimmed` is the control case for that
    argument and is what "reduced salience" would mean if it meant brightness.
  - **The condition is not a code path, now for real.** `draw3d` used to check
    `meta.condition == 'off'` directly. That check is gone: `presented_stage`
    maps `off` to a hidden stage and `static` to a pin, so all three modes go
    through one function. It also fixed a live bug — the old check read the
    PANEL's current condition, not the block's, so changing the radio button
    mid-block would have changed what a participant saw. `block.condition` is
    now captured at start.
  - **The corner-speed cue is an app window, not a screen overlay.** Only proven
    `ui.*` calls, positioned once by the experimenter (AC persists window
    positions, and the apparatus fixes display and seating anyway).
    `ui.beginTransparentWindow` is the upgrade path if the chrome distracts at
    G2, and is deliberately not taken now: it would be an unverified API on the
    one element a participant stares at.
  - **A window's draw function stops being called when the window is closed**, so
    the HUD's running minimum is accumulated in `draw3d` (a render callback,
    which always runs) and `windowCue` only renders the last result. Never keep
    per-frame state inside a window function.
  - **The `draw cues` review toggle suppresses drawing only.** The controller,
    the evaluator and the HUD's running minimum keep going underneath — the same
    distinction the probe stage rests on. Gating the measurement on it would
    leave the readout wrong for the rest of any corner it was toggled in.
  - **The review stage override is cleared by `start_block`.** A block that
    started with an element pinned by hand would render something the controller
    never asked for while logging as though it had, which is the one way the
    fade log and what the participant saw could disagree.
  - **G1 was re-pinned, not re-opened.** Adding `salience.reduced_form` changed
    `controller_config.json`'s hash, so the simulation was re-run and
    `G1_REVIEW.md` updated. `salience` is read only by `lib/markers` and
    `lib/hud`, and every measured number came back identical across all 2,800
    streams. The rule: the config's identity is `config_id` + hash, so any edit
    re-pins, and `test_m4_simulate.py` fails until it does.

  **What the in-game blocks DID establish** (dev blocks, pair 1, National,
  M235i — `m5_tst_s2_pair1_adaptive_20260909_003201`, 30 passes, and
  `M5_s2_pair1_adaptive_20261009_204120`, 10 passes; both integrity **PASS**
  including the fade-log replay clause): **the controller runs at frame rate
  inside CSP and measures a human correctly**, which closes M4's missing in-game
  check. Every pass carries real `brake_initiation`, `min_corner_speed_kmh` and
  `apex_rms_m`; `brake_rolling_mean_distance_m` is null on a corner's first pass
  and populated after, exactly as the consistency gate specifies; the validity
  gates fire (`first_lap`). No crash, no fault state, no frame cost complaint.

  **A G2 input these blocks handed over early — the criteria almost never hold
  under novice driving.** Over the 30-pass block: `apex` 3 true / 27 false,
  `braking` **0 true** / 28 false / 2 null, `corner_speed` 5 true / 25 false. All
  three elements therefore sat at `full` for every pass and the controller
  **never had cause to move a stage** — 0 fade events in both blocks. The
  braking element is the stark one: measured brake-initiation errors on
  2026-10-09 ran 3.1–20.0 m against a `band_floors.braking_m` of **5.0 m**, so
  one pass in ten cleared accuracy. This is not a fault — it is floor-set bands
  meeting a real novice, and it is exactly what **G2 exists to calibrate**. It
  also confirms G1's prediction that *partial traversal is the common case* from
  real driving rather than simulation. **Take the braking floor to G2 first**,
  the way M4 pointed G2 at the corner-speed distribution.

  **The on-track review still to do** (both tracks, using the panel's salience
  override to script the stages). Items 1–3 need no driving skill and should ride
  along with the M6 protocol dry run; item 4 may be **unreachable by the
  researcher's own driving at `frozen-g1` floors** (see above), so it is expected
  to need either a deliberately loosened dev config or a post-G2 re-run:
  1. Each element at `full`, `reduced`, `probe` — confirm the marker really is
     disc-only at reduced and really is gone at probe, and that the three
     elements can differ from each other on screen at the same time.
  2. The corner-speed window: legible at speed, positioned centre-bottom, and
     its three phases (approach / in_zone / settled) read correctly through a
     corner.
  3. A `static` block and an `off` block: constant-full and nothing-at-all.
  4. An adaptive block driven far enough for the controller itself to move a
     stage. **M4's half of this is now done** (the controller demonstrably runs
     in game); what is still unseen is a *stage transition* on screen. To force
     it, drive a dev block with a temporarily loosened floor, then restore
     `frozen-g1` — `test_m4_simulate.py` fails until the hash matches again,
     which is the guardrail working.
- [~] **M6 — Experimenter panel + protocol dry run** · *started 2026-10-09
  (500 headless tests)*
  Exit: complete fake-participant dataset ingested by frozen analysis scripts.

  **Built 2026-10-09 — the two panel affordances impl plan §7 names and M5
  shipped without:**
  - **Probe countdown** on the live per-element status line
    (`controller.probe_remaining`, added to **both** controllers and pinned to
    each other in `test_m6_panel.py`). It is a controller reader rather than
    panel arithmetic because the panel must not reach into controller
    internals, and the simulator wants the same number for probe-outcome
    reporting.
  - **The abort.** `aborted` + `abort_reason` in the manifest schema,
    `manifest.mark_aborted`, and a red two-click control on the panel.

  **Decisions from M6 so far (they bind later work):**
  - **`probe_remaining` is deliberately NOT in `snapshot`.** The golden traces
    pin the snapshot field for field, so adding a panel-only reader there would
    churn the whole G1 parity corpus to display a number. A test asserts it
    stays out, so moving it in has to be a deliberate act with a re-run
    simulation behind it.
  - **An abort discards the BLOCK, never the record of what happened.** Abort
    runs the entire normal stop path — every stream closed and flushed, open
    passes closed `incomplete`, the controller finished with mid-probe elements
    censored — and only then stamps the manifest. The partial logs stay on disk
    and stay auditable.
  - **`aborted` follows the `dev_block` pattern** (`const: true`, key present
    only when true), so its mere presence excludes the block from participant
    data and no reader has to special-case a third `false` state.
  - **`abort_reason` is a closed enum, chosen as a radio group**, never typed —
    the M2 sequence-field lesson. The Lua list and the schema enum are asserted
    equal, so they cannot drift. Free-text elaboration goes in `notes`.
  - **An abort excuses emptiness, never corruption.** `trace_kit.integrity`
    treats an aborted block the way it treats a dev block for the
    *evidence* clauses (no passes / no fades / a ticks file with no data rows is
    the explained outcome, not a fault) but holds it to schema validity and
    stream well-formedness exactly as before — otherwise an abort would be a way
    to launder a broken log past the integrity check. Aborted blocks stay **in**
    the apparatus-drift check: they really did run on the apparatus.
  - **Two clicks, never one.** A single red button is a misclick away from
    stamping a participant's block unusable, and a block cannot be re-run on the
    same person. Arming also reveals the reason list, so an abort can never be
    recorded without one. The arm is cleared by `start_block`, for the same
    reason the M5 salience override is.

  **Also built 2026-10-09 — the instrument and analysis layers:**
  - **`schemas/instrument.schema.json` + `instruments/`.** Questionnaire
    responses are schema-validated JSON files stored beside the block files, one
    per administration: `pre_study` (session 1), `nasa_tlx` (per session-2
    *block*), `post_study` and `interview` (session 3). `instruments/` holds the
    **drafts** of the item sets, written from the constructs eval plan Phase 3
    already names — **not ethics-reviewed, and the consent form and participant
    information sheet are still missing** (institutional documents whose wording
    comes from the committee, not from this repo).
  - **The eval plan's fourth integrity clause is now real.**
    `trace_kit.integrity.check_instruments` knows what each session owes and
    fails the same day when a questionnaire is missing — the only hour in which
    a missing TLX is recoverable. `--no-instruments` suppresses it for scanning
    the archive of pre-format test recordings.
  - **`trace_kit.analysis`** — Phase 4 ingestion (`load_dataset` → flat blocks /
    laps / passes / fades / instruments tables, every exclusion rule applied
    once, centrally) plus the **RQ1 descriptive layer**: fade trajectories,
    per-corner qualification heatmaps, time-to-first-fade and time-to-removal
    distributions, probe outcomes tabulated held/reverted/censored, reversion-cap
    hits, atypical trajectories as individual cases, and **RQ3's alignment
    table**. Figures are hand-written SVG, same reasoning as the G1 feasibility
    figure.

  **Further decisions (2026-10-09):**
  - **The RQ2 Bayesian model is deliberately NOT built yet.** Eval plan Phase 4
    only requires the analysis scripts frozen *before results are seen*, not
    before M6, and writing it now would freeze a model specification whose only
    test was data the simulator made up. Ingestion emits the lap-level table the
    model is specified over, and a test asserts it does, so the deferral stays
    honest and adding the model later is additive. **It must be written and
    frozen before any pilot data is analysed.** The toolkit stays
    `jsonschema` + `pytest` + `lupa`.
  - **`dry_run` is a third manifest marker**, alongside `dev_block` and
    `aborted`. A rehearsal block is a *full* study block — both gates pass, the
    controller runs — so without the flag the only thing separating the
    rehearsal dataset from participant data would be a participant-id
    convention, and the M2 lesson is that a convention is not a constraint.
    Panel toggle next to `dev block`, default off.
  - **A dry-run block owes every questionnaire** (a dev or aborted block owes
    none). A rehearsal that skipped the instruments could not catch a missing
    instrument, which is the specific failure the clause exists to prevent.
  - **`partial_lap` is a fifth lap-validity reason**, beyond the eval plan's
    four: the block's final lap has its tick span cut off at the stop, so its
    lap time measures when the experimenter pressed the button. Named separately
    so the count excluded by each rule stays reportable. **State it in the
    methods chapter** — it is an analysis decision, not a plan clause.
  - **Lap-level wall contact is only partly detectable, structurally.** The eval
    plan invalidates a lap where the car contacts a wall, but the tick log has no
    collision column — depth is captured only inside a corner's pass bracket. A
    wall contact on a straight is invisible to `lap_validity`. At Silverstone the
    barriers sit beyond run-off so such a contact almost always trips
    `wheels_outside` first, but "almost always" is a **limitation to state**, not
    a guarantee. A test pins the limitation so it surfaces if the tick schema
    ever gains the column.
  - **A disabled element is not a never-fade.** Zero applicable corners means
    pinned-and-never-evaluated, so RQ1 excludes it from the denominator rather
    than counting it among the elements that failed to fade — which would
    quietly inflate the one number RQ1 is most likely to be quoted on.

  **Still to do for M6:**
  1. **The three-session protocol dry run on yourself**, end to end, with the
     `dry run` toggle on, questionnaires filled in as JSON files, and the
     integrity checker run after each session. Then
     `trace_kit.analysis rq1 --include dry_run` must ingest the result with no
     manual fixes — that is the exit test.
  2. Carried in from M5: **visual review items 1–3** ride along with the dry
     run (see M5 above). They must be closed before a pilot participant drives.
  3. **Consent form + participant information sheet** — not draftable from this
     repo; they come from the ethics committee's required wording.
  4. **Data hygiene:** the pre-M2 test recordings in `trace_data` (participants
     `0`, `1`, `Test1`) are not flagged `dev_block`, so every checker reads them
     as study blocks and reports them as missing instruments and (for the
     pre-M3 ones) schema-invalid passes. They are test data. Either stamp them
     `dev_block` or move them out of the live directory before the dry run, so a
     FAIL in that report means something again.
- [ ] **M7 — Pilot (evaluation Phase 2)** · *not started* · closes **Gate G2**
  Exit: G2 met (EVM finalised, config re-frozen); main study may begin.

Gates (from `evaluation_plan_v2.md`): **G0** reference quality (M3) — **met
2026-09-08**, `configs/references/G0_REVIEW.md`; **G1** simulation feasibility
(M4) — **met 2026-09-08**, `configs/simulation/G1_REVIEW.md`, config frozen as
`frozen-g1`; **G2** pilot calibration (M7) — open.

**The frozen config is re-pinned by its hash, not by trust.** Any edit to
`configs/controller_config.json` changes its SHA-256 and fails
`test_m4_simulate.py` until the Phase 1 simulation is re-run and
`configs/simulation/` regenerated. That is deliberate: a config the simulation
never saw is a config no gate has passed.

### Repo layout note

`kit/` at repo root is the **offline Python toolkit** (`trace-kit`): modern
Python, conda env `ac_dev`, *not* subject to the Python-3.3 constraints below —
those apply only to in-game apps under `python/`. `kit/` must never be moved
under `python/`, because AC scans `apps/python/` for loadable in-game apps.
Shared data contracts live in `schemas/` (JSON Schema) with example fixtures in
`configs/`; the in-game runtime is `lua/trace_rt/`. `golden_traces/` at repo root
is the **controller parity corpus** — the only state the runtime and the
simulator share besides `controller_config.json` (impl plan §3), and the thing
that keeps Gate G1 honest. Read `golden_traces/README.md` before touching either
controller.

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
  control case for that argument. It is an RQ3 interview topic, so it is config —
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
- **Corner-speed indicator** (HUD) — the `cue` app window, logic in `lib/hud.lua`.
- **Apex marker** (world-anchored) — `render.*` in `draw3d`.

A racing line, gear-shift indicator, and delta-time bar were **considered and
deliberately dropped**. Do not add them back. "A working system on three
elements is better than a half-working system on five."

## The fading mechanism

Per element, independently: **full salience → reduced salience → probe
withdrawal**. Transitions move **one stage at a time, in either direction** —
forward on demonstrated competence, backward on regression.
- **Evidence is per corner-pass, not per lap.** Two tiers. **Per corner:** a
  corner *qualifies* for an element when its criterion holds in **3 of the last 4
  passes** (rolling window) and *de-qualifies* on **2 consecutive failures**.
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
  errs conservative, and is what makes the probe's "3 laps with quorum
  maintained" a verdict on real evidence rather than an empty one.
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
- **Probe rules:** a probe lasts **3 full laps** with the element hidden
  (qualification still evaluated throughout — withdrawal removes the scaffold,
  never the measurement); reverts one stage if qualified share drops below 50%;
  **at most 2 reversion cycles per element per block**, after which it stays at
  reduced salience *and is pinned in both directions*; permanence is
  **block-scoped** (every block starts at full salience, no state carries across
  blocks/sessions); a block ending mid-probe is logged as **incomplete /
  right-censored**. Probe completion is counted from the entry *pass*, not the
  next lap boundary, which gives every applicable corner exactly `probe.laps`
  passes driven with the element hidden.
- **Zero applicable corners → the element is DISABLED**: pinned at full salience,
  never evaluated, recorded in the manifest's `disabled_elements` (never in the
  fade log — a fade record with a zero denominator would be a fiction).
- Conservative on purpose: premature withdrawal is worse than delayed.
- Lap-budget feasibility is validated by a synthetic-novice simulation **before**
  any participant is run. ✓ **Done at M4; Gate G1 met** —
  `configs/simulation/G1_REVIEW.md`.
- The acknowledged alternating pass/fail pathology is encoded as a golden trace
  (`golden_traces/alternating_corner.json`): the corner never hits 2
  *consecutive* failures so it never de-qualifies, and after a re-qualification
  reset it can never reach 3-of-4 again. Recorded honestly there: at a
  four-corner denominator the other three still carry exactly the 0.75 advance
  threshold, so one permanently-failing corner is inside the design's tolerance.

**The controller is implemented twice** — `lua/trace_rt/lib/controller.lua`
(runtime) and `kit/trace_kit/controller.py` (simulator). They are kept identical
by `golden_traces/`; read its README before touching either. Every rule above is
stated in full at the top of `controller.lua`, which is the authoritative
description.

## Competency metrics (relative to an expert reference, tolerance bands)

All gates produce a **per-pass boolean** — that is the unit the controller's
3-of-4 rule consumes; nothing window-level leaves the evaluator.
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
  speed envelope.
- **Apex marker**: **RMS lateral deviation from the expert line over a short
  spline window centred on the apex gate** (half-width a per-corner annotation
  constant) — *not* a single-point sample at the gate, which is noisy and gameable.

Any gate whose metric could not be measured on a pass yields **null**, which the
controller treats as no evidence (see the fading mechanism above) — never as a
failure.

These gates are a **heuristic trigger for when to run an unassisted probe, not a
measurement of learning** — the probe stage is the actual retention test. Don't
write code or comments claiming the gates "certify internalisation."

**Expert reference** = AC AI driver at 95–100% strength, 12 laps per car-track
pair, fixed setup, logged through this project's own telemetry pipeline (not
internet hotlaps). It yields both the tolerance bands and the per-corner marker
world coordinates. A planned step (not a contingency) records human-reference
laps from one experienced non-participant; corners where the AI diverges
materially (it brakes conservatively, doesn't trail brake) substitute the human
reference.

**Tolerance bands are floored and source-dependent**, not raw reference variance:
`band_m = max(σ_ref,m × EVM_source, floor_m)`. The **Expertise Variance Multiplier
(EVM)** compensates for the AI's missing motor noise — `EVM_AI` (default 3.0) for
AI-sourced corners, `EVM_human` (default 1.25) for human-substituted ones (whose
σ_ref already contains motor noise). EVM_AI, EVM_human, and the per-metric floors
are named config parameters, finalised in the pilot (Gate G2).

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
the fade sequence** that rejects one no state machine could have produced), and —
over a directory of blocks — apparatus drift in CSP/AC/app versions and track
length.

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

In-game: enable the app under Settings → General → UI Modules. After editing,
**restart the session** (menu → back on track) to reload; full game restart is
safest. `print(...)` and errors go to
`Documents\Assetto Corsa\logs\py_log.txt`.

## Guiding principles (from the thesis)

- One main idea: **telemetry-driven, reversible UI fading.** Everything serves it.
- The system is a first-class contribution — **document design decisions as
  carefully as results.**
- **Per-participant trajectories matter more than group means** at n≈15.
- The thesis will **not** claim statistical significance, generalisation beyond
  the tested cars/tracks/population, or that the thresholds/schedule are optimal.
  Don't write code or comments that imply otherwise.
