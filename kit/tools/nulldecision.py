"""What can the RQ2 decision rule resolve, and how should censored probes count?

Written 2026-10-30 for ARS review roadmap R6 and R7
(`novelty_audit/review/round1/synthesis.md`; methodology W5/W6, perspective W4,
DA M2/M5).

R7 -- CENSORING. A probe still running when the 15-lap block ends is censored.
Three rules, each applied IDENTICALLY to P_obs and to the simulated P_null:
  exclude   rate = reverted / (reverted + removed); censored are not counted
  as_pass   censored count as passes:  reverted / (reverted + removed + censored)
  as_fail   censored count as failures: (reverted + censored) / (all three)
For each rule: the censored share, the true delta, and whether the estimate is
biased relative to it.

R6 -- DESIGN SENSITIVITY. Per synthetic study (n = 15, pair 1, real controller):
  delta_hat = P_obs - P_hat, where P_obs comes from ONE stream per participant
  (what the study sees) and P_hat from the primary null (full-salience
  exponential fit, `nullcheck.fit`) driven for R replicates per participant.
  The 90% interval is a participant cluster bootstrap (B resamples of whole
  participants: their observed probes and their null replicates together).
  Within-participant fit uncertainty is NOT resampled, so the interval is
  somewhat optimistic.
  Verdict, with a minimum delta of interest MDI:
    excess        lower 90% bound > 0
    no excess     upper 90% bound < MDI
    indeterminate otherwise
The true delta in each cell is P_dep - P_nodep from the true parameters
(replicated, with and without the dependency). The dependency is sustained, a
mean shift of delta x band on every withdrawn pass, varying between drivers
(x U(0, 2), mean 1) as in `nulltransient.py`.

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nulldecision.py [studies-per-cell] [replicates] [boot] [seed] [workers]
"""
import math
import multiprocessing
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import nullcheck as C
import nullrecovery as N
from trace_kit import evaluator as ev
from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS

DELTAS = (0.0, 0.125, 0.25, 0.375, 0.5)
RULES = ("exclude", "as_pass", "as_fail")
MDIS = (0.05, 0.10, 0.15)
FLOOR_KEY = {"braking": "braking_m", "corner_speed": "corner_speed_kmh", "apex": "apex_m"}


def rate(t, rule):
    """t = [probes, reverted, removed, censored]."""
    rev, rem, cen = t[1], t[2], t[3]
    if rule == "exclude":
        num, den = rev, rev + rem
    elif rule == "as_pass":
        num, den = rev, rev + rem + cen
    else:
        num, den = rev + cen, rev + rem + cen
    return num / float(den) if den else float("nan")


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def run_study(task):
    seed, delta, study, reps, boot = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    floors = cfg["band_floors"]
    rng = random.Random("{}|{}|{}".format(seed, delta, study))

    obs_t, null_t, dep_t, nodep_t = [], [], [], []
    for _ in range(N.PARTICIPANTS):
        truth = N.true_participant(rng, "exp", 1.0, applicable)
        h = rng.uniform(0.0, 2.0)
        dep = dict((e, (h * delta * floors[FLOOR_KEY[e]], 1.0)) for e in ELEMENTS)
        tally, obs = N.run_stream(cfg, reference, applicable, truth,
                                  N.draw_z(rng, corner_ids, N.TOTAL_LAPS), True, dep)
        obs_t.append(tally)
        null = dict((e, C.fit(C.fitted(obs[e]))) for e in ELEMENTS)
        acc = [dict((e, [0, 0, 0, 0]) for e in ELEMENTS) for _ in range(3)]
        for _ in range(reps):
            z = N.draw_z(rng, corner_ids, S.BLOCK_LAPS)
            for slot, (params, d) in enumerate(((null, None), (truth, dep), (truth, None))):
                t, _ = N.run_stream(cfg, reference, applicable, params, z, False, d)
                for e in ELEMENTS:
                    acc[slot][e] = add(acc[slot][e], t[e])
        null_t.append(acc[0])
        dep_t.append(acc[1])
        nodep_t.append(acc[2])

    def pooled(rows, e):
        tot = [0, 0, 0, 0]
        for r in rows:
            tot = add(tot, r[e])
        return tot

    out = {}
    idx = list(range(N.PARTICIPANTS))
    for e in ELEMENTS:
        po, pn = pooled(obs_t, e), pooled(null_t, e)
        pd, pnd = pooled(dep_t, e), pooled(nodep_t, e)
        res = {"probes_pp": po[0] / float(N.PARTICIPANTS),
               "cens_share": po[3] / float(po[0]) if po[0] else float("nan")}
        for rule in RULES:
            est = rate(po, rule) - rate(pn, rule)
            true = rate(pd, rule) - rate(pnd, rule)
            res[rule] = {"est": est, "true": true}
        # Bootstrap only for the primary rule.
        ds = []
        for _ in range(boot):
            pick = [rng.choice(idx) for _ in idx]
            a = pooled([obs_t[i] for i in pick], e)
            b = pooled([null_t[i] for i in pick], e)
            d = rate(a, "exclude") - rate(b, "exclude")
            if d == d:
                ds.append(d)
        ds.sort()
        if len(ds) >= boot // 2:
            res["lo"] = ds[int(0.05 * len(ds))]
            res["hi"] = ds[int(0.95 * len(ds)) - 1]
        else:
            res["lo"] = res["hi"] = float("nan")
        out[e] = res
    return delta, out


