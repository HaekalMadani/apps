"""Reference extractor and AI-vs-human comparison (impl-plan M3 / section 2.2,
eval-plan Phase 0).

Turns recorded reference laps -- AC AI laps at 95-100% strength, and the human
validation laps -- into the **per-corner reference table** every downstream
component consumes: the marker world coordinates the renderer draws at, the
per-metric means the criteria are judged against, and the per-metric sigma_ref
the tolerance bands are built from.

Inputs are ordinary TRACE blocks (a ``manifest_*.json`` plus its
``ticks_*.csv``), recorded through the same runtime participants use -- which is
why Phase 0 doubles as the pipeline's end-to-end test. Nothing here reads the
game; nothing here invents a constant. The brake-initiation event definition
comes from ``controller_config.json`` (one source of constants, impl plan
section 6.3), the corner geometry from the track's annotation, and the
spline-to-metre scale from the block's own ``track_length_m``.

Two commands:

    extract   blocks -> reference_<pair>.json + a quality report (Gate G0's
              lap-time CoV, per-corner contributing-lap counts)
    compare   an AI table and a human table -> the per-corner divergence report
              and a substituted table (Gate G0's substitution decisions)

What the metrics mean here (framing v6, restated because the arithmetic below
only makes sense with them in view):

* **Brake initiation** is the first sample inside the annotated braking zone
  where brake input crosses the configured threshold *and stays above it* for
  the debounce window -- not merely the first tap. Its sigma is measured along
  the track in metres, ``(spline_lap - spline_mean) * track_length_m``.
* **Minimum corner speed** is the minimum over the annotated corner-speed zone.
* **Apex** is *RMS lateral deviation from the expert line over a window centred
  on the apex gate*, never a single sample at the gate. So the reference is a
  sampled **line**, not a point: each lap is resampled onto a common spline grid
  across the window, the grid is averaged into the expert line, and each lap's
  RMS distance from that line gives the per-lap value whose mean and sigma are
  stored. At a fixed spline both positions sit at the same longitudinal station,
  so the distance between them is lateral by construction -- which is why the
  deviation is taken in the horizontal (X/Z) plane and elevation is ignored.

A compound corner has several apex gates but still yields **one** apex value per
pass, taken over the union of its windows -- the controller consumes one boolean
per element per pass.

Stdlib + trace_kit.validate only. Runnable as a CLI.
"""

import argparse
import csv
import json
import math
import statistics
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTROLLER_CONFIG = REPO_ROOT / "configs" / "controller_config.json"

# Spline grid step for the apex line, in metres of track length. 1 m is finer
# than the 20 Hz log itself (~1.4 m between samples at 100 km/h), so the grid is
# interpolation-limited rather than resolution-limited, and a 20 m half-width
# yields a readable 41-point line.
APEX_GRID_STEP_M = 1.0

# A corner's reference is refused below this many contributing laps. The schema
# permits sigma_ref = 0 (the AC AI really is that repeatable, and the band floors
# exist to absorb it), so the guard against a spuriously tiny sigma lives here,
# where the lap count is known, rather than as a bound on the value.
MIN_LAPS_PER_CORNER = 5

# Lap-time coefficient of variation Gate G0 requires of the reference laps.
G0_MAX_LAP_TIME_COV = 0.01

# A pass is dropped from the reference when this many wheels leave the track
# (AC's "more than two wheels off" rule), matching lib/pass_tracker.lua.
WHEELS_OUTSIDE_INVALID_MIN = 3


# --- spline arithmetic ------------------------------------------------------
#
# The spline wraps 1 -> 0 at start/finish and annotated zones may straddle the
# line, so every comparison below goes through these two helpers rather than
# raw subtraction.

def forward_span(start, end):
    """Forward distance start -> end in spline units, always in [0, 1)."""
    return (end - start) % 1.0


def signed_delta(a, b):
    """Shortest signed spline delta a -> b, in (-0.5, 0.5]."""
    return ((b - a + 0.5) % 1.0) - 0.5


def in_zone(spline, start, end):
    """True if `spline` lies in the forward interval [start, end], wrap included."""
    return forward_span(start, spline) <= forward_span(start, end)


