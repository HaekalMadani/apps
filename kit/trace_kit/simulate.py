"""Phase 1: threshold calibration by simulation (eval plan Phase 1, Gate G1).

Runs synthetic novice metric streams through the REAL controller and evaluator —
``trace_kit.controller`` and ``trace_kit.evaluator``, both pinned to their Lua
counterparts by the golden-trace and evaluator parity suites — and tunes the
controller's free parameters until the design targets hold. Its outputs are the
frozen configuration Gate G1 closes on and the feasibility figure that documents
the controller's behaviour as designed rather than accidental.

    python -m trace_kit.simulate run     [--streams N] [--out DIR] [--seed S]
    python -m trace_kit.simulate sweep   [--streams N] [--out DIR] [--seed S]
    python -m trace_kit.simulate freeze  --config-id frozen-g1

``run`` evaluates the committed configuration. ``sweep`` searches the free
parameters, reports the design-target verdict for each candidate, and names the
one to freeze. ``freeze`` writes chosen values into
``configs/controller_config.json`` and prints its SHA-256 for the record.

---------------------------------------------------------------------------
The synthetic novice, and what it is and is not
---------------------------------------------------------------------------

Each stream is one participant driving one block on one real car-track pair,
using that pair's COMMITTED annotation and reference table — not a synthetic
circuit. The corner count, the per-corner reference values and the resulting
quorum denominators are therefore the ones participants actually face.

Per corner and per metric the learner carries a systematic offset that decays
along a learning curve, plus lap-to-lap noise:

    metric(lap) = reference + offset0 x difficulty x exp(-rate x lap) + N(0, sigma)

Novice error has a direction in each metric, and the model respects it: novices
brake EARLIER than the reference, carry LESS speed through a corner, and sit
FURTHER from the expert line. Only the initial brake offset has an empirical
anchor — the Gate G0 review measured researcher-driven brake points running from
27.7 m early to 27.2 m late against the AI reference — so `brake_offset0_m` is
set from it. Every other entry in MODEL is a stated assumption, and the
lap-to-lap sigmas in particular are the ones Gate G2 exists to replace with
measured pilot distributions; `--model key=value` re-runs the whole verdict
against a different one. Nothing here is a claim about real novices; it is a stress test of
the controller's arithmetic against a plausible learner, which is all Phase 1
needs to be. Where a target fails, the honest reading is "these thresholds do not
suit THIS model", and the pilot decides whether the model was wrong.

Randomness lives ONLY here. The controller and evaluator stay pure, and every
run is reproducible from its seed.

Stdlib only (the whole toolkit is; the feasibility figure is hand-written SVG
rather than a matplotlib dependency).
"""

import argparse
import copy
import hashlib
import json
import math
import random
import statistics
from collections import OrderedDict
from pathlib import Path

from trace_kit import evaluator as ev
from trace_kit.controller import ELEMENTS, Controller

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "controller_config.json"
REFERENCES_DIR = REPO_ROOT / "configs" / "references"

# --- the novice model -------------------------------------------------------

# The novice model's parameters, in one place so a G1 verdict can be re-run
# against a different learner rather than argued about. `--model key=value`
# overrides any of them from the command line, and whatever was used is written
# into the report, because a simulated gate is only ever as good as this table.
#
# `brake_offset0_m` is the one entry with an empirical anchor: the Gate G0 review
# measured researcher-driven novice brake points running from 27.7 m early to
# 27.2 m late against the AI reference. The rest are stated assumptions of the
# same rough scale relative to their bands.
#
# The three sigmas are lap-to-lap noise, present at every skill level (inherent
# motor noise persists — Cohen & Sternad, 2009 — which is the premise of the EVM
# itself). They are what Gate G2 replaces with measured pilot variance, and the
# parameters the verdict is most sensitive to: the braking sigma in particular
# decides whether the two-gate braking criterion has a usable consistency gate
# at all (see the G1 report's sensitivity section).
MODEL = OrderedDict([
    ("brake_offset0_m", 25.0),      # metres EARLY (positive = early, per the schema)
    ("brake_sigma_m", 4.0),
    ("speed_offset0_kmh", 12.0),    # km/h SLOW through the corner
    ("speed_sigma_kmh", 2.0),
    ("apex_offset0_m", 1.2),        # metres of extra RMS deviation from the line
    ("apex_sigma_m", 0.30),
    # Corners are not equally hard. Each stream draws a per-corner difficulty
    # multiplier on its initial offsets, so the quorum has to be carried by a
    # mix of easy and hard corners rather than by a uniform learner.
    ("difficulty_min", 0.6),
    ("difficulty_max", 1.6),
])

