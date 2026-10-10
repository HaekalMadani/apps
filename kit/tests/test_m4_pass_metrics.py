"""M4: the runtime's in-pass metric accumulation, pinned to the extractor.

``lua/trace_rt/lib/pass_metrics.lua`` turns a per-frame sample stream into the
three raw metrics the evaluator judges. Offline, the same job belongs to
``trace_kit.reference``, which is what BUILT the reference table those metrics
are compared against. If the two detect events differently, the runtime compares
a participant against a reference measured a different way and every tolerance
band is quietly wrong — the same failure mode ``forward_crossed``'s parity test
already guards at the pass-segmentation level.

So these tests run both implementations over one corpus of synthetic passes and
require them to agree, then check the accumulators' own edge cases (wrap,
uncovered apex windows, pedal taps).

The Lua runs headless through lupa (LuaJIT 2.1), matching CSP.
"""

import json
import math
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import reference as ref

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"

TRACK_LENGTH_M = 2600.0
BRAKE_THRESHOLD = 0.1
DEBOUNCE_S = 0.1
DT = 0.05  # 20 Hz, the logged tick rate

CFG = {
    "brake_initiation": {"threshold": BRAKE_THRESHOLD, "debounce_ms": DEBOUNCE_S * 1000},
}


# --- synthetic passes --------------------------------------------------------

def make_rows(n, start_spline, step_spline, brake=None, speed=None, lateral=None):
    """A straight synthetic pass.

    The car runs along +X with spline advancing linearly and an optional lateral
    (Z) offset per sample, so an apex RMS has a known closed-form answer.
    """
    rows = []
    for i in range(n):
        spline = (start_spline + i * step_spline) % 1.0
        rows.append({
            "t": round(i * DT, 4),
            "spline": spline,
            "pos_x": spline * TRACK_LENGTH_M,
            "pos_y": 0.0,
            "pos_z": (lateral(i) if lateral else 0.0),
            "speed_kmh": (speed(i) if speed else 100.0),
            "brake": (brake(i) if brake else 0.0),
            "lap": 0,
            "gear": 3,
            "steer": 0.0,
            "throttle": 0.0,
            "wheels_outside": 0,
            "in_pit": False,
        })
    return rows


def straight_line(grid):
    """The expert line for a pass driven with zero lateral offset."""
    return [{"spline_pos": g, "world_pos": [g * TRACK_LENGTH_M, 0.0, 0.0]} for g in grid]


def plan_corner(braking_zone=None, corner_speed_zone=None, apex_line=None,
                brake_ref_spline=0.5):
    """An annotation corner + reference corner pair, as the runtime pairs them."""
    zones = {
        "apex_gates": [0.5],
        "apex_window_half_m": 20.0,
        "corner_speed": corner_speed_zone or {"start": 0.0, "end": 1.0},
    }
    if braking_zone:
        zones["braking"] = braking_zone
    corner = {"id": "C", "type": "medium", "compound": False,
              "entry_gate": 0.0, "exit_gate": 0.99, "zones": zones}
    reference = {
        "corner_id": "C", "source": "ai",
        "contributing_laps": {"clean_passes": 12, "apex": 12, "corner_speed": 12},
        "apex": {"gates": [{"world_pos": [0, 0, 0], "spline_pos": 0.5,
                            "line": apex_line or straight_line([0.49, 0.5, 0.51])}],
                 "mean_rms_m": 0.0, "sigma_ref_m": 0.0},
        "corner_speed": {"mean_kmh": 100.0, "sigma_ref_kmh": 1.0},
    }
    if braking_zone:
        reference["braking"] = {"world_pos": [0, 0, 0], "spline_pos": brake_ref_spline,
                                "sigma_ref_m": 1.0}
        reference["contributing_laps"]["braking"] = 12
    return corner, reference


# --- the two runners ---------------------------------------------------------

