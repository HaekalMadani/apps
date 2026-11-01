"""Bandwidth knowledge of results — the terminal error signal (lib/kr.lua).

Added 2026-10-10 in response to the literature review's central finding: TRACE's
three elements are prescriptive *concurrent guidance* and the system delivered no
*knowledge of results* at all — no terminal, signed, per-corner statement of how
far off the attempt was. The tolerance bands were modelled on bandwidth KR
(Sherwood 1988; Lee & Carnahan 1990), a paradigm whose whole mechanism is that
the learner receives quantitative error when outside the band and silence inside
it. TRACE had the band and never fired the signal.

What these tests are really protecting, in order of how much it would cost to get
wrong:

* **The probe stays a retention test.** An element's KR is withdrawn exactly when
  that element is hidden — probe, removed, and the `off` condition of sessions 1
  and 3. KR running during a probe would make the probe measure
  performance-with-feedback, which is not what the project claims it measures.
* **The message and the criterion cannot disagree.** Both read the same band out
  of ``lib/evaluator``, so a message can never describe a tolerance the fading
  decision did not apply. The last test here pins that against the real
  committed reference table.
* **Silence is distinguishable from absence.** Four different silences (inside
  the band, withdrawn, unmeasured, capped) are logged as different outcomes,
  because the section 0A diagnostic is entirely a question about which silence
  happened.
* **KR is not a fourth element.** It does not fade, it is identical in both
  conditions, and nothing in it feeds the controller — so the golden-trace
  parity corpus is untouched by it.
"""

import json
from pathlib import Path

import pytest
from lupa.luajit21 import LuaRuntime

REPO_ROOT = Path(__file__).resolve().parents[2]
LUA_APP_DIR = REPO_ROOT / "lua" / "trace_rt"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))

ELEMENTS = ("braking", "corner_speed", "apex")

# The three bands these tests probe around. With the sigmas in `corner_ref`
# every band is floor-set, so the band IS the configured floor -- and taking it
# from the config rather than writing it out is what stops these tests breaking
# on a recalibration that has nothing to do with KR. They did break that way at
# frozen-g1b (2026-10-15): the braking band went 5 m -> 12 m, and probes written
# as "14.2 m, which is outside the band" quietly became inside it, so the tests
# were asserting delivery of a message the apparatus is required NOT to send.
BAND_BRAKING = CFG["band_floors"]["braking_m"]
BAND_SPEED = CFG["band_floors"]["corner_speed_kmh"]
BAND_APEX = CFG["band_floors"]["apex_m"]

# A magnitude comfortably outside a band, and one comfortably inside it. Both
# scale with the band so the SHAPE under test (outside speaks, inside is
# silent) is what is asserted, never a particular number of metres.
def outside(band):
    return round(band * 2.0 + 0.2, 3)


def inside(band):
    return round(band * 0.6, 3)


def corner_ref(mean_kmh=90.0, mean_rms_m=0.20, braking=True):
    """One reference row, with sigmas small enough that every band is floor-set.

    Floor-set is not a convenience here: all 27 bands on the real reference
    tables are floor-set at `frozen-g1`, which is asserted as an exact count in
    test_m4_evaluator.py. These tests inherit that regime deliberately.
    """
    row = {
        "corner_id": "3", "source": "ai",
        "contributing_laps": {"clean_passes": 12, "apex": 12, "corner_speed": 12},
        "apex": {"gates": [{"world_pos": [0, 0, 0], "spline_pos": 0.5,
                            "line": [{"spline_pos": 0.49, "world_pos": [0, 0, 0]},
                                     {"spline_pos": 0.51, "world_pos": [1, 0, 0]}]}],
                 "mean_rms_m": mean_rms_m, "sigma_ref_m": 0.01},
        "corner_speed": {"mean_kmh": mean_kmh, "sigma_ref_kmh": 0.3},
    }
    if braking:
        row["braking"] = {"world_pos": [0, 0, 0], "spline_pos": 0.4,
                          "mean_distance_m": 0.0, "sigma_ref_m": 0.6}
    return row


