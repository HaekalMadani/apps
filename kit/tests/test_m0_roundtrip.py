"""M0 exit test: configs round-trip through validation in both Lua and Python.

Both validators run over the same fixture corpus:
  - valid fixtures (configs/*.json, configs/examples/*.json) must PASS in both;
  - the broken corpus (configs/examples/invalid/*) must FAIL in both.

The Lua side is the real runtime code (lua/trace_rt/lib/validate.lua +
lib/json.lua) executed headlessly through lupa (LuaJIT). This corpus-agreement
pattern is the same mechanism the M4 golden-trace controller parity suite will
use.
"""

import json
from pathlib import Path

import jsonschema
import pytest

# CSP embeds LuaJIT (Lua 5.1 semantics) — use the matching runtime, not lupa's
# default (newest bundled Lua), so headless behaviour mirrors in-game behaviour.
from lupa.luajit21 import LuaRuntime

from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS = REPO_ROOT / "configs"
INVALID_DIR = CONFIGS / "examples" / "invalid"
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"

# (path, format) for every valid fixture.
VALID_FIXTURES = [
    (CONFIGS / "controller_config.json", "controller_config"),
    (CONFIGS / "ticks_columns.json", "ticks_columns"),
    (CONFIGS / "examples" / "annotation_example_track.json", "annotation"),
    (CONFIGS / "examples" / "reference_example_pair.json", "reference"),
]

# The committed study configs are regression fixtures too: they are the files
# the game actually loads, and they are hand-edited between recordings, so they
# must round-trip through BOTH validators exactly like the examples do.
VALID_FIXTURES += [(p, "annotation") for p in sorted((CONFIGS / "annotations").glob("annotation_*.json"))]
VALID_FIXTURES += [(p, "reference")
                   for p in sorted((CONFIGS / "references").glob("reference_*.json"))]

# Invalid corpus: format inferred from "<format>__bad_<reason>.json".
INVALID_FIXTURES = sorted(INVALID_DIR.glob("*__bad_*.json"))


def fixture_format(path):
    return path.name.split("__bad_")[0]


@pytest.fixture(scope="module")
def lua_check():
    """Returns check(format_name, json_text) -> (ok, first_error) using the Lua validators."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return lua.eval(
        """
        function(fmt, text)
          local json = require('lib/json')
          local validate = require('lib/validate')
          local parsed, decoded = pcall(json.decode, text)
          if not parsed then
            return false, 'JSON parse error: ' .. tostring(decoded)
          end
          local ok, errs = validate[fmt](decoded)
          return ok, errs[1] or ''
        end
        """
    )


# --- the schemas themselves are well-formed ---------------------------------

@pytest.mark.parametrize("format_name", sorted(pyval.FORMATS))
def test_schema_is_valid_draft7(format_name):
    jsonschema.Draft7Validator.check_schema(pyval.load_schema(format_name))


# --- valid fixtures pass on both sides ---------------------------------------

@pytest.mark.parametrize("path,format_name", VALID_FIXTURES, ids=lambda v: getattr(v, "name", v))
def test_valid_fixture_passes_python(path, format_name):
    errors = pyval.validate_file(path, format_name)
    assert errors == [], "expected PASS, got: {}".format(errors)


@pytest.mark.parametrize(
    "path,format_name",
    [(p, f) for p, f in VALID_FIXTURES if f in pyval.RUNTIME_INPUT_FORMATS],
    ids=lambda v: getattr(v, "name", v),
)
def test_valid_fixture_passes_lua(lua_check, path, format_name):
    ok, first_error = lua_check(format_name, path.read_text(encoding="utf-8"))
    assert ok, "expected PASS, got: {}".format(first_error)


# --- broken corpus rejected on both sides ------------------------------------

def test_invalid_corpus_exists():
    assert len(INVALID_FIXTURES) >= 10
    assert all(fixture_format(p) in pyval.RUNTIME_INPUT_FORMATS for p in INVALID_FIXTURES)


@pytest.mark.parametrize("path", INVALID_FIXTURES, ids=lambda p: p.name)
def test_invalid_fixture_fails_python(path):
    errors = pyval.validate_file(path, fixture_format(path))
    assert errors != [], "expected FAIL, but Python validation passed"


@pytest.mark.parametrize("path", INVALID_FIXTURES, ids=lambda p: p.name)
def test_invalid_fixture_fails_lua(lua_check, path):
    ok, _ = lua_check(fixture_format(path), path.read_text(encoding="utf-8"))
    assert not ok, "expected FAIL, but Lua validation passed"


# --- parity: both sides agree on every file ----------------------------------

@pytest.mark.parametrize(
    "path,format_name",
    [(p, f) for p, f in VALID_FIXTURES if f in pyval.RUNTIME_INPUT_FORMATS]
    + [(p, fixture_format(p)) for p in INVALID_FIXTURES],
    ids=lambda v: getattr(v, "name", v),
)
def test_lua_python_agree(lua_check, path, format_name):
    py_ok = pyval.validate_file(path, format_name) == []
    lua_ok, _ = lua_check(format_name, path.read_text(encoding="utf-8"))
    assert py_ok == bool(lua_ok), "Python={} Lua={} for {}".format(py_ok, lua_ok, path.name)
