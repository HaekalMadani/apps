"""How many probes does the study yield, and how few is too few for RQ2?

Written 2026-11-01 for ARS review roadmap S20 (DA M6,
`novelty_audit/review/round1/synthesis.md`). Concept brief section 6's outcome
table opens with gate 1, "too few probes", whose floor was left to be "set with
the pilot stopping rule". This sets it. Two parts:

A -- YIELD. Probe yield is a model output (DA M6): it depends on the lap-to-lap
  sigma, and the brake and speed sigmas in `simulate.MODEL` are assumptions
  (apex is measured). Participants are drawn as in `nullrecovery.py` (committed
  exponential trend, no dependency) with the BRAKE and SPEED sigmas scaled by s;
  apex stays at its measured value. Per element and s: uncensored probes per
  participant (reverted + removed; censored probes are excluded from P_obs, R7),
  the share of participants contributing any, and over n = 15 studies the
  distribution of the pooled count. Also P(zero braking probes over the n = 2
  pilot), which says whether the pilot's own probe count can carry a rule.

B -- FLOOR. The R6 decision rule (90% participant cluster bootstrap on
  delta_hat against the full-salience null, MDI 0.10, the `nulldecision.py`
  machinery unchanged) run on BRAKING at committed sigma, for studies of
  n = 4, 6, 8, 10, 15 so the pooled uncensored count spans a wide range, at
  delta = 0 (no dependency) and delta = 0.375 band (true delta ~0.24). Results
  are binned by the study's pooled uncensored braking-probe count K.

PRE-STATED FLOOR CRITERION (fixed before the first run). The floor K* is the
smallest K such that, among delta = 0 studies whose pooled count is >= K:
  (i)  the bootstrap interval is defined in >= 99% of studies, and
  (ii) the false "excess" rate is <= 0.05, the nominal one-sided rate of a
       90% interval -- i.e. the rule is still calibrated there.
Below K* the verdict is gate 1 ("too few probes"), not "indeterminate": an
uncalibrated interval must not be allowed to report an excess. Detection at
delta = 0.375 is reported per bin but does not set K*: a floor that guaranteed
power would be a different (and at n = 15, unreachable) promise.

THAT CRITERION WAS VACUOUS, AND IT WAS REPLACED AFTER THE FIRST RUN (post hoc,
2026-11-01; say so wherever K* is quoted). It returned K* = 0: the false
"excess" rate stays at 1.4-6.3% in every K bin, with no trend. The failure at
small K is the OTHER verdict. With 2-3 contributing participants the cluster
bootstrap degenerates and its interval is too NARROW, so it declares "no excess"
when a real excess exists (53% of studies at K 0-2 with true delta 0.23). The
replacement guards that verdict, tested near the MDI with an extra cell
(delta = 0.3 band, true delta 0.133; `floor ... 0.3`). K* is the smallest K
from which the false "no excess" rate is <= 0.05 at true delta 0.23, and has
reached its K-invariant plateau at true delta 0.133. That gives K* = 7. The
plateau is ~5-8%, not 5%, and it does not shrink with K, so a larger floor
would not remove it. It is NOT fit uncertainty: `nullinterval.py` (R6, round 2)
resamples the null's fit and moves every verdict rate by <= 0.03. It is within
~2 Monte Carlo SE of nominal, plus percentile-bootstrap undercoverage at 15
clusters. (An earlier version of this note blamed fit uncertainty; R6 refuted
that.)

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nullyield.py yield [participants-per-cell] [seed]
    python kit/tools/nullyield.py floor [studies-per-cell] [replicates] [boot] [seed] [workers]
"""
import multiprocessing
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import nullcheck as C
import nulldecision as D
import nullrecovery as N
from trace_kit import evaluator as ev
from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS

SCALES = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
SCALED = ("braking", "corner_speed")     # apex sigma is measured; it stays put
STUDY_N = 15
PILOT_N = 2                               # evaluation plan v2, Phase 2
FLOOR_NS = (4, 6, 8, 10, 15)
FLOOR_DELTAS = (0.0, 0.375)
KGRID = (3, 5, 7, 9, 11, 13, 15)
BINS = ((0, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 13), (14, 17), (18, 99))


def participant(rng, scale, applicable):
    p = N.true_participant(rng, "exp", 1.0, applicable)
    for e in SCALED:
        p[e]["sigma"] *= scale
    return p


