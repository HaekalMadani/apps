"""M3: world-anchored marker geometry (lua/trace_rt/lib/markers.lua) and the
runtime-side contracts M3 adds to the session manifest.

The Lua here is the real runtime module, run through lupa (LuaJIT 2.1) exactly
as the M0/M1 suites do. What cannot be tested headless -- that CSP actually
projects these coordinates onto the track -- is the milestone's in-game exit
test and Gate G0's on-track review.

This file also carries a compile check over every runtime Lua file. It is cheap
insurance on the one module the headless suites otherwise never load:
trace_rt.lua needs ac.*/render.* globals so it can never be *run* here, but a
syntax error in it costs a full game restart to discover.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
REFERENCE_FIXTURE = REPO_ROOT / "configs" / "examples" / "reference_example_pair.json"


@pytest.fixture(scope="module")
def lua():
    rt = LuaRuntime(unpack_returned_tuples=True)
    rt.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return rt


@pytest.fixture(scope="module")
def build_markers(lua):
    """markers.build over a reference table, returned as a list of dicts."""
    fn = lua.eval(
        """
        function(text)
          local json = require('lib/json')
          local markers = require('lib/markers')
          local out = {}
          local list = markers.build(json.decode(text))
          for i = 1, #list do
            local m = list[i]
            out[i] = json.encode({ element = m.element, corner_id = m.corner_id,
              spline = m.spline, x = m.x, y = m.y, z = m.z })
          end
          return json.encode(out)
        end
        """
    )

    def run(doc):
        return [json.loads(s) for s in json.loads(fn(json.dumps(doc)))]

    return run


@pytest.fixture(scope="module")
def reference_doc():
    return json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))


# --- the draw list -----------------------------------------------------------

def test_fixture_is_a_valid_reference(reference_doc):
    assert pyval.validate_data("reference", reference_doc) == []


def test_marker_positions_come_from_the_reference_not_from_code(
        build_markers, reference_doc):
    """The M3 exit criterion, in the one place it can be checked headless:
    every drawn coordinate must be traceable to the extracted table."""
    markers = build_markers(reference_doc)
    allowed = set()
    for corner in reference_doc["corners"]:
        if "braking" in corner:
            allowed.add(tuple(corner["braking"]["world_pos"]))
        for gate in corner["apex"]["gates"]:
            allowed.add(tuple(gate["world_pos"]))
    assert markers
    for m in markers:
        assert (m["x"], m["y"], m["z"]) in allowed


def test_one_braking_marker_per_braking_corner_and_one_per_apex_gate(
        build_markers, reference_doc):
    markers = build_markers(reference_doc)
    expected_braking = sum(1 for c in reference_doc["corners"] if "braking" in c)
    expected_apex = sum(len(c["apex"]["gates"]) for c in reference_doc["corners"])
    assert sum(1 for m in markers if m["element"] == "braking") == expected_braking
    assert sum(1 for m in markers if m["element"] == "apex") == expected_apex


def test_corner_taken_flat_contributes_no_braking_marker(build_markers, reference_doc):
    """A corner with no braking zone is not applicable to the braking-point
    element: no marker, no criterion, out of that element's quorum."""
    flat = [c["corner_id"] for c in reference_doc["corners"] if "braking" not in c]
    assert flat, "fixture should contain a corner taken flat"
    markers = build_markers(reference_doc)
    for m in markers:
        assert not (m["element"] == "braking" and m["corner_id"] in flat)


def test_compound_corner_gets_a_marker_per_apex_gate(build_markers, reference_doc):
    compound = [c for c in reference_doc["corners"] if len(c["apex"]["gates"]) > 1]
    assert compound, "fixture should contain a compound corner"
    markers = build_markers(reference_doc)
    for corner in compound:
        drawn = [m for m in markers
                 if m["element"] == "apex" and m["corner_id"] == corner["corner_id"]]
        assert len(drawn) == len(corner["apex"]["gates"])


# --- salience ----------------------------------------------------------------

@pytest.fixture(scope="module")
def alpha(lua):
    return lua.eval(
        """
        function(stage, full, reduced)
          local markers = require('lib/markers')
          return markers.alpha(stage, { full_alpha = full, reduced_alpha = reduced })
        end
        """
    )


def test_alpha_maps_each_stage_to_its_configured_constant(alpha):
    assert alpha("full", 1.0, 0.4) == 1.0
    assert alpha("reduced", 1.0, 0.4) == 0.4
    assert alpha("hidden", 1.0, 0.4) == 0.0


def test_alpha_uses_the_config_not_a_literal(alpha):
    # A renderer that hardcoded 0.4 would pass the test above and fail this one.
    assert alpha("reduced", 1.0, 0.15) == pytest.approx(0.15)


def test_hidden_is_fully_transparent_whatever_the_config(alpha):
    """Probe withdrawal must remove the cue, never merely dim it."""
    assert alpha("hidden", 1.0, 0.9) == 0.0