@pytest.fixture(scope="module")
def run_kr():
    """evaluate(metrics, levels=..., cfg=..., ref=...) -> lib/kr's output as dicts.

    Runs the real runtime Lua through LuaJIT 2.1 (matching CSP), and goes through
    lib/evaluator first, exactly as trace_rt.lua does — so the bands the KR
    decision uses are the bands the criterion used, not bands the test invented.
    """
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval("""
        function(cfg_json, ref_json, metrics_json, levels_json)
          local json = require('lib/json')
          local evaluator = require('lib/evaluator')
          local kr = require('lib/kr')
          local cfg = json.decode(cfg_json)
          local ref = json.decode(ref_json)
          local metrics = json.decode(metrics_json)
          local levels = levels_json ~= nil and json.decode(levels_json) or nil
          local evaluation = evaluator.evaluate(cfg, ref, metrics, {})
          local out = kr.evaluate(cfg, ref, metrics, evaluation, levels)
          -- json.encode drops an empty table's arrayness, so the count travels
          -- separately rather than being inferred on the far side.
          return json.encode({ outcomes = out.outcomes, delivered = out.delivered,
                               n = #out.delivered })
        end
    """)

    def evaluate(metrics, levels=None, cfg=None, ref=None):
        raw = fn(json.dumps(cfg or CFG), json.dumps(ref if ref is not None else corner_ref()),
                 json.dumps(metrics), json.dumps(levels) if levels is not None else None)
        out = json.loads(raw)
        if out["n"] == 0:
            out["delivered"] = []
        return out

    return evaluate


def metrics(brake=None, speed=None, apex=None):
    """A closed pass's metrics. Any field left out is a null metric — no evidence."""
    out = {}
    if brake is not None:
        out["brake_initiation_distance_m"] = brake
    if speed is not None:
        out["min_corner_speed_kmh"] = speed
    if apex is not None:
        out["apex_rms_m"] = apex
    return out


def with_criteria(**overrides):
    """The real config with `criteria` fields overridden -- the gate's shape."""
    cfg = json.loads(json.dumps(CFG))
    cfg["criteria"].update(overrides)
    return cfg


def with_kr(**overrides):
    cfg = json.loads(json.dumps(CFG))
    cfg["kr"].update(overrides)
    return cfg


# --- rule 2: bandwidth delivery ---------------------------------------------

def test_outside_the_band_delivers_a_signed_message(run_kr):
    """The headline case: braked early, told how far early.

    `+` is EARLIER in this project's sign convention (passes.schema.json), which
    is the direction the measured novice bias runs in — 89% of the researcher's
    passes against the 100% reference, median +14.9 m.
    """
    error = outside(BAND_BRAKING)
    out = run_kr(metrics(brake=error))
    assert out["n"] == 1
    sent = out["delivered"][0]
    assert sent["element"] == "braking"
    assert sent["label"] == "BRAKE 3"
    assert sent["text"] == "BRAKED {:.0f} m early".format(error)
    assert sent["band"] == pytest.approx(BAND_BRAKING)
    assert out["outcomes"]["braking"]["outcome"] == "delivered"
    assert out["outcomes"]["braking"]["text"] == sent["text"]


def test_braking_late_is_reported_as_late(run_kr):
    """The sign is the point. An unsigned magnitude cannot be acted on."""
    error = outside(BAND_BRAKING)
    out = run_kr(metrics(brake=-error))
    assert out["delivered"][0]["text"] == "BRAKED {:.0f} m late".format(error)


def test_inside_the_band_is_silent_and_the_silence_is_logged(run_kr):
    """Bandwidth KR's actual mechanism: inside the band, saying nothing IS the
    message ("correct enough"). But the log must still record that we were
    silent *because the pass was good*, which is a different fact from the three
    other silences."""
    error = inside(BAND_BRAKING)
    out = run_kr(metrics(brake=error))
    assert out["n"] == 0
    entry = out["outcomes"]["braking"]
    assert entry["outcome"] == "inside_band"
    # The error is recorded even when nothing was said, so the CE/VE
    # decomposition can be computed over every pass rather than only the ones
    # that spoke.
    assert entry["error_value"] == pytest.approx(error)
    assert entry["band"] == pytest.approx(BAND_BRAKING)


