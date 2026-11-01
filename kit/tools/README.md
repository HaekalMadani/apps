# `kit/tools/` — analysis scripts that produced committed numbers

These are **not** part of `trace_kit`. They are one-off analyses that were run
against recorded blocks and whose answers are now asserted in prose elsewhere in
this repository — `CLAUDE.md`, `configs/references/G0_REVIEW.md`, and the `notes`
field of `configs/annotations/annotation_ks_silverstone-national.json`.

They live here for one reason: **a number in a thesis that cannot be recomputed
is not evidence.** Both scripts were originally written in a scratch directory
and would have been deleted with it, leaving sentences like "the same 162 human
passes come out at +0.31 km/h" with nothing behind them. That is the same mistake
one level up from the deleted 100% reference tick logs — see "Reference tick logs
are not scratch" in `CLAUDE.md`.

They are held to a lower bar than `trace_kit`: no test coverage, no schema
validation, paths passed in rather than discovered. What they must do is run and
reproduce. If one stops reproducing the figure recorded below, **that is a
finding** — either the library changed behaviour or the recorded figure was never
right — and it should be chased, not patched over.

Run them with the `ac_dev` interpreter from the repository root:

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/<script>.py ...

## `_blocks.py`

The seven human-driven pair-1 Silverstone National blocks every figure below was
computed over, as a hard-coded list. Deliberately not discovered from the
manifests: a query would silently grow the denominator as new blocks are
recorded and quietly invalidate the recorded numbers. Adding a block is a
deliberate act that comes with re-stating whatever moves.

## `rescore.py` — is the reference reachable, and what would a floor buy?

Re-scores every clean corner pass through the **real** `trace_kit.evaluator`,
with band floors and `criteria.consistency_delta_ratio` overridden in memory
only. It never writes `controller_config.json`, because an edit there re-pins the
frozen hash and re-opens Gate G1.

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/rescore.py \
        "<Documents>/Assetto Corsa/trace_data" \
        configs/references/reference_pair1.json \
        '{"braking_m": 15, "corner_speed_kmh": 11, "apex_m": 3.0}' 0.5

**Reproduced 2026-10-10** against the committed 85% table, 149 braking and 162
corner-speed/apex passes:

| floors (braking / speed / apex) | ratio | braking | corner speed | apex |
|---|---|---|---|---|
| 5 m / 4 km/h / 0.5 m (`frozen-g1`) | 0.5 | 6.0% | 31.5% | 7.4% |
| 15 m / 11 km/h / 3.0 m | 0.5 | 59.1% | 73.5% | 72.8% |
| 18 m / 12 km/h / 3.5 m | 0.5 | 70.5% | 79.6% | 78.4% |
| 15 m / 11 km/h / 3.0 m | 1.0 | 69.8% | 73.5% | 72.8% |

Residuals against the 85% table: brake `median +8.13 m` (median |err| 9.42),
corner speed `median +0.31 km/h` (median |err| 6.50), apex excess RMS
`median +1.68 m`. **The corner-speed median being within a third of a km/h of
zero is the whole case for the 85% reference** — against the 100% table the same
passes sat at −9.4 km/h with 83% on one side, which is an offset no band width
can absorb.

The two-gate conjunction is visible in the gate lines: at 15 m the accuracy gate
passes 76.5% and consistency 71.1%, but the criterion is their **AND** and comes
out at 59.1% — they fail on different passes. Raising the ratio to 1.0 lifts
braking to 69.8% by making the consistency gate wider than the accuracy gate,
at which point it cannot bind at all and the two-gate design is decorative.
**A real design tension, not a tuning opportunity.** Floors are a Gate G2
decision and need the 12-lap 85% reference and pair 2 first.

## `brakescan.py` — where does a human really brake?

`trace_kit.reference` searches for brake initiation *inside* `zones.braking`, so
a driver who braked before the zone opened has the brake already applied at the
zone edge and the detector reports the edge — a censored value that looks like a
measurement. This searches backwards from the reference brake point instead,
with the same detector and the same `controller_config.json` threshold and
debounce, so the censoring is visible.

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/brakescan.py \
        "<Documents>/Assetto Corsa/trace_data" \
        configs/references/reference_pair1.json \
        configs/annotations/annotation_ks_silverstone-national.json

`WIDE_BACK` is per corner and is bounded by the **previous** corner's braking
event, not chosen for symmetry. At a uniform 220 m, National's corner 4 sits
inside corner 3's trail braking and every pass comes back at about −218 m: the
window finds corner 3.

**Reproduced 2026-10-10**, signed metres from the 85% reference brake point
(negative = the human braked earlier):

| corner | n | min | p25 | median | p95 | max |
|---|---|---|---|---|---|---|
| 1 | 38 | −27.9 | 6.7 | 11.1 | 27.2 | 45.6 |
| 2 | 41 | −5.9 | 6.1 | 8.2 | 17.1 | 26.7 |
| 3 | 40 | −8.6 | 3.8 | 9.7 | 20.4 | 29.6 |
| 4 | 30 | −24.2 | −9.4 | −6.1 | 40.0 | 40.9 |

