# Gate G0 — reference quality review

Gate G0 (evaluation plan v2, Phase 0) is the gate M3 closes. It has five clauses;
three are checkable from the repository and are checked automatically, two can
only be done by looking at the track and are signed off at the bottom of this
file.

> Annotation files reviewed against a driven lap (every gate and evaluation zone
> visually checked on track); reference lap-time CoV < 1% per pair; visually sane
> lines in all corners, confirmed by standing the extracted markers on track and
> checking each sits where a competent driver would brake and apex; every corner
> contributing at least the extractor's minimum lap count; and the absence of
> human validation recorded as a limitation in the dataset README and the methods
> chapter. Otherwise re-annotate or re-record before proceeding.

| # | Clause | How it is checked | Status |
|---|---|---|---|
| 1 | Gates and evaluation zones checked on track | by eye, in game, plus the drive analysis below | **met** — both layouts, 2026-09-08 |
| 2 | Lap-time CoV < 1% per pair | `source_laps.lap_time_cov_pct`, asserted by `test_committed_reference_tables_meet_gate_g0_countable_clauses` | **met** (0.064% / 0.092%) |
| 3 | Visually sane lines; markers stand where a competent driver brakes and apexes | by eye, in game | **met** — both layouts, 2026-09-08, after the marker-disc render fix |
| 4 | Every corner at or above the extractor's minimum contributing-lap count | `contributing_laps`, asserted by the same test | **met** (12–13 everywhere; the minimum is 5) |
| 5 | Missing human validation recorded as a limitation | `DATASET_README.md` and `README.md` here (repo side); methods chapter (thesis side) | **repo side done**; methods chapter outstanding |

Clauses 2 and 4 were originally read off the extractor's console at recording
time. They are now carried *in the tables themselves* (`lap_time_cov_pct`,
`contributing_laps`) and re-asserted by the test suite, so a hand-edit or a
re-extraction cannot quietly drop a pair below the bar. This file plus those two
fields are the "reference quality report" the evaluation plan lists as a Phase 0
deliverable.

---

## Recorded evidence

Both tables come from a single AI block per pair: autopilot on the player car, AI
strength 100%, default setup, recorded through this project's own pipeline.

| | pair 1 | pair 2 |
|---|---|---|
| Track | `ks_silverstone-national` | `ks_silverstone-international` |
| Car | `ks_bmw_m235i_racing` | `ks_audi_tt_cup` |
| Block | `1_s2_pair1_adaptive_20260908_005132` | `1_s2_pair1_adaptive_20260908_001510` |
| Ticks | 16,164 | 18,420 |
| Timed laps | 12 | 12 |
| Lap-time CoV | **0.064%** | **0.092%** |
| Corners | 4 (all with braking) | 5 (all with braking) |
| Track length | 2600.26 m | 2945.10 m |

Both block ids say `pair1` — the panel's pair field was not re-set for the second
recording. The *manifest* records the real `track_id` and `car_id`, which is what
the extractor reads, so the tables are correct; the block id is cosmetic and is
left as recorded rather than rewritten after the fact.

### Pair 1 — Silverstone National, BMW M235i Racing

| Corner | Brake spline | Brake marker (x, z) | σ_b (m) | Band (m) | Apex gate(s) | Mean RMS (m) | σ_a (m) | Band (m) | Corner speed (km/h) | σ_s | Band |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.0436 | 185, −863 | 0.963 | 5.00 | 0.0970 | 0.031 | 0.0043 | 0.50 | 138.3 | 0.28 | 3.00 |
| 2 | 0.3028 | 450, −340 | 1.001 | 5.00 | 0.3512 | 0.095 | 0.0683 | 0.50 | 87.3 | 1.04 | **3.11** |
| 3 | 0.6266 | −92, −603 | 1.136 | 5.00 | 0.6878 | 0.054 | 0.0372 | 0.50 | 94.7 | 0.59 | 3.00 |
| 4 | 0.7192 | −257, −557 | 0.565 | 5.00 | 0.7399 | 0.023 | 0.0043 | 0.50 | 86.4 | 0.15 | 3.00 |

