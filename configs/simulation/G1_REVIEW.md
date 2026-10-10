# Gate G1 — simulation feasibility review

Gate G1 (evaluation plan v2, Phase 1) is the gate M4 closes.

> **Gate G1.** All three design targets met; otherwise revise window/thresholds
> (or block length) and re-run.

**Status: MET (2026-09-08).** Configuration frozen as `frozen-g1`, SHA-256
`c10fadc8ad8518902d4a7e3db1a581afbc003598a95fd47d0d07dbf30b345650`.

> **Re-pinned at M5, same verdict.** M5 added `salience.reduced_form` to
> `controller_config.json` (the reduced-salience visual form, which impl plan
> section 7 left open for M5 and which has to be frozen and hashed before the
> pilot because it is an RQ3 interview topic). That changes the file's hash, so
> the simulation was re-run and this file re-pinned. It cannot change the
> verdict, and did not: `salience` is read only by `lib/markers` and `lib/hud`
> — the controller and the evaluator never touch it — and every measured number
> in `simulation_report.json` came back identical, digit for digit, across all
> 2,800 streams. The earlier hash was
> `c7f9ca964bdeb9d6337e84a2565b214e7765385d267ed74fab7d8cdcb4020ba9`. The rule
> this follows: the config's identity is its `config_id` plus its hash, so any
> edit re-pins, and `test_m4_simulate.py` fails until it does.

Reproduce with:

    cd kit
    python -m trace_kit.simulate run --streams 200 --out ../configs/simulation
    python -m trace_kit.simulate sweep --streams 25 --out ../configs/simulation

Both are deterministic from their seed (`trace-g1`). `simulation_report.json`,
`sweep_report.json` and `feasibility_figure.svg` in this folder are the committed
outputs of exactly those two commands.

---

## What was simulated

2,800 streams: seven learner types × two car-track pairs × 200 streams each, 15
laps per stream. Every stream runs against a **committed reference table**
(`configs/references/reference_pair{1,2}.json`), so the corner counts and quorum
denominators are the ones participants face — 4 corners at National, 5 at
International, all with braking zones — rather than a synthetic circuit.

The streams are fed through the **real** controller and evaluator
(`trace_kit.controller`, `trace_kit.evaluator`), each pinned to its Lua
counterpart by `kit/tests/test_m4_controller_parity.py` and
`kit/tests/test_m4_evaluator.py`. That pinning is what makes a simulated gate
mean anything: without it G1 would certify a controller participants never drive
(impl plan §6).

The synthetic novice, its parameters, and their provenance are documented at the
top of `kit/trace_kit/simulate.py` and echoed into `simulation_report.json`. Only
one parameter has an empirical anchor — the initial brake offset, from the Gate
G0 review's measured novice brake points (27.7 m early to 27.2 m late). The rest,
and the three lap-to-lap sigmas in particular, are **stated assumptions**, and
they are what Gate G2 replaces with measured pilot variance.

---

## The three design targets

| # | Target | Measured | Verdict |
|---|---|---|---|
| 1 | A typical improver traverses full → reduced → probe → removed for ≥ 2 of 3 elements within one block | 59.3% of `typical_improver` streams; median 2 of 3 elements removed | **met** (bar: median stream, i.e. ≥ 50%) |
| 2 | A non-improver never leaves full salience | 0.00% of `non_improver` streams moved any element | **met** (read strictly: no tolerable failures) |
| 3 | Regression reverts promptly, and is never answered by removal | median excess latency 0 laps (synchronised) and 0 laps (staggered) over the arithmetic floor; 0.00% removed once regression was detectable | **met** |

The eval plan states the targets qualitatively; how each was turned into a number
is recorded in `simulation_report.json` under `targets[].operationalisation`, so
a reader can disagree with a bar without reverse-engineering it.

### Behaviour by learner type

| learner type | mean elements removed | any fade | median removal lap | any reversion | cap reached | censored |
|---|---|---|---|---|---|---|
| fast_improver | 1.88 | 100% | 11 | 6.8% | 0% | 12.0% |
| typical_improver | 1.56 | 100% | 13 | 5.0% | 0% | 38.3% |
| slow_improver | 0.01 | 88.8% | 14 | 0% | 0% | 16.3% |
| non_improver | 0.00 | 0% | — | 0% | 0% | 0% |
| erratic | 0.01 | 53.3% | 12.5 | 4.3% | 0% | 3.0% |
| synchronised_regressor | 0.00 | 1.5% | — | 1.5% | 0% | 0% |
| staggered_regressor | 0.00 | 44.3% | 9 | 44.3% | 0% | 0% |

`feasibility_figure.svg` plots the mean controller stage per element against lap
for each type. It is the thesis figure the eval plan lists as a Phase 1 output.

