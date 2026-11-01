"""Re-score every clean human corner pass against a reference table, with the
real evaluator, and report per-criterion pass rates and residuals.

This is the tool that answers two questions no committed artefact answers on its
own: *is the reference reachable*, and *what would a different band floor buy*.
It deliberately calls `trace_kit.evaluator.evaluate` rather than reimplementing
the criteria, so a change to the evaluator moves these numbers too -- the whole
point is that the answer is the system's own arithmetic, not a parallel estimate
of it.

It reads `configs/controller_config.json` and then overrides band floors and the
consistency ratio IN MEMORY only. It never writes the config, because any edit
there re-pins the frozen hash and re-opens Gate G1; floors are a G2 decision and
this tool exists to inform that decision, not to take it.

    python kit/tools/rescore.py <trace_data> <reference.json> [floors-json] [ratio]

      floors-json   e.g. {"braking_m": 15, "corner_speed_kmh": 11, "apex_m": 3.0}
      ratio         criteria.consistency_delta_ratio, default from the config

The residual block is what tells bias from scatter: a median far from zero with
a much smaller median |error| spread means the target is OFFSET, which widening
a band cannot fix and a different reference strength can. That is the reading
that moved pair 1 from the 100% table to the 85% one.
"""
import collections
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import evaluator as ev
from trace_kit import reference as ref
from tools._blocks import PAIR1_HUMAN_NATIONAL

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def pass_metrics(a_pass, corner, corner_ref, length_m, threshold, debounce_s):
    """The three metrics, measured the way `pass_metrics.lua` measures them."""
    metrics = {}
    hit = ref.brake_initiation(a_pass["rows"], corner["zones"]["braking"],
                               threshold, debounce_s)
    if hit is not None:
        metrics["brake_initiation_distance_m"] = ref.signed_delta(
            corner_ref["braking"]["spline_pos"], hit["spline"]) * length_m

    speed = ref.min_corner_speed(a_pass["rows"], corner["zones"]["corner_speed"])
    if speed is not None:
        metrics["min_corner_speed_kmh"] = speed

    gate = corner["zones"]["apex_gates"][0]
    grid = ref.apex_grid(gate, corner["zones"]["apex_window_half_m"], length_m)
    line = ref.sample_line(a_pass["rows"], grid, gate)
    if line is not None:
        expert = [point["world_pos"] for point in corner_ref["apex"]["gates"][0]["line"]]
        rms = ref.rms_lateral(line, expert)
        if rms is not None:
            metrics["apex_rms_m"] = rms
    return metrics


def main(argv):
    trace_data = argv[0]
    table = json.load(open(argv[1]))

    config = json.load(open(os.path.join(ROOT, "configs", "controller_config.json")))
    if len(argv) > 2 and argv[2]:
        config["band_floors"].update(json.loads(argv[2]))
    if len(argv) > 3 and argv[3]:
        config["criteria"]["consistency_delta_ratio"] = float(argv[3])

    annotation_path = os.path.join(
        ROOT, "configs", "annotations", "annotation_%s.json" % table["track"])
    annotation = json.load(open(annotation_path))

    length_m = table["track_length_m"]
    by_id = dict((c["corner_id"], c) for c in table["corners"])
    brake_cfg = config["brake_initiation"]
    threshold = brake_cfg["threshold"]
    debounce_s = brake_cfg["debounce_ms"] / 1000.0
    window_passes = config["qualification"]["window_passes"]

    tally = collections.defaultdict(collections.Counter)
    gate_tally = collections.Counter()
    residuals = collections.OrderedDict(
        (k, []) for k in ("brake_m", "speed_kmh", "apex_excess_m"))
    blocks_read = 0

    for block in PAIR1_HUMAN_NATIONAL:
        path = os.path.join(trace_data, "ticks_%s.csv" % block)
        if not os.path.exists(path):
            continue
        blocks_read += 1
        rows = ref.read_ticks(path)
        pitted = ref.pit_laps(rows)
        for corner in annotation["corners"]:
            corner_ref = by_id[corner["id"]]
            # The consistency gate reads the rolling mean of the corner's PRIOR
            # passes, so the history is per corner and per block and is built in
            # driving order -- the same way the runtime accumulates it.
            history = []
            for a_pass in ref.corner_passes(rows, corner):
                if not ref.pass_is_clean(a_pass["rows"], pitted):
                    continue
                metrics = pass_metrics(a_pass, corner, corner_ref, length_m,
                                       threshold, debounce_s)
                out = ev.evaluate(config, corner_ref, metrics, history)

                for element, value in out["criteria"].items():
                    tally[element][{True: "pass", False: "fail", None: "null"}[value]] += 1
                for gate, value in out["braking_gates"].items():
                    if value is not None:
                        gate_tally[gate + ("_pass" if value else "_fail")] += 1

                if "brake_initiation_distance_m" in metrics:
                    residuals["brake_m"].append(metrics["brake_initiation_distance_m"])
                    history = ev.push_history(
                        history, metrics["brake_initiation_distance_m"], window_passes)
                if out["speed_envelope_deviation_kmh"] is not None:
                    residuals["speed_kmh"].append(out["speed_envelope_deviation_kmh"])
                if "apex_rms_m" in metrics:
                    residuals["apex_excess_m"].append(
                        metrics["apex_rms_m"] - corner_ref["apex"]["mean_rms_m"])

    band = ev.bands(config, by_id[annotation["corners"][0]["id"]])
    print("reference    %s  (%s, AI %s%%)"
          % (os.path.basename(argv[1]), table["track"],
             table.get("source_laps", {}).get("ai_strength_pct", "?")))
    print("blocks read  %d of %d" % (blocks_read, len(PAIR1_HUMAN_NATIONAL)))
    print("bands        braking %.1f m   corner_speed %.1f km/h   apex %.2f m"
          "   consistency delta %.1f m"
          % (band["braking_m"], band["corner_speed_kmh"], band["apex_m"],
             config["criteria"]["consistency_delta_ratio"] * band["braking_m"]))
    print()
    print("%-14s %6s %6s %6s %8s" % ("criterion", "pass", "fail", "null", "rate"))
    for element in ("braking", "corner_speed", "apex"):
        counts = tally[element]
        scored = counts["pass"] + counts["fail"]
        print("%-14s %6d %6d %6d %7.1f%%"
              % (element, counts["pass"], counts["fail"], counts["null"],
                 100.0 * counts["pass"] / scored if scored else float("nan")))
    print()
    for gate in ("accuracy", "consistency"):
        scored = gate_tally[gate + "_pass"] + gate_tally[gate + "_fail"]
        print("  braking gate %-12s %7.1f%%  (%d/%d)"
              % (gate, 100.0 * gate_tally[gate + "_pass"] / scored if scored else float("nan"),
                 gate_tally[gate + "_pass"], scored))
    print()
    for name, values in residuals.items():
        if not values:
            continue
        ordered = sorted(values)
        absolute = sorted(abs(v) for v in values)
        print("  %-14s n=%3d  median %+7.2f   median |err| %6.2f"
              "   p75 |err| %6.2f   p90 |err| %6.2f"
              % (name, len(ordered), statistics.median(ordered),
                 statistics.median(absolute),
                 absolute[int(.75 * (len(absolute) - 1))],
                 absolute[int(.90 * (len(absolute) - 1))]))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
