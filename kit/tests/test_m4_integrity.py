"""M4: the integrity checker's new clauses over the pass and fade streams.

The evaluation plan's after-every-session integrity check includes "fade-event
log parses". M4 is when there is a fade-event log to parse, so this is where that
clause becomes real — and it goes further than parsing: the checker replays the
event sequence and rejects one no state machine could have produced.

That replay is the offline half of the golden-trace suite. The traces prove the
CONTROLLER can only emit legal sequences; this proves the sequence that reached
DISK is one of them, which is what catches a truncated, corrupted or hand-edited
log before it reaches an RQ1 fade timeline.
"""

import json

import pytest

from trace_kit import integrity

BLOCK = "P01_s2_pair1_adaptive_20260908_120000"
COLUMNS = integrity.expected_columns()


def manifest(**overrides):
    doc = {
        "schema_version": 1,
        "block_id": BLOCK,
        "participant_id": "P01",
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


def tick_row(t, lap):
    values = {"t": t, "lap": lap, "spline": 0.5, "pos_x": 1.0, "pos_y": 0.0,
              "pos_z": 2.0, "speed_kmh": 100.0, "brake": 0.0, "throttle": 1.0,
              "steer": 0.0, "gear": 3, "wheels_outside": 0, "in_pit": 0}
    return ",".join(str(values[c]) for c in COLUMNS)


def pass_record(corner_id, lap, valid=True, **overrides):
    doc = {
        "schema_version": 1, "block_id": BLOCK, "corner_id": corner_id, "lap": lap,
        "t_entry": 10.0 + lap * 60, "t_exit": 20.0 + lap * 60, "valid": valid,
        "metrics": {"brake_initiation_distance_m": 1.0, "min_corner_speed_kmh": 90.0,
                    "speed_envelope_deviation_kmh": 0.0, "apex_rms_m": 0.1},
        "criteria": {"braking": True, "corner_speed": True, "apex": True},
        "qualified": {"braking": True, "corner_speed": True, "apex": True},
        "stage": {"braking": "full", "corner_speed": "full", "apex": "full"},
    }
    if not valid:
        doc["invalid_reasons"] = ["wheels_outside"]
    doc.update(overrides)
    return doc


def fade_record(element, transition, lap, qualified=("1", "2", "3", "4"),
                applicable=4, **overrides):
    doc = {
        "schema_version": 1, "block_id": BLOCK, "t": 20.0 + lap * 60, "lap": lap,
        "element": element, "transition": transition,
        "quorum": {"qualified_share": len(qualified) / applicable,
                   "qualified_corners": list(qualified),
                   "applicable_corners": applicable, "flipped_corners": []},
    }
    doc.update(overrides)
    return doc


def write_block(tmp_path, manifest_doc, ticks=None, passes=None, fades=None):
    (tmp_path / "manifest_{}.json".format(BLOCK)).write_text(
        json.dumps(manifest_doc), encoding="utf-8")
    rows = ticks if ticks is not None else [
        tick_row(round(i * 0.05, 2), min(2, i // 20)) for i in range(60)]
    (tmp_path / "ticks_{}.csv".format(BLOCK)).write_text(
        ",".join(COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    if passes is not None:
        (tmp_path / "passes_{}.jsonl".format(BLOCK)).write_text(
            "".join(json.dumps(p) + "\n" for p in passes), encoding="utf-8")
    if fades is not None:
        (tmp_path / "fades_{}.jsonl".format(BLOCK)).write_text(
            "".join(json.dumps(f) + "\n" for f in fades), encoding="utf-8")
    return tmp_path / "manifest_{}.json".format(BLOCK)


def check(tmp_path, **kwargs):
    return integrity.check_block(write_block(tmp_path, **kwargs))


# --- the happy path ----------------------------------------------------------

def test_a_complete_block_passes(tmp_path):
    passes = [pass_record(c, lap) for lap in range(3) for c in ("1", "2")]
    fades = [fade_record("apex", "full_to_reduced", 2)]
    problems, summary = check(tmp_path, manifest_doc=manifest(), passes=passes, fades=fades)
    assert problems == [], problems
    assert summary["pass_count"] == 6
    assert summary["fade_count"] == 1


def test_the_counts_reach_the_summary(tmp_path):
    problems, summary = check(tmp_path, manifest_doc=manifest(),
                              passes=[pass_record("1", 0)], fades=[])
    assert summary["pass_count"] == 1 and summary["fade_count"] == 0


# --- streams that should be there, and are not -------------------------------

def test_a_participant_block_with_no_pass_stream_is_flagged(tmp_path):
    """A block that recorded no corner passes has no evidence in it."""
    problems, _ = check(tmp_path, manifest_doc=manifest())
    assert any("no passes_" in p for p in problems), problems
    assert any("no fades_" in p for p in problems), problems


def test_a_dev_block_may_have_neither_stream(tmp_path):
    """Which is how the reference laps themselves are recorded."""
    problems, _ = check(tmp_path, manifest_doc=manifest(dev_block=True))
    assert problems == [], problems


def test_an_off_condition_block_needs_passes_but_not_fades(tmp_path):
    """Sessions 1 and 3 show no elements, but the corner passes are the outcome data."""
    problems, _ = check(tmp_path, manifest_doc=manifest(condition="off"),
                        passes=[pass_record("1", 0)])
    assert problems == [], problems


# --- malformed streams -------------------------------------------------------

def test_an_unparseable_line_is_reported_with_its_line_number(tmp_path):
    path = write_block(tmp_path, manifest(), passes=[pass_record("1", 0)], fades=[])
    (path.parent / "passes_{}.jsonl".format(BLOCK)).write_text(
        json.dumps(pass_record("1", 0)) + "\n{ this is not json\n", encoding="utf-8")
    problems, _ = integrity.check_block(path)
    assert any("line 2: unparseable" in p for p in problems), problems


def test_a_schema_invalid_record_is_reported(tmp_path):
    bad = pass_record("1", 0)
    bad["stage"]["apex"] = "vanished"
    problems, _ = check(tmp_path, manifest_doc=manifest(), passes=[bad], fades=[])
    assert any("passes_" in p and "line 1" in p for p in problems), problems


def test_a_record_from_another_block_is_reported(tmp_path):
    """Two blocks' logs concatenated is a real hazard of a manual re-run."""
    stray = pass_record("1", 0)
    stray["block_id"] = "SOMEONE_ELSE"
    problems, _ = check(tmp_path, manifest_doc=manifest(), passes=[stray], fades=[])
    assert any("does not match the manifest" in p for p in problems), problems


# --- pass-stream consistency -------------------------------------------------

def test_two_passes_of_one_corner_on_one_lap_are_flagged(tmp_path):
    """The M2 exit criterion, re-checked on disk: the controller must not see
    one corner's evidence twice."""
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", 0), pass_record("1", 0)], fades=[])
    assert any("more than one pass on lap 0" in p for p in problems), problems


def test_an_invalid_pass_with_no_reason_is_flagged(tmp_path):
    bad = pass_record("1", 0, valid=False)
    del bad["invalid_reasons"]
    problems, _ = check(tmp_path, manifest_doc=manifest(), passes=[bad], fades=[])
    assert any("invalid with no reason" in p for p in problems), problems


def test_a_pass_closing_before_it_opens_is_flagged(tmp_path):
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", 0, t_entry=50.0, t_exit=10.0)], fades=[])
    assert any("closes before it opens" in p for p in problems), problems


# --- fade-stream consistency: the sequence replay ----------------------------

def test_a_legal_full_traverse_replays_cleanly(tmp_path):
    fades = [fade_record("apex", "full_to_reduced", 2),
             fade_record("apex", "reduced_to_probe", 5),
             fade_record("apex", "probe_to_removed", 8)]
    problems, _ = check(tmp_path, manifest_doc=manifest(laps_completed=2),
                        passes=[pass_record("1", lap) for lap in (2, 5, 8)],
                        fades=fades)
    assert [p for p in problems if p.startswith("fades")] == []


def test_a_transition_from_the_wrong_stage_is_flagged(tmp_path):
    """The log claims the element went reduced -> probe without ever leaving full."""
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", 2)],
                        fades=[fade_record("apex", "reduced_to_probe", 2)])
    assert any("but the element was at 'full'" in p for p in problems), problems


def test_censoring_outside_a_probe_is_flagged(tmp_path):
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", 2)],
                        fades=[fade_record("apex", "censored", 2)])
    assert any("censored" in p and "not in probe" in p for p in problems), problems


def test_an_element_censored_twice_is_flagged(tmp_path):
    fades = [fade_record("apex", "full_to_reduced", 1),
             fade_record("apex", "reduced_to_probe", 2),
             fade_record("apex", "censored", 3),
             fade_record("apex", "censored", 3)]
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", lap) for lap in (1, 2, 3)], fades=fades)
    assert any("censored 2 times" in p for p in problems), problems


def test_a_miscounted_reversion_is_flagged(tmp_path):
    fades = [fade_record("apex", "full_to_reduced", 1),
             fade_record("apex", "reduced_to_probe", 2),
             fade_record("apex", "probe_to_revert", 3, reversion_count=2)]
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", lap) for lap in (1, 2, 3)], fades=fades)
    assert any("reversion number 1" in p for p in problems), problems


def test_a_quorum_share_that_disagrees_with_its_own_corner_list_is_flagged(tmp_path):
    bad = fade_record("apex", "full_to_reduced", 2, qualified=("1", "2"), applicable=4)
    bad["quorum"]["qualified_share"] = 1.0        # says 100%, lists 2 of 4
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", 2)], fades=[bad])
    assert any("reports share 1.0 but lists 2 of 4" in p for p in problems), problems


def test_a_fade_on_a_lap_with_no_pass_is_flagged(tmp_path):
    """Every transition but censoring is caused BY a closed pass."""
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", 0)],
                        fades=[fade_record("apex", "full_to_reduced", 7)])
    assert any("no pass record exists for that lap" in p for p in problems), problems


def test_a_censoring_event_past_the_last_pass_is_allowed(tmp_path):
    """Censoring is stamped at block end, which is after the last closed pass."""
    fades = [fade_record("apex", "full_to_reduced", 1),
             fade_record("apex", "reduced_to_probe", 2),
             fade_record("apex", "censored", 99)]
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", lap) for lap in (1, 2)], fades=fades)
    assert [p for p in problems if p.startswith("fades")] == [], problems


def test_elements_are_replayed_independently(tmp_path):
    """One element's stage must not be read as another's."""
    fades = [fade_record("apex", "full_to_reduced", 1),
             fade_record("braking", "full_to_reduced", 2),
             fade_record("apex", "reduced_to_probe", 3),
             fade_record("corner_speed", "full_to_reduced", 3)]
    problems, _ = check(tmp_path, manifest_doc=manifest(),
                        passes=[pass_record("1", lap) for lap in (1, 2, 3)], fades=fades)
    assert [p for p in problems if p.startswith("fades")] == [], problems


# --- the golden corpus, replayed through the checker -------------------------

def test_every_golden_trace_replays_cleanly_through_the_checker(tmp_path):
    """The two halves of the parity regime must agree about what is legal.

    A sequence the controller CAN produce must never be one the integrity checker
    rejects, or a perfectly good participant block would be flagged as corrupt.
    """
    from pathlib import Path

    from trace_kit.controller import Controller

    repo_root = Path(__file__).resolve().parents[2]
    cfg = json.loads((repo_root / "configs" / "controller_config.json").read_text("utf-8"))
    for path in sorted((repo_root / "golden_traces").glob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        merged = json.loads(json.dumps(cfg))
        for section, values in trace.get("config_overrides", {}).items():
            merged[section].update(values)
        ctrl = Controller(merged, trace["applicable"])
        events = []
        for p in trace["passes"]:
            events.extend(ctrl.step(p))
        if "finish" in trace:
            events.extend(ctrl.finish(trace["finish"]["lap"], trace["finish"]["t"]))
        records = [dict(e, schema_version=1, block_id=BLOCK) for e in events]
        passes = [{"lap": p["lap"]} for p in trace["passes"]]
        problems = integrity.check_fades(records, passes)
        assert problems == [], "{}: {}".format(path.name, problems)
