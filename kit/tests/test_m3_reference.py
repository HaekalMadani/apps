"""M3: reference extractor + AI-vs-human comparison (trace_kit/reference.py).

The extractor has no in-game half, so it is tested against synthetic reference
laps with known ground truth: a circular track of known length, a braking event
placed at a chosen spline, a chosen minimum corner speed, and a chosen lateral
line offset. A test that asserts on those known values catches the arithmetic
errors that would otherwise only surface as a subtly wrong marker position on
track -- the kind of thing Gate G0's visual review is a last line of defence
against, not a first.

One test here is a *parity* test rather than a unit test: the extractor's
forward_crossed must agree with lua/trace_rt/lib/pass_tracker.lua's, run for
real through lupa, because the reference is only meaningful if it describes the
same stretch of track the runtime evaluates. Same mechanism as the M0 validator
parity and the M4 golden traces.
"""

import json
import math
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import reference as ref
from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"

TRACK_LENGTH_M = 2500.0
SAMPLES_PER_LAP = 500          # 5 m apart -- coarser than the 1 m apex grid
LAP_TIME_S = 100.0
RADIUS_M = TRACK_LENGTH_M / (2.0 * math.pi)


# --- synthetic reference laps -----------------------------------------------

def world_pos(spline, lateral_m=0.0):
    """A point on a circular track of TRACK_LENGTH_M, offset radially."""
    angle = 2.0 * math.pi * spline
    r = RADIUS_M + lateral_m
    return (r * math.cos(angle), 0.0, r * math.sin(angle))


def synth_rows(n_laps, brake_splines, min_speeds, lateral_offsets,
               brake_zone=(0.20, 0.26), cs_zone=(0.26, 0.34), apex_spline=0.30,
               cruise_kmh=140.0):
    """Build a tick stream for `n_laps` laps with per-lap ground truth.

    brake_splines / min_speeds / lateral_offsets are one value per lap. Braking
    is held from that lap's brake spline to the end of the braking zone; speed
    dips to that lap's minimum exactly at the apex; the whole lap's line is
    offset laterally by that lap's offset.
    """
    rows = []
    t = 0.0
    dt = LAP_TIME_S / SAMPLES_PER_LAP
    for lap in range(n_laps):
        for i in range(SAMPLES_PER_LAP):
            spline = i / SAMPLES_PER_LAP
            braking = ref.in_zone(spline, brake_splines[lap], brake_zone[1])
            speed = cruise_kmh
            if ref.in_zone(spline, *cs_zone):
                # a V-shaped dip reaching min_speeds[lap] at the apex
                d = abs(ref.signed_delta(apex_spline, spline))
                half = ref.forward_span(*cs_zone) / 2.0
                speed = min_speeds[lap] + (cruise_kmh - min_speeds[lap]) * min(1.0, d / half)
            x, y, z = world_pos(spline, lateral_offsets[lap])
            rows.append({
                "t": t, "lap": lap, "spline": spline,
                "pos_x": x, "pos_y": y, "pos_z": z,
                "speed_kmh": speed, "brake": 0.8 if braking else 0.0,
                "throttle": 0.0 if braking else 1.0, "steer": 0.0,
                "gear": 4, "wheels_outside": 0, "in_pit": False,
            })
            t += dt
    return rows


def synth_annotation(brake_zone=(0.20, 0.26), cs_zone=(0.26, 0.34), apex_spline=0.30,
                     apex_half_m=20.0, corner_id="T1"):
    return {
        "schema_version": 1,
        "track": "synth_track",
        "corners": [{
            "id": corner_id, "type": "medium", "compound": False,
            "entry_gate": 0.15, "exit_gate": 0.40,
            "zones": {
                "braking": {"start": brake_zone[0], "end": brake_zone[1]},
                "apex_gates": [apex_spline],
                "apex_window_half_m": apex_half_m,
                "corner_speed": {"start": cs_zone[0], "end": cs_zone[1]},
            },
        }],
    }


# --- spline arithmetic ------------------------------------------------------

def test_in_zone_handles_wrap():
    assert ref.in_zone(0.98, 0.95, 0.05)
    assert ref.in_zone(0.02, 0.95, 0.05)
    assert not ref.in_zone(0.50, 0.95, 0.05)