def median(xs):
    xs = sorted(x for x in xs if x == x)
    n = len(xs)
    return float("nan") if not n else (xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2]))


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 300
    reps = int(argv[2]) if len(argv) > 2 else 30
    boot = int(argv[3]) if len(argv) > 3 else 1000
    seed = argv[4] if len(argv) > 4 else "nulldecision"
    workers = int(argv[5]) if len(argv) > 5 else max(1, (os.cpu_count() or 2) - 1)
    print("studies/cell={} participants={} replicates={} boot={} seed={} workers={}".format(
        studies, N.PARTICIPANTS, reps, boot, seed, workers))
    tasks = [(seed, d, i, reps, boot) for d in DELTAS for i in range(studies)]
    res = dict((d, []) for d in DELTAS)
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for d, v in pool.imap_unordered(run_study, tasks, chunksize=2):
            res[d].append(v)
    print("elapsed {:.0f} s".format(time.time() - t0))

    for e in ELEMENTS:
        print("\n== {} ==".format(e))
        print("R7 censoring: delta  probes/pp  cens  | per rule: true delta / mean est / bias")
        for d in DELTAS:
            rs = [r[e] for r in res[d]]
            parts = []
            for rule in RULES:
                tr = [r[rule]["true"] for r in rs if r[rule]["true"] == r[rule]["true"]]
                es = [r[rule]["est"] for r in rs if r[rule]["est"] == r[rule]["est"]]
                mt = sum(tr) / len(tr) if tr else float("nan")
                me = sum(es) / len(es) if es else float("nan")
                parts.append("{} {:+.3f}/{:+.3f}/{:+.3f}".format(rule, mt, me, me - mt))
            print("  {:<5}  {:5.2f}  {:.3f} | {}".format(
                d, sum(r["probes_pp"] for r in rs) / len(rs),
                median([r["cens_share"] for r in rs]), "  ".join(parts)))
        print("R6 decision (exclude rule, 90% cluster bootstrap):")
        print("  delta  true_d  med_width  P(excess) " +
              " ".join("P(noexc<{0})".format(m) for m in MDIS) + "  P(indet@0.10)  undefined")
        for d in DELTAS:
            rs = [r[e] for r in res[d]]
            ok = [r for r in rs if r["lo"] == r["lo"]]
            n = float(len(rs))
            tr = [r["exclude"]["true"] for r in rs if r["exclude"]["true"] == r["exclude"]["true"]]
            exc = sum(1 for r in ok if r["lo"] > 0) / n
            noexc = [sum(1 for r in ok if r["hi"] < m) / n for m in MDIS]
            indet = 1.0 - exc - noexc[1] - (n - len(ok)) / n
            print("  {:<5}  {:+.3f}   {:.3f}     {:.3f}    {}   {:.3f}        {:.3f}".format(
                d, sum(tr) / len(tr) if tr else float("nan"),
                median([r["hi"] - r["lo"] for r in ok]), exc,
                "  ".join("{:.3f}     ".format(x) for x in noexc), indet, (n - len(ok)) / n))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
