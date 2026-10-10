"""M6: the two experimenter-panel affordances impl plan section 7 names and M5
shipped without — the probe countdown and the abort.

Both are panel features, and the panel itself is the ac.*/ui.* boundary that
cannot run headless. What IS testable is everything the panel only displays or
stamps, which is deliberately where the logic was put:

  * ``controller.probe_remaining`` — the countdown is a controller reader, in
    BOTH languages, because the panel must not do arithmetic on controller
    internals and the simulator wants the same number for probe-outcome
    reporting. Pinned to each other here, the way every other shared reader is.
  * the abort — a manifest stamp (``aborted`` / ``abort_reason``), a closed
    reason list that must not drift from the schema's enum, and an integrity
    checker that treats an aborted block as explained-empty rather than broken.

What is NOT covered here, and is on the M5/M6 in-game checklist: that the two
clicks of the abort control behave as two clicks on screen, and that the
countdown renders. A headless test cannot press a CSP button.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import integrity
from trace_kit import validate as pyval
from trace_kit.controller import Controller

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))


# --- Lua bootstrap ----------------------------------------------------------

@pytest.fixture(scope="module")
def lua():
    rt = LuaRuntime(unpack_returned_tuples=True)
    rt.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return rt


@pytest.fixture(scope="module")
def lua_controller(lua):
    """Returns build(cfg_json, applicable_json) -> a Lua-side driver table."""
    return lua.eval(
        """
        function(cfg_text, applicable_text)
          local json = require('lib/json')
          local controller = require('lib/controller')
          local cfg = json.decode(cfg_text)
          local st = controller.new(cfg, json.decode(applicable_text))
          return {
            step = function(pass_text)
              controller.step(st, json.decode(pass_text))
            end,
            stage = function(element)
              return controller.snapshot(st)[element].stage
            end,
            -- nil is returned as Python None by lupa, which is exactly the
            -- parity we want to assert against controller.py.
            probe_remaining = function(element, lap)
              return controller.probe_remaining(st, element, lap)
            end,
          }
        end
        """
    )


# --- a stream that actually reaches the probe -------------------------------
#
# Two corners, every criterion met on every pass. With window_passes 4 /
# required_passes 3 the quorum becomes READY once both corners hold 3 passes
# (rule 2), and re-qualification on advance (rule 1) means each advance needs
# another 3 passes per corner. So: full -> reduced, then reduced -> probe.

APPLICABLE = {"braking": ["1", "2"], "corner_speed": ["1", "2"], "apex": ["1", "2"]}
ALL_MET = {"braking": True, "corner_speed": True, "apex": True}


def a_pass(corner_id, lap):
    return {"corner_id": corner_id, "lap": lap, "t": lap * 60.0 + float(corner_id),
            "criteria": dict(ALL_MET)}


def test_probe_remaining_is_none_while_not_probing(lua_controller):
    ctrl = Controller(CFG, APPLICABLE)
    lctrl = lua_controller(json.dumps(CFG), json.dumps(APPLICABLE))

    assert ctrl.stages()["braking"] == "full"
    assert ctrl.probe_remaining("braking", 1) is None
    assert lctrl.probe_remaining("braking", 1) is None


def test_probe_countdown_matches_across_both_controllers(lua_controller):
    """The countdown is read in the controller's own lap space, in both languages."""
    ctrl = Controller(CFG, APPLICABLE)
    lctrl = lua_controller(json.dumps(CFG), json.dumps(APPLICABLE))

    probe_laps = CFG["probe"]["laps"]
    entry_lap = None

    for lap in range(1, 40):
        for corner_id in ("1", "2"):
            p = a_pass(corner_id, lap)
            ctrl.step(p)
            lctrl.step(json.dumps(p))

        py_stage = ctrl.stages()["braking"]
        assert py_stage == lctrl.stage("braking"), "stage parity broke at lap {}".format(lap)

        py_left = ctrl.probe_remaining("braking", lap)
        lua_left = lctrl.probe_remaining("braking", lap)
        if lua_left is not None:
            lua_left = int(lua_left)
        assert py_left == lua_left, "countdown parity broke at lap {}".format(lap)

        if py_stage == "probe" and entry_lap is None:
            entry_lap = lap
            # Counted from the entry PASS: a probe entered on lap N still has
            # all `probe.laps` laps to run.
            assert py_left == probe_laps
        if py_stage == "removed":
            break

    assert entry_lap is not None, "the stream never reached a probe"


def test_probe_countdown_never_goes_negative(lua_controller):
    """A stalled probe reads 0 laps left, not a negative number on the panel."""
    ctrl = Controller(CFG, APPLICABLE)
    lctrl = lua_controller(json.dumps(CFG), json.dumps(APPLICABLE))

    entry_lap = None
    for lap in range(1, 40):
        for corner_id in ("1", "2"):
            p = a_pass(corner_id, lap)
            ctrl.step(p)
            lctrl.step(json.dumps(p))
        if ctrl.stages()["braking"] == "probe":
            entry_lap = lap
            break
    assert entry_lap is not None

    far_future = entry_lap + CFG["probe"]["laps"] + 10
    assert ctrl.probe_remaining("braking", far_future) == 0
    assert int(lctrl.probe_remaining("braking", far_future)) == 0


def test_probe_remaining_is_not_in_the_snapshot(lua_controller):
    """Guard the reason it is a separate reader: the golden traces pin snapshot.

    If a future change moves this field into `snapshot`, the whole G1 parity
    corpus has to be regenerated. That should be a deliberate act, not a
    side effect, so it fails here first.
    """
    ctrl = Controller(CFG, APPLICABLE)
    for element in ("braking", "corner_speed", "apex"):
        assert "probe_start_lap" not in ctrl.snapshot()[element]
        assert "probe_remaining" not in ctrl.snapshot()[element]


