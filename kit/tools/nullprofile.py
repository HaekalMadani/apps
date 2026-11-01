"""The time-profile READING RULE, fully specified, and how long a transient it survives.

Written 2026-11-01 for the round 2 re-review residual on R8
(`novelty_audit/review/round2/verification_report.md`). `nulltransient.py`
showed that the time profile separates a ONE-lap transient from a sustained
deficit. Round 2 found three gaps:
  1. no stated test, alpha, or reading when both statistics are significant;
  2. only a one-lap transient was simulated, so a transient of 2+ laps could be
     read as dependency (braking rarely fades, so unassisted lap 1 is a fresh
     withdrawal and the late level L_u = laps 2-4 includes lap 2);
  3. L_u is a block-level statistic, while delta is made of probes.

Statistics, all standardised residuals against the primary null
(`nullcheck.fit`, full-salience laps), one-sided t over participants at
alpha = 0.05 (t > 1.761), fixed for every n:
  T_p    first probe lap - second probe lap        (decay, probe level)
  L_u24  mean of unassisted laps 2-4               (late level, block; the brief's)
  L_u34  mean of unassisted laps 3-4               (late level, block, later)
  L_p    mean of the SECOND probe lap              (late level, probe level)

THE READING RULE (pre-specified here), per element, given a "late" statistic L:
  sustained   L significant (with or without T_p): an initial decay on top of
              a persisting deficit is still a persisting deficit
  decaying    T_p significant, L not
  neither     otherwise
"Sustained" licenses "immediate guidance dependency"; "decaying" licenses
"withdrawal transient or fast re-acquisition"; "neither" gives no construct.

Scenarios (band units, drivers vary x U(0, 2)): none; sustained 0.25 / 0.5;
transient lasting k = 1, 2, 3 laps of each withdrawal, at 0.5 (and k = 1 at
0.25). For braking a 2-lap probe sees all of a k >= 2 transient.

PRE-STATED ADOPTION RULE (fixed before the first run), braking: among L_u24,
L_u34 and L_p, adopt the one whose misreading of a k = 2 transient (delta 0.5)
as "sustained" is <= 0.10, with the highest "sustained" rate at sustained
0.25. If none meets 0.10, keep L_u24 and state the measured misreading rate as
the limitation. A k = 3 transient fills 3 of the 4 unassisted laps; no
statistic inside the block can be expected to separate it, and it is reported
as the design's horizon, not as a criterion.

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nullprofile.py [studies-per-scenario] [seed] [workers]
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
import nulltransient as T
from trace_kit import evaluator as ev
from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS

SCENARIOS = [("none", 0.0, 0), ("sustained", 0.25, 0), ("sustained", 0.5, 0),
             ("transient", 0.25, 1), ("transient", 0.5, 1),
             ("transient", 0.5, 2), ("transient", 0.5, 3)]
LATES = ("lu24", "lu34", "lp")
REPORTED = ("braking", "corner_speed")


def mean(xs):
    return sum(xs) / len(xs)


def run_study(task):
    seed, kind, delta, k, study = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    floors = cfg["band_floors"]
    rng = random.Random("{}|{}|{}|{}|{}".format(seed, kind, delta, k, study))

    per = dict((e, dict((s, []) for s in ("tp",) + LATES)) for e in ELEMENTS)
    for _ in range(N.PARTICIPANTS):
        truth = N.true_participant(rng, "exp", 1.0, applicable)
        h = rng.uniform(0.0, 2.0)
        dep = dict((e, (h * delta * floors[T.FLOOR_KEY[e]], 1.0, 0.0, k)) for e in ELEMENTS)
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
                l24 = [u(o) for o in obs[e] if o[0] > S.BLOCK_LAPS]
                l34 = [u(o) for o in obs[e] if o[0] > S.BLOCK_LAPS + 1]
                if l24:
                    per[e]["lu24"].append(mean(l24))
                if l34:
                    per[e]["lu34"].append(mean(l34))
            laps = sorted(set(o[0] for o in obs[e] if o[3] == "probe"))
            pos = {}
            for l in laps:
                pos[l] = pos[l - 1] + 1 if (l - 1) in pos else 0
            a = [u(o) for o in obs[e] if o[3] == "probe" and pos.get(o[0]) == 0]
            b = [u(o) for o in obs[e] if o[3] == "probe" and pos.get(o[0]) == 1]
            if a and b:
                per[e]["tp"].append(mean(a) - mean(b))
                per[e]["lp"].append(mean(b))
    out = {}
    for e in ELEMENTS:
        sig = dict((s, T.tstat(v) > T.T_CRIT) for s, v in per[e].items())
        n = dict((s, len(v)) for s, v in per[e].items())
        out[e] = {"sig": sig, "n": n}
    return (kind, delta, k), out


def reading(sig, late):
    if sig[late]:
        return "sustained"
    if sig["tp"]:
        return "decaying"
    return "neither"


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 1000
    seed = argv[2] if len(argv) > 2 else "nullprofile"
    workers = int(argv[3]) if len(argv) > 3 else max(1, (os.cpu_count() or 2) - 1)
    print("studies/scenario={} participants={} seed={} workers={}  one-sided t > {}".format(
        studies, N.PARTICIPANTS, seed, workers, T.T_CRIT))
    tasks = [(seed, kind, d, k, i) for kind, d, k in SCENARIOS for i in range(studies)]
    res = dict(((kind, d, k), []) for kind, d, k in SCENARIOS)
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for key, v in pool.imap_unordered(run_study, tasks, chunksize=8):
            res[key].append(v)
    print("elapsed {:.0f} s".format(time.time() - t0))

    for e in REPORTED:
        print("\n== {} ==   reading shares: sustained / decaying / neither   "
              "(n contributing: tp, lu24, lu34, lp)".format(e))
        print("scenario          " + "".join("{:<22}".format("late=" + l) for l in LATES))
        for kind, d, k in SCENARIOS:
            rs = [r[e] for r in res[(kind, d, k)]]
            m = float(len(rs))
            cells = []
            for late in LATES:
                c = dict((x, 0) for x in ("sustained", "decaying", "neither"))
                for r in rs:
                    c[reading(r["sig"], late)] += 1
                cells.append("{:.2f}/{:.2f}/{:.2f}      ".format(
                    c["sustained"] / m, c["decaying"] / m, c["neither"] / m))
            ns = " ".join("{:4.1f}".format(sum(r["n"][s] for r in rs) / m)
                          for s in ("tp", "lu24", "lu34", "lp"))
            print("{:<9} {:<4} k={} ".format(kind, d, k) + "".join(cells) + " " + ns)
        # The pre-stated adoption rule, braking only.
        if e == "braking":
            mis = {}
            det = {}
            for late in LATES:
                rs2 = [r[e] for r in res[("transient", 0.5, 2)]]
                rs_s = [r[e] for r in res[("sustained", 0.25, 0)]]
                mis[late] = sum(1 for r in rs2 if reading(r["sig"], late) == "sustained") / float(len(rs2))
                det[late] = sum(1 for r in rs_s if reading(r["sig"], late) == "sustained") / float(len(rs_s))
            ok = [l for l in LATES if mis[l] <= 0.10]
            pick = max(ok, key=lambda l: det[l]) if ok else "lu24 (none met 0.10)"
            print("  adoption: k=2 misread-as-sustained " +
                  ", ".join("{} {:.2f}".format(l, mis[l]) for l in LATES) +
                  " | sustained-0.25 detection " +
                  ", ".join("{} {:.2f}".format(l, det[l]) for l in LATES) +
                  " -> adopt {}".format(pick))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