def forward_crossed(prev, cur, gate, wrap_threshold=0.5):
    """True iff driving forward from `prev` to `cur` passes through `gate`.

    Mirrors ``M.forward_crossed`` in lua/trace_rt/lib/pass_tracker.lua exactly --
    the extractor must segment reference laps into corner passes the same way
    the runtime segments participant laps, or the reference would describe
    slightly different stretches of track than the criteria are evaluated over.
    kit/tests/test_m3_reference.py pins the two implementations against each
    other over a shared case corpus.
    """
    if cur >= prev:
        if (cur - prev) > wrap_threshold:
            return False
        return prev < gate <= cur
    if (prev - cur) > wrap_threshold:
        return gate > prev or gate <= cur
    return False


# --- reading blocks ---------------------------------------------------------

TICK_FLOATS = ("t", "spline", "pos_x", "pos_y", "pos_z", "speed_kmh", "brake", "throttle", "steer")
TICK_INTS = ("lap", "gear", "wheels_outside")


def read_ticks(ticks_path):
    """Parse a ticks CSV into a list of typed row dicts, in file order."""
    rows = []
    with open(ticks_path, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row = {}
            for k in TICK_FLOATS:
                if k in raw:
                    row[k] = float(raw[k])
            for k in TICK_INTS:
                if k in raw:
                    row[k] = int(raw[k])
            row["in_pit"] = raw.get("in_pit", "0") == "1"
            rows.append(row)
    return rows


def load_block(manifest_path):
    """Load one recorded block. Returns (manifest, rows)."""
    manifest_path = Path(manifest_path)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    ticks_path = manifest_path.parent / "ticks_{}.csv".format(manifest["block_id"])
    return manifest, read_ticks(ticks_path)


def lap_times(rows):
    """Per-lap durations, seconds, keyed by lap number.

    Derived from the tick clock at lap-counter changes. Only laps whose start
    AND end are both inside the recording are timed. Both ends need excluding,
    for different reasons: the LAST lap has no following lap-change to end it,
    and the FIRST lap's start is before recording began -- what looks like a lap
    there is only its tail. Recording almost never begins exactly on the line,
    so the first entry is otherwise a stray fragment (0.05 s in the first real
    reference block) that wrecks the lap-time CoV Gate G0 is judged on. It also
    matches the eval plan's lap-validity rule, which discards the first lap of a
    block anyway.

    At 20 Hz the quantisation is +/- 0.05 s -- about 0.09% of a 55 s lap, far
    inside G0's 1% CoV bar.
    """
    starts = OrderedDict()
    for row in rows:
        starts.setdefault(row["lap"], row["t"])
    laps = list(starts)
    return OrderedDict(
        (laps[i], starts[laps[i + 1]] - starts[laps[i]]) for i in range(1, len(laps) - 1)
    )


# --- corner passes ----------------------------------------------------------

def corner_passes(rows, corner):
    """Yield the rows of each complete entry-gate -> exit-gate pass of `corner`.

    Yields dicts: {corner_id, lap, rows}. Incomplete passes (recording started
    or stopped mid-corner) are not yielded -- a reference must never be built
    from a half-observed corner.
    """
    entry, exit_gate = corner["entry_gate"], corner["exit_gate"]
    open_rows = None
    prev = None
    for row in rows:
        cur = row["spline"]
        if prev is not None:
            if open_rows is not None:
                open_rows.append(row)
                if forward_crossed(prev, cur, exit_gate):
                    yield {"corner_id": corner["id"], "lap": open_rows[0]["lap"], "rows": open_rows}
                    open_rows = None
            elif forward_crossed(prev, cur, entry):
                open_rows = [row]
        prev = cur


def pass_is_clean(pass_rows):
    """A reference pass must be on-track and out of the pits."""
    return not any(
        r["in_pit"] or r.get("wheels_outside", 0) >= WHEELS_OUTSIDE_INVALID_MIN
        for r in pass_rows
    )


def zone_rows(pass_rows, zone):
    """Rows of a pass lying inside an annotated zone (wrap-aware)."""
    return [r for r in pass_rows if in_zone(r["spline"], zone["start"], zone["end"])]


# --- per-lap metrics --------------------------------------------------------

def brake_initiation(pass_rows, braking_zone, threshold, debounce_s):
    """First sustained brake application inside the braking zone, or None.

    "Sustained" = brake input at or above `threshold` and still at or above it
    without interruption for `debounce_s`, which is what distinguishes turn-in
    braking from a pedal tap or a brush of the pedal on the approach (impl plan
    section 7). Every sample in the candidate window must stay above threshold,
    not merely its endpoints.

    The zone bounds where the event is *searched for*, not where braking must
    stay: the hold is checked over the rest of the pass, because a trail-braking
    driver is legitimately still on the brakes past the zone's end. A pass that
    ends before the debounce window elapses yields no event -- the hold was
    never observed, and guessing one would put an unobserved point into the
    reference.
    """
    for i, row in enumerate(pass_rows):
        if row["brake"] < threshold:
            continue
        if not in_zone(row["spline"], braking_zone["start"], braking_zone["end"]):
            continue
        t0 = row["t"]
        for later in pass_rows[i:]:
            if later["brake"] < threshold:
                break                      # released too early; keep scanning
            if later["t"] - t0 >= debounce_s:
                return row
    return None


# How much track must lie between the start of a braking zone and the expert's
# brake point. The zone bounds where a brake initiation is SEARCHED FOR, and
# novices brake EARLIER than the reference -- so a zone that only just contains
# the expert's point will silently miss a participant braking 30 m early,
# yielding a null metric and dropping that corner out of the braking element's
# evidence without anything looking wrong. Generous is nearly free; the only
# cost of a wide zone is reaching back toward the previous corner's braking.
MIN_EARLY_MARGIN_M = 30.0


def check_braking_zone_fit(corner, passes, braking_zone, threshold, track_length_m):
    """Problems where a braking zone does not sit where the car actually brakes.

    Two failure modes, both silent without this check, and both found in the
    first real International reference block:

      * the car is ALREADY braking as it enters the zone -- the true initiation
        happened before the zone opened, so the detector clamps every lap to the
        zone start and reports a brake point that is biased late and
        artificially consistent (a fake near-zero sigma);
      * the zone leaves too little room before the expert's brake point for a
        novice, who brakes earlier, to be detected at all.

    Both are annotation faults, not data faults: the braking zones were captured
    by driving and pressing a button, and a beginner's brake points sit well
    before a 95-100% AI's.
    """
    problems = []
    already_braking = 0
    margins = []
    for p in passes:
        rows = zone_rows(p["rows"], braking_zone)
        if not rows:
            continue
        if rows[0]["brake"] >= threshold:
            already_braking += 1
        hit = brake_initiation(p["rows"], braking_zone, threshold, 0.0)
        if hit is not None:
            margins.append(signed_delta(braking_zone["start"], hit["spline"]) * track_length_m)

    if already_braking:
        problems.append(
            "corner {}: the car was ALREADY braking on entering the braking zone "
            "in {} of {} pass(es) -- the zone opens too late, so the recorded "
            "brake point is clamped to the zone start (biased late, sigma "
            "artificially small). Move zones.braking.start earlier".format(
                corner["id"], already_braking, len(passes))
        )
    if margins:
        worst = min(margins)
        if worst < MIN_EARLY_MARGIN_M:
            problems.append(
                "corner {}: only {:.1f} m of braking zone lies before the expert's "
                "brake point (want >= {:.0f} m). Novices brake EARLIER than the "
                "reference, so their brake initiation would fall outside the zone "
                "and go undetected. Move zones.braking.start earlier".format(
                    corner["id"], worst, MIN_EARLY_MARGIN_M)
            )
    return problems


def min_corner_speed(pass_rows, corner_speed_zone):
    """Minimum speed over the corner-speed zone, or None if it was not sampled."""
    rows = zone_rows(pass_rows, corner_speed_zone)
    return min((r["speed_kmh"] for r in rows), default=None)


def apex_grid(gate_spline, half_m, track_length_m, step_m=APEX_GRID_STEP_M):
    """The common spline grid across one apex window, in driving order."""
    half_spline = half_m / track_length_m
    steps = max(1, int(round(half_m / step_m)))
    return [(gate_spline + (i / steps) * half_spline) % 1.0 for i in range(-steps, steps + 1)]


def pass_axis(pass_rows):
    """Forward distance along the pass, in spline units, from its first sample.

    The pass's own first sample is the anchor, so the axis is monotone and
    ordinary numeric comparison works even when the pass straddles
    start/finish. Anchoring to the PASS (rather than unwrapping around the apex
    gate) is what lets the caller tell "this window is outside this pass" from
    "this window wraps the line" -- unwrapping around the gate maps far-away
    rows to small offsets and would happily interpolate across half a lap.

    A sample a hair *behind* the anchor -- spline jitter at the entry gate --
    would otherwise wrap to ~1.0, so anything past the half-lap mark is read as
    that, exactly as lib/pass_tracker.lua's WRAP_THRESHOLD reads a large
    backward step as a forward wrap. A corner pass is a small fraction of a lap,
    so 0.5 is a wide separator.
    """
    axis = []
    start = pass_rows[0]["spline"]
    for row in pass_rows:
        d = forward_span(start, row["spline"])
        if d > 0.5:
            d = 0.0
        axis.append(max(d, axis[-1]) if axis else d)
    return axis


def sample_line(pass_rows, grid, gate_spline):
    """Interpolate a pass's world positions onto an apex grid.

    Returns a list of (x, y, z) aligned to `grid`, or None when the pass does not
    cover the whole window (which excludes that lap from the apex reference
    rather than silently extrapolating it).
    """
    if len(pass_rows) < 2:
        return None
    axis = pass_axis(pass_rows)
    start = pass_rows[0]["spline"]
    out = []
    for g in grid:
        gd = forward_span(start, g)
        if gd < axis[0] or gd > axis[-1]:
            return None
        lo = 0
        for i in range(len(axis) - 1):
            if axis[i] <= gd:
                lo = i
        hi = min(lo + 1, len(axis) - 1)
        d0, d1 = axis[lo], axis[hi]
        r0, r1 = pass_rows[lo], pass_rows[hi]
        f = 0.0 if d1 == d0 else (gd - d0) / (d1 - d0)
        out.append(tuple(
            r0["pos_" + a] + f * (r1["pos_" + a] - r0["pos_" + a]) for a in ("x", "y", "z")
        ))
    return out


def mean_positions(lines):
    """Element-wise mean of aligned position lists."""
    return [
        tuple(statistics.fmean(line[i][a] for line in lines) for a in range(3))
        for i in range(len(lines[0]))
    ]


def rms_lateral(line, expert_line):
    """RMS horizontal distance between two aligned position lists, metres.

    Horizontal (X/Z) only: at a fixed spline both points share a longitudinal
    station, so their separation is lateral, and elevation difference is not
    line error.
    """
    total = sum(
        (a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2 for a, b in zip(line, expert_line)
    )
    return math.sqrt(total / len(line))


def _stdev(values):
    """Sample standard deviation; 0.0 for a single value."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


# --- extraction -------------------------------------------------------------

def extract_corner(corner, passes, track_length_m, brake_threshold, debounce_s, source):
    """Build one reference-table corner from its clean passes.

    Returns (corner_doc, problems, stats). `corner_doc` is None when the corner
    cannot be referenced at all.
    """
    problems = []
    stats = {"corner_id": corner["id"], "passes": len(passes)}
    zones = corner["zones"]

    # --- braking (absent by design on a corner taken flat) ---
    braking_doc = None
    if "braking" in zones:
        hits = [brake_initiation(p["rows"], zones["braking"],
                                 brake_threshold, debounce_s) for p in passes]
        hits = [h for h in hits if h is not None]
        stats["braking_laps"] = len(hits)
        if len(hits) < MIN_LAPS_PER_CORNER:
            problems.append(
                "corner {}: brake initiation found on only {} of {} pass(es); "
                "need >= {}. Either the corner is taken flat (drop zones.braking) "
                "or the braking zone does not cover where the car actually brakes "
                "(check it against a reference lap)".format(
                    corner["id"], len(hits), len(passes), MIN_LAPS_PER_CORNER)
            )
        problems.extend(check_braking_zone_fit(corner, passes, zones["braking"],
                                               brake_threshold, track_length_m))
        if hits:
            ref_spline = hits[0]["spline"]
            offsets = [signed_delta(ref_spline, h["spline"]) for h in hits]
            mean_spline = (ref_spline + statistics.fmean(offsets)) % 1.0
            dists_m = [signed_delta(mean_spline, h["spline"]) * track_length_m for h in hits]
            braking_doc = OrderedDict([
                ("world_pos", [round(statistics.fmean(h["pos_" + a] for h in hits), 4)
                               for a in ("x", "y", "z")]),
                ("spline_pos", round(mean_spline, 8)),
                ("sigma_ref_m", round(_stdev(dists_m), 4)),
            ])
    else:
        stats["braking_laps"] = None   # not applicable to the braking element

    # --- apex: one expert line per gate, one RMS per pass over their union ---
    #
    # The apex window is evaluated inside the pass, so it has to FIT inside the
    # pass bracket -- a window running past the exit gate can never be covered
    # and would otherwise show up only as the opaque "covered by 0 of N passes".
    # Easy to create by accident when a corner's bracket is short: either widen
    # the bracket or shrink that corner's apex_window_half_m.
    for gate_spline in zones["apex_gates"]:
        lead = signed_delta(corner["entry_gate"], gate_spline) * track_length_m
        tail = signed_delta(gate_spline, corner["exit_gate"]) * track_length_m
        half_m = zones["apex_window_half_m"]
        if lead < half_m or tail < half_m:
            problems.append(
                "corner {}: apex window (+/-{:.0f} m around {:.4f}) does not fit inside "
                "the pass bracket ({:.0f} m before the gate, {:.0f} m after) -- widen the "
                "bracket or reduce apex_window_half_m".format(
                    corner["id"], half_m, gate_spline, lead, tail)
            )

    gates_doc = []
    per_pass_rms = {}
    for gate_spline in zones["apex_gates"]:
        grid = apex_grid(gate_spline, zones["apex_window_half_m"], track_length_m)
        sampled = OrderedDict()
        for index, p in enumerate(passes):
            line = sample_line(p["rows"], grid, gate_spline)
            if line is not None:
                sampled[index] = line
        if len(sampled) < MIN_LAPS_PER_CORNER:
            problems.append(
                "corner {}: apex gate {:.5f} covered by only {} of {} pass(es); "
                "need >= {}".format(corner["id"], gate_spline, len(sampled),
                                    len(passes), MIN_LAPS_PER_CORNER)
            )
        if not sampled:
            return None, problems, stats
        expert = mean_positions(list(sampled.values()))
        for key, line in sampled.items():
            # Squared error accumulates across a compound corner's gates so the
            # union yields a single RMS per pass.
            se, n = per_pass_rms.get(key, (0.0, 0))
            per_pass_rms[key] = (se + rms_lateral(line, expert) ** 2 * len(grid), n + len(grid))
        centre = expert[len(expert) // 2]
        gates_doc.append(OrderedDict([
            ("world_pos", [round(c, 4) for c in centre]),
            ("spline_pos", round(gate_spline, 8)),
            ("line", [
                OrderedDict([
                    ("spline_pos", round(s, 8)),
                    ("world_pos", [round(c, 4) for c in pos]),
                ])
                for s, pos in zip(grid, expert)
            ]),
        ]))
    rms_values = [math.sqrt(se / n) for se, n in per_pass_rms.values()]
    stats["apex_laps"] = len(rms_values)

    # --- corner speed ---
    speeds = [min_corner_speed(p["rows"], zones["corner_speed"]) for p in passes]
    speeds = [s for s in speeds if s is not None]
    stats["corner_speed_laps"] = len(speeds)
    if len(speeds) < MIN_LAPS_PER_CORNER:
        problems.append(
            "corner {}: minimum corner speed found on only {} of {} pass(es); "
            "need >= {}".format(corner["id"], len(speeds), len(passes), MIN_LAPS_PER_CORNER)
        )
    if not speeds:
        return None, problems, stats

    doc = OrderedDict([("corner_id", corner["id"]), ("source", source)])
    # Carried into the table so Gate G0's "every corner contributing at least the
    # extractor's minimum lap count" is checkable from the committed file, not
    # only from this run's console output.
    contributing = OrderedDict([("clean_passes", len(passes))])
    if stats["braking_laps"] is not None:
        contributing["braking"] = stats["braking_laps"]
    contributing["apex"] = stats["apex_laps"]
    contributing["corner_speed"] = stats["corner_speed_laps"]
    doc["contributing_laps"] = contributing
    if braking_doc is not None:
        doc["braking"] = braking_doc
    doc["apex"] = OrderedDict([
        ("gates", gates_doc),
        ("mean_rms_m", round(statistics.fmean(rms_values), 4)),
        ("sigma_ref_m", round(_stdev(rms_values), 4)),
    ])
    doc["corner_speed"] = OrderedDict([
        ("mean_kmh", round(statistics.fmean(speeds), 3)),
        ("sigma_ref_kmh", round(_stdev(speeds), 4)),
    ])
    return doc, problems, stats


def extract(blocks, annotation, pair_id, car, track_length_m, source,
            brake_threshold, debounce_s, source_laps=None):
    """Build a reference table from loaded blocks.

    `blocks` is a list of row-lists (one per recorded block). Returns
    (doc, problems, report).
    """
    problems = []
    report = {"corners": [], "lap_times": [], "lap_time_cov": None}

    for rows in blocks:
        report["lap_times"].extend(round(v, 3) for v in lap_times(rows).values())

    if len(report["lap_times"]) >= 2:
        mean_t = statistics.fmean(report["lap_times"])
        cov = _stdev(report["lap_times"]) / mean_t if mean_t else None
        report["lap_time_cov"] = cov
        if cov is not None:
            source_laps = dict(source_laps or {})
            source_laps["lap_time_cov_pct"] = round(cov * 100.0, 4)
        if cov is not None and cov >= G0_MAX_LAP_TIME_COV:
            problems.append(
                "lap-time CoV {:.3%} over {} lap(s) fails Gate G0's < {:.0%} bar".format(
                    cov, len(report["lap_times"]), G0_MAX_LAP_TIME_COV)
            )
    else:
        problems.append("fewer than 2 timed laps: no lap-time CoV for Gate G0")

    corners_doc = []
    for corner in annotation["corners"]:
        passes = []
        for rows in blocks:
            passes.extend(p for p in corner_passes(rows, corner) if pass_is_clean(p["rows"]))
        if not passes:
            problems.append("corner {}: no clean passes in any block".format(corner["id"]))
            continue
        doc, corner_problems, stats = extract_corner(
            corner, passes, track_length_m, brake_threshold, debounce_s, source)
        problems.extend(corner_problems)
        report["corners"].append(stats)
        if doc is not None:
            corners_doc.append(doc)

    missing = {c["id"] for c in annotation["corners"]} - {c["corner_id"] for c in corners_doc}
    if missing:
        problems.append("no reference extracted for corner(s): {}".format(sorted(missing)))

    doc = OrderedDict([
        ("schema_version", 1),
        ("pair_id", pair_id),
        ("track", annotation["track"]),
        ("car", car),
        ("track_length_m", round(track_length_m, 3)),
    ])
    if source_laps:
        doc["source_laps"] = OrderedDict(sorted(source_laps.items()))
    doc["corners"] = corners_doc
    return doc, problems, report


# --- AI vs human comparison (Gate G0) ---------------------------------------

def band(sigma, evm, floor):
    """The tolerance band a reference imposes: max(sigma x EVM, floor)."""
    return max(sigma * evm, floor)


def compare_corner(ai, human, track_length_m, evm_ai, floors):
    """Per-corner AI-vs-human divergence, and whether it is *material*.

    The substitution rule (M3 decision, recorded in configs/references/README.md):
    a corner is materially divergent on an element when the human reference
    point falls **outside the tolerance band the AI reference would impose** --
    that is, when a competent human driving the same car and setup would itself
    fail the AI-anchored criterion. Such a criterion is not a usable target for a
    learner, so that corner takes the human reference.

    Substitution is per CORNER, triggered by divergence on any element: mixing a
    human brake point with an AI apex line within one corner would describe a
    corner nobody drove.
    """
    result = {"corner_id": ai["corner_id"], "elements": OrderedDict(), "material": False}

    if "braking" in ai and "braking" in human:
        delta_m = signed_delta(ai["braking"]["spline_pos"],
                               human["braking"]["spline_pos"]) * track_length_m
        limit = band(ai["braking"]["sigma_ref_m"], evm_ai, floors["braking_m"])
        result["elements"]["braking"] = {
            "delta": delta_m, "unit": "m", "ai_band": limit,
            "material": abs(delta_m) > limit,
        }

    delta_kmh = human["corner_speed"]["mean_kmh"] - ai["corner_speed"]["mean_kmh"]
    limit = band(ai["corner_speed"]["sigma_ref_kmh"], evm_ai, floors["corner_speed_kmh"])
    result["elements"]["corner_speed"] = {
        "delta": delta_kmh, "unit": "km/h", "ai_band": limit,
        "material": abs(delta_kmh) > limit,
    }

    # Apex: how far the human's line sits from the AI's, averaged over the
    # window -- a line-to-line offset, not a difference of RMS scalars.
    offsets = []
    for ai_gate, human_gate in zip(ai["apex"]["gates"], human["apex"]["gates"]):
        offsets.extend(
            math.hypot(a["world_pos"][0] - h["world_pos"][0], a["world_pos"][2] - h["world_pos"][2])
            for a, h in zip(ai_gate["line"], human_gate["line"])
        )
    delta_apex = statistics.fmean(offsets) if offsets else 0.0
    limit = band(ai["apex"]["sigma_ref_m"], evm_ai, floors["apex_m"])
    result["elements"]["apex"] = {
        "delta": delta_apex, "unit": "m", "ai_band": limit,
        "material": delta_apex > limit,
    }

    result["material"] = any(e["material"] for e in result["elements"].values())
    return result


def compare(ai_doc, human_doc, evm_ai, floors):
    """Compare two reference tables for the same pair. Returns (rows, problems)."""
    problems = []
    for field in ("pair_id", "track", "car"):
        if ai_doc[field] != human_doc[field]:
            problems.append("{} differs: AI {!r} vs human {!r}".format(
                field, ai_doc[field], human_doc[field]))
    if abs(ai_doc["track_length_m"] - human_doc["track_length_m"]) > 1.0:
        problems.append("track_length_m differs: {} vs {}".format(
            ai_doc["track_length_m"], human_doc["track_length_m"]))

    human_by_id = {c["corner_id"]: c for c in human_doc["corners"]}
    rows = []
    for ai_corner in ai_doc["corners"]:
        human_corner = human_by_id.get(ai_corner["corner_id"])
        if human_corner is None:
            problems.append("corner {}: no human reference to compare".format(
                ai_corner["corner_id"]))
            continue
        rows.append(compare_corner(ai_corner, human_corner,
                                   ai_doc["track_length_m"], evm_ai, floors))
    return rows, problems


def substitute(ai_doc, human_doc, comparison):
    """AI table with materially divergent corners replaced by the human ones.

    Every substituted corner keeps ``source: "human"``, which is what selects
    EVM_human over EVM_AI at run time, so the swap is not merely bookkeeping.
    """
    human_by_id = {c["corner_id"]: c for c in human_doc["corners"]}
    material = {r["corner_id"] for r in comparison if r["material"]}
    doc = OrderedDict(ai_doc)
    doc["corners"] = [
        human_by_id[c["corner_id"]] if c["corner_id"] in material else c
        for c in ai_doc["corners"]
    ]
    # The substituted table draws on BOTH lap sets, so it must carry both
    # provenances -- otherwise the file the runtime actually loads would credit
    # every corner to the AI while some of them came from the human laps.
    merged = OrderedDict(ai_doc.get("source_laps") or {})
    for key, value in (human_doc.get("source_laps") or {}).items():
        if key.startswith("human") or key not in merged:
            merged[key] = value
    if merged:
        doc["source_laps"] = OrderedDict(sorted(merged.items()))
    return doc, sorted(material)


# --- CLI --------------------------------------------------------------------

def load_controller_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _resolve_manifests(paths):
    out = []
    for p in paths:
        p = Path(p)
        out.extend(sorted(p.glob("manifest_*.json")) if p.is_dir() else [p])
    return out


def cmd_extract(args):
    cfg = load_controller_config(args.config)
    manifests = _resolve_manifests(args.blocks)
    if not manifests:
        print("no blocks found in {}".format(args.blocks))
        return 1

    with open(args.annotation, encoding="utf-8") as f:
        annotation = json.load(f)

    blocks, track_lengths, cars = [], [], []
    for m_path in manifests:
        manifest, rows = load_block(m_path)
        blocks.append(rows)
        if manifest.get("track_length_m"):
            track_lengths.append(manifest["track_length_m"])
        if manifest.get("car_id"):
            cars.append(manifest["car_id"])
        print("  block {}: {} tick(s)".format(manifest["block_id"], len(rows)))

    track_length_m = args.track_length or (track_lengths[0] if track_lengths else None)
    if track_length_m is None:
        print("no track_length_m in any manifest (pre-M3 block?); pass --track-length")
        return 1
    if track_lengths and max(track_lengths) - min(track_lengths) > 1.0:
        print("WARNING: blocks disagree on track_length_m: {}".format(sorted(set(track_lengths))))

    car = args.car or (cars[0] if cars else None)
    if car is None:
        print("no car_id in any manifest (pre-M3 block?); pass --car")
        return 1

    source_laps = {"setup": args.setup}
    if args.source == "ai":
        source_laps["ai_laps"] = sum(len(lap_times(rows)) for rows in blocks)
        if args.ai_strength is not None:
            source_laps["ai_strength_pct"] = args.ai_strength
    else:
        source_laps["human_laps"] = sum(len(lap_times(rows)) for rows in blocks)
        source_laps["human_driver"] = args.human_driver

    doc, problems, report = extract(
        blocks, annotation, args.pair, car, track_length_m, args.source,
        cfg["brake_initiation"]["threshold"],
        cfg["brake_initiation"]["debounce_ms"] / 1000.0,
        source_laps=source_laps,
    )

    schema_errors = pyval.validate_data("reference", doc)
    out = Path(args.out) if args.out else Path("reference_{}.json".format(args.pair))
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print("wrote {}  ({} corner(s), source {})".format(out, len(doc["corners"]), args.source))

    if report["lap_time_cov"] is not None:
        print("  lap-time CoV: {:.3%} over {} lap(s)  (G0 bar: < {:.0%})".format(
            report["lap_time_cov"], len(report["lap_times"]), G0_MAX_LAP_TIME_COV))
    for stats in report["corners"]:
        print("  corner {}: {} clean pass(es)  braking={} apex={} speed={}".format(
            stats["corner_id"], stats["passes"],
            "n/a" if stats.get("braking_laps") is None else stats["braking_laps"],
            stats.get("apex_laps"), stats.get("corner_speed_laps")))
    for p in problems:
        print("  - problem: {}".format(p))
    for e in schema_errors:
        print("  - schema: {}".format(e))
    return 1 if (problems or schema_errors) else 0


def cmd_compare(args):
    cfg = load_controller_config(args.config)
    with open(args.ai, encoding="utf-8") as f:
        ai_doc = json.load(f)
    with open(args.human, encoding="utf-8") as f:
        human_doc = json.load(f)

    rows, problems = compare(ai_doc, human_doc, cfg["evm"]["ai"], cfg["band_floors"])

    print("AI-vs-human per-corner comparison ({})".format(ai_doc["pair_id"]))
    print("  substitution rule: substitute the corner when the human reference falls")
    print("  outside the tolerance band the AI reference would impose.")
    for row in rows:
        print("  corner {}{}".format(row["corner_id"], "  <- SUBSTITUTE" if row["material"] else ""))
        for name, e in row["elements"].items():
            print("    {:13s} delta {:+8.3f} {:5s} vs AI band {:6.3f}  {}".format(
                name, e["delta"], e["unit"], e["ai_band"],
                "MATERIAL" if e["material"] else "ok"))
    for p in problems:
        print("  - problem: {}".format(p))

    if args.out:
        doc, substituted = substitute(ai_doc, human_doc, rows)
        errors = pyval.validate_data("reference", doc)
        Path(args.out).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print("wrote {}  (substituted: {})".format(args.out, substituted or "none"))
        for e in errors:
            print("  - schema: {}".format(e))
        if errors:
            return 1
    if args.report:
        Path(args.report).write_text(json.dumps(OrderedDict([
            ("generated", date.today().isoformat()),
            ("pair_id", ai_doc["pair_id"]),
            ("evm_ai", cfg["evm"]["ai"]),
            ("band_floors", cfg["band_floors"]),
            ("corners", rows),
        ]), indent=2) + "\n", encoding="utf-8")
        print("wrote report {}".format(args.report))
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="TRACE reference extractor (M3).")
    sub = parser.add_subparsers(dest="command", required=True)

    e = sub.add_parser("extract", help="build a reference table from recorded blocks")
    e.add_argument("blocks", nargs="+", help="manifest_*.json files, or directories of blocks")
    e.add_argument("--annotation", required=True, help="the track's annotation file")
    e.add_argument("--pair", required=True, help="pair id, e.g. pair1")
    e.add_argument("--source", required=True, choices=["ai", "human"])
    e.add_argument("--car", default=None, help="AC car id (default: from the manifest)")
    e.add_argument("--track-length", type=float, default=None,
                   help="track length in metres (default: from the manifest)")
    e.add_argument("--setup", default="default (car ships)", help="the fixed setup used")
    e.add_argument("--ai-strength", type=float, default=None, help="AI strength %% (source ai)")
    e.add_argument("--human-driver", default="researcher (not a study participant)",
                   help="ROLE of the human reference driver, never a name (source human)")
    e.add_argument("--config", default=str(DEFAULT_CONTROLLER_CONFIG))
    e.add_argument("-o", "--out", default=None)
    e.set_defaults(func=cmd_extract)

    c = sub.add_parser("compare", help="AI-vs-human comparison and substitution (Gate G0)")
    c.add_argument("ai", help="AI-sourced reference table")
    c.add_argument("human", help="human-sourced reference table for the same pair")
    c.add_argument("--config", default=str(DEFAULT_CONTROLLER_CONFIG))
    c.add_argument("-o", "--out", default=None, help="write the substituted reference table here")
    c.add_argument("--report", default=None, help="write the comparison report JSON here")
    c.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
