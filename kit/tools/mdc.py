"""How many passes a window needs before the metric can see a real change.

Gate G2 item 8a from `BAND_CALIBRATION_BRIEF.md` §E, and as of 2026-10-15 the
**blocker for the whole protocol**: `SESSION_BUDGET_BRIEF.md` adopts a 30-minute
sitting with a 12-lap training block, which Gate G1 only clears at a 3-pass
qualification window (0.003 at the frozen 3-of-4, 0.728 at 2-of-3). The lap
budget POINTS AT 2-of-3; it cannot license it, because no simulated learner type
can price a shorter window's real cost. This script is the measurement that can.

The method is the one the literature review landed on, because there is no
published rule for a bandwidth width: **minimal detectable change** (Weir 2005).
Measure the metric's own lap-to-lap noise, convert it to the smallest change a
window of n passes could distinguish from that noise, and read off the n at
which MDC drops under the improvement actually available to a learner.

    sigma_within  pooled SD of DETRENDED residuals, per metric
    MDC95(n)      1.96 * sqrt(2) * sigma_within / sqrt(n)
    verdict       smallest n with MDC95(n) < the improvement available

Four reported quantities and why each is here:

  trend        the within-cell OLS slope. Reported, not just removed: these
               blocks are PRE-KR and the driver was plateaued, so the slopes
               should be near zero -- and if they are, this data cannot supply
               the "improvement available" denominator and the anchors below
               have to come from elsewhere. That is a finding about the data,
               not a defect in the method.
  sigma_within pooled over cells by residual degrees of freedom, so a cell with
               4 passes does not count as much as one with 12.
  ICC(1,1)     one-way random effects with CORNER as the factor, on
               trend-removed values that keep their cell mean. It answers
               whether the metric reflects a stable corner-specific state or is
               mostly lap-to-lap noise -- which is the same ratio the
               sigma/band argument makes from the other side.
  rho_between  residual correlation between pairs of corners, matched by lap
               within a block. This is what decides whether the QUORUM adds
               protection: near zero and requiring 3 of 4 corners multiplies
               independent evidence, high and the corners fail together so the
               quorum is close to a single measurement wearing four hats.

A CELL is one (block, corner) series in driving order. Cells with fewer than 4
clean passes are dropped -- a linear fit leaves n-2 residual df, so 3 passes
would contribute a single df and 2 would contribute none.

Metrics, measured exactly as `rescore.py` measures them (the same
`pass_metrics` helper, so the evaluator's own arithmetic rather than a parallel
estimate):

    brake_m         signed brake-initiation error against the reference point
    speed_kmh       corner-speed envelope deviation
    apex_excess_m   apex RMS minus the reference's own mean_rms_m

    ~/anaconda3/envs/ac_dev/python.exe -I kit/tools/mdc.py <trace_data> [reference.json]

Reads nothing it can change: no config is written, no reference is rewritten.
Figures are tabulated in README.md.
"""
import collections
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import reference as ref
from tools._blocks import PAIR1_HUMAN_NATIONAL
from tools.rescore import pass_metrics

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

METRICS = ("brake_m", "speed_kmh", "apex_excess_m")
UNITS = {"brake_m": "m", "speed_kmh": "km/h", "apex_excess_m": "m"}

# The improvement available to a learner, per metric, with provenance. The
# denominator MDC is read against. NOT derived from the blocks this script
# reads: those are pre-KR and plateaued (see the `trend` table), so their own
# early-vs-late split is near zero by construction -- `CLAUDE.md` says as much
# about the half-split in `analysis kr`.
AVAILABLE = collections.OrderedDict([
    ("brake_m", (8.19, "the KR diagnostic, 2026-10-14: braking CE +10.56 m over "
                       "laps 0-2 fell to +2.37 m over laps 3-6 once the driver "
                       "was told the error (MILESTONE_LOG)")),
    ("speed_kmh", (None, "NO ANCHOR EXISTS. Nothing in the repo measures how much "
                         "corner-speed deviation a novice can recover; the 85% "
                         "re-reference removed the BIAS (+0.31 km/h) rather than "
                         "measuring a learning range")),
    ("apex_excess_m", (2.2, "apexscan.py: the whole improvement available at the "
                            "apex is ~2.2 m against a lap-to-lap SD of 1.86 m")),
])

MIN_PASSES = 4          # a linear fit needs n-2 >= 2 residual df
WINDOW_MAX = 10
Z95 = 1.959963985