def test_exactly_on_the_band_edge_is_inside(run_kr):
    """`<=` in the evaluator, so `>` here. The two must agree on the boundary or
    a pass could fail its criterion and be told it was fine."""
    out = run_kr(metrics(brake=BAND_BRAKING))
    assert out["outcomes"]["braking"]["outcome"] == "inside_band"
    out = run_kr(metrics(brake=BAND_BRAKING + 0.001))
    assert out["outcomes"]["braking"]["outcome"] == "delivered"


# --- rule 4: withdrawn with the scaffold, never with the measurement --------

@pytest.mark.parametrize("level", ["hidden"])
def test_kr_is_withdrawn_while_the_element_is_hidden(run_kr, level):
    """The most consequential test in this file.

    `probe` and `removed` both map to the hidden LEVEL (lib/markers.level_of),
    as does the `off` condition. The probe stage is this project's retention
    test; a retention test with KR still firing measures
    performance-with-feedback instead (Winstein & Schmidt 1990).
    """
    out = run_kr(metrics(brake=14.2), levels={"braking": level,
                                              "corner_speed": "full", "apex": "full"})
    assert out["n"] == 0
    assert out["outcomes"]["braking"]["outcome"] == "withdrawn"


def test_withdrawal_is_per_element_not_per_block(run_kr):
    """Braking in probe must not silence the corner-speed message. The three
    elements fade on independent trajectories, and so does their KR."""
    out = run_kr(metrics(brake=14.2, speed=78.0),
                 levels={"braking": "hidden", "corner_speed": "full", "apex": "full"})
    assert out["outcomes"]["braking"]["outcome"] == "withdrawn"
    assert out["n"] == 1
    assert out["delivered"][0]["element"] == "corner_speed"
    assert out["delivered"][0]["text"] == "CARRIED 12 km/h slow"


def test_reduced_salience_does_not_change_the_message(run_kr):
    """Rule 5: KR does not fade. At `reduced` the cue drops parts of itself; the
    error message is identical. Making KR fade too would add a second fading
    channel and the manipulation would stop being the one the study claims."""
    full = run_kr(metrics(brake=14.2), levels={"braking": "full",
                                               "corner_speed": "full", "apex": "full"})
    reduced = run_kr(metrics(brake=14.2), levels={"braking": "reduced",
                                                  "corner_speed": "full", "apex": "full"})
    assert full["delivered"] == reduced["delivered"]


def test_levels_omitted_means_visible(run_kr):
    """trace_rt always passes levels; a nil must not silently withdraw
    everything, because that failure mode is invisible (no message is also the
    normal case)."""
    out = run_kr(metrics(brake=14.2), levels=None)
    assert out["n"] == 1


# --- rule 7: a null metric produces no message ------------------------------

def test_a_null_metric_produces_no_message(run_kr):
    """Same rule as the controller's: no measurable metric is NO EVIDENCE.
    Inventing a number would be a fabrication, and "no reading" would tell the
    learner about an annotation-zone fit problem rather than their driving."""
    out = run_kr(metrics(speed=90.0, apex=0.2))
    assert out["outcomes"]["braking"]["outcome"] == "not_measured"
    assert "error_value" not in out["outcomes"]["braking"]


def test_a_corner_with_no_braking_zone_is_not_measured(run_kr):
    """A corner taken flat has no braking reference, so there is no band and no
    message — the same exclusion the braking element's quorum denominator
    applies."""
    out = run_kr(metrics(brake=14.2), ref=corner_ref(braking=False))
    assert out["outcomes"]["braking"]["outcome"] == "not_measured"


# --- rule 6: priority order and the message cap -----------------------------

def test_the_cap_holds_and_the_loser_is_logged_capped(run_kr):
    """With all three outside their bands and max_messages = 1, braking wins and
    the other two are logged `capped` — outside the band, but it lost the
    priority order. Distinguishing that from `inside_band` is what stops a
    capped element reading as a competent one."""
    out = run_kr(metrics(brake=14.2, speed=70.0, apex=3.0))
    assert out["n"] == 1
    assert out["delivered"][0]["element"] == "braking"
    assert out["outcomes"]["corner_speed"]["outcome"] == "capped"
    assert out["outcomes"]["apex"]["outcome"] == "capped"
    # The error is still recorded for a capped element: it was measured and
    # judged, it just was not spoken.
    assert out["outcomes"]["apex"]["error_value"] is not None