**These are the excursions the braking zones have to contain, on both sides** —
−28 m to +46 m overall, which is what the re-derived zones were sized against
(see `MIN_EARLY_MARGIN_M` / `MIN_LATE_MARGIN_M` in `trace_kit/reference.py` and
the seconds-based budget written out in the annotation's `notes`).

Note corner 4: the only corner whose median is **negative**, i.e. the one corner
where this driver brakes earlier than the reference rather than later. It is also
the slow one (114 km/h approach), which is why the late side needed room there.

---

## `apexscan.py` — what an apex band floor would buy, and where the error sits

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/apexscan.py \
        "<Documents>/Assetto Corsa/trace_data" \
        [block-id-for-the-window-profile]

Two outputs. The **rates** table scores every recorded apex pass through the real
evaluator at a range of candidate floors, overall and per corner. The **profile**
replays one block's tick log against the reference apex line and reports the mean
deviation at the entry fifth, at the gate and at the exit fifth of the window —
which is what separates "the driver is off the line" from "the window is
measuring turn-in and exit rather than the apex".

It scores two block sets and their union: the seven pre-KR blocks in `_blocks.py`
and the three 2026-10-14 blocks in `PAIR1_KR_BLOCKS` (the first with bandwidth KR
on screen). Both lists are records, not queries, for the reason `_blocks.py`
gives.

**Reproduced 2026-10-14**, 227 measured apex passes against the 85% pair-1
reference, whose own `mean_rms_m` is 0.014–0.024 m:

| apex floor | overall | corner 1 | corner 2 | corner 3 | corner 4 |
|---|---|---|---|---|---|
| **0.5 (frozen)** | **11%** | 11% | 3% | 12% | 16% |
| 1.0 | 31% | 41% | 13% | 27% | 45% |
| 1.5 | 50% | 61% | 25% | 46% | 69% |
| 2.0 | 61% | 73% | 37% | 55% | 80% |
| 3.0 | 74% | 89% | 60% | 64% | 85% |
| 3.5 | 80% | 91% | 68% | 71% | 89% |

Excess over the reference's own RMS: mean **2.49 m**, median 1.52 m. Lap-to-lap
SD **within one corner: 1.86 m**, against a novice-model assumption of 0.30 m.

**The load-bearing number is that 1.86 m.** The whole improvement available at
the apex is about 2.2 m, so the scatter is the same size as the signal and no
band separates an improver from a non-improver **on a single pass** — which is
why raising this floor to 2.0 m makes Gate G1 fail outright (100% of simulated
non-improvers lose the apex element). The attempt and the reversion are recorded
in the second 2026-10-14 note in `configs/simulation/G1_REVIEW.md`.

**Corrected 2026-10-14, read this before quoting the sentence above.** That
"no band works" conclusion was measured with the qualification window held at
the frozen **3-of-4**, and it does not survive a longer one: at 4-of-6 with a
1.5 m floor a typical improver advances the apex element in 41% of streams and a
non-improver in 0%. The 100% figure also came from the *committed* novice model,
whose non-improver sits at 1.2 m of apex excess — inside a 2.0 m band by
construction. The claim that survives is narrower and is about the **per-pass
unit of evidence**, not the band: see `windowscan.py` below, and the third
2026-10-14 note in `G1_REVIEW.md`.

Window profile, block `test14-10_s2_pair1_adaptive_20261014_191319` (entry fifth
/ at the gate / exit fifth):

| corner | half-window | entry | gate | exit |
|---|---|---|---|---|
| 1 | 20 m | 2.32 | 1.89 | 2.03 |
| 2 | 20 m | **3.34** | 1.67 | 2.03 |
| 3 | 15 m | 2.66 | 2.72 | 2.41 |
| 4 | 20 m | 1.11 | 0.64 | 0.58 |

Flat everywhere except **corner 2**, whose entry fifth is measuring turn-in line
rather than apex. That is the one corner where a narrower `apex_window_half_m` is
justified, and it needs a re-extraction, so it rides with the pair-1 re-record.

---

## `windowscan.py` — which element traverses, and does a longer window help?

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/windowscan.py \
        [streams-per-type-per-pair] [seed]

Written 2026-10-14 to answer the tolerance-calibration review
(`TRACE_tolerance-calibration_lit-review_v1.0.md`), whose central methodological
claim is that a pass/fail vote over four passes discards information a longer
window keeps — so the apex element's problem may be the **window** rather than
the band. The committed Phase 1 report cannot answer that: it aggregates
`elements_removed` as a count, so it never says *which* element moved, and
`SWEEP_GRID` sweeps the four band parameters only, because its own comment rules
the qualification window out as structural rather than calibratable. Everything
is overridden in memory; `controller_config.json` is never written, and this is
**not** a Gate G1 run.

**Harness check first, because the per-element split is only worth having if the
whole reproduces.** At `200 trace-g1` — the committed report's own seed and
stream count — `mean_elements_removed` comes out at 1.565 (typical), 0.117
(erratic), 0.003 (staggered), 0.000 (non-improver), matching
`configs/simulation/simulation_report.json` exactly. **Every table below is
that same run** — `200 trace-g1` — so the whole and the parts are the same
streams.

**Reproduced 2026-10-14**, `200 trace-g1`, 15-lap blocks, `frozen-g1`.

### 1. Only ONE element traverses the machine, and it is not braking

Per element, the share of streams that left `full` / that reached `removed`:

| learner | model | braking | corner speed | apex |
|---|---|---|---|---|
| typical improver | committed | 4% / **0%** | 100% / 83% | 100% / 74% |
| typical improver | measured apex | 4% / **0%** | 100% / 83% | **0% / 0%** |
| non-improver | either | 0% / 0% | 0% / 0% | 0% / 0% |
| erratic | committed | 0% / 0% | 86% / 12% | 26% / 0% |

Two findings, both new:

- **The braking element never completes a traversal — 0% of streams, every
  learner type, both models.** Gate G1's "2 of 3 elements" is carried by corner
  speed and the apex element, *not* by braking.
- **Substituting the measured apex novice** (2.49 m offset, 1.86 m σ, from
  `apexscan.py`, against the committed assumption of 1.2 m / 0.30 m) drops the
  typical improver from 1.565 to **0.828** elements removed and apex removal to
  **0%**. Only corner speed is left, so Gate G1's first target (2 of 3 elements
  for at least half of typical improvers) **fails** once the one parameter known
  to be wrong is corrected.

### 2. A longer window makes the apex element decidable

Measured apex novice. "Advanced" is *left `full`*, not removed, for the reason
the arithmetic below gives:

| window | apex floor | typical improver advances | non-improver advances |
|---|---|---|---|
| 3-of-4 | 0.5 m (frozen) | 0% | 0% |
| 3-of-4 | 1.5 m | 44% | 0% |
| 3-of-4 | 2.0 m | 82% | 4% |
| 3-of-4 | 3.0 m | 100% | 34% |
| **4-of-6** | **1.5 m** | **41%** | **0%** |
| 4-of-6 | 2.0 m | 78% | 4% |
| 5-of-6 | 2.0 m | 49% | 0% |
| 6-of-8 | 2.0 m | 58% | 0% |
| 7-of-8 | 2.5 m | 73% | 0% |
| **8-of-10** | **2.5 m** | **87%** | **0%** |

The longer window buys exactly what the review predicted: the same improver
detection at a far lower false-advance rate (8-of-10 at 2.5 m dominates 3-of-4
at 2.0 m on both margins). **But the lap budget caps the window**, and the
binding parameter is `required_passes`, not `window_passes` — see
`traversal_floor()` for why, and **correction 2026-10-14** below, because this
section first carried the wrong formula. A full traversal needs

    2 × required_passes + max(probe.laps, required_passes) ≤ laps

| window | laps needed | 15-lap block |
|---|---|---|
| 3-of-4 | 9 | OK |
| 4-of-6 | 12 | OK on paper — see table 2b |
| 5-of-6 | 15 | the entire block |
| 6-of-8 | 18 | impossible |
| 8-of-10 | 24 | impossible |

It is a **lower bound and a loose one**: it assumes every corner qualifies on its
first `required_passes` passes at every stage, which a learner on a learning
curve does not do. The committed 3-of-4 config has a floor of 9 and its earliest
observed corner-speed removal is lap **11**.

> **Correction, 2026-10-14.** This section first gave the floor as
> `2 × window_passes + probe.laps`, which is wrong twice over.
> `Controller._quorum_ready` is keyed on `required_passes` (a partly-filled
> window counts — 4 of 4 satisfies "4 of the last 6"), so a stage costs
> `required_passes` laps, not a whole window; and that same readiness check gates
> `probe_to_removed`, so a probe cannot complete on `probe.laps` alone — after
> the advance into it resets the evidence it also needs `required_passes` fresh
> passes. The formula was derived from the prose rather than from the code. The
> *direction* of the conclusion survives and in fact strengthens: see 2b.

### 2b. A longer window makes the apex element advance, not traverse

Table 2 reads "left `full`", which is **one** advance. This walks the whole
ladder — the final stage of a typical improver's block, measured apex novice:

| window | apex floor | full | reduced | probe (censored) | removed | non-improver advances |
|---|---|---|---|---|---|---|
| 3-of-4 | 0.5 (frozen) | 100% | 0% | 0% | 0% | 0% |
| 3-of-4 | 1.5 | 56% | 37% | 6% | 0% | 0% |
| 3-of-4 | 2.0 | 18% | 40% | 27% | 15% | 4% |
| **4-of-6** | **1.5** | 59% | **40%** | 1% | **0%** | **0%** |
| 4-of-6 | 2.0 | 22% | 63% | 14% | 2% | 4% |
| 4-of-6 | 2.5 | 9% | 37% | 32% | 23% | 13% |
| 5-of-6 | 1.5 | 86% | 14% | 0% | 0% | 0% |

So at a 6-pass window the apex element gets **exactly one stage** and no further:
4-of-6 at 1.5 m advances 40% of typical improvers to `reduced` with a 0%
false-advance rate, and 1% ever enter a probe. Every apex configuration that does
complete a traversal also advances a non-improver (2.0 m: 2% removed against 4%
false; 2.5 m: 23% against 13%), which the design's conservatism forbids. **The
honest reading: within a 15-lap block the apex element can be DECIDED once, not
traversed** — a two-stage ladder in effect, whether or not it is coded as one.