@pytest.fixture(scope="module")
def lua_metrics():
    """run(corner, reference, rows) -> the runtime's metrics for that pass."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval(
        """
        function(corner_json, ref_json, rows_json, track_length_m, cfg_json)
          local json = require('lib/json')
          local pm = require('lib/pass_metrics')
          local corner = json.decode(corner_json)
          local reference = { corners = { json.decode(ref_json) } }
          local rows = json.decode(rows_json)
          local plans = pm.plans({ corner }, reference, track_length_m, json.decode(cfg_json))
          local st = pm.open(plans[corner.id], rows[1])
          for i = 1, #rows do pm.update(st, rows[i]) end
          return json.encode(pm.close(st))
        end
        """
    )

    def run(corner, reference, rows):
        return json.loads(fn(json.dumps(corner), json.dumps(reference), json.dumps(rows),
                             TRACK_LENGTH_M, json.dumps(CFG)))

    return run


def extractor_metrics(corner, reference, rows):
    """The same three metrics computed the way trace_kit.reference computes them."""
    out = {}
    zones = corner["zones"]
    if "braking" in zones:
        hit = ref.brake_initiation(rows, zones["braking"], BRAKE_THRESHOLD, DEBOUNCE_S)
        if hit is not None:
            out["brake_initiation_distance_m"] = (
                ref.signed_delta(hit["spline"], reference["braking"]["spline_pos"])
                * TRACK_LENGTH_M)
            out["brake_initiation"] = {"t": hit["t"], "spline_pos": hit["spline"]}
    out["min_corner_speed_kmh"] = ref.min_corner_speed(rows, zones["corner_speed"])

    # Apex: sample the pass onto the reference line's own spline stations and
    # take the RMS against it, exactly as extract_corner does per lap.
    se, n = 0.0, 0
    complete = True
    for gate in reference["apex"]["gates"]:
        grid = [p["spline_pos"] for p in gate["line"]]
        line = ref.sample_line(rows, grid, gate["spline_pos"])
        if line is None:
            complete = False
            break
        expert = [tuple(p["world_pos"]) for p in gate["line"]]
        se += ref.rms_lateral(line, expert) ** 2 * len(grid)
        n += len(grid)
    if complete and n:
        out["apex_rms_m"] = math.sqrt(se / n)
    return out


def assert_agree(lua, extractor, keys=("brake_initiation_distance_m",
                                       "min_corner_speed_kmh", "apex_rms_m")):
    for key in keys:
        a, b = lua.get(key), extractor.get(key)
        if a is None or b is None:
            assert a is None and b is None, "{}: runtime={} extractor={}".format(key, a, b)
        else:
            assert a == pytest.approx(b, abs=1e-6), \
                "{}: runtime={} extractor={}".format(key, a, b)


# --- brake initiation --------------------------------------------------------

def test_sustained_braking_agrees_with_the_extractor(lua_metrics):
    zone = {"start": 0.30, "end": 0.45}
    corner, reference = plan_corner(braking_zone=zone, brake_ref_spline=0.40)
    # Brakes hard from sample 20 (spline 0.30 + 20*0.005 = 0.40... ) onward.
    rows = make_rows(80, 0.25, 0.005, brake=lambda i: 0.8 if i >= 30 else 0.0)
    lua = lua_metrics(corner, reference, rows)
    assert lua["brake_initiation_distance_m"] is not None
    assert_agree(lua, extractor_metrics(corner, reference, rows))


def test_a_pedal_tap_before_the_real_braking_is_ignored_by_both(lua_metrics):
    """The debounce constant exists for exactly this (impl plan section 7)."""
    zone = {"start": 0.30, "end": 0.60}
    corner, reference = plan_corner(braking_zone=zone, brake_ref_spline=0.50)

    def brake(i):
        if i == 22:          # one frame above threshold: a tap, not an initiation
            return 0.4
        return 0.8 if i >= 40 else 0.0

    rows = make_rows(90, 0.25, 0.005, brake=brake)
    lua = lua_metrics(corner, reference, rows)
    extractor = extractor_metrics(corner, reference, rows)
    assert_agree(lua, extractor)
    # And the tap really was skipped: the event is at the sustained application.
    assert lua["brake_initiation"]["spline_pos"] == pytest.approx(rows[40]["spline"])


def test_already_braking_on_entering_the_zone_clamps_identically(lua_metrics):
    """The M3 annotation fault, reproduced: both must clamp to the zone start.

    This is the case ``check_braking_zone_fit`` warns about offline. It must at
    least be detected the SAME way in both places, or a mis-fitted zone would
    bias the runtime and the reference in different directions.
    """
    zone = {"start": 0.40, "end": 0.60}
    corner, reference = plan_corner(braking_zone=zone, brake_ref_spline=0.50)
    rows = make_rows(90, 0.25, 0.005, brake=lambda i: 0.8 if i >= 10 else 0.0)
    lua = lua_metrics(corner, reference, rows)
    assert_agree(lua, extractor_metrics(corner, reference, rows))
    assert lua["brake_initiation"]["spline_pos"] >= zone["start"]


def test_no_braking_in_the_zone_yields_no_evidence_on_both_sides(lua_metrics):
    zone = {"start": 0.30, "end": 0.45}
    corner, reference = plan_corner(braking_zone=zone, brake_ref_spline=0.40)
    # All the braking happens AFTER the zone closes, as a novice-late driver's
    # would; neither side may invent an event.
    rows = make_rows(80, 0.25, 0.005, brake=lambda i: 0.8 if i >= 60 else 0.0)
    lua = lua_metrics(corner, reference, rows)
    assert lua.get("brake_initiation_distance_m") is None
    assert_agree(lua, extractor_metrics(corner, reference, rows))


def test_a_corner_with_no_braking_zone_yields_no_braking_metric(lua_metrics):
    """A corner taken flat is not applicable to the braking-point element."""
    corner, reference = plan_corner()
    rows = make_rows(80, 0.25, 0.005, brake=lambda i: 0.9)
    lua = lua_metrics(corner, reference, rows)
    assert lua.get("brake_initiation_distance_m") is None
    assert lua.get("brake_initiation") is None


def test_braking_earlier_than_the_reference_is_a_positive_distance(lua_metrics):
    """passes.schema.json's sign convention: positive = EARLY.

    It matters which way this points: novice error runs early, and a sign flip
    would leave the accuracy gate symmetric but the logged distributions
    mirrored, which is the kind of bug that only shows up in the thesis figures.
    """
    zone = {"start": 0.30, "end": 0.60}
    corner, reference = plan_corner(braking_zone=zone, brake_ref_spline=0.50)
    rows = make_rows(90, 0.25, 0.005, brake=lambda i: 0.8 if i >= 20 else 0.0)
    lua = lua_metrics(corner, reference, rows)
    braked_at = rows[20]["spline"]
    assert braked_at < 0.50
    assert lua["brake_initiation_distance_m"] > 0
    assert lua["brake_initiation_distance_m"] == pytest.approx(
        (0.50 - braked_at) * TRACK_LENGTH_M, abs=1e-6)


def test_brake_modulation_is_recorded_but_never_gates(lua_metrics):
    zone = {"start": 0.30, "end": 0.60}
    corner, reference = plan_corner(braking_zone=zone, brake_ref_spline=0.50)

    def brake(i):
        if 20 <= i < 30 or 40 <= i < 50:
            return 0.75
        return 0.0

    rows = make_rows(90, 0.25, 0.005, brake=brake)
    mod = lua_metrics(corner, reference, rows)["brake_modulation"]
    assert mod["peak"] == pytest.approx(0.75)
    assert mod["releases"] == 2


# --- minimum corner speed ----------------------------------------------------

def test_minimum_corner_speed_agrees_and_respects_the_zone(lua_metrics):
    corner, reference = plan_corner(corner_speed_zone={"start": 0.40, "end": 0.60})
    # The slowest point of the pass sits OUTSIDE the zone and must be ignored.
    rows = make_rows(100, 0.25, 0.005, speed=lambda i: 40.0 if i < 10 else 70.0 + i)
    lua = lua_metrics(corner, reference, rows)
    assert lua["min_corner_speed_kmh"] > 40.0
    assert_agree(lua, extractor_metrics(corner, reference, rows))


# --- apex RMS ----------------------------------------------------------------

def test_a_pass_on_the_expert_line_has_near_zero_apex_rms(lua_metrics):
    grid = [0.48 + 0.005 * i for i in range(9)]
    corner, reference = plan_corner(apex_line=straight_line(grid))
    rows = make_rows(120, 0.40, 0.002)
    lua = lua_metrics(corner, reference, rows)
    assert lua["apex_rms_m"] == pytest.approx(0.0, abs=1e-6)
    assert_agree(lua, extractor_metrics(corner, reference, rows))


def test_a_constant_lateral_offset_reads_back_as_that_offset(lua_metrics):
    """RMS of a constant 2 m offset is 2 m — the metric's units are metres."""
    grid = [0.48 + 0.005 * i for i in range(9)]
    corner, reference = plan_corner(apex_line=straight_line(grid))
    rows = make_rows(120, 0.40, 0.002, lateral=lambda i: 2.0)
    lua = lua_metrics(corner, reference, rows)
    assert lua["apex_rms_m"] == pytest.approx(2.0, abs=1e-6)
    assert_agree(lua, extractor_metrics(corner, reference, rows))