def test_priority_order_is_the_config_array_order(run_kr):
    """`kr.elements` is an ordered priority list, so reordering it reorders
    delivery. The committed order is the corner's causal chain (brake point ->
    entry speed -> line through the apex), so the message names the cause rather
    than its consequence."""
    cfg = with_kr(elements=["apex", "corner_speed", "braking"])
    out = run_kr(metrics(brake=14.2, speed=70.0, apex=3.0), cfg=cfg)
    assert out["delivered"][0]["element"] == "apex"
    assert out["outcomes"]["braking"]["outcome"] == "capped"


def test_raising_the_cap_delivers_several_in_priority_order(run_kr):
    out = run_kr(metrics(brake=14.2, speed=70.0, apex=3.0), cfg=with_kr(max_messages=3))
    assert [m["element"] for m in out["delivered"]] == ["braking", "corner_speed", "apex"]


def test_an_element_left_out_of_the_list_is_off(run_kr):
    """The braking-only diagnostic variant. `off` is a distinct outcome from
    `inside_band`: the element was never considered, not judged and passed."""
    out = run_kr(metrics(brake=14.2, speed=70.0, apex=3.0), cfg=with_kr(elements=["braking"]))
    assert out["n"] == 1
    assert out["outcomes"]["corner_speed"]["outcome"] == "off"
    assert out["outcomes"]["apex"]["outcome"] == "off"


def test_disabling_kr_silences_everything_and_says_so(run_kr):
    out = run_kr(metrics(brake=14.2, speed=70.0, apex=3.0), cfg=with_kr(enabled=False))
    assert out["n"] == 0
    assert all(out["outcomes"][e]["outcome"] == "off" for e in ELEMENTS)


def test_every_element_always_has_an_outcome(run_kr):
    """Whatever `kr.elements` holds, the pass record carries all three. A missing
    key would be a third kind of silence that no reader is looking for."""
    out = run_kr(metrics(), cfg=with_kr(elements=[]))
    assert sorted(out["outcomes"]) == sorted(ELEMENTS)


# --- the three metrics' messages --------------------------------------------

def test_corner_speed_message_is_signed_in_km_h(run_kr):
    error = outside(BAND_SPEED)
    slow = run_kr(metrics(speed=90.0 - error))
    assert slow["delivered"][0]["text"] == "CARRIED {:.0f} km/h slow".format(error)
    # The fast wording exists only for the `two_sided` gate -- under the default
    # `slow_only` a fast pass is inside the band and says nothing (below).
    fast = run_kr(metrics(speed=90.0 + error),
                  cfg=with_criteria(corner_speed_gate="two_sided"))
    assert fast["delivered"][0]["text"] == "CARRIED {:.0f} km/h fast".format(error)


def test_apex_message_is_the_excess_over_the_references_own_rms(run_kr):
    """The apex criterion is one-sided against `mean_rms_m + band`, so the
    quantity to report is the excess over what the reference itself managed —
    the same number the criterion gates on, not the raw RMS."""
    excess = outside(BAND_APEX)
    out = run_kr(metrics(apex=0.20 + excess), ref=corner_ref(mean_rms_m=0.20))
    # The excess over the reference's own RMS, against the configured apex floor.
    assert out["delivered"][0]["text"] == "RAN {:.1f} m off line".format(excess)
    assert out["delivered"][0]["error_value"] == pytest.approx(excess)


def test_apex_is_one_sided_so_beating_the_reference_is_never_an_error(run_kr):
    """Driving closer to the expert line than the AI did is not a mistake, and
    telling a learner it was would be actively wrong."""
    out = run_kr(metrics(apex=0.05), ref=corner_ref(mean_rms_m=0.20))
    assert out["n"] == 0
    assert out["outcomes"]["apex"]["outcome"] == "inside_band"
    assert out["outcomes"]["apex"]["error_value"] == pytest.approx(-0.15)


