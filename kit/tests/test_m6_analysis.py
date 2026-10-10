"""M6: the Phase 4 ingestion layer and the RQ1 descriptive report.

M6's exit criterion is that a complete fake-participant dataset is ingested by
the analysis scripts "without manual fixes", which is a statement about
``analysis.load_dataset``. So this file is mostly about ingestion being exactly
as strict and as forgiving as the evaluation plan says:

  * the three exclusion markers (dev / aborted / dry_run) keep their blocks out
    of participant data, and the dry run can opt its own data back IN;
  * the lap-validity rules are applied once, centrally, including the one that
    cannot be fully applied (wall contact outside an annotated corner);
  * a block that ends mid-probe is right-censored rather than dropped, because
    dropping it would bias the probe-outcome table toward whichever outcome
    resolves faster. G1 predicts ~38% of typical improvers end this way, so this
    is the common case, not an edge case.

The RQ2 Bayesian model is deliberately absent (decision 2026-10-09); there is a
test below asserting the lap table it will need is actually emitted, so the
deferral stays honest.
"""

import json
import xml.etree.ElementTree as ET

import pytest

from trace_kit import analysis, integrity

COLUMNS = integrity.expected_columns()


# --- fixtures: a small directory of blocks ----------------------------------

def manifest(block_id, **overrides):
    doc = {
        "schema_version": 1,
        "block_id": block_id,
        "participant_id": block_id.split("_")[0],
        "session": 2,
        "condition": "adaptive",
        "pair_id": "pair1",
        "config_hashes": {"annotation": "a" * 64, "reference": "b" * 64,
                          "controller_config": "c" * 64},
        "versions": {"app": "0.3.0", "csp": "0.2.11", "ac": "1.16.4"},
        "started_at": "2026-09-08T12:00:00",
        "laps_completed": 2,
    }
    doc.update(overrides)
    return doc


def tick_row(t, lap, wheels_outside=0, in_pit=0):
    values = {"t": t, "lap": lap, "spline": 0.5, "pos_x": 1.0, "pos_y": 0.0,
              "pos_z": 2.0, "speed_kmh": 100.0, "brake": 0.0, "throttle": 1.0,
              "steer": 0.0, "gear": 3, "wheels_outside": wheels_outside,
              "in_pit": in_pit}
    return ",".join(str(values[c]) for c in COLUMNS)


def write_block(directory, block_id, ticks=(), passes=(), fades=(), **manifest_overrides):
    (directory / "manifest_{}.json".format(block_id)).write_text(
        json.dumps(manifest(block_id, **manifest_overrides)), encoding="utf-8")
    (directory / "ticks_{}.csv".format(block_id)).write_text(
        "\n".join([",".join(COLUMNS)] + list(ticks)) + "\n", encoding="utf-8")
    if passes:
        (directory / "passes_{}.jsonl".format(block_id)).write_text(
            "\n".join(json.dumps(p) for p in passes) + "\n", encoding="utf-8")
    if fades:
        (directory / "fades_{}.jsonl".format(block_id)).write_text(
            "\n".join(json.dumps(f) for f in fades) + "\n", encoding="utf-8")


def three_laps(wheels_on_lap=None, pit_on_lap=None):
    """Ticks for laps 0,1,2 at 20 Hz, 10 ticks each (0.5 s of 'lap')."""
    wheels_on_lap = wheels_on_lap or {}
    pit_on_lap = pit_on_lap or {}
    rows, t = [], 0.0
    for lap in (0, 1, 2):
        for i in range(10):
            rows.append(tick_row(round(t, 2), lap,
                                 wheels_outside=wheels_on_lap.get(lap, 0) if i == 5 else 0,
                                 in_pit=pit_on_lap.get(lap, 0) if i == 5 else 0))
            t += 0.05
    return rows


# --- block classification ---------------------------------------------------

@pytest.mark.parametrize("flags,expected", [
    ({}, "study"),
    ({"dev_block": True}, "dev"),
    ({"aborted": True, "abort_reason": "other"}, "aborted"),
    ({"dry_run": True}, "dry_run"),
])
def test_block_kind(flags, expected):
    assert analysis.block_kind(manifest("P01_x", **flags)) == expected


def test_an_aborted_dry_run_block_reads_as_aborted():
    """Abort wins over dry_run: the block was discarded, whatever it was for."""
    doc = manifest("P01_x", dry_run=True, aborted=True, abort_reason="sim_or_app_crash")
    assert analysis.block_kind(doc) == "aborted"


