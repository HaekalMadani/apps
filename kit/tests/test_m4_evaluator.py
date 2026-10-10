"""M4: the per-pass evaluator — metrics in, criterion booleans out.

Like the controller, the evaluator exists twice (``lib/evaluator.lua`` for the
runtime, ``trace_kit.evaluator`` for the Phase 1 simulator) and a divergence
would mean the simulation tunes thresholds against different arithmetic than
participants are judged by. Every case below is run through BOTH.

What is checked, beyond agreement: that the bands are built the way framing v6
says (floored, source-dependent), that the braking criterion really is
two-gate — the "consistent but 30 m early" learner must FAIL — and that an
unmeasurable metric comes back as null rather than as a failure.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import evaluator as pyev

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))

FLOORS = CFG["band_floors"]
EVM_AI = CFG["evm"]["ai"]
DELTA_RATIO = CFG["criteria"]["consistency_delta_ratio"]


def corner_ref(source="ai", sigma_brake=0.5, sigma_speed=0.3, sigma_apex=0.01,
               mean_speed=90.0, mean_rms=0.05, braking=True):
    doc = {
        "corner_id": "1",
        "source": source,
        "contributing_laps": {"clean_passes": 12, "apex": 12, "corner_speed": 12},
        "apex": {"gates": [{"world_pos": [0, 0, 0], "spline_pos": 0.5,
                            "line": [{"spline_pos": 0.49, "world_pos": [0, 0, 0]},
                                     {"spline_pos": 0.51, "world_pos": [1, 0, 0]}]}],
                 "mean_rms_m": mean_rms, "sigma_ref_m": sigma_apex},
        "corner_speed": {"mean_kmh": mean_speed, "sigma_ref_kmh": sigma_speed},
    }
    if braking:
        doc["braking"] = {"world_pos": [0, 0, 0], "spline_pos": 0.4,
                          "sigma_ref_m": sigma_brake}
        doc["contributing_laps"]["braking"] = 12
    return doc


@pytest.fixture(scope="module")
def lua_eval():
    """run(corner_ref, metrics, history) -> the runtime evaluator's result."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval(
        """
        function(cfg_json, ref_json, metrics_json, history_json)
          local json = require('lib/json')
          local ev = require('lib/evaluator')
          local metrics = json.decode(metrics_json)
          -- json.decode gives json.null for JSON nulls; the evaluator's contract
          -- is Lua nil for "not measurable".
          local m = {}
          for _, k in ipairs({'brake_initiation_distance_m', 'min_corner_speed_kmh', 'apex_rms_m'}) do
            if type(metrics[k]) == 'number' then m[k] = metrics[k] end
          end
          local r = ev.evaluate(json.decode(cfg_json), json.decode(ref_json), m,
                                json.decode(history_json))
          -- Normalise for comparison: Lua drops nil fields from tables, so send
          -- an explicit presence map alongside the values.
          return json.encode({
            braking = r.criteria.braking, corner_speed = r.criteria.corner_speed,
            apex = r.criteria.apex,
            has = { braking = r.criteria.braking ~= nil,
                    corner_speed = r.criteria.corner_speed ~= nil,
                    apex = r.criteria.apex ~= nil },
            accuracy = r.braking_gates.accuracy, consistency = r.braking_gates.consistency,
            bands = r.bands, rolling_mean_m = r.rolling_mean_m,
            speed_dev = r.speed_envelope_deviation_kmh,
          })
        end
        """
    )

    def run(ref, metrics, history=None):
        out = json.loads(fn(json.dumps(CFG), json.dumps(ref), json.dumps(metrics),
                            json.dumps(history or [])))
        for k in ("braking", "corner_speed", "apex"):
            if not out["has"][k]:
                out[k] = None
        del out["has"]
        # json.encode drops nil-valued keys, so absent means "not evaluated".
        for k in ("accuracy", "consistency", "rolling_mean_m", "speed_dev"):
            out.setdefault(k, None)
        out["bands"].setdefault("braking_m", None)
        return out

    return run


