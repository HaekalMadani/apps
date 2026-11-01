"""Would ANYTHING fade? Real passes, real evaluator, real controller.

The question `SESSION_BUDGET_BRIEF.md` leaves open and the one that decides
whether the study produces data at all: inside a 12-15 lap block, driven by a
real novice rather than a synthetic one, does any element ever leave `full`?

The fear is not hypothetical. `CLAUDE.md` records an in-game M5 block where
**all three elements sat at `full` for every pass and the controller never had
cause to move a stage** (apex 3 true / 27 false, braking 0 true / 28 false / 2
null, corner speed 5 true / 25 false). At the frozen floors that is the measured
status quo, not a risk.

Every other feasibility artefact in this repo answers a neighbouring question:

  simulate run / windowscan  the SYNTHETIC novice, whose apex parameters are
                             known wrong by ~6x on sigma and whose other seven
                             have no empirical anchor
  rescore                    REAL per-pass rates, but no controller -- it stops
                             at the criterion and never asks what the state
                             machine would have done with it
  lapbudget                  the lap arithmetic, synthetic again
  mdc                        the noise, and whether a window can see a change

This script closes the gap: it replays **real recorded passes** through the
**real evaluator** at candidate band floors and then through the **real
controller** at candidate windows, and reports what the machine would actually
have done. No synthetic learner anywhere in it.

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/feasible.py "<trace_data>"

Two block groups, reported separately and never pooled, because they are
different populations:

  pre-KR   the seven `_blocks.py` blocks. No error signal was ever delivered, so
           every per-pass rate measured on them describes a system with no
           feedback -- `CLAUDE.md` says to measure floors AFTER the diagnostic
           rather than before it.
  with-KR  the three 2026-10-14 blocks (KRtest, shortHUDtest, test14-10). Short
           (5-6 laps) and n=1 and the driver knows the hypothesis, but bandwidth
           KR is in the apparatus for BOTH conditions now, so this is the
           population a participant belongs to.

Overrides are in memory only. It never writes `controller_config.json`, because
an edit there re-pins the frozen hash and re-opens Gate G1. It is not a Gate G1
run and its numbers are not a verdict -- they are what the frozen verdict could
not see.

Figures are tabulated in README.md.
"""
import collections
import copy
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import evaluator as ev
from trace_kit import reference as ref
from trace_kit.controller import Controller, ELEMENTS
from tools._blocks import PAIR1_HUMAN_NATIONAL
from tools.rescore import pass_metrics

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# The three 2026-10-14 blocks driven WITH bandwidth KR visible. Hard-coded for
# the same reason `_blocks.py` is a record rather than a query: a discovered
# list would silently change the denominator under the figures in README.md.
WITH_KR = (
    "KRtest_s2_pair1_adaptive_20261014_144710",
    "shortHUDtest_s2_pair1_adaptive_20261014_181110",
    "test14-10_s2_pair1_adaptive_20261014_191319",
)

# Candidate band floors: braking_m / corner_speed_kmh / apex_m.
#
# The apex floor is deliberately NOT raised past 1.5. `CLAUDE.md` records that
# at apex_m = 2.0 Gate G1 fails outright -- non-improvers fading an element goes
# 0% -> 100%, and the element they lose is the apex one, because novice apex
# scatter is the size of the whole available improvement. So the floors that can
# move are braking and corner speed, and the apex element is expected not to
# fade. Raising it to 3.0 m would buy a 73% per-pass rate and hand a
# non-improver the one element whose job is line accuracy.
# `g1-old` is the superseded `frozen-g1` calibration, kept as the baseline row
# because it is the one that demonstrably never faded anything; `ADOPTED` is
# `frozen-g1b`, live since 2026-10-15. Labels rather than a lookup of the live
# config, so the table means the same thing after the next recalibration.
FLOORS = collections.OrderedDict([
    ("g1-old",      {"braking_m": 5.0,  "corner_speed_kmh": 4.0,  "apex_m": 0.5}),
    ("8/6/1.0",     {"braking_m": 8.0,  "corner_speed_kmh": 6.0,  "apex_m": 1.0}),
    ("10/8/1.5",    {"braking_m": 10.0, "corner_speed_kmh": 8.0,  "apex_m": 1.5}),
    ("ADOPTED",     {"braking_m": 12.0, "corner_speed_kmh": 9.0,  "apex_m": 1.5}),
    ("15/11/1.5",   {"braking_m": 15.0, "corner_speed_kmh": 11.0, "apex_m": 1.5}),
    ("18/12/1.5",   {"braking_m": 18.0, "corner_speed_kmh": 12.0, "apex_m": 1.5}),
])

