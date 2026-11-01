# Milestone log (TRACE)

The full build record, moved out of `CLAUDE.md` on 2026-10-14 because that file
is loaded into every session and had grown to 1,700 lines, 1,250 of them this
log. **Nothing here was deleted** -- this is the roadmap section verbatim as it
stood on 2026-10-14, and it is the place to look for the narrative behind a
decision: which block found a fault, what the measured numbers were, what was
tried and abandoned.

`CLAUDE.md` keeps what BINDS current work: milestone status, the gates, the
decisions later work must respect, and the open to-do lists. If you are about to
reverse a decision, read it here first -- most of them were taken because
something broke in game.

Reviews with their own documents are not duplicated here in full:
`configs/references/G0_REVIEW.md` (reference quality, Gate G0),
`configs/simulation/G1_REVIEW.md` (simulation feasibility, Gate G1),
`kit/tools/README.md` (the one-off analyses and the figures they reproduce).

---

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
  **Config frozen as `frozen-g1`. Its hash changes whenever the file is edited —
  read the current value from `configs/simulation/G1_REVIEW.md`, never from here;
  this line used to carry a copy and it went stale within a month.** Re-pinned
  three times since the freeze (M5's `salience.reduced_form`, the 2026-10-10
  `kr` block, then the 2026-10-14 one-sided corner-speed gate), verdict
  unchanged each time. **The third one is different in kind from the first two:**
  `salience` and `kr` are read by nothing the simulator touches, so every number
  came back identical and the re-run was a formality. `criteria.corner_speed_gate`
  changes which passes meet a criterion, so the numbers moved and Gate G1 was
  genuinely re-reviewed rather than re-stamped.
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
  table is right-censored; and the reversion cap is reached by **1 stream in
  400** (fast improvers only), so expect roughly no participant to reach it and
  treat the `erratic_cap_reached` golden trace as the thing that exercises it.
  *(That last figure was "never reached by any of the 2,800 streams" until the
  2026-10-10 re-run against the 85% pair-1 reference.)*

  **The simulation's inputs are both pinned by hash now, and the second one was
  added the hard way.** `test_m4_simulate.py` always asserted the committed
  report's `config_sha256` against the live `controller_config.json`. It did not
  check the **reference tables**, so when pair 1's reference was replaced on
  2026-10-10 the committed G1 report went on describing results computed against
  a table the repository no longer held — silently, because nothing was watching.
  It surfaced by accident, days of claims later, when the unrelated `kr` config
  field forced a re-run and every apex curve moved (the apex criterion is
  one-sided against the reference's own `mean_rms_m`, and the 85% AI holds a
  tighter line). `simulation_report.json` now carries `reference_sha256` per
  table and a test asserts it. **A reference the simulation never saw is as much
  a problem as a config it never saw** — and the general lesson is that a hash
  pin only protects the inputs it names.
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
  (535 headless tests)*
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

  **Built 2026-10-10 — the braking zones re-derived, and the trapezoid cue:**
  - **National's braking zones and their pass brackets moved**, re-derived from
    the 85% reference (the earliest-braking of the three candidate strengths, so
    one set of zones fits whichever is finally committed). The braking *end*
    moved too, at corners 1 and 4.
  - **The braking marker is now a trapezoid covering the accuracy band**
    (`markers.band_splines` / `markers.band_quad`, pure; `band_quad_for` in
    `trace_rt.lua` does the ac.* sampling), replacing the disc at the reference
    point. The apex marker keeps its disc.

  **Decisions from that work (they bind later work):**
  - **Braking-zone room is budgeted in SECONDS, not metres.** The old rule was a
    flat "60 m before the expert brake point, >= 30 m required". 60 m at Copse's
    197 km/h approach is 1.1 s; the same 60 m at corner 4's 114 km/h is 1.9 s,
    and 36 m there already buys what 60 m buys at Copse. The flat metre rule is
    what made corner 4 read as the problem corner in the first 85% extraction
    when it was the roomiest in time. Target is now **1.5 s early / 1.0 s late**,
    per corner, with the arithmetic written out in the annotation's `notes`.
    The threshold in `reference.py` stays in metres (the reference table carries
    no approach speed) with the reasoning recorded beside it.
  - **The zone-fit check now looks BOTH ways.** A learner braking later than the
    zone end yields a null exactly as one braking earlier than its start does,
    and the corner silently leaves the braking element's evidence either way.
    Corner 1's zone ended **5.7 m** beyond the latest observed human brake point
    and nothing had flagged it for a month, because the check only had an
    early-side clause. `MIN_LATE_MARGIN_M` is the mirror.
  - **Pit involvement is a property of the LAP, not of a corner pass** — the
    same bug as the lap-time CoV one, one level down. The AI boxing for fuel on
    lap 9 left a corner-4 pass that was clean by every validity gate (the
    bracket is nowhere near the pit entry) and braked **35 m early**, because the
    car was already on its way in. That single pass took the corner's sigma_ref
    from 0.49 m to **10.98 m**, and bands being `max(sigma_ref x EVM_AI, floor)`
    it would have handed corner 4 a 33 m braking band — a trivially-true
    criterion from a reference that looks fine. `reference.pit_laps` is now one
    definition with two consumers (lap timing and pass filtering) so they cannot
    disagree.
  - **The trapezoid's width is the evaluator's own band, resolved once at
    reference load**, carried into the marker list as data. The cue on the road
    and the tolerance the criterion applies are then the same number by
    construction, not by two code paths agreeing. `markers` never imports the
    evaluator.
  - **It tapers in the direction of travel**, wide mouth early and narrow exit
    late, because the two edges mean different things: braking early of the band
    costs lap time, braking late costs the corner and is the side a novice
    cannot recover from.
  - **At `reduced` the trapezoid is the whole cue** — band, no cross, no stalk,
    no label. That keeps the reduced form strictly less telling than full (the
    tolerance without the precise point), which is the `minimal` argument from
    M5 applied to a shape instead of a disc.
  - **KNOWN RISK, recorded rather than engineered away:** showing the band may
    teach aiming at its edges, and a wider band shows a more permissive target.
    That is `LITERATURE_BRIEF.md` question 8 and an **RQ3 interview topic** — a
    reason to ask about the trapezoid, not a reason to hide the tolerance the
    system is in fact applying.
  - **G2 band-floor candidates, measured** (162 human pair-1 passes, 85%
    reference, scored by the real evaluator). At the frozen `frozen-g1` floors
    the per-pass rates are braking **6.0%**, corner speed **31.5%**, apex
    **7.4%**. Raising the floors to **15 m / 11 km/h / 3.0 m** gives 59% / 74% /
    73%; **18 / 12 / 3.5** gives 71% / 80% / 78%. A 3-of-4 corner rule wants
    ~75% per pass. The laggard is braking, because it is the AND of two gates
    that fail on *different* passes: at 15 m the accuracy gate passes 76.5% and
    consistency 71.1% but their conjunction only 59.1%. Raising
    `criteria.consistency_delta_ratio` from 0.5 to 1.0 lifts braking to 69.8%
    — but at a ratio >= 1.0 the consistency gate is wider than the accuracy gate
    and stops binding at all, which makes the two-gate design decorative.
    **Do not set these yet**: the floors are a Gate G2 decision, they need the
    12-lap 85% reference and pair 2, and any edit re-pins the config and
    re-opens G1.

  **Built 2026-10-10 (later the same day) — BANDWIDTH KNOWLEDGE OF RESULTS.**
  This one is a response to an external literature review, not a planned
  milestone item, and it is the largest design change since M4. Full rationale
  and rules are at the top of `lua/trace_rt/lib/kr.lua`, which is the
  authoritative description the way `controller.lua` is for the controller.

  **What the review found.** TRACE's three elements show *where* to brake, *what*
  speed to carry and *where* the apex is. All three are **prescriptive,
  concurrent guidance**. None of them is **knowledge of results** — terminal
  information about how far off the attempt was. The only outcome-related signal
  in the whole system was the stage machine, and "nothing faded" says nothing
  about which element, which corner, which direction or by how much. That is a
  real hole, and it is the hole that explains the plateau better than the
  criterion does: the tolerance bands were modelled on **bandwidth KR**
  (Sherwood 1988; Lee & Carnahan 1990), a paradigm whose entire mechanism is that
  the learner receives quantitative error outside the band and silence inside it.
  TRACE had the band and never fired the signal. Lee & Carnahan showed the
  benefit is more than reduced feedback frequency — the band carries information
  about correctness. de Groot et al. (2011) is the driving case (seat vibration
  outside 0.5 m of lane centre, off-target feedback beating on-target); van
  Leeuwen et al. (2011) is the contrast in the same task, where continuous visual
  guidance helped during training and did not survive retention.

  **Built:** `lua/trace_rt/lib/kr.lua` (pure, headless-tested), a `kr` block in
  `controller_config.json` and both validators, a `kr` field on every pass
  record, delivery in the participant-facing `cue` window, live counts on the
  panel, `trace_kit.integrity.check_kr`, and `trace_kit.analysis kr` — the CE/VE
  diagnostic report. Also, two gaps this work exposed and closed:
  `kit/tests/test_m7_runtime_syntax.py` parses every shipped Lua file under
  LuaJIT 2.1 (**`trace_rt.lua` was never loaded by any test** — a syntax error in
  it showed up only in game, as a half-blank window), and the simulation now pins
  the reference tables by hash as well as the config (see M4 above).

  **Decisions from the KR work (they bind later work):**
  - **KR is NOT a fourth UI element.** It is an **apparatus property**: present
    identically in both conditions, never part of the fading ladder, and nothing
    in it feeds the controller or the evaluator — so the golden-trace parity
    corpus is untouched and G1 was re-pinned rather than re-opened. The
    adaptive-vs-static manipulation stays exactly what it was: whether the
    guidance elements fade. See the scope section below, which says so there too,
    because the three-element rule is otherwise a reason to delete this.
  - **KR is withdrawn with the scaffold, never with the measurement.** An
    element's KR is suppressed exactly when that element is hidden — `probe`,
    `removed`, and the whole `off` condition of sessions 1 and 3. Forced by this
    project's own framing: the probe is the retention test, and a retention test
    with feedback running measures performance-WITH-feedback (Winstein & Schmidt
    1990). It is implemented as **one rule, not a second condition check** — the
    caller hands `lib/kr` the per-element salience LEVEL that `lib/markers`
    already computed for the renderer, so KR visibility is *derived from* cue
    visibility and cannot drift from it.
  - **KR does not fade.** At `reduced` the cue drops parts of itself; the message
    is byte-identical. A fading KR would be a second fading channel and the
    manipulation would stop being the one the study claims to run.
  - **CONFOUND, stated rather than engineered away:** because a faded element
    loses its KR, an **adaptive** participant who reaches a probe receives less
    *total* feedback than a **static** one, not merely less guidance. The review
    names the alternative (keep KR through probes) and recommends against it,
    because then the probe is a transfer test rather than a retention test. The
    asymmetry is pinned by a test
    (`test_a_faded_element_loses_its_kr_and_a_static_one_does_not`) so it is a
    measured property rather than a sentence someone has to remember. **State it
    in the methods chapter.**
  - **Suppression is decided AFTER the controller step**, on the stage in force
    at the moment of delivery. If this pass pushed the element into a probe, the
    driver is in the probe when the message would land.
  - **Bandwidth delivery, and the silence is logged.** A message fires only
    outside the band — the same `max(σ_ref × EVM, floor)` the criterion uses,
    resolved once by `lib/evaluator`, so the tolerance the learner is told about
    and the tolerance the fading decision applied are the same number by
    construction. Inside the band the system is silent and the silence *is* the
    message. Every pass therefore records a per-element **outcome**:
    `delivered` / `inside_band` / `withdrawn` / `not_measured` / `capped` / `off`.
    Four of those are silences and the diagnostic turns entirely on telling them
    apart — the same discipline as null-vs-failure one level out.
  - **A null metric produces no message** (rule 7): no evidence, so nothing to
    report. Reporting "no reading" would tell the learner about an
    annotation-zone fit problem rather than about their driving.
  - **One message per pass, in the corner's causal order.** `kr.elements` is an
    **ordered priority list** (braking → corner speed → apex) and
    `kr.max_messages` caps delivery at 1. The order is the causal chain through a
    corner: the brake point sets the entry speed, which sets the line through the
    apex, so the message names the cause rather than its consequence. The cap is
    because per-component bandwidth KR on a multi-part task can overload the
    learner, and because one braking message is what the review's diagnostic
    asks for. **KNOWN CONSEQUENCE:** at the frozen floors braking is outside its
    band on ~94% of novice passes, so braking monopolises the channel and the
    other two elements are near-silent — which means two of three elements
    currently fade on a criterion the learner gets no information about.
    **Revisit at G2**, where the calibrated floors let the order distribute.
    *Update 2026-10-14: this is already moving on its own, in both directions.
    On the shortHUDtest block braking was inside its band on 14 of 27 measured
    passes (the learner stopped being 14 m early, see the second KR block
    above), so the channel passed on and corner speed spoke 14 times. But the
    one-sided corner-speed gate then silenced the fast side of that, so the
    element that gains the channel is whichever one the learner is currently
    worst at — which is the behaviour the priority order was designed for.*
  - **The braking CONSISTENCY gate is deliberately not reported.** "You were 3 m
    from your own rolling mean" is a statement about the learner's recent passes,
    not knowledge of results about this corner.
  - **Apex KR is unsigned**, because the metric is an RMS and has no direction.
    It reports the excess over the reference's own `mean_rms_m`, which is the
    quantity the criterion gates on. Whether to use signed lateral offset instead
    is an open question in the review's §10.2.
  - **The corner-speed HUD already delivered something KR-like and still does.**
    `lib/hud`'s `settled` phase lingers past a zone showing the achieved minimum,
    coloured by band membership. It is not bandwidth-gated and exists for one
    element only. The two are complementary in practice (the settled readout is
    dropped at reduced salience, and corner-speed KR rarely wins the priority
    order), but **the asymmetry across elements is a confound to state**, not to
    assume away.
  - **CE/VE vocabulary is adopted for REPORTING, and the criterion is NOT
    changed.** `trace_kit.analysis kr` reports constant error (signed mean bias)
    and variable error (SD) per corner per element, which is what makes the two
    failure modes separately visible — "consistently 14 m early" and "on average
    right but all over the place" are different problems and the pass/fail record
    cannot tell them apart. The review's §10.2 proposes **gating** on windowed
    CE/VE instead; that is **rejected**, because framing v6 withdrew window-level
    gating in favour of a per-pass boolean and the review's own note concedes an
    SD from 3–4 passes is very noisy. Its §10.3 learner-σ band is also not
    adopted: the review calls it one weak precedent itself, and it would need
    session-1 state carried across blocks, against the block-scoped rule. Also
    correct the vocabulary in the thesis: TRACE's "accuracy" gate is an
    **AE**-like per-pass absolute error, and its "consistency" gate is a **VE**
    proxy.
  - **`kr` is the one pass-record field that differs between conditions.**
    Everything the controller produces is byte-identical in adaptive and static;
    `kr` is not, because it records what the participant was *told* and the
    conditions differ in exactly that. The "static and adaptive log identically"
    test now compares with `kr` stripped and asserts the difference separately.
  - **`hold_s` (3.0 s) and the one-message cap are provisional and in-game
    unverified.** Legibility at speed, and whether the message overlaps the next
    corner's approach readout, are G2 review items.

  **FIRST IN-GAME KR BLOCK, 2026-10-14** (`KRtest_s2_pair1_adaptive_20261014_144710`,
  pair 1, National, 21 passes; the driver deliberately braked very early, very
  late, and then tried to sit inside the band). It found five things, and the
  first is the most important thing any in-game check has caught so far.

  - **THE MESSAGE WAS READ AS AN INSTRUCTION.** The text was a bare magnitude
    (`6 m early`) under a label in the imperative (`BRAKE 2`), and the first
    person to see it at speed - the person who specified and built it - took the
    pair to mean *"brake 6 m earlier"*, the exact inverse of what it reports. A
    bandwidth-KR manipulation whose sign a participant may invert measures
    nothing. Every message now opens with a **past-tense verb**: `BRAKED 6 m
    early`, `CARRIED 9 km/h slow`, `RAN 0.9 m off line`. All three, not braking
    alone: mixed tense inside one channel would be worse than the original,
    because a participant who learned that `BRAKED ...` is a report would still
    have to guess at `... off line`. Pinned per element by
    `test_every_message_opens_with_a_past_tense_verb`, with the finding as its
    docstring. **The KRtest block's own pass records carry the old wording.**
    *Lesson: `lib/kr` rule 3 said "signed, in the metric's own units" and the
    old text satisfied that literally while failing it in the cockpit. A cue's
    wording is part of the instrument, and it cannot be reviewed headlessly.*
  - **The alignment between the trapezoid and the measurement was checked and is
    CORRECT** - it was the first suspicion and it was wrong. Each reference
    `braking.world_pos` (where the cross, stalk and trapezoid draw) was located
    against the driven path and compared with its own `spline_pos` (what the
    criterion measures): longitudinal agreement -0.25 / +0.94 / +0.22 / +0.04 m
    on corners 1-4. `markers.build` takes the trapezoid's centre from that same
    `spline_pos`, so the shape on the road is centred on the measured point.
  - **A REAL, SYSTEMATIC ~1.4 m BIAS TOWARD "EARLY", from a sampling asymmetry.**
    `reference.brake_initiation` returns the first **20 Hz logged row** at or
    above the brake threshold, so the reference point lands up to one full tick
    *after* the AI truly crossed it; the participant's point is sampled **per
    frame**, so it is essentially exact. The reference is therefore biased late
    and the driver biased early by the same amount. Measured on the 85%
    recording that built the live table, by interpolating the true crossing
    between bracketing ticks: mean **+1.13 / +1.61 / +1.41 / +0.80 m** (max
    2.64 m) on corners 1-4. That is **16-32% of the 5 m band, one-directional**.
    `test_m4_pass_metrics.py`'s parity test cannot see it: it hands the *same
    row list* to both detectors, so it pins the rule and is blind to the sample
    rate. **Fix by interpolating the crossing in the extractor**; it forces a
    re-extraction, so it rides along with the pair-1 re-record (item 5) rather
    than being done on its own. *Lesson: two implementations agreeing on a rule
    is not the same as two measurements being comparable.*
  - **The driver aims at the band's front edge, and 10 m is too short a target
    to aim at.** On the two laps spent trying to sit inside the band: mean
    **+7.52 m**, with 5 of 8 passes between +5 and +10 m - i.e. 0.3-4.7 m before
    the trapezoid's early edge, every time. Not scatter, a landmark. At the
    frozen 5 m floor the shape is 10 m long (0.18 s at 195 km/h), lies flat on
    the road, and is measured at the car's **origin**, which sits behind the
    nose the driver aims with; committing as the near edge arrives spends the
    whole early half of the budget before reaction time is counted. This is
    `markers.lua`'s recorded "aiming at the edges" risk arriving on schedule,
    and it is a **G2 band-floor input**: at the measured 15 m candidate the
    shape is 30 m long and the edge-aiming error is a far smaller share of it.
  - **KR can deliver a censored number as if it were a measurement.** Two
    deliberate very-early passes reported `83 m early` (lap 3 corner 3) and
    `79 m early` (lap 5 corner 2) - both within 0.3 m of their braking zone's
    opening (82.9 m and 79.5 m before the reference point). The detector only
    searches *inside* the zone, so braking before it opens makes the first
    in-zone sample the event, and the number is a **floor, not a measurement**:
    the truth is "at least 83 m early". This is exactly the clamping
    `reference.check_braking_zone_fit` warns about at extraction time, happening
    live for the first time. **Fixed 2026-10-14** - see the clamped-initiation
    note below.

  **Built 2026-10-14 - CLAMPED BRAKE INITIATIONS ARE NO LONGER REPORTED.** The
  fifth KRtest finding, closed. `lib/pass_metrics` now flags the pass
  (`brake_initiation_clamped`, present only when true) and `lib/kr` gained a
  seventh outcome, **`clamped`** - the magnitude is logged as the lower bound it
  is and nothing is said. Rule 8 at the top of `lib/kr.lua` is the full
  argument. Replayed over the real KRtest block it flags **exactly the two
  suspect passes and nothing else**, including the genuine 26 m and 36 m early
  ones.

  **Decisions from it (they bind later work):**
  - **Detected from the brake trace, not from a distance threshold.** Either the
    sample before the event was already above threshold (and so was outside the
    zone, because an in-zone sample above threshold would already have been the
    event), or the event is the pass's first sample and the crossing happened
    before the bracket opened. Exact, and it needs no second constant to
    calibrate.
  - **The CRITERION is deliberately unchanged, and must stay unchanged.** The
    driver really did brake at least that early, so failing is the truth;
    turning the pass into a null would withhold real evidence from the
    controller. The flag governs what may be **said** (`lib/kr`) and what may be
    **averaged** (`trace_kit.analysis`), not what counts as evidence. Nothing
    reaches the controller or the evaluator, so the golden traces and Gate G1
    are untouched and the config is not re-pinned.
  - **A clamped element passes the message channel on**, exactly as a null does.
    Otherwise one badly fitted braking zone would silence the other two elements
    for a whole block, since braking is first in the priority order.
  - **Withdrawal still beats a clamp**: rule 4 is checked before the metric, so a
    hidden element reads `withdrawn`. An element logging `clamped` while hidden
    would read to `trace_kit.integrity` as one that was never withdrawn.
  - **`clamped`, not `censored`.** `censored` is already taken by the fade log,
    where it means a block that ended mid-probe. Both are genuine right-
    censoring - one of an error magnitude, one of an event - and `clamped` is
    what `reference.check_braking_zone_fit` has always called this one.
  - **Excluded from every CE/VE average and counted in `clamped_excluded`.**
    Averaging a floor turns a braking zone's geometry into an apparent change in
    bias, in the one report whose whole job is to say whether bias moved - and
    the direction of the lie depends on which side the zone is narrow. The raw
    `series` still carries the recorded value, because it is the audit trail.
  - **The pairing is checked from the logs, both ways** (`integrity.check_kr`): a
    flagged metric that was `delivered` is the KRtest fault itself; a `clamped`
    outcome with no flag is a message withheld for no recorded reason; and only
    braking can be clamped. It can only check what a block recorded, so blocks
    written before 2026-10-14 are silent on it by construction.
  - **The offline detector was added too** (`reference.brake_initiation_clamped`)
    and is pinned to the runtime's by a parity case in
    `test_m4_pass_metrics.py`. A reference built offline and a participant judged
    at runtime must agree about which brake points were measurable at all, which
    is the same argument that put every other metric in that file.
  - **The experimenter panel shows the count, and only when it is non-zero.** A
    clamped count climbing during a block is not a fact about the driver but
    about the annotation, and it is worth seeing in the hour it can still be
    acted on rather than at analysis.

  **The participant-facing window had never been opened (2026-10-14).** No
  corner-speed readout and no KR message had ever been seen on screen, through
  M5's deferred visual review and the whole KR build. `cfg/acos.ini` carried
  `[DESK_0_FORM_IMGUI_LUA_TRACE_cue] VISIBLE=0`: the `cue` window is a second AC
  app window and has to be opened from the apps sidebar once, like any app.
  Nothing was broken - `draw3d` and `script.update` are script-level callbacks
  and `[CORE] LAZY = 0`, so the markers, the sampler, the controller and the KR
  decision had all been running correctly with the window shut, which is
  precisely why the gap stayed invisible for a month. Two consequences:
  - **`manifest.ini`'s cue `SIZE` went 150x96 -> 300x150.** The window now
    carries up to four lines (corner label, target number in the Title font,
    achieved minimum, KR message) and 96 px clipped the last of them. Kept
    FIXED rather than `FLAGS = AUTO_RESIZE`, because a stimulus window that
    resizes as messages appear and expire moves the readout under the
    participant's eyes and makes the cue's own geometry a variable. **This had
    to change before the window was ever opened** - imgui persists size per
    window in `cfg/extension/state/imgui_settings.ini`, after which the manifest
    value is only an initial default.
  - **Hiding the experimenter panel during a block is safe, and is now a
    verified property rather than an assumption.** Sampling is driven from
    `script.update` and the markers from `draw3d`; neither is a window function.
    The panel is still needed to Start and to Stop, so the protocol is: start
    the block with the panel open, hide the panel, drive, show it again to stop.

  **SECOND IN-GAME KR BLOCK, 2026-10-14** (`shortHUDtest_s2_pair1_adaptive_20261014_181110`,
  pair 1, National, 6 laps, 28 passes, KR wording now past-tense). The first
  block in which a participant-facing cue was actually ON SCREEN while driving:
  the `cue` window was opened for it. Four findings, and the first is the one the
  whole KR build was for.

  - **THE SECTION 0A DIAGNOSTIC ANSWERED, AND IT ANSWERED THE GOOD WAY.** Braking
    bias collapsed within three laps of the driver being told the error:

    | braking | n | CE | VE | AE | inside the 5 m band |
    |---|---|---|---|---|---|
    | laps 0-2 | 11 | **+10.56 m** | 4.72 m | 10.56 m | 1/11 |
    | laps 3-6 | 16 | **+2.37 m** | 5.11 m | 2.88 m | **13/16** |

    Per lap, CE runs +11.6, +12.9, +6.0, +1.8, +0.8, +1.0, +6.0 m. The no-KR
    baseline on the same car and track was **CE +15.06 m** (block
    `m5_tst_...20260909_003201`) and the first KR block, read off the
    EXPERIMENTER panel rather than the participant window, sat at **+8.4 m**. So
    the reading is item 0's first branch: *the target is reachable and the
    missing error signal was the cause.* **The 85% reference change is now
    justified non-circularly on the braking element** -- and the corollary is
    that every per-pass rate measured before today (braking 6.0%) describes a
    system with no error signal and should not be used to set a floor.
    **Caveats, and they are not small:** n=1, the driver is the person who built
    the thing and knows the hypothesis, it is a 6-lap dev block, and **VE did not
    improve** (5.11 m, inflated by one 19.4 m pass on the lap the block was
    stopped). This is a design-iteration finding, not a result. Re-run it as the
    real item-0 diagnostic on a full block before writing it up.
  - **THE CONSISTENCY GATE NOW BLOCKS EXACTLY WHAT KR FIXED.** Over laps 3-6 the
    accuracy gate passed **13 of 16** passes and the braking criterion passed
    **3**: the rolling mean still carried the 10-16 m passes from laps 0-2, so
    every improved pass sat more than `0.5 x band` = 2.5 m from the driver's own
    recent average. The gate was designed to stop "reliably 30 m early" counting
    as competence; what it does in practice is **fault a learner for improving**,
    and it does so hardest in the three laps right after the feedback starts
    working. Whole block: accuracy 52%, both gates **11%**. This is a Gate G2
    item and it is now the binding one on braking -- the measured options are
    the ratio (at >= 1.0 the gate stops binding at all), computing the mean only
    over passes that were themselves in band, or dropping the gate and letting
    the accuracy band bound the scatter on its own.
  - **THE CORNER-SPEED GATE FAULTS THE DRIVER FOR BEING FASTER, and the stated
    reason for that does not survive contact with the data.** 15 of the 24
    measured corner-speed failures were for carrying MORE speed than the 85%
    reference minimum (9 for less, 3 passes in band). `lib/evaluator` justifies
    the two-sided band as "too fast is an error too (the car runs wide)". In this
    block: **1 of those 15 fast passes put a wheel outside** (against 2 of 9 on
    the slow side), the correlation between speed deviation and apex RMS is
    **-0.26 within the fast passes** (going faster went with a *better* line, not
    a worse one), and the fast passes average **+2.3 km/h against the 100% AI**,
    i.e. about the pace of a maximal AI rather than something out of control.
    Note also what the metric is: a MINIMUM over the corner-speed window, so an
    unsustainably hot entry shows up as a *lower* minimum later in the same
    window -- the only way to post a high minimum is to have actually carried the
    speed through. **DECIDED the same day: one-sided (`slow_only`)**, which is
    what the apex gate has always been. See the decisions block below.
  - **The braking band is already "the point, with tolerance either side"** --
    `|distance from the expert point| <= band`, symmetric, drawn as the
    trapezoid. At the frozen 5 m floor that is +/-5 m, i.e. a 10 m shape, which
    is what made it read as a zone to be inside rather than a point with slack.
    The G2 candidate measured on 2026-10-10 was +/-15 m; the braking trajectory
    above argues *against* going that wide, because this driver reached +/-3 m
    within three laps once they were told the error. **Measure the floor after
    the KR diagnostic, not before it.**

  **THE APEX TOLERANCE WAS WIDENED AND THE CHANGE WAS REVERTED (2026-10-14).**
  Asked for directly, tried at `band_floors.apex_m = 2.0`, and **it fails Gate
  G1**: `non_improver_never_fades` goes 0% -> **100%** and
  `share_removed_despite_regression` 0% -> **99.5%**, because the element that
  fades for the non-improver is the apex one. The floor is back at 0.5 m. Full
  record, with the tables, in the second 2026-10-14 note in
  `configs/simulation/G1_REVIEW.md`.

  **What the measurement says (227 real pair-1 apex passes, 85% reference):**
  - Excess apex RMS over the reference's own `mean_rms_m`: mean **2.49 m**,
    median 1.52 m, p90 4.7-6.4 m. The reference's own `mean_rms_m` is
    **0.014-0.024 m** — the AI drives the same line to within two centimetres.
  - Per-pass rate by floor, overall: **0.5 m -> 8-12%**, 1.0 m -> 27-33%,
    2.0 m -> 59-61%, 3.0 m -> 73-75%. By corner at 3.0 m: corner 1 89%,
    corner 4 94%, **corner 3 50-71%, corner 2 60%** — so even 3.0 m does not get
    three of four corners to the ~75% a 3-of-4 rule needs.
  - **Lap-to-lap SD within one corner: 1.86 m.** The total improvement available
    at the apex is about 2.2 m. So the signal is the same size as the noise, and
    **no band separates an improver from a non-improver** — below 1.5 m nobody
    qualifies, above 2.0 m everybody does. That is why widening cannot work, and
    it is a property of the driving rather than of the threshold.
  - **Not the metric's shape:** closest approach to the apex POINT measures mean
    0.94-3.12 m by corner with SD 0.69-2.03 m — the same ratio, so the
    single-point metric framing v6 rejected would not discriminate either.
  - **Not the window's length:** the deviation profile across the apex window is
    flat (corner 1: 2.3 m entry / 1.9 m at the gate / 2.0 m exit; corner 3:
    2.7 / 2.7 / 2.4; corner 4: 1.1 / 0.6 / 0.6). **Corner 2 is the exception**
    (3.3 / 1.7 / 2.0): its entry fifth is measuring turn-in line, not apex, and
    it is the one corner where a narrower `apex_window_half_m` is justified —
    **do it at the pair-1 re-record** (item 5), since it needs a re-extraction.

  **Decisions from it (they bind later work):**
  - **The apex floor stays at 0.5 m**, and the apex element is now expected NOT
    to fade for a novice inside a block. Report that as a finding about the
    element rather than hiding it in a wider band: an apex band of 3 m is about
    one and a half car widths, so it would certify a line nobody would call "on
    the apex" and make the one element whose job is line accuracy decorative.
  - **The novice model's apex parameters are now known to be wrong** —
    `apex_sigma_m` 0.30 against a measured 1.86, `apex_offset0_m` 1.2 against a
    measured 2.49 — so **G1's committed apex numbers are optimistic**. Left in
    place deliberately: recalibrating the model is a Gate G2 act and doing it
    from one driver's passes would re-base the whole report on an n of 1. Stated
    in `G1_REVIEW.md`'s limitations instead, which is where a known-wrong
    assumption belongs.
  - **G1's guardrail is the thing that caught this.** The floor change took
    thirty seconds; the simulation refusing it is what stopped a three-element
    study shipping with an element that fades for a learner who never improved.
    Keep floor changes going through `simulate freeze` + `run` for exactly that
    reason.
  - **The remaining levers, for G2:** narrow corner 2's apex window; accept the
    element stays at full and report it; or buy evidence per decision
    (`qualification.window_passes` 4 -> 6, averaging the noise down) — which
    costs laps the 30-minute block does not obviously have, and which the sweep
    does not currently explore. **An apex band wide enough to be reachable is a
    band too wide to mean anything, and that trade is the finding.**

  **Built 2026-10-14 - THE CORNER-SPEED CRITERION IS ONE-SIDED.**
  `criteria.corner_speed_gate` (`slow_only` | `two_sided`, default `slow_only`):
  a pass fails only when the minimum is more than a band BELOW the expert's. The
  evidence and the three arguments are in the finding above and in the schema's
  own description; what follows is what it cost and what it binds.

  **Decisions from it (they bind later work):**
  - **It is CONFIG, not a code shape.** `two_sided` is the comparison case for
    the argument "beating the reference is not an error", and that argument is a
    thesis claim rather than an implementation detail -- so the choice is frozen
    and hashed like `salience.reduced_form`, and both shapes are tested in both
    languages.
  - **One function per language knows the shape** (`evaluator.corner_speed_ok`,
    Lua and Python). It has two callers on the Lua side -- the pass evaluation
    and the live HUD colour -- and a duplicated comparison would have gone on
    painting a fast pass red while the pass record said it met the criterion.
    `within_band` on the HUD readout therefore now means "met the criterion",
    not "between two edges".
  - **KR mirrors the gate's SHAPE, not just its band.** Under bandwidth KR the
    silence inside the band IS a message, so a criterion that passes a fast pass
    while KR announces an error on it would tell the participant they were wrong
    about a pass the apparatus just recorded as right. `lib/kr`'s per-element
    error now carries a side (`two_sided` / `high_side` / `low_side`) instead of
    a one-sided boolean, and **'CARRIED n km/h fast' is unreachable** under the
    default gate. The wording is kept, not deleted, because `two_sided` has to
    keep working.
  - **Gate G1 was genuinely re-reviewed, not re-stamped** -- the first re-pin
    since the freeze that changes which passes meet a criterion. Verdict
    unchanged, all three targets met: typical improvers traversing 2 of 3 went
    58.3% -> **60.0%**, non-improvers still never fade, reversion latency
    unchanged. **The learner it changed is the ERRATIC one** (any fade 52% ->
    **88.5%**, mid-probe censored 2.5% -> **28.0%**): a noisy learner oscillates
    about the target and only the slow half of that oscillation now fails, so
    they accumulate qualification instead of being held at full salience by their
    own scatter. Read the censoring figure as a study-planning number -- more
    participants will end blocks mid-probe, on top of the 37% of typical
    improvers already there.
  - **It resolved the sweep fragility recorded on 2026-10-10.** The 25-stream
    grid had the frozen `corner_speed_kmh = 4.0` at 48%, just under target 1's
    bar, with the "tightest passing" selection drifting to 5.0 while the
    authoritative run passed at 58.3%. The same grid now reads 22% / **50%** /
    68% at 3.0 / 4.0 / 5.0 and its tightest passing configuration is the frozen
    configuration exactly. **No floor was moved** -- the floors are still a G2
    decision, and now the gate shape and the reference strength are the same
    decision.

  **Built 2026-10-14 - THE HUD IS A SCREEN OVERLAY, NOT AN APP WINDOW.** The
  corner-speed readout and the KR message now draw from
  `manifest.ini [UI_CALLBACKS] IN_GAME = hudOverlay`: centre-bottom, no title
  bar, no frame, no background, TTF text with a dark outline, sized from the AC
  window height. The full argument is in `trace_rt.lua`'s overlay section.

  **Decisions from it (they bind later work):**
  - **A stimulus must not depend on a setup step.** The window's three M5
    justifications all inverted on contact: "the experimenter positions it once"
    meant nobody ever did (a month with no participant-facing cue on screen at
    all), "AC persists window positions" meant the cue's geometry lived in the
    player's imgui state file instead of in this repository, and "only proven
    ui.* calls" bought a cue that looked like a dialog sitting next to the
    experimenter's own dialog -- an asymmetry between two of the study's three
    elements, since the world markers always read as driving assistance.
  - **The cue's geometry is apparatus, so it is code.** `hud.layout(w, h)` is
    pure arithmetic, scales every size with window HEIGHT (so the cue subtends
    the same angle on any display), and **grows the block DOWNWARD from a fixed
    top** so a KR message appearing cannot shift the speed number under the
    driver's eyes. Tested headless, like every other decision the renderer only
    executes.
  - **`[UI_CALLBACKS]` is verified by example, not by documentation.** It is not
    in the `ac_apps` SDK reference; it is taken from CSP's own Mumble app, which
    uses it for the talking-users overlay. So the `cue` window is **kept as a
    fallback** and the panel reports whether the callback has ever fired, which
    tells "nothing on screen" apart from "nothing to show". **Delete the window
    once the overlay is confirmed in game** -- two draw paths for one stimulus is
    one too many, and if both are live the participant sees the readout twice.
  - **The overlay never writes an error on the participant's screen.** The panel
    pattern (surface the `pcall` failure as on-window text) is right for the
    experimenter's surface and wrong for this one: a red Lua error across the
    cockpit is worse than a missing cue. It goes to the panel instead, and the
    font stack is popped on the error path so one bad frame cannot corrupt every
    other window on screen.
  - **The readout appears 1.5 s before the corner-speed window and lingers 2.0
    s, in SECONDS of travel rather than metres of track** (the M6 braking-zone
    lesson, one level out). It was 300 m of lookahead and 80 m of linger, flat,
    which measured against the real National annotation is **1,979 m of a
    2,600 m lap: the readout was on screen 76% of every lap.** A cue that is up
    three quarters of the time is furniture, and it costs the manipulation its
    meaning twice -- the participant stops reading a thing that is always there,
    and withdrawing it at `reduced` changes the whole screen rather than one
    corner's worth of help. 1.5 s / 2.0 s brings the same lap to ~36%, of which
    18% is the zones themselves.
  - **The lookahead is deliberately NOT zero.** Inside the zone the car is
    already at or near its minimum, so a readout that appears only there can
    report but cannot change anything -- it would be knowledge of results
    wearing a cue's clothes, and `lib/kr` does that job properly. 1.5 s is about
    where the brake point is, which is the last moment the number can still be
    acted on.

  **Still to do for M6:**
  0. **Run the §0A diagnostic blocks** — the reason the KR work was done, and
     the thing that decides whether the 85% reference change was justified.
     Drive dev blocks on pair 1 with KR on, then
     `python -m trace_kit.analysis kr "<trace_data>" --include dev`. Two
     readings, both reportable as a design iteration: **CE shrinks within a few
     passes** → the target is reachable and the missing error signal was the
     cause, so keep the reference and the criterion problem largely goes away;
     **CE does not move** → the target is physically hard to reach with this car
     and input setup, which is the non-circular justification the 85% change
     currently lacks. The **no-KR baseline already exists** and is committed in
     the recorded blocks: block `m5_tst_s2_pair1_adaptive_20260909_003201`,
     28 braking passes, **CE +15.06 m, VE 4.68 m** with `kr` absent on every
     pass. *Caveat: that CE is against the 100% reference that was loaded at
     recording time, so compare like with like — re-score with
     `kit/tools/rescore.py` rather than against the new table by eye.*
     **This must precede M6 item 5's band-floor work**, because every per-pass
     rate measured so far (braking 6.0%, corner speed 31.5%, apex 7.4%) came
     from a system with no error signal, and so did G1's "partial traversal is
     the common case" prediction.
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
     FAIL in that report means something again. **Add today's blocks to that
     list: `shortHUDtest` and `test14-10` (2026-10-14) were both recorded with
     the `dev block` toggle OFF**, so they are currently indistinguishable from
     participant data by anything but their participant ids — which is precisely
     the "a convention is not a constraint" lesson the `dry_run` flag exists for.
     `KRtest` the same morning was stamped correctly, so the toggle is being
     missed rather than broken; it is cleared by nothing, so it has to be set
     each time the app reloads.
  5. **Close out the reference change (2026-10-10).** **Sequencing decision
     (2026-10-10): settle the whole approach on PAIR 1 first, then replicate it
     to pair 2 in one pass.** Pair 2 is deliberately left at its 100% table until
     then — the apparatus is knowingly inconsistent in the meantime, which is
     fine for dev blocks and is a **hard blocker before any participant drives**.
     Doing pair 2 early would mean re-recording it again after the KR diagnostic
     or the G2 floors moved something.
     Then: re-record pair 1 at 85% with **fuel for 12+ laps** (8 clean laps is
     below the protocol, so Gate G0 is re-opened), re-record **pair 2** at the
     settled strength and re-derive International's braking zones against it the
     same way, re-extract both, re-review G0, set the band floors from the
     residuals, re-freeze the config and **re-run the Phase 1 simulation and
     re-review G1**. Item 0's diagnostic comes first, because it may change what
     "the settled approach" is.
  6. **See the trapezoid on track.** It is headless-tested as geometry only;
     that CSP projects the quad onto the tarmac, that it reads at speed, and
     that it does not spill off a narrow part of the circuit are in-game checks.
     At the frozen 5 m braking floor it is only 10 m long — legible but tight,
     so judge the shape again after the G2 floors.
  7. **Verify the participant HUD overlay** (2026-10-14, rewritten the same day
     the cue window was superseded). Restart the session and check the panel's
     `HUD overlay:` line says it is drawing. If it says the callback never
     fired, `[UI_CALLBACKS] IN_GAME` is not honoured for a user app -- open
     "TRACE cue" from the apps sidebar as the fallback and say so, because the
     fix is then a different surface rather than a different position. Then run
     M5 visual review item 2 (the three readout phases) and check: legibility at
     speed, whether `hold_s` 3.0 holds a KR message into the next corner's
     approach, whether the readout and a message coexist without either moving,
     and whether centre-bottom at `top_y = 0.76 x height` clashes with the stock
     HUD or the driver's line of sight. **Once it is confirmed, delete the `cue`
     window from `manifest.ini` and `windowCue` from `trace_rt.lua`.**
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
controller. `kit/tools/` is **not** part of `trace_kit`: it holds the one-off
analysis scripts that produced numbers now asserted in prose here and in
`G0_REVIEW.md`, kept only so those numbers can be recomputed — see
`kit/tools/README.md`, which records each figure they reproduce.