12–13 clean passes per corner; every element built from all of them.

### Pair 2 — Silverstone International, Audi TT Cup

| Corner | Brake spline | Brake marker (x, z) | σ_b (m) | Band (m) | Apex gate(s) | Mean RMS (m) | σ_a (m) | Band (m) | Corner speed (km/h) | σ_s | Band |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.0781 | −250, 47 | 0.768 | 5.00 | 0.0995 | 0.046 | 0.0144 | 0.50 | 153.4 | 0.47 | 3.00 |
| 2 | 0.2265 | 140, −93 | 0.589 | 5.00 | 0.2648 | 0.020 | 0.0017 | 0.50 | 85.7 | 0.33 | 3.00 |
| 3 | 0.3368 | 364, 6 | 0.659 | 5.00 | 0.3617 | 0.024 | 0.0069 | 0.50 | 91.2 | 0.22 | 3.00 |
| 4 | 0.6352 | 58, 774 | 0.724 | 5.00 | 0.6938 | 0.058 | 0.0248 | 0.50 | 129.0 | 0.23 | 3.00 |
| 5 | 0.8070 | −290, 592 | 0.798 | 5.00 | 0.8421, 0.8635 | 0.021 | 0.0029 | 0.50 | 74.8 | 0.19 | 3.00 |

13 clean passes per corner; every element built from all of them.

### What the numbers say about the bands

Every band in both tables is set by its **floor**, with exactly one exception —
pair 1 corner 2's corner-speed band, where σ × EVM_AI = 3.11 km/h just clears the
3.00 km/h floor. This is the measured form of the M3 note that the bands are
floor-dominated: against an AI this repeatable, **EVM_AI does essentially
nothing, and floor calibration is the load-bearing part of Gate G2.** The tight σ
values are not evidence that the criteria are well calibrated for novices; they
are evidence that the AI is repeatable, which is a different claim.

---

## On-track checklist (clauses 1 and 3)

Run once per pair, as a **dev block** — the annotation and reference gates are
for participant blocks, and nothing recorded during a review should be readable
as study data. Load the pair's car and layout, drive at moderate pace, and check
each item. Anything that fails is a re-annotate or a re-record, not a note.

**Per corner, for each pair:**

- [ ] The **braking marker** stands on the racing line, before turn-in, where you
      would actually begin braking in that car — not in a run-off, not past the
      turn-in point, not floating off the surface.
- [ ] The **apex marker** stands at the geometric apex you would aim for, on the
      inside kerb or just off it.
- [ ] Both markers appear early enough to be usable at speed and cull cleanly at
      distance rather than popping.
- [ ] The **corner-speed zone** covers the slowest part of the corner — drive it
      and watch where minimum speed actually falls.
- [ ] The **entry/exit gates** bracket the whole corner and do not overlap the
      neighbouring corner's bracket. These are pass brackets, not driving
      landmarks: nothing is measured at them, so "a sensible bracket" is the
      whole bar.
- [ ] The **braking zone** opens before you would brake even on a slow lap — see
      the margins below.

**Recorded margins.** How far a novice may deviate from the expert brake point
and still have the event detected inside the zone. Outside these, the corner does
not *fail* the braking criterion; it silently leaves that element's evidence,
which is worse:

| Pair | Corner | May brake this early | Zone ends this far after the expert point |
|---|---|---|---|
| 1 | 1 | 60.1 m | 29.8 m |
| 1 | 2 | 60.0 m | 60.4 m |
| 1 | 3 | 60.0 m | 56.2 m |
| 1 | 4 | **40.0 m** | 28.2 m |
| 2 | 1 | 60.0 m | **12.0 m** |
| 2 | 2 | 60.0 m | 72.3 m |
| 2 | 3 | 60.0 m | 37.5 m |
| 2 | 4 | 60.0 m | 49.3 m |
| 2 | 5 | 60.0 m | 73.1 m |

