"""Post-session integrity checker for a recorded block (impl-plan M1 / eval-plan
integrity check).

Verifies that a block's outputs are complete and gap-free before the data is
trusted:

  * the session manifest parses and validates against its schema;
  * the ticks CSV header matches configs/ticks_columns.json exactly (order +
    names) — the runtime writes the header from that descriptor, so a mismatch
    means a contract drift;
  * the per-tick clock `t` is strictly increasing with no gap larger than
    ``max_gap_s`` (default 0.5 s, the eval-plan threshold);
  * the `lap` counter never decreases;
  * the manifest's ``laps_completed`` reconciles with the lap span in the ticks;
  * the per-pass and fade-event JSON-Lines streams parse, validate against their
    schemas, and are internally consistent with the block and with each other
    (M4: "fade-event log parses" is one of the eval plan's integrity clauses).

``check_block`` returns a list of human-readable problem strings (empty == pass)
plus a small summary dict. The module is also runnable as a CLI over a directory
of blocks. Stdlib only (csv/json) — no pandas dependency.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from trace_kit import validate as pyval

REPO_ROOT = Path(__file__).resolve().parents[2]
TICKS_COLUMNS = REPO_ROOT / "configs" / "ticks_columns.json"

DEFAULT_MAX_GAP_S = 0.5


def expected_columns():
    """Ordered list of column names from the canonical ticks descriptor."""
    with open(TICKS_COLUMNS, encoding="utf-8") as f:
        descriptor = json.load(f)
    return [c["name"] for c in descriptor["columns"]]


def check_manifest(manifest_path):
    """Validate the manifest file against its schema. Returns (problems, data)."""
    problems = []
    if not manifest_path.exists():
        return ["manifest missing: {}".format(manifest_path)], None
    errors = pyval.validate_file(manifest_path, "session_manifest")
    for e in errors:
        problems.append("manifest schema: {}".format(e))
    data = None
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        problems.append("manifest unreadable: {}".format(e))
    return problems, data


def check_ticks(ticks_path, columns, max_gap_s=DEFAULT_MAX_GAP_S, aborted=False):
    """Scan the ticks CSV for header, monotonicity, gaps. Returns (problems, summary).

    summary keys (present when at least one data row was read): row_count,
    min_lap, max_lap, duration_s, max_gap_s.

    `aborted` excuses one case only: a block the experimenter aborted before a
    single tick was written is empty on purpose, so "header but no data rows" is
    the explained outcome rather than a fault. Every other check still applies --
    whatever an aborted block did record has to be well formed.
    """
    problems = []
    summary = {"row_count": 0}
    if not ticks_path.exists():
        return ["ticks missing: {}".format(ticks_path)], summary

    with open(ticks_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return ["ticks file is empty (no header)"], summary

        if header != columns:
            problems.append(
                "ticks header mismatch:\n  expected {}\n  found    {}".format(columns, header)
            )
            # Without a trustworthy header we can't index columns reliably.
            return problems, summary

        t_idx = columns.index("t")
        lap_idx = columns.index("lap")
        prev_t = None
        prev_lap = None
        first_t = None
        min_lap = None
        max_lap = None
        worst_gap = 0.0
        n = 0

        for lineno, row in enumerate(reader, start=2):
            if len(row) != len(columns):
                problems.append(
                    "line {}: expected {} fields, got {}".format(lineno, len(columns), len(row))
                )
                continue
            try:
                t = float(row[t_idx])
                lap = int(row[lap_idx])
            except ValueError as e:
                problems.append("line {}: unparseable t/lap ({})".format(lineno, e))
                continue

            n += 1
            if first_t is None:
                first_t = t
            if prev_t is not None:
                delta = t - prev_t
                if delta <= 0:
                    problems.append(
                        "line {}: t not increasing ({:.4f} -> {:.4f})".format(lineno, prev_t, t)
                    )
                else:
                    if delta > worst_gap:
                        worst_gap = delta
                    if delta > max_gap_s:
                        problems.append(
                            "line {}: gap of {:.3f}s exceeds {:.3f}s".format(lineno, delta, max_gap_s)
                        )
            if prev_lap is not None and lap < prev_lap:
                problems.append(
                    "line {}: lap decreased ({} -> {})".format(lineno, prev_lap, lap)
                )
            min_lap = lap if min_lap is None else min(min_lap, lap)
            max_lap = lap if max_lap is None else max(max_lap, lap)
            prev_t = t
            prev_lap = lap

        summary["row_count"] = n
        if n > 0:
            summary["min_lap"] = min_lap
            summary["max_lap"] = max_lap
            summary["duration_s"] = round(prev_t - first_t, 3)
            summary["max_gap_s"] = round(worst_gap, 4)
        elif not aborted:
            problems.append("ticks file has a header but no data rows")

    return problems, summary


def reconcile_laps(manifest_data, ticks_summary):
    """Cross-check manifest laps_completed against the lap span seen in ticks."""
    problems = []
    if manifest_data is None or "max_lap" not in ticks_summary:
        return problems  # nothing to reconcile against
    declared = manifest_data.get("laps_completed")
    if declared is None:
        problems.append("manifest has no laps_completed to reconcile")
        return problems
    observed = ticks_summary["max_lap"] - ticks_summary["min_lap"]
    if declared != observed:
        problems.append(
            "lap mismatch: manifest laps_completed={} but ticks span {} lap(s)".format(
                declared, observed
            )
        )
    return problems


def read_jsonl(path, format_name, block_id):
    """Parse and schema-validate a JSON-Lines stream. Returns (problems, records).

    A missing file is NOT a problem here: passes_*.jsonl exists only when the
    block had an annotation, and fades_*.jsonl only when it had a reference too.
    A dev block legitimately has neither, and a reference-lap recording is a dev
    block by construction. The caller decides whether absence is expected.
    """
    problems, records = [], []
    if not path.exists():
        return problems, None
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append("{} line {}: unparseable ({})".format(path.name, number, e))
                continue
            for error in pyval.validate_data(format_name, record):
                problems.append("{} line {}: {}".format(path.name, number, error))
            if record.get("block_id") != block_id:
                problems.append(
                    "{} line {}: block_id {!r} does not match the manifest's {!r}".format(
                        path.name, number, record.get("block_id"), block_id))
            records.append(record)
    return problems, records


# The transitions a single element may make, as (from, to). `censored` and
# `cap_reached` annotate the state rather than change it, so they are handled
# separately below.
_STAGE_MOVES = {
    "full_to_reduced": ("full", "reduced"),
    "reduced_to_probe": ("reduced", "probe"),
    "probe_to_removed": ("probe", "removed"),
    "probe_to_revert": ("probe", "reduced"),
    "reduced_to_full": ("reduced", "full"),
}


def _transition_counts(records, transition):
    out = {}
    for r in records:
        if r["transition"] == transition:
            out[r["element"]] = out.get(r["element"], 0) + 1
    return out


def check_fades(fades, passes):
    """Problems in a block's fade-event stream beyond schema validity.

    Schema validity says each record is well formed; it says nothing about the
    SEQUENCE being one a state machine could have produced. These checks are the
    offline half of the golden-trace suite: the traces prove the controller can
    only emit legal sequences, and this proves the sequence on disk is one of
    them -- which is what catches a corrupted, truncated or hand-edited log
    before it reaches the RQ1 fade timeline.
    """
    problems = []
    if fades is None:
        return problems

    stage = {}
    reversions = {}
    for record in fades:
        element = record["element"]
        transition = record["transition"]
        current = stage.get(element, "full")

        if transition in _STAGE_MOVES:
            src, dst = _STAGE_MOVES[transition]
            if current != src:
                problems.append(
                    "fades: {} {} at lap {} but the element was at {!r}".format(
                        element, transition, record["lap"], current))
            stage[element] = dst
            if transition == "probe_to_revert":
                reversions[element] = reversions.get(element, 0) + 1
                if record.get("reversion_count") not in (None, reversions[element]):
                    problems.append(
                        "fades: {} probe_to_revert at lap {} carries reversion_count "
                        "{} but is reversion number {}".format(
                            element, record["lap"], record["reversion_count"],
                            reversions[element]))
        elif transition == "censored" and current != "probe":
            problems.append(
                "fades: {} censored at lap {} but the element was at {!r}, not in "
                "probe".format(element, record["lap"], current))
        elif transition == "cap_reached" and current != "reduced":
            problems.append(
                "fades: {} cap_reached at lap {} but the element was at {!r}".format(
                    element, record["lap"], current))

        share = record["quorum"]["qualified_share"]
        applicable = record["quorum"]["applicable_corners"]
        counted = len(record["quorum"]["qualified_corners"])
        if applicable and abs(share - counted / applicable) > 1e-6:
            problems.append(
                "fades: {} {} at lap {} reports share {} but lists {} of {} "
                "qualified corners".format(element, transition, record["lap"],
                                           share, counted, applicable))

    # Censoring is a block-end event, so an element can only be censored once.
    for element, count in _transition_counts(fades, "censored").items():
        if count > 1:
            problems.append("fades: {} censored {} times".format(element, count))

    if passes:
        pass_laps = {p["lap"] for p in passes}
        for record in fades:
            # A censoring event is stamped at block end and may sit past the last
            # closed pass; every other event is caused BY a pass.
            if record["transition"] != "censored" and record["lap"] not in pass_laps:
                problems.append(
                    "fades: {} {} at lap {} but no pass record exists for that "
                    "lap".format(record["element"], record["transition"], record["lap"]))
    return problems


def check_passes(passes):
    """Problems in a block's per-pass stream beyond schema validity."""
    problems = []
    if not passes:
        return problems
    for record in passes:
        if record["t_exit"] < record["t_entry"]:
            problems.append("passes: {} lap {} closes before it opens".format(
                record["corner_id"], record["lap"]))
        # An invalid pass still feeds the controller (eval plan v2), so a missing
        # reason list on an invalid pass means the reason was lost, not that the
        # pass was fine.
        if not record["valid"] and not record.get("invalid_reasons"):
            problems.append("passes: {} lap {} is invalid with no reason given".format(
                record["corner_id"], record["lap"]))
    # One pass per corner per lap is the M2 exit criterion; a duplicate means the
    # tracker double-fired and the controller saw one corner's evidence twice.
    seen = set()
    for record in passes:
        key = (record["corner_id"], record["lap"])
        if key in seen:
            problems.append("passes: corner {} has more than one pass on lap {}".format(*key))
        seen.add(key)
    return problems