# A block is 30 minutes of driving, which the eval plan expects to yield 13-15
# laps on a ~2-minute circuit.
BLOCK_LAPS = 15


class Learner:
    """One learner type's parameters. See LEARNER_TYPES for the roster."""

    def __init__(self, name, rate, noise_scale=1.0, regression=None, description=""):
        self.name = name
        self.rate = rate                  # exponential learning rate per lap
        self.noise_scale = noise_scale
        # regression = (first_onset_lap, laps_between_corner_onsets, severity)
        self.regression = regression
        self.description = description


LEARNER_TYPES = [
    Learner("fast_improver", 0.55, description=(
        "Learns quickly; the lap-budget case framing v6 puts at 9-11 laps.")),
    Learner("typical_improver", 0.30, description=(
        "The design target's subject: the middle of the improving range.")),
    Learner("slow_improver", 0.12, description=(
        "Improves, but not fast enough to traverse inside one block.")),
    Learner("non_improver", 0.0, description=(
        "Never improves; the second design target says the scaffold must stay.")),
    Learner("erratic", 0.30, noise_scale=2.5, description=(
        "Improves on average but with heavy lap-to-lap noise; the learner the "
        "reversion cap and the hysteresis dead band exist for.")),
    Learner("synchronised_regressor", 0.55, regression=(7, 0, 1.0), description=(
        "Improves, then every corner regresses in the SAME lap. Only synthetic "
        "streams do this, which is why the one-lap reversion target applies "
        "here and nowhere else.")),
    Learner("staggered_regressor", 0.55, regression=(7, 1, 1.0), description=(
        "Improves, then regresses one corner per lap - the honest shape of real "
        "regression, and the stream eval plan v2 added to keep the reversion "
        "target from being stated against synthetic behaviour only.")),
]


# --- one stream --------------------------------------------------------------

def _offset(learner, lap, onset_lap):
    """The learning curve, with regression folded in.

    Before the learner's own regression onset the offset decays exponentially;
    from the onset it is restored to a `severity` fraction of where it started,
    which is what "regression" means for a scaffold: the skill the cue stood in
    for stops holding up.
    """
    decayed = math.exp(-learner.rate * lap)
    if onset_lap is not None and lap >= onset_lap:
        severity = learner.regression[2]
        return max(decayed, severity)
    return decayed


def _onset_laps(learner, corner_ids, rng):
    """Per-corner regression onset laps, or None for every corner."""
    if learner.regression is None:
        return {cid: None for cid in corner_ids}
    first, stagger, _ = learner.regression
    order = list(corner_ids)
    rng.shuffle(order)
    return {cid: first + i * stagger for i, cid in enumerate(order)}


def simulate_stream(cfg, reference, learner, rng, laps=BLOCK_LAPS):
    """Drive one synthetic block. Returns the controller events and a stage trace."""
    corners = reference["corners"]
    corner_ids = [c["corner_id"] for c in corners]
    by_id = ev.index_corners(reference)

    difficulty = {cid: rng.uniform(MODEL["difficulty_min"], MODEL["difficulty_max"])
                  for cid in corner_ids}
    onsets = _onset_laps(learner, corner_ids, rng)

    ctrl = Controller(cfg, ev.applicable(reference))
    history = {cid: [] for cid in corner_ids}
    events = []
    # stage_trace[element][lap] = the stage in force when that lap ENDED.
    stage_trace = {e: [] for e in ELEMENTS}
    null_counts = {e: 0 for e in ELEMENTS}

    window = cfg["qualification"]["window_passes"]
    for lap in range(laps):
        for cid in corner_ids:
            ref_corner = by_id[cid]
            k = difficulty[cid] * _offset(learner, lap, onsets[cid])
            noise = learner.noise_scale
            metrics = {
                "min_corner_speed_kmh": (
                    ref_corner["corner_speed"]["mean_kmh"]
                    - MODEL["speed_offset0_kmh"] * k
                    + rng.gauss(0.0, MODEL["speed_sigma_kmh"] * noise)),
                # RMS is a magnitude: it cannot go below zero, and folding at
                # zero rather than clipping keeps the noise from piling up on
                # the boundary for a learner already on the line.
                "apex_rms_m": abs(
                    ref_corner["apex"]["mean_rms_m"]
                    + MODEL["apex_offset0_m"] * k
                    + rng.gauss(0.0, MODEL["apex_sigma_m"] * noise)),
            }
            if ref_corner.get("braking") is not None:
                metrics["brake_initiation_distance_m"] = (
                    MODEL["brake_offset0_m"] * k
                    + rng.gauss(0.0, MODEL["brake_sigma_m"] * noise))

            result = ev.evaluate(cfg, ref_corner, metrics, history[cid])
            if metrics.get("brake_initiation_distance_m") is not None:
                ev.push_history(history[cid], metrics["brake_initiation_distance_m"], window)
            for e in ELEMENTS:
                if result["criteria"][e] is None:
                    null_counts[e] += 1

            events.extend(ctrl.step({
                "corner_id": cid, "lap": lap, "t": float(lap * 120 + 10),
                "criteria": result["criteria"],
            }))
        stages = ctrl.stages()
        for e in ELEMENTS:
            stage_trace[e].append(stages[e])

    events.extend(ctrl.finish(laps, float(laps * 120)))
    return {
        "events": events,
        "stage_trace": stage_trace,
        "final_stages": ctrl.stages(),
        "disabled": ctrl.disabled_elements(),
        "onsets": onsets,
        "earliest_reversion": earliest_reversion_lap(cfg, reference, onsets),
        "null_counts": null_counts,
    }