# --- laps -------------------------------------------------------------------

def test_lap_rows_time_and_partial_flags(tmp_path):
    write_block(tmp_path, "P01_a", ticks=three_laps())
    rows = analysis.lap_rows(tmp_path / "ticks_P01_a.csv", COLUMNS, "P01_a")
    assert [r["lap"] for r in rows] == [0, 1, 2]
    # Interior lap: 9 inter-tick gaps of 0.05 s.
    assert rows[1]["lap_time_s"] == pytest.approx(0.45, abs=1e-6)
    # First and last are partial; the middle one is not.
    assert [r["partial"] for r in rows] == [True, False, True]
    assert [r["first_of_block"] for r in rows] == [True, False, False]


def test_lap_validity_rules():
    first = {"first_of_block": True, "partial": True}
    assert analysis.lap_validity(first, [])[1] == ["first_of_block"]

    clean = {"first_of_block": False, "partial": False, "max_wheels_outside": 2}
    assert analysis.lap_validity(clean, []) == (True, [])

    # The plan's threshold is "more than two wheels", so two is still valid.
    off = {"first_of_block": False, "partial": False, "max_wheels_outside": 3}
    assert "wheels_outside" in analysis.lap_validity(off, [])[1]

    pit = {"first_of_block": False, "partial": False, "pit": True}
    assert "pit" in analysis.lap_validity(pit, [])[1]

    last = {"first_of_block": False, "partial": True}
    assert "partial_lap" in analysis.lap_validity(last, [])[1]


def test_wall_contact_reaches_lap_validity_through_the_pass_records():
    """The tick log has no collision column, so this is the only path there is."""
    lap = {"first_of_block": False, "partial": False}
    passes = [{"corner_id": "1", "lap": 1, "invalid_reasons": ["wall_contact"]}]
    valid, reasons = analysis.lap_validity(lap, passes)
    assert valid is False
    assert "wall_contact" in reasons


def test_a_wall_contact_outside_a_corner_is_invisible():
    """Documents the structural limitation rather than pretending it is covered.

    Collision depth is captured only inside a corner's pass bracket, so a
    contact on a straight leaves no trace this function can read. If this test
    ever starts failing because the tick log gained a collision column, the
    limitation in `lap_validity`'s docstring and in the methods chapter is the
    thing to update.
    """
    assert "collision" not in " ".join(COLUMNS)
    lap = {"first_of_block": False, "partial": False}
    passes = [{"corner_id": "1", "lap": 1, "invalid_reasons": []}]
    assert analysis.lap_validity(lap, passes) == (True, [])


# --- ingestion --------------------------------------------------------------

def test_ingestion_keeps_study_blocks_and_excludes_the_rest(tmp_path):
    write_block(tmp_path, "P01_study", ticks=three_laps())
    write_block(tmp_path, "P02_dev", ticks=three_laps(), dev_block=True)
    write_block(tmp_path, "P03_abort", ticks=three_laps(),
                aborted=True, abort_reason="participant_request")
    write_block(tmp_path, "P04_dry", ticks=three_laps(), dry_run=True)

    dataset = analysis.load_dataset(tmp_path)
    assert [b["block_id"] for b in dataset["blocks"]] == ["P01_study"]
    assert {row["kind"] for row in dataset["excluded"]} == {"dev", "aborted", "dry_run"}
    # The abort reason survives into the exclusion record, so the dataset README
    # can explain the discarded block later.
    abort = [r for r in dataset["excluded"] if r["kind"] == "aborted"][0]
    assert abort["abort_reason"] == "participant_request"


def test_the_dry_run_can_ingest_its_own_data(tmp_path):
    """How the rehearsal proves the analysis path without polluting it."""
    write_block(tmp_path, "DRY01_a", ticks=three_laps(), dry_run=True)
    dataset = analysis.load_dataset(tmp_path, include=("dry_run",))
    assert [b["block_id"] for b in dataset["blocks"]] == ["DRY01_a"]
    assert dataset["blocks"][0]["kind"] == "dry_run"


