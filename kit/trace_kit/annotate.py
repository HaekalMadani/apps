"""Assemble drive-and-mark captures into a draft corner annotation (impl-plan
M2 / §2.2).

The in-game annotator mode (lua/trace_rt/lib/annotator.lua) writes a marks file:
one JSON object per line, each a landmark the experimenter tagged while driving
slowly --

    {"track": "...", "corner_id": "T1", "type": "medium", "compound": false,
     "role": "entry", "spline": 0.081, "pos": [x, y, z]}

This tool groups those marks by corner, maps each role to the annotation schema
shape, and writes a draft ``annotation_<track>.json``. The draft is validated
against schemas/annotation.schema.json before writing and is meant for manual
cleanup (naming corners, nudging spline values) -- it is a starting point, not a
finished file. Roles:

    entry        -> corner.entry_gate
    exit         -> corner.exit_gate
    brake_start  -> zones.braking.start   (optional pair -- see below)
    brake_end    -> zones.braking.end
    cs_start     -> zones.corner_speed.start
    cs_end       -> zones.corner_speed.end
    apex         -> zones.apex_gates[]   (one or more; compound corners repeat it)

``zones.apex_window_half_m`` has no mark of its own -- it is the half-width of
the window centred on each apex gate over which RMS lateral deviation is taken
-- so the assembler seeds the default and G0's on-track review confirms it.

Beyond completeness, the assembler checks each corner's *geometry*: landmarks
must run in driving order along two chains -- entry -> brake_start -> brake_end
-> exit, and entry -> cs_start -> apex(es) -> cs_end -> exit -- every apex gate
must fall inside the corner-speed window, and pass brackets must not overlap
between corners. The chains are separate because a trail-braking driver is
still braking past turn-in, so the braking zone may overlap the corner-speed
window. Corners straddling start/finish are unwrapped first.

The brake marks are an all-or-neither pair: skip both on a corner taken flat
(no braking zone => the corner is not applicable to the braking-point element),
but one without the other is reported as a problem.

Stdlib + trace_kit.validate only. Runnable as a CLI.
"""

import argparse
import json
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

from trace_kit import validate as pyval

# role -> where its spline lands. apex is many-valued and handled separately.
SINGLE_ROLE_TARGET = {
    "entry": ("entry_gate",),
    "exit": ("exit_gate",),
    "brake_start": ("zones", "braking", "start"),
    "brake_end": ("zones", "braking", "end"),
    "cs_start": ("zones", "corner_speed", "start"),
    "cs_end": ("zones", "corner_speed", "end"),
}

# Every role a complete corner needs (apex counts as >= 1 apex mark).
# brake_start/brake_end are NOT here: a no-braking corner legitimately omits
# both. They are validated as an all-or-neither pair in assemble().
REQUIRED_ROLES = ("entry", "exit", "cs_start", "cs_end")

# Half-width (metres of track length) of the apex evaluation window, written
# into every assembled corner. It is not a driven landmark -- there is nothing
# to press a button at -- so the assembler seeds the impl-plan section 7 default
# and the value is reviewed per corner on track at Gate G0, like every other
# gate. Kept in the annotation rather than the controller config because it is a
# property of the corner's geometry, not a tuned controller parameter.
DEFAULT_APEX_WINDOW_HALF_M = 20.0


