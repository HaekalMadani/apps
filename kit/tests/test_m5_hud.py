"""M5: the corner-speed indicator's logic.

The third UI element, and the only one that is not world-anchored. Its hard
question is not "where" but "which corner, and what do I say about it right
now", and that decision is pure — ``lua/trace_rt/lib/hud.lua`` — so it can be
driven headless the same way the pass tracker is.

Two things these tests are really protecting:

* the readout and the criterion must never disagree about what "on target"
  means. Both come from the reference table through ``lib/evaluator``'s band
  arithmetic, and the last test here pins that they do.
* the running minimum must survive the cue being hidden. During a probe the
  participant sees nothing, but the corner-speed metric is still being measured
  — withdrawal removes the scaffold, never the measurement.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))
SALIENCE = CFG["salience"]
TRACK_LENGTH_M = 2600.0


def annotation_corners():
    return [
        {"id": "1", "type": "medium", "compound": False,
         "entry_gate": 0.10, "exit_gate": 0.35,
         "zones": {"apex_gates": [0.28], "apex_window_half_m": 20.0,
                   "corner_speed": {"start": 0.20, "end": 0.30}}},
        {"id": "2", "type": "fast", "compound": False,
         "entry_gate": 0.55, "exit_gate": 0.80,
         "zones": {"apex_gates": [0.72], "apex_window_half_m": 20.0,
                   "corner_speed": {"start": 0.65, "end": 0.75}}},
    ]


def reference(sigma_speed=0.3):
    def corner(cid, mean):
        return {
            "corner_id": cid, "source": "ai",
            "contributing_laps": {"clean_passes": 12, "apex": 12, "corner_speed": 12},
            "apex": {"gates": [{"world_pos": [0, 0, 0], "spline_pos": 0.5,
                                "line": [{"spline_pos": 0.49, "world_pos": [0, 0, 0]},
                                         {"spline_pos": 0.51, "world_pos": [1, 0, 0]}]}],
                     "mean_rms_m": 0.05, "sigma_ref_m": 0.01},
            "corner_speed": {"mean_kmh": mean, "sigma_ref_kmh": sigma_speed},
        }

    return {"schema_version": 1, "pair_id": "pair1", "track": "synthetic",
            "car": "synthetic_car", "track_length_m": TRACK_LENGTH_M,
            "corners": [corner("1", 90.0), corner("2", 120.0)]}


@pytest.fixture(scope="module")
def hud():
    """drive(frames, stage) -> the readout after replaying those frames.

    `frames` is a list of (spline, speed_kmh); the readout is taken after the
    last one, which is how the real runtime works — lib/hud accumulates every
    frame from draw3d and the window only renders the result.
    """
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval("""
        function(corners_json, ref_json, cfg_json, frames_json, stage, sal_json, track_length_m)
          local json = require('lib/json')
          local hud = require('lib/hud')
          local corners = json.decode(corners_json)
          local reference = json.decode(ref_json)
          local cfg = json.decode(cfg_json)
          local salience = json.decode(sal_json)
          local frames = json.decode(frames_json)
          local plans = hud.plans(corners, reference, cfg)
          local st = hud.new()
          local out = nil
          for i = 1, #frames do
            local spline, speed = frames[i][1], frames[i][2]
            hud.update(st, plans, spline, speed)
            out = hud.readout(plans, st, spline, speed, track_length_m, stage, salience)
          end
          if out == nil then return 'nil' end
          return json.encode(out)
        end
    """)

    def drive(frames, stage="full", salience=None, ref=None, cfg=None):
        raw = fn(json.dumps(annotation_corners()), json.dumps(ref or reference()),
                 json.dumps(cfg or CFG), json.dumps(frames), stage,
                 json.dumps(salience or SALIENCE), TRACK_LENGTH_M)
        return None if raw == "nil" else json.loads(raw)

    return drive


def approach_to(corner_start, speed=150.0, metres_out=100.0, steps=20):
    """Frames running up to a zone start from `metres_out` before it."""
    span = metres_out / TRACK_LENGTH_M
    return [(corner_start - span + span * i / steps, speed) for i in range(steps)]


def through(zone_start, zone_end, speeds):
    """Frames spread evenly across a zone, at the given speeds."""
    n = len(speeds)
    return [(zone_start + (zone_end - zone_start) * i / (n - 1), speeds[i])
            for i in range(n)]


# --- which corner ------------------------------------------------------------

def test_nothing_is_shown_when_no_corner_is_near(hud):
    """Between corners the readout is blank, not stale."""
    assert hud([(0.45, 150.0)]) is None


def test_the_upcoming_corner_appears_on_the_approach(hud):
    r = hud(approach_to(0.20))
    assert r is not None
    assert r["corner_id"] == "1"
    assert r["phase"] == "approach"
    assert r["target_kmh"] == pytest.approx(90.0)


def test_the_nearest_corner_wins_when_two_are_in_range(hud):
    """Corner 2's zone opens at 0.65; from 0.62 that is the one being approached."""
    r = hud([(0.62, 150.0)])
    assert r["corner_id"] == "2"
    assert r["target_kmh"] == pytest.approx(120.0)