def test_signed_delta_is_shortest_signed_path():
    assert ref.signed_delta(0.98, 0.02) == pytest.approx(0.04)
    assert ref.signed_delta(0.02, 0.98) == pytest.approx(-0.04)
    assert ref.signed_delta(0.10, 0.20) == pytest.approx(0.10)


# --- parity with the runtime pass tracker ------------------------------------

FORWARD_CROSSED_CASES = [
    (0.10, 0.20, 0.15),   # ordinary forward crossing
    (0.10, 0.20, 0.25),   # gate not reached
    (0.10, 0.20, 0.10),   # exclusive at prev
    (0.10, 0.20, 0.20),   # inclusive at cur
    (0.98, 0.02, 0.99),   # forward wrap, gate before the line
    (0.98, 0.02, 0.01),   # forward wrap, gate after the line
    (0.98, 0.02, 0.50),   # forward wrap, gate elsewhere
    (0.20, 0.19, 0.195),  # small reverse: no crossing
    (0.02, 0.98, 0.50),   # backward over the line: no forward crossing
]


@pytest.fixture(scope="module")
def lua_forward_crossed():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return lua.eval(
        """
        function(prev, cur, gate)
          local pass_tracker = require('lib/pass_tracker')
          return pass_tracker.forward_crossed(prev, cur, gate)
        end
        """
    )


@pytest.mark.parametrize("prev,cur,gate", FORWARD_CROSSED_CASES)
def test_forward_crossed_matches_lua_runtime(lua_forward_crossed, prev, cur, gate):
    assert ref.forward_crossed(prev, cur, gate) == bool(lua_forward_crossed(prev, cur, gate))


# --- per-lap metrics ---------------------------------------------------------

def test_brake_initiation_finds_first_sustained_application():
    rows = synth_rows(1, [0.22], [90.0], [0.0])
    passes = list(ref.corner_passes(rows, synth_annotation()["corners"][0]))
    hit = ref.brake_initiation(passes[0]["rows"], {"start": 0.20, "end": 0.26}, 0.1, 0.1)
    assert hit is not None
    # 5 m sample spacing, so the detected point is within one sample of truth.
    assert hit["spline"] == pytest.approx(0.22, abs=1.0 / SAMPLES_PER_LAP)


def test_brake_initiation_rejects_a_tap():
    """A one-sample brush of the pedal must not count as turn-in braking."""
    rows = synth_rows(1, [0.22], [90.0], [0.0])
    corner = synth_annotation()["corners"][0]
    # exactly ONE sample above threshold, early in the zone: released before the
    # debounce window elapses, so it is a tap and not an initiation
    tap = next(r for r in rows if r["spline"] >= 0.205)
    tap["brake"] = 0.8
    tapped = list(ref.corner_passes(rows, corner))[0]["rows"]
    hit = ref.brake_initiation(tapped, {"start": 0.20, "end": 0.26}, 0.1, 0.1)
    assert hit["spline"] == pytest.approx(0.22, abs=1.0 / SAMPLES_PER_LAP)


def test_brake_initiation_ignores_braking_outside_the_zone():
    rows = synth_rows(1, [0.22], [90.0], [0.0])
    corner = synth_annotation()["corners"][0]
    pass_rows = list(ref.corner_passes(rows, corner))[0]["rows"]
    # a zone that ends before the braking starts finds nothing
    assert ref.brake_initiation(pass_rows, {"start": 0.16, "end": 0.19}, 0.1, 0.1) is None


def test_min_corner_speed_is_the_dip():
    rows = synth_rows(1, [0.22], [88.0], [0.0])
    pass_rows = list(ref.corner_passes(rows, synth_annotation()["corners"][0]))[0]["rows"]
    assert ref.min_corner_speed(pass_rows, {"start": 0.26, "end": 0.34}) == pytest.approx(88.0, abs=1.0)


def test_apex_grid_spans_the_window_in_driving_order():
    grid = ref.apex_grid(0.30, 20.0, TRACK_LENGTH_M)
    assert len(grid) == 41
    assert grid[0] == pytest.approx(0.30 - 20.0 / TRACK_LENGTH_M)
    assert grid[-1] == pytest.approx(0.30 + 20.0 / TRACK_LENGTH_M)
    assert grid[20] == pytest.approx(0.30)


def test_apex_grid_wraps_at_start_finish():
    grid = ref.apex_grid(0.002, 20.0, TRACK_LENGTH_M)
    assert all(0.0 <= s <= 1.0 for s in grid)
    assert grid[0] > 0.9 and grid[-1] < 0.1     # window straddles the line