# (window_passes, required_passes, probe.laps)
WINDOWS = [(4, 3, 3), (3, 2, 2), (3, 2, 3)]


def load_block(trace_data, block, annotation, table, config):
    """Every clean pass of every corner, in DRIVING order, with real criteria.

    Returns a list of {corner_id, lap, criteria} ready for Controller.step, and
    the per-element true/false/null tallies behind them. The consistency gate
    reads the rolling mean of the corner's PRIOR passes, so history is per
    corner and built in driving order -- the way the runtime accumulates it.
    """
    path = os.path.join(trace_data, "ticks_%s.csv" % block)
    if not os.path.exists(path):
        return None, None
    rows = ref.read_ticks(path)
    pitted = ref.pit_laps(rows)
    length_m = table["track_length_m"]
    by_id = dict((c["corner_id"], c) for c in table["corners"])
    threshold = config["brake_initiation"]["threshold"]
    debounce_s = config["brake_initiation"]["debounce_ms"] / 1000.0
    window_passes = config["qualification"]["window_passes"]

    collected = []
    tally = collections.defaultdict(collections.Counter)
    for corner in annotation["corners"]:
        corner_ref = by_id[corner["id"]]
        history = []
        for a_pass in ref.corner_passes(rows, corner):
            if not ref.pass_is_clean(a_pass["rows"], pitted):
                continue
            metrics = pass_metrics(a_pass, corner, corner_ref, length_m,
                                   threshold, debounce_s)
            out = ev.evaluate(config, corner_ref, metrics, history)
            for element, value in out["criteria"].items():
                tally[element][{True: "pass", False: "fail", None: "null"}[value]] += 1
            collected.append({"corner_id": corner["id"], "lap": a_pass["lap"],
                              "criteria": out["criteria"]})
            if "brake_initiation_distance_m" in metrics:
                history = ev.push_history(
                    history, metrics["brake_initiation_distance_m"], window_passes)
    # Driving order: lap, then the annotation's corner order within the lap.
    order = dict((c["id"], i) for i, c in enumerate(annotation["corners"]))
    collected.sort(key=lambda p: (p["lap"], order[p["corner_id"]]))
    return collected, tally


def replay(config, table, passes):
    """Run real passes through the real controller. Returns stages and events."""
    ctrl = Controller(config, ev.applicable(table))
    events = []
    for p in passes:
        events.extend(ctrl.step({"corner_id": p["corner_id"], "lap": p["lap"],
                                 "t": float(p["lap"] * 70 + 10),
                                 "criteria": p["criteria"]}))
    return ctrl.stages(), events


ADVANCES = ("full_to_reduced", "reduced_to_probe", "probe_to_removed")


def first_advance(events, element):
    for e in events:
        if e["element"] == element and e["transition"] in ADVANCES:
            return e["lap"]
    return None


def advance_count(events, element):
    return sum(1 for e in events
               if e["element"] == element and e["transition"] in ADVANCES)


