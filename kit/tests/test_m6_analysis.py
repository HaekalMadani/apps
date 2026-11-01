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


# --- autopilot blocks are never participant data (regression 2026-10-10) ----

def test_an_autopilot_block_is_never_study_data():
    """A reference recording is not a participant, whatever else is stamped.

    The 85%-strength reference block was recorded with the dev toggle off. Before
    this, `load_dataset` would have ingested the AC AI as participant P-"85AI1".
    """
    assert analysis.block_kind(manifest("85AI1_x", autopilot=True)) == "ai"
    # And it wins over every other marker, including none at all.
    assert analysis.block_kind(manifest("x", autopilot=True, dev_block=True)) == "ai"
    assert analysis.block_kind(manifest("x", autopilot=True, dry_run=True)) == "ai"


def test_autopilot_blocks_are_excluded_from_ingestion(tmp_path):
    write_block(tmp_path, "85AI1_a", ticks=three_laps(), autopilot=True, ai_level_pct=85)
    write_block(tmp_path, "P01_a", ticks=three_laps())
    dataset = analysis.load_dataset(tmp_path)
    assert [b["block_id"] for b in dataset["blocks"]] == ["P01_a"]
    assert [r["kind"] for r in dataset["excluded"]] == ["ai"]


# --- the section 0A KR diagnostic (CE/VE) -----------------------------------
#
# Added with bandwidth KR (2026-10-10). The literature review's step 2 is a
# diagnostic, not a study: drive with the error signal on, and read whether the
# BIAS moves. So the thing that has to be right here is the CE/VE decomposition
# — the measured novice problem is a CE problem (89% of brake points on the same
# side of the reference), which a composite absolute error cannot show.


def kr_metric_pass(corner_id, lap, brake=None, speed=None, apex=None,
                   kr=None, block_id="P01_a", t_exit=None, stage=None,
                   brake_clamped=False):
    stages = stage or {"braking": "full", "corner_speed": "full", "apex": "full"}
    return {"schema_version": 1, "block_id": block_id, "corner_id": corner_id, "lap": lap,
            "t_entry": 1.0 + lap, "t_exit": t_exit if t_exit is not None else 2.0 + lap,
            "valid": True,
            "metrics": {"brake_initiation_distance_m": brake,
                        "min_corner_speed_kmh": None,
                        "speed_envelope_deviation_kmh": speed,
                        "apex_rms_m": apex,
                        **({"brake_initiation_clamped": True} if brake_clamped else {})},
            "criteria": {"braking": None, "corner_speed": None, "apex": None},
            "qualified": {"braking": False, "corner_speed": False, "apex": False},
            "stage": stages,
            **({"kr": kr} if kr else {})}


def test_ce_and_ve_separate_bias_from_scatter():
    """The whole reason this exists. Two learners with the same mean ABSOLUTE
    error, one all bias and one all scatter, must not look the same."""
    biased = analysis.ce_ve([15.0, 15.0, 15.0, 15.0])
    scattered = analysis.ce_ve([15.0, -15.0, 15.0, -15.0])
    assert biased["ae"] == scattered["ae"] == 15.0
    assert biased["ce"] == 15.0 and biased["ve"] == 0.0
    assert scattered["ce"] == 0.0 and scattered["ve"] > 15.0


def test_ce_ve_handles_short_and_empty_series():
    """An SD needs two samples. The review's own note is that an SD from 3-4
    passes is very noisy, which is why this is a report and not a criterion."""
    assert analysis.ce_ve([]) == {"n": 0, "ce": None, "ve": None, "ae": None}
    one = analysis.ce_ve([7.0])
    assert one["n"] == 1 and one["ce"] == 7.0 and one["ve"] is None
    # Nulls are no evidence and drop out rather than counting as zero error.
    assert analysis.ce_ve([7.0, None, 9.0])["n"] == 2