def test_rms_lateral_recovers_a_known_offset():
    """A line offset by a constant 0.75 m has an RMS deviation of 0.75 m."""
    grid = ref.apex_grid(0.30, 20.0, TRACK_LENGTH_M)
    inner = [world_pos(s, 0.0) for s in grid]
    outer = [world_pos(s, 0.75) for s in grid]
    assert ref.rms_lateral(outer, inner) == pytest.approx(0.75, abs=0.01)


def test_sample_line_returns_none_when_the_window_is_not_covered():
    rows = synth_rows(1, [0.22], [90.0], [0.0])
    pass_rows = list(ref.corner_passes(rows, synth_annotation()["corners"][0]))[0]["rows"]
    grid = ref.apex_grid(0.80, 20.0, TRACK_LENGTH_M)     # nowhere near this pass
    assert ref.sample_line(pass_rows, grid, 0.80) is None


# --- pass segmentation -------------------------------------------------------

def test_one_pass_per_lap_and_partial_passes_dropped():
    rows = synth_rows(4, [0.22] * 4, [90.0] * 4, [0.0] * 4)
    corner = synth_annotation()["corners"][0]
    assert len(list(ref.corner_passes(rows, corner))) == 4
    # start recording mid-corner: that lap's pass is incomplete and not yielded
    trimmed = [r for r in rows if not (r["lap"] == 0 and r["spline"] < 0.20)]
    assert len(list(ref.corner_passes(trimmed, corner))) == 3


def test_pass_with_wheels_off_is_not_clean():
    rows = synth_rows(1, [0.22], [90.0], [0.0])
    for row in rows:
        if 0.28 < row["spline"] < 0.29:
            row["wheels_outside"] = 3
    pass_rows = list(ref.corner_passes(rows, synth_annotation()["corners"][0]))[0]["rows"]
    assert not ref.pass_is_clean(pass_rows)


def test_lap_times_exclude_both_partial_laps():
    """Recording starts mid-lap and stops mid-lap, so the first and last lap
    groups are fragments, not laps."""
    rows = synth_rows(4, [0.22] * 4, [90.0] * 4, [0.0] * 4)
    times = ref.lap_times(rows)
    assert list(times) == [1, 2]        # lap 0's start and lap 3's end are outside
    assert all(v == pytest.approx(LAP_TIME_S) for v in times.values())


def test_a_mid_lap_start_does_not_wreck_the_cov():
    """Regression: the first real reference block began 0.05 s before the line,
    and counting that fragment as a lap reported a 31% CoV on laps that were
    actually within one tick of each other -- failing Gate G0 on a bug."""
    rows = synth_rows(5, [0.22] * 5, [90.0] * 5, [0.0] * 5)
    # drop all but the last sample of lap 0, as a real mid-lap start would
    rows = [r for r in rows if r["lap"] > 0 or r["spline"] >= 0.998]
    _, problems, report = ref.extract([rows], synth_annotation(), "pair", "car",
                                      TRACK_LENGTH_M, "ai", 0.1, 0.1)
    assert report["lap_time_cov"] == pytest.approx(0.0, abs=1e-9)
    assert not any("Gate G0" in p for p in problems)


# --- extraction end to end ---------------------------------------------------

def extract_synth(n_laps=12, brake_splines=None, min_speeds=None, lateral_offsets=None,
                  annotation=None, source="ai"):
    brake_splines = brake_splines or [0.22] * n_laps
    min_speeds = min_speeds or [90.0] * n_laps
    lateral_offsets = lateral_offsets or [0.0] * n_laps
    annotation = annotation or synth_annotation()
    rows = synth_rows(n_laps, brake_splines, min_speeds, lateral_offsets)
    return ref.extract([rows], annotation, "pair_synth", "synth_car", TRACK_LENGTH_M,
                       source, 0.1, 0.1)


def test_extracted_table_validates_against_the_schema():
    doc, problems, report = extract_synth()
    assert pyval.validate_data("reference", doc) == []
    assert [p for p in problems if "CoV" not in p] == []
    assert report["lap_time_cov"] == pytest.approx(0.0, abs=1e-9)


