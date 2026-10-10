"""Phase 4 analysis — ingestion and the RQ1 descriptive layer.

Two jobs, deliberately separated:

**Ingestion** (`load_dataset`) turns a directory of recorded blocks into flat,
tidy tables — blocks, laps, passes, fades, instruments — with every exclusion
rule in the evaluation plan applied once, here, rather than re-derived by each
figure. This is the contract between recording and analysis: M6's exit criterion
is that a complete fake-participant dataset is ingested "without manual fixes",
which is a statement about THIS function.

**RQ1** (`rq1`) is the descriptive characterisation the eval plan pre-commits to:
fade trajectories per participant per element, per-corner qualification heatmaps,
time-to-first-fade and time-to-removal distributions, probe outcomes tabulated
held/reverted/censored, reversion-cap hits, and atypical trajectories flagged as
individual cases.

**What is NOT here, by decision (2026-10-09):** the RQ2 Bayesian mixed-effects
model. It needs a stats stack the toolkit does not have (`jsonschema`, `pytest`,
`lupa` and nothing else), and eval plan Phase 4 only requires the analysis
scripts frozen *before results are seen* — not before M6. Ingestion emits the
lap-level table that model consumes, so adding it later is additive. Writing it
against synthetic data now would also mean freezing a model specification whose
only test was data the simulator made up.

Stdlib only (csv/json). Figures are hand-written SVG, the same choice and the
same reasoning as `simulate.feasibility_svg`.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

# Stage names as an ordinal scale, for trajectories and "time to removal".
STAGES = ("full", "reduced", "probe", "removed")
STAGE_INDEX = {name: i for i, name in enumerate(STAGES)}

ELEMENTS = ("braking", "corner_speed", "apex")

# Eval plan Phase 3, "Lap-validity rules (applied uniformly, automated at
# logging time)". `wall_contact` is the awkward one — see lap_validity below.
MAX_WHEELS_OUTSIDE_VALID = 2


# --- block classification ---------------------------------------------------

def block_kind(manifest):
    """Why a block is or is not participant data.

    The three exclusion markers all follow the same schema pattern (present only
    when true) and all mean "never pool this with participant data", but for
    different reasons that the dataset README has to state separately:

      dev    — scratch recording, opted out of the annotation gate (M2)
      abort  — the experimenter discarded it from the panel, with a reason (M6)
      dry    — protocol rehearsal, a full study block in every other respect (M6)
    """
    if manifest.get("dev_block"):
        return "dev"
    if manifest.get("aborted"):
        return "aborted"
    if manifest.get("dry_run"):
        return "dry_run"
    return "study"


# --- lap-level table --------------------------------------------------------

def lap_rows(ticks_path, columns, block_id):
    """Per-lap rows from a ticks CSV: lap number, time span, validity inputs.

    A lap's time is the span of `t` across its ticks, which is exact to one tick
    (0.05 s at 20 Hz) for interior laps and MEANINGLESS for the first and last
    lap of a block, which are partial. Both are marked `partial` and excluded
    from lap-time outcomes — the first lap is already invalid by rule.
    """
    rows = []
    if not ticks_path.exists():
        return rows

    with open(ticks_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return rows
        if header != columns:
            return rows

        idx = {name: header.index(name) for name in
               ("t", "lap", "wheels_outside", "in_pit")}
        current = None
        for raw in reader:
            if len(raw) != len(header):
                continue
            try:
                lap = int(raw[idx["lap"]])
                t = float(raw[idx["t"]])
                wheels = int(raw[idx["wheels_outside"]])
                in_pit = int(raw[idx["in_pit"]])
            except ValueError:
                continue

            if current is None or current["lap"] != lap:
                if current is not None:
                    rows.append(current)
                current = {"block_id": block_id, "lap": lap, "t_start": t, "t_end": t,
                           "tick_count": 0, "max_wheels_outside": 0, "pit": False}
            current["t_end"] = t
            current["tick_count"] += 1
            current["max_wheels_outside"] = max(current["max_wheels_outside"], wheels)
            current["pit"] = current["pit"] or bool(in_pit)
        if current is not None:
            rows.append(current)

    for i, row in enumerate(rows):
        row["lap_time_s"] = round(row["t_end"] - row["t_start"], 3)
        row["partial"] = (i == 0 or i == len(rows) - 1)
        row["first_of_block"] = (i == 0)
    return rows


def lap_validity(lap_row, passes_on_lap):
    """Apply the eval plan's lap-validity rules. Returns (valid, reasons).

    The plan names four: more than two wheels off, wall contact, a pit
    entry/exit, and the first lap of a block. `partial_lap` is a FIFTH reason
    added here, for the block's final lap: its tick span is cut off at the stop,
    so its lap time is an artefact of when the experimenter pressed the button
    rather than a measurement. It is excluded from lap-time outcomes for the
    same reason the first lap is, and it is named separately so the count of
    laps excluded by each rule stays reportable.

    Honest limitation, stated here because it is structural rather than an
    oversight: the plan invalidates a lap where "the car contacts a wall", but
    the tick log has no collision column — collision depth is only captured
    inside a corner's pass bracket. So wall contact is detectable on this lap
    ONLY if it happened inside an annotated corner. A wall contact on a straight
    is invisible to this function. At Silverstone the barriers sit beyond
    run-off, so such a contact almost always sets wheels_outside to 4 first and
    is caught by the track-limits rule instead — "almost always" being exactly
    the kind of claim that belongs in the limitations section rather than in a
    docstring pretending to be a guarantee.
    """
    reasons = []
    if lap_row.get("first_of_block"):
        reasons.append("first_of_block")
    if lap_row.get("partial") and not lap_row.get("first_of_block"):
        reasons.append("partial_lap")
    if lap_row.get("max_wheels_outside", 0) > MAX_WHEELS_OUTSIDE_VALID:
        reasons.append("wheels_outside")
    if lap_row.get("pit"):
        reasons.append("pit")
    for record in passes_on_lap:
        if "wall_contact" in (record.get("invalid_reasons") or []):
            reasons.append("wall_contact")
            break
    return (not reasons), reasons


# --- ingestion --------------------------------------------------------------

def _read_jsonl(path):
    records = []
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_dataset(directory, include=("study",)):
    """Ingest a directory of blocks into flat tables.

    `include` names which block kinds to keep (see `block_kind`). The default is
    participant data only; the M6 dry run passes ("dry_run",) to analyse the
    rehearsal, which is how the rehearsal proves the analysis path works without
    ever letting rehearsal data into a participant figure.

    Returns a dict with keys: blocks, laps, passes, fades, instruments, excluded.
    Every table is a list of plain dicts — tidy rows, no index, nothing that
    needs a dependency to read.
    """
    from trace_kit import integrity   # local import: shares the ticks descriptor

    directory = Path(directory)
    columns = integrity.expected_columns()

    blocks, laps, passes, fades, excluded = [], [], [], [], []

    for manifest_path in sorted(directory.glob("manifest_*.json")):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        kind = block_kind(manifest)
        block_id = manifest.get("block_id")
        if kind not in include:
            excluded.append({"block_id": block_id, "kind": kind,
                             "abort_reason": manifest.get("abort_reason")})
            continue

        block_passes = _read_jsonl(directory / "passes_{}.jsonl".format(block_id))
        block_fades = _read_jsonl(directory / "fades_{}.jsonl".format(block_id))

        blocks.append({
            "block_id": block_id,
            "participant_id": manifest.get("participant_id"),
            "session": manifest.get("session"),
            "condition": manifest.get("condition"),
            "pair_id": manifest.get("pair_id"),
            "sequence": manifest.get("sequence"),
            "track_id": manifest.get("track_id"),
            "car_id": manifest.get("car_id"),
            "laps_completed": manifest.get("laps_completed"),
            "disabled_elements": manifest.get("disabled_elements") or [],
            "kind": kind,
        })

        by_lap = {}
        for record in block_passes:
            by_lap.setdefault(record.get("lap"), []).append(record)

        for row in lap_rows(directory / "ticks_{}.csv".format(block_id), columns, block_id):
            valid, reasons = lap_validity(row, by_lap.get(row["lap"], []))
            row["valid"] = valid
            row["invalid_reasons"] = reasons
            row["participant_id"] = manifest.get("participant_id")
            row["session"] = manifest.get("session")
            row["condition"] = manifest.get("condition")
            row["pair_id"] = manifest.get("pair_id")
            laps.append(row)

        passes.extend(block_passes)
        fades.extend(block_fades)

    kept_ids = {b["block_id"] for b in blocks}
    instrument_problems, instruments = integrity.read_instruments(directory)
    # Session-scoped instruments always come through; a block-scoped one (TLX)
    # follows its block, so excluding a block excludes its TLX with it.
    instruments = [doc for _, doc in instruments
                   if doc.get("block_id") is None or doc["block_id"] in kept_ids]

    return {"blocks": blocks, "laps": laps, "passes": passes, "fades": fades,
            "instruments": instruments, "excluded": excluded,
            "instrument_problems": instrument_problems}


# --- RQ1 --------------------------------------------------------------------

def fade_trajectory(block_fades, element):
    """Stage over the block for one element, as (lap, stage_index) steps.

    Starts at `full` because every block does (permanence is block-scoped), then
    one step per transition. `probe_to_revert` and the block-end censoring event
    are both transitions, so a trajectory shows reversions as downward steps —
    which is what makes an "atypical trajectory" visible at a glance.
    """
    points = [(0, STAGE_INDEX["full"])]
    stage = "full"
    for event in block_fades:
        if event.get("element") != element:
            continue
        transition = event.get("transition", "")
        if transition.endswith("_to_reduced"):
            stage = "reduced"
        elif transition.endswith("_to_probe"):
            stage = "probe"
        elif transition.endswith("_to_removed"):
            stage = "removed"
        elif transition == "probe_to_revert":
            stage = "reduced"
        elif transition == "reduced_to_full":
            stage = "full"
        elif transition.endswith("_censored") or transition.endswith("_incomplete"):
            continue   # a censoring marker, not a stage change
        points.append((event.get("lap", 0), STAGE_INDEX[stage]))
    return points


def probe_outcome(block_fades, element):
    """held / reverted / censored / never_probed, per the eval plan's tabulation.

    `censored` is G1's expected common case — a block that ends mid-probe is
    right-censored, counting as neither held nor reverted. Reported, never
    silently dropped, because dropping it would bias the probe-outcome table
    toward whichever outcome resolves faster.
    """
    reached, outcome = False, "never_probed"
    for event in block_fades:
        if event.get("element") != element:
            continue
        transition = event.get("transition", "")
        if transition.endswith("_to_probe"):
            reached, outcome = True, "censored"
        elif transition.endswith("_to_removed") and reached:
            outcome = "held"
        elif transition == "probe_to_revert" and reached:
            outcome = "reverted"
    return outcome


def _first_lap_of(block_fades, element, suffix):
    for event in block_fades:
        if event.get("element") == element and event.get("transition", "").endswith(suffix):
            return event.get("lap")
    return None


def qualification_heatmap(block_passes, element):
    """corner x lap qualification grid for one element (eval plan's supplementary).

    Shows WHICH corners carried or blocked each quorum transition, which is the
    question a trajectory alone cannot answer. Cells are True/False/None, where
    None is a pass that yielded no evidence for this element (a null criterion —
    no evidence, not a failure) or a corner the element does not apply to.
    """
    corners, lapset = set(), set()
    cells = {}
    for record in block_passes:
        corner_id, lap = record.get("corner_id"), record.get("lap")
        corners.add(corner_id)
        lapset.add(lap)
        criterion = (record.get("criteria") or {}).get(element)
        qualified = (record.get("qualified") or {}).get(element)
        cells[(corner_id, lap)] = {
            "criterion": criterion,
            "qualified": qualified,
            "valid": record.get("valid"),
        }
    return {"corners": sorted(corners, key=str), "laps": sorted(l for l in lapset if l is not None),
            "cells": {"{}|{}".format(c, l): v for (c, l), v in cells.items()}}


def _mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def _sd(values):
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return round(math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1)), 3)


def rq1(dataset):
    """The RQ1 descriptive report: trajectories, timings, probe outcomes, oddities."""
    by_block = {}
    for event in dataset["fades"]:
        by_block.setdefault(event.get("block_id"), []).append(event)
    passes_by_block = {}
    for record in dataset["passes"]:
        passes_by_block.setdefault(record.get("block_id"), []).append(record)

    per_block = []
    for block in dataset["blocks"]:
        block_id = block["block_id"]
        block_fades = by_block.get(block_id, [])
        block_passes = passes_by_block.get(block_id, [])
        elements = {}
        for element in ELEMENTS:
            disabled = element in (block.get("disabled_elements") or [])
            elements[element] = {
                "disabled": disabled,
                "trajectory": fade_trajectory(block_fades, element),
                "probe_outcome": None if disabled else probe_outcome(block_fades, element),
                "first_fade_lap": _first_lap_of(block_fades, element, "_to_reduced"),
                "removal_lap": _first_lap_of(block_fades, element, "_to_removed"),
                "reversions": sum(1 for e in block_fades
                                  if e.get("element") == element
                                  and e.get("transition", "") in
                                  ("probe_to_revert", "reduced_to_full")),
                "heatmap": qualification_heatmap(block_passes, element),
            }
        per_block.append({
            "block_id": block_id,
            "participant_id": block["participant_id"],
            "session": block["session"],
            "condition": block["condition"],
            "pair_id": block["pair_id"],
            "elements": elements,
        })

    # Distributions across blocks, per element.
    timings = {}
    for element in ELEMENTS:
        rows = [b["elements"][element] for b in per_block if not b["elements"][element]["disabled"]]
        first = [r["first_fade_lap"] for r in rows]
        removal = [r["removal_lap"] for r in rows]
        outcomes = {}
        for name in ("held", "reverted", "censored", "never_probed"):
            outcomes[name] = sum(1 for r in rows if r["probe_outcome"] == name)
        timings[element] = {
            "blocks": len(rows),
            "never_faded": sum(1 for v in first if v is None),
            "time_to_first_fade_laps": {"mean": _mean(first), "sd": _sd(first),
                                        "values": [v for v in first if v is not None]},
            "time_to_removal_laps": {"mean": _mean(removal), "sd": _sd(removal),
                                     "values": [v for v in removal if v is not None]},
            "probe_outcomes": outcomes,
            "reversion_cap_hits": sum(1 for r in rows if r["reversions"] >= 2),
        }

    # Atypical trajectories, reported as individual cases (eval plan's wording).
    atypical = []
    for block in per_block:
        for element, data in block["elements"].items():
            if data["disabled"]:
                continue
            if data["first_fade_lap"] is None:
                atypical.append({"block_id": block["block_id"], "element": element,
                                 "case": "never_faded"})
            elif data["reversions"] >= 2:
                atypical.append({"block_id": block["block_id"], "element": element,
                                 "case": "repeated_reverts",
                                 "reversions": data["reversions"]})

    valid_laps = [row for row in dataset["laps"] if row["valid"]]
    return {
        "block_count": len(dataset["blocks"]),
        "excluded_blocks": dataset["excluded"],
        "lap_summary": {
            "laps": len(dataset["laps"]),
            "valid_laps": len(valid_laps),
            "valid_lap_time_mean_s": _mean([row["lap_time_s"] for row in valid_laps]),
            "valid_lap_time_sd_s": _sd([row["lap_time_s"] for row in valid_laps]),
        },
        "per_block": per_block,
        "timings": timings,
        "atypical": atypical,
    }


# --- RQ3 alignment ----------------------------------------------------------

def alignment_table(dataset):
    """RQ3's bridge to RQ1: reported awareness of fading vs the fade-event log.

    Per participant: did they say they noticed elements disappearing, and did
    anything actually disappear? The four cells are the interesting output — a
    participant who noticed nothing because nothing faded is a different case
    from one who noticed nothing while all three elements were withdrawn.
    """
    faded = {}
    for event in dataset["fades"]:
        if event.get("transition", "").endswith("_to_probe"):
            faded.setdefault(event.get("block_id"), set()).add(event.get("element"))
    block_participant = {b["block_id"]: b["participant_id"] for b in dataset["blocks"]}

    withdrew = {}
    for block_id, elements in faded.items():
        participant = block_participant.get(block_id)
        withdrew.setdefault(participant, set()).update(elements)

    rows = []
    for doc in dataset["instruments"]:
        if doc.get("instrument") != "post_study":
            continue
        participant = doc["participant_id"]
        noticed = bool(doc["responses"].get("noticed_fading"))
        elements = sorted(withdrew.get(participant, ()))
        rows.append({
            "participant_id": participant,
            "reported_noticed": noticed,
            "elements_withdrawn": elements,
            "any_withdrawn": bool(elements),
            "noticed_when": doc["responses"].get("noticed_when"),
            "cell": ("aware" if noticed and elements else
                     "false_alarm" if noticed and not elements else
                     "unaware" if not noticed and elements else
                     "nothing_to_notice"),
        })
    return sorted(rows, key=lambda r: str(r["participant_id"]))


# --- figures ----------------------------------------------------------------

def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def trajectory_svg(report):
    """Per-participant fade trajectories, one panel per block, three lines each.

    Hand-written SVG for the same reason as the Phase 1 feasibility figure: the
    toolkit is stdlib-only, and a figure a reader can open, diff and re-style in
    a text editor suits a thesis artefact better than a binary.
    """
    blocks = report["per_block"]
    cols = 3
    rows = max(1, (len(blocks) + cols - 1) // cols)
    pw, ph = 250, 150
    ml, mt, gx, gy = 56, 58, 30, 54
    width = ml + cols * pw + (cols - 1) * gx + 20
    height = mt + rows * ph + (rows - 1) * gy + 56

    colours = {"braking": "#1f77b4", "corner_speed": "#d62728", "apex": "#2ca02c"}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" '
           'viewBox="0 0 {} {}" font-family="Helvetica,Arial,sans-serif">'.format(
               width, height, width, height),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="{}" y="26" font-size="15" font-weight="bold">Fade trajectories '
           'per block</text>'.format(ml),
           '<text x="{}" y="44" font-size="11" fill="#555">stage: full -> reduced -> '
           'probe -> removed; downward steps are reversions</text>'.format(ml)]

    max_lap = 1
    for block in blocks:
        for element in ELEMENTS:
            for lap, _ in block["elements"][element]["trajectory"]:
                max_lap = max(max_lap, lap)

    for i, block in enumerate(blocks):
        cx = ml + (i % cols) * (pw + gx)
        cy = mt + (i // cols) * (ph + gy)
        out.append('<rect x="{}" y="{}" width="{}" height="{}" fill="#fafafa" '
                   'stroke="#ddd"/>'.format(cx, cy, pw, ph))
        label = "{} s{} {} / {}".format(block["participant_id"], block["session"],
                                        block["condition"], block["pair_id"])
        out.append('<text x="{}" y="{}" font-size="10" font-weight="bold">{}</text>'.format(
            cx, cy - 6, _escape(label)))
        for s, name in enumerate(STAGES):
            y = cy + ph - 10 - s * (ph - 24) / 3.0
            out.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}" stroke="#eee"/>'.format(
                cx, y, cx + pw, y))
            out.append('<text x="{}" y="{:.1f}" font-size="8" fill="#888" '
                       'text-anchor="end">{}</text>'.format(cx - 4, y + 3, name))

        for element in ELEMENTS:
            points = block["elements"][element]["trajectory"]
            if not points:
                continue
            # Step plot: a stage holds until the next transition.
            path = []
            for j, (lap, stage) in enumerate(points):
                x = cx + 6 + (pw - 16) * (lap / float(max_lap))
                y = cy + ph - 10 - stage * (ph - 24) / 3.0
                if j == 0:
                    path.append("M {:.1f} {:.1f}".format(x, y))
                else:
                    path.append("H {:.1f}".format(x))
                    path.append("V {:.1f}".format(y))
            path.append("H {:.1f}".format(cx + pw - 10))
            out.append('<path d="{}" fill="none" stroke="{}" stroke-width="1.6" '
                       'opacity="0.85"/>'.format(" ".join(path), colours[element]))

    lx = ml
    ly = height - 18
    for element in ELEMENTS:
        out.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" '
                   'stroke-width="2"/>'.format(lx, ly, lx + 18, ly, colours[element]))
        out.append('<text x="{}" y="{}" font-size="10">{}</text>'.format(
            lx + 23, ly + 3, element))
        lx += 110
    out.append("</svg>")
    return "\n".join(out)


# --- CLI --------------------------------------------------------------------

def cmd_ingest(args):
    dataset = load_dataset(args.path, include=tuple(args.include))
    print("blocks: {}  laps: {}  passes: {}  fades: {}  instruments: {}".format(
        len(dataset["blocks"]), len(dataset["laps"]), len(dataset["passes"]),
        len(dataset["fades"]), len(dataset["instruments"])))
    if dataset["excluded"]:
        print("excluded {} block(s):".format(len(dataset["excluded"])))
        for row in dataset["excluded"]:
            print("  {}  [{}]{}".format(
                row["block_id"], row["kind"],
                "  " + row["abort_reason"] if row.get("abort_reason") else ""))
    for problem in dataset["instrument_problems"]:
        print("  instrument problem: {}".format(problem))
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for name in ("blocks", "laps", "passes", "fades", "instruments"):
            (out / "{}.json".format(name)).write_text(
                json.dumps(dataset[name], indent=2), encoding="utf-8")
        print("wrote 5 table(s) to {}".format(out))
    return 0


def cmd_rq1(args):
    dataset = load_dataset(args.path, include=tuple(args.include))
    report = rq1(dataset)
    print("RQ1 over {} block(s), {} valid lap(s)".format(
        report["block_count"], report["lap_summary"]["valid_laps"]))
    for element in ELEMENTS:
        t = report["timings"][element]
        print("  {:<13} blocks {:>2}  never-faded {:>2}  probe {}".format(
            element, t["blocks"], t["never_faded"],
            ", ".join("{} {}".format(k, v) for k, v in t["probe_outcomes"].items())))
    for case in report["atypical"]:
        print("  atypical: {} {} {}".format(case["block_id"], case["element"], case["case"]))
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "rq1_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out / "rq1_trajectories.svg").write_text(trajectory_svg(report), encoding="utf-8")
        alignment = alignment_table(dataset)
        (out / "rq3_alignment.json").write_text(json.dumps(alignment, indent=2),
                                                encoding="utf-8")
        print("wrote rq1_report.json, rq1_trajectories.svg, rq3_alignment.json to {}".format(out))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="trace_kit.analysis",
        description="Phase 4 ingestion and RQ1 descriptives (the RQ2 Bayesian model "
                    "is deliberately not here -- see the module docstring).")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("ingest", cmd_ingest), ("rq1", cmd_rq1)):
        p = sub.add_parser(name)
        p.add_argument("path", help="directory of recorded blocks")
        p.add_argument("--out", help="directory to write tables/figures into")
        p.add_argument("--include", action="append", default=None,
                       choices=["study", "dry_run", "dev", "aborted"],
                       help="block kinds to ingest (default: study only; the M6 "
                            "dry run passes --include dry_run)")
        p.set_defaults(func=handler)
    args = parser.parse_args(argv)
    if args.include is None:
        args.include = ["study"]
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