def setup():
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    return cfg, reference, applicable, corner_ids


def uncensored(t):
    return t[1] + t[2]


# --- A: yield ----------------------------------------------------------------

def yield_cell(task):
    seed, scale, count = task
    cfg, reference, applicable, corner_ids = setup()
    rng = random.Random("{}|{}".format(seed, scale))
    rows = []
    for _ in range(count):
        truth = participant(rng, scale, applicable)
        t, _ = N.run_stream(cfg, reference, applicable, truth,
                            N.draw_z(rng, corner_ids, S.BLOCK_LAPS), False)
        rows.append(dict((e, (uncensored(t[e]), t[e][3])) for e in ELEMENTS))
    return scale, rows


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def main_yield(argv):
    count = int(argv[2]) if len(argv) > 2 else 3000
    seed = argv[3] if len(argv) > 3 else "nullyield"
    print("participants/cell={} seed={} (brake+speed sigma scaled; apex measured)".format(count, seed))
    with multiprocessing.Pool(len(SCALES)) as pool:
        res = dict(pool.map(yield_cell, [(seed, s, count) for s in SCALES]))
    rng = random.Random(seed + "|studies")
    for e in ELEMENTS:
        print("\n== {} ==".format(e))
        print("  s     sigma   unc/pp  cens/pp  share>=1   n=15 pooled: mean  p10  p50  p90"
              "   P(pilot n=2 has 0)")
        for s in SCALES:
            rows = res[s]
            unc = [r[e][0] for r in rows]
            cen = [r[e][1] for r in rows]
            pooled = [sum(rng.choice(unc) for _ in range(STUDY_N)) for _ in range(4000)]
            pilot0 = sum(1 for _ in range(4000)
                         if sum(rng.choice(unc) for _ in range(PILOT_N)) == 0) / 4000.0
            sig = S.MODEL[N.SIGMA_KEY[e]] * (s if e in SCALED else 1.0)
            print("  {:<5} {:5.2f}   {:5.2f}   {:5.2f}    {:.3f}       {:5.1f}  {:3d}  {:3d}  {:3d}"
                  "      {:.3f}".format(
                      s, sig, sum(unc) / float(len(unc)), sum(cen) / float(len(cen)),
                      sum(1 for u in unc if u) / float(len(unc)),
                      sum(pooled) / float(len(pooled)), pct(pooled, 0.1), pct(pooled, 0.5),
                      pct(pooled, 0.9), pilot0))
        print("  P(n=15 pooled >= K):  K = " + " ".join("{:>4}".format(k) for k in KGRID))
        for s in SCALES:
            unc = [r[e][0] for r in res[s]]
            pooled = [sum(rng.choice(unc) for _ in range(STUDY_N)) for _ in range(4000)]
            print("   s={:<5}            ".format(s) + " ".join(
                "{:.2f}".format(sum(1 for x in pooled if x >= k) / 4000.0) for k in KGRID))


# --- B: floor ----------------------------------------------------------------

def floor_study(task):
    """`nulldecision.run_study` for braking only, with n as a parameter."""
    seed, delta, n, study, reps, boot = task
    cfg, reference, applicable, corner_ids = setup()
    floors = cfg["band_floors"]
    rng = random.Random("{}|{}|{}|{}".format(seed, delta, n, study))
    e = "braking"
    obs_t, null_t, dep_t, nodep_t = [], [], [], []
    for _ in range(n):
        truth = participant(rng, 1.0, applicable)
        h = rng.uniform(0.0, 2.0)
        dep = dict((x, (h * delta * floors[D.FLOOR_KEY[x]], 1.0)) for x in ELEMENTS)
        tally, obs = N.run_stream(cfg, reference, applicable, truth,
                                  N.draw_z(rng, corner_ids, N.TOTAL_LAPS), True, dep)
        obs_t.append(tally[e])
        null = dict((x, C.fit(C.fitted(obs[x]))) for x in ELEMENTS)
        acc = [[0, 0, 0, 0] for _ in range(3)]
        for _ in range(reps):
            z = N.draw_z(rng, corner_ids, S.BLOCK_LAPS)
            for slot, (params, d) in enumerate(((null, None), (truth, dep), (truth, None))):
                t, _ = N.run_stream(cfg, reference, applicable, params, z, False, d)
                acc[slot] = D.add(acc[slot], t[e])
        null_t.append(acc[0])
        dep_t.append(acc[1])
        nodep_t.append(acc[2])

    def pooled(rows):
        tot = [0, 0, 0, 0]
        for r in rows:
            tot = D.add(tot, r)
        return tot

    po = pooled(obs_t)
    idx = list(range(n))
    ds = []
    for _ in range(boot):
        pick = [rng.choice(idx) for _ in idx]
        d = D.rate(pooled([obs_t[i] for i in pick]), "exclude") - \
            D.rate(pooled([null_t[i] for i in pick]), "exclude")
        if d == d:
            ds.append(d)
    ds.sort()
    lo = hi = float("nan")
    if len(ds) >= boot // 2:
        lo, hi = ds[int(0.05 * len(ds))], ds[int(0.95 * len(ds)) - 1]
    return {"delta": delta, "n": n, "K": uncensored(po),
            "contrib": sum(1 for t in obs_t if uncensored(t)),
            "true": D.rate(pooled(dep_t), "exclude") - D.rate(pooled(nodep_t), "exclude"),
            "est": D.rate(po, "exclude") - D.rate(pooled(null_t), "exclude"),
            "lo": lo, "hi": hi}


