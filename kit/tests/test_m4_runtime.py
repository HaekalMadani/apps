"""M4: the runtime loop end to end, headless.

The individual M4 modules are covered elsewhere — ``test_m4_pass_metrics`` pins
the accumulators to the offline extractor, ``test_m4_evaluator`` pins the
criteria, ``test_m4_controller_parity`` pins the state machine. What none of them
covers is the WIRING: that a driven pass flows tracker -> metrics -> evaluator ->
controller -> record, and that what lands on disk validates against
``passes.schema.json`` and ``fades.schema.json``.

``trace_rt.lua`` cannot run headless (it is the ac.*/io.* boundary by design), so
the harness below reproduces its per-frame sequence over the real lib/ modules.
That is a real limitation and it is bounded deliberately: the harness is kept
small and mirrors one specific ordering in ``trace_rt.lua`` — feed every open
pass THIS frame's sample, then advance the tracker, then evaluate and record each
closed pass. If that ordering changes in trace_rt.lua it must change here, and
the comments in both name each other.
"""

import json
import math
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))

TRACK_LENGTH_M = 2600.0
DT = 0.05


# --- a synthetic two-corner track -------------------------------------------
#
# Corner "1" has a braking zone; corner "2" is taken FLAT, so it is applicable to
# corner_speed and apex but NOT to braking. That asymmetry is the study's own
# (impl plan section 7) and it is what makes the per-element quorum denominators
# differ within one block.

def apex_line(centre):
    return [{"spline_pos": round(centre - 0.004 + 0.001 * i, 6),
             "world_pos": [(centre - 0.004 + 0.001 * i) * TRACK_LENGTH_M, 0.0, 0.0]}
            for i in range(9)]


ANNOTATION = {
    "schema_version": 1,
    "track": "synthetic",
    "corners": [
        {"id": "1", "type": "medium", "compound": False,
         "entry_gate": 0.10, "exit_gate": 0.35,
         "zones": {"braking": {"start": 0.14, "end": 0.22},
                   "apex_gates": [0.28], "apex_window_half_m": 20.0,
                   "corner_speed": {"start": 0.22, "end": 0.32}}},
        {"id": "2", "type": "fast", "compound": False,
         "entry_gate": 0.55, "exit_gate": 0.80,
         "zones": {"apex_gates": [0.72], "apex_window_half_m": 20.0,
                   "corner_speed": {"start": 0.66, "end": 0.78}}},
    ],
}

REFERENCE = {
    "schema_version": 1, "pair_id": "pair1", "track": "synthetic",
    "car": "synthetic_car", "track_length_m": TRACK_LENGTH_M,
    "corners": [
        {"corner_id": "1", "source": "ai",
         "contributing_laps": {"clean_passes": 12, "braking": 12, "apex": 12, "corner_speed": 12},
         "braking": {"world_pos": [0.0, 0.0, 0.0], "spline_pos": 0.18, "sigma_ref_m": 0.8},
         "apex": {"gates": [{"world_pos": [0, 0, 0], "spline_pos": 0.28,
                             "line": apex_line(0.28)}],
                  "mean_rms_m": 0.05, "sigma_ref_m": 0.01},
         "corner_speed": {"mean_kmh": 90.0, "sigma_ref_kmh": 0.3}},
        {"corner_id": "2", "source": "ai",
         "contributing_laps": {"clean_passes": 12, "apex": 12, "corner_speed": 12},
         "apex": {"gates": [{"world_pos": [0, 0, 0], "spline_pos": 0.72,
                             "line": apex_line(0.72)}],
                  "mean_rms_m": 0.05, "sigma_ref_m": 0.01},
         "corner_speed": {"mean_kmh": 120.0, "sigma_ref_kmh": 0.4}},
    ],
}


def test_the_synthetic_fixtures_are_schema_valid():
    """If the fixtures were invalid the runtime would refuse to start on them."""
    assert pyval.validate_data("annotation", ANNOTATION) == []
    assert pyval.validate_data("reference", REFERENCE) == []


# --- the harness -------------------------------------------------------------