def test_the_diagnostic_reports_ce_per_corner_and_the_half_split(tmp_path):
    """The diagnostic's actual output: is the bias moving within the block?"""
    passes = [kr_metric_pass("1", lap, brake=b, t_exit=float(lap))
              for lap, b in enumerate([16.0, 15.0, 14.0, 5.0, 4.0, 3.0])]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes,
                fades=[{"schema_version": 1, "block_id": "P01_a", "t": 1.0, "lap": 1,
                        "element": "apex", "transition": "full_to_reduced",
                        "quorum": {"qualified_share": 1.0, "qualified_corners": ["1"],
                                   "applicable_corners": 1, "flipped_corners": []}}])
    report = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))
    corner = report["blocks"][0]["elements"]["braking"]["corners"]["1"]
    assert corner["overall"]["ce"] == pytest.approx(9.5)
    assert corner["first_half"]["ce"] == pytest.approx(15.0)
    assert corner["second_half"]["ce"] == pytest.approx(4.0)
    # The series is kept in pass order, so the trajectory can be plotted rather
    # than only summarised — a half-split cannot detect learning in a plateaued
    # driver by construction (the review's flag on Finding 3).
    assert corner["series"] == [16.0, 15.0, 14.0, 5.0, 4.0, 3.0]


def test_the_series_is_ordered_by_pass_close_not_file_order(tmp_path):
    """t_exit is the order the driver drove them in; file order is whatever the
    flushes happened to produce."""
    passes = [kr_metric_pass("1", 2, brake=3.0, t_exit=30.0),
              kr_metric_pass("1", 0, brake=1.0, t_exit=10.0),
              kr_metric_pass("1", 1, brake=2.0, t_exit=20.0)]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    report = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))
    assert report["blocks"][0]["elements"]["braking"]["corners"]["1"]["series"] == \
        [1.0, 2.0, 3.0]


def test_the_diagnostic_counts_what_kr_actually_did(tmp_path):
    """A diagnostic in which the messages never fired measures nothing, so the
    outcome counts are part of the report rather than something to infer."""
    def entry(outcome):
        doc = {"outcome": outcome}
        if outcome == "delivered":
            doc.update({"text": "14 m early", "error_value": 14.0, "band": 5.0})
        return doc

    passes = [
        kr_metric_pass("1", 0, brake=14.0, kr={"braking": entry("delivered"),
                                               "corner_speed": entry("capped"),
                                               "apex": entry("capped")}),
        kr_metric_pass("1", 1, brake=2.0, kr={"braking": entry("inside_band"),
                                              "corner_speed": entry("inside_band"),
                                              "apex": entry("inside_band")}),
        kr_metric_pass("1", 2, brake=14.0,
                       stage={"braking": "probe", "corner_speed": "full", "apex": "full"},
                       kr={"braking": entry("withdrawn"),
                           "corner_speed": entry("inside_band"),
                           "apex": entry("inside_band")}),
    ]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    report = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))
    counts = report["blocks"][0]["elements"]["braking"]["kr_outcomes"]
    assert counts == {"delivered": 1, "inside_band": 1, "withdrawn": 1}


def test_a_block_with_no_kr_field_counts_as_absent_not_off(tmp_path):
    """`absent` (never reached the evaluator) and `off` (KR configured off) are
    different facts, and the diagnostic turns on telling the silences apart."""
    passes = [kr_metric_pass("1", lap, brake=10.0) for lap in range(3)]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    report = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))
    assert report["blocks"][0]["elements"]["braking"]["kr_outcomes"] == {"absent": 3}


def test_the_diagnostic_pools_corners_and_keeps_them_separate(tmp_path):
    """Pooled CE is the headline number; per-corner CE is what says whether the
    bias is the same corner everywhere or one corner dragging the mean."""
    passes = ([kr_metric_pass("1", lap, brake=20.0, t_exit=float(lap)) for lap in range(3)]
              + [kr_metric_pass("2", lap, brake=0.0, t_exit=float(lap) + 0.5)
                 for lap in range(3)])
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    element = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))["blocks"][0] \
        ["elements"]["braking"]
    assert element["pooled"]["ce"] == pytest.approx(10.0)
    assert element["corners"]["1"]["overall"]["ce"] == pytest.approx(20.0)
    assert element["corners"]["2"]["overall"]["ce"] == pytest.approx(0.0)
    assert element["unit"] == "m"