def test_a_pass_faster_than_the_reference_is_told_nothing(run_kr):
    """KR has to mirror the criterion's SHAPE, not just its band.

    The gate stopped failing the fast side on 2026-10-14, and under bandwidth KR
    the silence inside the band is itself a message -- so if the criterion passes
    a fast pass and KR still announces an error on it, the apparatus tells the
    participant they were wrong about a pass it has just recorded as right. The
    outcome is `inside_band`, which is the same silence an exactly-on-target pass
    gets, and that is the intended claim: beating the reference is not an error.
    """
    out = run_kr(metrics(speed=90.0 + 4.5))
    assert out["outcomes"]["corner_speed"]["outcome"] == "inside_band"
    assert out["n"] == 0


def test_the_two_sided_gate_still_speaks_on_the_fast_side(run_kr):
    """The comparison case keeps working, from the one config field."""
    out = run_kr(metrics(speed=90.0 + outside(BAND_SPEED)),
                 cfg=with_criteria(corner_speed_gate="two_sided"))
    assert out["outcomes"]["corner_speed"]["outcome"] == "delivered"


# --- the band the message quotes is the band the criterion applied ----------

def test_the_message_band_is_the_evaluators_band(run_kr):
    """The guarantee that makes KR honest: the tolerance the learner is told
    about and the tolerance the fading decision used are the same number,
    resolved once by lib/evaluator. Checked here through a sigma large enough to
    beat the floor, so the test would fail if lib/kr quoted a floor while the
    evaluator used sigma x EVM."""
    ref = corner_ref()
    ref["braking"]["sigma_ref_m"] = 4.0          # 4.0 x EVM_AI 3.0 = 12.0 m band
    out = run_kr(metrics(brake=13.0), ref=ref)
    assert out["delivered"][0]["band"] == pytest.approx(12.0)
    # ...and a 10 m error is now inside that band, where at the 5 m floor it
    # would have spoken.
    inside = run_kr(metrics(brake=10.0), ref=ref)
    assert inside["outcomes"]["braking"]["outcome"] == "inside_band"


def test_the_consistency_gate_is_deliberately_not_reported(run_kr):
    """The braking criterion is accuracy AND consistency, but KR reports only
    accuracy. "You were 3 m from your own rolling mean" is a statement about the
    learner's recent passes, not knowledge of results about this corner — and it
    would make a learner who is consistently 15 m early hear two different
    things about one pass."""
    out = run_kr(metrics(brake=3.0))
    assert out["n"] == 0
    assert out["outcomes"]["braking"]["outcome"] == "inside_band"


# --- the real reference table ----------------------------------------------

def test_kr_fires_on_the_committed_reference_at_the_no_kr_baseline_bias(run_kr):
    """The diagnostic's precondition: KR must fire at the bias it starts from.

    **Changed at frozen-g1b (2026-10-15), and the change is a FINDING.** This
    test used to assert that KR speaks at **+8.1 m** — the bias measured over
    162 human passes against the 85% table. At a 5 m braking band it did. At the
    frozen-g1b band of 12 m, **+8.1 m is inside the band and KR says nothing
    about it.**

    So widening the braking floor to make the criterion reachable also silences
    the error signal for errors under 12 m, which includes the measured mean
    bias. KR now fires only on grosser errors. That is a real cost of the
    recalibration and belongs in the limitations beside the band itself: the
    learner is told about an error only when it exceeds a tolerance that is now
    more than two car lengths of braking distance.

    What the diagnostic still has to work with is the **no-KR baseline** bias of
    **+15.06 m** (block `m5_tst_...20260909_003201`, 28 braking passes, CE
    +15.06 m / VE 4.68 m), which is outside a 12 m band and does speak. That is
    what this now pins -- the diagnostic begins from the untreated bias, not
    from the post-re-reference one.
    """
    table = json.loads(
        (REPO_ROOT / "configs" / "references" / "reference_pair1.json").read_text("utf-8"))
    baseline_bias = 15.06
    measured_bias = 8.1
    assert baseline_bias > BAND_BRAKING, (
        "the no-KR baseline bias is inside the braking band, so bandwidth KR "
        "would be silent on the very error the section 0A diagnostic exists to "
        "detect -- at that point the braking floor is too wide to study")
    spoke = 0
    for row in table["corners"]:
        if "braking" not in row:
            continue
        out = run_kr(metrics(brake=baseline_bias), ref=row)
        assert out["outcomes"]["braking"]["outcome"] == "delivered", row["corner_id"]
        assert out["delivered"][0]["text"] == "BRAKED 15 m early"
        # The cost, asserted so it cannot be forgotten: the post-re-reference
        # bias the thesis quotes is now INSIDE the band and draws silence.
        quiet = run_kr(metrics(brake=measured_bias), ref=row)
        assert quiet["outcomes"]["braking"]["outcome"] == "inside_band"
        assert quiet["n"] == 0
        spoke += 1
    assert spoke >= 4, "pair 1 has 4 corners, all with braking (M3 decision)"


