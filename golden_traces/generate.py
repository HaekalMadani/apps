"""Author the golden-trace corpus (impl plan section 6.1).

The COMMITTED JSON FILES are the contract, not this script. Both controller
implementations — ``lua/trace_rt/lib/controller.lua`` and
``kit/trace_kit/controller.py`` — must reproduce every committed trace exactly,
and ``kit/tests/test_m4_controller_parity.py`` reads the files, never this
generator. Re-run it only to add a trace or to re-author the corpus after a
DELIBERATE rule change, and re-read the diff against the spec when you do: the
expected sequences are produced by the Python implementation, so an undetected
bug there would be baked into the corpus. That is why the parity test also
carries hand-written, spec-level assertions that do not read the blobs (a lap
budget, an event ordering, a stage) — a corpus regenerated around a bug would
still have to get past those.

    python golden_traces/generate.py

Stdlib only. Run from the repository root.
"""

import copy
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "kit"))

from trace_kit.controller import Controller  # noqa: E402

OUT_DIR = REPO_ROOT / "golden_traces"
BASE_CONFIG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))

# The National layout's four corners: the real study geometry, so the corpus
# exercises the quorum denominator the participants actually drive (4 corners,
# all with braking, so >= 75% is 3 of 4 — see CLAUDE.md's M3 notes).
CORNERS = ["1", "2", "3", "4"]
ALL = {"braking": CORNERS, "corner_speed": CORNERS, "apex": CORNERS}

# One lap of the study circuit is ~55-75 s; a corner pass every ~15 s is close
# enough for a trace whose only use of `t` is stamping events.
LAP_SECONDS = 60.0

# --- the ladder's landmarks, DERIVED from the config -------------------------
#
# Added 2026-10-15. Several traces have to place an event at a precise point on
# the ladder -- a collapse *inside* a probe, a block ending *mid*-probe, a
# regression onset arriving before removal completes -- and they did it with
# written-out lap numbers tuned to the frozen-g1 ladder (9 laps). When
# frozen-g1b shortened it to 6, those numbers silently stopped meaning what
# their names said: `block_end_mid_probe` ran past its probe and ended at
# `removed`, so it censored nothing; `erratic_cap_reached` never reverted, so it
# never reached the cap; `staggered_regression` had already removed the element
# before the first onset. **Three cases went on passing their own blobs while
# testing nothing.** Deriving the landmarks instead means the corpus re-times
# itself the next time G2 recalibrates.
#
# A perfect learner advances every `required_passes` laps, and the advance into
# a probe resets the evidence, so the probe costs
# max(probe.laps, required_passes) more laps. Verified against the runtime at
# frozen-g1b: reduced@1, probe@3, removed@5.
REQUIRED = BASE_CONFIG["qualification"]["required_passes"]
PROBE_LAPS = BASE_CONFIG["probe"]["laps"]
LAP_REDUCED = REQUIRED - 1
LAP_PROBE = 2 * REQUIRED - 1
LAP_REMOVED = LAP_PROBE + max(PROBE_LAPS, REQUIRED)
# One full rebuild after a probe reversion: back to reduced, re-qualify, advance.
REBUILD_LAPS = 2 * REQUIRED


def merged_config(overrides):
    cfg = copy.deepcopy(BASE_CONFIG)
    for section, values in (overrides or {}).items():
        cfg[section].update(values)
    return cfg


def passes(laps, decide, corners=CORNERS):
    """Build a pass stream: `decide(lap, corner_id) -> criteria dict`."""
    out = []
    for lap in range(laps):
        for i, cid in enumerate(corners):
            out.append({
                "corner_id": cid,
                "lap": lap,
                "t": round(lap * LAP_SECONDS + (i + 1) * (LAP_SECONDS / (len(corners) + 1)), 3),
                "criteria": decide(lap, cid),
            })
    return out


def const(braking=None, corner_speed=None, apex=None):
    return {"braking": braking, "corner_speed": corner_speed, "apex": apex}