Two of these want a decision at the review. Neither is caught by the extractor's
`check_braking_zone_fit`, which guards only the early side and only at a 30 m
minimum:

1. **Pair 1 corner 4 has 40 m of early margin**, the tightest on either track,
   because it is the second half of the split compound and its entry gate sits
   about 15 m before the zone. Decide on track whether a novice plausibly brakes
   more than 40 m early there; if so, corner 3's exit gate and corner 4's entry
   gate both have to move earlier.
2. **Pair 2 corner 1's zone ends 12 m after the expert brake point.** A novice
   who brakes *late* there — plausible on a fast corner a beginner does not
   respect — produces no detectable event and drops out of the evidence instead
   of failing. The late side is the less likely direction, which is why it was
   never guarded, but 12 m is small enough to be worth checking by driving it.

**Per pair, once:**

- [ ] Drive a lap with all markers on and confirm nothing renders in an obviously
      wrong place.
- [ ] Confirm the marker world positions match the tables above — markers are
      drawn from the loaded reference, so a mismatch means the wrong file loaded.
- [ ] Check the `wall_contact` threshold: graze a kerb deliberately and confirm
      the pass is **not** invalidated, then put two wheels off and confirm it
      **is**. `WALL_CONTACT_DEPTH_M` is provisionally 0.05 m in
      `pass_tracker.lua`, and G0 is where it gets calibrated against the
      `max_collision_depth_m` values stamped into the recorded pass records.

---

## Findings — review drives, 2026-09-08

| | pair 1 | pair 2 |
|---|---|---|
| Blocks | `g0_s2_pair1_adaptive_20260908_162754` | `g0_s2_pair2_adaptive_20260908_160513`, `..._161433` |
| Racing laps (out-lap excluded) | 3 | 8 |
| Clean passes per corner | 2–3 | 4–7 |

Both `dev_block: true`, driven by the researcher — a novice, which is the point:
this checks each annotation against the driving it has to survive, not against an
expert's. All config hashes on all three blocks match the committed files, so
these drives tested exactly the tables in the repo.

**A note on how these numbers were produced.** The out-lap is excluded
throughout. `pass_is_clean` in the extractor filters only pits and off-track, so
it keeps the out-lap — and on the out-lap the car coasts, which showed up at
first as National corner 4 "missing" a brake event on 1 of 4 passes. It had not:
the driver simply never touched the brakes that lap. Any tooling built on this
analysis has to drop the out-lap the way the pass tracker already does.

### Passed on both pairs

- **One pass per corner per lap**, every corner, every lap, no gaps and no
  doubles. The pass brackets work on both layouts.
- **Brake initiation detected on every clean racing pass** — 11 of 11 at
  National, 25 of 25 at International. No corner lost a pass to a zone that
  missed the event, and nothing was clamped to a zone edge. The braking zones
  re-derived from the reference at M3 hold up against real novice braking, which
  is exactly the fault that made them need re-deriving.
- Measured brake points ran from **27.7 m earlier to 27.2 m later** than the
  expert point across both tracks — well inside the 40–60 m of early room every
  zone leaves. At National corner 4, the corner with the tightest margin (40 m),
  the driver braked between 12.8 m early and 8.8 m late, so that margin was never
  stressed.
- **`wheels_outside` behaves at its boundary, now confirmed from both sides.**
  2 wheels off stayed valid; 3 wheels off invalidated (National, lap 2 corner 1);
  4 wheels off invalidated. That is AC's "more than two wheels off" rule
  (`WHEELS_OUTSIDE_INVALID_MIN = 3`). International only ever produced 4s, so the
  National drive is what actually exercised the threshold.
