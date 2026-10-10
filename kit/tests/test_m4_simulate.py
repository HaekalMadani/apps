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
    """G1's verdict, asserted from the repository rather than from memory."""
    assert [t["id"] for t in report["targets"]] == [
        "typical_improver_traverses", "non_improver_never_fades",
        "regression_reverts_promptly"]
    for target in report["targets"]:
        assert target["met"], "{} is recorded as NOT met".format(target["id"])


def test_the_committed_report_was_run_at_the_scale_the_eval_plan_asks_for(report):
    """'Generate >= 1,000 synthetic participant streams' (eval plan Phase 1)."""
    assert report["total_streams"] >= 1000
    assert report["block_laps"] in range(13, 16), "a training block is 13-15 laps"


def test_the_committed_report_matches_the_committed_config(report):
    """A report describing a configuration the repository no longer holds is a lie."""
    assert report["config_id"] == CFG["config_id"] == "frozen-g1"
    assert report["config_sha256"] == sim.config_hash(), (
        "controller_config.json has changed since the G1 simulation was run; "
        "re-run `python -m trace_kit.simulate run --streams 200 --out "
        "../configs/simulation` and re-review Gate G1")


def test_the_frozen_config_keeps_the_structural_rules_the_design_argues_for():
    """These are framing v6's choices, not tuned parameters, and the sweep leaves them alone."""
    assert CFG["qualification"] == {"window_passes": 4, "required_passes": 3,
                                    "dequalify_consecutive_failures": 2,
                                    "requalify_on_advance": True}
    assert CFG["quorum"] == {"advance_threshold": 0.75, "revert_threshold": 0.5}
    assert CFG["probe"] == {"laps": 3, "reversion_cap": 2}


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
    assert result["by_type"]["non_improver"]["stats"]["share_any_fade"] == 0.0
    assert result["by_type"]["non_improver"]["stats"]["mean_elements_removed"] == 0.0


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