def both(lua_eval, ref, metrics, history=None):
    """Run a case through both implementations, assert agreement, return the result."""
    lua = lua_eval(ref, metrics, history)
    py = pyev.evaluate(CFG, ref, metrics, list(history or []))
    assert lua["braking"] == py["criteria"]["braking"]
    assert lua["corner_speed"] == py["criteria"]["corner_speed"]
    assert lua["apex"] == py["criteria"]["apex"]
    assert lua["accuracy"] == py["braking_gates"]["accuracy"]
    assert lua["consistency"] == py["braking_gates"]["consistency"]
    for key, value in py["bands"].items():
        assert lua["bands"][key] == pytest.approx(value)
    return lua


# --- bands -------------------------------------------------------------------

def test_bands_are_floored_when_the_reference_is_repeatable(lua_eval):
    """The measured M3 case: the AI's sigma sits far under every floor.

    'The floors set every band' is the finding that makes floor calibration the
    load-bearing part of Gate G2, so it is asserted here rather than assumed.
    """
    ref = corner_ref(sigma_brake=0.005, sigma_speed=0.2, sigma_apex=0.005)
    bands = both(lua_eval, ref, {"brake_initiation_distance_m": 0.0})["bands"]
    assert bands["braking_m"] == pytest.approx(FLOORS["braking_m"])
    assert bands["corner_speed_kmh"] == pytest.approx(FLOORS["corner_speed_kmh"])
    assert bands["apex_m"] == pytest.approx(FLOORS["apex_m"])


def test_a_large_reference_sigma_lifts_the_band_above_the_floor(lua_eval):
    ref = corner_ref(sigma_brake=10.0)
    bands = both(lua_eval, ref, {"brake_initiation_distance_m": 0.0})["bands"]
    assert bands["braking_m"] == pytest.approx(10.0 * EVM_AI)


def test_the_evm_is_chosen_per_corner_by_its_own_source(lua_eval):
    """A human-substituted corner's sigma already contains motor noise."""
    ai = both(lua_eval, corner_ref(source="ai", sigma_brake=10.0), {})["bands"]
    human = both(lua_eval, corner_ref(source="human", sigma_brake=10.0), {})["bands"]
    assert ai["braking_m"] == pytest.approx(10.0 * CFG["evm"]["ai"])
    assert human["braking_m"] == pytest.approx(10.0 * CFG["evm"]["human"])
    assert human["braking_m"] < ai["braking_m"], "EVM_human must not double-count motor noise"


def test_a_zero_reference_sigma_is_legal_and_absorbed_by_the_floor(lua_eval):
    """sigma_ref = 0 is expected at some corners; the band must still be usable."""
    ref = corner_ref(sigma_brake=0.0, sigma_speed=0.0, sigma_apex=0.0)
    result = both(lua_eval, ref, {"brake_initiation_distance_m": FLOORS["braking_m"] * 0.9})
    assert result["bands"]["braking_m"] == pytest.approx(FLOORS["braking_m"])
    assert result["braking"] is True


# --- braking: two gates ------------------------------------------------------

def test_the_first_pass_at_a_corner_is_judged_on_accuracy_alone(lua_eval):
    ref = corner_ref(sigma_brake=0.005)
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 1.0}, history=[])
    assert result["consistency"] is True and result["accuracy"] is True
    assert result["braking"] is True


def test_accurate_but_erratic_fails_the_consistency_gate(lua_eval):
    """Inside the band, but a long way from the driver's own rolling mean."""
    ref = corner_ref(sigma_brake=0.005)          # band = 5 m floor, delta = 2.5 m
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 4.5},
                  history=[-4.0, -4.5, -4.2])
    assert result["accuracy"] is True
    assert result["consistency"] is False
    assert result["braking"] is False


def test_consistently_thirty_metres_early_fails_the_accuracy_gate(lua_eval):
    """Framing v6's motivating case, stated as a test.

    'A learner who brakes reliably 30 m too early sits tight to their own
    rolling mean (passing consistency) but outside the accuracy band, so the
    marker stays.' Consistency alone is insufficient BY DESIGN, and this is what
    makes the trigger track the correct braking point rather than repeatability.
    """
    ref = corner_ref(sigma_brake=0.005)
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 30.0},
                  history=[30.2, 29.8, 30.1])
    assert result["consistency"] is True, "the learner IS consistent"
    assert result["accuracy"] is False, "...but 30 m early is outside the band"
    assert result["braking"] is False, "so the braking criterion must not be met"