---

## What the calibration changed, and what it did not

The sweep evaluated 144 configurations over the four free parameters
(`band_floors.braking_m`, `band_floors.corner_speed_kmh`, `band_floors.apex_m`,
`criteria.consistency_delta_ratio`); 34 met every target. The selection rule
takes the **tightest** passing configuration — the least total relaxation
relative to the provisional defaults — because a loose band fades a scaffold for
a learner who has not earned it, which the design says is the worse failure.

**Exactly one parameter moved:**

| parameter | provisional | frozen | why |
|---|---|---|---|
| `band_floors.corner_speed_kmh` | 3.0 | **4.0** | The single binding constraint on target 1. At 3.0 only 15% of typical improvers traverse two elements; at 3.5, 38%; at 4.0, 59.8%. Nothing else in the grid moved target 1 while target 2 still held. |

Everything else keeps its framing-v6 default: braking floor 5.0 m, apex floor
0.5 m, consistency delta ratio 0.5, the 3-of-4 window, the 2-failure
de-qualification rule, the 75%/50% quorum thresholds, the 3-lap probe, the
reversion cap of 2. The qualification window, quorum thresholds and probe rules
were **not** swept: they are structural choices framing v6 argues for, and moving
them would change the mechanism rather than calibrate it.

`evm.ai` (3.0) and `evm.human` (1.25) are also unchanged and remain
**provisional** — the eval plan finalises them at Gate G2, and the AI's measured
σ sits under every floor anyway, so they do almost nothing at present.

---

## Findings that belong in the thesis

Three things the simulation established that are not just parameter values.

**1. Two rules had to be added for the machine to work at all, and the golden
traces are why they were found.** Framing v6 specifies the stages, the evidence
rules and the quorum, but two gaps only appear when the machine is actually run:

- *Quorum readiness.* The re-qualification reset drops the qualified share to
  zero on every advance, which is below the revert threshold — so without a rule,
  the pass right after an advance would revert it. The controller therefore does
  not evaluate quorum until every applicable corner holds `required_passes` of
  evidence.
- *One regression, one stage.* A reversion leaves the element one stage down with
  the same sub-threshold share that caused it, so the next pass reverted it
  again, and a deep collapse cascaded to full in two passes — which also made the
  reversion cap unreachable. The revert check is now disarmed after a reversion
  until the share recovers.

Both are documented in full in `lua/trace_rt/lib/controller.lua` and each has a
golden trace. They are design decisions, not implementation details, and belong
in the system chapter.

**2. The eval plan's staggered-reversion target was below its own arithmetic
floor.** "Within two laps when regression is staggered" is not reachable by any
threshold setting: with onsets one lap apart across four corners, a *majority*
has not regressed until the third lap, and a corner cannot de-qualify until its
second consecutive failure. The measured median lag from the first corner's onset
is 3 laps, and no configuration in the sweep changed that. Target 3 is therefore
measured as **excess latency over that floor**, which the controller does meet at
zero excess — and which reproduces the eval plan's own one-lap figure exactly for
synchronised regression. The eval plan's wording should be corrected rather than
the controller retuned.

**3. Under this novice model the corner-speed criterion, not braking, is what
gates the fade.** The braking and apex floors were already permissive enough; the
3 km/h corner-speed floor was where typical improvers stalled. That points Gate
G2's calibration effort at the corner-speed distribution first. It is also a
reminder of how much rests on the assumed lap-to-lap sigmas: rerun any of this
with `--model speed_sigma_kmh=…` and the binding constraint can move.

---

## Limitations of this gate, stated

- **The novice model is an assumption, not data.** One of its eight parameters
  has an empirical anchor. G1 certifies that the controller behaves as designed
  *against a plausible learner*; it does not certify that real novices are that
  learner. That is Gate G2's job, and eval plan v2 already routes a G2 failure
  back to this simulation.
- **`share_all_three_removed` is 0.0% for every type.** No simulated learner
  clears all three elements inside 15 laps. The target asks for 2 of 3, and the
  block is time-boxed, so this is within design — but it means the study should
  expect *partial* traversal to be the common case, and RQ1's trajectory figures
  should be built for that rather than for full traversal.
- **38% of typical improvers end mid-probe (censored).** With a 15-lap block that
  is the expected consequence of a machine that needs ~9-13 laps to traverse.
  The censoring semantics exist for exactly this and the rate is worth quoting in
  the methods chapter, since it sets how much of RQ1's probe-outcome table will be
  right-censored.
- **The reversion cap was never reached** by any of the 2,800 streams, including
  the erratic type. It remains an untested-in-practice safeguard, exercised only
  by the `erratic_cap_reached` golden trace.
