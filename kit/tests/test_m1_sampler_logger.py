"""M1 tests: the headless-testable half of the sampler + logger + manifest libs,
plus the offline integrity checker.

The Lua side runs the real runtime modules (lua/trace_rt/lib/*) through lupa
(LuaJIT 2.1), exactly as the M0 parity suite does, so headless behaviour mirrors
in-game behaviour. The integrity checker is pure Python and is exercised against
synthetic good/broken logs.
"""

import csv
import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

from trace_kit import validate as pyval
from trace_kit import integrity

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
TICKS_COLUMNS_TEXT = (REPO_ROOT / "configs" / "ticks_columns.json").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lua():
    rt = LuaRuntime(unpack_returned_tuples=True)
    rt.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return rt


# --- sampler: downsampling cadence ------------------------------------------

def test_sampler_cadence_20hz_at_60fps(lua):
    # 10 s of 60 fps frames at a 20 Hz tick rate -> ~200 ticks.
    fn = lua.eval(
        """
        function(rate, dt, frames)
          local sampler = require('lib/sampler')
          local s = sampler.new(rate)
          local total = 0
          for _ = 1, frames do total = total + sampler.tick(s, dt) end
          return total
        end
        """
    )
    total = fn(20, 1.0 / 60.0, 600)
    assert abs(total - 200) <= 1, total


def test_sampler_ignores_nonpositive_dt(lua):
    fn = lua.eval(
        """
        function()
          local sampler = require('lib/sampler')
          local s = sampler.new(20)
          return sampler.tick(s, 0) + sampler.tick(s, -0.1)
        end
        """
    )
    assert fn() == 0


def test_sampler_catchup_is_capped(lua):
    # A huge stall must not emit thousands of rows; the accumulator caps and resets.
    fn = lua.eval(
        """
        function()
          local sampler = require('lib/sampler')
          local s = sampler.new(20)
          local n = sampler.tick(s, 100.0)  -- would be 2000 ticks uncapped
          return n, s.acc
        end
        """
    )
    n, acc = fn()
    assert n == 8        # the cap in sampler.tick
    assert acc == 0.0    # backlog dropped, no permanent drift


# --- sampler: CSV serialisation against the real descriptor ------------------

def _expected_cell(col_type):
    return {"float": "1.500000", "int": "3", "bool": "1"}[col_type]


def test_sampler_header_and_row_match_descriptor(lua):
    fn = lua.eval(
        """
        function(text)
          local json = require('lib/json')
          local sampler = require('lib/sampler')
          local d = json.decode(text)
          local snap = {}
          for i = 1, #d.columns do
            local c = d.columns[i]
            if c.type == 'float' then snap[c.name] = 1.5
            elseif c.type == 'int' then snap[c.name] = 3
            elseif c.type == 'bool' then snap[c.name] = true end
          end
          return sampler.header(d), sampler.format_row(d, snap)
        end
        """
    )
    header, row = fn(TICKS_COLUMNS_TEXT)

    descriptor = json.loads(TICKS_COLUMNS_TEXT)
    cols = descriptor["columns"]
    assert header == ",".join(c["name"] for c in cols)
    assert row == ",".join(_expected_cell(c["type"]) for c in cols)


def test_sampler_row_missing_column_raises(lua):
    fn = lua.eval(
        """
        function(text)
          local json = require('lib/json')
          local sampler = require('lib/sampler')
          local d = json.decode(text)
          local ok = pcall(sampler.format_row, d, { t = 1.0 })  -- missing the rest
          return ok
        end
        """
    )
    ok = fn(TICKS_COLUMNS_TEXT)
    assert ok is False


# --- hash.to_hex normalisation ----------------------------------------------

def test_hash_to_hex_raw_bytes(lua):
    fn = lua.eval(
        """
        function()
          local hash = require('lib/hash')
          return hash.to_hex(string.rep('\\0', 32))  -- 32 zero bytes
        end
        """
    )
    assert fn() == "0" * 64


def test_hash_to_hex_passthrough_lowercases(lua):
    fn = lua.eval(
        """
        function()
          local hash = require('lib/hash')
          return hash.to_hex(string.rep('AB', 32))  -- already 64 hex chars
        end
        """
    )
    assert fn() == "ab" * 32