def check_block(manifest_path, ticks_path=None, max_gap_s=DEFAULT_MAX_GAP_S, columns=None):
    """Run all checks for one block. Returns (problems, summary).

    If ``ticks_path`` is omitted it is derived from the manifest's block_id
    (ticks_<block_id>.csv next to the manifest).
    """
    manifest_path = Path(manifest_path)
    if columns is None:
        columns = expected_columns()

    problems, manifest_data = check_manifest(manifest_path)

    if ticks_path is None:
        block_id = manifest_data.get("block_id") if manifest_data else None
        if block_id:
            ticks_path = manifest_path.parent / "ticks_{}.csv".format(block_id)
        else:
            problems.append("cannot locate ticks file (no block_id in manifest)")
            return problems, {"row_count": 0}
    ticks_path = Path(ticks_path)

    tick_problems, summary = check_ticks(
        ticks_path, columns, max_gap_s,
        aborted=bool((manifest_data or {}).get("aborted")))
    problems.extend(tick_problems)
    problems.extend(reconcile_laps(manifest_data, summary))

    # M4: the per-pass and fade-event streams. Both are optional on disk (a dev
    # block has no annotation and no reference), but a PARTICIPANT block missing
    # them recorded no evidence at all, which is exactly what the eval plan's
    # integrity clause exists to catch the same day rather than at analysis.
    block_id = (manifest_data or {}).get("block_id")
    if block_id:
        pass_problems, passes = read_jsonl(
            manifest_path.parent / "passes_{}.jsonl".format(block_id), "passes", block_id)
        fade_problems, fades = read_jsonl(
            manifest_path.parent / "fades_{}.jsonl".format(block_id), "fades", block_id)
        problems.extend(pass_problems)
        problems.extend(fade_problems)
        problems.extend(check_passes(passes))
        problems.extend(check_fades(fades, passes))
        summary["pass_count"] = len(passes) if passes is not None else None
        summary["fade_count"] = len(fades) if fades is not None else None
        # An ABORTED block is excused the evidence requirements below, exactly
        # as a dev block is, but for a different reason: the experimenter
        # discarded it on purpose and the manifest says why, so "this block has
        # no evidence in it" is the expected outcome rather than a fault to
        # chase. It is NOT excused schema validity or stream well-formedness --
        # whatever it did record still has to be readable, because an abort
        # discards the block, never the record of what happened.
        excused = bool(manifest_data) and (
            manifest_data.get("dev_block") or manifest_data.get("aborted"))
        if manifest_data and not excused:
            if passes is None:
                problems.append(
                    "no passes_{}.jsonl: a participant block that records no corner "
                    "passes has no evidence in it".format(block_id))
            if fades is None and manifest_data.get("condition") != "off":
                problems.append(
                    "no fades_{}.jsonl: the controller did not run, so this block has "
                    "no fade-event log".format(block_id))
    return problems, summary