def test_both_gates_met_passes(lua_eval):
    ref = corner_ref(sigma_brake=0.005)
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 1.0},
                  history=[0.8, 1.2, 0.9])
    assert result["braking"] is True


def test_the_consistency_delta_scales_with_the_corner_band(lua_eval):
    ref = corner_ref(sigma_brake=20.0)           # band = 60 m, delta = 30 m
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 25.0}, history=[0.0])
    assert result["bands"]["braking_m"] == pytest.approx(20.0 * EVM_AI)
    assert result["consistency"] is True, "25 m from the mean is inside a 30 m delta"
    assert result["rolling_mean_m"] == pytest.approx(0.0)


def test_the_rolling_mean_excludes_the_pass_being_judged(lua_eval):
    """Including it would partly measure the pass against itself."""
    ref = corner_ref(sigma_brake=0.005)
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 3.0},
                  history=[0.0, 0.0, 0.0])
    assert result["rolling_mean_m"] == pytest.approx(0.0)


def test_history_keeps_only_the_window_minus_one(lua_eval):
    """The consistency datum is 'the same passes that form the qualification window'."""
    window = CFG["qualification"]["window_passes"]
    history = []
    for value in range(10):
        pyev.push_history(history, float(value), window)
    assert len(history) == window - 1
    assert history == [7.0, 8.0, 9.0]


# --- corner speed and apex ---------------------------------------------------

def test_corner_speed_is_two_sided(lua_eval):
    """Too fast is an error too: the car runs wide.

    Written against the CONFIGURED floor rather than a literal, because Gate G1
    moved it (3.0 -> 4.0 km/h) and Gate G2 may move it again.
    """
    band = FLOORS["corner_speed_kmh"]
    ref = corner_ref(sigma_speed=0.0, mean_speed=90.0)
    for inside in (90.0 - band * 0.9, 90.0, 90.0 + band * 0.9):
        assert both(lua_eval, ref, {"min_corner_speed_kmh": inside})["corner_speed"] is True
    for outside in (90.0 - band * 1.1, 90.0 + band * 1.1):
        assert both(lua_eval, ref, {"min_corner_speed_kmh": outside})["corner_speed"] is False


def test_the_speed_deviation_is_signed_and_logged(lua_eval):
    ref = corner_ref(mean_speed=90.0)
    assert both(lua_eval, ref, {"min_corner_speed_kmh": 85.0})["speed_dev"] == pytest.approx(-5.0)
    assert both(lua_eval, ref, {"min_corner_speed_kmh": 95.0})["speed_dev"] == pytest.approx(5.0)


def test_apex_is_one_sided_against_the_reference_mean_rms(lua_eval):
    """Driving closer to the expert line than the AI managed is not an error."""
    ref = corner_ref(sigma_apex=0.0, mean_rms=0.05)       # band = 0.5 m floor
    assert both(lua_eval, ref, {"apex_rms_m": 0.0})["apex"] is True
    assert both(lua_eval, ref, {"apex_rms_m": 0.54})["apex"] is True
    assert both(lua_eval, ref, {"apex_rms_m": 0.56})["apex"] is False


# --- nulls -------------------------------------------------------------------

def test_an_unmeasurable_metric_is_null_not_a_failure(lua_eval):
    """The controller must be able to tell 'no evidence' from 'failed'."""
    ref = corner_ref()
    result = both(lua_eval, ref, {})
    assert result["braking"] is None
    assert result["corner_speed"] is None
    assert result["apex"] is None
    assert result["accuracy"] is None and result["consistency"] is None


