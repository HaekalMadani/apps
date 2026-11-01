"""What an apex band floor would buy, and where inside the window the error is.

Two questions, one script, because they are only useful together:

  rates     the per-pass apex criterion rate at a range of candidate floors,
            overall and per corner, with the floor overridden IN MEMORY only
            (same rule as rescore.py: this tool informs a Gate G2 decision, it
            never takes one)
  profile   the deviation from the expert line station by station ACROSS the
            apex window, which is what tells a driver who is uniformly off the
            line from a window that is measuring turn-in and exit rather than
            the apex

It reads `apex_rms_m` straight out of the committed pass records for the rates,
rather than re-deriving it from the tick logs the way rescore.py does: the
criterion needs only the metric, and reading the records is what lets a block
recorded today be scored beside the historical corpus without editing
tools/_blocks.py. The profile does go to the tick logs, because a per-station
error is not in any pass record.

    python kit/tools/apexscan.py <trace_data> [block-id-for-the-profile]

Reproduced figures are tabulated in README.md.
"""
import csv
import io
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import evaluator as ev
from tools._blocks import PAIR1_HUMAN_NATIONAL

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# The three blocks driven on 2026-10-14, the first with bandwidth KR on screen.
# Listed here for the same reason _blocks.py lists its seven: a discovered set
# would silently change the denominator of every figure in the README.
PAIR1_KR_BLOCKS = (
    "KRtest_s2_pair1_adaptive_20261014_144710",
    "shortHUDtest_s2_pair1_adaptive_20261014_181110",
    "test14-10_s2_pair1_adaptive_20261014_191319",
)

CANDIDATE_FLOORS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5)