---

## 2026-10-14 — the tolerance-calibration review, and the per-element finding it led to

The narrative behind M6 item 8. What binds is in `CLAUDE.md`; the recorded answer
to the literature question is the last section of `BAND_CALIBRATION_BRIEF.md`;
the gate consequences are the third 2026-10-14 note in
`configs/simulation/G1_REVIEW.md`; the reproducible figures are in
`kit/tools/README.md` under `windowscan.py`. This entry is the account of how it
went, including the two things that were tried and dropped.

### What was asked, and what came back

`BAND_CALIBRATION_BRIEF.md`'s prompt was run externally. The reply is committed
as `TRACE_tolerance-calibration_lit-review_v1.0.md`, with a per-claim
verification label (full text / abstract / secondary / unverified) — which is
what made it usable, because the labels are where the holes are.

**The headline is a negative result and it is worth more than a positive one
would have been.** There is no published rule for setting bandwidth/tolerance
widths for novices. Widths are conventionally a percentage *of the movement
goal* (5–20%), inherited from earlier papers rather than derived, and two
full-text sources say so explicitly (Cruz et al. 2018; Ugrinowitsch et al. 2018,
which also states the width effect "remains to be investigated"). Width-as-IV
studies contradict each other. Four of the six questions came back **empty**, and
they are recorded as empty in the brief: no scaling rule, no traceable
justification for driving's recurring 0.5 m lane tolerance, **no precedent at all
for inflating an artificial reference's variance** (the EVM), and no evidence
that any alternative line metric is more reliable trial-to-trial than windowed
RMS.

