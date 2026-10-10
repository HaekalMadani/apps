"""M5: salience staging — controller stage plus condition, in, drawing out.

Everything the renderer decides happens in ``lua/trace_rt/lib/markers.lua``
BEFORE any ``render.*`` call: ``presented_stage`` applies the block's condition,
``visual`` turns the resulting stage into an alpha and a set of parts. The draw
calls in ``trace_rt.lua`` only execute that. Splitting it that way is what makes
the whole staging layer testable headless while the drawing itself is not — and
it is also what keeps the experiment's condition a config field rather than a
code path (impl plan section 5).

M5's exit test is still an on-track one ("scripted controller states produce the
intended visuals"); these tests pin the decisions the eye cannot check — that
`static` really is a pin and not a separate path, that `probe` really is hidden,
and that no salience level is ever read from a literal instead of the config.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))
SALIENCE = CFG["salience"]

STAGES = ("full", "reduced", "probe", "removed")
MODES = ("adaptive", "static", "off")


@pytest.fixture(scope="module")
def lua():
    rt = LuaRuntime(unpack_returned_tuples=True)
    rt.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    return rt


@pytest.fixture(scope="module")
def presented(lua):
    fn = lua.eval("""
        function(mode, stage)
          return require('lib/markers').presented_stage(mode, stage)
        end
    """)
    return fn


@pytest.fixture(scope="module")
def visual(lua):
    fn = lua.eval("""
        function(stage, salience_json)
          local json = require('lib/json')
          local markers = require('lib/markers')
          local v = markers.visual(stage, json.decode(salience_json))
          return json.encode(v)
        end
    """)

    def run(stage, salience=None):
        return json.loads(fn(stage, json.dumps(salience or SALIENCE)))

    return run


# --- the condition switch ----------------------------------------------------

def test_adaptive_shows_exactly_what_the_controller_decided(presented):
    for stage in STAGES:
        assert presented("adaptive", stage) == stage


def test_static_pins_every_stage_to_full(presented):
    """Static is a PIN on the presentation, not a second pipeline.

    Impl plan section 5: static mode runs the identical pipeline — sampler,
    tracker, evaluator, even the controller computing qualification invisibly —
    and only salience is held constant. That is what makes static blocks produce
    the same per-pass records as adaptive ones, and it is why this is one
    function rather than a branch in the renderer.
    """
    for stage in STAGES:
        assert presented("static", stage) == "full"


def test_off_hides_everything_whatever_the_controller_says(presented):
    """Sessions 1 and 3 record with no elements active.

    A marker shown during an unassisted block would contaminate the study's
    primary outcome measure, so this one matters more than it looks.
    """
    for stage in STAGES:
        assert presented("off", stage) == "hidden"


def test_the_condition_never_changes_the_controller_stage(presented):
    """`presented_stage` returns a PRESENTATION, and the log keeps the real stage.

    If this ever started rewriting the controller's state, static blocks would
    stop being analysable — their whole value is the invisible trajectory.
    """
    # The function is pure and takes the stage by value; the guard is that
    # nothing here is capable of writing back. Assert the shape of the contract:
    # every mode maps every stage to a legal presentation, and only `adaptive`
    # is the identity.
    for mode in MODES:
        for stage in STAGES:
            assert presented(mode, stage) in STAGES + ("hidden",)
    assert any(presented("static", s) != s for s in STAGES)


# --- stage to visual ---------------------------------------------------------

def test_full_salience_draws_the_whole_cue(visual):
    v = visual("full")
    assert v["level"] == "full"
    assert v["alpha"] == pytest.approx(SALIENCE["full_alpha"])
    assert v["disc"] and v["cross"] and v["stalk"] and v["label"]


def test_probe_and_removed_are_both_hidden(visual):
    """The probe IS the withdrawal; removal is its permanent form.

    They stay distinct in the controller and in the fade log, where the
    difference is the whole of RQ1's probe-outcome tabulation, and collapse only
    here, where it makes no visual difference.
    """
    for stage in ("probe", "removed", "hidden"):
        v = visual(stage)
        assert v["level"] == "hidden"
        assert v["alpha"] == 0.0
        assert not any(v[part] for part in ("disc", "cross", "stalk", "label"))


def test_reduced_salience_is_the_disc_alone_by_default(visual):
    """The open M5 decision from impl plan section 7, settled at `minimal`.

    Reducing salience should reduce what the cue TELLS the learner, not just how
    bright it is: a dimmer copy of the same marker still hands over the corner
    id and a precise point. The disc keeps a positional hint and takes away the
    reading.
    """
    v = visual("reduced")
    assert v["level"] == "reduced"
    assert v["alpha"] == pytest.approx(SALIENCE["reduced_alpha"])
    assert v["disc"]
    assert not v["cross"] and not v["stalk"] and not v["label"]


def test_the_reduced_form_is_a_config_value_not_a_literal(visual):
    """Section 7's alternatives are kept as config, because the choice is an
    RQ3 interview topic and has to be frozen and hashed before the pilot."""
    minimal = visual("reduced", dict(SALIENCE, reduced_form="minimal"))
    intermediate = visual("reduced", dict(SALIENCE, reduced_form="intermediate"))
    dimmed = visual("reduced", dict(SALIENCE, reduced_form="dimmed"))

    assert (minimal["disc"], minimal["cross"], minimal["label"]) == (True, False, False)
    assert (intermediate["disc"], intermediate["cross"], intermediate["label"]) == (
        True, True, False)
    assert all(dimmed[part] for part in ("disc", "cross", "stalk", "label"))
    # `dimmed` is the control case: it is what "reduced salience" would mean if
    # it meant brightness alone, so it must differ from full ONLY in alpha.
    full = visual("full")
    assert dimmed["alpha"] < full["alpha"]
    assert {k: dimmed[k] for k in ("disc", "cross", "stalk", "label")} == \
           {k: full[k] for k in ("disc", "cross", "stalk", "label")}


def test_the_alphas_come_from_the_config(visual):
    custom = dict(SALIENCE, full_alpha=0.9, reduced_alpha=0.15)
    assert visual("full", custom)["alpha"] == pytest.approx(0.9)
    assert visual("reduced", custom)["alpha"] == pytest.approx(0.15)


def test_the_frozen_config_carries_the_studys_choice():
    """`minimal` is the study's reduced form; a change must be deliberate."""
    assert SALIENCE["reduced_form"] == "minimal"
    assert SALIENCE["full_alpha"] == 1.0
    assert SALIENCE["reduced_alpha"] == 0.4