# --- view culling ------------------------------------------------------------

@pytest.fixture(scope="module")
def in_view(lua):
    return lua.eval(
        """
        function(marker, car, length, ahead, behind)
          local markers = require('lib/markers')
          return markers.in_view(marker, car, length, ahead, behind)
        end
        """
    )


TRACK_M = 2500.0


def test_marker_just_ahead_is_visible(in_view):
    assert in_view(0.14, 0.10, TRACK_M, 250.0, 30.0)      # 100 m ahead


def test_marker_far_ahead_is_culled(in_view):
    assert not in_view(0.60, 0.10, TRACK_M, 250.0, 30.0)  # 1250 m ahead


def test_marker_just_behind_stays_visible(in_view):
    """A cue must not blink out the instant the car crosses it."""
    assert in_view(0.10, 0.104, TRACK_M, 250.0, 30.0)     # 10 m behind


def test_marker_well_behind_is_culled(in_view):
    assert not in_view(0.10, 0.15, TRACK_M, 250.0, 30.0)  # 125 m behind


def test_view_window_wraps_start_finish(in_view):
    # car just before the line, marker just after it: 50 m ahead, not 2450 m
    assert in_view(0.01, 0.99, TRACK_M, 250.0, 30.0)


def test_view_window_is_metres_not_spline_units(in_view):
    """The same spline gap is in view on a long track and culled on a short one."""
    assert in_view(0.14, 0.10, 8000.0, 250.0, 30.0) is False   # 320 m ahead
    assert in_view(0.14, 0.10, 2500.0, 250.0, 30.0) is True    # 100 m ahead


# --- M3 manifest fields ------------------------------------------------------

def test_manifest_carries_the_apparatus_pins(lua):
    """track_id / car_id / track_length_m make a block's pair verifiable, and
    pin the scale every spline-to-metre conversion in the analysis uses."""
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='B1', participant_id='P01', session=2,
              condition='adaptive', pair_id='pair1',
              track_id='ks_silverstone-national', car_id='ks_mazda_mx5_cup',
              track_length_m=2597.4 },
            { annotation=h, reference=h, controller_config=h },
            { app='0.2.0', csp='0.2.x', ac='1.16.4' },
            '2026-09-07T15:30:00')
          return json.encode(m)
        end
        """
    )
    doc = json.loads(fn())
    assert doc["track_id"] == "ks_silverstone-national"
    assert doc["car_id"] == "ks_mazda_mx5_cup"
    assert doc["track_length_m"] == pytest.approx(2597.4)
    assert doc["versions"]["ac"] == "1.16.4"
    assert pyval.validate_data("session_manifest", doc) == []


def test_dev_block_may_carry_a_null_reference_hash(lua):
    """The reference laps are recorded before any reference table exists, so a
    dev block must be able to run with no reference to hash -- and a study block
    must not."""
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='REF1', participant_id='dev', session=2,
              condition='off', pair_id='pair1', dev_block=true },
            { annotation=h, reference=nil, controller_config=h },
            { app='0.2.0', csp='0.2.x', ac='1.16.4' },
            '2026-09-07T15:30:00')
          return json.encode(m)
        end
        """
    )
    doc = json.loads(fn())
    assert doc["dev_block"] is True
    assert doc["config_hashes"]["reference"] is None
    assert pyval.validate_data("session_manifest", doc) == []


def test_reference_hash_must_be_a_real_digest_when_present():
    doc = {
        "schema_version": 1, "block_id": "B1", "participant_id": "P01",
        "session": 2, "condition": "adaptive", "pair_id": "pair1",
        "config_hashes": {"annotation": "a" * 64, "reference": "placeholder",
                          "controller_config": "a" * 64},
        "versions": {"app": "0.2.0", "csp": "0.2.x", "ac": "1.16.4"},
        "started_at": "2026-09-07T15:30:00",
    }
    assert pyval.validate_data("session_manifest", doc) != []


# --- every runtime Lua file compiles under LuaJIT ----------------------------

RUNTIME_LUA = sorted(LUA_APP_DIR.rglob("*.lua"))


def test_runtime_lua_files_found():
    assert len(RUNTIME_LUA) >= 10
    assert any(p.name == "trace_rt.lua" for p in RUNTIME_LUA)


@pytest.mark.parametrize("path", RUNTIME_LUA, ids=lambda p: p.name)
def test_runtime_lua_compiles(lua, path):
    compile_fn = lua.eval(
        'function(src, name) local f, err = loadstring(src, name); '
        'return f ~= nil, err or "" end'
    )
    ok, err = compile_fn(path.read_text(encoding="utf-8"), path.name)
    assert ok, "{} does not compile: {}".format(path.name, err)


# --- apparatus drift across blocks (what "pinned at M3" enforces) ------------