def earliest_reversion_lap(cfg, reference, onsets):
    """The first lap at which a quorum collapse is ARITHMETICALLY possible.

    Reversion latency has a floor the thresholds cannot move, and measuring
    against the first corner's onset conflates that floor with the controller's
    responsiveness. Two rules set it. A corner cannot de-qualify until it has
    failed `dequalify_consecutive_failures` times, so not before
    `dequalify - 1` laps after its own onset. And the element cannot revert until
    enough corners have de-qualified to put the qualified share below
    `revert_threshold`, which for staggered onsets is not the first corner's
    onset but the k-th.

    That floor is why eval plan v2's "within two laps when staggered" is not
    reachable by tuning: with onsets one lap apart across four corners, a
    majority has not even regressed until the third lap. Returning the floor per
    element lets the target be measured as EXCESS latency over it, which is the
    part the controller is actually responsible for — and which collapses to the
    eval plan's own numbers when regression is synchronised.

    Returns element -> lap, or None where the element cannot collapse at all.
    """
    q = cfg["qualification"]["dequalify_consecutive_failures"]
    revert = cfg["quorum"]["revert_threshold"]
    out = {}
    for element, ids in ev.applicable(reference).items():
        laps = sorted(o for cid, o in onsets.items() if cid in ids and o is not None)
        n = len(ids)
        if not laps or not n:
            out[element] = None
            continue
        # Smallest k with (n - k) / n < revert_threshold.
        k = next((k for k in range(1, n + 1) if (n - k) / n < revert), None)
        out[element] = (laps[k - 1] + q - 1) if (k is not None and k <= len(laps)) else None
    return out


# --- aggregation -------------------------------------------------------------

STAGE_INDEX = {"full": 0, "reduced": 1, "probe": 2, "removed": 3}


def _first(events, element, transition):
    for e in events:
        if e["element"] == element and e["transition"] == transition:
            return e
    return None


def summarise_stream(stream):
    """The per-stream facts the design targets are decided on."""
    events = stream["events"]
    elements = [e for e in ELEMENTS if e not in stream["disabled"]]
    removed = [e for e in elements if stream["final_stages"][e] == "removed"]

    reversion_lags = []       # laps from the FIRST corner's onset (descriptive)
    reversion_excess = []     # laps beyond the arithmetic floor (the target)
    if stream["onsets"] and any(v is not None for v in stream["onsets"].values()):
        onset = min(v for v in stream["onsets"].values() if v is not None)
        for e in elements:
            floor = stream["earliest_reversion"].get(e)
            for kind in ("probe_to_revert", "reduced_to_full"):
                first = _first(events, e, kind)
                if first is not None and first["lap"] >= onset:
                    reversion_lags.append((kind, first["lap"] - onset))
                    if floor is not None:
                        reversion_excess.append(first["lap"] - floor)
                    break

    # A removal is only a FAILURE if it happened once the regression could
    # already have been detected. An element removed before that point was
    # removed on evidence that was still good, and block-scoped permanence then
    # says it stays removed — the design working, not a misfire.
    removed_after_detectable = 0
    for e in removed:
        floor = stream["earliest_reversion"].get(e)
        event = _first(events, e, "probe_to_removed")
        if floor is not None and event is not None and event["lap"] >= floor:
            removed_after_detectable += 1

    return {
        "elements_removed": len(removed),
        "removed_after_regression_detectable": removed_after_detectable,
        "elements_total": len(elements),
        "left_full": sum(1 for e in elements if stream["final_stages"][e] != "full"),
        "removal_laps": [
            _first(events, e, "probe_to_removed")["lap"] for e in removed],
        "reversion_lags": reversion_lags,
        "reversion_excess": reversion_excess,
        "reverted": sum(1 for e in elements if _first(events, e, "probe_to_revert")),
        "censored": sum(1 for e in elements if _first(events, e, "censored")),
        "cap_hits": sum(1 for e in elements if _first(events, e, "cap_reached")),
        "null_criteria": sum(stream["null_counts"].values()),
    }