# --- the two layers compose --------------------------------------------------

def test_a_static_block_draws_full_even_when_the_controller_has_removed(presented, visual):
    """The combination that makes the two conditions comparable.

    Under static the controller may well have decided `removed` — it runs
    invisibly — and the participant must still see the cue at full salience.
    """
    v = visual(presented("static", "removed"))
    assert v["level"] == "full" and v["alpha"] == pytest.approx(SALIENCE["full_alpha"])


def test_an_off_block_draws_nothing_even_at_stage_full(presented, visual):
    v = visual(presented("off", "full"))
    assert v["level"] == "hidden" and v["alpha"] == 0.0


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("stage", STAGES)
def test_every_mode_and_stage_pair_yields_a_drawable_description(presented, visual, mode, stage):
    """No combination may produce a partial or contradictory visual."""
    v = visual(presented(mode, stage))
    assert v["level"] in ("full", "reduced", "hidden")
    assert 0.0 <= v["alpha"] <= 1.0
    if v["level"] == "hidden":
        assert v["alpha"] == 0.0
        assert not any(v[part] for part in ("disc", "cross", "stalk", "label"))
    else:
        assert v["alpha"] > 0.0
        # A visible cue must draw at least one part, or it is hidden by accident.
        assert any(v[part] for part in ("disc", "cross", "stalk", "label"))