def test_a_varying_line_agrees_with_the_extractor_to_the_metre(lua_metrics):
    grid = [0.48 + 0.0025 * i for i in range(17)]
    corner, reference = plan_corner(apex_line=straight_line(grid))
    rows = make_rows(200, 0.40, 0.0012, lateral=lambda i: 3.0 * math.sin(i / 7.0))
    lua = lua_metrics(corner, reference, rows)
    extractor = extractor_metrics(corner, reference, rows)
    assert lua["apex_rms_m"] > 0.5, "the synthetic line should actually deviate"
    assert_agree(lua, extractor)


def test_an_apex_window_the_pass_does_not_cover_yields_no_value(lua_metrics):
    """No partial unions: an uncovered window is no evidence, not a small RMS."""
    grid = [0.48 + 0.005 * i for i in range(9)]
    corner, reference = plan_corner(apex_line=straight_line(grid))
    # The pass stops before the window's far end.
    rows = make_rows(30, 0.45, 0.0015)
    assert rows[-1]["spline"] < grid[-1]
    lua = lua_metrics(corner, reference, rows)
    assert lua.get("apex_rms_m") is None
    assert_agree(lua, extractor_metrics(corner, reference, rows))


def test_a_compound_corner_yields_one_value_over_the_union(lua_metrics):
    """Two apex gates, one apex criterion per pass (framing v6)."""
    grid_a = [0.30 + 0.005 * i for i in range(9)]
    grid_b = [0.60 + 0.005 * i for i in range(9)]
    corner, reference = plan_corner(apex_line=straight_line(grid_a))
    reference["apex"]["gates"].append({
        "world_pos": [0, 0, 0], "spline_pos": 0.62, "line": straight_line(grid_b)})
    corner["zones"]["apex_gates"] = [0.32, 0.62]
    # 3 m off through the first window, on-line through the second: the union
    # RMS is sqrt((9*9 + 9*0)/18) = 3/sqrt(2).
    rows = make_rows(300, 0.25, 0.0015,
                     lateral=lambda i: 3.0 if i < 150 else 0.0)
    lua = lua_metrics(corner, reference, rows)
    assert lua["apex_rms_m"] == pytest.approx(3.0 / math.sqrt(2), abs=1e-3)
    assert_agree(lua, extractor_metrics(corner, reference, rows))