# MDC's confidence level is a CHOICE, not a measurement, and the verdict turns
# on it: see the `confidence` table. 95% is the convention in the Weir /
# reliable-change literature, but these gates are a trigger for running a probe
# rather than a certification, so the design's own asymmetry ("premature
# withdrawal is worse than delayed") is a statement about the FALSE-PASS rate --
# which is what contrasting groups (item 8b) sets explicitly instead of letting
# a conventional z imply one.
CONFIDENCE = ((1.959963985, "95%"), (1.644853627, "90%"), (1.281551566, "80%"))


def detrend(series):
    """OLS linear fit on pass index. Returns (slope, residuals, centred values).

    `centred` keeps the cell mean and removes only the trend, which is what the
    ICC needs: between-corner differences must survive, within-cell drift must
    not.
    """
    n = len(series)
    xs = list(range(n))
    mx = statistics.fmean(xs)
    my = statistics.fmean(series)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs, series)) / sxx) if sxx else 0.0
    residuals = [y - (my + slope * (x - mx)) for x, y in zip(xs, series)]
    centred = [my + r for r in residuals]
    return slope, residuals, centred


def collect(trace_data, table):
    """Per metric, the cells: {(block, corner_id): [value, ...]} in driving order."""
    annotation = json.load(open(os.path.join(
        ROOT, "configs", "annotations", "annotation_%s.json" % table["track"])))
    config = json.load(open(os.path.join(ROOT, "configs", "controller_config.json")))
    length_m = table["track_length_m"]
    by_id = dict((c["corner_id"], c) for c in table["corners"])
    threshold = config["brake_initiation"]["threshold"]
    debounce_s = config["brake_initiation"]["debounce_ms"] / 1000.0

    cells = dict((m, collections.OrderedDict()) for m in METRICS)
    clamped_n = [0]
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
            series = dict((m, []) for m in METRICS)
            for a_pass in ref.corner_passes(rows, corner):
                if not ref.pass_is_clean(a_pass["rows"], pitted):
                    continue
                metrics = pass_metrics(a_pass, corner, corner_ref, length_m,
                                       threshold, debounce_s)
                # A CLAMPED brake initiation is a floor ("at least this early"),
                # not a measurement, so it is a hole here for the same reason
                # `analysis kr` excludes it from every CE/VE average: its value
                # is the braking zone's geometry, and averaging it would turn
                # that geometry into apparent driver noise. This is the one
                # metric that can be clamped.
                clamped = ref.brake_initiation_clamped(
                    a_pass["rows"], corner["zones"]["braking"], threshold, debounce_s)
                if clamped:
                    clamped_n[0] += 1
                # Lap alignment matters for rho_between, so a null is recorded
                # as a hole rather than skipped.
                series["brake_m"].append(
                    None if clamped else metrics.get("brake_initiation_distance_m"))
                speed = metrics.get("min_corner_speed_kmh")
                series["speed_kmh"].append(
                    None if speed is None
                    else speed - corner_ref["corner_speed"]["mean_kmh"])
                rms = metrics.get("apex_rms_m")
                series["apex_excess_m"].append(
                    None if rms is None else rms - corner_ref["apex"]["mean_rms_m"])
            for m in METRICS:
                cells[m][(block, corner["id"])] = series[m]
    return cells, blocks_read, len(annotation["corners"]), clamped_n[0]


def pooled_for(cells, only_corner=None):
    """`pooled`, restricted to one corner_id when `only_corner` is given."""
    subset = collections.OrderedDict(
        (k, v) for k, v in cells.items() if only_corner is None or k[1] == only_corner)
    return pooled(subset)


def pooled(cells):
    """sigma_within pooled by residual df, plus the slopes and the ICC inputs."""
    ss, df, slopes = 0.0, 0, []
    groups = collections.defaultdict(list)   # corner_id -> trend-removed values
    resid_by_cell = {}
    for (block, corner_id), raw in cells.items():
        series = [v for v in raw if v is not None]
        if len(series) < MIN_PASSES:
            continue
        slope, residuals, centred = detrend(series)
        ss += sum(r * r for r in residuals)
        df += len(series) - 2
        slopes.append(slope)
        groups[corner_id].extend(centred)
        # Residuals re-aligned to the original (hole-preserving) index, for rho.
        out, i = [], 0
        for v in raw:
            if v is None:
                out.append(None)
            else:
                out.append(residuals[i])
                i += 1
        resid_by_cell[(block, corner_id)] = out
    sigma = math.sqrt(ss / df) if df else float("nan")
    return sigma, df, slopes, groups, resid_by_cell