# --- clamped passes stay out of the averages (2026-10-14) --------------------

def test_a_clamped_pass_is_excluded_from_ce_but_kept_in_the_series(tmp_path):
    """A floor averaged into a bias is an annotation constant posing as learning.

    The three real passes sit at a steady +15 m. The fourth is a brake point
    clamped to its zone's opening at +80 m: a lower bound, not a measurement.
    Averaging it would report CE +31.25 m and make the bias look worse; a
    clamped pass on the NARROW side would make it look better. Either way the
    number would be about the braking zone's geometry, not the driver.
    """
    passes = [kr_metric_pass("1", 0, brake=15.0, t_exit=1.0),
              kr_metric_pass("1", 1, brake=15.0, t_exit=2.0),
              kr_metric_pass("1", 2, brake=15.0, t_exit=3.0),
              kr_metric_pass("1", 3, brake=80.0, t_exit=4.0, brake_clamped=True)]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    element = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))["blocks"][0] \
        ["elements"]["braking"]
    corner = element["corners"]["1"]
    assert corner["overall"]["ce"] == pytest.approx(15.0)
    assert corner["overall"]["n"] == 3
    assert corner["clamped_excluded"] == 1
    assert element["pooled"]["ce"] == pytest.approx(15.0)
    assert element["clamped_excluded"] == 1
    # The audit trail keeps what the apparatus recorded, averages or not.
    assert corner["series"] == [15.0, 15.0, 15.0, 80.0]


def test_a_clamped_pass_does_not_shift_the_half_split(tmp_path):
    """The half-split is the "did the bias move?" reading, so it is exactly where
    a clamped floor would do the most damage."""
    passes = [kr_metric_pass("1", 0, brake=16.0, t_exit=1.0),
              kr_metric_pass("1", 1, brake=90.0, t_exit=2.0, brake_clamped=True),
              kr_metric_pass("1", 2, brake=14.0, t_exit=3.0),
              kr_metric_pass("1", 3, brake=4.0, t_exit=4.0),
              kr_metric_pass("1", 4, brake=2.0, t_exit=5.0)]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    corner = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))["blocks"][0] \
        ["elements"]["braking"]["corners"]["1"]
    # Usable series is [16, 14, 4, 2]: halves are [16, 14] and [4, 2].
    assert corner["first_half"]["ce"] == pytest.approx(15.0)
    assert corner["second_half"]["ce"] == pytest.approx(3.0)
    assert corner["clamped_excluded"] == 1


def test_only_the_braking_metric_is_ever_treated_as_clamped(tmp_path):
    """The flag is about the brake-initiation search bracket. A corner-speed or
    apex window a pass did not cover yields a null, which is a different case
    and already handled."""
    passes = [kr_metric_pass("1", 0, brake=80.0, speed=-9.0, apex=1.2,
                             t_exit=1.0, brake_clamped=True)]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    elements = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))["blocks"][0]["elements"]
    assert elements["braking"]["corners"]["1"]["overall"]["n"] == 0
    assert elements["corner_speed"]["corners"]["1"]["overall"]["ce"] == pytest.approx(-9.0)
    assert elements["corner_speed"]["clamped_excluded"] == 0
    assert elements["apex"]["corners"]["1"]["overall"]["ce"] == pytest.approx(1.2)


def test_the_kr_outcome_counts_show_the_clamped_silences(tmp_path):
    """`clamped` is one of the silences the diagnostic has to tell apart, so a
    block where messages were withheld as floors is visible rather than
    inferred from a suspiciously small n."""
    passes = [kr_metric_pass("1", 0, brake=80.0, t_exit=1.0, brake_clamped=True,
                             kr={"braking": {"outcome": "clamped", "error_value": 80.0,
                                             "band": 5.0},
                                 "corner_speed": {"outcome": "not_measured"},
                                 "apex": {"outcome": "not_measured"}})]
    write_block(tmp_path, "P01_a", ticks=three_laps(), passes=passes)
    element = analysis.kr_diagnostic(analysis.load_dataset(tmp_path))["blocks"][0] \
        ["elements"]["braking"]
    assert element["kr_outcomes"] == {"clamped": 1}