def read_marks(marks_path):
    """Parse a marks JSONL file into a list of mark dicts. Blank lines ignored."""
    marks = []
    with open(marks_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                marks.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("marks line {}: {}".format(lineno, e))
    return marks


def _set_path(corner, path, value):
    """Set corner[path[0]][path[1]]... = value, creating intermediate dicts."""
    node = corner
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def _get_path(corner, path):
    """Read corner[path[0]][path[1]]..., or None if any level is absent."""
    node = corner
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


# Landmark order along the spline, as two independent chains. They are kept
# separate because the braking zone and the corner-speed window legitimately
# OVERLAP: a driver trail-braking is still on the brakes past turn-in, so
# brake_end may fall after cs_start. What is never valid is a chain running
# backwards within itself.
LANDMARK_CHAINS = (
    (("entry", ("entry_gate",)),
     ("brake_start", ("zones", "braking", "start")),
     ("brake_end", ("zones", "braking", "end")),
     ("exit", ("exit_gate",))),
    (("entry", ("entry_gate",)),
     ("cs_start", ("zones", "corner_speed", "start")),
     ("apex", None),                       # expands to every apex gate
     ("cs_end", ("zones", "corner_speed", "end")),
     ("exit", ("exit_gate",))),
)


def check_geometry(corner):
    """Problems with one corner's landmark *geometry*, as a list of strings.

    Completeness (are the roles present?) is checked in assemble(); this asks
    whether the splines are ordered the way the corner is actually driven. The
    easy capture mistake -- pressing cs_start after the apex -- otherwise
    assembles into a schema-valid file that measures the wrong thing, and would
    not surface until the G0 gate review on track.

    A corner straddling start/finish is unwrapped before comparison, so the
    fixture's T4 (entry 0.97, exit 0.03) is legal; this matches pass_tracker's
    forward-wrap handling.
    """
    problems = []
    corner_id = corner.get("id")
    entry = corner.get("entry_gate")
    exit_gate = corner.get("exit_gate")
    wraps = (entry is not None and exit_gate is not None and exit_gate < entry)

    def unwrap(spline):
        """Put a post-start/finish landmark after the entry gate, not before."""
        return spline + 1.0 if (wraps and spline < entry) else spline

    for chain in LANDMARK_CHAINS:
        landmarks = []
        for role, path in chain:
            if role == "apex":
                for spline in sorted(corner.get("zones", {}).get("apex_gates") or []):
                    landmarks.append(("apex", unwrap(spline)))
            else:
                spline = _get_path(corner, path)
                if spline is not None:
                    landmarks.append((role, unwrap(spline)))
        if len(landmarks) < 2:
            continue
        expected = " -> ".join(r for r, _ in landmarks)
        for i in range(len(landmarks) - 1):
            role_a, a = landmarks[i]
            role_b, b = landmarks[i + 1]
            if b < a:
                problems.append(
                    "corner {}: {} ({:.4f}) is not before {} ({:.4f}); expected "
                    "order {}".format(corner_id, role_a, a % 1.0, role_b, b % 1.0, expected)
                )

    # The corner-speed window is where minimum speed is searched for, so it has
    # to bracket the apex rather than follow it.
    cs_start = _get_path(corner, ("zones", "corner_speed", "start"))
    cs_end = _get_path(corner, ("zones", "corner_speed", "end"))
    if cs_start is not None and cs_end is not None:
        span = (cs_end - cs_start) % 1.0
        for spline in corner.get("zones", {}).get("apex_gates") or []:
            if (spline - cs_start) % 1.0 > span:
                problems.append(
                    "corner {}: apex {:.4f} is outside the corner_speed window "
                    "{:.4f}-{:.4f}; the window must bracket the apex".format(
                        corner_id, spline, cs_start, cs_end)
                )
    return problems


def check_gate_overlap(corners):
    """Problems where one corner's pass bracket runs into another's.

    entry/exit gates bracket a pass. Overlapping brackets put a tick inside two
    corners at once, which the pass tracker cannot resolve.
    """
    problems = []
    bracketed = [c for c in corners
                 if c.get("entry_gate") is not None and c.get("exit_gate") is not None]
    ordered = sorted(bracketed, key=lambda c: c["entry_gate"])
    for prev, cur in zip(ordered, ordered[1:]):
        # A wrapping corner's exit sorts below its entry; it is handled below.
        if prev["exit_gate"] < prev["entry_gate"]:
            continue
        if cur["entry_gate"] < prev["exit_gate"]:
            problems.append(
                "corner {} entry ({:.4f}) is inside corner {}'s bracket "
                "({:.4f}-{:.4f})".format(cur["id"], cur["entry_gate"], prev["id"],
                                         prev["entry_gate"], prev["exit_gate"])
            )
    # The wrapping corner runs past start/finish into the first corner.
    for c in bracketed:
        if c["exit_gate"] < c["entry_gate"] and ordered and c is not ordered[0]:
            first = ordered[0]
            if c["exit_gate"] > first["entry_gate"]:
                problems.append(
                    "corner {} wraps to {:.4f}, past corner {}'s entry ({:.4f})".format(
                        c["id"], c["exit_gate"], first["id"], first["entry_gate"])
                )
    return problems


def assemble(marks, track=None):
    """Build a draft annotation document from marks. Returns (doc, problems).

    `problems` lists corners missing required roles, corners whose landmarks
    are out of driving order or whose brackets overlap, and any track mismatch;
    the doc is still returned so it can be inspected, but callers should treat a
    non-empty problems list as "needs manual completion before use".
    """
    problems = []

    # Resolve the track: explicit arg wins, else the marks' own `track` field.
    track_values = {m.get("track") for m in marks if m.get("track") is not None}
    if track is None:
        if len(track_values) == 1:
            track = next(iter(track_values))
        elif len(track_values) > 1:
            problems.append("marks span multiple tracks: {}".format(sorted(track_values)))
            track = sorted(track_values)[0]
        else:
            problems.append("no track given and marks carry no track field")
            track = "UNKNOWN_TRACK"
    elif track_values and track_values != {track}:
        problems.append(
            "track arg {!r} disagrees with marks {}".format(track, sorted(track_values))
        )

    # Group marks by corner, preserving first-seen order.
    by_corner = OrderedDict()
    for m in marks:
        by_corner.setdefault(m["corner_id"], []).append(m)

    corners = []
    for corner_id, cmarks in by_corner.items():
        corner = {"id": corner_id, "zones": {}}

        # type / compound come off the marks; flag inconsistency rather than guess.
        types = {m.get("type") for m in cmarks if m.get("type") is not None}
        if len(types) == 1:
            corner["type"] = next(iter(types))
        elif len(types) > 1:
            problems.append("corner {}: inconsistent type {}".format(corner_id, sorted(types)))
            corner["type"] = sorted(types)[0]
        compounds = {bool(m.get("compound")) for m in cmarks}
        corner["compound"] = any(compounds)
        if len(compounds) > 1:
            problems.append("corner {}: inconsistent compound flag".format(corner_id))

        apex_splines = []
        seen_roles = set()
        for m in cmarks:
            role = m.get("role")
            seen_roles.add(role)
            if role == "apex":
                apex_splines.append(m["spline"])
            elif role in SINGLE_ROLE_TARGET:
                _set_path(corner, SINGLE_ROLE_TARGET[role], m["spline"])
            else:
                problems.append("corner {}: unknown role {!r}".format(corner_id, role))

        if apex_splines:
            corner["zones"]["apex_gates"] = apex_splines
        else:
            problems.append("corner {}: no apex mark".format(corner_id))
        corner["zones"]["apex_window_half_m"] = DEFAULT_APEX_WINDOW_HALF_M

        missing = [r for r in REQUIRED_ROLES if r not in seen_roles]
        if missing:
            problems.append("corner {}: missing roles {}".format(corner_id, missing))

        if ("brake_start" in seen_roles) != ("brake_end" in seen_roles):
            problems.append(
                "corner {}: brake marks are all-or-neither (skip both on a "
                "no-braking corner); got only one of brake_start/brake_end".format(corner_id)
            )

        problems.extend(check_geometry(corner))

        corners.append(corner)

    problems.extend(check_gate_overlap(corners))

    doc = OrderedDict(
        [
            ("schema_version", 1),
            ("track", track),
            (
                "notes",
                "DRAFT auto-assembled by annotate.py on {}. Review and clean "
                "(names, spline values) before use.".format(date.today().isoformat()),
            ),
            ("corners", corners),
        ]
    )
    return doc, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assemble marks into a draft annotation (M2).")
    parser.add_argument("marks", help="a marks_*.jsonl capture file")
    parser.add_argument("--track", default=None, help="track full id (else read from marks)")
    parser.add_argument("-o", "--out", default=None,
                        help="output path (default annotation_<track>.json next to marks)")
    args = parser.parse_args(argv)

    marks = read_marks(Path(args.marks))
    if not marks:
        print("no marks in {}".format(args.marks))
        return 1

    doc, problems = assemble(marks, track=args.track)

    schema_errors = pyval.validate_data("annotation", doc)

    out = Path(args.out) if args.out else \
        Path(args.marks).parent / "annotation_{}.json".format(doc["track"])

    # Write the draft regardless (so the human can fix it), but report loudly.
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print("wrote draft: {}  ({} corner(s))".format(out, len(doc["corners"])))

    for p in problems:
        print("  - problem: {}".format(p))
    for e in schema_errors:
        print("  - schema: {}".format(e))

    return 1 if (problems or schema_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