def test_hash_to_hex_bad_length_raises(lua):
    fn = lua.eval(
        """
        function()
          local hash = require('lib/hash')
          local ok = pcall(hash.to_hex, 'too-short')
          return ok
        end
        """
    )
    assert fn() is False


# --- dev_block + the annotation hash it may omit (M2 hard gate) --------------


def test_study_manifest_omits_dev_block(lua):
    # A participant block carries no dev_block key at all, so its presence is
    # enough to exclude a block from study data.
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='B1', participant_id='P01', session=2,
              condition='adaptive', pair_id='pairA' },
            { annotation=h, reference=h, controller_config=h },
            { app='0.1.0', csp='0.2.x', ac='unpinned' },
            '2026-06-13T15:30:00')
          return json.encode(m)
        end
        """
    )
    doc = json.loads(fn())
    assert "dev_block" not in doc
    assert pyval.validate_data("session_manifest", doc) == []


def test_dev_block_manifest_may_carry_a_null_annotation_hash(lua):
    # A dev block can start on an un-annotated track; it then has no annotation
    # to hash. The schema permits null there and nowhere else.
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='B1', participant_id='dev', session=2,
              condition='off', pair_id='scratch', dev_block=true },
            { annotation=nil, reference=h, controller_config=h },
            { app='0.1.0', csp='0.2.x', ac='unpinned' },
            '2026-06-13T15:30:00')
          return json.encode(m)
        end
        """
    )
    doc = json.loads(fn())
    assert doc["dev_block"] is True
    assert doc["config_hashes"]["annotation"] is None
    assert pyval.validate_data("session_manifest", doc) == []


def test_annotation_hash_must_be_a_real_hash_when_present():
    # Guards the regression this replaced: the hash has to be a genuine digest,
    # not a placeholder. (That it is the *per-track* file is enforced in
    # trace_rt.lua, which needs ac.* and so is checked in game.)
    doc = _valid_manifest()
    doc["config_hashes"]["annotation"] = "not-a-hash"
    assert pyval.validate_data("session_manifest", doc) != []


def test_dev_block_key_cannot_be_false():
    # Only ever present-and-true; a false key would be a third state to reason
    # about when filtering study data.
    doc = _valid_manifest()
    doc["dev_block"] = False
    assert pyval.validate_data("session_manifest", doc) != []


# --- manifest build -> json -> schema validity (cross-language) --------------

def test_manifest_build_and_finalize_validate(lua):
    fn = lua.eval(
        """
        function()
          local manifest = require('lib/manifest')
          local json = require('lib/json')
          local h = string.rep('a', 64)
          local m = manifest.build(
            { block_id='B1', participant_id='P01', session=2,
              condition='adaptive', pair_id='pairA', sequence='A' },
            { annotation=h, reference=h, controller_config=h },
            { app='0.1.0', csp='0.2.x', ac='unpinned' },
            '2026-06-13T15:30:00')
          local started = json.encode(m)
          manifest.finalize(m, '2026-06-13T16:00:00', 12, {})
          local finished = json.encode(m)
          return started, finished
        end
        """
    )
    started, finished = fn()

    started_doc = json.loads(started)
    finished_doc = json.loads(finished)
    assert pyval.validate_data("session_manifest", started_doc) == []
    assert pyval.validate_data("session_manifest", finished_doc) == []
    # finalize stamped the closing fields; empty faults stays absent.
    assert finished_doc["laps_completed"] == 12
    assert finished_doc["ended_at"] == "2026-06-13T16:00:00"
    assert "faults" not in finished_doc


# --- logger buffer + injected flush -----------------------------------------

def test_logger_serialize_and_flush(lua):
    fn = lua.eval(
        """
        function()
          local logger = require('lib/logger')
          local L = logger.new('a,b,c')
          logger.add(L, '1,2,3')
          logger.add(L, '4,5,6')
          local captured = {}
          local save = function(path, text)
            captured.path = path; captured.text = text; return true
          end
          local dirty_before = logger.dirty(L)
          local ok = logger.flush(L, 'out.csv', save)
          return captured.text, logger.count(L), ok, dirty_before, logger.dirty(L)
        end
        """
    )
    text, count, ok, dirty_before, dirty_after = fn()
    assert text == "a,b,c\n1,2,3\n4,5,6\n"
    assert count == 2
    assert ok is True
    assert dirty_before is True
    assert dirty_after is False


