"""Where a human ACTUALLY starts braking, searched in a window wide enough to
see past the annotated braking zone.

Why this exists and `trace_kit.reference` does not do it: the extractor searches
inside `zones.braking` and reports the first sustained brake application there.
If the driver braked before the zone opened, the detector finds the brake already
on at the zone edge and reports the edge -- a censored value that looks like a
measurement. That censoring is exactly what has to be visible when choosing where
the zone goes, so this tool searches backwards from the reference brake point
instead of from the zone, using the same `brake_initiation` detector and the same
`controller_config.json` threshold and debounce the runtime uses.

`WIDE_BACK` is per corner because one window does not fit every corner on a lap.
At 220 m, National's corner 4 sits inside corner 3's trail braking and every
value comes back at about -218 m -- the window finds corner 3's brake
application, not corner 4's. The per-corner values are each the largest that
stays clear of the preceding braking event.

Output is signed metres relative to the reference brake point, negative meaning
the human braked EARLIER. Those are the excursions the zone has to contain on
both sides; see `MIN_EARLY_MARGIN_M` / `MIN_LATE_MARGIN_M` in
`trace_kit.reference`, and the seconds-based budget in the annotation's `notes`.

    python kit/tools/brakescan.py <trace_data> <reference.json> <annotation.json>
"""
import collections
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import reference as ref
from tools._blocks import PAIR1_HUMAN_NATIONAL

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# Metres to search back from the reference brake point, per corner id. Bounded
# by the previous corner's braking event, not chosen for symmetry.
WIDE_BACK = {"1": 90.0, "2": 220.0, "3": 220.0, "4": 52.0}


def quantile(sorted_values, fraction):
    if not sorted_values:
        return float("nan")
    i = int(round(fraction * (len(sorted_values) - 1)))
    return sorted_values[max(0, min(len(sorted_values) - 1, i))]


def main(argv):
    trace_data = argv[0]
    table = json.load(open(argv[1]))
    annotation = json.load(open(argv[2]))
    blocks = argv[3:] or list(PAIR1_HUMAN_NATIONAL)

    config = json.load(open(os.path.join(ROOT, "configs", "controller_config.json")))
    brake_cfg = config["brake_initiation"]
    threshold = brake_cfg["threshold"]
    debounce_s = brake_cfg["debounce_ms"] / 1000.0

    length_m = table["track_length_m"]
    brake_at = dict((c["corner_id"], c["braking"]["spline_pos"]) for c in table["corners"])

    found = collections.OrderedDict()
    for corner in annotation["corners"]:
        corner_id = corner["id"]
        if corner_id not in brake_at:
            continue
        point = brake_at[corner_id]
        back_m = WIDE_BACK.get(corner_id, 120.0)
        wide = {
            "start": (point - back_m / length_m) % 1.0,
            "end": corner["zones"]["braking"]["end"],
        }
        # The pass bracket has to open before the wide window does, or the rows
        # handed to the detector start after the braking it is looking for.
        wide_corner = dict(corner)
        wide_corner["entry_gate"] = (wide["start"] - 10.0 / length_m) % 1.0

        deltas = []
        for block in blocks:
            path = os.path.join(trace_data, "ticks_%s.csv" % block)
            if not os.path.exists(path):
                continue
            rows = ref.read_ticks(path)
            pitted = ref.pit_laps(rows)
            for a_pass in ref.corner_passes(rows, wide_corner):
                if not ref.pass_is_clean(a_pass["rows"], pitted):
                    continue
                hit = ref.brake_initiation(a_pass["rows"], wide, threshold, debounce_s)
                if hit is None:
                    continue
                deltas.append(ref.signed_delta(point, hit["spline"]) * length_m)
        found[corner_id] = sorted(deltas)

    print("%-7s %4s %8s %8s %8s %8s %8s %8s"
          % ("corner", "n", "min", "p5", "p25", "med", "p95", "max"))
    for corner_id, deltas in found.items():
        if not deltas:
            print("%-7s %4d  (no brake initiation found in the wide window)"
                  % (corner_id, 0))
            continue
        print("%-7s %4d %8.1f %8.1f %8.1f %8.1f %8.1f %8.1f"
              % (corner_id, len(deltas), min(deltas), quantile(deltas, .05),
                 quantile(deltas, .25), statistics.median(deltas),
                 quantile(deltas, .95), max(deltas)))
    print()
    print("(signed metres from the reference brake point; negative = human braked EARLIER)")
    print()
    for corner_id, deltas in found.items():
        print("corner %s %s" % (corner_id, ["%.0f" % d for d in deltas]))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
