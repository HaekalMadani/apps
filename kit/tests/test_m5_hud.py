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
    """Frames running up to a zone start from `metres_out` before it.

    The default starts FURTHER out than the readout's lookahead, deliberately:
    the readout is taken after the last frame, so these fixtures test what is
    shown on arrival, not when it first appeared. When the question is when it
    appears, assert on a single frame at a known distance instead.
    """
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
    """Corner 2's zone opens at 0.65; from 0.642 that is the one being approached.

    0.642 is 21 m out, inside the 1.5 s lookahead at this speed; corner 1's
    zone ended 890 m ago and is long gone.
    """
    r = hud([(0.642, 150.0)])
    assert r["corner_id"] == "2"
    assert r["target_kmh"] == pytest.approx(120.0)


def test_a_corner_further_out_than_the_lookahead_shows_nothing(hud):
    """The readout is a cue for the corner being arrived at, not a lap preview.

    It used to appear 300 m out, flat. Measured against the real National
    annotation that put it on screen for 76% of every lap -- which is not a cue,
    it is furniture: the participant stops reading a thing that is always there,
    and withdrawing it at `reduced` then changes the whole screen rather than one
    corner's worth of help.
    """
    # 260 m before corner 1's zone, at 150 km/h: 4.2 s away, far outside 1.5 s.
    assert hud([(0.20 - 0.1, 150.0)]) is None
    # 26 m before it, same speed: 0.6 s away, inside.
    assert hud([(0.20 - 0.01, 150.0)])["phase"] == "approach"


def test_the_lookahead_is_seconds_of_travel_not_metres_of_track(hud):
    """One spline position, two speeds, two answers.

    The same lesson the braking zones learned at M6: a flat metre budget buys
    1.1 s at Copse and 1.9 s at a slow corner, so one number means two different
    things at two corners of one lap. Here it is what decides whether the driver
    gets the target in time to act on it.
    """
    out = 0.20 - 0.02                      # 52 m before the zone
    assert hud([(out, 200.0)])["phase"] == "approach"   # 0.9 s away: shown
    assert hud([(out, 60.0)]) is None                   # 3.1 s away: not yet


def test_the_settled_window_scales_with_speed_too(hud):
    """A fast exit carries the driver further in the same reading time."""
    frames = through(0.20, 0.30, [110.0, 95.0, 86.0])
    far = 0.30 + 0.02                      # 52 m past the zone end
    assert hud(frames + [(far, 200.0)])["phase"] == "settled"
    assert hud(frames + [(far, 40.0)]) is None


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


def test_carrying_more_speed_than_the_target_reads_as_on_target(hud):
    """The criterion stopped faulting the fast side on 2026-10-14, so the colour
    on screen had to stop too -- otherwise the readout goes red on a pass the
    record says met the criterion, and the participant is trained against a
    target the system does not reward.

    `within_band` means "met the criterion" for this element, not "between two
    edges": there is no upper edge any more.
    """
    band = CFG["band_floors"]["corner_speed_kmh"]
    r = hud(through(0.20, 0.30, [90.0 + band * 2, 90.0 + band * 2]))
    assert r["within_band"] is True
    assert r["deviation_kmh"] > 0


def test_the_readout_follows_the_configured_gate_shape(hud):
    """Under `two_sided` the same pass reads as a miss, from the same config
    field the criterion reads."""
    band = CFG["band_floors"]["corner_speed_kmh"]
    cfg = json.loads(json.dumps(CFG))
    cfg["criteria"]["corner_speed_gate"] = "two_sided"
    r = hud(through(0.20, 0.30, [90.0 + band * 2, 90.0 + band * 2]), cfg=cfg)
    assert r["within_band"] is False


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


# --- screen layout -----------------------------------------------------------

@pytest.fixture(scope="module")
def layout():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval("""
        function(w, h)
          local json = require('lib/json')
          local hud = require('lib/hud')
          return json.encode(hud.layout(w, h))
        end
    """)
    return lambda w, h: json.loads(fn(w, h))