### 2c. The cost of changing the window GLOBALLY — why per-element is required

Corner speed, the one element that traverses at the frozen window:

| window | full | reduced | probe (censored) | removed |
|---|---|---|---|---|
| 3-of-4 (frozen) | 0% | 1% | 16% | **83%** |
| 4-of-6 | 0% | 5% | **94%** | **1%** |

A global move to a 6-pass window takes corner-speed removal from 83% to 1% and
leaves 94% of blocks ending mid-probe. Per-element `qualification` is therefore
**not** an optimisation — it is the only way to lengthen the apex window without
destroying the element that works.

### 3. The braking consistency gate is most of why braking never traverses

`criteria.consistency_delta_ratio` varied alone, committed model, braking element:

| ratio | typical improver left full | removed |
|---|---|---|
| **0.5 (frozen)** | 4% | 0% |
| 1.0 | 51% | 0% |
| 2.0 | 84% | 2% |
| 10.0 (effectively off) | 85% | 2% |

The gate holds braking at `full`, as `CLAUDE.md` already suspected — but turning
it off does not fix the element: removal only reaches 2%. The second cause is the
band itself against the model's noise. **σ/band per element** is the number that
predicts all of this: corner speed 2.0/4.0 = **0.50** and it traverses; braking
4.0/5.0 = **0.80** and it never does; the apex element, measured, is
1.86/0.5 = **3.7**. Gate G1 passes on the one element whose assumed lap-to-lap
noise is comfortably inside its band.

## `lapbudget.py` — what a shorter session buys, and what it costs

Written 2026-10-15 against a protocol constraint that arrived after Gate G1 was
met: the eval plan books **~3 h 15 of participant time** (sessions of 60 + 75 +
60 min) and the real ceiling is **30–60 min for the whole study**. Every
committed feasibility figure — the G1 verdict, `windowscan.py`'s tables, the
traversal arithmetic — is computed at `simulate.BLOCK_LAPS = 15`, which the eval
plan derived from *"30 minutes of driving on a ~2-minute circuit"*. **Both
halves of that premise are wrong.** Overrides are in memory only; it never
writes `controller_config.json` and it is not a Gate G1 run.

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/lapbudget.py 200 trace-g1

### 0. Measured lap time — the circuit is not 2 minutes

Wall clock (`started_at` → `ended_at` over `laps_completed`) across every real
block in `trace_data`. It includes the rolling start and any resets, so it
*over*-states a flying lap and is the right number for a session budget:

| pair | layout | length | blocks | s/lap | median |
|---|---|---|---|---|---|
| pair 1 | national | 2.60 km | 9 | 62–76 | **~70 s** |
| pair 2 | international | 2.95 km | 3 | 71–98 | **~80 s** |

A 15-lap block is **~17.5 min** of driving at National, not 30. The eval plan's
lap budget is wrong by nearly 2× **in TRACE's favour**.

### 1. Cutting the probe buys nothing — the lever is `required_passes`

`traversal_floor = 2 × required_passes + max(probe.laps, required_passes)`, from
`windowscan.py`, with `probe.laps` varied:

| window | probe.laps | floor (laps) | national | international |
|---|---|---|---|---|
| **3-of-4 (frozen)** | **3** | **9** | 10.5 min | 12.0 min |
| 3-of-4 | 2 | 9 | 10.5 min | 12.0 min |
| 3-of-4 | 1 | 9 | 10.5 min | 12.0 min |
| 2-of-3 | 3 | 7 | 8.2 min | 9.3 min |
| 2-of-3 | 2 | **6** | 7.0 min | 8.0 min |
| 4-of-6 | 3 | 12 | 14.0 min | 16.0 min |

**Shortening the probe while `probe.laps ≤ required_passes` changes the floor by
nothing**, because `_quorum_ready` gates `probe_to_removed` as well, so the probe
already costs `required_passes` laps of fresh evidence. It only starts buying
laps once `required_passes` has come down — and then it is worth exactly one lap.

### 2. The frozen window falls off a cliff below 15 laps

Typical improver, 3-of-4, probe 3, per element (braking / corner speed / apex):

| laps | removed | ended mid-probe (censored) |
|---|---|---|
| 10 | 0% / 0% / 0% | 0% / 10% / 24% |
| **12** | 0% / **2%** / 5% | 0% / **80%** / 71% |
| **15 (committed)** | 0% / **83%** / 74% | 0% / 16% / 24% |
| 18 | 0% / 99% / 94% | 0% / 1% / 6% |

At 12 laps the one element that traverses stops traversing: corner-speed removal
goes **83% → 2%** and 80% of blocks end mid-probe. The 15-lap figure is not a
comfortable margin — it is **three laps above a cliff**. Under the *measured*
apex novice the apex column is 0% at every budget, as `windowscan.py` already
found, so the whole budget question is a question about one element.

### 3. A shorter window restores it, at 12 laps

Measured apex model, corner-speed removal for a typical improver:

| window | probe | 12 laps | 15 laps |
|---|---|---|---|
| 3-of-4 (frozen) | 3 | 2% | 83% |
| 2-of-3 | 3 | 62% | 98% |
| **2-of-3** | **2** | **86%** | 100% |
| 2-of-4 | 2 | 89% | 100% |

Scored against G1's own three targets (`trace_kit.simulate.run`, committed
model, 200 streams/type/pair, seed `trace-g1`), **2-of-3 with a 2-lap probe
meets all three at 12 laps** — `share_traversing_2_of_3` 0.73, median 2 elements
removed, `non_improver.share_with_any_fade` 0.0, and the safety clause
`share_removed_despite_regression` **0.0**. The frozen 3-of-4 fails target 1 at
12 laps (0.0025).

### 4. What it costs — read this before adopting it

- **Probe-and-revert gets exercised far less.** `n_staggered_reversions` falls
  **799 → 227** (15 laps, 3-of-4 → 2-of-3 p2). The element is now often
  *removed* before a staggered regression onset arrives, so there is no reversion
  left to observe. The safety target still passes, but the mechanism the thesis
  is *about* appears in much less of the data.
- **The simulation cannot price the real cost.** `non_improver.share_with_any_fade`
  is 0.0 at *every* window length, so the false-advance margin looks free — but
  that model learner sits far outside the band by construction. The cost of a
  shorter window is **discriminability near the band edge**, which is exactly
  what `BAND_CALIBRATION_BRIEF.md` §E's minimal-detectable-change analysis
  (Weir 2005) is for, and what the repeated-looks inflation in `CLAUDE.md`
  thesis-correction item 8 is about. **A 3-pass window raises MDC₉₅ and the
  false-advance rate, and no simulated learner type can show it.** Do not adopt
  2-of-3 on these tables alone; adopt it on the G2 MDC analysis, for which this
  is the lap-budget constraint rather than the answer.
- **The probe is the retention test.** A 2-lap probe is 8 unassisted corner
  passes per element at National. Defensible, thinner, and a limitation to state.
- Any adoption edits `controller_config.json`, which re-pins its SHA-256 and
  **re-opens Gate G1** — re-run `simulate run` and re-review.

## `mdc.py` — how many passes a window needs before it can see a real change

Gate G2 item 8a (`BAND_CALIBRATION_BRIEF.md` §E), run 2026-10-15 because
`SESSION_BUDGET_BRIEF.md` made it the blocker for the protocol: Shape B's 12-lap
block needs a 3-pass qualification window, and the lap budget can only *point*
at one. The method is **minimal detectable change** (Weir 2005), adopted because
the review found no published rule for a bandwidth width.

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/mdc.py "<trace_data>"