def run_type(cfg, references, learner, streams, seed):
    """Run one learner type over every pair. Returns summaries plus mean stage curves."""
    summaries = []
    # curves[element][lap] accumulates the mean stage index across streams, which
    # is what the feasibility figure draws.
    curves = {e: [0.0] * BLOCK_LAPS for e in ELEMENTS}
    n = 0
    for pair_index, reference in enumerate(references):
        rng = random.Random("{}|{}|{}".format(seed, learner.name, pair_index))
        for _ in range(streams):
            stream = simulate_stream(cfg, reference, learner, rng)
            summaries.append(summarise_stream(stream))
            for e in ELEMENTS:
                for lap, stage in enumerate(stream["stage_trace"][e]):
                    curves[e][lap] += STAGE_INDEX[stage]
            n += 1
    for e in ELEMENTS:
        curves[e] = [round(v / n, 4) for v in curves[e]]
    return summaries, curves, n


def _share(values, predicate):
    return (sum(1 for v in values if predicate(v)) / len(values)) if values else 0.0


def evaluate_targets(by_type):
    """The three Gate G1 design targets, with how each was operationalised.

    The eval plan states the targets qualitatively; the operationalisation is an
    M4 decision and is carried in the report next to the verdict, so a reader can
    disagree with the bar without having to reverse-engineer it.
    """
    targets = []

    typical = by_type["typical_improver"]["summaries"]
    share = _share(typical, lambda s: s["elements_removed"] >= 2)
    targets.append({
        "id": "typical_improver_traverses",
        "statement": (
            "A typical improver fully traverses the machine (full -> reduced -> "
            "probe -> removed) for at least 2 of 3 elements within one training "
            "block of {} laps.".format(BLOCK_LAPS)),
        "operationalisation": (
            "The target is about the TYPICAL learner, so it is read as the "
            "median stream: at least half of typical_improver streams must "
            "traverse 2 of 3 elements."),
        "measured": {"share_traversing_2_of_3": round(share, 4),
                     "median_elements_removed": statistics.median(
                         s["elements_removed"] for s in typical)},
        "threshold": 0.5,
        "met": share >= 0.5,
    })

    non = by_type["non_improver"]["summaries"]
    leaked = _share(non, lambda s: s["left_full"] > 0)
    targets.append({
        "id": "non_improver_never_fades",
        "statement": "A non-improver never leaves full salience.",
        "operationalisation": (
            "Read strictly: NO non_improver stream may move any element off "
            "full. This is what bounds the bands from above, and it is the "
            "direction the design says to err on (premature withdrawal is worse "
            "than delayed)."),
        "measured": {"share_with_any_fade": round(leaked, 4)},
        "threshold": 0.0,
        "met": leaked == 0.0,
    })

    sync_lags = [lag for s in by_type["synchronised_regressor"]["summaries"]
                 for _, lag in s["reversion_lags"]]
    stag_lags = [lag for s in by_type["staggered_regressor"]["summaries"]
                 for _, lag in s["reversion_lags"]]
    sync_excess = [x for s in by_type["synchronised_regressor"]["summaries"]
                   for x in s["reversion_excess"]]
    stag_excess = [x for s in by_type["staggered_regressor"]["summaries"]
                   for x in s["reversion_excess"]]
    sync_median = statistics.median(sync_lags) if sync_lags else None
    stag_median = statistics.median(stag_lags) if stag_lags else None
    sync_excess_median = statistics.median(sync_excess) if sync_excess else None
    stag_excess_median = statistics.median(stag_excess) if stag_excess else None
    # The property that actually protects a participant: broad regression must
    # never be answered by PERMANENT withdrawal. A late reversion costs a lap of
    # driving without the cue; a removal costs the rest of the block.
    removed_despite_regression = max(
        _share(by_type[name]["summaries"],
               lambda s: s["removed_after_regression_detectable"] > 0)
        for name in ("synchronised_regressor", "staggered_regressor"))
    targets.append({
        "id": "regression_reverts_promptly",
        "statement": (
            "Reversion triggers on broad regression within one lap of onset when "
            "regression is synchronised across corners, and within two laps when "
            "it is staggered; and broad regression is never answered by removal."),
        "operationalisation": (
            "Measured as EXCESS latency over the arithmetic floor (see "
            "earliest_reversion_lap), read as the median stream for the same "
            "reason the first target is. The raw lag from the first corner's "
            "onset is reported too, but it is not the bar: reversion latency has "
            "a floor set by the de-qualification rule and by how many corners "
            "must regress before a majority exists, and eval plan v2's "
            "'within two laps when staggered' sits BELOW that floor for onsets "
            "one lap apart across four corners - a majority has not regressed "
            "until the third lap, so no threshold tuning can reach it. Excess "
            "latency is the part the controller is responsible for, and it "
            "reproduces the eval plan's own numbers exactly where regression is "
            "synchronised. The removal clause is an M4 addition: it is the safety "
            "property the latency is a proxy for and admits no tolerable "
            "failures, so it is read strictly - but it counts only removals "
            "that happen once the regression could ALREADY have been detected. "
            "An element removed before that point was removed on evidence that "
            "was still good, and block-scoped permanence then keeps it removed; "
            "that is the design working, not a misfire. A negative excess "
            "latency is likewise not an anomaly: inside a probe the evidence "
            "windows have just been reset, so a regressing corner never "
            "re-qualifies rather than having to de-qualify, and the reversion "
            "can beat the de-qualification floor."),
        "measured": {
            "synchronised_median_excess_laps": sync_excess_median,
            "staggered_median_excess_laps": stag_excess_median,
            "synchronised_share_at_the_floor": round(_share(sync_excess, lambda v: v <= 0), 4),
            "staggered_share_at_the_floor": round(_share(stag_excess, lambda v: v <= 0), 4),
            "synchronised_median_lag_from_first_onset": sync_median,
            "staggered_median_lag_from_first_onset": stag_median,
            "n_synchronised_reversions": len(sync_lags),
            "n_staggered_reversions": len(stag_lags),
            "share_removed_despite_regression": round(removed_despite_regression, 4),
        },
        "threshold": {"median_excess_laps": 1, "share_removed_despite_regression": 0.0},
        "met": (sync_excess_median is not None and stag_excess_median is not None
                and sync_excess_median <= 1 and stag_excess_median <= 1
                and removed_despite_regression == 0.0),
    })
    return targets