def test_extracted_brake_point_matches_ground_truth():
    doc, _, _ = extract_synth(brake_splines=[0.22] * 12)
    braking = doc["corners"][0]["braking"]
    assert braking["spline_pos"] == pytest.approx(0.22, abs=1.0 / SAMPLES_PER_LAP)
    # the marker coordinate must sit on the track, not at some averaged nowhere
    x, _, z = braking["world_pos"]
    assert math.hypot(x, z) == pytest.approx(RADIUS_M, abs=1.0)


def test_brake_point_sigma_is_metres_along_the_track():
    """Laps braking 10 m apart must give a sigma in metres, not spline units."""
    step = 10.0 / TRACK_LENGTH_M
    splines = [0.22 - step, 0.22, 0.22 + step] * 4
    doc, _, _ = extract_synth(brake_splines=splines)
    sigma = doc["corners"][0]["braking"]["sigma_ref_m"]
    # sample stdev of (-10, 0, +10) repeated is ~8.5 m; the 5 m sampling grid
    # quantises it, so assert the order of magnitude rather than the exact value
    assert 5.0 < sigma < 12.0


def test_identical_laps_give_zero_sigma_and_still_validate():
    """The AC AI really is this repeatable; the band FLOORS absorb it, not a
    schema bound, so a zero sigma must round-trip rather than fail."""
    doc, _, _ = extract_synth()
    assert doc["corners"][0]["corner_speed"]["sigma_ref_kmh"] == pytest.approx(0.0)
    assert pyval.validate_data("reference", doc) == []


def test_corner_speed_envelope_matches_ground_truth():
    doc, _, _ = extract_synth(min_speeds=[88.0, 90.0, 92.0] * 4)
    speed = doc["corners"][0]["corner_speed"]
    assert speed["mean_kmh"] == pytest.approx(90.0, abs=1.0)
    assert speed["sigma_ref_kmh"] == pytest.approx(1.65, abs=0.4)


def test_apex_line_is_a_sampled_line_not_a_point():
    doc, _, _ = extract_synth()
    gate = doc["corners"][0]["apex"]["gates"][0]
    assert len(gate["line"]) == 41
    assert all(len(s["world_pos"]) == 3 for s in gate["line"])
    # every sample sits on the synthetic track circle
    for s in gate["line"]:
        x, _, z = s["world_pos"]
        assert math.hypot(x, z) == pytest.approx(RADIUS_M, abs=0.5)


def test_apex_rms_recovers_the_spread_of_the_lines():
    """Laps offset +/-1 m from centre must show ~1 m mean RMS about the mean line."""
    doc, _, _ = extract_synth(lateral_offsets=[-1.0, 1.0] * 6)
    apex = doc["corners"][0]["apex"]
    assert apex["mean_rms_m"] == pytest.approx(1.0, abs=0.1)
    assert apex["sigma_ref_m"] == pytest.approx(0.0, abs=0.05)


def test_corner_without_braking_zone_gets_no_braking_reference():
    annotation = synth_annotation()
    del annotation["corners"][0]["zones"]["braking"]
    doc, problems, report = extract_synth(annotation=annotation)
    assert "braking" not in doc["corners"][0]
    assert pyval.validate_data("reference", doc) == []
    assert report["corners"][0]["braking_laps"] is None      # not applicable, not zero
    assert not any("brake" in p for p in problems)


def test_too_few_laps_is_reported():
    _, problems, _ = extract_synth(n_laps=4)
    assert any("need >= {}".format(ref.MIN_LAPS_PER_CORNER) in p for p in problems)


def test_inconsistent_lap_times_fail_the_g0_cov_bar():
    rows = synth_rows(6, [0.22] * 6, [90.0] * 6, [0.0] * 6)
    for row in rows:                       # stretch laps 3+ by 5%
        if row["lap"] >= 3:
            row["t"] += LAP_TIME_S * 0.05 * (row["lap"] - 2)
    _, problems, report = ref.extract([rows], synth_annotation(), "pair_synth", "synth_car",
                                      TRACK_LENGTH_M, "ai", 0.1, 0.1)
    assert report["lap_time_cov"] > ref.G0_MAX_LAP_TIME_COV
    assert any("Gate G0" in p for p in problems)