def icc_1_1(groups):
    """One-way random effects ICC(1,1), corner as the factor. Shrout & Fleiss."""
    sizes = [len(v) for v in groups.values() if len(v) > 1]
    if len(sizes) < 2:
        return float("nan"), 0
    allv = [v for vals in groups.values() for v in vals]
    grand = statistics.fmean(allv)
    k = len(sizes)
    msb_num = sum(len(v) * (statistics.fmean(v) - grand) ** 2
                  for v in groups.values() if len(v) > 1)
    msw_num = sum((x - statistics.fmean(v)) ** 2
                  for v in groups.values() if len(v) > 1 for x in v)
    dfb, dfw = k - 1, sum(sizes) - k
    if not dfb or not dfw:
        return float("nan"), 0
    msb, msw = msb_num / dfb, msw_num / dfw
    n0 = statistics.fmean(sizes)
    denom = msb + (n0 - 1) * msw
    return ((msb - msw) / denom if denom else float("nan")), int(n0)


def rho_between(resid_by_cell, corner_ids):
    """Pearson r between corners' residuals, matched by pass index within block."""
    out = []
    for i, a in enumerate(corner_ids):
        for b in corner_ids[i + 1:]:
            xs, ys = [], []
            for (block, cid), series in resid_by_cell.items():
                if cid != a:
                    continue
                other = resid_by_cell.get((block, b))
                if other is None:
                    continue
                for x, y in zip(series, other):
                    if x is not None and y is not None:
                        xs.append(x)
                        ys.append(y)
            if len(xs) < 5:
                continue
            mx, my = statistics.fmean(xs), statistics.fmean(ys)
            sxx = sum((x - mx) ** 2 for x in xs)
            syy = sum((y - my) ** 2 for y in ys)
            if sxx <= 0 or syy <= 0:
                continue
            r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)
            out.append((a, b, r, len(xs)))
    return out


def mdc(sigma, n, z=Z95):
    return z * math.sqrt(2.0) * sigma / math.sqrt(n)


def needs_n(sigma, avail, z=Z95, cap=40):
    return next((n for n in range(1, cap + 1) if mdc(sigma, n, z) < avail), None)