@pytest.fixture(scope="module")
def runtime():
    """run(snaps, close_t) -> {'passes': [...], 'fades': [...], 'disabled': [...]}."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval(
        """
        function(ann_json, ref_json, cfg_json, snaps_json, close_t, track_length_m)
          local json = require('lib/json')
          local pass_tracker = require('lib/pass_tracker')
          local pass_metrics = require('lib/pass_metrics')
          local evaluator = require('lib/evaluator')
          local controller = require('lib/controller')
          local pass_record = require('lib/pass_record')

          local corners = json.decode(ann_json).corners
          local reference = json.decode(ref_json)
          local cfg = json.decode(cfg_json)
          local snaps = json.decode(snaps_json)

          -- Mirrors trace_rt.lua's start_block(): the same five objects, built
          -- from the same three inputs, in the same order.
          local tracker = pass_tracker.new(corners, 'BLK')
          local plans = pass_metrics.plans(corners, reference, track_length_m, cfg)
          local ref_corners = evaluator.index_corners(reference)
          local ctrl = controller.new(cfg, evaluator.applicable(reference))
          local open_metrics, history = {}, {}
          for i = 1, #corners do history[corners[i].id] = {} end

          local passes, fades = {}, {}

          local function evaluate_pass(record)
            local st = open_metrics[record.corner_id]
            open_metrics[record.corner_id] = nil
            if st == nil then return end
            local ref_corner = ref_corners[record.corner_id]
            if ref_corner == nil then return end
            local metrics = pass_metrics.close(st)
            local h = history[record.corner_id]
            local evaluation = evaluator.evaluate(cfg, ref_corner, metrics, h)
            if metrics.brake_initiation_distance_m ~= nil then
              evaluator.push_history(h, metrics.brake_initiation_distance_m,
                cfg.qualification.window_passes)
            end
            local evs = controller.step(ctrl, {
              corner_id = record.corner_id, lap = record.lap, t = record.t_exit,
              criteria = evaluation.criteria,
            })
            for j = 1, #evs do
              fades[#fades + 1] = pass_record.fade_record('BLK', evs[j])
            end
            pass_record.attach(record, metrics, evaluation,
              controller.qualified(ctrl, record.corner_id), controller.stages(ctrl))
          end

          local function handle(events, snap)
            for i = 1, #events do
              local e = events[i]
              if e.kind == 'open' then
                local plan = plans[e.corner_id]
                if plan ~= nil then
                  open_metrics[e.corner_id] = pass_metrics.update(
                    pass_metrics.open(plan, snap), snap)
                end
              else
                evaluate_pass(e.record)
                passes[#passes + 1] = e.record
              end
            end
          end

          -- Mirrors trace_rt.lua's sample_frame(): feed the already-open passes
          -- THIS frame's sample first, then advance the tracker, so a pass that
          -- closes on this frame still gets the exit-crossing sample.
          for i = 1, #snaps do
            local snap = snaps[i]
            for _, st in pairs(open_metrics) do pass_metrics.update(st, snap) end
            handle(pass_tracker.update(tracker, snap), snap)
          end
          if close_t ~= nil then
            handle(pass_tracker.close_open(tracker, close_t), nil)
            local evs = controller.finish(ctrl, snaps[#snaps].lap, close_t)
            for j = 1, #evs do
              fades[#fades + 1] = pass_record.fade_record('BLK', evs[j])
            end
          end

          return json.encode({
            passes = passes, fades = fades,
            disabled = controller.disabled_elements(ctrl),
            stages = controller.stages(ctrl),
          })
        end
        """
    )

    def run(snaps, close_t=None, reference=None, annotation=None, cfg=None):
        out = fn(json.dumps(annotation or ANNOTATION), json.dumps(reference or REFERENCE),
                 json.dumps(cfg or CFG), json.dumps(snaps), close_t, TRACK_LENGTH_M)
        result = json.loads(out)
        result.setdefault("passes", [])
        result.setdefault("fades", [])
        result.setdefault("disabled", [])
        return result

    return run


# --- driving -----------------------------------------------------------------

def drive(laps, skill, seed=0.0):
    """Generate per-frame snapshots for `laps` laps.

    `skill` in [0, 1] scales how close the driver is to the reference: 0 is a
    raw novice (brakes far too early, slow, off the line), 1 sits on it. It is a
    single knob rather than a model because the point here is the wiring, not
    the learner — ``trace_kit.simulate`` is where learner behaviour is modelled.
    """
    step = 0.0025
    snaps = []
    t = 0.0
    for lap in range(laps):
        spline = 0.0
        while spline < 1.0:
            k = skill(lap) if callable(skill) else skill
            # Brake early by up to 40 m of track at zero skill.
            brake_spline = 0.18 - (1.0 - k) * (40.0 / TRACK_LENGTH_M)
            in_c1_speed = 0.22 <= spline <= 0.32
            in_c2_speed = 0.66 <= spline <= 0.78
            speed = 150.0
            if in_c1_speed:
                speed = 90.0 - (1.0 - k) * 14.0
            elif in_c2_speed:
                speed = 120.0 - (1.0 - k) * 14.0
            snaps.append({
                "t": round(t, 4), "lap": lap, "spline": round(spline, 6),
                "wheels_outside": 0, "in_pit": False, "collision_depth": 0.0,
                "brake": 0.8 if spline >= brake_spline and spline <= 0.24 else 0.0,
                "speed_kmh": speed,
                "pos_x": spline * TRACK_LENGTH_M,
                "pos_y": 0.0,
                # Lateral offset from the expert line: 2.5 m off at zero skill.
                "pos_z": (1.0 - k) * 2.5 + seed * math.sin(lap * 3.0),
            })
            spline += step
            t += DT
    return snaps


# --- the tests ---------------------------------------------------------------

def test_a_driven_block_produces_schema_valid_pass_records(runtime):
    result = runtime(drive(6, 1.0))
    assert result["passes"], "no passes closed"
    for record in result["passes"]:
        assert pyval.validate_data("passes", record) == [], record


def test_every_fade_event_is_schema_valid(runtime):
    result = runtime(drive(14, 1.0))
    assert result["fades"], "an on-the-reference driver must fade something"
    for record in result["fades"]:
        assert pyval.validate_data("fades", record) == [], record


def test_metrics_reach_the_pass_record_with_the_right_shape(runtime):
    """The wiring this test exists for: real numbers, not the M2 placeholders."""
    result = runtime(drive(3, 1.0))
    c1 = [p for p in result["passes"] if p["corner_id"] == "1"]
    assert c1
    metrics = c1[-1]["metrics"]
    assert metrics["brake_initiation_distance_m"] is not None
    assert metrics["min_corner_speed_kmh"] == pytest.approx(90.0, abs=0.5)
    assert metrics["apex_rms_m"] is not None
    # The raw brake-initiation sample, stamped for the Gate G2 event-log audit
    # (impl plan section 2.1.4): the 20 Hz tick log cannot resolve it.
    assert metrics["brake_initiation"]["spline_pos"] == pytest.approx(0.18, abs=0.01)
    assert metrics["brake_initiation"]["t"] > 0
    assert metrics["brake_modulation"]["peak"] == pytest.approx(0.8)
    # Descriptive only: logged, never gated.
    assert metrics["brake_modulation"]["releases"] >= 0


def test_a_flat_corner_never_gets_a_braking_criterion(runtime):
    """Corner 2 has no braking zone: not applicable, not failing."""
    result = runtime(drive(6, 1.0))
    for record in result["passes"]:
        if record["corner_id"] == "2":
            assert record["metrics"]["brake_initiation_distance_m"] is None
            assert record["criteria"]["braking"] is None
            assert record["braking_gates"]["accuracy"] is None
    # ...and it never appears in a braking quorum denominator: only corner 1 is
    # applicable, so that element's denominator is 1 while the others' are 2.
    braking = [f for f in result["fades"] if f["element"] == "braking"]
    others = [f for f in result["fades"] if f["element"] != "braking"]
    assert all(f["quorum"]["applicable_corners"] == 1 for f in braking)
    assert all(f["quorum"]["applicable_corners"] == 2 for f in others)


def test_an_on_the_reference_driver_traverses_the_machine(runtime):
    result = runtime(drive(14, 1.0))
    assert result["stages"]["corner_speed"] == "removed"
    assert result["stages"]["apex"] == "removed"
    transitions = [f["transition"] for f in result["fades"] if f["element"] == "apex"]
    assert transitions == ["full_to_reduced", "reduced_to_probe", "probe_to_removed"]


def test_a_novice_never_fades_anything(runtime):
    """The other end of the same wiring: metrics far outside every band."""
    result = runtime(drive(14, 0.0))
    assert result["fades"] == []
    assert set(result["stages"].values()) == {"full"}
    # And the criteria really were evaluated and failed, not skipped as null.
    c1 = [p for p in result["passes"] if p["corner_id"] == "1"]
    assert all(p["criteria"]["corner_speed"] is False for p in c1)
    assert all(p["criteria"]["apex"] is False for p in c1)


def test_the_pass_record_carries_the_state_the_pass_produced(runtime):
    """A fade event and the pass that caused it must agree on corner and lap."""
    result = runtime(drive(14, 1.0))
    for fade in result["fades"]:
        if fade["transition"] == "full_to_reduced":
            matching = [p for p in result["passes"]
                        if p["lap"] == fade["lap"] and p["t_exit"] == fade["t"]]
            assert len(matching) == 1, "no pass record matches the fade event"
            # The record shows the stage the pass PRODUCED, not the one it met.
            assert matching[0]["stage"][fade["element"]] == "reduced"


def test_an_improving_driver_shows_the_dwell_the_reset_enforces(runtime):
    """The re-qualification rule, visible in a driven block rather than a trace."""
    result = runtime(drive(16, lambda lap: min(1.0, 0.25 * lap)))
    apex = [f for f in result["fades"] if f["element"] == "apex"]
    laps = {f["transition"]: f["lap"] for f in apex}
    assert {"full_to_reduced", "reduced_to_probe"} <= set(laps), \
        "the improving driver must reach the probe for this test to mean anything"
    assert laps["reduced_to_probe"] - laps["full_to_reduced"] >= 3


def test_the_three_elements_fade_on_independent_trajectories(runtime):
    """The thesis's contribution (a), demonstrated rather than asserted.

    Framing v6's gap statement rests on per-element independence: three scaffolds
    with distinct telemetry criteria fading on separate trajectories, where the
    adaptive-training prior art adjusted a single global parameter. A driver who
    masters corner speed before braking must therefore lose the corner-speed
    indicator first, with the braking marker still at full salience — if all
    three moved together the mechanism would be a global difficulty knob wearing
    three hats.
    """
    result = runtime(drive(16, lambda lap: min(1.0, 0.25 * lap)))
    first = {}
    for fade in result["fades"]:
        first.setdefault((fade["element"], fade["transition"]), fade["lap"])

    advance = "full_to_reduced"
    laps = {e: first[(e, advance)] for e in ("braking", "corner_speed", "apex")
            if (e, advance) in first}
    assert len(laps) == 3, "all three elements must fade for this to be a test"
    assert len(set(laps.values())) > 1, (
        "all three elements advanced on the same lap: the trajectories are not "
        "independent, or the synthetic driver improves at every metric at once")
    # And the spread is real, not a one-pass ordering artefact within a lap.
    assert max(laps.values()) - min(laps.values()) >= 2, laps


def test_a_block_ending_mid_probe_censors_and_closes_open_passes(runtime):
    snaps = drive(9, 1.0)
    # Stop mid-corner-1, so a pass is open at block end as well.
    snaps = [s for s in snaps if not (s["lap"] == 8 and s["spline"] > 0.20)]
    result = runtime(snaps, close_t=9999.0)

    incomplete = [p for p in result["passes"]
                  if "incomplete" in (p.get("invalid_reasons") or [])]
    assert incomplete, "the pass open at block end must close incomplete"
    # An incomplete pass has no metrics to speak of, and that is NO EVIDENCE:
    # it must not read as a failure.
    assert incomplete[-1]["criteria"]["apex"] is None

    censored = [f for f in result["fades"] if f["transition"] == "censored"]
    assert censored, "an element mid-probe at block end must be censored"
    for record in censored:
        assert pyval.validate_data("fades", record) == [], record
        assert result["stages"][record["element"]] == "probe"


def test_an_element_with_no_applicable_corners_is_disabled(runtime):
    """impl plan section 7's degenerate case, through the real runtime path."""
    annotation = json.loads(json.dumps(ANNOTATION))
    reference = json.loads(json.dumps(REFERENCE))
    del annotation["corners"][0]["zones"]["braking"]
    del reference["corners"][0]["braking"]
    del reference["corners"][0]["contributing_laps"]["braking"]
    assert pyval.validate_data("reference", reference) == []

    result = runtime(drive(12, 1.0), annotation=annotation, reference=reference)
    assert result["disabled"] == ["braking"]
    assert result["stages"]["braking"] == "full"
    assert not any(f["element"] == "braking" for f in result["fades"])
    # The other two are unaffected, and no event ever carries a zero denominator.
    assert any(f["element"] == "apex" for f in result["fades"])
    assert all(f["quorum"]["applicable_corners"] >= 1 for f in result["fades"])


def test_static_and_adaptive_blocks_log_identically(runtime):
    """Impl plan section 5: the condition is a config field, not a code path.

    Static mode runs the identical pipeline and pins only the SALIENCE, which
    lives in the renderer. So the controller must produce byte-identical pass and
    fade records under either mode — that is what makes the two conditions
    comparable at all.
    """
    static = json.loads(json.dumps(CFG))
    static["mode"] = "static"
    snaps = drive(12, 1.0)
    assert runtime(snaps) == runtime(snaps, cfg=static)