# --- the stage -> level -> kr chain -----------------------------------------
#
# lib/kr suppresses on the salience LEVEL; the integrity checker's clause keys
# on the recorded STAGE name; trace_rt joins the two through
# markers.level_of(presented_stage(element)). A drift between those two mappings
# would open exactly the hole the integrity clause exists to close, silently, so
# the whole chain is pinned here rather than each half separately.

@pytest.fixture(scope="module")
def run_chain():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = "{}/?.lua;" .. package.path'.format(LUA_APP_DIR.as_posix()))
    fn = lua.eval("""
        function(cfg_json, ref_json, metrics_json, mode, stage)
          local json = require('lib/json')
          local evaluator = require('lib/evaluator')
          local markers = require('lib/markers')
          local kr = require('lib/kr')
          local cfg = json.decode(cfg_json)
          local ref = json.decode(ref_json)
          local metrics = json.decode(metrics_json)
          -- Exactly trace_rt.lua's presented_levels(), for one element.
          local presented = markers.presented_stage(mode, stage)
          local levels = { braking = markers.level_of(presented),
                           corner_speed = 'full', apex = 'full' }
          local evaluation = evaluator.evaluate(cfg, ref, metrics, {})
          local out = kr.evaluate(cfg, ref, metrics, evaluation, levels)
          return json.encode({ outcome = out.outcomes.braking.outcome,
                               level = levels.braking, n = #out.delivered })
        end
    """)

    def chain(mode, stage, brake=14.2):
        return json.loads(fn(json.dumps(CFG), json.dumps(corner_ref()),
                             json.dumps(metrics(brake=brake)), mode, stage))

    return chain


@pytest.mark.parametrize("mode,stage,expected", [
    # Adaptive: the controller's stage decides, and probe/removed are hidden.
    ("adaptive", "full", "delivered"),
    ("adaptive", "reduced", "delivered"),
    ("adaptive", "probe", "withdrawn"),
    ("adaptive", "removed", "withdrawn"),
    # Static pins every element at full, so KR runs throughout whatever stage
    # the controller has reached underneath. That is what keeps the only
    # difference between conditions "whether the guidance elements fade".
    ("static", "full", "delivered"),
    ("static", "probe", "delivered"),
    ("static", "removed", "delivered"),
    # Off shows nothing, so it tells nothing: sessions 1 and 3 measure
    # unassisted performance, and an error signal is assistance.
    ("off", "full", "withdrawn"),
    ("off", "probe", "withdrawn"),
])
def test_condition_and_stage_decide_suppression_together(run_chain, mode, stage, expected):
    out = run_chain(mode, stage)
    assert out["outcome"] == expected, out
    assert out["n"] == (1 if expected == "delivered" else 0)


# --- rule 3: the message is a report, never an instruction -------------------