def main(argv):
    trace_data = argv[0]
    table_path = (argv[1] if len(argv) > 1 else
                  os.path.join(ROOT, "configs", "references", "reference_pair1.json"))
    table = json.load(open(table_path))
    cells, blocks_read, n_corners, clamped = collect(trace_data, table)

    print("mdc -- Gate G2 item 8a (Weir 2005), %s" % os.path.basename(table_path))
    print("blocks read  %d of %d   corners %d   cells kept: >= %d clean passes"
          % (blocks_read, len(PAIR1_HUMAN_NATIONAL), n_corners, MIN_PASSES))
    print("clamped brake initiations excluded: %d" % clamped)
    print("MDC95(n) = 1.96 * sqrt(2) * sigma_within / sqrt(n)\n")

    results = {}
    print("## noise and reliability\n")
    print("  %-14s %5s %5s %5s   %9s %7s %7s   %s"
          % ("metric", "cells", "n", "df", "sigma", "ICC", "n0", "median slope /pass"))
    for m in METRICS:
        sigma, df, slopes, groups, resid = pooled(cells[m])
        kept = sum(1 for v in cells[m].values()
                   if len([x for x in v if x is not None]) >= MIN_PASSES)
        n_obs = sum(len([x for x in v if x is not None]) for v in cells[m].values())
        icc, n0 = icc_1_1(groups)
        results[m] = (sigma, resid)
        print("  %-14s %5d %5d %5d   %7.3f %s %7.3f %7d   %+8.4f %s"
              % (m, kept, n_obs, df, sigma, UNITS[m], icc, n0,
                 statistics.median(slopes) if slopes else float("nan"), UNITS[m]))
    print("")
    print("  The slopes are the check on this data's OWN ability to supply an")
    print("  improvement-available figure: these seven blocks are pre-KR and the")
    print("  driver was plateaued, so a near-zero slope means the denominator")
    print("  must come from elsewhere -- it does, see `available` below.")
    print("")

    print("## per corner -- because the band and the qualification are per corner\n")
    print("A single pooled sigma is the wrong unit: each corner is effectively a")
    print("different instrument, and one noisy corner drags the whole pool. Corner 1")
    print("is the one `CLAUDE.md` records as mis-annotated 'taken flat' at")
    print("drive-and-mark pace and re-derived later.\n")
    corner_ids_pc = sorted(set(cid for (_b, cid) in cells[METRICS[0]].keys()))
    for m in METRICS:
        avail = AVAILABLE[m][0]
        print("  %s (improvement available: %s)"
              % (m, ("%.2f %s" % (avail, UNITS[m])) if avail else "NO ANCHOR"))
        print("    %-8s %5s %5s %11s %9s %9s   %s"
              % ("corner", "n", "df", "sigma", "MDC95(3)", "MDC95(4)", "needs n"))
        for cid in corner_ids_pc:
            sigma, df, _slopes, _g, _r = pooled_for(cells[m], cid)
            if not df:
                continue
            n_obs = sum(len([x for x in v if x is not None])
                        for k, v in cells[m].items() if k[1] == cid)
            need = (next((n for n in range(1, 41) if mdc(sigma, n) < avail), None)
                    if avail else None)
            label = ("n >= %d" % need) if need else ("NO n <= 40" if avail else "-")
            print("    %-8s %5d %5d %7.2f %-4s %9.2f %9.2f   %s"
                  % (cid, n_obs, df, sigma, UNITS[m],
                     mdc(sigma, 3), mdc(sigma, 4), label))
        print("")

    print("## MDC95(n) -- the smallest change a window of n passes can see\n")
    print("  %-14s %s" % ("metric", "".join("%8d" % n for n in range(1, WINDOW_MAX + 1))))
    for m in METRICS:
        sigma = results[m][0]
        print("  %-14s %s" % (m, "".join("%8.2f" % mdc(sigma, n)
                                         for n in range(1, WINDOW_MAX + 1))))
    print("")

    print("## verdict -- the n at which MDC drops under the improvement available\n")
    for m in METRICS:
        sigma = results[m][0]
        avail, why = AVAILABLE[m]
        if avail is None:
            print("  %-14s UNDECIDABLE -- %s" % (m, why))
            print("  %-14s   (MDC95(3) = %.2f %s; nothing to compare it with)"
                  % ("", mdc(sigma, 3), UNITS[m]))
            continue
        need = next((n for n in range(1, 41) if mdc(sigma, n) < avail), None)
        verdict = ("n >= %d" % need) if need else "NO n <= 40 suffices"
        print("  %-14s available %.2f %s -> needs %s   (MDC95(3) = %.2f, MDC95(4) = %.2f)"
              % (m, avail, UNITS[m], verdict, mdc(sigma, 3), mdc(sigma, 4)))
        print("  %-14s   %s" % ("", why))
    print("")

    print("## confidence -- the verdict turns on a CHOICE, not on the data\n")
    print("MDC95 is strict by convention, not by necessity. `quorum` counts the")
    print("corners whose MDC falls under the available improvement at that window;")
    print("the element's quorum needs 3 of 4. Read the 80% row against the 95%")
    print("one: the same sigmas license opposite answers.\n")
    print("  %-14s %6s   %-30s %9s %9s"
          % ("metric", "conf", "needs n, per corner", "quorum@3", "quorum@4"))
    for m in METRICS:
        avail = AVAILABLE[m][0]
        if avail is None:
            print("  %-14s %6s   (no anchor -- undecidable at any confidence)"
                  % (m, "-"))
            continue
        for z, lab in CONFIDENCE:
            per, ok3, ok4 = [], 0, 0
            for cid in corner_ids_pc:
                sigma, df, _s, _g, _r = pooled_for(cells[m], cid)
                if not df:
                    continue
                need = needs_n(sigma, avail, z)
                per.append("c%s:%s" % (cid, need if need else ">40"))
                ok3 += 1 if mdc(sigma, 3, z) < avail else 0
                ok4 += 1 if mdc(sigma, 4, z) < avail else 0
            print("  %-14s %6s   %-30s %7d/4 %7d/4"
                  % (m, lab, " ".join(per), ok3, ok4))
    print("")
    print("  So MDC ALONE CANNOT DECIDE THE WINDOW: at 95% neither 2-of-3 nor the")
    print("  frozen 3-of-4 reaches a braking quorum, and at 80% BOTH do. That is")
    print("  the argument for item 8b -- state a false-pass rate and report the")
    print("  false-fail rate, rather than letting a conventional z imply one.")
    print("")

    print("## rho_between -- does the quorum multiply independent evidence?\n")
    corner_ids = sorted(set(cid for (_b, cid) in cells[METRICS[0]].keys()))
    for m in METRICS:
        pairs = rho_between(results[m][1], corner_ids)
        if not pairs:
            print("  %-14s (too few lap-matched pairs)" % m)
            continue
        rs = [r for (_a, _b, r, _n) in pairs]
        print("  %-14s pairs %2d   median r %+0.3f   range %+0.3f .. %+0.3f"
              % (m, len(pairs), statistics.median(rs), min(rs), max(rs)))
    print("")
    print("  Near zero: a corner's noise is its own, so requiring 3 of 4 corners")
    print("  really is four looks at the driver rather than one. Strongly")
    print("  positive: the corners fail together and the quorum's protection is")
    print("  much weaker than its denominator suggests.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