- **A pass open at block end closed `incomplete`** (National lap 4 corner 1) —
  right-censoring works.

### Open items

**1. Two corners where the driver was still slowing past the corner-speed
window's end edge**: National corner 3 (1 of 3 passes, 8.2 km/h lower within
40 m) and International corner 2 (1 of 4, 4.2 km/h). Every other corner on both
tracks is clean at both edges.

The metric itself is not broken by this — the window is fixed and applied
identically to the AI reference and to the participant, so the comparison stays
valid. What it means is narrower: on those passes the window did not contain
*that driver's* own minimum. National corner 3 is the more interesting of the
two, because corners 3 and 4 there were **one corner until M3 split them**, on
the strength of an AI trace showing 113 m of acceleration between two braking
events. A novice who does not accelerate between them drives it as one corner,
and the window boundary falls mid-deceleration. That is a finding about the
corner split under novice driving, not a measurement fault. Worth a look on
track; extending corner 3's window costs only that it includes more of the run to
corner 4.

**2. `wall_contact` is still only bounded from below — and may be hard to bound
from above at all on these two tracks.** Across every block ever
recorded there are 21 non-zero collision depths and the largest is **0.0362 m**,
against the 0.05 m threshold — nothing has ever fired since the threshold was
added, where the same kerb grazing previously flagged 6 of 13 passes. The
National drive recorded **no collisions at all**, so the deliberate wall hit did
not happen. The threshold is confirmed clear of kerb contact and **not** confirmed
to catch a real barrier strike.

Two things constrain what a deliberate wall test can establish here:

- **Collision depth is only captured inside a corner's pass bracket.** The tick
  log has no collision column (`configs/ticks_columns.json`: t, lap, spline,
  pos_x/y/z, speed_kmh, brake, throttle, steer, gear, wheels_outside, in_pit), so
  `max_collision_depth_m` on a pass record is the only place a contact is ever
  written down. A barrier strike on a straight, or in a run-off past the exit
  gate, records nothing anywhere. Any test hit has to happen between a corner's
  entry and exit gates.
- **At Silverstone the barriers sit beyond the run-off.** Reaching one from
  inside a corner bracket means crossing grass or gravel first, which sets
  `wheels_outside` to 4 and invalidates the pass before the contact is reached.
  So on these two layouts a wall strike may simply never arrive on a pass that
  track limits has not already invalidated — in which case `wall_contact`'s
  practical job is the one it is already confirmed to do: **not** fire on kerbs.

That the two gates are not redundant at low depth is already established: of the
21 recorded contacts, **11 occurred on passes with no track-limits breach at all**
(on-track kerb grazing) and 10 alongside 3+ wheels off. The open question is only
about the deep end.

**3. Sample size.** 2–3 clean passes per corner at National, 4–7 at
International, one driver, one session each. Enough to establish that every
bracket and zone functions, which is what G0 asks. Not enough to calibrate
anything — that is Gate G2's job.

## Sign-off

| Pair | Reviewed on | Result | Notes |
|---|---|---|---|
| 1 | 2026-09-08 | **PASS** | Markers (incl. disc, after the render fix), brackets, braking zones and all three validity gates confirmed. Open: corner 3's corner-speed window under novice driving |
| 2 | 2026-09-08 | **PASS** | As above. Open: corner 2's corner-speed window |

Markers were confirmed by eye on both layouts, including the ground disc after
the `MARKER_DISC_LIFT_M` fix. The two open corner-speed windows are recorded
observations, not blockers: the metric is well defined either way, and the
windows are annotation constants that Gate G2 revisits against real pilot
distributions. `WALL_CONTACT_DEPTH_M` stays at its provisional 0.05 m, confirmed
clear of kerb contact and untested against a barrier, for the reasons above.

**M3 is closed. M4 may start.**

Until both rows read PASS, **M3 is not closed and M4 must not start** — the
standing rule in `CLAUDE.md`.