def test_a_corner_without_a_braking_reference_never_yields_a_braking_criterion(lua_eval):
    """Not applicable is not the same as failing: it is out of the quorum entirely."""
    ref = corner_ref(braking=False)
    result = both(lua_eval, ref, {"brake_initiation_distance_m": 0.0,
                                  "min_corner_speed_kmh": 90.0, "apex_rms_m": 0.0})
    assert result["braking"] is None
    assert result["bands"]["braking_m"] is None, "no braking reference, so no braking band"
    assert pyev.bands(CFG, ref).get("braking_m") is None
    assert result["corner_speed"] is True and result["apex"] is True


# --- applicable sets ---------------------------------------------------------

def test_applicable_sets_exclude_flat_corners_from_the_braking_element_only():
    reference = {"corners": [corner_ref(), dict(corner_ref(braking=False), corner_id="2")]}
    applicable = pyev.applicable(reference)
    assert applicable["braking"] == ["1"]
    assert applicable["corner_speed"] == ["1", "2"]
    assert applicable["apex"] == ["1", "2"]


def test_applicable_sets_match_the_committed_study_references():
    """The real tables: National has 4 corners all with braking, International 5."""
    for name, corners in (("reference_pair1.json", 4), ("reference_pair2.json", 5)):
        path = REPO_ROOT / "configs" / "references" / name
        reference = json.loads(path.read_text(encoding="utf-8"))
        applicable = pyev.applicable(reference)
        assert len(applicable["corner_speed"]) == corners
        assert len(applicable["apex"]) == corners
        # Every study corner has a braking zone, so no element is disabled and
        # the braking quorum denominator is the full corner count (the M3 fix
        # that lifted National's from 2 to 4).
        assert len(applicable["braking"]) == corners


def test_lua_and_python_agree_on_the_committed_study_references(lua_eval):
    """The bands the game will actually use, computed by both implementations."""
    for name in ("reference_pair1.json", "reference_pair2.json"):
        reference = json.loads(
            (REPO_ROOT / "configs" / "references" / name).read_text(encoding="utf-8"))
        for c in reference["corners"]:
            both(lua_eval, c, {
                "brake_initiation_distance_m": 2.0,
                "min_corner_speed_kmh": c["corner_speed"]["mean_kmh"] + 1.0,
                "apex_rms_m": c["apex"]["mean_rms_m"] + 0.1,
            })


def test_the_floors_set_every_band_on_the_real_reference_tables():
    """The M3 finding, pinned to the exact count rather than left as a slogan.

    'EVM_AI does almost nothing against an AI this repeatable — the floors set
    every band' is the claim that makes floor calibration the load-bearing part
    of Gate G2 and is repeated in framing v6's limitation of the AI-only
    reference. Under the frozen-g1 configuration it is exactly true: all 27 bands
    (9 corners x 3 metrics) come from their floor, so EVM_AI currently has no
    effect on any criterion at all. It was not quite true before Gate G1 — at the
    provisional 3.0 km/h corner-speed floor, pair 1 corner 2's band came from its
    sigma instead (1.037 km/h x EVM 3.0 = 3.111 km/h), and raising that floor to
    4.0 absorbed it. Asserting the count means a re-extraction, an EVM change at
    Gate G2, or a floor change that moves the balance shows up here instead of
    quietly invalidating the sentence in the thesis.
    """
    floored = exceptions = 0
    for name in ("reference_pair1.json", "reference_pair2.json"):
        reference = json.loads(
            (REPO_ROOT / "configs" / "references" / name).read_text(encoding="utf-8"))
        for c in reference["corners"]:
            b = pyev.bands(CFG, c)
            for key, floor in (("braking_m", FLOORS["braking_m"]),
                               ("corner_speed_kmh", FLOORS["corner_speed_kmh"]),
                               ("apex_m", FLOORS["apex_m"])):
                if key not in b:
                    continue
                if b[key] == pytest.approx(floor):
                    floored += 1
                else:
                    exceptions += 1
                    assert b[key] < floor * 1.05, (
                        "{} corner {} {}: sigma x EVM now exceeds the floor by more "
                        "than 5%; the 'floor-dominated' claim needs revisiting"
                        .format(name, c["corner_id"], key))
    assert (floored, exceptions) == (27, 0)
