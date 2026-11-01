"""Can the time profile of a withdrawal deficit tell a transient from dependency?

Written 2026-10-30 for ARS review roadmap R8 (`novelty_audit/review/round1/
synthesis.md`; methodology W8, domain W1, DA M3). The learning-plus-noise null
excludes BOTH guidance dependency and any transient effect of withdrawing a cue
(surprise, attention shift, the immediate dip), so a positive delta is consistent
with either. With no randomised arm the only internal contrast is TIME: a
transient should sit in the first lap after a withdrawal and fade, while a
deficit from dependency should persist.

Two candidate profiles, both read as standardised residuals (novice direction
positive) against the primary null (full-salience exponential fit,
`nullcheck.fit`):

  unassisted  T_u = mean residual on unassisted lap 1 minus laps 2-4, per
              participant, for elements still VISIBLE at the end of training
              (for an element already removed, the unassisted block is not a new
              withdrawal). Every participant drives it, and nothing about its
              length depends on how the learner did.
  probe       T_p = mean residual on the first probe lap minus the second. A
              probe REVERTS mid-way when the quorum collapses, so its second
              lap exists only for probes that were going well. If dependency
              differs between drivers, the drivers with the largest deficits
              lose their second lap, and a sustained deficit looks like a
              decaying one.

The late level L_u = mean residual on unassisted laps 2-4 is reported beside
T_u: dependency shows as L_u > 0; a pure transient leaves L_u ~ 0.

Scenarios: no dependency; a SUSTAINED mean shift on every withdrawn pass; a
TRANSIENT shift on the first lap of each withdrawal only. Shift sizes are in
band units and vary between drivers (x U(0, 2), mean 1), because a
heterogeneous effect is what exposes the probe profile's selection. The tests
are one-sided t-tests over participants at 5% (n = 15). Reported: the share of
studies in which each reading would be made.

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nulltransient.py [studies-per-scenario] [seed] [workers]
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

SCENARIOS = [("none", 0.0, 0), ("sustained", 0.25, 0), ("sustained", 0.5, 0),
             ("transient", 0.25, 1), ("transient", 0.5, 1)]
FLOOR_KEY = {"braking": "braking_m", "corner_speed": "corner_speed_kmh", "apex": "apex_m"}
T_CRIT = 1.761   # one-sided 5%, df = 14; used for every n as a fixed rule


def tstat(xs):
    n = len(xs)
    if n < 3:
        return float("nan")
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def run_study(task):
    seed, kind, delta, k, study = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    floors = cfg["band_floors"]
    rng = random.Random("{}|{}|{}|{}|{}".format(seed, kind, delta, k, study))

    per = dict((e, {"tu": [], "lu": [], "tp": []}) for e in ELEMENTS)
    for _ in range(N.PARTICIPANTS):
        truth = N.true_participant(rng, "exp", 1.0, applicable)
        h = rng.uniform(0.0, 2.0)
        dep = dict((e, (h * delta * floors[FLOOR_KEY[e]], 1.0, 0.0, k)) for e in ELEMENTS)
        _, obs = N.run_stream(cfg, reference, applicable, truth,
                              N.draw_z(rng, corner_ids, N.TOTAL_LAPS), True, dep)
        for e in ELEMENTS:
            g = C.fitted(obs[e])
            if len(g) < 6:
                continue
            f = C.fit(g)
            if f["sigma"] <= 0:
                continue
            u = lambda o: (o[2] - f["mean"][o[1]][o[0]]) / f["sigma"]
            last = [o for o in obs[e] if o[0] == S.BLOCK_LAPS - 1]
            if not any(o[3] == "removed" for o in last):
                first = [u(o) for o in obs[e] if o[0] == S.BLOCK_LAPS]
                late = [u(o) for o in obs[e] if o[0] > S.BLOCK_LAPS]
                if first and late:
                    per[e]["tu"].append(sum(first) / len(first) - sum(late) / len(late))
                    per[e]["lu"].append(sum(late) / len(late))
            # Probe episodes: runs of consecutive probe laps.
            laps = sorted(set(o[0] for o in obs[e] if o[3] == "probe"))
            pos = {}
            for l in laps:
                pos[l] = pos[l - 1] + 1 if (l - 1) in pos else 0
            a = [u(o) for o in obs[e] if o[3] == "probe" and pos.get(o[0]) == 0]
            b = [u(o) for o in obs[e] if o[3] == "probe" and pos.get(o[0]) == 1]
            if a and b:
                per[e]["tp"].append(sum(a) / len(a) - sum(b) / len(b))
    out = {}
    for e in ELEMENTS:
        out[e] = dict((key, (tstat(v), len(v))) for key, v in per[e].items())
    return (kind, delta, k), out


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 1000
    seed = argv[2] if len(argv) > 2 else "nulltransient"
    workers = int(argv[3]) if len(argv) > 3 else max(1, (os.cpu_count() or 2) - 1)
    print("studies/scenario={} participants={} seed={} workers={}  one-sided t > {}".format(
        studies, N.PARTICIPANTS, seed, workers, T_CRIT))
    tasks = [(seed, kind, d, k, i) for kind, d, k in SCENARIOS for i in range(studies)]
    res = dict(((kind, d, k), []) for kind, d, k in SCENARIOS)
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for key, v in pool.imap_unordered(run_study, tasks, chunksize=8):
            res[key].append(v)
    print("elapsed {:.0f} s".format(time.time() - t0))

    print("\nshare of studies with a significant positive statistic"
          " (n = participants contributing, mean)")
    print("scenario        delta element       T_u decay  L_u late   T_p probe-decay |  n_u  n_p")
    for kind, d, k in SCENARIOS:
        for e in ELEMENTS:
            rs = [r[e] for r in res[(kind, d, k)]]
            def share(key):
                ts = [r[key][0] for r in rs if r[key][0] == r[key][0]]
                return sum(1 for t in ts if t > T_CRIT) / float(len(rs))
            n_u = sum(r["tu"][1] for r in rs) / float(len(rs))
            n_p = sum(r["tp"][1] for r in rs) / float(len(rs))
            print("{:<15} {:<5} {:<13} {:.3f}      {:.3f}      {:.3f}         | {:4.1f} {:4.1f}".format(
                kind, d, e, share("tu"), share("lu"), share("tp"), n_u, n_p))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