def test_ingestion_emits_the_lap_table_the_rq2_model_will_need(tmp_path):
    """The deferral of the Bayesian model is only honest if its input exists.

    Condition, pair, participant and a lap time per valid lap are exactly the
    columns eval plan RQ2's model is specified over.
    """
    write_block(tmp_path, "P01_a", ticks=three_laps())
    dataset = analysis.load_dataset(tmp_path)
    valid = [row for row in dataset["laps"] if row["valid"]]
    assert valid, "no valid laps ingested"
    for key in ("participant_id", "session", "condition", "pair_id", "lap_time_s"):
        assert key in valid[0], key


# --- fade trajectories and probe outcomes -----------------------------------

def fade(element, transition, lap, block_id="P01_a"):
    return {"schema_version": 1, "block_id": block_id, "element": element,
            "transition": transition, "lap": lap, "t": lap * 60.0,
            "quorum": {"qualified_share": 1.0, "qualified_corners": ["1"],
                       "applicable_corners": 1, "flipped_corners": []}}


def test_a_trajectory_starts_at_full_and_steps_up():
    events = [fade("braking", "full_to_reduced", 4),
              fade("braking", "reduced_to_probe", 8),
              fade("braking", "probe_to_removed", 11)]
    points = analysis.fade_trajectory(events, "braking")
    assert points == [(0, 0), (4, 1), (8, 2), (11, 3)]


def test_a_reversion_is_a_downward_step():
    events = [fade("braking", "full_to_reduced", 4),
              fade("braking", "reduced_to_probe", 8),
              fade("braking", "probe_to_revert", 10)]
    points = analysis.fade_trajectory(events, "braking")
    assert points[-1] == (10, analysis.STAGE_INDEX["reduced"])


def test_other_elements_do_not_appear_in_a_trajectory():
    events = [fade("apex", "full_to_reduced", 4)]
    assert analysis.fade_trajectory(events, "braking") == [(0, 0)]


@pytest.mark.parametrize("transitions,expected", [
    ([], "never_probed"),
    ([("full_to_reduced", 4)], "never_probed"),
    ([("full_to_reduced", 4), ("reduced_to_probe", 8)], "censored"),
    ([("full_to_reduced", 4), ("reduced_to_probe", 8), ("probe_to_removed", 11)], "held"),
    ([("full_to_reduced", 4), ("reduced_to_probe", 8), ("probe_to_revert", 10)], "reverted"),
])
def test_probe_outcomes(transitions, expected):
    events = [fade("braking", name, lap) for name, lap in transitions]
    assert analysis.probe_outcome(events, "braking") == expected


def test_a_block_ending_mid_probe_is_censored_not_dropped(tmp_path):
    """G1 says this is the common case, so it must be counted, not lost."""
    events = [fade("braking", "full_to_reduced", 4), fade("braking", "reduced_to_probe", 8)]
    write_block(tmp_path, "P01_a", ticks=three_laps(), fades=events)
    report = analysis.rq1(analysis.load_dataset(tmp_path))
    outcomes = report["timings"]["braking"]["probe_outcomes"]
    assert outcomes["censored"] == 1
    assert outcomes["held"] == 0 and outcomes["reverted"] == 0


# --- qualification heatmap --------------------------------------------------

def pass_record(corner_id, lap, criterion, qualified=False, block_id="P01_a"):
    return {"schema_version": 1, "block_id": block_id, "corner_id": corner_id, "lap": lap,
            "t_entry": 1.0, "t_exit": 2.0, "valid": True,
            "metrics": {}, "criteria": {"braking": criterion},
            "qualified": {"braking": qualified},
            "stage": {"braking": "full", "corner_speed": "full", "apex": "full"}}


def test_heatmap_grid_and_null_cells():
    passes = [pass_record("1", 1, True, qualified=True),
              pass_record("2", 1, None),
              pass_record("1", 2, False)]
    grid = analysis.qualification_heatmap(passes, "braking")
    assert grid["corners"] == ["1", "2"]
    assert grid["laps"] == [1, 2]
    assert grid["cells"]["1|1"]["criterion"] is True
    assert grid["cells"]["1|1"]["qualified"] is True
    # A null criterion is no evidence: it must stay distinguishable from False.
    assert grid["cells"]["2|1"]["criterion"] is None
    assert grid["cells"]["1|2"]["criterion"] is False


# --- RQ1 report -------------------------------------------------------------

