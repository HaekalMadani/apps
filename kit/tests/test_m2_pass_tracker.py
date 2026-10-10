"""M2 tests: the corner-pass tracker + the headerless logger mode.

The Lua side runs the real runtime modules (lua/trace_rt/lib/pass_tracker.lua,
pass_record.lua, logger.lua, json.lua) through lupa (LuaJIT 2.1), exactly as the
M0/M1 suites do, so headless behaviour mirrors in-game behaviour. Every emitted
pass record is validated against passes.schema.json via trace_kit.validate.

The tracker is driven by a small Lua harness that feeds it a list of per-tick
snapshots and returns the JSON of all closed-pass records, so the Python tests
stay declarative.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"

# Gates offset off round sample positions so a 0.01 spline step never lands
# exactly on a gate (keeps crossing assertions free of float-equality flakiness).
C1 = {"id": "C1", "entry_gate": 0.105, "exit_gate": 0.205}
C2 = {"id": "C2", "entry_gate": 0.505, "exit_gate": 0.605}
WRAP = {"id": "W", "entry_gate": 0.955, "exit_gate": 0.055}  # straddles start/finish


@pytest.fixture(scope="module")
def lua():
    rt = LuaRuntime(unpack_returned_tuples=True)
    rt.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return rt


@pytest.fixture(scope="module")
def driver(lua):
    """Returns run(corners, snaps, close_t) -> list of record dicts."""
    fn = lua.eval(
        """
        function(corners_json, snaps_json, close_t)
          local json = require('lib/json')
          local pt = require('lib/pass_tracker')
          local corners = json.decode(corners_json)
          local snaps = json.decode(snaps_json)
          local st = pt.new(corners, 'BLK')
          local recs = {}
          for i = 1, #snaps do
            local evs = pt.update(st, snaps[i])
            for j = 1, #evs do
              if evs[j].kind == 'close' then recs[#recs + 1] = evs[j].record end
            end
          end
          if close_t ~= nil then
            local evs = pt.close_open(st, close_t)
            for j = 1, #evs do
              if evs[j].kind == 'close' then recs[#recs + 1] = evs[j].record end
            end
          end
          return json.encode(recs)
        end
        """
    )

    def run(corners, snaps, close_t=None):
        out = fn(json.dumps(corners), json.dumps(snaps), close_t)
        return json.loads(out)

    return run


# --- snapshot generation -----------------------------------------------------

def _snap(spline, lap, t, wheels=0, in_pit=False, collision=0.0):
    return {
        "spline": round(spline, 6),
        "lap": lap,
        "t": round(t, 4),
        "wheels_outside": wheels,
        "in_pit": in_pit,
        "collision_depth": collision,
    }


def _drive(stop_lap, stop_spline, step=0.01, hazard=None):
    """Walk spline forward at `step`/tick from (lap 0, spline 0), wrapping 1->0 and
    incrementing lap, until reaching (stop_lap, stop_spline). `hazard(lap, spline)`
    may return a dict of snap overrides (e.g. {"wheels": 4}) for that sample.
    """
    snaps = []
    lap, s, t = 0, 0.0, 0.0
    snaps.append(_snap(s, lap, t))
    while not (lap > stop_lap or (lap == stop_lap and s >= stop_spline)):
        s += step
        t += 0.05
        if s >= 1.0:
            s -= 1.0
            lap += 1
        over = hazard(lap, s) if hazard else None
        if over:
            snaps.append(_snap(s, lap, t, wheels=over.get("wheels", 0),
                               in_pit=over.get("in_pit", False),
                               collision=over.get("collision", 0.0)))
        else:
            snaps.append(_snap(s, lap, t))
    return snaps


def _by_corner(records, corner_id):
    return [r for r in records if r["corner_id"] == corner_id]


# --- one pass per corner, lap attribution, wrap ------------------------------

def test_one_pass_per_corner_per_lap_and_wrap(driver):
    snaps = _drive(stop_lap=2, stop_spline=0.70)
    recs = driver([C1, C2, WRAP], snaps)

    # C1 and C2 fire once each on laps 0, 1, 2.
    assert [r["lap"] for r in _by_corner(recs, "C1")] == [0, 1, 2]
    assert [r["lap"] for r in _by_corner(recs, "C2")] == [0, 1, 2]
    # The wrap corner opens at 0.955 and closes after the line; attributed to the
    # ENTRY lap. Entered on laps 0 and 1 (lap-2 entry at 0.955 is never reached).
    assert [r["lap"] for r in _by_corner(recs, "W")] == [0, 1]

    # Every record is schema-valid.
    for r in recs:
        assert pyval.validate_data("passes", r) == [], r


def test_no_double_count_on_gate_jitter(driver):
    # Oscillate across the entry gate, then across the exit gate: still one pass.
    snaps = [_snap(0.00, 0, 0.0)]
    pattern = [0.10, 0.11, 0.10, 0.11, 0.12,       # jitter across entry 0.105
               0.19, 0.20, 0.21, 0.20, 0.21, 0.22]  # jitter across exit 0.205
    for i, s in enumerate(pattern):
        snaps.append(_snap(s, 0, 0.05 * (i + 1)))
    recs = driver([C1], snaps)
    assert len(recs) == 1
    assert recs[0]["corner_id"] == "C1"


# --- validity flags ----------------------------------------------------------

def test_first_lap_passes_are_invalid(driver):
    # On the session's starting lap (start_lap == entry_lap) passes are flagged.
    snaps = _drive(stop_lap=0, stop_spline=0.70)
    recs = driver([C1, C2], snaps)
    assert recs, "expected lap-0 passes"
    for r in recs:
        assert r["valid"] is False
        assert "first_lap" in r["invalid_reasons"]


def test_clean_later_lap_pass_is_valid(driver):
    snaps = _drive(stop_lap=1, stop_spline=0.30)  # drive into lap 1
    recs = _by_corner(driver([C1], snaps), "C1")
    laps = {r["lap"]: r for r in recs}
    assert laps[0]["valid"] is False           # out-lap
    assert laps[1]["valid"] is True            # clean flying lap
    assert "invalid_reasons" not in laps[1]


def test_wheels_outside_invalidates(driver):
    # 3+ wheels off inside the lap-1 C1 pass -> invalid via wheels_outside only.
    def hazard(lap, s):
        if lap == 1 and 0.105 < s < 0.205:
            return {"wheels": 4}
        return None
    snaps = _drive(stop_lap=1, stop_spline=0.30, hazard=hazard)
    rec = {r["lap"]: r for r in _by_corner(driver([C1], snaps), "C1")}[1]
    assert rec["valid"] is False
    assert rec["invalid_reasons"] == ["wheels_outside"]


def test_two_wheels_off_still_valid(driver):
    # 2 wheels off is within AC's track-limit rule -> pass stays valid.
    def hazard(lap, s):
        if lap == 1 and 0.105 < s < 0.205:
            return {"wheels": 2}
        return None
    snaps = _drive(stop_lap=1, stop_spline=0.30, hazard=hazard)
    rec = {r["lap"]: r for r in _by_corner(driver([C1], snaps), "C1")}[1]
    assert rec["valid"] is True


def test_pit_and_wall_invalidate(driver):
    def hazard(lap, s):
        if lap == 1 and 0.105 < s < 0.205:
            return {"in_pit": True, "collision": 0.4}
        return None
    snaps = _drive(stop_lap=1, stop_spline=0.30, hazard=hazard)
    rec = {r["lap"]: r for r in _by_corner(driver([C1], snaps), "C1")}[1]
    assert rec["valid"] is False
    assert "wall_contact" in rec["invalid_reasons"]
    assert "pit_transition" in rec["invalid_reasons"]


def test_block_end_mid_pass_is_incomplete(driver):
    # Cross entry, never reach exit, then close the block.
    snaps = [_snap(0.00, 0, 0.0), _snap(0.10, 0, 0.05), _snap(0.15, 0, 0.10)]
    recs = driver([C1], snaps, close_t=99.0)
    assert len(recs) == 1
    assert recs[0]["valid"] is False
    assert "incomplete" in recs[0]["invalid_reasons"]
    assert recs[0]["t_exit"] == 99.0
    assert pyval.validate_data("passes", recs[0]) == []


# --- forward_crossed unit checks (wrap logic) --------------------------------

def test_forward_crossed_wrap_and_reverse(lua):
    fn = lua.eval(
        """
        function(prev, cur, gate)
          return require('lib/pass_tracker').forward_crossed(prev, cur, gate)
        end
        """
    )
    assert fn(0.09, 0.11, 0.10) is True       # normal forward crossing
    assert fn(0.11, 0.09, 0.10) is False      # small reverse: no forward cross
    assert fn(0.97, 0.02, 0.005) is True      # wrap, gate just after the line
    assert fn(0.97, 0.02, 0.99) is True       # wrap, gate just before the line
    assert fn(0.97, 0.02, 0.50) is False      # wrap, gate on the far side
    assert fn(0.10, 0.10, 0.10) is False      # no movement


# --- headerless logger (JSONL) mode ------------------------------------------

def test_logger_headerless_serializes_rows_only(lua):
    fn = lua.eval(
        """
        function()
          local logger = require('lib/logger')
          local L = logger.new(nil)             -- headerless
          local empty = logger.serialize(L)
          logger.add(L, '{"a":1}')
          logger.add(L, '{"a":2}')
          return empty, logger.serialize(L)
        end
        """
    )
    empty, text = fn()
    assert empty == ""                          # no stray leading newline
    assert text == '{"a":1}\n{"a":2}\n'


def test_logger_with_header_unchanged(lua):
    fn = lua.eval(
        """
        function()
          local logger = require('lib/logger')
          local L = logger.new('a,b')
          local header_only = logger.serialize(L)
          logger.add(L, '1,2')
          return header_only, logger.serialize(L)
        end
        """
    )
    header_only, text = fn()
    assert header_only == "a,b\n"
    assert text == "a,b\n1,2\n"


# --- wall contact is a THRESHOLD on depth, not any contact at all ------------

def test_kerb_graze_does_not_invalidate(driver):
    """Regression, from the first International reference block: 6 of 13 passes
    at corner 5 were flagged wall_contact while the car never put a wheel off
    and lost no speed -- the AI's floor grazing a kerb. A few millimetres of
    contact is fast driving, not an incident."""
    def hazard(lap, s):
        if lap == 1 and 0.12 < s < 0.16:
            return {"collision": 0.004}
        return None
    snaps = _drive(stop_lap=1, stop_spline=0.30, hazard=hazard)
    rec = {r["lap"]: r for r in _by_corner(driver([C1], snaps), "C1")}[1]
    assert rec["valid"] is True
    assert "invalid_reasons" not in rec


def test_real_impact_still_invalidates(driver):
    def hazard(lap, s):
        if lap == 1 and 0.12 < s < 0.16:
            return {"collision": 0.30}
        return None
    snaps = _drive(stop_lap=1, stop_spline=0.30, hazard=hazard)
    rec = {r["lap"]: r for r in _by_corner(driver([C1], snaps), "C1")}[1]
    assert rec["valid"] is False
    assert "wall_contact" in rec["invalid_reasons"]


def test_gate_inputs_are_stamped_into_the_record(driver):
    """The verdict is not enough: the raw inputs must be in the record, or a
    disputed flag can only be second-guessed by inference from speed traces."""
    def hazard(lap, s):
        if lap == 1 and 0.12 < s < 0.16:
            return {"collision": 0.004, "wheels": 2}
        return None
    snaps = _drive(stop_lap=1, stop_spline=0.30, hazard=hazard)
    rec = {r["lap"]: r for r in _by_corner(driver([C1], snaps), "C1")}[1]
    assert rec["max_collision_depth_m"] == pytest.approx(0.004)
    assert rec["max_wheels_outside"] == 2
    assert rec["valid"] is True          # neither gate tripped
