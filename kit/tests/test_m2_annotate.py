"""M2 tests: the offline marks -> draft-annotation assembler (trace_kit.annotate).

Pure Python. Checks that a complete set of marks assembles into a schema-valid
annotation, and that missing landmarks are reported rather than silently dropped.
"""

import json

import pytest

from trace_kit import annotate
from trace_kit import validate as pyval

TRACK = "ks_silverstone-national"


def _mark(corner_id, role, spline, ctype="medium", compound=False, pos=(1.0, 2.0, 3.0)):
    return {
        "track": TRACK,
        "corner_id": corner_id,
        "type": ctype,
        "compound": compound,
        "role": role,
        "spline": spline,
        "pos": list(pos),
    }


def _complete_corner(corner_id, base, ctype="medium"):
    """All seven role marks (incl. the optional brake pair) for one simple corner."""
    return [
        _mark(corner_id, "entry", base + 0.00, ctype),
        _mark(corner_id, "brake_start", base + 0.01, ctype),
        _mark(corner_id, "brake_end", base + 0.03, ctype),
        _mark(corner_id, "apex", base + 0.05, ctype),
        _mark(corner_id, "cs_start", base + 0.02, ctype),
        _mark(corner_id, "cs_end", base + 0.07, ctype),
        _mark(corner_id, "exit", base + 0.09, ctype),
    ]


def test_complete_marks_assemble_to_valid_annotation():
    marks = _complete_corner("T1", 0.10) + _complete_corner("T2", 0.40, ctype="hairpin")
    doc, problems = annotate.assemble(marks)

    assert problems == [], problems
    assert pyval.validate_data("annotation", doc) == []
    assert doc["track"] == TRACK
    ids = [c["id"] for c in doc["corners"]]
    assert ids == ["T1", "T2"]                         # first-seen order preserved

    t1 = doc["corners"][0]
    assert t1["entry_gate"] == pytest.approx(0.10)
    assert t1["exit_gate"] == pytest.approx(0.19)
    assert t1["zones"]["braking"]["start"] == pytest.approx(0.11)
    assert t1["zones"]["braking"]["end"] == pytest.approx(0.13)
    assert t1["zones"]["corner_speed"]["start"] == pytest.approx(0.12)
    assert t1["zones"]["corner_speed"]["end"] == pytest.approx(0.17)
    assert t1["zones"]["apex_gates"] == pytest.approx([0.15])


def test_compound_corner_keeps_multiple_apexes():
    marks = _complete_corner("T2", 0.40, ctype="chicane")
    # second apex mark -> compound corner with two apex gates. It has to sit
    # inside the corner-speed window (0.42-0.47), like a real chicane's second
    # apex; check_geometry rejects an apex outside it.
    marks.append(_mark("T2", "apex", 0.46, ctype="chicane", compound=True))
    # make the whole corner compound by flagging its marks
    for m in marks:
        m["compound"] = True
    doc, problems = annotate.assemble(marks)
    assert problems == [], problems
    assert doc["corners"][0]["compound"] is True
    assert doc["corners"][0]["zones"]["apex_gates"] == pytest.approx([0.45, 0.46])
    assert pyval.validate_data("annotation", doc) == []


def test_flat_corner_without_brake_marks_is_complete():
    # A corner taken flat legitimately has no brake marks: no problems, no
    # braking zone in the draft, and the draft is schema-valid (braking-point
    # element simply does not apply to that corner).
    marks = [m for m in _complete_corner("T1", 0.10, ctype="fast")
             if m["role"] not in ("brake_start", "brake_end")]
    doc, problems = annotate.assemble(marks)
    assert problems == [], problems
    assert "braking" not in doc["corners"][0]["zones"]
    assert pyval.validate_data("annotation", doc) == []


def test_lone_brake_mark_is_reported():
    marks = [m for m in _complete_corner("T1", 0.10) if m["role"] != "brake_end"]
    _, problems = annotate.assemble(marks)
    assert any("all-or-neither" in p for p in problems), problems


def test_missing_apex_is_reported():
    marks = [m for m in _complete_corner("T1", 0.10) if m["role"] != "apex"]
    doc, problems = annotate.assemble(marks)
    assert any("no apex" in p for p in problems), problems