# --- integrity checker -------------------------------------------------------

COLUMNS = integrity.expected_columns()


def _valid_manifest(block_id="TEST", laps_completed=2):
    h = "a" * 64
    return {
        "schema_version": 1,
        "block_id": block_id,
        "participant_id": "P01",
        "session": 2,
        "condition": "adaptive",
        "pair_id": "pairA",
        "config_hashes": {"annotation": h, "reference": h, "controller_config": h},
        "versions": {"app": "0.1.0", "csp": "0.2.x", "ac": "unpinned"},
        "started_at": "2026-06-13T15:30:00",
        "ended_at": "2026-06-13T16:00:00",
        "laps_completed": laps_completed,
    }


def _row(t, lap):
    """One CSV row (list) in column order; only t and lap carry meaning here."""
    idx = {name: i for i, name in enumerate(COLUMNS)}
    row = ["0"] * len(COLUMNS)
    row[idx["t"]] = "{:.6f}".format(t)
    row[idx["lap"]] = str(lap)
    return row


def _write_block(tmp_path, manifest_dict, rows, header=None):
    block_id = manifest_dict["block_id"]
    mpath = tmp_path / "manifest_{}.json".format(block_id)
    mpath.write_text(json.dumps(manifest_dict), encoding="utf-8")
    tpath = tmp_path / "ticks_{}.csv".format(block_id)
    with open(tpath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header if header is not None else COLUMNS)
        w.writerows(rows)
    return mpath


def _laps_over(n_rows):
    """Rows spanning laps 0->2 across n_rows samples at 20 Hz."""
    rows = []
    for i in range(n_rows):
        lap = 0 if i < n_rows // 3 else (1 if i < 2 * n_rows // 3 else 2)
        rows.append(_row(i * 0.05, lap))
    return rows


def test_integrity_good_block_passes(tmp_path):
    # A ticks-only recording IS a dev block (no annotation, no reference, so no
    # corner passes and no controller). Stamped as one here so M4's "a
    # participant block with no evidence in it" check does not fire on a fixture
    # that is deliberately tick-only; kit/tests/test_m4_integrity.py covers that
    # check on its own terms.
    manifest = _valid_manifest(laps_completed=2)
    manifest["dev_block"] = True
    mpath = _write_block(tmp_path, manifest, _laps_over(60))
    problems, summary = integrity.check_block(mpath)
    assert problems == [], problems
    assert summary["row_count"] == 60
    assert summary["min_lap"] == 0 and summary["max_lap"] == 2


def test_integrity_gap_flagged(tmp_path):
    rows = _laps_over(60)
    # Shift everything from index 30 on by +1 s, opening a 1 s gap (> 0.5 s).
    for i in range(30, len(rows)):
        lap = rows[i][COLUMNS.index("lap")]
        rows[i] = _row(i * 0.05 + 1.0, int(lap))
    mpath = _write_block(tmp_path, _valid_manifest(laps_completed=2), rows)
    problems, _ = integrity.check_block(mpath)
    assert any("gap" in p for p in problems), problems


def test_integrity_lap_mismatch_flagged(tmp_path):
    rows = _laps_over(60)  # ticks span 2 laps
    mpath = _write_block(tmp_path, _valid_manifest(laps_completed=5), rows)  # manifest claims 5
    problems, _ = integrity.check_block(mpath)
    assert any("lap mismatch" in p for p in problems), problems


def test_integrity_bad_header_flagged(tmp_path):
    rows = _laps_over(10)
    mpath = _write_block(tmp_path, _valid_manifest(laps_completed=2), rows,
                         header=["wrong", "header"])
    problems, _ = integrity.check_block(mpath)
    assert any("header mismatch" in p for p in problems), problems


def test_integrity_lap_decrease_flagged(tmp_path):
    rows = [_row(i * 0.05, lap) for i, lap in enumerate([0, 1, 2, 1, 2])]
    mpath = _write_block(tmp_path, _valid_manifest(laps_completed=2), rows)
    problems, _ = integrity.check_block(mpath)
    assert any("lap decreased" in p for p in problems), problems