σ_within is the pooled SD of **detrended** residuals over the seven
`_blocks.py` pair-1 National blocks, cells being (block, corner) series in
driving order, pooled by residual df, cells under 4 clean passes dropped.
**MDC95(n) = 1.96 × √2 × σ_within / √n.** Clamped brake initiations are excluded
as floors rather than measurements — there turned out to be **zero** of them in
this set, which rules that worry out rather than correcting for it.

### 1. Noise, reliability, and why this data cannot supply its own denominator

| metric | cells | n | df | σ_within | ICC(1,1) | median slope/pass |
|---|---|---|---|---|---|---|
| `brake_m` | 16 | 149 | 90 | **8.40 m** | 0.454 | −0.45 m |
| `speed_kmh` | 18 | 162 | 104 | **8.40 km/h** | 0.116 | −0.32 km/h |
| `apex_excess_m` | 18 | 162 | 104 | **2.25 m** | 0.099 | −0.04 m |

The two 8.40s are a coincidence in different units, checked per cell. The near-
zero slopes are the point of reporting them: these blocks are **pre-KR and the
driver was plateaued**, so they cannot supply an improvement-available figure
and the denominators below come from elsewhere, with provenance. The **ICCs of
0.12 and 0.10** say almost all variance in corner speed and apex is lap-to-lap
noise rather than stable corner-level state — the σ/band argument arriving from
measurement theory instead of from simulation.

### 2. Per corner, because the band and the qualification are per corner

A single pooled σ is the wrong unit — each corner is effectively a different
instrument, and corner 1 drags the pool (the zone `CLAUDE.md` records as
mis-annotated "taken flat" at drive-and-mark pace). `needs n` is the smallest
window whose MDC95 falls under the improvement available:

**`brake_m`** — available **8.19 m** (the KR diagnostic: CE +10.56 → +2.37 m)

| corner | n | σ_within | MDC95(3) | MDC95(4) | needs n |
|---|---|---|---|---|---|
| 1 | 38 | 12.63 m | 20.21 | 17.50 | **n ≥ 19** |
| 2 | 41 | 4.74 m | 7.58 | 6.56 | n ≥ 3 |
| 3 | 40 | 7.18 m | 11.48 | 9.94 | n ≥ 6 |
| 4 | 30 | 6.95 m | 11.13 | 9.64 | n ≥ 6 |

**`apex_excess_m`** — available **2.20 m** (`apexscan.py`)

| corner | n | σ_within | MDC95(3) | MDC95(4) | needs n |
|---|---|---|---|---|---|
| 1 | 40 | 1.73 m | 2.77 | 2.40 | n ≥ 5 |
| 2 | 41 | 2.35 m | 3.77 | 3.26 | n ≥ 9 |
| 3 | 40 | 3.23 m | 5.17 | 4.48 | **n ≥ 17** |
| 4 | 41 | 1.04 m | 1.66 | 1.44 | n ≥ 2 |

**`speed_kmh`** — **no anchor exists.** σ_within per corner is 12.81 / 5.94 /
6.65 / 6.56 km/h, so MDC95(3) is 20.51 / 9.51 / 10.64 / 10.49 km/h — and there
is nothing in the repo to compare them with. Nothing measures how much
corner-speed deviation a novice can recover; the 85% re-reference removed the
**bias** (+0.31 km/h), which is a different quantity.

### 3. What this licenses — and the answer is nothing, at either window

- **`2-of-3` is not licensed.** At a 3-pass window only **1 of 4** corners can
  resolve the available braking improvement, and only **1 of 4** the apex one.
  The quorum needs 3 of 4.
- **`3-of-4` is not licensed either**, and this is the finding that matters.
  At 4 passes it is still 1 of 4 corners on braking (corners 3 and 4 need 6,
  corner 1 needs 19) and 1 of 4 on apex. **The frozen window was never
  licensed at its own value**, so 2-of-3 does not cross a line that 3-of-4
  stayed behind: MDC95 grows by √(4/3) = **15%** between them.
- **The element Gate G1 rests on cannot be assessed at all.** `windowscan.py`
  shows corner speed is the only element that traverses (83% removal) — and it
  is the one metric with no improvement-available anchor. **Measuring that
  anchor is now the critical path**, not choosing a window.
- **Independent corroboration of why braking never traverses.** `windowscan.py`
  found 0% across every learner type and attributed it to the consistency gate
  plus σ/band = 0.80. MDC says the measurement itself cannot resolve the
  available improvement at any window the block affords. Two methods, same
  conclusion, different evidence.
- **A window median is worse, not better.** `CLAUDE.md` prefers a median for the
  right-skewed apex distribution; a median's standard error is ~1.25× a mean's
  on normal data, so every `needs n` above is optimistic for the statistic
  actually used.
- **MDC95 is a strict standard, deliberately.** The gates are a *heuristic
  trigger for running a probe*, not a measurement of learning, and the probe is
  the retention test — so 95% confidence in detecting individual change is a
  higher bar than the design claims to clear. The honest consequence is that
  **the window length is licensed by item 8b (contrasting-groups ROC with the
  cut at a stated false-pass rate), and MDC is reported as a limitation** on all
  three elements. That is §E's own ordering; this analysis establishes the size
  of the limitation rather than removing it.

### 4. The verdict turns on the CONFIDENCE LEVEL, which is a choice

MDC95 is strict by convention, not by necessity. `quorum` counts the corners
whose MDC falls under the improvement available; the element needs 3 of 4.

| metric | conf | needs n per corner (c1/c2/c3/c4) | quorum@3 | quorum@4 |
|---|---|---|---|---|
| braking | 95% | 19 / 3 / 6 / 6 | 1/4 | 1/4 |
| braking | 90% | 13 / 2 / 5 / 4 | 1/4 | 2/4 |
| braking | **80%** | 8 / 2 / 3 / 3 | **3/4** | **3/4** |
| apex | 95% | 5 / 9 / 17 / 2 | 1/4 | 1/4 |
| apex | 90% | 4 / 7 / 12 / 2 | 1/4 | 2/4 |
| apex | **80%** | 3 / 4 / 8 / 1 | 2/4 | **3/4** |

**At 95% neither 2-of-3 nor the frozen 3-of-4 reaches a braking quorum; at 80%
BOTH do.** So section 3 must be read as "MDC95 licenses neither", *not* as
"measurement theory forbids a 3-pass window" — the same sigmas license opposite
answers and nothing in the data picks the z.

That is an argument for item 8b rather than a result against the window. These
gates are a trigger for running a probe, not a certification, and the design's
own asymmetry — *premature withdrawal is worse than delayed* — is a statement
about the **false-pass rate**. Contrasting groups sets that rate explicitly and
reports the false-fail rate beside it; a conventional z only implies one.

### 5. Methods considered instead, and what the literature's own numbers say

Checked 2026-10-15 against the question *"is there a more sample-efficient
analysis?"*, since `BAND_CALIBRATION_BRIEF.md` §G's reading list was assembled
for a different question (how wide should a band be, not how few observations
can decide).

- **Sequential methods (SPRT, LC-CUSUM)** are the sample-efficient family, and
  `BAND_CALIBRATION_BRIEF.md` §E already records them as **considered and
  rejected** — on engineering cost (they rewrite both controllers and churn the
  golden-trace parity corpus), not on validity. The published counts are the
  useful part: LC-CUSUM competence decisions land at a **median of 13 procedures**
  for peribulbar blocks, **15 (8–25)** for bronchoscope-guided intubation,
  **14–27** for one gynaecological procedure, **56** in an outpatient
  hysteroscopy case, and **369 ± 70** for simulated cordocentesis. SPRT's own
  literature notes it does not bound the maximum sample and needs truncation.
  So the sequential family does not make a proficiency decision from 3–4
  observations either; **13–56 is the realistic order of magnitude.**