def test_the_readout_is_centred_horizontally(layout):
    for w in (1280.0, 1920.0, 3440.0):
        assert layout(w, 1080.0)["centre_x"] == pytest.approx(w / 2)


def test_every_size_scales_with_the_window_height(layout):
    """So the cue subtends the same angle at the same seating distance on any
    display -- it is a stimulus, and its apparent size is part of the apparatus.

    The box dimensions are in here too: a box that scaled differently from the
    number inside it would crop the number on some displays and not others.
    """
    small, big = layout(1280.0, 720.0), layout(2560.0, 1440.0)
    for key in ("top_y", "size_label", "size_speed", "size_target", "size_kr",
                "line_gap", "box_w", "box_h", "box_radius"):
        assert big[key] == pytest.approx(small[key] * 2.0), key


def test_the_live_speed_is_the_biggest_thing_on_screen(layout):
    """REVISED 2026-10-15, after the dry run.

    It was the TARGET that held the big size, and on track it took the attention
    the live number should have had. The driver needs to read what they are
    *doing*; the target is reference they glance at, and the box's fill colour
    already carries the comparison. So `size_speed` is now the largest and the
    target is a caption -- smaller than the KR message, which is a sentence that
    has to be read rather than a number to be glanced at.
    """
    lay = layout(1920.0, 1080.0)
    assert lay["size_speed"] > lay["size_kr"] > lay["size_target"]
    assert lay["size_target"] > lay["size_label"]


def test_the_number_fits_inside_its_box(layout):
    """The box is fixed-width on purpose -- a box sized to its contents changes
    width when the speed crosses 100 km/h, a twitch at exactly the moment the
    driver is reading it. Fixed width then has to be wide enough for the widest
    number it will ever hold, and tall enough for the glyphs.

    Three digits at `size_speed` is the worst case for this element (corner
    speeds on both layouts are well under 1000 km/h). DWrite advance widths are
    not available headlessly, so this bounds it generously: a digit in a
    semibold UI face is comfortably under 0.7 em wide.
    """
    for h in (240.0, 720.0, 1080.0, 1440.0, 2160.0):
        lay = layout(h * 16.0 / 9.0, h)
        assert lay["box_w"] > 3.0 * 0.7 * lay["size_speed"], h
        assert lay["box_h"] > lay["size_speed"], h


def test_the_block_grows_downward_from_a_fixed_top_of_the_upper_half(layout):
    """The KR message is drawn below the readout and the top never moves, so a
    message appearing cannot shift the speed number under the driver's eyes.

    Pinned as arithmetic because the alternative is only visible in game: a
    bottom-anchored layout looks identical until the moment a message lands.

    MOVED TO THE UPPER HALF 2026-10-15. Impl plan section 7 said centre-bottom,
    which put the one element a participant is meant to stare at into the strip
    of screen AC's own HUD already owns -- speedometer, gear, pedal bars. The
    dry run found it competing with them.
    """
    lay = layout(1920.0, 1080.0)
    # The box, the target caption, a corner label and a KR line, plus gaps,
    # still has to clear the bottom of the screen.
    stack = (lay["size_label"] + lay["box_h"] + lay["size_target"]
             + lay["size_kr"] + 4 * lay["line_gap"])
    assert lay["top_y"] + stack < 1080.0
    # ...and the whole block must stay in the UPPER half, clear of the native
    # instruments along the bottom.
    assert lay["top_y"] + stack < 540.0
    # ...without riding so high it leaves the screen or sits under AC's own
    # top-centre widgets.
    assert lay["top_y"] > 1080.0 * 0.10


def test_a_tiny_window_does_not_collapse_the_cue(layout):
    """AC can be run in a small window while setting up; the readout must stay
    legible rather than scaling to nothing."""
    lay = layout(320.0, 240.0)
    assert lay["size_speed"] >= 10.0
    assert lay["box_border"] >= 1.0