def test_compound_corner_yields_one_apex_value_over_both_windows():
    annotation = synth_annotation()
    annotation["corners"][0]["compound"] = True
    annotation["corners"][0]["zones"]["apex_gates"] = [0.29, 0.31]
    doc, _, _ = extract_synth(annotation=annotation, lateral_offsets=[-1.0, 1.0] * 6)
    apex = doc["corners"][0]["apex"]
    assert len(apex["gates"]) == 2                 # two markers to draw...
    assert isinstance(apex["mean_rms_m"], float)   # ...but one value per pass
    assert apex["mean_rms_m"] == pytest.approx(1.0, abs=0.1)


# --- AI vs human comparison (Gate G0) ----------------------------------------

FLOORS = {"braking_m": 5.0, "corner_speed_kmh": 3.0, "apex_m": 0.5}


def test_agreeing_references_are_not_substituted():
    ai, _, _ = extract_synth(source="ai")
    human, _, _ = extract_synth(source="human")
    rows, problems = ref.compare(ai, human, 3.0, FLOORS)
    assert problems == []
    assert not rows[0]["material"]
    _, substituted = ref.substitute(ai, human, rows)
    assert substituted == []


def test_human_braking_outside_the_ai_band_triggers_substitution():
    """The AI brakes conservatively; a human braking 40 m later falls outside
    the band the AI reference would impose, so that corner takes the human."""
    ai, _, _ = extract_synth(source="ai")
    later = 0.22 + 40.0 / TRACK_LENGTH_M
    human, _, _ = extract_synth(brake_splines=[later] * 12, source="human")
    rows, _ = ref.compare(ai, human, 3.0, FLOORS)
    assert rows[0]["elements"]["braking"]["material"]
    assert rows[0]["elements"]["braking"]["delta"] == pytest.approx(40.0, abs=6.0)
    assert rows[0]["material"]

    doc, substituted = ref.substitute(ai, human, rows)
    assert substituted == ["T1"]
    # the swap must carry the source through: it is what selects EVM_human
    assert doc["corners"][0]["source"] == "human"
    assert pyval.validate_data("reference", doc) == []


def test_divergent_corner_speed_alone_substitutes_the_whole_corner():
    ai, _, _ = extract_synth(source="ai")
    human, _, _ = extract_synth(min_speeds=[110.0] * 12, source="human")
    rows, _ = ref.compare(ai, human, 3.0, FLOORS)
    assert rows[0]["elements"]["corner_speed"]["material"]
    assert not rows[0]["elements"]["braking"]["material"]
    assert rows[0]["material"], "any element diverging substitutes the whole corner"


def test_compare_reports_a_pair_mismatch():
    ai, _, _ = extract_synth(source="ai")
    human, _, _ = extract_synth(source="human")
    human["car"] = "a_different_car"
    _, problems = ref.compare(ai, human, 3.0, FLOORS)
    assert any("car differs" in p for p in problems)


def test_band_uses_the_floor_when_sigma_is_tiny():
    assert ref.band(0.0, 3.0, 5.0) == 5.0
    assert ref.band(4.0, 3.0, 5.0) == 12.0


# --- the real study configs still parse through the extractor's expectations --

@pytest.mark.parametrize("name", [
    "annotation_ks_silverstone-national.json",
    "annotation_ks_silverstone-international.json",
])
def test_study_annotations_carry_an_apex_window(name):
    path = REPO_ROOT / "configs" / "annotations" / name
    annotation = json.loads(path.read_text(encoding="utf-8"))
    for corner in annotation["corners"]:
        half = corner["zones"]["apex_window_half_m"]
        assert half > 0
        # the window must not swallow the corner's own pass bracket
        bracket_m = ref.forward_span(corner["entry_gate"], corner["exit_gate"]) * 2597.0
        assert 2 * half < bracket_m, "corner {}: apex window wider than the pass".format(corner["id"])


def test_substituted_table_records_both_provenances():
    """The file the runtime loads must credit the human laps for the corners
    that came from them, not attribute everything to the AI."""
    ai, _, _ = ref.extract([synth_rows(12, [0.22] * 12, [90.0] * 12, [0.0] * 12)],
                           synth_annotation(), "pair1", "car", TRACK_LENGTH_M, "ai", 0.1, 0.1,
                           source_laps={"ai_laps": 12, "ai_strength_pct": 98,
                                        "setup": "default (car ships)"})
    later = 0.22 + 40.0 / TRACK_LENGTH_M
    human, _, _ = ref.extract([synth_rows(12, [later] * 12, [90.0] * 12, [0.0] * 12)],
                              synth_annotation(), "pair1", "car", TRACK_LENGTH_M, "human",
                              0.1, 0.1,
                              source_laps={"human_laps": 12,
                                           "human_driver": "researcher (not a study participant)",
                                           "setup": "default (car ships)"})
    rows, _ = ref.compare(ai, human, 3.0, FLOORS)
    doc, substituted = ref.substitute(ai, human, rows)
    assert substituted == ["T1"]
    assert doc["source_laps"]["ai_laps"] == 12
    assert doc["source_laps"]["human_laps"] == 12
    assert "researcher" in doc["source_laps"]["human_driver"]
    assert pyval.validate_data("reference", doc) == []