Three things it broke:

- **The EVM.** No precedent, and it changes no decision anyway — the floors set
  all 27 bands. Gallagher et al. (2004)'s "2 SD from the expert mean" is the
  published form of what it was reaching for, and it needs a *human* reference.
- **Bugeja et al. (2017), worse than thesis-correction item 6 had it.** Not
  citable for empirically-set tolerances, and **nothing accessible supports
  probe-and-revert either** — the paper's result is that gains dissipated when
  feedback was removed, i.e. a guidance-hypothesis finding. Framing v6 §42 and
  §48 read it that way already; §163's "tolerance parameters set by empirical
  observation" is the sentence that has to go.
- **The bandwidth-KR analogy.** Those are bands for *delivering feedback*, not
  for *withdrawing a scaffold*, and the paradigm assumes error inside the band is
  partly motor noise the learner cannot correct — which argues the band should be
  **at least as wide as the noise**. A 0.5 m apex floor against 1.86 m of
  lap-to-lap scatter is wrong on the paradigm's own terms, before any
  discriminability argument.

And one criticism that was simply new: the controller **re-evaluates 3-of-4 every
lap**, so the per-check false-pass rate is not the per-block one (~7% becomes
~37% over fifteen looks in the review's model). Nothing here had treated per-lap
re-evaluation as a statistical property.

### Where the review was wrong, and why that mattered

It inferred from the simulation's behaviour that the synthetic novice must have
**correlated** errors across corners. It does not: `simulate.py` draws
`difficulty` independently per corner. The real reason `apex_m = 2.0` fades a
simulated non-improver is duller and more important — that learner's apex excess
is `1.2 x U(0.6,1.6)` ~ 1.3 m mean at σ 0.30 m, so **a 2.0 m band contains it by
construction**. Chasing that is what produced everything below.

Its own section C.0 numbers came from a `disc.py` "available on request", so they
could not be used: the standing rule in `kit/tools/README.md` is that a number
that cannot be recomputed is not evidence. The load-bearing part was re-derived
in this project's own simulator instead.

### `kit/tools/windowscan.py`, and the harness check that came first

Written to ask two questions the committed Phase 1 report cannot answer:
`elements_removed` is a *count*, so the report never says which element moved,
and `SWEEP_GRID` sweeps the four band parameters only — its own comment rules the
qualification window out as "structural rather than calibratable", which is
exactly the assumption the review attacked.

The harness was checked against the committed report before anything was read off
it: at seed `trace-g1` and 200 streams it reproduces
`simulation_report.json`'s `mean_elements_removed` for every learner type
(1.565 typical, 0.117 erratic, 0.003 staggered, 0.000 non-improver). Only then
the split.

**1. Braking never completes a traversal. 0% of streams, every learner type,
both novice models.** The committed 1.565 is corner speed (83% removed) plus the
**apex** element (74%); braking leaves `full` in 4% of streams and reaches
`removed` in none. The G1 review's own sentence — "Target 1 is carried by braking
and corner speed" — was therefore backwards, and is struck there.

**2. Correcting the one model parameter already known to be wrong fails Gate G1's
first target.** With the measured apex novice (offset 2.49 m, σ 1.86 m, from
`apexscan.py`) substituted for the committed 1.2 m / 0.30 m, the typical improver
goes from **1.565 to 0.828** elements removed and apex removal to 0%, leaving
corner speed alone against a bar of 2 of 3 elements for half of streams. The
earlier note had said the apex numbers were "optimistic"; this is what that is
worth.

**3. "No band width works" was conditional on the 3-of-4 window.** Measured apex
novice, apex floor x window:

| window | apex floor | typical improver advances | non-improver advances |
|---|---|---|---|
| 3-of-4 | 0.5 (frozen) | 0% | 0% |
| 3-of-4 | 2.0 | 82% | 4% |
| 4-of-6 | 1.5 | 41% | **0%** |
| 6-of-8 | 2.0 | 58% | 0% |
| 8-of-10 | 2.5 | **87%** | **0%** |

The longer window buys what the review predicted: the same improver detection at
a far lower false-advance rate, with 8-of-10 at 2.5 m dominating 3-of-4 at 2.0 m
on both margins. So the apex element is not undecidable — a **per-pass**
criterion on it is.

**4. Tried and dropped: just lengthening the window.** First with the wrong
arithmetic, which is worth recording because the fix came from a question rather
than from a test. The floor was written as `2 x window + probe.laps <= laps`,
derived from the prose rule that each advance needs a fresh window of evidence.
Reading `controller.py` instead: `_quorum_ready` is keyed on **`required_passes`**
(a partly-filled window counts — 4 of 4 satisfies "4 of the last 6"), and that
same readiness check gates `probe_to_removed`, so a probe cannot complete on
`probe.laps` alone either. The floor is
`2 x required_passes + max(probe.laps, required_passes)`: **9** laps at 3-of-4,
**12** at 4-of-6, the whole **15** at 5-of-6, impossible from 6-of-8 up. A loose
lower bound at that — the frozen config's floor is 9 and its earliest observed
corner-speed removal is lap 11.

The conclusion survives the correction and gets sharper. Walking the whole ladder
instead of reading "left full": at **4-of-6, floor 1.5 m** the apex element ends
at `reduced` in 40% of typical-improver blocks, enters a probe in 1%, completes in
**0%**, at a 0% non-improver false-advance rate. And every apex floor that does
complete also advances a non-improver (2.0 m: 2% removed vs 4% false; 2.5 m: 23%
vs 13%), which the conservatism requirement forbids. So MDC wants n >= 6 and the
block cannot traverse at n >= 6: **inside one 15-lap block the apex element can be
decided once, not traversed** — a two-stage ladder in effect.

**4b. And the window cannot be changed globally.** Moving every element to 4-of-6
takes corner-speed removal from **83% to 1%** with **94%** of blocks ending
mid-probe. Per-element `qualification` is therefore a prerequisite for any window
change, not a tidiness refinement — which is the strongest thing to come out of
this whole exercise, and it came from being asked whether a 15-lap block can
actually finish a probe at 4-of-6.

**5. One number explains the whole verdict: σ/band per element.** Corner speed
2.0/4.0 = 0.50 and it traverses. Braking 4.0/5.0 = 0.80 and it never does. The
apex element at the measured σ is 1.86/0.5 = 3.7. Gate G1 passes on the one
element whose assumed lap-to-lap noise sits comfortably inside its band — which
is the same fact the review arrived at from the literature side, that a tolerance
narrower than the performer's irreducible noise is not a tolerance.

**6. The braking consistency gate is most of why braking stalls, but not all of
it.** Varying `consistency_delta_ratio` alone: left-`full` 4% -> 51% -> 84% as it
goes 0.5 -> 1.0 -> 2.0. With the gate effectively off (10.0), removal still only
reaches 2%, so the accuracy band against a 4 m brake σ is the other half. That
moves the gate from second to **first** in the G2 queue: it is the reason one of
three elements cannot traverse at all, and braking is the element bandwidth KR
demonstrably fixed in three laps.

### Declined, and the reason recorded

The review's Ranks 3 and 4 — **EWMA, LC-CUSUM/SPRT, and gating on a window
statistic instead of a per-pass boolean**. They would rewrite both controllers,
churn the golden-trace parity corpus that keeps Gate G1 honest, and be validated
by the same simulation whose learner model is the thing under question. Framing
v6 withdrew window-level gating in favour of a per-pass boolean and that holds:
the per-pass boolean plus a `k`-of-`n` window **is** an aggregation. What was
never done is sizing `n` by measurement theory, and that needs no new mechanism.
Recording them as considered-and-rejected with this reason is a stronger position
than not having known about them.

**No config value and no model value was changed.** The frozen hash still
matches, the committed report is untouched, and `pytest -q` is green (654 passed). Everything
adopted is a Gate G2 act, which is where band floors already belonged.

---

## 2026-10-15 — the session budget collapses to 30 minutes, and Shape B is adopted

A protocol constraint arrived after Gate G1 was met: `evaluation_plan_v2.md`
books **three sessions of 60 + 75 + 60 min ≈ 3 h 15** per participant, and the
real ceiling is **30 minutes in one sitting**. The question asked was narrower —
*"advancing a probe takes 3–4 laps, can that be reduced?"* — and the answer to
that one turned out to be no, for a structural reason, while the budget turned
out to have slack nobody had claimed. Full brief: `SESSION_BUDGET_BRIEF.md`.
Tables and reproduction: `kit/tools/README.md` § `lapbudget.py`.

### 1. The eval plan's lap budget was wrong, and wrong in our favour

The plan's whole lap arithmetic rests on *"30 minutes of driving on a ~2-minute
circuit"*, which is also the comment on `simulate.BLOCK_LAPS = 15`. Measured
wall clock (`started_at` → `ended_at` over `laps_completed`) across **every real
block in `trace_data`**: national (2.60 km, M235i) **62–76 s/lap over 9 blocks**,
international (2.95 km, TT Cup) **71–98 s/lap over 3 blocks**. Neither layout is
a 2-minute circuit. A 15-lap block is **~17.5 min** of driving, not 30, so the
195 min booked was padded against a lap time nearly **2× too slow**. *An
assumption that was never measured sat under the one number the whole protocol
was costed from.*

### 2. Shortening the probe buys exactly nothing

The question as asked. `traversal_floor = 2 × required_passes +
max(probe.laps, required_passes)` — and `_quorum_ready` is keyed on
`required_passes`, not `window_passes`, and it gates **`probe_to_removed` as
well**, so after the advance into a probe resets the evidence the probe needs a
fresh `required_passes` laps regardless of its own lap count. Measured:

| window | probe.laps | floor |
|---|---|---|
| 3-of-4 (frozen) | **3 → 2 → 1** | **9 laps, unchanged** |
| 2-of-3 | 3 | 7 |
| 2-of-3 | 2 | **6** |

So the probe is worth exactly **one** lap, and only once `required_passes` has
come down. **The lever is `required_passes`.** Cutting the probe alone would have
bought zero laps and cost the probe its status as a retention test — a change
that looks like a saving and is purely a loss.

### 3. 15 laps was three laps above a cliff, and nobody knew

Gate G1 target 1 (`share_traversing_2_of_3`), committed novice model, 200
streams/type/pair, seed `trace-g1`, scored through `trace_kit.simulate.run`:

| training laps | frozen 3-of-4 p3 | 2-of-3 p2 |
|---|---|---|
| 10 | 0.000 ✗ | 0.085 ✗ |
| 12 | **0.003** ✗ | **0.728** ✓ |
| 14 | 0.290 ✗ | 0.970 ✓ |
| **15 (committed)** | **0.600** ✓ | 0.998 ✓ |
| 18 | 0.932 ✓ | 0.998 ✓ |

**At 14 laps the committed config fails G1 outright.** The gate was met at a lap
count three above its own failure point, and the margin had never been
measured — the committed report fixes `BLOCK_LAPS` and reports one number at it.
G1's safety clause survives everywhere: `share_removed_despite_regression` is
**0.000** in every row and the non-improver never fades in any row.

Per-pair, at 15 laps and the frozen window: **pair 1 88%, pair 2 78%** corner
speed removed. A quorum-granularity effect, not noise — 4 corners makes
`advance_threshold = 0.75` an exact 3-of-4, while 5 corners rounds up to
4-of-5 = **0.80**. Pair 1 is structurally the easier apparatus.

### 4. Three costed shapes, and the one chosen

With consent pre-signed and the RQ3 interview moved to a remote call (neither
needs the rig), at pair 1's 1.17 min/lap:

- **A (29.3 min)** — 15-lap training block only. Keeps the frozen config, Gate
  G1 closed, RQ1 in full. **Loses RQ2 entirely**, and with no static arm
  "adaptive vs static" stops being the manipulation.
- **B (29.4 min) — ADOPTED** — 12-lap training + 4-lap unassisted (3 valid),
  condition **between subjects**.
- **C (~80 min over 3 sittings of ≤ 30)** — the full crossover, every RQ, frozen
  config intact. Recorded because it is **less than half** the 195 min currently
  booked: the 3 h 15 was never the real cost, it was the wrong lap time.

There is no honest half-measure between A and B. A condition contrast measured
on *training* laps is measured with the cues on screen — performance-*with*-
feedback (Winstein & Schmidt 1990), the exact error the probe exists to avoid.
**No unassisted block means no RQ2.**

### 5. What B costs, recorded rather than smoothed over

- **RQ2 keeps its form, not its substance:** between subjects, ~7–8 per arm at
  n ≈ 15, **no baseline covariate** (training laps 1–2 are the only proxy and
  they are measured with full scaffolding in both arms), 3 valid retention laps.
  `(1 + condition | participant)`, the crossed-condition term, `pair`,
  `condition order` and `pair order` all leave the model.
- **Probe-and-revert appears in much less of the data:** `n_staggered_reversions`
  **799 → 227** at 2-of-3 p2, because the element is often already removed before
  a staggered onset arrives. The safety target still passes; the mechanism the
  thesis is about is observed less often.
- **A 2-lap probe is 8 unassisted corner passes per element.** The probe is the
  actual retention test by this project's own framing, so that is a limitation on
  the construct, not on the schedule.
- **Pair 2 is descoped, not deferred.** One pair per participant, so its 100%
  reference table stops gating the first participant — and the thesis then rests
  on one car and one layout.
- **A time-boxed block is no longer safe.** 12 is a floor, not a target. At
  70 s/lap a participant who spins twice is at 10 laps, where nothing traverses
  at any window setting, and a time box would fail G1 **silently**. The block
  must end on a lap count.

### 6. The cost no simulation here can price — so the config was NOT edited

`non_improver.share_with_any_fade` is **0.000 at every window length**, so on
these tables a shorter window looks free. It is not: that model learner sits far
outside the band by construction and cannot fail in the way a short window makes
likely, which is **loss of discriminability near the band edge**. Two things in
the repo already say so from the other side — `BAND_CALIBRATION_BRIEF.md` §E
adopts minimal detectable change (Weir 2005) *precisely because* simulated
behaviour cannot justify a window length, and correction item 8's repeated-looks
inflation (~7% → ~37% across fifteen looks) gets worse with more looks per unit
of evidence.

So the lapbudget tables **point at** 2-of-3 and cannot license it. §E item 8a is
**promoted from refinement to the protocol's blocker**: it is now the only thing
that can license the window the schedule requires, and if it does not, Shape B
is unavailable at 12 laps and the decision reverts to the brief's § D. *Adopting
a window because the clock demanded it is the "seeing what works" justification
this project does not accept.*

**No config value and no model value was changed.** `controller_config.json` is
untouched, the frozen hash still matches, the committed report is untouched, and
`pytest -q` is green (654 passed). New files: `SESSION_BUDGET_BRIEF.md`,
`kit/tools/lapbudget.py`, and a README section for it.

### The MDC analysis ran the same day, and it undercut the FROZEN window too

Gate G2 item 8a (`kit/tools/mdc.py`, Weir 2005) was promoted to the protocol's
blocker by the Shape B decision above, then run immediately. Tables:
`kit/tools/README.md` § `mdc.py`. It was written to answer "does a 3-pass window
survive measurement theory"; the answer is that **a 4-pass one does not either.**

σ_within over the seven `_blocks.py` blocks, pooled by residual df on detrended
(block, corner) cells: braking **8.40 m**, corner speed **8.40 km/h** (a
coincidence in different units, checked per cell), apex **2.25 m**. ICC(1,1) is
**0.454 / 0.116 / 0.099** — almost all variance in corner speed and apex is
lap-to-lap noise, not stable corner-level state, which is the σ/band argument
arriving from measurement theory rather than from simulation.

Per corner, `needs n` being the smallest window whose MDC95 falls under the
improvement available:

| metric | available | c1 | c2 | c3 | c4 |
|---|---|---|---|---|---|
| braking | 8.19 m (the KR diagnostic) | **n ≥ 19** | n ≥ 3 | n ≥ 6 | n ≥ 6 |
| apex | 2.20 m (`apexscan.py`) | n ≥ 5 | n ≥ 9 | **n ≥ 17** | n ≥ 2 |
| corner speed | **no anchor exists** | — | — | — | — |

**Three findings, in order of how much they change.**

1. **The frozen 3-of-4 window was never licensed at its own value.** At 4 passes
   only **1 of 4** corners can resolve the available braking improvement
   (corners 3 and 4 need 6, corner 1 needs 19) and 1 of 4 the apex one. The
   quorum needs 3 of 4. So 2-of-3 does not cross a line 3-of-4 stayed behind —
   MDC95 grows by √(4/3) = **15%** between them, and the window becomes a stated
   limitation of the design rather than a discriminator between protocol shapes.
   *The brief's step-2 branch was written expecting a yes/no and got "neither".*
2. **The element Gate G1 rests on cannot be assessed by this method at all.**
   `windowscan.py` established that corner speed is the only element that
   traverses (83% removal) — and it is the one metric with **no
   improvement-available anchor**. Nothing in the repo measures how much
   corner-speed deviation a novice can recover; the 85% re-reference removed the
   *bias* (+0.31 km/h), a different quantity. **Measuring that anchor is the new
   critical path**, and it is measurable from data already recorded.
3. **Independent corroboration of why braking never traverses.** `windowscan.py`
   found 0% across every learner type and attributed it to the consistency gate
   plus σ/band = 0.80. MDC says the measurement cannot resolve the available
   improvement at any window the block affords. Two methods, different evidence,
   same conclusion — which is the strongest the braking finding has been.

Two things checked rather than assumed: **clamped brake initiations, of which
there were ZERO** in this block set (so the floor-averaging worry is ruled out,
not corrected for), and the near-identical braking and corner-speed sigmas,
which are a coincidence confirmed per cell. **Corner 1 dominates both pooled
sigmas** (12.6 m / 12.8 km/h against 4.7–7.2 for the rest) — it is the zone
recorded as mis-annotated "taken flat" at drive-and-mark pace, so per-corner
reporting was added and a single pooled σ is the wrong unit here.

`rho_between`, the quorum's own question: median residual r is **−0.12**
(braking), **+0.27** (corner speed), **−0.07** (apex). Near zero, so requiring
3 of 4 corners really is four looks at the driver rather than one wearing four
hats — **the quorum survives this analysis even though the window does not.**
Corner speed's +0.27 means its corners fail together somewhat, so its protection
is a little weaker than its denominator suggests.

A caveat on the standard itself: MDC95 is strict, and deliberately so. These
gates are *a heuristic trigger for running a probe, not a measurement of
learning*, and the probe is the retention test — 95% confidence in detecting
individual change is a higher bar than the design claims. The consequence is
that the window is licensed by **item 8b** (contrasting-groups ROC with the cut
at a stated false-pass rate) and MDC reports the size of the limitation, which
is §E's own ordering. Also: `CLAUDE.md` prefers a window **median** for the
right-skewed apex distribution, and a median's standard error is ~1.25× a mean's
on normal data, so every `needs n` above is **optimistic** for the statistic
actually used.

**`2-of-3` was NOT adopted. No config value changed, the frozen hash still
matches, and `pytest -q` is green (654 passed).** New: `kit/tools/mdc.py` and
its README section.

### `frozen-g1b` adopted the same day — and what re-running G1 turned up

Decisions taken: **15 laps**, the alternating pathology **accepted**, the tests
**fixed**. Config: floors **12 m / 9 km/h / 1.5 m**, qualification **2-of-3**,
`probe.laps` **2**, `config_id` `frozen-g1b`. Full justification in
`SESSION_BUDGET_BRIEF.md` § K; per-target verdict in `G1_REVIEW.md`.

**1. The floors were the binding constraint, not the window.** The whole
preceding analysis had treated the evidence window as the thing to squeeze.
Replaying real recorded passes through the real evaluator and controller
(`kit/tools/feasible.py`) showed otherwise: at 5/4/0.5 the braking and apex
elements **never advanced in a single real block** at either window, and
`share_traversing_2_of_3` was 0.000 at *every* window and lap count. Widening
the floors is what makes the criterion reachable; the window only decides
whether the ladder completes in the budget.

**2. The novice model's apex parameters were wrong in a way that reversed a
verdict.** Corrected to the measured 2.49 m / 1.86 m (`apexscan.py`, 227 real
passes) from the assumed 1.2 / 0.30. At a 1.5 m apex floor the *assumed*
novice's apex excess is **contained by the band**, so 68% of non-improvers fade;
the measured novice gives 5.75%. Leaving the assumption in place would have
certified a band width against a learner nobody has observed. *A wrong model
parameter is not merely imprecise — it can invert the sign of a gate.*

**3. The chosen calibration is the best of the tested set on all three error
margins at once** (measured apex novice, 200 streams/type/pair, 15 laps):

| floors | window | t1 share | false-fade | removed-despite-regression |
|---|---|---|---|---|
| **12/9/1.5** | **2-of-3 p2** | **0.720** | **5.8%** | **0.75%** |
| 15/11/1.5 | 3-of-4 p3 | 0.515 | 8.0% | 13.8% |
| 18/12/1.5 | 3-of-4 p3 | 0.855 | 13.5% | 25.0% |

The 3-of-4 packages are an order of magnitude worse on the safety clause,
because a 9-lap ladder puts removal exactly where regression onsets land while a
6-lap ladder completes before them. Three laps of block length (12 → 15, ~3.5
min of session time) is what moves target 1 from 0.430 to 0.720.

**4. THE ALTERNATING PATHOLOGY INVERTED, and the trade-off is derivable.** A
corner meeting its criterion every *other* pass yields ⌈n/2⌉ of its last n
passes: **2 of 4 stalls** under 3-of-4 (the conservative direction), **2 of 3
qualifies** under 2-of-3. A driver right half the time at a corner now counts as
competent there. Only `required_passes = 3` excludes an alternating pattern, and
that costs a 9-lap floor — **so a 6-lap ladder and alternating-rejection cannot
both be had.** Accepted knowingly. `dequalify_consecutive_failures = 1` was
measured as a fix and rejected: it does not stop the corner qualifying and takes
removed-despite-regression from 0.75% to **27%**. Found by the parity corpus's
hand-written assertions, which is exactly the job the corpus README claims for
them.

**5. A 12 m braking band silences KR on the measured bias.** The +8.1 m mean
over 162 human passes is now *inside* the band, so bandwidth KR says nothing
about it; only the untreated +15.06 m no-KR baseline still speaks. Widening the
floor to make the criterion reachable also withdrew the error signal for the
most common error — a cost of the recalibration, pinned by a renamed test so it
cannot be forgotten.

**6. Gate G1's targets 2 and 3 cannot be met by a working system.** Both are
zero-tolerance clauses on events only a working system produces. `frozen-g1`
satisfied them by never fading anything, for anyone. Restating them as stated
rates with the counter-rate reported is now required before G1 can judge a
working configuration — and a NOT MET G1 blocks M7 by the standing rule.

**7. The researcher is not a representative novice.** Best lap **63.60 s**
against the 85% AI's **62.30** (+2.1%), and 8 s clear of the 80% AI. The 85%
reference is therefore demonstrably reachable — good news for G2 — but floors
derived from these passes are a **lower bound**: a true novice needs wider, not
narrower. Re-check after the first pilot participant. (`_blocks.py` describes the
driver as a novice and the lap times disagree; the direction is what matters.)
Also noted for checking: the 80% AI block runs **71.95 s** against 85%'s 62.35,
a 9.6 s step that looks more like a bad block than an AI-strength curve.

### Three cases in the golden corpus had stopped testing what their names said

Regenerating the corpus took parity failures 28 → 6, and the six survivors were
the hand-written spec-level assertions that never read the stored blobs. Three
of them caught real breakage: `block_end_mid_probe` ran past its probe and ended
at `removed`, censoring nothing; `erratic_cap_reached` never reverted so never
reached the cap; `staggered_regression` had already removed the element before
the first onset. Their lap numbers were written out against the 9-lap ladder and
silently stopped meaning what they said at 6 laps. `generate.py` now derives the
ladder landmarks from the config. **The blobs would have been regenerated around
the new, wrong behaviour without a word — only the assertions that refuse to
read them noticed.**

Two placement rules learned while re-timing, recorded in the generator: a broad
collapse must begin the lap **after** a probe is entered (failing every corner on
the entry lap withholds the quorum and merely blocks the advance, so the element
reverts from `reduced` and never exercises `probe_to_revert`), and a rebuild
after a probe reversion costs `required_passes` laps, not a fresh ladder
(reversions do not reset evidence windows).

**Structural weakness recorded, not fixed:** golden traces carry no config of
their own, so they read the live `controller_config.json`. A *calibration* change
therefore churns a corpus whose job is pinning *logic parity* between the Lua and
Python controllers — at the one moment the two could silently diverge, the
detector had to be regenerated. Traces should carry their own `config` block.
G2 will recalibrate again.

### Test repair: assertions now DERIVE the calibration

All 654 kit tests and 6 GRApp tests pass. The ~27 that broke were rewritten to
compute from `controller_config.json` rather than quote numbers — history length
from `window_passes`, the dwell from `required_passes`, the traversal bound from
the arithmetic floor, KR probe magnitudes from the band floors, the mid-probe
block length from `2 x required_passes + 1`. One test that had been passing on a
coincidence of calibration was found doing so: `test_a_block_ending_mid_probe...`
drove 9 laps, which the 6-lap ladder had already completed, so it censored
nothing.

`test_m4_simulate.py` now pins **which** G1 targets are met rather than
requiring all three, and bounds the two failing margins so a drift surfaces
there rather than in the thesis.

### A bug fixed on the way

`simulate.cmd_freeze` coerced every `--set` value with `float()`, writing
`window_passes: 3.0` into the frozen config. Six schema fields are
`"type": "integer"`; a float there validates only by the grace of JSON Schema
treating 3.0 as integral, and the Lua validator is a separate implementation that
must not be relied on to agree.

### Process note, recorded because it nearly cost work

A `git checkout configs/controller_config.json` mid-session discarded the
**uncommitted** 2026-10-14 `corner_speed_gate` and `kr` fields. They were
recoverable only because their exact content was in the session transcript. The
repository has a large uncommitted working tree; a revert of any file in it is
not a safe undo.

### Gate G1's targets 2 and 3 were RESTATED, and the gate is MET again (2026-10-15)

Both had been **zero-tolerance clauses** — a non-improver must leave full
salience in exactly 0.000 of streams, broad regression must be answered by
removal in exactly 0.000 — and both were satisfied only by the `frozen-g1`
floors, **which satisfied them by never fading anything, for anyone.** On real
recorded passes at those floors the braking and apex elements never advanced in
a single block. *A conservatism target is trivially met by a system that never
acts*, so neither clause could judge a working configuration, and every
calibration that made the machine work failed both.

They are now **stated rates with the counter-rate reported** —
`simulate.TARGET_RATES`, which is the contrasting-groups reporting style already
adopted for the band floors (Jørgensen et al. 2018), and the same move eval plan
v2 already made once for target 3's staggered-reversion clause.

| target | bound | measured | counter-rate reported |
|---|---|---|---|
| 2 · `non_improver_false_fade_rate_is_bounded` | ≤ **10%** false pass | **5.75%** | false fail **28%** (typical improvers not traversing) |
| 3 · removal despite regression | ≤ **2%** | **0.75%** | latency excess over the arithmetic floor |

**Both values are DECLARED DESIGN PARAMETERS, not literature values, and they
are provisional until Gate G2** — the review's central finding is that no
published rule exists for a tolerance of this kind. What justifies each is
recorded beside it in `simulate.TARGET_RATES`:

- **10% false pass** is justified by the *ratio*, not the absolute: the design's
  own asymmetry ("premature withdrawal is worse than delayed") requires a false
  pass to be rarer than a false fail, and at 28% false fail this keeps it at
  roughly 3:1. **The asymmetry is asserted as well as the bound**, so a
  calibration that inverted it fails even from inside the bound.
- **2% removal-despite-regression** is bounded an order of magnitude tighter
  because the error is strictly costlier — a late reversion costs one lap driven
  without the cue, a removal costs the rest of the block. It is also the value
  that makes the bound **discriminate**: the adopted 2-of-3 ladder measures
  0.75% while every 3-of-4 alternative at workable floors measures 12–26%. A
  bound admitting 13% would not be a safety bound at all.

`test_the_restated_g1_targets_declare_their_rates_as_provisional` pins both
values and the asymmetry between them, so changing one is deliberate.

### Golden traces now pin their own config, decoupling parity from calibration

Each trace carries the **complete** controller config it was generated against
(`config`, required by `schemas/golden_trace.schema.json`), and both
implementations are handed that object rather than the file on disk.

**Why it mattered:** the corpus exists to catch a divergence between
`controller.lua` and `controller.py`, and it was reading the live config — so a
*calibration* change churned it. The frozen-g1 → frozen-g1b recalibration broke
**28 parity assertions** and silently invalidated three cases (a block that no
longer ended mid-probe, a reversion cap never reached, a regression arriving
after removal). At the one moment the two implementations could have diverged,
the detector had to be regenerated.

**Verified, not assumed:** with the live config temporarily set back to 3-of-4,
**92 parity tests pass** and exactly one fails —
`test_the_corpus_is_not_silently_detached_from_the_study_configuration`, which
is the deliberate guard that at least one trace must still be pinned at the
shipped calibration. The same edit used to break 28 tests.

Two further guards came with it: each pinned config must be a **valid**
controller config (otherwise the trace certifies agreement on input the
apparatus would refuse to load), and where a trace carries `config_overrides`
those must actually be reflected in the pinned config — the two cannot drift
into disagreeing about what the case is.

What pins the **live** calibration is the committed simulation report's SHA-256
in `test_m4_simulate.py`, which is the right place for it.

---

## L. Every open decision closed (2026-10-15)

| decision | resolution |
|---|---|
| Protocol shape | **Shape B** |
| Training block length | **15 laps** — the sitting runs ~32.9 min, not 30 |
| Ethics, consent, pre-questionnaire | **Outside the timed sitting**, confirmed |
| RQ3 interview | **Remote, afterwards** — outside the sitting |
| Band floors / window | **12 m / 9 km/h / 1.5 m, 2-of-3, probe 2** (`frozen-g1b`) |
| Alternating-corner pathology | **Accepted**, documented as a derivable trade-off |
| G1 targets 2 and 3 | **Restated** as stated rates; gate MET |

### 15 laps, and why the three minutes were the cheap option

Gate G1's first target scores **0.72 at 15 laps and 0.43 at 12**. The alternative
way to buy the same traversal rate inside 12 laps is to widen the floors to
15/11/1.5, which costs **false pass 5.8% → 8.0%** and **removal-despite-regression
0.75% → 13.8%**. Three laps of block length costs ~3.5 minutes of rig time and
nothing measurable. The frozen configuration was also certified at 15, so running
15 keeps the gate and the protocol describing the same apparatus.

**The §F open questions are closed, and one of them changed what gets reported.**
With the ethics process, consent, the pre-study questionnaire and the interview
all outside the timed sitting, **~32.9 min is rig time rather than participant
burden.** Real per-participant commitment is **~55–60 min** once the pre-reading
and the 10–15 min remote interview are counted. Both figures belong in the
methods chapter: the sitting is what the apparatus and the lap budget constrain,
the total is what a participant is actually asked for. Quoting only the 33
minutes would understate the ask.

**One limitation this creates, now recorded with a measurement attached.** Moving
the interview out of the session puts a gap between the drive and the questions,
and RQ3 asks partly about moment-to-moment experience — so the further apart they
sit, the more the interview measures recollection. Run it the same day where
possible and **record the gap per participant**, so the limitation can be reported
as a number rather than a caveat.

### What remains, and it is all in-game

Nothing in the repository blocks the first participant any more. The outstanding
work is the dev blocks and the visual review, which need the game:

1. **M6 item 0 — the §0A KR diagnostic re-run**, now with a new question
   attached: at a 12 m braking band, KR is silent on errors under 12 m, which
   includes the +8.1 m bias this driver was running. Does it still fire often
   enough to be a signal?
2. **M6 item 1 — the dry run**, 15 laps, stopwatch on every phase. Every
   non-driving number in the budget above is an estimate and this is the only
   thing that measures them.
3. **M5 visual review items 1–4.** At the `frozen-g1b` floors a stage transition
   should be reachable by real driving, so the deliberately-loosened dev config
   item 4 contemplated may be unnecessary — check before building one.
4. **Data hygiene (M6 item 4)** — the unflagged pre-M2 recordings and the two
   2026-10-14 blocks recorded with the dev toggle off.

### 2026-10-15 — the dry run's visual review found two rendering faults

Both were invisible to every headless test in the repository, which is the
point: `CLAUDE.md` already says *a cue's wording is part of the instrument, and
it cannot be reviewed headlessly.* The same is true of its geometry.

**1. The braking trapezoid floated above the track.** `band_quad_for` shifted the
shape onto the marker in **X and Z but not Y**. The three sampled points come
from `ac.trackProgressToWorldCoordinate`, which follows the AI `fast_lane` and
carries the fast_lane's own vertical datum; the marker itself sits at the
recorded reference **car position**. Those are different heights, so the disc
(drawn at `m.y`) and the trapezoid (drawn at the spline's `y`) sat at different
heights — two halves of one cue on two datums. Fixed by offsetting Y by the
mid-point delta, which puts the quad on the marker's datum **while keeping the
per-vertex spline heights relative to it**, so the shape still follows elevation
and camber instead of being flattened to a single height.

*Why no test caught it:* `markers.band_quad` passes Y straight through from its
inputs and is correct; the fault was entirely in what the caller handed it, and
the caller needs `ac.*`. The existing note in `CLAUDE.md` — "anything flat built
from logged car positions needs vertical lift… a claim verified on one car is
not a constant" — was written about `MARKER_DISC_LIFT_M` and the **disc**. The
generalisation it was pointing at is broader: **a vertical datum verified for
one primitive is not verified for another**, and the trapezoid was added later
without re-checking it.

**2. A stray "BRAKE" cue just past the start line was the PROJECTION SPIKE still
rendering.** `lua/projspike_lua/` freezes an anchor 25 m straight ahead of the
car on its first 3D frame and draws a green disc, a cross, a stalk and the
floating text **"BRAKE"** — so from a standing start it plants a braking cue a
few car lengths past the line and leaves it there for the session. It had been
mistaken for a TRACE marker.

It rendered **whether or not its window was open**: `[CORE] LAZY = 0` plus
`[RENDER_CALLBACKS] TRANSPARENT = draw3d` means CSP calls `draw3d` every frame
once the app is enabled in UI Modules. This is the *inverse* of the rule already
recorded in `CLAUDE.md` ("a window's draw function stops being called when the
window is closed") — true of **window** functions, emphatically not of **render
callbacks**, and that asymmetry is why a throwaway spike could keep drawing for
four months unnoticed.

**This was apparatus contamination, not untidiness.** A participant would have
seen a cue the controller never asked for, possibly in a `static` or `off`
block, with no record of it in any log — and RQ1's fade analysis would have been
scored against a screen nobody could reconstruct afterwards. It belongs to the
same class as the duplicate `cue` window that `manifest.ini` is already slated
to delete: **two draw paths for one stimulus is one too many.**

Fixed by deleting `manifest.ini` and `projspike_lua.lua` (both in git at
`5464f14`; `README.md` stays as the record, with the removal and its reasoning
at the top). `lua/trace_rt/manifest.ini` is now the **only** manifest in the
repository with a render callback, which was checked rather than assumed.

**Standing rule this earns:** before a participant drives, audit every
`TRANSPARENT` render callback on the machine, not just TRACE's own. A throwaway
with a render callback must be **deleted**, not left unopened. And deleting the
manifest stops CSP *finding* the app — an install that already has it enabled
keeps the entry in its config, so the stray marker must be confirmed gone **on
track**.

### Found while auditing: `SESSION_BUDGET_BRIEF.md` was invisible to git

`.gitignore` is an allowlist (`/*` then un-ignore by name), so the brief written
that day was **ignored** — it would not have appeared in `git status`, would not
have been committed, and would have been lost the moment the working tree was
cleaned. `CLAUDE.md`, `evaluation_plan_v2.md` and `G1_REVIEW.md` all cite it for
reasoning they do not restate, so the citations would have dangled. Now
allowlisted, with the failure mode written into the comment beside it.

The allowlist's own comment already warned about this ("a new top-level file is
invisible to git until it is named here") and it still happened, so the warning
is now repeated at the new entry. `trace-litreview-v0.3.md` remains deliberately
untracked, as its existing note says.

### The corner-speed readout redesigned, and the fallback window deleted (2026-10-15)

The dry run confirmed `[UI_CALLBACKS] IN_GAME = hudOverlay` is honoured for a
user app, which closed M6 item 7's open question and let the fallback go. It
also produced two design faults that only a screen could show.

**1. The target was the big number and it took the wrong attention.** The cue
rendered the target speed at `0.044 × height` with the live speed as a small
line beneath it. On track the eye went to the number that never changes. The
driver needs to read what they are **doing**; the target is reference to glance
at, and the box's fill already carries the comparison. Reversed:

| | was | now |
|---|---|---|
| live speed | small line, `size_actual` | **big, centred in a colour-coded box** (`size_speed`) |
| target speed | big, `size_target` | small caption just outside the box's bottom edge |
| in-band verdict | text colour on the small line | **the box's fill and border** |

**2. Centre-bottom was the stock HUD's territory.** Impl plan §7 put the readout
centre-bottom, "close to the road, out of the mirror and the stock HUD's
corners" — but AC's own speedometer, gear indicator and pedal bars all live
along the bottom of the screen, so the one element a participant is meant to
stare at was competing with native instruments for the same strip. `top_y` moves
from `0.76 × height` to **`0.17 ×`**, and a test asserts the whole block —
label, box, target caption, KR line and gaps — stays inside the upper half.

**`box_w` is fixed, not measured from its contents.** A box sized to its text
changes width when the speed crosses 100 km/h: a twitch at exactly the moment
the driver is reading it. Same class of fault as a resizing cue window, and the
same fix — pin the geometry. A test bounds `box_w` against three digits at
`size_speed` and `box_h` against the glyph height, at five resolutions, because
DWrite advance widths are not available headlessly and this is the part that
would crop a digit on one display and not another.

**What did NOT change: the reduced form.** The box is gated by `show_actual`,
the same flag that gated the live speed before. The box *is* the live-speed
display and its fill is the verdict, so drawing it at `minimal` would hand back
exactly the comparison `minimal` exists to withdraw. At `minimal` the readout is
still the target number alone. This was the constraint worth being careful
about: `salience.reduced_form` is frozen config, hashed into every block, and an
RQ3 interview topic — the redesign changed the cue's **form**, not what it tells
the learner at each stage, so no frozen semantics moved and no block already
recorded is reinterpreted.

**The approach phase stays neutral.** The box has no verdict colour while the
car is still slowing, because the live speed is not yet the metric there and a
red/green fill would be a judgement on a number the criterion never sees. That
rule predates the redesign and is preserved; only its *carrier* changed, from
text colour to box fill.

**The `cue` window is deleted** — its manifest section, `windowCue`,
`drawCueWindow` and `drawKrMessages` (which only it used). The shared colour
constants stay, because the overlay uses them. Its epitaph is worth keeping: it
was chosen as an app window because that used only `ui.*` calls already proven
in the app, and the cost was that the cue's position and size lived in the
player's imgui state rather than in the repository — after which **it was never
opened in the month it existed**, so no participant-facing element had ever been
seen on screen. *A stimulus must not depend on a setup step.*

**Still unverified in game**, and it needs one more block: whether the box reads
at speed, whether the fill colour reads as a verdict rather than decoration,
whether `box_w` is wide enough for three digits at the real font, and whether
`top_y = 0.17` has landed under AC's own top-centre widgets. Moving a cue off
one HUD's strip and onto another's would be the same fault twice.