- **Generalizability theory (a G-study then a D-study on Φ, the dependability
  index for absolute decisions)** is the framework this project does not yet
  have and the one that fits its structure best: TRACE's design is literally
  crossed corner × lap, and a D-study answers *how many corners × how many laps*
  for a target Φ — which is the budget question in the right currency, and more
  than MDC can say. **It needs several drivers**, because Φ's numerator is
  between-person variance, so it is pilot (G2) work and not runnable on one
  researcher's blocks. The within-driver half of its inputs is already here:
  ICC(1,1) = 0.454 / 0.116 / 0.099.

**The structural finding these put together.** A 12-lap block at pair 1 yields
**4 corners × 12 laps = 48 corner passes per element** — inside the LC-CUSUM
literature's 13–56 range. But the architecture never looks at more than
**`window_passes` of them per corner**, and then votes across corners. The
sample is adequate; the *per-corner-then-quorum* structure is what spends it.
That is the strongest available argument for the sequential family, and it is a
different argument from the one §E rejected them on — so the rejection should be
re-recorded against this reasoning rather than left as-is.

## `feasible.py` — would anything fade? Real passes, real evaluator, real controller

Run 2026-10-15 to answer the question the 30-minute budget forces and no other
artefact in this repo answers: **inside a 12–15 lap block, driven by a real
novice, does any element ever leave `full`?** Every other feasibility number is
either synthetic (`simulate`, `windowscan`, `lapbudget`) or stops at the
criterion without asking what the state machine would do with it (`rescore`).
This replays **real recorded passes** through the **real evaluator** at candidate
floors and then the **real controller** at candidate windows.

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/feasible.py "<trace_data>"

Two block groups, never pooled: **pre-KR** (the seven `_blocks.py` blocks, no
error signal ever delivered) and **with-KR** (the three 2026-10-14 blocks —
short, n=1, driver knows the hypothesis, but bandwidth KR is in the apparatus
for both conditions now, so it is the population a participant belongs to).

### 1. Per-pass criterion rate on real passes

| floors (brake m / speed km/h / apex m) | group | braking | speed | apex |
|---|---|---|---|---|
| **frozen** 5 / 4 / 0.5 | pre-KR | **6.0%** | 67.9% | **7.4%** |
| frozen | with-KR | 21.1% | 65.3% | 8.3% |
| 10 / 8 / 1.5 | pre-KR | 32.9% | 78.4% | 43.2% |
| 10 / 8 / 1.5 | with-KR | 50.7% | 75.0% | 47.2% |
| 12 / 9 / 1.5 | pre-KR | 43.6% | 80.9% | 43.2% |
| 12 / 9 / 1.5 | with-KR | 57.7% | 75.0% | 47.2% |
| 15 / 11 / 1.5 | with-KR | 70.4% | 81.9% | 47.2% |
| 18 / 12 / 1.5 | with-KR | **80.3%** | 81.9% | 47.2% |

Two updates to figures quoted in `CLAUDE.md`. **Corner speed is 67.9% at the
frozen floors, not 31.5%** — that figure predates the one-sided `slow_only` gate
(2026-10-14), which fixed most of this element on its own. And **KR roughly
triples the braking rate at the frozen floors** (6.0% → 21.1%), which is the
§0A diagnostic showing up in a per-pass rate.

The apex rate stops improving above a 1.5 m floor because apex floors are capped
there on purpose: `CLAUDE.md` records that at `apex_m = 2.0` Gate G1 fails
outright (non-improvers fading goes 0% → 100%).

### 2. Controller replay — `engaged` (ever advanced) vs `ended>` (final stage above full)

`engaged` is the study's precondition: an element that never moves yields no
fade record and nothing for RQ1 to describe. `ended>` is lower wherever an
element advanced and then reverted — probe-and-revert working, not failing.
Real blocks average **6.3 laps** (range 5–11), so a 12–15 lap study block gives
roughly double this evidence and these figures **understate** it.

| floors | window | group | engaged b / s / a | median first-advance lap |
|---|---|---|---|---|
| **frozen** | 3-of-4 | pre-KR | **0 / 3 / 0** of 7 | – / 6 / – |
| **frozen** | 3-of-4 | with-KR | **0 / 2 / 0** of 3 | – / 4 / – |
| 12 / 9 / 1.5 | 3-of-4 | pre-KR | 2 / 5 / 1 of 7 | 11 / 5 / 13 |
| 12 / 9 / 1.5 | 2-of-3 | pre-KR | **4 / 5 / 3** of 7 | 7.5 / 2 / 6 |
| 12 / 9 / 1.5 | 2-of-3 | with-KR | **2 / 3 / 2** of 3 | 3 / 2 / 3 |
| 15 / 11 / 1.5 | 2-of-3 | pre-KR | 4 / 6 / 3 of 7 | 6.5 / 1.5 / 6 |

**At the frozen floors, braking and apex never advance in any real block, at
either window.** Corner speed advances in about half. That is the measured
status quo, and it matches the in-game M5 observation `CLAUDE.md` records.

### 3. The two levers do different jobs — this is the load-bearing result

Scored against Gate G1's own targets (`simulate.run`, **measured** apex novice,
200 streams/type/pair, seed `trace-g1`):

| laps | floors | window | G1-t1 traverse | share | non-improver false-fade |
|---|---|---|---|---|---|
| 12 | frozen | 3-of-4 | ✗ | 0.000 | **0.000** |
| 12 | frozen | 2-of-3 | ✗ | 0.000 | **0.000** |
| 12 | 12/9/1.5 | 3-of-4 | ✗ | 0.003 | 0.018 |
| 12 | 12/9/1.5 | 2-of-3 | ✗ | 0.430 | 0.052 |
| 12 | 15/11/1.5 | 2-of-3 | **✓** | 0.828 | 0.150 |
| 15 | 12/9/1.5 | 3-of-4 | ✗ | 0.087 | 0.018 |
| 15 | **12/9/1.5** | **2-of-3** | **✓** | **0.720** | **0.058** |
| 15 | 15/11/1.5 | 3-of-4 | **✓** | 0.515 | 0.080 |
| 15 | 15/11/1.5 | 2-of-3 | ✓ | 0.970 | 0.140 |

- **The floors decide whether an element ENGAGES.** At the frozen floors nothing
  engages at *any* window or lap count — 0.000 everywhere. The window was never
  the binding constraint on engagement.
- **The window decides whether it can COMPLETE the ladder** in the budget, which
  is the lap arithmetic in `lapbudget.py` (9 laps at 3-of-4, 6 at 2-of-3 p2).
- So the fear that *"all 12 laps run at full and the mechanism never engages"* is
  a **band-floor** problem, not a window problem — and it is the current config's
  actual behaviour rather than a risk.

### 4. Gate G1's second target is satisfied VACUOUSLY, and that is a finding

`non_improver_never_fades` is read strictly: `share_with_any_fade` must be
**0.000**. Only the frozen floors achieve that — and they achieve it by never
fading anything, for anyone. **A conservatism target is trivially met by a
system that never acts.** Every floor that makes the system work at all fails
target 2 as written, at 1.8% (12/9/1.5) to 15% (15/11/1.5 at 12 laps).

This is exactly what the contrasting-groups method replaces: a **stated**
false-pass rate with the false-fail rate reported beside it
(`BAND_CALIBRATION_BRIEF.md` §E, Jørgensen et al. 2018), rather than a
zero-tolerance clause that only an inert system can satisfy. **Target 2 needs
restating before it can be used to judge a working configuration.**