def test_rq1_reports_timings_and_never_fades(tmp_path):
    write_block(tmp_path, "P01_a", ticks=three_laps(),
                fades=[fade("braking", "full_to_reduced", 4),
                       fade("braking", "reduced_to_probe", 8)])
    report = analysis.rq1(analysis.load_dataset(tmp_path))

    braking = report["timings"]["braking"]
    assert braking["time_to_first_fade_laps"]["values"] == [4]
    assert braking["never_faded"] == 0

    # The two elements that never moved are the never-fade cases.
    assert report["timings"]["apex"]["never_faded"] == 1
    cases = {(c["element"], c["case"]) for c in report["atypical"]}
    assert ("apex", "never_faded") in cases
    assert ("braking", "never_faded") not in cases


def test_a_disabled_element_is_not_counted_as_a_never_fade(tmp_path):
    """Zero applicable corners means pinned-and-never-evaluated, not a failure.

    Counting a disabled element among the never-fades would quietly inflate the
    denominator of the one number RQ1 is most likely to be quoted on.
    """
    write_block(tmp_path, "P01_a", ticks=three_laps(), disabled_elements=["braking"])
    report = analysis.rq1(analysis.load_dataset(tmp_path))
    assert report["timings"]["braking"]["blocks"] == 0
    assert report["timings"]["braking"]["never_faded"] == 0
    assert all(c["element"] != "braking" for c in report["atypical"])


def test_repeated_reverts_are_flagged_as_an_individual_case(tmp_path):
    write_block(tmp_path, "P01_a", ticks=three_laps(),
                fades=[fade("braking", "full_to_reduced", 2),
                       fade("braking", "reduced_to_probe", 4),
                       fade("braking", "probe_to_revert", 5),
                       fade("braking", "reduced_to_probe", 7),
                       fade("braking", "probe_to_revert", 8)])
    report = analysis.rq1(analysis.load_dataset(tmp_path))
    cases = [c for c in report["atypical"] if c["element"] == "braking"]
    assert cases and cases[0]["case"] == "repeated_reverts"
    assert report["timings"]["braking"]["reversion_cap_hits"] == 1


# --- RQ3 alignment ----------------------------------------------------------

def instrument(participant, noticed, session=3):
    return {"schema_version": 1, "instrument": "post_study",
            "participant_id": participant, "session": session,
            "recorded_at": "2026-09-08T14:00:00",
            "responses": {"confidence_overall": 5, "confidence_braking": 5,
                          "confidence_corner_speed": 4, "confidence_apex": 4,
                          "dependence_braking": 3, "dependence_corner_speed": 3,
                          "dependence_apex": 2, "noticed_fading": noticed}}


@pytest.mark.parametrize("noticed,withdrew,cell", [
    (True, True, "aware"),
    (True, False, "false_alarm"),
    (False, True, "unaware"),
    (False, False, "nothing_to_notice"),
])
def test_alignment_cells(tmp_path, noticed, withdrew, cell):
    """All four cells, because 'noticed nothing' means two different things.

    A participant who noticed nothing because nothing faded is not the same
    case as one who noticed nothing while an element was withdrawn, and the
    alignment table is the only place that distinction is made.
    """
    fades = [fade("braking", "full_to_reduced", 2, block_id="P01_a"),
             fade("braking", "reduced_to_probe", 4, block_id="P01_a")] if withdrew else []
    write_block(tmp_path, "P01_a", ticks=three_laps(), fades=fades)
    (tmp_path / "instrument_post_study_P01_s3.json").write_text(
        json.dumps(instrument("P01", noticed)), encoding="utf-8")

    rows = analysis.alignment_table(analysis.load_dataset(tmp_path))
    assert len(rows) == 1
    assert rows[0]["cell"] == cell
    assert rows[0]["reported_noticed"] is noticed


# --- figure -----------------------------------------------------------------

def test_the_trajectory_figure_is_well_formed_svg(tmp_path):
    write_block(tmp_path, "P01_a", ticks=three_laps(),
                fades=[fade("braking", "full_to_reduced", 4),
                       fade("braking", "reduced_to_probe", 8)])
    report = analysis.rq1(analysis.load_dataset(tmp_path))
    svg = analysis.trajectory_svg(report)
    root = ET.fromstring(svg)   # raises if malformed
    assert root.tag.endswith("svg")
    assert "braking" in svg


def test_the_figure_survives_an_empty_dataset(tmp_path):
    """A figure call on a directory with nothing in it must not crash the run."""
    report = analysis.rq1(analysis.load_dataset(tmp_path))
    ET.fromstring(analysis.trajectory_svg(report))