@pytest.mark.parametrize("m,expected_verb", [
    (dict(brake=outside(BAND_BRAKING)), "BRAKED"),
    (dict(brake=-outside(BAND_BRAKING)), "BRAKED"),
    (dict(speed=90.0 - outside(BAND_SPEED)), "CARRIED"),
    (dict(apex=0.20 + outside(BAND_APEX)), "RAN"),
])
def test_every_message_opens_with_a_past_tense_verb(run_kr, m, expected_verb):
    """Found in game by the KRtest block, 2026-10-14, and it is not cosmetic.

    The text was a bare magnitude ("6 m early") under a label in the imperative
    ("BRAKE 2"), and the first person to read it at speed took the pair as an
    instruction to brake six metres EARLIER -- the exact inverse of what it
    reports. A bandwidth-KR manipulation a participant may read with the sign
    flipped measures nothing, so the tense is part of the instrument: the
    message is knowledge of RESULTS about a corner already behind the car, not
    guidance for the one ahead.

    Pinned per element rather than on braking alone, because mixed tense inside
    one channel would be worse than the original: a participant who learns that
    "BRAKED ..." is a report would still have to guess at "... off line".
    """
    # Only the element under test has a measurable metric, so max_messages = 1
    # cannot hand the channel to a different element and pass this vacuously.
    out = run_kr(metrics(**m))
    assert out["n"] == 1, out
    assert out["delivered"][0]["text"].split()[0] == expected_verb, out["delivered"][0]


# --- rule 8: a clamped measurement is a floor, and floors are not spoken -----

def test_a_clamped_braking_metric_is_logged_but_never_said(run_kr):
    """The KRtest fault (2026-10-14), as a rule.

    A brake initiation clamped to its zone's opening means "at least 83 m
    early". The magnitude is the annotation's geometry talking, not the
    driver's, and bandwidth KR must not report a quantity the apparatus did not
    measure. The number is still logged, because the floor is a real lower bound
    and the diagnostic wants to count these.
    """
    floor_error = 82.6          # the KRtest block's own figure
    out = run_kr(dict(metrics(brake=floor_error), brake_initiation_clamped=True))
    entry = out["outcomes"]["braking"]
    assert entry["outcome"] == "clamped"
    assert entry["error_value"] == pytest.approx(floor_error)
    assert entry["band"] == pytest.approx(BAND_BRAKING)
    assert "text" not in entry
    assert out["n"] == 0


def test_the_same_error_unclamped_is_said(run_kr):
    """The control for the test above: nothing but the flag differs."""
    out = run_kr(metrics(brake=82.6))
    assert out["outcomes"]["braking"]["outcome"] == "delivered"
    assert out["delivered"][0]["text"] == "BRAKED 83 m early"


def test_a_clamped_element_passes_the_channel_on(run_kr):
    """Exactly as a null metric does (rule 7), and for the same reason.

    With `max_messages` 1 and braking first in the priority order, a braking
    message normally monopolises the channel. A clamped braking reading is not a
    message, so corner speed should get the slot rather than the pass falling
    silent -- otherwise one badly fitted braking zone would silence the other
    two elements for the whole block.
    """
    out = run_kr(dict(metrics(brake=82.6, speed=78.0), brake_initiation_clamped=True))
    assert out["outcomes"]["braking"]["outcome"] == "clamped"
    assert out["n"] == 1
    assert out["delivered"][0]["element"] == "corner_speed"
    assert out["delivered"][0]["text"] == "CARRIED 12 km/h slow"


def test_withdrawal_still_beats_a_clamp(run_kr):
    """Rule 4 is checked before the metric, so a hidden element reads `withdrawn`.

    `withdrawn` is the more informative outcome: the probe-suppression guarantee
    is checked from these outcomes, and an element that logged `clamped` while
    hidden would read to trace_kit.integrity as an element that was never
    withdrawn at all.
    """
    out = run_kr(dict(metrics(brake=82.6), brake_initiation_clamped=True),
                 levels={"braking": "hidden", "corner_speed": "full", "apex": "full"})
    assert out["outcomes"]["braking"]["outcome"] == "withdrawn"


def test_only_braking_can_be_clamped(run_kr):
    """The flag is a property of the brake-initiation search bracket alone.

    A corner-speed window or an apex window a pass did not cover yields a NULL,
    which is already rule 7's case. Nothing should make an unrelated element
    read `clamped`.
    """
    out = run_kr(dict(metrics(brake=outside(BAND_BRAKING),
                              speed=90.0 - outside(BAND_SPEED),
                              apex=0.20 + outside(BAND_APEX)),
                      brake_initiation_clamped=True))
    assert out["outcomes"]["braking"]["outcome"] == "clamped"
    assert out["outcomes"]["corner_speed"]["outcome"] == "delivered"
    assert out["outcomes"]["apex"]["outcome"] == "capped"