def find_blocks(directory):
    """Yield manifest paths in a directory (manifest_*.json)."""
    return sorted(Path(directory).glob("manifest_*.json"))


# --- instruments ("questionnaire files saved", eval plan Phase 3) -----------
#
# Session-scoped instruments: one per participant per session. NASA-TLX is
# handled separately because it is BLOCK-scoped -- it is administered
# immediately after each session-2 training block, and a TLX score with no block
# attached cannot be compared between conditions, which is the one thing the
# eval plan asks of it.
SESSION_INSTRUMENTS = {
    1: ("pre_study",),
    3: ("post_study", "interview"),
}
BLOCK_INSTRUMENT_SESSION = 2
BLOCK_INSTRUMENT = "nasa_tlx"


def read_instruments(directory):
    """Parse and schema-validate every instrument_*.json. Returns (problems, records)."""
    problems, records = [], []
    for path in sorted(Path(directory).glob("instrument_*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            problems.append("{}: unreadable ({})".format(path.name, e))
            continue
        errors = pyval.validate_data("instrument", doc)
        for error in errors:
            problems.append("{}: {}".format(path.name, error))
        if not errors:
            records.append((path.name, doc))
    return problems, records


def check_instruments(directory, manifests):
    """Problems where a recorded session is missing its instrument files.

    `manifests` is a list of (name, manifest_dict), as `check_apparatus_drift`
    takes. Dev blocks are skipped (scratch recordings answer no questionnaires)
    and so are aborted blocks (the block was discarded, so the instrument that
    would have followed it was never administered). Dry-run blocks are NOT
    skipped: rehearsing the protocol without the questionnaires is exactly the
    rehearsal that would not catch a missing questionnaire.
    """
    problems, records = read_instruments(directory)

    have_session = set()     # (participant_id, session, instrument)
    have_block = set()       # (block_id, instrument)
    for _, doc in records:
        have_session.add((doc["participant_id"], doc["session"], doc["instrument"]))
        if doc.get("block_id"):
            have_block.add((doc["block_id"], doc["instrument"]))

    blocks = [(n, m) for n, m in manifests
              if m and not m.get("dev_block") and not m.get("aborted")]
    known_block_ids = {m.get("block_id") for _, m in blocks}

    # Every session that produced a block must have produced its instruments.
    want_session = set()
    for _, m in blocks:
        session = m.get("session")
        for instrument in SESSION_INSTRUMENTS.get(session, ()):
            want_session.add((m.get("participant_id"), session, instrument))
    for participant, session, instrument in sorted(want_session):
        if (participant, session, instrument) not in have_session:
            problems.append(
                "no {} instrument for participant {!r} session {}: the eval plan's "
                "integrity check requires questionnaire files saved the same day".format(
                    instrument, participant, session))

    # Session-2 training blocks each need their own TLX.
    for _, m in blocks:
        if m.get("session") != BLOCK_INSTRUMENT_SESSION:
            continue
        block_id = m.get("block_id")
        if (block_id, BLOCK_INSTRUMENT) not in have_block:
            problems.append(
                "no {} instrument for training block {}: TLX is administered "
                "immediately after each session-2 block".format(BLOCK_INSTRUMENT, block_id))

    # An instrument pointing at a block that is not here is a filing error, and
    # the same-day check is the only cheap moment to notice it.
    for name, doc in records:
        block_id = doc.get("block_id")
        if block_id and block_id not in known_block_ids:
            problems.append(
                "{}: block_id {!r} matches no manifest in this directory".format(
                    name, block_id))

    return problems


# Fields that must not drift across a study's blocks. The risk register's
# "pin CSP + AC versions at M3, updates forbidden until data collection ends" is
# only a pin if something checks it: the runtime stamps the detected versions
# into every manifest, and this compares them across blocks.
PINNED_VERSION_FIELDS = ("app", "csp", "ac")


def check_apparatus_drift(manifests):
    """Problems where study blocks disagree about the apparatus they ran on.

    `manifests` is a list of (name, manifest_dict). Dev blocks are excluded --
    they are scratch recordings and may legitimately predate a pin. Blocks with
    no version data at all (recorded before M3 stamped it) are skipped rather
    than reported, so historical blocks do not raise a permanent alarm.
    """
    problems = []
    study = [(n, m) for n, m in manifests if m and not m.get("dev_block")]

    for field in PINNED_VERSION_FIELDS:
        seen = {}
        for name, m in study:
            value = (m.get("versions") or {}).get(field)
            if value:
                seen.setdefault(value, []).append(name)
        if len(seen) > 1:
            problems.append(
                "apparatus drift: versions.{} differs across blocks -- {}".format(
                    field,
                    "; ".join("{} in {}".format(v, ", ".join(sorted(b)))
                              for v, b in sorted(seen.items())),
                )
            )
        if any(str(v).startswith("unknown") for v in seen):
            problems.append(
                "versions.{} is unrecorded on some blocks; the apparatus is not "
                "pinned for them".format(field)
            )

    # Track length is per track, so only blocks on the SAME track are comparable.
    by_track = {}
    for name, m in study:
        if m.get("track_id") and m.get("track_length_m"):
            by_track.setdefault(m["track_id"], {}).setdefault(
                round(m["track_length_m"], 1), []).append(name)
    for track, lengths in by_track.items():
        if len(lengths) > 1:
            problems.append(
                "track_length_m disagrees on {}: {} -- every spline-to-metre "
                "conversion depends on it".format(track, sorted(lengths)))

    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="TRACE block integrity checker (M1).")
    parser.add_argument("path", help="a manifest_*.json file, or a directory of blocks")
    parser.add_argument("--max-gap", type=float, default=DEFAULT_MAX_GAP_S,
                        help="max allowed gap between ticks, seconds (default 0.5)")
    parser.add_argument("--no-instruments", action="store_true",
                        help="skip the questionnaire-files-saved check. Intended for "
                             "scanning a mixed archive of old test recordings; the "
                             "after-every-session check should run it.")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if path.is_dir():
        manifests = find_blocks(path)
        if not manifests:
            print("no manifest_*.json found in {}".format(path))
            return 1
    else:
        manifests = [path]

    columns = expected_columns()
    any_failed = False
    loaded = []
    for manifest_path in manifests:
        problems, summary = check_block(manifest_path, max_gap_s=args.max_gap, columns=columns)
        status = "PASS" if not problems else "FAIL"
        if problems:
            any_failed = True
        detail = "{} ticks".format(summary.get("row_count", 0))
        if summary.get("pass_count") is not None:
            detail += ", {} passes".format(summary["pass_count"])
        if summary.get("fade_count") is not None:
            detail += ", {} fades".format(summary["fade_count"])
        _, data = check_manifest(manifest_path)
        # An abort is not a failure, but it must never read as a clean block:
        # the status line is what the experimenter checks after each session.
        if (data or {}).get("aborted"):
            detail += ", ABORTED: {}".format(data.get("abort_reason", "?"))
        print("[{}] {}  ({})".format(status, manifest_path.name, detail))
        for p in problems:
            print("    - {}".format(p))
        loaded.append((manifest_path.name, data))

    # The instrument check is directory-scoped: the files sit next to the blocks.
    if path.is_dir() and not args.no_instruments:
        missing = check_instruments(path, loaded)
        status = "PASS" if not missing else "FAIL"
        print("[{}] instrument files".format(status))
        for p in missing:
            print("    - {}".format(p))
        if missing:
            any_failed = True

    # Cross-block checks only mean something over a set of blocks.
    if len(loaded) > 1:
        drift = check_apparatus_drift(loaded)
        status = "PASS" if not drift else "FAIL"
        print("[{}] apparatus consistency across {} block(s)".format(status, len(loaded)))
        for p in drift:
            print("    - {}".format(p))
        if drift:
            any_failed = True
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