def test_missing_gate_role_is_reported():
    marks = [m for m in _complete_corner("T1", 0.10) if m["role"] != "exit"]
    _, problems = annotate.assemble(marks)
    assert any("missing roles" in p and "exit" in p for p in problems), problems


def test_track_resolved_from_marks():
    marks = _complete_corner("T1", 0.10)
    doc, _ = annotate.assemble(marks)            # no explicit track arg
    assert doc["track"] == TRACK


def test_explicit_track_mismatch_reported():
    marks = _complete_corner("T1", 0.10)
    _, problems = annotate.assemble(marks, track="some_other_track")
    assert any("disagrees" in p for p in problems), problems


def test_read_marks_round_trip(tmp_path):
    marks = _complete_corner("T1", 0.10)
    p = tmp_path / "marks_demo.jsonl"
    p.write_text("\n".join(json.dumps(m) for m in marks) + "\n", encoding="utf-8")
    assert annotate.read_marks(p) == marks


# --- geometry: landmarks must run in driving order (check_geometry) ----------


def test_cs_start_after_apex_is_reported():
    # The capture slip the check exists for: pressing cs_start past the apex.
    # It stays schema-valid, so nothing else would catch it before G0.
    marks = _complete_corner("T1", 0.10)
    for m in marks:
        if m["role"] == "cs_start":
            m["spline"] = 0.16          # apex is at 0.15, cs_end at 0.17
    doc, problems = annotate.assemble(marks)
    assert any("cs_start" in p and "not before" in p for p in problems), problems
    assert pyval.validate_data("annotation", doc) == []   # schema alone misses it


def test_apex_outside_corner_speed_window_is_reported():
    marks = _complete_corner("T1", 0.10)      # cs window 0.12-0.17
    for m in marks:
        if m["role"] == "apex":
            m["spline"] = 0.175
    _, problems = annotate.assemble(marks)
    assert any("outside the corner_speed window" in p for p in problems), problems


def test_trail_braking_overlap_is_allowed():
    # brake_end after cs_start is legitimate: a trail-braking driver is still on
    # the brakes past turn-in. The two chains are checked independently.
    marks = _complete_corner("T1", 0.10)
    for m in marks:
        if m["role"] == "brake_end":
            m["spline"] = 0.14           # cs_start 0.12, apex 0.15
    _, problems = annotate.assemble(marks)
    assert problems == [], problems


def test_wrapping_corner_is_not_reported_as_misordered():
    # A corner straddling start/finish: entry 0.97 ... exit 0.03.
    marks = [
        _mark("T4", "entry", 0.97),
        _mark("T4", "brake_start", 0.98),
        _mark("T4", "brake_end", 0.995),
        _mark("T4", "cs_start", 0.999),
        _mark("T4", "apex", 0.01),
        _mark("T4", "cs_end", 0.02),
        _mark("T4", "exit", 0.03),
    ]
    doc, problems = annotate.assemble(marks)
    assert problems == [], problems
    assert pyval.validate_data("annotation", doc) == []


def test_overlapping_pass_brackets_are_reported():
    # T2 opens before T1's exit gate, so a tick sits in both corners at once.
    marks = _complete_corner("T1", 0.10) + _complete_corner("T2", 0.15)
    _, problems = annotate.assemble(marks)
    assert any("inside corner" in p and "bracket" in p for p in problems), problems


def test_real_study_annotations_pass_every_geometry_check():
    # The two committed study annotations are the regression fixtures: both
    # layouts must stay geometrically sound as they are hand-edited.
    import pathlib
    ann_dir = pathlib.Path(__file__).resolve().parents[2] / "configs" / "annotations"
    files = sorted(ann_dir.glob("annotation_*.json"))
    assert files, "no study annotations found in {}".format(ann_dir)
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert pyval.validate_data("annotation", doc) == [], path.name
        problems = annotate.check_gate_overlap(doc["corners"])
        for corner in doc["corners"]:
            problems.extend(annotate.check_geometry(corner))
        assert problems == [], "{}: {}".format(path.name, problems)