def test_a_compound_corner_with_one_uncovered_window_yields_nothing(lua_metrics):
    """The one deliberate divergence from the extractor, pinned so it stays deliberate.

    The extractor keeps a lap's covered gates and drops the uncovered one; the
    runtime refuses the whole corner. A partial union is not comparable with the
    reference's mean_rms_m, which was built over the whole union. Every corner
    in both study annotations has one apex gate, so on the study's own data the
    two never differ.
    """
    grid_a = [0.30 + 0.005 * i for i in range(9)]
    grid_b = [0.60 + 0.005 * i for i in range(9)]
    corner, reference = plan_corner(apex_line=straight_line(grid_a))
    reference["apex"]["gates"].append({
        "world_pos": [0, 0, 0], "spline_pos": 0.62, "line": straight_line(grid_b)})
    rows = make_rows(120, 0.25, 0.0015)   # covers window A, stops before B
    assert rows[-1]["spline"] < grid_b[0]
    assert lua_metrics(corner, reference, rows).get("apex_rms_m") is None


# --- start/finish wrap -------------------------------------------------------

def test_a_pass_straddling_start_finish_measures_correctly(lua_metrics):
    """The hazard pass_tracker was built around, at the metric level too."""
    grid = [(0.99 + 0.005 * i) % 1.0 for i in range(9)]
    corner, reference = plan_corner(
        braking_zone={"start": 0.95, "end": 0.99},
        corner_speed_zone={"start": 0.98, "end": 0.04},
        apex_line=[{"spline_pos": g,
                    "world_pos": [((0.99 + 0.005 * i) * TRACK_LENGTH_M), 0.0, 0.0]}
                   for i, g in enumerate(grid)],
        brake_ref_spline=0.97)
    rows = []
    for i in range(120):
        spline = (0.93 + i * 0.0012) % 1.0
        rows.append({
            "t": round(i * DT, 4),
            "spline": spline,
            # Unwrapped X, so the geometry is continuous across the line and the
            # apex arithmetic is not measuring a 2.6 km jump.
            "pos_x": (0.93 + i * 0.0012) * TRACK_LENGTH_M,
            "pos_y": 0.0, "pos_z": 1.0,
            "speed_kmh": 90.0 + i, "brake": 0.8 if i >= 30 else 0.0,
            "lap": 0, "gear": 3, "steer": 0.0, "throttle": 0.0,
            "wheels_outside": 0, "in_pit": False,
        })
    lua = lua_metrics(corner, reference, rows)
    assert lua["brake_initiation_distance_m"] is not None
    assert lua["apex_rms_m"] == pytest.approx(1.0, abs=1e-6)
    assert lua["min_corner_speed_kmh"] is not None
    assert_agree(lua, extractor_metrics(corner, reference, rows))