# --- the abort: manifest stamp ---------------------------------------------

BLOCK = "P01_s2_pair1_adaptive_20260908_120000"


def manifest(**overrides):
    doc = {
        "schema_version": 1,
        "block_id": BLOCK,
        "participant_id": "P01",
        "session": 2,
        "condition": "adaptive",
        "pair_id": "pair1",
        "config_hashes": {"annotation": "a" * 64, "reference": "b" * 64,
                          "controller_config": "c" * 64},
        "versions": {"app": "0.3.0", "csp": "0.2.11", "ac": "1.16.4"},
        "started_at": "2026-09-08T12:00:00",
        "laps_completed": 0,
    }
    doc.update(overrides)
    return doc


def test_an_aborted_manifest_validates():
    doc = manifest(aborted=True, abort_reason="participant_request")
    assert pyval.validate_data("session_manifest", doc) == []


def test_an_abort_must_say_why():
    """`dependencies` in the schema: aborted without a reason is invalid.

    The dataset README has to explain every discarded block later, and a reason
    nobody recorded at the time is a reason nobody can reconstruct.
    """
    assert pyval.validate_data("session_manifest", manifest(aborted=True)) != []


def test_an_unknown_abort_reason_is_rejected():
    assert pyval.validate_data(
        "session_manifest", manifest(aborted=True, abort_reason="felt_like_it")) != []


def test_aborted_false_is_rejected():
    """Follows dev_block: the key is present only when true.

    A completed block omits it entirely, so `aborted: false` would be a third
    state that readers would have to know to special-case.
    """
    assert pyval.validate_data(
        "session_manifest", manifest(aborted=False, abort_reason="other")) != []


def test_lua_and_schema_agree_on_the_reason_list(lua):
    """The panel's radio group and the schema's enum are one list, not two.

    The M2 lesson was that a manifest field constrained in only one of the two
    places is a schema-invalid manifest waiting to happen.
    """
    lua_reasons = list(lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local out = {}
          for i = 1, #manifest.ABORT_REASONS do out[i] = manifest.ABORT_REASONS[i] end
          return out
        end
        """
    )().values())
    schema_reasons = pyval.load_schema("session_manifest")["properties"]["abort_reason"]["enum"]
    assert sorted(lua_reasons) == sorted(schema_reasons)


def test_lua_mark_aborted_writes_a_valid_manifest(lua):
    """mark_aborted + a known reason round-trips through the Python validator."""
    stamped = lua.eval(
        """
        function(text, reason)
          local json = require('lib/json')
          local manifest = require('lib/manifest')
          local m = json.decode(text)
          manifest.mark_aborted(m, reason)
          return json.encode(m)
        end
        """
    )(json.dumps(manifest()), "sim_or_app_crash")
    doc = json.loads(stamped)
    assert doc["aborted"] is True
    assert doc["abort_reason"] == "sim_or_app_crash"
    assert pyval.validate_data("session_manifest", doc) == []


def test_lua_mark_aborted_coerces_an_unknown_reason(lua):
    """Belt and braces: an unknown reason becomes `other`, never a bad manifest.

    The panel can only send a listed reason, so this is the defence against a
    future caller rather than against the UI — and it fails toward a valid
    manifest, because a block that is gone is worse than a reason that is vague.
    """
    stamped = lua.eval(
        """
        function(text, reason)
          local json = require('lib/json')
          local manifest = require('lib/manifest')
          local m = json.decode(text)
          manifest.mark_aborted(m, reason)
          return json.encode(m)
        end
        """
    )(json.dumps(manifest()), "not_a_reason")
    doc = json.loads(stamped)
    assert doc["abort_reason"] == "other"
    assert pyval.validate_data("session_manifest", doc) == []


# --- the abort: what the integrity checker makes of it ----------------------

COLUMNS = integrity.expected_columns()


def write_block(tmp_path, manifest_doc, ticks=None):
    (tmp_path / "manifest_{}.json".format(BLOCK)).write_text(
        json.dumps(manifest_doc), encoding="utf-8")
    rows = [",".join(COLUMNS)] + list(ticks or [])
    (tmp_path / "ticks_{}.csv".format(BLOCK)).write_text(
        "\n".join(rows) + "\n", encoding="utf-8")
    return tmp_path / "manifest_{}.json".format(BLOCK)


def test_an_aborted_block_with_nothing_in_it_passes(tmp_path):
    """The real case from 2026-10-09: a block started and abandoned at once.

    Aborted deliberately, it should read as explained-empty. The same file set
    WITHOUT the abort stamp is what the checker must keep flagging.
    """
    path = write_block(tmp_path, manifest(aborted=True, abort_reason="experimenter_error"))
    problems, summary = integrity.check_block(path)
    assert problems == [], problems
    assert summary["row_count"] == 0


def test_the_same_empty_block_without_an_abort_still_fails(tmp_path):
    path = write_block(tmp_path, manifest())
    problems, _ = integrity.check_block(path)
    assert any("no data rows" in p for p in problems), problems


def test_an_aborted_block_is_still_held_to_well_formedness(tmp_path):
    """An abort excuses emptiness, never corruption.

    An abort discards the block, not the record of what happened, so whatever
    the block did write still has to be readable — otherwise an abort would be
    a way to launder a broken log past the integrity check.
    """
    path = write_block(
        tmp_path,
        manifest(aborted=True, abort_reason="hardware_fault", laps_completed=0),
        ticks=["this,is,not,a,valid,tick,row"])
    problems, _ = integrity.check_block(path)
    assert problems != []
