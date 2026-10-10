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
| `fast_improver` | The lap-budget case: a full traverse in 9 laps, and the dwell at reduced that the re-qualification reset enforces. |
| `non_improver` | Design target 2 — never leaves full salience, emits no events at all. |
| `alternating_corner` | The acknowledged hysteresis pathology (framing v6): a qualified corner failing every *other* pass never accumulates two consecutive failures, so it never de-qualifies. Both backstops, and the honest consequence — at a four-corner denominator the other three still carry exactly 0.75, so the element still fades. |
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