### 5. Limits on every number above

- Engagement figures: **n = 1 driver** (the researcher), blocks of 5–11 laps, and
  the three with-KR blocks are dev blocks driven by the person who built the
  system.
- False-fade figures: the **synthetic** non-improver. Its apex parameters are now
  the measured ones, but `brake_sigma_m` and `speed_sigma_kmh` remain
  assumptions.
- So these set the **pre-pilot feasibility envelope**, not the floors. The floors
  are still a Gate G2 contrasting-groups decision on pilot data, which is where
  they always belonged.

## `percornerscan.py` — what a per element × corner controller would buy

Written 2026-10-30 for the v9 novelty audit, step 2
(`novelty_audit/STEP2_directions.md` §3). Framing v9 §5.2 says the controller
fades "per element × per corner"; the frozen one fades per element on a
cross-corner quorum. v9's RQ2 is a probe-failure *rate*, so the question is how
many probes each design yields and what the per-corner design costs at G1's
bounds. The per-corner variant is the **real `Controller`, one instance per
corner** (denominator 1, so the quorum is "this corner is qualified"); streams
are paired, because `simulate_stream` draws every random number before the
controller steps. Pair 1 only. Never writes the config.

    python kit/tools/percornerscan.py 400 percorner 15

**Reproduction check:** element mode at seed `trace-g1`, 200 streams, both
pairs gives `mean_elements_removed` 1.85 (typical) and `share_any_fade` 0.0575
(non-improver), matching `simulation_report.json`. Note that the report's
`share_any_fade` is the **final** stage off full; ever-left-full on the same
streams is 0.1575. The script prints both (`endsoff`, `everleft`).

### 1. Frozen config (`frozen-g1b`, 2-of-3, 2-lap probe), 400 streams per type

| learner | controller | probes / participant | noise-only probe-fail (b / cs / apex) | non-improver ends off full | any removed (non-impr.) | removal despite regression (stag.) |
|---|---|---|---|---|---|---|
| typical | element | **2.83** | 0.16 / 0.00 / 0.53 | — | — | — |
| typical | corner | **11.59** | 0.40 / 0.00 / 0.62 | — | — | — |
| non-improver | element | 0.03 | — | **0.085** | 0.005 | — |
| non-improver | corner | 1.39 | — | **0.790** | **0.295** | — |
| staggered | element | 1.73 | — | — | — | **0.000** |
| staggered | corner | 7.83 | — | — | — | **0.055** |

Every probe failure is noise plus selection here, because the novice model has no
cue-dependency term: the failure column is v9 §7.3's noise-only null, under the
committed model.

### 2. A stricter per-corner window does not rescue it (300 streams per type)

| ctrl | window | probes (typ.) | non-improver ends off full (≤ 0.10) | non-improver any removed | removal despite regression (≤ 0.02) |
|---|---|---|---|---|---|
| E | 2-of-3 | 2.83 | 0.097 | 0.003 | 0.000 |
| C | 2-of-3 | 11.54 | 0.797 | 0.313 | 0.043 |
| C | 3-of-3 | 6.56 | 0.517 | 0.073 | 0.123 |
| C | 3-of-4 | 7.38 | 0.620 | 0.103 | 0.127 |
| C | 4-of-5 | 5.11 | 0.530 | 0.023 | 0.160 |
| C | 5-of-5 | 4.09 | 0.223 | 0.003 | 0.060 |

**No per-corner window meets either G1 bound.** Tightening it cuts false fades
but makes removal-despite-regression *worse*, because a longer ladder puts
removal after the lap-7 regression onsets: the same mechanism that sank every
3-of-4 alternative under the element controller. `probe.laps` 2 → 3 changes
nothing (quorum readiness at `required_passes` gates `probe_to_removed`, as
`windowscan.py` already found).

### 3. What it means

- **Per corner buys events by fading on noise.** It quadruples probes, but the
  extra ones come from the per-pass noise the quorum was added to average
  (ICC 0.12 / 0.10, `mdc.py`). It is ruled out *as the deployed controller*.
- **The element controller yields more probes than the step-2 doc estimated.**
  It is 2.83 per typical participant, about 42 at n = 15, giving a pooled
  95% CI of ±0.12. Per element that is ~16 / 15 / 11 events (braking / corner
  speed / apex), with CIs of ±0.2 or wider. F3's 80 probes needs ~28 typical
  participants.
- **The noise-only null differs sharply by element.** Corner speed probes never
  fail under noise (σ/band 0.5), so any observed failure there would be
  dependency, *if* the model's speed sigma is right. Apex fails 53% under noise
  alone, so a dependency excess there is nearly undetectable at these counts.
  **Braking (16%) is the element where Δ is best identified.**
- Limits: the synthetic novice; `brake_sigma_m` and `speed_sigma_kmh` are still
  assumptions. Corner-speed's 0.00 null depends entirely on that sigma.

## `nullrecovery.py` — can the RQ2 null be identified? (roadmap R2)

Written 2026-10-30 for ARS review roadmap item R2 (methodology W1). It is a
parameter-recovery study. Synthetic participants (n = 15 per study) come from a
known model: an exponential or power-law trend, with noise at 0.5× / 1× / 2× the
committed sigmas. They drive the real controller for a 15-lap block plus the
4-lap unassisted block. Each candidate null (form × σ pooling × fit set) is fitted
to what the study would see. Its P_hat is compared with P_true on paired common
random numbers. **Pass criterion, fixed before the first run:** braking
RMSE(P_hat − P_true) ≤ 0.045 in every cell. Never writes the config.

    python kit/tools/nullrecovery.py 100 30 nullrecovery 15

**Run 2026-10-30, 100 studies per cell, 30 replicates per participant (676 s):
NO candidate passes the pre-stated criterion.**

- **Every ×2.0 cell fails, for every form.** There, braking P_true ≈ 0.53 and
  probes per participant ≈ 0.2, so braking becomes as uninformative as apex. That
  is a design limit, not a fitting limit.
- **At ×0.5–×1.0, only `exp_driver / driver σ / hybrid` stays ≤ 0.045** (worst
  0.043). Hybrid fits the trend on ALL laps, cue-on included, which re-opens the
  R5 question.
- **The brief's own fit set (`cueoff`) misses narrowly at ×1.0.** Worst cases:
  exp_pooled 0.048, lin 0.053, exp_driver 0.059.
- **`unassisted`-only fits are worse.** RMSE is 0.06–0.12, and per-driver
  exponential trends extrapolate back to the guided laps with errors of ~5σ.
- **Pooled σ fails badly at high noise** (bias about +0.25 at ×2.0). Per-driver σ
  is the better F6 choice.
- **Apex: a Gaussian residual recovers σ at only ~0.6×**, because RMS is a
  magnitude folded at zero. The apex null needs a magnitude-aware noise form
  (folded or log-normal) whatever else is decided.
- **SD of P_obs − P_true for braking is 0.13–0.14 at ×1.0**, not the 0.09 the
  criterion assumed. Only ~11 braking probes per study were decided, because this
  population includes non-learners.

**OPEN:** part of every RMSE above is Monte Carlo noise from 30 replicates. The
×1.0 cells are being re-run at 100 replicates
(`nullrecovery.py 100 100 nullrecovery 15 1.0`) to separate it. If the `cueoff`
forms drop under 0.045 there, the brief's design is recoverable at ≤ 1× noise.
R2 is not closed until that is read and the author picks the form-selection rule.

