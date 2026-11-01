"""How much of a real guidance dependency does each RQ2 null absorb?

Written 2026-10-30 for roadmap item R5 of the ARS methodology review
(`novelty_audit/review/round1/synthesis.md`; DA C1, methodology W3, domain W2,
perspective W6). The R2 primary null (`nullrecovery.py`) is fitted on cue-off
laps, and cue-off laps are where dependency shows. A null that learns the
dependency as ordinary noise raises P_null and pulls delta toward zero.

AUTHOR DECISION (2026-10-30): BOTH manifestations count as guidance dependency:
a MEAN SHIFT back toward the novice error on withdrawal, and a VARIANCE INCREASE
on withdrawal. The probe fails on either. So the null that excludes dependency
by definition is the one fitted on cue-ON laps only, and every other null is
judged by how much of a known injected dependency it hides.

Method. Synthetic participants come from the committed exponential learner at 1x
noise (`nullrecovery.true_participant`). A dependency is injected on every pass
driven with an element hidden (probe, removed, unassisted): the mean moves by
delta x band in the novice direction, and the noise is scaled by kappa. The same
size is used for all three elements. Per study:

    true delta = P_dep - P_nodep    (true parameters, with / without dependency)
    est. delta = P_dep - P_hat      (P_hat from a null fitted on the
                                     dependency-contaminated data)
    attenuation = est. delta / true delta    (1 = nothing absorbed)

P_dep is the EXPECTED observed rate (replicates of the true process), so the
attenuation isolates absorption from P_obs's sampling error. That sampling
error is reported separately, from the one stream per participant a real study
would have (`sd obs`). Every rate runs on common random numbers.

The nulls:
  primary  R2's choice: exponential trend, rate pooled across drivers,
           per-driver amplitudes and sigma, all fitted on cue-off laps
  lopo     the same, but each participant's OWN probe laps are left out (the
           shared rate is refitted without them; amplitudes and sigma come from
           that participant's unassisted and removed laps)
  hybrid   per-driver exponential trend on ALL laps, sigma from cue-off residuals
  cueon    per-driver exponential trend and sigma on cue-ON laps only (the
           unbiased-by-definition null, whose identifiability R2 never tested;
           the delta = 0, kappa = 1 cell is that test)
  cuefull  the same on FULL-salience laps only. Reduced salience is a partial
           withdrawal, so if it carries part of the dependency (the optional
           reduced fraction r below) the cueon null absorbs that part, and
           this one does not.

An optional reduced fraction r applies r x the dependency on passes driven at
reduced salience (`nullrecovery.run_stream`).

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nullabsorption.py [studies-per-cell] [replicates] [seed] [workers] [delta:kappa,...] [r]
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

import nullrecovery as N
from trace_kit import evaluator as ev
from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS

DELTAS = (0.0, 0.5, 1.0)     # mean shift on withdrawal, in band units
KAPPAS = (1.0, 1.5, 2.0)     # noise multiplier on withdrawal
NULLS = ("primary", "lopo", "hybrid", "cueon", "cuefull")
FLOOR_KEY = {"braking": "braking_m", "corner_speed": "corner_speed_kmh", "apex": "apex_m"}
CUE_ON = ("full", "reduced")


def _sigma(sse, n, p):
    return math.sqrt(sse / max(n - p, 1))


def _sse_table(obs, mean):
    return sum((y - mean[c][l]) ** 2 for l, c, y, _ in obs)


def _table(a, g):
    return dict((c, [a[c] * g[l] for l in range(N.TOTAL_LAPS)]) for c in a)


def _pooled_rate(obs_sets):
    best = None
    for r in N.RATE_GRID:
        g = N._gexp(r)
        total = sum(N._sse_mult(o, g, N._amps_mult(o, g)) for o in obs_sets)
        if best is None or total < best[0]:
            best = (total, g)
    return best[1]


def fit_nulls(obs_all):
    """null -> [params per participant], each params = {element: {mean, sigma}}."""
    out = dict((k, [dict() for _ in obs_all]) for k in NULLS)
    for e in ELEMENTS:
        off = [[o for o in obs[e] if o[3] in N.CUE_OFF] for obs in obs_all]
        on = [[o for o in obs[e] if o[3] in CUE_ON] for obs in obs_all]
        full = [[o for o in obs[e] if o[3] == "full"] for obs in obs_all]
        everything = [list(obs[e]) for obs in obs_all]

        g = _pooled_rate(off)
        for i, o in enumerate(off):
            a = N._amps_mult(o, g)
            mean = _table(a, g)
            out["primary"][i][e] = {"mean": mean, "sigma": _sigma(_sse_table(o, mean), len(o), len(a))}

        for i in range(len(off)):
            own = [o for o in off[i] if o[3] != "probe"]
            others = [off[j] for j in range(len(off)) if j != i]
            gi = _pooled_rate(others + [own])
            a = N._amps_mult(own, gi)
            mean = _table(a, gi)
            out["lopo"][i][e] = {"mean": mean, "sigma": _sigma(_sse_table(own, mean), len(own), len(a))}

        for i in range(len(off)):
            mean, _ = N.fit_exp_driver(everything[i])
            out["hybrid"][i][e] = {"mean": mean,
                                   "sigma": _sigma(_sse_table(off[i], mean), len(off[i]), 0)}
            mean, p = N.fit_exp_driver(on[i])
            out["cueon"][i][e] = {"mean": mean, "sigma": _sigma(_sse_table(on[i], mean), len(on[i]), p)}
            mean, p = N.fit_exp_driver(full[i])
            out["cuefull"][i][e] = {"mean": mean, "sigma": _sigma(_sse_table(full[i], mean), len(full[i]), p)}
    return out


def run_study(task):
    seed, delta, kappa, study, reps, rfrac = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    floors = cfg["band_floors"]
    dep = dict((e, (delta * floors[FLOOR_KEY[e]], kappa, rfrac)) for e in ELEMENTS)
    # rfrac is left out of the seed when it is 0, so the committed runs reproduce.
    rng = random.Random("{}|{}|{}|{}".format(seed, delta, kappa, study) if not rfrac
                        else "{}|{}|{}|{}|r{}".format(seed, delta, kappa, study, rfrac))

    truths = [N.true_participant(rng, "exp", 1.0, applicable) for _ in range(N.PARTICIPANTS)]
    observed, obs_all = [], []
    for tp in truths:
        tally, obs = N.run_stream(cfg, reference, applicable, tp,
                                  N.draw_z(rng, corner_ids, N.TOTAL_LAPS), True, dep)
        observed.append(tally)
        obs_all.append(obs)
    nulls = fit_nulls(obs_all)
    zs = [[N.draw_z(rng, corner_ids, S.BLOCK_LAPS) for _ in range(reps)] for _ in truths]

    def tally(param_list, d):
        tot = dict((e, [0, 0, 0, 0]) for e in ELEMENTS)
        for params, zp in zip(param_list, zs):
            for z in zp:
                t, _ = N.run_stream(cfg, reference, applicable, params, z, False, d)
                for e in ELEMENTS:
                    for k in range(4):
                        tot[e][k] += t[e][k]
        return tot

    res = {"dep": tally(truths, dep), "nodep": tally(truths, None),
           "observed": dict((e, [sum(o[e][k] for o in observed) for k in range(4)])
                            for e in ELEMENTS)}
    for k in NULLS:
        res[k] = tally(nulls[k], None)
    return (delta, kappa), res


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 60
    reps = int(argv[2]) if len(argv) > 2 else 40
    seed = argv[3] if len(argv) > 3 else "nullabsorption"
    workers = int(argv[4]) if len(argv) > 4 else max(1, (os.cpu_count() or 2) - 1)
    # Optional "delta:kappa[,delta:kappa]" subset, e.g. "0.0:1.0" for the
    # no-dependency cell alone (the cue-on null's R2-style recovery check).
    grid = ([tuple(float(v) for v in c.split(":")) for c in argv[5].split(",")]
            if len(argv) > 5 else [(d, k) for d in DELTAS for k in KAPPAS])
    rfrac = float(argv[6]) if len(argv) > 6 else 0.0
    cfg = S.load_config()
    print("reduced fraction r = {}".format(rfrac))
    print("studies/cell={} participants={} replicates={} seed={} workers={}".format(
        studies, N.PARTICIPANTS, reps, seed, workers))
    print("truth: exp trend, 1x committed sigmas; floors {}".format(cfg["band_floors"]))

    tasks = [(seed, d, k, i, reps, rfrac) for d, k in grid for i in range(studies)]
    cells = dict(((d, k), []) for d, k in grid)
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for key, res in pool.imap_unordered(run_study, tasks):
            cells[key].append(res)
    print("elapsed {:.0f} s".format(time.time() - t0))

    rate = N.rate
    for e in ELEMENTS:
        print("\n== {} ==".format(e))
        print("delta kappa  P_nodep P_dep  true_d | est. delta (attenuation) per null: "
              + "  ".join(NULLS) + " | sd obs (primary) | RMSE(P_hat - P_nodep) per null")
        for d, k in grid:
            if True:
                rs = cells[(d, k)]
                pool_ = lambda key: [sum(r[key][e][j] for r in rs) for j in range(4)]
                p_nodep, p_dep = rate(pool_("nodep")), rate(pool_("dep"))
                true_d = p_dep - p_nodep
                parts = []
                for n in NULLS:
                    est = p_dep - rate(pool_(n))
                    att = est / true_d if abs(true_d) > 0.01 else float("nan")
                    parts.append("{:+.3f} ({})".format(
                        est, "  -  " if att != att else "{:.2f}".format(att)))
                obs_d = [rate(r["observed"][e]) - rate(r["primary"][e]) for r in rs]
                obs_d = [x for x in obs_d if x == x]
                m = sum(obs_d) / len(obs_d) if obs_d else float("nan")
                sd = math.sqrt(sum((x - m) ** 2 for x in obs_d) / max(len(obs_d) - 1, 1)) if obs_d else float("nan")
                # The R2 criterion, per null: recovery of the NO-dependency rate.
                # Only meaningful for a null meant to estimate P_nodep (cueon).
                rmse = []
                for n in NULLS:
                    diffs = [rate(r[n][e]) - rate(r["nodep"][e]) for r in rs]
                    diffs = [x for x in diffs if x == x]
                    rmse.append("{:.3f}".format(math.sqrt(sum(x * x for x in diffs) / len(diffs)))
                                if diffs else "nan")
                print("{:<5} {:<5}  {:.3f}   {:.3f}  {:+.3f} | {} | {:.3f} | {}".format(
                    d, k, p_nodep, p_dep, true_d, "  ".join(parts), sd, " ".join(rmse)))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