def run(cfg, references, streams, seed):
    """Simulate every learner type and evaluate the design targets."""
    by_type = OrderedDict()
    total = 0
    for learner in LEARNER_TYPES:
        summaries, curves, n = run_type(cfg, references, learner, streams, seed)
        total += n
        removal_laps = [lap for s in summaries for lap in s["removal_laps"]]
        by_type[learner.name] = {
            "description": learner.description,
            "streams": n,
            "summaries": summaries,
            "curves": curves,
            "stats": {
                "mean_elements_removed": round(
                    statistics.fmean(s["elements_removed"] for s in summaries), 3),
                "share_any_fade": round(_share(summaries, lambda s: s["left_full"] > 0), 4),
                "share_all_three_removed": round(
                    _share(summaries, lambda s: s["elements_removed"] == s["elements_total"]), 4),
                "median_removal_lap": statistics.median(removal_laps) if removal_laps else None,
                "share_any_reversion": round(_share(summaries, lambda s: s["reverted"] > 0), 4),
                "share_cap_reached": round(_share(summaries, lambda s: s["cap_hits"] > 0), 4),
                "share_censored": round(_share(summaries, lambda s: s["censored"] > 0), 4),
                "null_criteria": sum(s["null_criteria"] for s in summaries),
            },
        }
    targets = evaluate_targets(by_type)
    return {"total_streams": total, "by_type": by_type, "targets": targets}


# --- parameter sweep ---------------------------------------------------------