**Rerun 2026-10-30: ×1.0 cells only, 100 replicates (731 s).** This resolves the
open item above. Moving from 30 to 100 replicates barely changes the RMSEs, so
they are recovery error, not Monte Carlo noise. The ×1.0 braking criterion is now
met by:
- **`exp_pooled / driver σ / cueoff`** (worst 0.043). This is the brief's own
  fit set, with one exponential rate shared across participants, per-driver
  amplitudes and per-driver σ.
- **`exp_driver / driver σ / hybrid`** (worst 0.035).

`lin_driver / driver / cueoff` misses at 0.046, and every `unassisted`-only fit
fails. So the brief's cue-off design is recoverable up to 1× noise **only with
the trend's rate partially pooled across drivers**, which is R1's "stronger"
remedy. Above that noise level nothing is recoverable.

## `nullabsorption.py`: how much real dependency does each null hide? (roadmap R5)

Written 2026-10-30 for ARS review roadmap item R5 (DA C1; methodology W3,
domain W2, perspective W6). **Author definition:** a mean shift on withdrawal and
a variance increase on withdrawal BOTH count as guidance dependency.

**Method.** A known dependency is injected on every pass driven with an element
hidden. The mean moves by δ × band in the novice direction and the noise is
scaled by κ. The learner is the exponential one at 1× noise, pair 1. The table
reports attenuation = est. Δ / true Δ, where 1 means nothing is absorbed. It is
computed on the expected P_obs, so the absorption is separated from sampling
error. Never writes the config.

    python kit/tools/nullabsorption.py 100 40 nullabsorption 15
    python kit/tools/nullabsorption.py 100 40 nullabsorption 15 0.0:1.0   # recovery check

**Run 2026-10-30, 100 studies per cell, 40 replicates (514 s + 56 s).**
Braking attenuation by null:

| δ (band) | κ | true Δ | primary (cue-off, pooled rate) | lopo | hybrid | cue-on |
|---|---|---|---|---|---|---|
| 0 | 1.5 | 0.232 | 0.26 | 0.31 | 0.39 | 1.04 |
| 0 | 2.0 | 0.445 | 0.25 | 0.30 | 0.30 | 1.02 |
| 0.5 | 1.0 | 0.301 | 0.79 | 0.82 | 0.07 | 1.03 |
| 0.5 | 1.5 | 0.466 | 0.54 | 0.58 | 0.16 | 1.02 |
| 0.5 | 2.0 | 0.597 | 0.34 | 0.41 | 0.12 | 1.01 |
| 1.0 | 1.0 | 0.827 | 0.37 | 0.47 | 0.43 | 1.01 |
| 1.0 | 2.0 | 0.806 | 0.22 | 0.36 | 0.25 | 1.01 |

The braking recovery check, with no dependency at δ = 0 and κ = 1, gives
RMSE(P̂ − P_true) of **cue-on 0.027**, primary 0.045, lopo 0.051 and hybrid
0.032.

- **The R2 primary (cue-off) hides 20–80% of a real braking dependency.** It is
  worst on a variance increase, where only ~25% survives, because a cue-off σ
  simply learns the larger noise.
- **Leaving each participant's own probes out barely helps** (+0.03 to +0.14).
  The shared rate and the unassisted block still carry the dependency.
- **The hybrid fit is the worst at a mean shift** (0.07). An all-laps
  exponential bends to fit the shifted late laps.
- **The cue-on null is unbiased for braking and corner speed** (1.00–1.04), and
  it is the MOST recoverable braking null (0.027 ≤ 0.045). It was not tested at
  2× noise.
- **On apex the cue-on null is biased UP** (1.2–1.9, and P̂ is 0.17 low with no
  dependency). This is the Gaussian-on-a-folded-RMS problem from
  `nullrecovery.py`, so the apex noise form has to be fixed before any apex Δ
  means anything.
- **The sampling SD of the observed braking Δ is 0.12–0.31.** At δ = 0.5 band
  (true Δ ≈ 0.30) an excess is roughly at the edge of detectability with
  n = 15.

**What the cue-on null costs.**
- **The definition widens.** Δ now includes the loss of any performance benefit
  the guidance gave *while it was on* (performance with guidance minus without).
  That is the author's definition, but the RQ2 construct text and roadmap items
  R8/R9 must say so.
- **The cue-on model check becomes in-sample.** v9 §7.3 step 5 says the null
  must reproduce the cue-on statistics, but those are now the statistics it was
  fitted on. So it needs held-out targets (methodology W2). **Cue-off statistics
  are NOT one of them:** under this definition a dependency makes them differ by
  design, so a cue-off check would reject the null exactly when the effect
  exists. The resolved check is in `novelty_audit/review/CONCEPT_BRIEF_v9.md` §5.

## `nullcheck.py`: does the RQ2 model check catch a wrong null? (roadmap R3/R4)

Written 2026-10-30 to measure the power of the model check specified in
`novelty_audit/review/CONCEPT_BRIEF_v9.md` §5. The three checks are:
- **S1:** 5-fold-by-lap 80% predictive coverage;
- **S2:** the post-qualification pass rate;
- **S3:** lag-1 residual autocorrelation.

A check fails at |z| > 2.39 against M simulated studies from the fitted cue-on
null (95% Bonferroni over three). Four truths were tested, none with a
dependency: `correct` (the null's own form), `ar1` (ρ = 0.5), `heavy` (t3
noise) and `power` (a power-law trend). The last column is the misspecified
null's own error, which says whether that misspecification actually harms
P_null.

    python kit/tools/nullcheck.py 100 60 20 nullcheck 15

**Run 2026-10-30, 100 studies per truth, M = 60 (1125 s). Braking:**

| truth | S1 | S2 | S3 | any fails | P̂ − P_true RMSE | harmful (> 0.045)? |
|---|---|---|---|---|---|---|
| correct | 0.03 | 0.02 | 0.01 | **0.06** (false alarm) | 0.030 | no |
| ar1 | 0.07 | 0.12 | 1.00 | **1.00** | 0.035 | no |
| heavy | 0.93 | 0.22 | 0.02 | **0.93** | 0.035 | no |
| power | 0.47 | 0.01 | 0.18 | **0.56** | 0.058 | **yes** |

Corner speed has a 0.08 false-alarm rate. On apex, the Gaussian null is wrong
under every truth (P̂ bias of −0.15 to −0.19), and the check catches it in only
15–17% of studies.

**THE CHECK'S SENSITIVITY IS MISALIGNED WITH HARM.**
- The false-alarm rate is on target (0.06).
- But it rejects AR(1) and heavy-tailed nulls almost always, even though those
  misspecifications leave the braking P̂ inside R2's 0.045 bound. That would
  throw away Δ for nothing.
- It catches only 56% of the misspecification that does harm (the trend form).
- It misses the apex problem 85% of the time.

**What follows:** "fail → abandon Δ" is the wrong rule. A revision is pending an
author decision (2026-10-30).

### `nullabsorption.py` with dependency at reduced salience (r = 0.5)

Reduced salience is a partial withdrawal. In this run, half of the dependency
(shift × 0.5, κ → 1 + 0.5(κ − 1)) also appears on passes driven at `reduced`.
The new `cuefull` null is fitted on full-salience laps only.

    python kit/tools/nullabsorption.py 100 40 nullabsorption 15 0.0:1.0,0.5:1.0,0.0:1.5,0.5:1.5,1.0:1.0 0.5

**Run 2026-10-30, 100 studies per cell, 40 replicates (365 s). Braking
attenuation:**

| δ | κ | true Δ | cueon (full + reduced) | cuefull |
|---|---|---|---|---|
| 0.5 | 1.0 | 0.093 | 0.80 | 1.11 |
| 0 | 1.5 | 0.226 | 0.89 | 1.04 |
| 0.5 | 1.5 | 0.315 | 0.81 | 1.03 |
| 1.0 | 1.0 | 0.721 | 0.74 | 1.01 |