# --- Gate G0 auditability: the table carries its own provenance ---------------

def test_contributing_lap_counts_are_persisted_in_the_table():
    """G0 requires every corner to meet the minimum contributing-lap count.
    The counts must live in the committed table, not only in the console output
    of the run that produced it — otherwise the gate cannot be re-checked."""
    doc, _, report = extract_synth(n_laps=12)
    counts = doc["corners"][0]["contributing_laps"]
    assert counts["clean_passes"] == report["corners"][0]["passes"]
    assert counts["braking"] == report["corners"][0]["braking_laps"]
    assert counts["apex"] == report["corners"][0]["apex_laps"]
    assert counts["corner_speed"] == report["corners"][0]["corner_speed_laps"]
    assert all(v >= ref.MIN_LAPS_PER_CORNER for v in counts.values())


def test_flat_corner_omits_the_braking_lap_count():
    """Absent, not zero: a corner taken flat is outside the braking element's
    denominator, and a 0 would read as 'detected on no lap' — a failure."""
    annotation = synth_annotation()
    del annotation["corners"][0]["zones"]["braking"]
    doc, _, _ = extract_synth(annotation=annotation)
    assert "braking" not in doc["corners"][0]["contributing_laps"]
    assert pyval.validate_data("reference", doc) == []


def test_lap_time_cov_is_persisted_as_percent():
    doc, _, report = extract_synth(min_speeds=[88.0, 90.0, 92.0] * 4)
    assert doc["source_laps"]["lap_time_cov_pct"] == pytest.approx(
        report["lap_time_cov"] * 100.0, abs=1e-4)


def test_committed_reference_tables_meet_gate_g0_countable_clauses():
    """G0's two numeric clauses, checked against the files the game loads.

    Lap-time CoV < 1% and every corner meeting the minimum contributing-lap
    count were read off the extractor's console when each pair was recorded.
    Persisting them makes the gate re-checkable, and this test is what does the
    re-checking — so a hand-edit or a re-extraction cannot quietly drop a pair
    below the bar. The two visual clauses (gates and markers seen on track)
    cannot be automated and are signed off in configs/references/G0_REVIEW.md.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2] / "configs"
    tables = sorted((root / "references").glob("reference_pair*.json"))
    assert tables, "no committed reference tables found"

    annotations = {}
    for path in sorted((root / "annotations").glob("annotation_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        annotations[doc["track"]] = doc

    for path in tables:
        doc = json.loads(path.read_text(encoding="utf-8"))
        name = path.name
        assert pyval.validate_data("reference", doc) == [], name

        cov = doc["source_laps"]["lap_time_cov_pct"]
        assert cov < ref.G0_MAX_LAP_TIME_COV * 100.0, "{}: lap-time CoV {}%".format(name, cov)

        # Corner ids must agree with the annotation the runtime pairs it with,
        # and a corner annotated WITH a braking zone must have a braking
        # reference -- a silently dropped corner is the failure mode that costs
        # the braking element its quorum denominator.
        annotation = annotations[doc["track"]]
        by_id = {c["corner_id"]: c for c in doc["corners"]}
        assert set(by_id) == {c["id"] for c in annotation["corners"]}, name
        for corner in annotation["corners"]:
            entry = by_id[corner["id"]]
            has_zone = "braking" in corner["zones"]
            assert ("braking" in entry) == has_zone, "{}: corner {}".format(name, corner["id"])
            counts = entry["contributing_laps"]
            assert ("braking" in counts) == has_zone, "{}: corner {}".format(name, corner["id"])
            for element, n in counts.items():
                if element == "clean_passes":
                    continue
                assert n >= ref.MIN_LAPS_PER_CORNER, "{}: corner {} {} built from {} lap(s)".format(
                    name, corner["id"], element, n)
