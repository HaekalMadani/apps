# Golden traces — the controller parity corpus

The fading controller exists **twice**:

- `lua/trace_rt/lib/controller.lua` — runs inside Assetto Corsa; the code
  participants actually drive.
- `kit/trace_kit/controller.py` — runs the Phase 1 simulation that tunes and
  certifies it.

Implementation plan §6 names the divergence between them as the risk that
*silently* invalidates Gate G1: the simulation would certify a controller nobody
experiences, and nothing would look wrong. This folder is the mitigation.

Each file here is one case: a sequence of per-pass criterion booleans, plus the
exact controller event sequence and final state both implementations must
produce. `kit/tests/test_m4_controller_parity.py` runs every trace through both
(the Lua headless via lupa/LuaJIT 2.1, matching CSP) and requires them to agree
with each other **and** with the committed expectations.

Impl plan §3's rule applies here: *runtime and simulator share no state except
`controller_config.json` and these traces.*

## The corpus

| trace | what it pins |
|---|---|
| `fast_improver` | The lap-budget case: a full traverse in **6 laps** at `frozen-g1b` (it was 9 at `frozen-g1`), and the dwell at reduced that the re-qualification reset enforces. The test computes the floor from the config rather than quoting a number. |
| `non_improver` | Design target 2 — never leaves full salience, emits no events at all. |
| `alternating_corner` | The acknowledged hysteresis pathology (framing v6): a corner failing every *other* pass never accumulates two consecutive failures, so it never de-qualifies. **Its direction INVERTED at `frozen-g1b`:** alternating yields ceil(n/2) of n, so it was 2 of 4 and stalled under 3-of-4, and is 2 of 3 and **qualifies** under 2-of-3. An accepted design cost, not a bug — see the test and `SESSION_BUDGET_BRIEF.md` section K. The honest consequence is unchanged: at a four-corner denominator the other three carry exactly 0.75 on their own, so the element fades either way. |
| `midwindow_requalification_reset` | An advance landing while evidence windows are unevenly filled, and the quorum-readiness rule waiting for the lagging corner. |
| `block_end_mid_probe` | Censoring: a block ending mid-probe is right-censored and the stage stays `probe`. |
| `erratic_cap_reached` | Two probe reversions, the reversion cap, and the element pinned at reduced for the rest of the block. |
| `zero_applicable_braking` | The degenerate element (impl plan §7): zero applicable corners is *disabled*, not a division by zero. |
| `staggered_regression` | Regression onset spread one corner per lap — the honest shape, and the stream eval plan v2 added. |
| `null_criteria_stall` | A corner that yields no metric at all stalls its element instead of fading it. The conservative direction of the null-is-no-evidence rule, and the residual risk it accepts. |
| `reduced_to_full_revert` | The hysteresis dead band holding at a share of exactly 0.5, then a genuine de-qualification-driven reversion. |
| `no_requalify_degenerate` | The degenerate machine the re-qualification rule prevents, run deliberately with the flag off: the element advances twice in two laps and the reduced stage is a cosmetic waypoint. The rule's justification as a runnable demonstration rather than a claim in a document. |

Each file carries its own `description` field saying the same thing, so a trace
that fails in CI explains itself without this table.

## Re-authoring

`generate.py` writes the corpus. It exists for convenience; **the committed JSON
is the contract**, and the test suite never reads the generator.

    python golden_traces/generate.py

Re-run it only to add a case or after a *deliberate* rule change, and read the
resulting diff against the specification when you do. The expectations are
produced by the Python implementation, so a bug there would be baked straight
into the corpus. That is why the parity test also carries hand-written,
spec-level assertions that never touch the stored blobs — a lap budget, an event
ordering, a stage sequence, "no element ever skips a stage" — which a corpus
regenerated around a bug would still have to get past.

Files are validated against `schemas/golden_trace.schema.json` like every other
format in the repository.

## Three rules the corpus found

The traces are not only a regression net; two of the controller's rules exist
*because* running the corpus exposed a broken machine, and one is demonstrated by
it. All three are documented in full at the top of `controller.lua`:

1. **Quorum readiness.** The re-qualification reset drops the qualified share to
   zero on every advance, which is below the revert threshold — so the pass right
   after an advance would have reverted it.
2. **One regression, one stage.** A reversion left the element one stage down
   holding the same sub-threshold share, so the next pass reverted it again; a
   deep collapse cascaded two stages in two passes, and the reversion cap could
   never be reached.
3. **Re-qualification on advance** is framing v6's, not a discovery — but
   `no_requalify_degenerate` is what makes its necessity checkable rather than
   argued.

## Re-timing after a calibration change (added 2026-10-15)

Several cases have to place an event at a precise point on the ladder — a
collapse *inside* a probe, a block ending *mid*-probe, a regression onset
arriving before removal can complete. Those points used to be written out as lap
numbers tuned to `frozen-g1`'s 9-lap ladder. When `frozen-g1b` shortened the
ladder to 6, the numbers silently stopped meaning what their names said:

- `block_end_mid_probe` ran past its probe and ended at `removed`, censoring
  nothing;
- `erratic_cap_reached` never reverted, so it never reached the cap;
- `staggered_regression` had already removed the element before the first onset.

**Three cases went on passing their own committed blobs while testing nothing** —
the blobs were regenerated around the new behaviour, and only the hand-written
spec-level assertions in the parity test caught it. `generate.py` now derives
`LAP_REDUCED`, `LAP_PROBE`, `LAP_REMOVED` and `REBUILD_LAPS` from the config, so
the corpus re-times itself the next time G2 recalibrates.

Two placement rules learned the hard way while re-timing, both recorded in the
generator beside the code:

- **A broad collapse must begin the lap AFTER a probe is entered, not on it.**
  Failing every corner on the entry lap withholds the quorum and merely blocks
  the advance, so the element reverts from `reduced` and the case never exercises
  `probe_to_revert`. `staggered_regression` can start on the entry lap because
  only one of its four corners fails there, leaving exactly 0.75.
- **A rebuild after a probe reversion costs `required_passes` laps, not a fresh
  ladder.** Reversions do not reset evidence windows, so the second probe is
  entered that soon. Overshooting let the second probe complete, and the case
  reached `removed` instead of the cap.

## A structural weakness, recorded and not yet fixed

Traces carry no config of their own, so they read the live
`controller_config.json`. That means a **calibration** change churns a corpus
whose job is pinning **logic parity** between the Lua and Python controllers — at
the one moment the two could silently diverge, the detector has to be
regenerated. Traces should carry their own `config` block, pinned at the
calibration they were authored for, with new cases added for a new calibration.
G2 will recalibrate again, so this is worth fixing before it does.