def _manifest(block_id, ac="1.16.4", csp="0.2.3", track="ks_silverstone-national",
              length=2597.4, dev=False):
    m = {
        "schema_version": 1, "block_id": block_id, "participant_id": "P01",
        "session": 2, "condition": "adaptive", "pair_id": "pair1",
        "config_hashes": {"annotation": "a" * 64, "reference": "a" * 64,
                          "controller_config": "a" * 64},
        "versions": {"app": "0.2.0", "csp": csp, "ac": ac},
        "started_at": "2026-09-07T15:30:00",
        "track_id": track, "track_length_m": length,
    }
    if dev:
        m["dev_block"] = True
    return m


def test_matching_blocks_show_no_apparatus_drift():
    from trace_kit import integrity
    blocks = [("b1", _manifest("B1")), ("b2", _manifest("B2"))]
    assert integrity.check_apparatus_drift(blocks) == []


def test_a_csp_update_mid_study_is_reported():
    from trace_kit import integrity
    blocks = [("b1", _manifest("B1", csp="0.2.3")), ("b2", _manifest("B2", csp="0.2.4"))]
    problems = integrity.check_apparatus_drift(blocks)
    assert any("versions.csp differs" in p for p in problems)


def test_dev_blocks_do_not_trigger_drift():
    from trace_kit import integrity
    blocks = [("b1", _manifest("B1")), ("dev", _manifest("D1", ac="1.16.3", dev=True))]
    assert integrity.check_apparatus_drift(blocks) == []


def test_unknown_version_is_reported_as_unpinned():
    from trace_kit import integrity
    blocks = [("b1", _manifest("B1", ac="unknown (changelog.txt unreadable)")),
              ("b2", _manifest("B2", ac="unknown (changelog.txt unreadable)"))]
    problems = integrity.check_apparatus_drift(blocks)
    assert any("not pinned" in p for p in problems)


def test_disagreeing_track_length_on_one_track_is_reported():
    from trace_kit import integrity
    blocks = [("b1", _manifest("B1", length=2597.4)),
              ("b2", _manifest("B2", length=2601.0))]
    problems = integrity.check_apparatus_drift(blocks)
    assert any("track_length_m disagrees" in p for p in problems)


def test_different_tracks_may_have_different_lengths():
    from trace_kit import integrity
    blocks = [("b1", _manifest("B1", track="ks_silverstone-national", length=2597.4)),
              ("b2", _manifest("B2", track="ks_silverstone-international", length=2943.0))]
    assert integrity.check_apparatus_drift(blocks) == []


def test_pre_m3_blocks_without_versions_are_skipped_not_flagged():
    from trace_kit import integrity
    old = _manifest("OLD")
    del old["versions"]
    del old["track_length_m"]
    assert integrity.check_apparatus_drift([("b1", _manifest("B1")), ("old", old)]) == []


# --- AI-driven provenance (M3) ----------------------------------------------

def test_autopilot_block_records_that_the_ai_drove(lua):
    """Whether the AI drove is the most load-bearing fact about a reference
    block. The first real one could only be identified as AI-driven by noticing
    its lap times agreed to within one tick -- an inference, not provenance."""
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='REF1', participant_id='dev', session=2,
              condition='off', pair_id='pair1', dev_block=true,
              track_id='ks_silverstone-national', car_id='ks_bmw_m235i_racing',
              track_length_m=2600.26 },
            { annotation=h, reference=nil, controller_config=h },
            { app='0.2.0', csp='0.2.11', ac='1.16.4' },
            '2026-09-07T23:45:53')
          manifest.stamp_autopilot(m, 98.0)
          manifest.finalize(m, '2026-09-07T23:56:02', 12, {})
          return json.encode(m)
        end
        """
    )
    doc = json.loads(fn())
    assert doc["autopilot"] is True
    assert doc["ai_level_pct"] == pytest.approx(98.0)
    assert pyval.validate_data("session_manifest", doc) == []


def test_human_driven_block_carries_no_autopilot_key(lua):
    """Absent means human-driven; the field is never three-valued."""
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='B1', participant_id='P01', session=2,
              condition='adaptive', pair_id='pair1' },
            { annotation=h, reference=h, controller_config=h },
            { app='0.2.0', csp='0.2.11', ac='1.16.4' },
            '2026-09-07T15:30:00')
          return json.encode(m)
        end
        """
    )
    doc = json.loads(fn())
    assert "autopilot" not in doc
    assert "ai_level_pct" not in doc
    assert pyval.validate_data("session_manifest", doc) == []


def test_autopilot_key_cannot_be_false():
    doc = {
        "schema_version": 1, "block_id": "B1", "participant_id": "P01",
        "session": 2, "condition": "adaptive", "pair_id": "pair1",
        "config_hashes": {"annotation": "a" * 64, "reference": "a" * 64,
                          "controller_config": "a" * 64},
        "versions": {"app": "0.2.0", "csp": "0.2.11", "ac": "1.16.4"},
        "started_at": "2026-09-07T15:30:00", "autopilot": False,
    }
    assert pyval.validate_data("session_manifest", doc) != []