Recovery with no dependency gives RMSE: cueon 0.029, cuefull 0.032.

- **If reduced salience carries part of the dependency, the full+reduced null
  absorbs 11–26% of braking Δ**, and 5% of corner-speed Δ.
- **The full-only null stays unbiased** (braking 1.01–1.11, corner speed
  0.99–1.00). It costs only 0.003 of recovery RMSE and stays inside R2's
  0.045.
- **Apex:** both cue-on nulls overstate Δ, for the Gaussian-on-RMS reason
  already recorded.

### `nullcheck.py`, revised rule (escalation + trend bracket), full-salience null

    python kit/tools/nullcheck.py 100 60 20 nullcheck2 15

**Run 2026-10-30, 100 studies per truth, M = 60, 20 replicates (1477 s).
Braking:**

| truth | checks fail at first | pass after escalation | bracket agrees | Δ kept | P_null RMSE: kept / dropped |
|---|---|---|---|---|---|
| correct | 0.07 | **0.95** | **0.31** | 0.29 | 0.059 / 0.044 |
| ar1 | 1.00 | **0.88** | 0.33 | 0.31 | 0.033 / 0.036 |
| heavy | 0.83 | 0.61 | 0.25 | 0.13 | 0.042 / 0.044 |
| power | 0.43 | 0.65 | **0.62** | 0.43 | 0.045 / 0.056 |

- **The escalation works.** The false-alarm rate is still ~5%. After one
  escalation, an autocorrelated null passes 88% of the time, against 0% before
  (heavy tails: 61%). Corner speed: 86–93% kept under every truth.
- **The trend bracket does NOT work: drop it as a gate.**
  - It rejects 69% of studies whose exponential null is CORRECT, and it agrees
    MORE often under a power-law truth (62%) than under the correct one (31%).
  - The estimates it keeps are no more accurate than the ones it drops.
  - So it measures how unstable a power-law fit is on a driver's few
    full-salience laps, not whether the exponential null is wrong.
- **Read the RMSE column with care.** Here P_true and P̂ are NOT paired (the
  truth uses its own noise draws), so ~0.035 of each RMSE is Monte Carlo noise
  at 20 replicates. The paired figure for this null is 0.032
  (`nullabsorption.py`).
- **Apex is kept in only 15–38% of studies** (bracket) and its P_null error is
  0.10–0.25 whatever the rule. Its noise form is a G2 decision.

## `nulltransient.py`: transient withdrawal dip vs sustained deficit (roadmap R8)

Written 2026-10-30 for ARS review roadmap R8 (methodology W8, domain W1, DA M3).
The null excludes both dependency and a transient effect of withdrawal
(surprise, attention, the immediate dip), and the only internal contrast is
time. All three statistics are standardised residuals against the primary
(full-salience) null:
- **T_p:** first probe lap − second probe lap.
- **T_u:** unassisted lap 1 − laps 2–4, for elements still visible at the end of
  training.
- **L_u:** the late unassisted level (laps 2–4).

Each was tested with a one-sided t-test over participants. Shift sizes vary
between drivers (× U(0, 2)).

    python kit/tools/nulltransient.py 1000 nulltransient 15

**Run 2026-10-30, 1000 studies per scenario (48 s).** Share of studies in which
the statistic is significant:

| scenario | δ (band) | braking T_p | braking T_u | braking L_u | corner speed T_p | corner speed L_u |
|---|---|---|---|---|---|---|
| none | 0 | 0.06 | 0.08 | 0.06 | 0.06 | 0.02 |
| sustained | 0.25 | 0.05 | 0.05 | **0.94** | 0.05 | 0.22 |
| sustained | 0.5 | 0.06 | 0.07 | **1.00** | 0.05 | 0.82 |
| transient (1 lap) | 0.25 | **0.74** | 0.56 | 0.06 | **0.96** | 0.03 |
| transient (1 lap) | 0.5 | **0.96** | 0.84 | 0.05 | **1.00** | 0.02 |

- **The time profile separates the two cleanly for braking.** A transient raises
  T_p and leaves L_u at its false-alarm rate. A sustained deficit raises L_u and
  leaves T_p and T_u at theirs.
- **The probe-truncation bias I expected did NOT appear.** A sustained,
  heterogeneous deficit leaves T_p at 0.05, so T_p is usable and is the more
  powerful of the two decay statistics.
- **Corner speed: T_u is unusable.** Only 1.5–4 participants still have the
  element visible at the end of training. T_p is strong (0.96–1.00), but L_u
  detects a sustained deficit only at 0.5 band.
- **Apex: unusable.** L_u is significant in 78% of studies with NO dependency,
  which is the apex null's Gaussian-on-RMS bias again.
- **The reading is asymmetric.** A decaying profile fits a transient, but it
  also fits dependency that the learner quickly re-acquires without guidance.
  A sustained profile argues against a pure transient.

## `nulldecision.py`: censoring rule (R7) and design sensitivity of Δ (R6)

Written 2026-10-30 for ARS review roadmap R6/R7 (methodology W5/W6,
perspective W4, DA M2/M5).
- **Δ̂** = P_obs − P̂_null. P_obs comes from one stream per participant, and
  P̂_null from the full-salience primary null.
- **Interval:** a 90% participant cluster bootstrap. It does not resample the
  within-participant fit, so it is somewhat optimistic.
- **True Δ:** from the true parameters, with and without the dependency.
- **Dependency:** sustained, varying between drivers (× U(0, 2)).

    python kit/tools/nulldecision.py 300 30 1000 nulldecision 15

**Run 2026-10-30, 300 studies per cell, 30 replicates, B = 1000 (331 s).**

**R7, censoring (braking).** 12–20% of braking probes are censored. Corner
speed has none.
- **Every rule is unbiased against its own true Δ** (|bias| ≤ 0.02) when it is
  applied identically to P_obs and P_null. The trend-dependent bias the review
  feared cancels out under identical application.
- **The rules differ in scale, not validity.** At δ = 0.5 band the true Δ is
  0.37 under exclude, 0.27 under as-pass and 0.34 under as-fail.

**R6, braking, exclude rule:**

| δ (band) | true Δ | median 90% CI width | P(excess) | P(no excess, MDI 0.10) | P(indeterminate) |
|---|---|---|---|---|---|
| 0 | 0.000 | 0.34 | **0.04** | 0.29 | 0.67 |
| 0.125 | 0.006 | 0.37 | 0.03 | 0.25 | 0.72 |
| 0.25 | 0.078 | 0.40 | 0.10 | 0.15 | 0.76 |
| 0.375 | 0.239 | 0.49 | 0.45 | 0.03 | 0.52 |
| 0.5 | 0.366 | 0.50 | 0.67 | 0.00 | 0.32 |

- **The false "excess" rate is calibrated at 4%.**
- **At n = 15, braking resolves only large excesses.** Detection is 45% at
  Δ = 0.24 and 67% at Δ = 0.37, so 80% power needs Δ ≳ 0.4. With no dependency
  the usual verdict is **indeterminate** (67%), not "no excess".
- **A rough √n extrapolation:** 80% power at Δ ≈ 0.24 needs n ≈ 36.

**Corner speed resolves better than braking** because its P_null is ≈ 0:
- the CI is ~0.01 wide with no dependency;
- the verdict is "no excess" in 95% of studies with no dependency;
- detection is 83% at Δ = 0.36.

That rests on the assumed speed σ.

**Apex** is biased by +0.11 to +0.17 under every rule (the null's
Gaussian-on-RMS problem), so it gets no verdict.