ALL_TRUE = const(True, True, True)
ALL_FALSE = const(False, False, False)


def build(trace_id, description, pass_list, applicable=None, overrides=None, finish=None):
    """Run a trace through the Python controller and package it with its expectations."""
    cfg = merged_config(overrides)
    ctrl = Controller(cfg, applicable or ALL)
    events = []
    for p in pass_list:
        events.extend(ctrl.step(p))
    if finish is not None:
        events.extend(ctrl.finish(finish["lap"], finish["t"]))
    doc = {
        "schema_version": 1,
        "trace_id": trace_id,
        "description": description,
        "applicable": applicable or ALL,
    }
    if overrides:
        doc["config_overrides"] = overrides
    # The COMPLETE config this trace was generated against, pinned into the
    # trace (2026-10-15). Both implementations are handed this object, never the
    # file on disk, so a recalibration no longer churns the corpus -- see the
    # `config` description in schemas/golden_trace.schema.json and the
    # "Re-timing after a calibration change" section of README.md.
    doc["config"] = cfg
    doc["passes"] = pass_list
    if finish is not None:
        doc["finish"] = finish
    doc["expected_events"] = events
    doc["expected_disabled_elements"] = ctrl.disabled_elements()
    doc["expected_final_state"] = ctrl.snapshot()
    return doc


# ---------------------------------------------------------------------------
# the corpus
# ---------------------------------------------------------------------------

def trace_fast_improver():
    return build(
        "fast_improver",
        "A learner who meets every criterion at every corner from the first lap. "
        "The lap-budget case framing v6 puts at 9-11 laps: broad qualification at "
        "full salience, the dwell the re-qualification reset enforces at reduced, "
        "then the 3-lap probe. All three elements traverse full -> reduced -> "
        "probe -> removed.",
        passes(12, lambda lap, cid: dict(ALL_TRUE)),
    )


def trace_non_improver():
    return build(
        "non_improver",
        "A learner who never meets a criterion. The design target is that this "
        "learner never leaves full salience: no events at all, every element "
        "still at full after 15 laps.",
        passes(15, lambda lap, cid: dict(ALL_FALSE)),
    )


def trace_alternating_corner():
    """The acknowledged hysteresis pathology (framing v6, impl plan section 6.1)."""
    def decide(lap, cid):
        if cid != "1":
            return dict(ALL_TRUE)
        # Corner 1 qualifies on three clean passes, then fails every OTHER pass.
        # It never accumulates two CONSECUTIVE failures, so it never de-qualifies
        # despite a sustained 50% failure rate.
        met = True if lap < 3 else (lap % 2 == 1)
        return const(met, met, met)

    return build(
        "alternating_corner",
        "The acknowledged hysteresis pathology: a corner that qualifies and then "
        "fails every other pass never accumulates two CONSECUTIVE failures, so it "
        "never de-qualifies despite a 50% failure rate. Two backstops are visible "
        "here. The re-qualification reset wipes the coasting corner's state on "
        "every advance, and after the reset an alternating corner can never reach "
        "3 of 4 again, so it stays unqualified for the rest of the block. What the "
        "trace also shows honestly: with FOUR applicable corners the remaining "
        "three carry a quorum of exactly 0.75, which still meets the advance "
        "threshold — one permanently-failing corner is inside the design's "
        "tolerance at this denominator.",
        passes(14, decide),
    )


def trace_midwindow_reset():
    def decide(lap, cid):
        # Corner 4 yields nothing on lap 0, so it lags a pass behind the others
        # and the advance lands while windows are unevenly filled.
        if cid == "4" and lap == 0:
            return const(None, None, None)
        return dict(ALL_TRUE)

    return build(
        "midwindow_requalification_reset",
        "A stage advance landing while the corners are partway through their "
        "evidence windows: corner 4 produces no measurable metric on lap 0, so it "
        "trails the other three by a pass and the advance resets windows of "
        "unequal length. Also exercises the quorum-readiness rule directly — the "
        "element cannot advance until the LAGGING corner has its evidence, not "
        "when the first three corners alone would carry 75%.",
        passes(12, decide),
    )