# The free parameters Phase 1 tunes. The qualification window, quorum thresholds
# and probe rules are NOT swept here: they are structural choices framing v6
# argues for, and moving them would change the mechanism rather than calibrate
# it. What is calibrated is the tolerance the criteria allow.
SWEEP_GRID = OrderedDict([
    ("band_floors.braking_m", [5.0, 8.0, 12.0, 16.0]),
    ("band_floors.corner_speed_kmh", [3.0, 4.0, 5.0]),
    ("band_floors.apex_m", [0.5, 0.8, 1.2]),
    ("criteria.consistency_delta_ratio", [0.5, 0.75, 1.0, 1.5]),
])

# Relative to the committed defaults, so "looseness" compares like with like
# across parameters measured in metres, km/h and a bare ratio.
SWEEP_BASELINE = {
    "band_floors.braking_m": 5.0,
    "band_floors.corner_speed_kmh": 3.0,
    "band_floors.apex_m": 0.5,
    "criteria.consistency_delta_ratio": 0.5,
}


def _set(cfg, dotted, value):
    section, key = dotted.split(".")
    cfg[section][key] = value


def _looseness(candidate):
    """How much a candidate relaxes the criteria, relative to the defaults.

    The selection rule prefers the TIGHTEST configuration that still meets every
    target. Loose bands are not free: they fade a scaffold for a learner who has
    not earned it, which is the failure the design explicitly says is worse than
    fading late.
    """
    return round(sum(candidate[k] / SWEEP_BASELINE[k] for k in SWEEP_BASELINE), 6)


def sweep(base_cfg, references, streams, seed):
    """Search the free parameters; return every candidate, tightest-first among those that pass."""
    keys = list(SWEEP_GRID)
    results = []

    def recurse(i, chosen):
        if i == len(keys):
            cfg = copy.deepcopy(base_cfg)
            for k, v in chosen.items():
                _set(cfg, k, v)
            report = run(cfg, references, streams, seed)
            results.append({
                "params": dict(chosen),
                "looseness": _looseness(chosen),
                "targets": [{"id": t["id"], "met": t["met"], "measured": t["measured"]}
                            for t in report["targets"]],
                "all_met": all(t["met"] for t in report["targets"]),
            })
            return
        for value in SWEEP_GRID[keys[i]]:
            chosen[keys[i]] = value
            recurse(i + 1, chosen)

    recurse(0, OrderedDict())
    passing = [r for r in results if r["all_met"]]
    passing.sort(key=lambda r: (r["looseness"], sorted(r["params"].items())))
    return results, passing


# --- the feasibility figure --------------------------------------------------

ELEMENT_COLOURS = {"braking": "#c8501e", "corner_speed": "#1d7a54", "apex": "#2a63b0"}
STAGE_LABELS = ["full", "reduced", "probe", "removed"]