def main_floor(argv):
    studies = int(argv[2]) if len(argv) > 2 else 300
    reps = int(argv[3]) if len(argv) > 3 else 30
    boot = int(argv[4]) if len(argv) > 4 else 1000
    seed = argv[5] if len(argv) > 5 else "nullyield"
    workers = int(argv[6]) if len(argv) > 6 else max(1, (os.cpu_count() or 2) - 1)
    deltas = tuple(float(x) for x in argv[7].split(",")) if len(argv) > 7 else FLOOR_DELTAS
    print("studies/cell={} n={} replicates={} boot={} seed={} workers={} deltas={}".format(
        studies, FLOOR_NS, reps, boot, seed, workers, deltas))
    tasks = [(seed, d, n, i, reps, boot) for d in deltas for n in FLOOR_NS
             for i in range(studies)]
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        rows = list(pool.imap_unordered(floor_study, tasks, chunksize=2))
    print("elapsed {:.0f} s".format(time.time() - t0))

    def ok(r):
        return r["lo"] == r["lo"]

    for d in deltas:
        rs = [r for r in rows if r["delta"] == d]
        tr = [r["true"] for r in rs if r["true"] == r["true"]]
        print("\n== braking, delta = {} band (true delta {:+.3f}) ==".format(
            d, sum(tr) / len(tr) if tr else float("nan")))
        print("  K bin    studies  contrib(med)  defined  P(excess)  P(no excess)  P(indet)  med width")
        for a, b in BINS:
            br = [r for r in rs if a <= r["K"] <= b]
            if not br:
                continue
            m = float(len(br))
            okr = [r for r in br if ok(r)]
            print("  {:>2}-{:<3}   {:5d}     {:4.1f}        {:.3f}    {:.3f}      {:.3f}        {:.3f}     {:.3f}".format(
                a, b if b < 99 else "+", len(br), D.median([r["contrib"] for r in br]),
                len(okr) / m, sum(1 for r in okr if r["lo"] > 0) / m,
                sum(1 for r in okr if r["hi"] < 0.10) / m,
                1 - sum(1 for r in okr if r["lo"] > 0 or r["hi"] < 0.10) / m,
                D.median([r["hi"] - r["lo"] for r in okr])))
    # The pre-stated criterion, on the delta = 0 studies, cumulative from K upward.
    null_rows = [r for r in rows if r["delta"] == 0.0]
    print("\nCumulative, delta = 0, studies with pooled K >= k:")
    print("  k   studies  defined  P(excess)")
    star = None
    for k in range(0, 31):
        br = [r for r in null_rows if r["K"] >= k]
        if len(br) < 50:
            break
        m = float(len(br))
        defined = sum(1 for r in br if ok(r)) / m
        fx = sum(1 for r in br if ok(r) and r["lo"] > 0) / m
        print("  {:<3} {:5d}    {:.3f}    {:.3f}".format(k, len(br), defined, fx))
        if star is None and defined >= 0.99 and fx <= 0.05:
            star = k
    print("K* (pre-stated criterion) = {}".format(star))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    mode = sys.argv[1] if len(sys.argv) > 1 else "yield"
    (main_yield if mode == "yield" else main_floor)(sys.argv)