def test_inside_a_zone_the_phase_switches(hud):
    r = hud(through(0.20, 0.30, [110.0, 95.0, 88.0]))
    assert r["phase"] == "in_zone"
    assert r["corner_id"] == "1"


# --- the running minimum -----------------------------------------------------

def test_the_readout_tracks_the_running_minimum_not_the_live_speed(hud):
    """The minimum is what the criterion is computed on, so it is what is shown."""
    r = hud(through(0.20, 0.30, [110.0, 95.0, 86.0, 92.0, 99.0]))
    assert r["phase"] == "in_zone"
    assert r["actual_kmh"] == pytest.approx(86.0)


def test_the_achieved_minimum_lingers_past_the_zone(hud):
    """Taking the number away at the exit gate would remove it exactly when it
    first means something."""
    frames = through(0.20, 0.30, [110.0, 95.0, 86.0]) + [(0.31, 120.0)]
    r = hud(frames)
    assert r["phase"] == "settled"
    assert r["corner_id"] == "1"
    assert r["actual_kmh"] == pytest.approx(86.0)


def test_the_minimum_resets_between_corners(hud):
    """Corner 2's readout must not inherit corner 1's minimum."""
    frames = through(0.20, 0.30, [110.0, 86.0]) + through(0.65, 0.75, [130.0, 118.0])
    r = hud(frames)
    assert r["corner_id"] == "2"
    assert r["actual_kmh"] == pytest.approx(118.0)


def test_the_minimum_is_still_tracked_while_the_cue_is_hidden(hud):
    """Withdrawal removes the scaffold, never the measurement.

    During a probe the participant sees nothing, but the corner-speed metric is
    still being taken — and the moment the element reverts, the readout must be
    correct rather than starting from blank.
    """
    frames = through(0.20, 0.30, [110.0, 95.0, 86.0])
    assert hud(frames, stage="probe") is None          # nothing drawn...
    # ...but the same frames replayed at full salience give the same minimum,
    # which is only possible because update() runs regardless of the stage.
    assert hud(frames, stage="full")["actual_kmh"] == pytest.approx(86.0)


# --- the verdict -------------------------------------------------------------

def test_a_minimum_inside_the_band_reads_as_within(hud):
    band = CFG["band_floors"]["corner_speed_kmh"]
    r = hud(through(0.20, 0.30, [110.0, 90.0 - band * 0.5]))
    assert r["within_band"] is True
    assert r["deviation_kmh"] == pytest.approx(-band * 0.5)


def test_a_minimum_outside_the_band_reads_as_outside(hud):
    band = CFG["band_floors"]["corner_speed_kmh"]
    r = hud(through(0.20, 0.30, [110.0, 90.0 - band * 2]))
    assert r["within_band"] is False


def test_too_fast_is_outside_the_band_too(hud):
    """The corner-speed criterion is two-sided; the readout must agree."""
    band = CFG["band_floors"]["corner_speed_kmh"]
    r = hud(through(0.20, 0.30, [90.0 + band * 2, 90.0 + band * 2]))
    assert r["within_band"] is False
    assert r["deviation_kmh"] > 0


def test_no_verdict_is_given_on_the_approach(hud):
    """The car is still slowing, so 'outside the band' would be the normal case.

    A red light on every approach would train the participant to ignore it.
    """
    r = hud(approach_to(0.20, speed=150.0))
    assert r["phase"] == "approach"
    assert r.get("within_band") is None
    assert r["actual_kmh"] == pytest.approx(150.0)