def load_json(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def passes(data_dir, block):
    path = os.path.join(data_dir, "passes_%s.jsonl" % block)
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def rates(data_dir, cfg, ref, label, blocks):
    corner_ids = sorted(ref)
    rows = [r for b in blocks for r in passes(data_dir, b)
            if (r.get("metrics") or {}).get("apex_rms_m") is not None]
    if not rows:
        print("\n%s: no measured apex passes found" % label)
        return
    values = sorted(r["metrics"]["apex_rms_m"] for r in rows)
    n = len(values)
    print("\n=== %s: %d measured apex passes" % (label, n))

    def pct(q):
        return values[min(n - 1, int(n * q))]

    print("    apex RMS  min %.2f  p25 %.2f  median %.2f  p75 %.2f  p90 %.2f  max %.2f"
          % (values[0], pct(0.25), pct(0.5), pct(0.75), pct(0.9), values[-1]))

    # The lap-to-lap scatter WITHIN one corner is the quantity the novice model's
    # `apex_sigma_m` claims to be, and the one that decides whether any band can
    # separate an improver from a non-improver.
    within = []
    excess = []
    for block in blocks:
        per_corner = {}
        for r in passes(data_dir, block):
            v = (r.get("metrics") or {}).get("apex_rms_m")
            if v is None:
                continue
            per_corner.setdefault(r["corner_id"], []).append(v)
            excess.append(v - ref[r["corner_id"]]["apex"]["mean_rms_m"])
        for series in per_corner.values():
            if len(series) >= 3:
                within.append(statistics.stdev(series))
    if excess:
        print("    excess over the reference's own mean_rms: mean %.2f m  median %.2f m"
              % (statistics.mean(excess), statistics.median(excess)))
    if within:
        print("    lap-to-lap SD within one corner: %.2f m  (over %d corner-blocks)"
              % (statistics.mean(within), len(within)))

    print("    floor  overall  " + "  ".join("cnr %s" % c for c in corner_ids))
    for floor in CANDIDATE_FLOORS:
        probe = json.loads(json.dumps(cfg))
        probe["band_floors"]["apex_m"] = floor
        met = 0
        per = dict((cid, [0, 0]) for cid in corner_ids)
        for r in rows:
            result = ev.evaluate(probe, ref[r["corner_id"]],
                                 {"apex_rms_m": r["metrics"]["apex_rms_m"]}, [])
            hit = 1 if result["criteria"]["apex"] else 0
            met += hit
            per[r["corner_id"]][0] += hit
            per[r["corner_id"]][1] += 1
        cells = "  ".join("%3.0f%%" % (100.0 * per[c][0] / per[c][1]) if per[c][1]
                          else "   -" for c in corner_ids)
        print("    %5.2f    %3.0f%%    %s" % (floor, 100.0 * met / n, cells))


def profile(data_dir, ref, annotation, block):
    """Mean deviation from the expert line at each line station, per corner.

    Mirrors lib/pass_metrics: interpolate the car's X/Z at the station's spline
    and take the horizontal separation. One profile per lap, averaged.
    """
    path = os.path.join(data_dir, "ticks_%s.csv" % block)
    if not os.path.exists(path):
        print("\nprofile: no tick log for %s" % block)
        return
    rows = []
    with io.open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append((int(r["lap"]), float(r["spline"]),
                         float(r["pos_x"]), float(r["pos_z"])))
    ann = dict((c["id"], c) for c in annotation["corners"])
    print("\n=== deviation across the apex window, block %s" % block)
    for cid in sorted(ref):
        gate = ref[cid]["apex"]["gates"][0]
        line = gate["line"]
        stations = [[] for _ in line]
        for lap in sorted(set(l for l, _, _, _ in rows)):
            seq = [(s, x, z) for l, s, x, z in rows if l == lap]
            if len(seq) < 10:
                continue
            for k, sample in enumerate(line):
                target = sample["spline_pos"]
                for i in range(1, len(seq)):
                    a, b = seq[i - 1][0], seq[i][0]
                    if a <= target <= b:
                        f = 0.0 if b == a else (target - a) / (b - a)
                        x = seq[i - 1][1] + f * (seq[i][1] - seq[i - 1][1])
                        z = seq[i - 1][2] + f * (seq[i][2] - seq[i - 1][2])
                        stations[k].append(math.hypot(
                            x - sample["world_pos"][0], z - sample["world_pos"][2]))
                        break
        prof = [statistics.mean(v) if v else None for v in stations]
        if not [p for p in prof if p is not None]:
            print("  corner %s: not covered" % cid)
            continue
        fifth = max(1, len(prof) // 5)
        mid = len(prof) // 2

        def mean_of(seq):
            vals = [p for p in seq if p is not None]
            return statistics.mean(vals) if vals else float("nan")

        print("  corner %s (half-window %.0f m): entry fifth %.2f m   at the gate "
              "%.2f m   exit fifth %.2f m"
              % (cid, ann[cid]["zones"]["apex_window_half_m"], mean_of(prof[:fifth]),
                 mean_of(prof[mid - 2:mid + 3]), mean_of(prof[-fifth:])))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    data_dir = sys.argv[1]
    block = sys.argv[2] if len(sys.argv) > 2 else PAIR1_KR_BLOCKS[-1]
    cfg = load_json("configs", "controller_config.json")
    ref_doc = load_json("configs", "references", "reference_pair1.json")
    ref = dict((c["corner_id"], c) for c in ref_doc["corners"])
    annotation = load_json("configs", "annotations",
                           "annotation_ks_silverstone-national.json")

    print("the criterion is apex_rms <= mean_rms_m + max(sigma_ref x EVM, floor):")
    for cid in sorted(ref):
        a = ref[cid]["apex"]
        band = max(a["sigma_ref_m"] * cfg["evm"]["ai"], cfg["band_floors"]["apex_m"])
        print("  corner %s  mean_rms %.3f  sigma_ref %.4f  band %.3f  threshold %.3f m"
              % (cid, a["mean_rms_m"], a["sigma_ref_m"], band, a["mean_rms_m"] + band))

    rates(data_dir, cfg, ref, "historic (pre-KR, 7 blocks)", PAIR1_HUMAN_NATIONAL)
    rates(data_dir, cfg, ref, "2026-10-14 (3 KR blocks)", PAIR1_KR_BLOCKS)
    rates(data_dir, cfg, ref, "all 10 blocks",
          PAIR1_HUMAN_NATIONAL + PAIR1_KR_BLOCKS)
    profile(data_dir, ref, annotation, block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