def main(argv):
    trace_data = argv[0]
    table = json.load(open(os.path.join(
        ROOT, "configs", "references", "reference_pair1.json")))
    annotation = json.load(open(os.path.join(
        ROOT, "configs", "annotations", "annotation_%s.json" % table["track"])))
    base = json.load(open(os.path.join(ROOT, "configs", "controller_config.json")))

    groups = collections.OrderedDict([
        ("pre-KR", PAIR1_HUMAN_NATIONAL), ("with-KR", WITH_KR)])

    print("feasible -- real passes, real evaluator, real controller")
    print("reference reference_pair1.json   config_id %s (overridden in memory)\n"
          % base["config_id"])

    # ---- 1. per-pass criterion rates, which bound everything downstream ----
    print("## per-pass criterion rate on REAL passes\n")
    print("A corner qualifies on 3 of its last 4 passes, so a per-pass rate")
    print("much under ~75% cannot hold a corner qualified for long, and the")
    print("element-level quorum then needs 3 of 4 corners to manage it at once.\n")
    print("  %-10s %-12s %8s %8s %8s %8s"
          % ("floors", "group", "braking", "speed", "apex", "laps"))
    rates = {}
    for label, floors in FLOORS.items():
        for gname, blocks in groups.items():
            cfg = copy.deepcopy(base)
            cfg["band_floors"].update(floors)
            total = collections.defaultdict(collections.Counter)
            laps = []
            for block in blocks:
                passes, tally = load_block(trace_data, block, annotation, table, cfg)
                if passes is None:
                    continue
                laps.append(len(set(p["lap"] for p in passes)))
                for element, counts in tally.items():
                    total[element].update(counts)
            cells = []
            for element in ELEMENTS:
                c = total[element]
                scored = c["pass"] + c["fail"]
                cells.append(100.0 * c["pass"] / scored if scored else float("nan"))
            rates[(label, gname)] = cells
            print("  %-10s %-12s %7.1f%% %7.1f%% %7.1f%%  %4.1f avg"
                  % (label, gname, cells[0], cells[1], cells[2],
                     statistics.fmean(laps) if laps else float("nan")))
    print("")

    # ---- 2. the controller replay: did anything actually move? ----
    print("## controller replay -- blocks in which the element LEFT `full`\n")
    print("Real passes through the real state machine. Three different")
    print("questions, deliberately not collapsed:\n")
    print("  engaged   blocks where the element EVER advanced a stage. This is")
    print("            'did the mechanism do anything', the study's own")
    print("            precondition -- an element that never moves yields no")
    print("            fade record and nothing for RQ1 to describe.")
    print("  ended>    blocks whose FINAL stage was above `full`. Lower than")
    print("            `engaged` wherever an element advanced and then reverted,")
    print("            which is probe-and-revert working rather than failing.")
    print("  lap       median lap of the first advance.\n")
    print("Real blocks average 6.3 laps (range 5-11), so a 12-15 lap study block")
    print("gives roughly DOUBLE this evidence: these figures UNDERSTATE it, and")
    print("a first advance at lap 3-6 leaves room for a second stage.\n")
    for window, required, probe_laps in WINDOWS:
        print("  window %d-of-%d, probe %d" % (required, window, probe_laps))
        print("    %-10s %-12s %6s   %-18s %-18s %s"
              % ("floors", "group", "blocks", "engaged b / s / a",
                 "ended> b / s / a", "median first-advance lap"))
        for label, floors in FLOORS.items():
            for gname, blocks in groups.items():
                cfg = copy.deepcopy(base)
                cfg["band_floors"].update(floors)
                cfg["qualification"]["window_passes"] = window
                cfg["qualification"]["required_passes"] = required
                cfg["probe"]["laps"] = probe_laps
                left = dict((e, 0) for e in ELEMENTS)
                engaged = dict((e, 0) for e in ELEMENTS)
                when = dict((e, []) for e in ELEMENTS)
                n = 0
                for block in blocks:
                    passes, _t = load_block(trace_data, block, annotation, table, cfg)
                    if not passes:
                        continue
                    n += 1
                    stages, events = replay(cfg, table, passes)
                    for e in ELEMENTS:
                        if stages[e] != "full":
                            left[e] += 1
                        if advance_count(events, e):
                            engaged[e] += 1
                        lap = first_advance(events, e)
                        if lap is not None:
                            when[e].append(lap)
                if not n:
                    continue
                print("    %-10s %-12s %6d   %-18s %-18s %s"
                      % (label, gname, n,
                         "%2d /%2d /%2d" % tuple(engaged[e] for e in ELEMENTS),
                         "%2d /%2d /%2d" % tuple(left[e] for e in ELEMENTS),
                         " / ".join(("%g" % statistics.median(when[e]))
                                    if when[e] else "-" for e in ELEMENTS)))
        print("")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