# --- salience ----------------------------------------------------------------

def test_the_cue_is_hidden_at_probe_and_removed(hud):
    for stage in ("probe", "removed", "hidden"):
        assert hud(through(0.20, 0.30, [110.0, 88.0]), stage=stage) is None


def test_full_salience_shows_the_label_and_the_achieved_speed(hud):
    r = hud(through(0.20, 0.30, [110.0, 88.0]), stage="full")
    assert r["alpha"] == pytest.approx(SALIENCE["full_alpha"])
    assert r["show_label"] is True and r["show_actual"] is True


def test_reduced_salience_keeps_only_the_target(hud):
    """The same reasoning as the markers' `minimal` form, applied to the readout.

    A dimmer copy of the whole thing still does the driver's comparing for them,
    and it is the comparing that has to be internalised.
    """
    r = hud(through(0.20, 0.30, [110.0, 88.0]), stage="reduced")
    assert r["alpha"] == pytest.approx(SALIENCE["reduced_alpha"])
    assert r["show_label"] is False and r["show_actual"] is False
    # The target itself is always there — it is the cue.
    assert r["target_kmh"] == pytest.approx(90.0)


def test_the_reduced_form_config_reaches_the_readout(hud):
    frames = through(0.20, 0.30, [110.0, 88.0])
    intermediate = hud(frames, stage="reduced",
                       salience=dict(SALIENCE, reduced_form="intermediate"))
    dimmed = hud(frames, stage="reduced", salience=dict(SALIENCE, reduced_form="dimmed"))
    assert intermediate["show_actual"] is True and intermediate["show_label"] is False
    assert dimmed["show_actual"] is True and dimmed["show_label"] is True


# --- the readout and the criterion agree -------------------------------------

def test_the_band_on_screen_is_the_band_the_criterion_uses(hud):
    """The claim the HUD's whole design rests on, asserted rather than asserted-to.

    If the readout said "on target" using a different band from the one
    lib/evaluator judges the pass on, the participant would be trained against a
    target the system does not reward — and the mismatch would be invisible in
    every log, because only one of the two numbers is ever written down.
    """
    from trace_kit import evaluator as pyev

    for sigma in (0.0, 0.3, 5.0):        # floor-dominated, and sigma-dominated
        ref = reference(sigma_speed=sigma)
        r = hud(through(0.20, 0.30, [110.0, 88.0]), ref=ref)
        expected = pyev.bands(CFG, ref["corners"][0])["corner_speed_kmh"]
        assert r["band_kmh"] == pytest.approx(expected), sigma


def test_the_verdict_matches_the_evaluators_criterion_exactly(hud):
    """Same inputs, same answer, on both sides of the band edge."""
    from trace_kit import evaluator as pyev

    ref = reference()
    band = pyev.bands(CFG, ref["corners"][0])["corner_speed_kmh"]
    for minimum in (90.0, 90.0 - band * 0.99, 90.0 - band * 1.01,
                    90.0 + band * 0.99, 90.0 + band * 1.01):
        r = hud(through(0.20, 0.30, [150.0, minimum]), ref=ref)
        criterion = pyev.evaluate(CFG, ref["corners"][0],
                                  {"min_corner_speed_kmh": minimum})["criteria"]["corner_speed"]
        assert r["within_band"] == criterion, minimum


def test_a_corner_missing_from_the_reference_gets_no_readout(hud):
    """No target to show, and inventing one would be worse than showing nothing."""
    ref = reference()
    ref["corners"] = [ref["corners"][1]]          # drop corner 1
    assert hud(through(0.20, 0.30, [110.0, 88.0]), ref=ref) is None
    # Corner 2 is unaffected.
    assert hud(through(0.65, 0.75, [130.0, 118.0]), ref=ref)["corner_id"] == "2"


def test_the_readout_uses_the_real_study_references():
    """The targets a participant will actually see, sanity-checked for plausibility."""
    for name in ("reference_pair1.json", "reference_pair2.json"):
        ref = json.loads(
            (REPO_ROOT / "configs" / "references" / name).read_text(encoding="utf-8"))
        for corner in ref["corners"]:
            target = corner["corner_speed"]["mean_kmh"]
            assert 50.0 < target < 250.0, "{} corner {}".format(name, corner["corner_id"])