def trace_block_end_mid_probe():
    return build(
        "block_end_mid_probe",
        "A block that ends while every element is mid-probe. Each is logged "
        "censored (incomplete / right-censored): in RQ1's probe-outcome tabulation "
        "it counts as neither held nor reverted, and the element's final stage "
        "stays `probe`.",
        passes(LAP_PROBE + 2, lambda lap, cid: dict(ALL_TRUE)),
        finish={"lap": LAP_PROBE + 2, "t": (LAP_PROBE + 2) * LAP_SECONDS},
    )


def trace_erratic_cap_reached():
    # Two broad collapses, each placed INSIDE a probe -- the one entered at
    # LAP_PROBE, and the one entered after the rebuild -- so both produce probe
    # reversions rather than reversions from reduced. The second hits the cap.
    # Two consecutive failing laps per collapse, because a corner cannot
    # de-qualify before its second consecutive failure.
    # The collapse must begin the lap AFTER the probe is entered, not on it: a
    # broad failure ON the entry lap withholds the quorum and simply blocks the
    # advance, so the element reverts from `reduced` and the case never
    # exercises `probe_to_revert` at all. (It did exactly that on the first
    # re-timing attempt.) `staggered_regression` can start on the entry lap
    # because only one of its four corners fails there, leaving 0.75.
    first = (LAP_PROBE + 1, LAP_PROBE + 2)
    # A probe reversion drops the element to `reduced` and leaves the collapsed
    # corners de-qualified, but it does NOT reset their windows (reversions
    # never do), so the rebuild is `required_passes` clean laps and the second
    # probe is entered that soon -- not after a full fresh ladder. Overshooting
    # this let the second probe complete, so the case reached `removed` and
    # never touched the cap.
    second_probe = first[-1] + REQUIRED
    second = (second_probe + 1, second_probe + 2)
    collapses = set(first) | set(second)

    def decide(lap, cid):
        met = lap not in collapses
        return const(met, met, met)

    return build(
        "erratic_cap_reached",
        "The erratic learner the reversion cap exists for: reaches the probe, "
        "collapses, rebuilds, reaches it again, collapses again. The second "
        "probe_to_revert hits `probe.reversion_cap`, so a cap_reached event "
        "follows immediately and the element is pinned at reduced salience for "
        "the rest of the block — no further transitions in EITHER direction, "
        "which is what makes the remainder of the block interpretable instead of "
        "an oscillation.",
        passes(26, decide),
    )


def trace_zero_applicable_braking():
    return build(
        "zero_applicable_braking",
        "The degenerate element the impl plan (section 7) requires a defined "
        "answer for: a track where no annotated corner has a braking zone, so the "
        "braking element has ZERO applicable corners. It is disabled — pinned at "
        "full salience, never evaluated, reported through disabled_elements() so "
        "the runtime can stamp it into the block manifest — and the quorum share "
        "is never a division by zero. The other two elements are unaffected and "
        "traverse normally.",
        passes(12, lambda lap, cid: dict(ALL_TRUE)),
        applicable={"braking": [], "corner_speed": CORNERS, "apex": CORNERS},
    )


def trace_staggered_regression():
    def decide(lap, cid):
        # Broad competence, then regression onset spread one corner per lap —
        # real regression is not synchronised (eval plan v2, target 3). The
        # first onset lands INSIDE the probe entered at LAP_PROBE, which is the
        # whole point of the case: it must arrive before the probe can
        # complete, or the element is already `removed` and there is no probe
        # left to revert.
        onset = LAP_PROBE + CORNERS.index(cid)
        met = lap < onset
        return const(met, met, met)

    return build(
        "staggered_regression",
        "The staggered regressor: regression onset spread across corners over "
        "several laps rather than arriving synchronised. Under the "
        "de-qualification rule (two consecutive failures) no corner can flip "
        "earlier than one lap after its own onset, so a quorum collapse takes "
        "about two laps from the first onset here — which is the honest target "
        "eval plan v2 states, against the one-lap figure that only synchronised "
        "synthetic streams can achieve.",
        passes(18, decide),
    )


