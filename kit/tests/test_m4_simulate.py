"""M4: the Phase 1 simulator, and the committed Gate G1 result.

Two jobs. The first is ordinary regression cover on ``trace_kit.simulate`` — the
learner model, the target arithmetic, determinism. The second matters more: the
committed ``configs/simulation/simulation_report.json`` records that Gate G1 was
met, and like the Gate G0 clauses before it, that claim is re-asserted here on
every run rather than trusted to a console message from the day it was produced.

Simulations run at small stream counts for speed; the G1 verdict itself is
re-checked against the committed report rather than re-simulated at full size.
"""

import json
from pathlib import Path

import pytest

from trace_kit import simulate as sim
from trace_kit.controller import ELEMENTS

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_DIR = REPO_ROOT / "configs" / "simulation"
CFG = json.loads((REPO_ROOT / "configs" / "controller_config.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def references():
    return sim.load_references()


# --- the committed Gate G1 result -------------------------------------------

@pytest.fixture(scope="module")
def report():
    return json.loads((SIM_DIR / "simulation_report.json").read_text(encoding="utf-8"))


def test_the_committed_simulation_report_records_gate_g1_as_met(report):
    """G1's verdict, asserted from the repository rather than from memory.

    **Targets 2 and 3 were RESTATED on 2026-10-15 and the gate is MET again.**
    They had been zero-tolerance clauses -- a non-improver must leave full
    salience in exactly 0.000 of streams, broad regression must be answered by
    removal in exactly 0.000 -- and both were satisfied only by the `frozen-g1`
    floors, which satisfied them by never fading anything for anyone. On real
    recorded passes at those floors the braking and apex elements never advanced
    in a single block (`kit/tools/README.md` section `feasible.py`). A
    conservatism target is trivially met by a system that never acts, so neither
    clause could judge a working configuration.

    They are now stated rates with the counter-rate reported, per
    `simulate.TARGET_RATES`, whose values are declared design parameters and are
    PROVISIONAL until Gate G2. This test therefore checks three things rather
    than one, because "MET" now means something weaker than it used to and the
    difference must not be invisible:

      1. every target is met, as before;
      2. the two restated targets still report their counter-rate, so the gate
         cannot silently revert to a bare pass/fail;
      3. the margins are bounded tighter than the declared rates, so a drift
         that stays inside the bound still surfaces here.
    """
    assert [t["id"] for t in report["targets"]] == [
        "typical_improver_traverses", "non_improver_false_fade_rate_is_bounded",
        "regression_reverts_promptly"]
    for target in report["targets"]:
        assert target["met"], "{} is recorded as NOT met".format(target["id"])

    measured = {t["id"]: t["measured"] for t in report["targets"]}
    assert measured["typical_improver_traverses"]["share_traversing_2_of_3"] >= 0.70

    # The restated target must keep reporting BOTH margins -- a stated false-pass
    # rate without its false-fail rate is the thing contrasting groups exists to
    # prevent.
    false_pass = measured["non_improver_false_fade_rate_is_bounded"]
    assert "false_fail_share_typical_improver_not_traversing" in false_pass
    assert false_pass["asymmetry_holds"], (
        "a false pass is now at least as likely as a false fail, which inverts "
        "'premature withdrawal is worse than delayed'")
    # ~5.75% at frozen-g1b, against a declared bound of 10%. Bounded tighter
    # here so drift inside the declared rate still fails a test.
    assert false_pass["share_with_any_fade"] <= 0.08, (
        "a non-improver fades more often than this calibration was chosen for")

    # The safety margin, and the reason 2-of-3 with a 2-lap probe was chosen
    # over 3-of-4: a 9-lap ladder puts removal where regression onsets land and
    # ran 12-26% there, against 0.75% for the 6-lap one.
    assert measured["regression_reverts_promptly"][
        "share_removed_despite_regression"] <= 0.01, (
        "broad regression is being answered by REMOVAL more than the "
        "calibration was chosen for -- this is the design's core safety claim")


def test_the_restated_g1_targets_declare_their_rates_as_provisional():
    """The two restated bars are DESIGN parameters, not literature values.

    The band-calibration review's central finding is that no published rule
    exists for a tolerance of this kind, so a rate written into the gate is
    something this project declared. It is pinned here so it cannot drift into
    being quoted as though it were derived, and so that changing one is a
    deliberate act with a test to update.
    """
    assert sim.TARGET_RATES == {
        "non_improver_false_fade": 0.10,
        "removed_despite_regression": 0.02,
    }
    # The asymmetry the design argues for, as an invariant on the rates
    # themselves rather than on one run's measurements: answering regression
    # with permanent removal costs the rest of the block, so it must be bounded
    # more tightly than a single false fade.
    assert (sim.TARGET_RATES["removed_despite_regression"]
            < sim.TARGET_RATES["non_improver_false_fade"])


def test_the_committed_report_was_run_at_the_scale_the_eval_plan_asks_for(report):
    """'Generate >= 1,000 synthetic participant streams' (eval plan Phase 1)."""
    assert report["total_streams"] >= 1000
    assert report["block_laps"] in range(13, 16), "a training block is 13-15 laps"


def test_the_committed_report_matches_the_committed_config(report):
    """A report describing a configuration the repository no longer holds is a lie."""
    assert report["config_id"] == CFG["config_id"] == "frozen-g1b"
    assert report["config_sha256"] == sim.config_hash(), (
        "controller_config.json has changed since the G1 simulation was run; "
        "re-run `python -m trace_kit.simulate run --streams 200 --out "
        "../configs/simulation` and re-review Gate G1")


def test_the_committed_report_matches_the_committed_reference_tables(report):
    """The same rule, for the other input the verdict depends on.

    Every stream runs against the committed reference tables, so their corner
    counts, quorum denominators and own `mean_rms_m` all feed the measured
    numbers. Pinning only the config left this open, and it bit: pair 1's
    reference was replaced with the 85%-strength table on 2026-10-10 and the
    committed report went on reporting results computed against the superseded
    100% one. Nothing failed, because nothing was watching. It only surfaced
    when an unrelated config field forced a re-run and every apex curve moved.
    """
    assert "reference_sha256" in report, (
        "the committed report predates reference pinning; re-run "
        "`python -m trace_kit.simulate run --streams 200 --out "
        "../configs/simulation`")
    assert report["reference_sha256"] == sim.reference_hashes(), (
        "a reference table has changed since the G1 simulation was run; re-run "
        "`python -m trace_kit.simulate run --streams 200 --out "
        "../configs/simulation` and re-review Gate G1")


def test_the_frozen_config_keeps_the_structural_rules_the_design_argues_for():
    """These are framing v6's choices, not tuned parameters, and the sweep leaves them alone."""
    assert CFG["qualification"] == {"window_passes": 3, "required_passes": 2,
                                    "dequalify_consecutive_failures": 2,
                                    "requalify_on_advance": True}
    assert CFG["quorum"] == {"advance_threshold": 0.75, "revert_threshold": 0.5}
    assert CFG["probe"] == {"laps": 2, "reversion_cap": 2}


def test_the_feasibility_figure_exists_and_covers_every_learner_type(report):
    svg = (SIM_DIR / "feasibility_figure.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for name in report["by_type"]:
        assert name.replace("_", " ") in svg, "{} missing from the figure".format(name)


def test_every_learner_type_has_a_curve_per_element(report):
    for name, data in report["by_type"].items():
        for element in ELEMENTS:
            curve = data["curves"][element]
            assert len(curve) == report["block_laps"]
            assert all(0.0 <= v <= 3.0 for v in curve), name


# --- the simulator itself ----------------------------------------------------

def test_runs_are_deterministic_from_their_seed(references):
    a = sim.run(CFG, references, 3, "seed-a")
    b = sim.run(CFG, references, 3, "seed-a")
    c = sim.run(CFG, references, 3, "seed-b")
    assert a["targets"] == b["targets"]
    assert a["targets"] != c["targets"] or a["by_type"] != c["by_type"]


def test_a_perfect_learner_traverses_and_a_flat_learner_does_not(references):
    """The two ends of the roster, on the real reference tables."""
    result = sim.run(CFG, references, 25, "roster")
    assert result["by_type"]["fast_improver"]["stats"]["share_any_fade"] == 1.0
    # A flat learner never COMPLETES a traversal -- that is the claim that
    # survives, and it is the one that matters: a non-improver never loses a
    # cue for the rest of the block.
    assert result["by_type"]["non_improver"]["stats"]["mean_elements_removed"] == 0.0
    # It does, however, sometimes leave `full`. At frozen-g1b that is ~6-8% of
    # streams, and it is the price of floors wide enough for anything to fade
    # at all: the previous `== 0.0` held only because braking and apex never
    # advanced for ANY learner, real or synthetic (kit/tools/README.md section
    # `feasible.py`). Bounded rather than forbidden, so a drift upward fails.
    assert result["by_type"]["non_improver"]["stats"]["share_any_fade"] <= 0.12


def test_the_simulator_drives_the_real_study_geometry(references):
    """Not a synthetic circuit: the committed tables, with their own corner counts."""
    assert len(references) == 2
    assert [len(r["corners"]) for r in references] == [4, 5]
    assert {r["track"] for r in references} == {
        "ks_silverstone-national", "ks_silverstone-international"}


def test_the_arithmetic_floor_on_reversion_latency_is_computed_per_element(references):
    """The finding that made eval plan v2's staggered target unreachable.

    With onsets one lap apart across four corners, a majority has not regressed
    until the third onset, and a corner cannot de-qualify before its second
    consecutive failure. The floor is therefore the third onset plus one lap, not
    the first onset plus one — and no threshold setting moves it.
    """
    reference = references[0]                       # National: 4 corners
    onsets = {"1": 7, "2": 8, "3": 9, "4": 10}
    floors = sim.earliest_reversion_lap(CFG, reference, onsets)
    # 4 corners, revert below 0.5: need 3 de-qualified -> the 3rd onset is lap 9,
    # de-qualification lands one lap later.
    assert floors["apex"] == 10
    assert floors["corner_speed"] == 10
    # Synchronised regression collapses to the eval plan's own one-lap figure.
    assert sim.earliest_reversion_lap(
        CFG, reference, {c: 7 for c in "1234"})["apex"] == 8


def test_a_learner_with_no_regression_has_no_reversion_floor(references):
    floors = sim.earliest_reversion_lap(
        CFG, references[0], {c: None for c in "1234"})
    assert all(v is None for v in floors.values())


def test_the_sweep_leaves_the_structural_parameters_alone():
    """The sweep calibrates tolerance, it does not redesign the mechanism."""
    swept = set(sim.SWEEP_GRID)
    assert swept == {"band_floors.braking_m", "band_floors.corner_speed_kmh",
                     "band_floors.apex_m", "criteria.consistency_delta_ratio"}
    assert not any(k.startswith(("qualification.", "quorum.", "probe."))
                   for k in swept)


def test_the_novice_model_is_recorded_in_the_committed_report(report):
    """A simulated gate is only as good as its learner, so the learner is published."""
    assert set(report["novice_model"]) == set(sim.MODEL)
    assert report["novice_model"]["brake_offset0_m"] == pytest.approx(25.0), (
        "the one empirically anchored parameter (Gate G0's measured novice brake "
        "points) changed without the report being re-run")
