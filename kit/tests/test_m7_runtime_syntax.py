"""Every shipped Lua file parses under LuaJIT 2.1.

A gap that was open until 2026-10-10: the `lib/` modules are all exercised
headlessly, but `trace_rt.lua` is the ac.*/io.* boundary and so is never loaded
by any test. A syntax error in it therefore showed up only in game — and in game
it shows up as CSP abandoning the rest of the frame's draw, which reads as a
half-blank window rather than as a parse error.

Parsing is not running: nothing here calls anything, and `trace_rt.lua` would
raise on its first `ac.*` call if it did. But a parse is most of the value for
the cheapest possible test, because the mistakes that actually happen while
editing a 1,900-line file are unbalanced `end`s, a stray `local` and a typo in a
long string — all of them parse errors.

LuaJIT 2.1 specifically, matching CSP. The repository's own rule: lupa's default
runtime is a newer Lua and does not match the game.
"""

import re
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_DIR = REPO_ROOT / "lua" / "trace_rt"

LUA_FILES = sorted(LUA_DIR.rglob("*.lua"))


def test_there_are_lua_files_to_check():
    """A glob that silently matches nothing is a test that silently passes."""
    names = {p.name for p in LUA_FILES}
    assert "trace_rt.lua" in names
    assert {"controller.lua", "evaluator.lua", "kr.lua", "markers.lua"} <= names


@pytest.fixture(scope="module")
def parse():
    """src -> None when it parses, the LuaJIT error message when it does not.

    The error string is returned rather than the chunk because `loadstring`
    returns `nil, err` on failure, and with `unpack_returned_tuples=True` that
    arrives in Python as a two-element tuple — which is truthy. Testing the
    chunk for truth therefore passes for every input, broken or not. The two
    self-checks below exist because this test was written that way first and
    was silently vacuous.
    """
    lua = LuaRuntime(unpack_returned_tuples=True)
    return lua.eval("""
        function(src, name)
          local chunk, err = loadstring(src, name)
          if chunk == nil then return err end
          return nil
        end
    """)


def test_the_parser_accepts_valid_lua(parse):
    assert parse("local a = 1 return a", "@ok") is None


def test_the_parser_rejects_broken_lua(parse):
    """Without this, a bug in the harness makes every check below vacuous."""
    err = parse("local a = 1 if a then return", "@broken")
    assert err is not None and "end" in err, err


@pytest.mark.parametrize("path", LUA_FILES, ids=lambda p: str(p.relative_to(LUA_DIR)))
def test_the_file_parses(parse, path):
    err = parse(path.read_text(encoding="utf-8"), "@" + path.name)
    assert err is None, "{} does not parse under LuaJIT 2.1: {}".format(path.name, err)


def test_no_lua_file_stores_a_function_in_a_table_literal():
    """The CSP runtime gotcha, as a crude but load-bearing grep.

    Confirmed in game at M0: a table holding a closure as a field and dispatched
    as `t.fn(...)` passes headless under LuaJIT and crashes in CSP with "attempt
    to call field 'check' (a number value)" — CSP hands the stored closure back
    as a number. Every module in this project is written with helpers called
    directly because of it, and CLAUDE.md says so, but nothing checked.

    The pattern caught is an INDENTED bare identifier assigned a function —
    `  check = function(...)` — which is what a table field looks like. The two
    legitimate shapes are not matched: `function M.foo(...)` (how every module
    here exports) and `local foo = function(...)` (the same thing as
    `local function foo`, called directly).
    """
    field_function = re.compile(r"^\s+[\w.\[\]\"']+\s*=\s*function\s*\(")
    offenders = []
    for path in LUA_FILES:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("--"):
                continue
            if field_function.match(line):
                offenders.append("{}:{}: {}".format(path.name, lineno, line.strip()))
    assert offenders == [], (
        "a function stored as a table field will be returned as a number by CSP "
        "in game; call helpers directly instead:\n" + "\n".join(offenders))


def test_the_table_closure_check_catches_the_m0_pattern(tmp_path):
    """The shape that actually crashed in game, so the grep above is not vacuous."""
    field_function = re.compile(r"^\s+[\w.\[\]\"']+\s*=\s*function\s*\(")
    assert field_function.match("    check = function(v) return v end,")
    assert field_function.match("\t\tvalidate = function(x)")
    # ...and the two legitimate shapes stay unmatched.
    assert not field_function.match("function M.plans(corners, reference, cfg)")
    assert not field_function.match("local function in_zone(spline, start, finish)")
    assert not field_function.match("local check = function(v) return v end")