def trace_null_criteria_stall():
    def decide(lap, cid):
        if cid == "3":
            # Corner 3 never yields a brake-initiation event (e.g. the driver
            # brakes before the zone opens on every lap).
            return const(None, True, True)
        return dict(ALL_TRUE)

    return build(
        "null_criteria_stall",
        "A corner that yields NO braking metric on any pass — the shape a "
        "mis-fitted braking zone takes, and the residual risk the controller's "
        "null-is-no-evidence rule accepts. The braking element never becomes "
        "quorum-ready, because corner 3 never accumulates evidence, so it STALLS "
        "at full salience and emits no events at all. A stall, not a false fade: "
        "the failure is in the conservative direction and is visible in the logs "
        "as an element with no fade events while the other two traverse normally.",
        passes(12, decide),
    )


def trace_reduced_to_full_revert():
    def decide(lap, cid):
        # Everyone qualifies through lap 2, so the element advances to reduced.
        # Under the reduced cue only corners 1 and 2 rebuild: the share settles
        # at exactly 0.5, inside the hysteresis dead band (not >= 0.75, not
        # < 0.5), and the element sits there. From lap 8 corners 1 and 2 regress
        # too and de-qualify on their second consecutive failure, dropping the
        # share to 0 and reverting the element.
        if lap <= 2:
            met = True
        elif cid in ("3", "4"):
            met = False
        else:
            met = lap < 8
        return const(met, met, met)

    return build(
        "reduced_to_full_revert",
        "Reversion from reduced salience back to full, and the hysteresis dead "
        "band on the way. The learner reaches quorum at full salience and "
        "advances; under the reduced cue only half the corners rebuild, so the "
        "qualified share settles at exactly 0.5 - neither at the 0.75 advance "
        "threshold nor below the 0.5 revert threshold - and the element holds "
        "there for several laps, which is what the asymmetric thresholds are "
        "for. When the two remaining corners regress and de-qualify on their "
        "second consecutive failure, the share falls to 0 and the element "
        "reverts. The reversion does NOT reset the evidence windows (framing "
        "v6): the depleted evidence that fell below quorum is exactly what the "
        "learner has to rebuild to advance again.",
        passes(14, decide),
    )


def trace_no_requalify_degenerate():
    return build(
        "no_requalify_degenerate",
        "The degenerate machine the re-qualification rule prevents, run "
        "deliberately with `qualification.requalify_on_advance` false. The quorum "
        "that triggered full -> reduced still holds immediately afterwards, so the "
        "element advances again on the very next pass and the reduced stage is a "
        "cosmetic waypoint rather than a test. Committed as a golden trace so the "
        "rule's justification is a runnable demonstration rather than a claim in "
        "a document; the frozen study config sets the flag true.",
        passes(8, lambda lap, cid: dict(ALL_TRUE)),
        overrides={"qualification": {"requalify_on_advance": False}},
    )


BUILDERS = [
    trace_fast_improver,
    trace_non_improver,
    trace_alternating_corner,
    trace_midwindow_reset,
    trace_block_end_mid_probe,
    trace_erratic_cap_reached,
    trace_zero_applicable_braking,
    trace_staggered_regression,
    trace_null_criteria_stall,
    trace_reduced_to_full_revert,
    trace_no_requalify_degenerate,
]


def main():
    for builder in BUILDERS:
        doc = builder()
        path = OUT_DIR / "{}.json".format(doc["trace_id"])
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        summary = ", ".join(
            "{}:{}".format(e["element"], e["transition"]) for e in doc["expected_events"]
        ) or "(no events)"
        print("{:34s} {:3d} passes -> {}".format(doc["trace_id"], len(doc["passes"]), summary))


if __name__ == "__main__":
    main()