def _escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def feasibility_svg(report, config_id):
    """Simulated fade trajectories by learner type — the eval plan's Phase 1 figure.

    Hand-written SVG rather than a plotting dependency: the whole toolkit is
    stdlib-only, and a figure that any reader can open, diff and re-style in a
    text editor suits a thesis artefact better than a binary PNG.

    Each panel plots the MEAN controller stage across streams, per element,
    against lap. A mean between stages means the streams disagree at that lap,
    which is the interesting part: a curve that rises smoothly to 3 is a
    population traversing at different rates, while a flat curve at 0 is the
    non-improver target holding.
    """
    types = list(report["by_type"])
    cols, rows = 3, (len(types) + 2) // 3
    pw, ph = 260, 170            # panel size
    ml, mt, gx, gy = 58, 62, 34, 58
    width = ml + cols * pw + (cols - 1) * gx + 20
    height = mt + rows * ph + (rows - 1) * gy + 40

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" '
           'viewBox="0 0 {} {}" font-family="Helvetica,Arial,sans-serif">'.format(
               width, height, width, height),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="{}" y="26" font-size="15" font-weight="bold">Simulated fade '
           'trajectories by learner type</text>'.format(ml),
           '<text x="{}" y="44" font-size="10.5" fill="#555">Mean controller stage over '
           '{} streams per type, {} laps, config "{}". Higher is less scaffolding.'
           '</text>'.format(ml, report["total_streams"] // len(types), BLOCK_LAPS,
                            _escape(config_id))]

    # legend
    lx = width - 20
    for name in reversed(ELEMENTS):
        label = name.replace("_", " ")
        lx -= 8 * len(label) + 26
        out.append('<rect x="{}" y="18" width="10" height="10" fill="{}"/>'.format(
            lx, ELEMENT_COLOURS[name]))
        out.append('<text x="{}" y="27" font-size="10.5">{}</text>'.format(
            lx + 15, _escape(label)))

    for index, name in enumerate(types):
        col, row = index % cols, index // cols
        ox = ml + col * (pw + gx)
        oy = mt + row * (ph + gy)
        out.append('<text x="{}" y="{}" font-size="11.5" font-weight="bold">{}</text>'.format(
            ox, oy - 8, _escape(name.replace("_", " "))))
        out.append('<rect x="{}" y="{}" width="{}" height="{}" fill="#fbfbfb" '
                   'stroke="#dddddd"/>'.format(ox, oy, pw, ph))

        # y gridlines: one per stage
        for s, label in enumerate(STAGE_LABELS):
            y = oy + ph - (s / 3.0) * ph
            out.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}" stroke="#eeeeee"/>'.format(
                ox, y, ox + pw, y))
            if col == 0:
                out.append('<text x="{}" y="{:.1f}" font-size="9" text-anchor="end" '
                           'fill="#666">{}</text>'.format(ox - 6, y + 3, label))

        for e in ELEMENTS:
            curve = report["by_type"][name]["curves"][e]
            points = " ".join(
                "{:.1f},{:.1f}".format(
                    ox + (lap / max(1, BLOCK_LAPS - 1)) * pw,
                    oy + ph - (value / 3.0) * ph)
                for lap, value in enumerate(curve))
            out.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="1.8" '
                       'stroke-linejoin="round"/>'.format(points, ELEMENT_COLOURS[e]))

        for lap in (0, BLOCK_LAPS // 2, BLOCK_LAPS - 1):
            x = ox + (lap / max(1, BLOCK_LAPS - 1)) * pw
            out.append('<text x="{:.1f}" y="{}" font-size="9" text-anchor="middle" '
                       'fill="#666">{}</text>'.format(x, oy + ph + 13, lap))
        out.append('<text x="{}" y="{}" font-size="9" text-anchor="middle" '
                   'fill="#666">lap</text>'.format(ox + pw / 2, oy + ph + 26))

        stats = report["by_type"][name]["stats"]
        out.append('<text x="{}" y="{}" font-size="9" fill="#444">removed {:.2f}/3 '
                   'mean, any fade {:.0f}%, reversion {:.0f}%</text>'.format(
                       ox, oy + ph + 40, stats["mean_elements_removed"],
                       100 * stats["share_any_fade"], 100 * stats["share_any_reversion"]))

    out.append("</svg>")
    return "\n".join(out)


# --- CLI ---------------------------------------------------------------------

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_references():
    refs = []
    for path in sorted(REFERENCES_DIR.glob("reference_pair?.json")):
        with open(path, encoding="utf-8") as f:
            refs.append(json.load(f))
    if not refs:
        raise SystemExit("no reference tables in {} - run M3 first".format(REFERENCES_DIR))
    return refs


def config_hash():
    return hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()


def strip_summaries(report):
    """The report minus the per-stream detail, for writing to disk."""
    out = {"total_streams": report["total_streams"],
           "block_laps": BLOCK_LAPS,
           "novice_model": dict(MODEL),
           "targets": report["targets"],
           "by_type": OrderedDict()}
    for name, data in report["by_type"].items():
        out["by_type"][name] = {"description": data["description"],
                                "streams": data["streams"],
                                "stats": data["stats"],
                                "curves": data["curves"]}
    return out


def print_report(report):
    print("streams: {}   block: {} laps".format(report["total_streams"], BLOCK_LAPS))
    print()
    header = "{:24s} {:>8s} {:>9s} {:>9s} {:>9s} {:>8s}".format(
        "learner type", "removed", "any fade", "all 3", "reversion", "cap")
    print(header)
    print("-" * len(header))
    for name, data in report["by_type"].items():
        s = data["stats"]
        print("{:24s} {:8.2f} {:8.0f}% {:8.0f}% {:8.0f}% {:7.0f}%".format(
            name, s["mean_elements_removed"], 100 * s["share_any_fade"],
            100 * s["share_all_three_removed"], 100 * s["share_any_reversion"],
            100 * s["share_cap_reached"]))
    print()
    for t in report["targets"]:
        print("[{}] {}".format("PASS" if t["met"] else "FAIL", t["id"]))
        print("      {}".format(t["statement"]))
        print("      measured: {}".format(json.dumps(t["measured"])))
    print()
    print("GATE G1: {}".format(
        "MET" if all(t["met"] for t in report["targets"]) else "NOT MET"))


def cmd_run(args):
    cfg = load_config()
    references = load_references()
    report = run(cfg, references, args.streams, args.seed)
    print_report(report)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        doc = strip_summaries(report)
        doc["config_id"] = cfg["config_id"]
        doc["config_sha256"] = config_hash()
        doc["seed"] = args.seed
        (out / "simulation_report.json").write_text(
            json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        (out / "feasibility_figure.svg").write_text(
            feasibility_svg(report, cfg["config_id"]), encoding="utf-8")
        print("\nwrote {} and {}".format(out / "simulation_report.json",
                                         out / "feasibility_figure.svg"))
    return 0 if all(t["met"] for t in report["targets"]) else 1


def cmd_sweep(args):
    cfg = load_config()
    references = load_references()
    results, passing = sweep(cfg, references, args.streams, args.seed)
    print("evaluated {} candidate configurations at {} streams/type/pair\n".format(
        len(results), args.streams))
    print("{:>10s} {:>10s} {:>8s} {:>7s}  {:>10s}  {}".format(
        "brake_m", "speed_kmh", "apex_m", "ratio", "looseness", "targets met"))
    for r in results:
        p = r["params"]
        print("{:10.1f} {:10.1f} {:8.1f} {:7.2f}  {:10.3f}  {}".format(
            p["band_floors.braking_m"], p["band_floors.corner_speed_kmh"],
            p["band_floors.apex_m"], p["criteria.consistency_delta_ratio"],
            r["looseness"],
            "".join("Y" if t["met"] else "." for t in r["targets"])))
    print()
    if not passing:
        print("NO candidate met every design target. Gate G1 is not met; either the "
              "grid is too narrow or the novice model's noise is incompatible with "
              "the mechanism as configured.")
    else:
        best = passing[0]
        print("tightest configuration meeting every target:")
        for k, v in sorted(best["params"].items()):
            print("    {} = {}".format(k, v))
        print("\nfreeze it with:")
        print("    python -m trace_kit.simulate freeze --config-id frozen-g1 \\")
        print("        " + " ".join("--set {}={}".format(k, v)
                                    for k, v in sorted(best["params"].items())))
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "sweep_report.json").write_text(
            json.dumps({"grid": {k: v for k, v in SWEEP_GRID.items()},
                        "streams_per_type_per_pair": args.streams,
                        "seed": args.seed,
                        "candidates": results}, indent=2) + "\n", encoding="utf-8")
        print("\nwrote {}".format(out / "sweep_report.json"))
    return 0 if passing else 1


def cmd_freeze(args):
    cfg = load_config()
    cfg["config_id"] = args.config_id
    for assignment in args.set or []:
        dotted, value = assignment.split("=")
        _set(cfg, dotted, float(value))
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("wrote {}".format(CONFIG_PATH))
    print("config_id: {}".format(cfg["config_id"]))
    print("sha256:    {}".format(config_hash()))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="trace_kit.simulate",
        description="Phase 1 controller simulation and threshold calibration (Gate G1).")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler, default_streams in (("run", cmd_run, 100), ("sweep", cmd_sweep, 15)):
        p = sub.add_parser(name)
        p.add_argument("--streams", type=int, default=default_streams,
                       help="streams per learner type per pair (default %(default)s)")
        p.add_argument("--seed", default="trace-g1", help="RNG seed (default %(default)s)")
        p.add_argument("--out", help="directory for the report and figure")
        p.add_argument("--model", action="append", metavar="KEY=VALUE",
                       help="override a novice-model parameter, repeatable "
                            "(e.g. --model brake_sigma_m=2). A G1 verdict is only "
                            "as good as this model, so re-running under a different "
                            "one is a first-class operation.")
        p.set_defaults(func=handler)

    p = sub.add_parser("freeze")
    p.add_argument("--config-id", required=True)
    p.add_argument("--set", action="append",
                   help="section.key=value, repeatable (e.g. band_floors.braking_m=8)")
    p.set_defaults(func=cmd_freeze)

    args = parser.parse_args(argv)
    for assignment in getattr(args, "model", None) or []:
        key, value = assignment.split("=")
        if key not in MODEL:
            parser.error("unknown novice-model parameter '{}'; known: {}".format(
                key, ", ".join(MODEL)))
        MODEL[key] = float(value)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