# --- frame-rate independence -------------------------------------------------

def test_metrics_are_stable_across_frame_rates(lua_metrics):
    """The runtime accumulates per FRAME, the reference was built at 20 Hz.

    A metric that moved with frame rate would make every band a function of the
    participant's hardware.
    """
    grid = [0.48 + 0.0025 * i for i in range(17)]
    corner, reference = plan_corner(
        braking_zone={"start": 0.42, "end": 0.50}, brake_ref_spline=0.46,
        apex_line=straight_line(grid))

    def build(samples_per_spline_unit):
        step = 1.0 / samples_per_spline_unit
        n = int(0.20 * samples_per_spline_unit)
        return make_rows(n, 0.40, step,
                         brake=lambda i: 0.8 if i * step >= 0.03 else 0.0,
                         lateral=lambda i: 2.5)

    coarse = lua_metrics(corner, reference, build(1000))    # ~20 Hz at speed
    fine = lua_metrics(corner, reference, build(6000))      # ~120 Hz
    assert coarse["apex_rms_m"] == pytest.approx(fine["apex_rms_m"], abs=1e-6)
    assert coarse["brake_initiation_distance_m"] == pytest.approx(
        fine["brake_initiation_distance_m"], abs=3.0), \
        "brake point should agree to within a few metres of track"
