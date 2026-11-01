"""One interval procedure for delta, and its design sensitivity (roadmap R6, round 2).

Written 2026-11-01 for the round 2 re-review residual on R6
(`novelty_audit/review/round2/verification_report.md`). The round 1 fix
(`nulldecision.py`) bootstraps participants but treats each participant's fitted
null as KNOWN: the within-participant fit uncertainty in P_null is never
resampled. The brief called that interval "somewhat optimistic" and then
quoted its design sensitivity as the rule's. This script measures the
procedure the analysis will actually use and sets it beside the old one, on
the SAME simulated studies.

  plug_in   the round 1 interval: outer cluster bootstrap over participants,
            each participant's P_null from their single fitted null.
  nested    outer cluster bootstrap over participants; INNER, each sampled
            participant contributes one of M parametric-bootstrap refits of
            their own null, drawn at random. A refit = simulate that
            participant's full-salience observations (same laps, same corners)
            from the fitted trend and sigma, refit the per-driver exponential
            (`nullcheck.fit`), and drive the refit through the real controller
            for `refit_reps` replicate blocks. The point estimate still uses
            the original fit at `reps` replicates.

What `nested` does NOT carry: the fit window itself ends at the element's first
advance, a selection event, and the parametric refit keeps that window fixed.
That is the S6 extrapolation question, stated rather than resampled here.

Verdict rule, unchanged from R6: 90% interval, excess if lo > 0, no excess if
hi < MDI 0.10, indeterminate otherwise. Censored probes excluded (R7). The
dependency is the `nulldecision.py` one: sustained mean shift of delta x band
on every withdrawn pass, varying between drivers (x U(0, 2)).

PRE-STATED ADOPTION RULE (fixed before the first run): `nested` becomes the
pre-registered procedure unless its false "excess" rate at delta = 0 exceeds
0.05 + 2 Monte Carlo SE, in which case both are reported and the author
decides. The design-sensitivity table quoted in the brief is the adopted
procedure's, whatever it shows.

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nullinterval.py [studies-per-cell] [M] [refit-reps] [reps] [boot] [seed] [workers]
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

DELTAS = (0.0, 0.25, 0.375, 0.5)
REPORTED = ("braking", "corner_speed")   # apex has no verdict (brief section 6)
PROCS = ("plug_in", "nested")
MDI = 0.10


def refit(rng, fit_obs, null_e):
    """One parametric-bootstrap refit of a participant's null for one element."""
    sim = [(l, c, null_e["mean"][c][l] + null_e["sigma"] * rng.gauss(0.0, 1.0), s)
           for l, c, _, s in fit_obs]
    return C.fit(sim)


def run_study(task):
    seed, delta, study, m_refits, refit_reps, reps, boot = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    floors = cfg["band_floors"]
    rng = random.Random("{}|{}|{}".format(seed, delta, study))

    obs_t, null_t, refit_t, dep_t, nodep_t = [], [], [], [], []
    for _ in range(N.PARTICIPANTS):
        truth = N.true_participant(rng, "exp", 1.0, applicable)
        h = rng.uniform(0.0, 2.0)
        dep = dict((e, (h * delta * floors[D.FLOOR_KEY[e]], 1.0)) for e in ELEMENTS)
        tally, obs = N.run_stream(cfg, reference, applicable, truth,
                                  N.draw_z(rng, corner_ids, N.TOTAL_LAPS), True, dep)
        obs_t.append(tally)
        fit_obs = dict((e, C.fitted(obs[e])) for e in ELEMENTS)
        null = dict((e, C.fit(fit_obs[e])) for e in ELEMENTS)
        acc = [dict((e, [0, 0, 0, 0]) for e in ELEMENTS) for _ in range(3)]
        for _ in range(reps):
            z = N.draw_z(rng, corner_ids, S.BLOCK_LAPS)
            for slot, (params, d) in enumerate(((null, None), (truth, dep), (truth, None))):
                t, _ = N.run_stream(cfg, reference, applicable, params, z, False, d)
                for e in ELEMENTS:
                    acc[slot][e] = D.add(acc[slot][e], t[e])
        null_t.append(acc[0])
        dep_t.append(acc[1])
        nodep_t.append(acc[2])
        refits = []
        for _ in range(m_refits):
            params = dict((e, refit(rng, fit_obs[e], null[e])) for e in ELEMENTS)
            r_acc = dict((e, [0, 0, 0, 0]) for e in ELEMENTS)
            for _ in range(refit_reps):
                t, _ = N.run_stream(cfg, reference, applicable, params,
                                    N.draw_z(rng, corner_ids, S.BLOCK_LAPS), False)
                for e in ELEMENTS:
                    r_acc[e] = D.add(r_acc[e], t[e])
            refits.append(r_acc)
        refit_t.append(refits)

    def pooled(rows):
        tot = [0, 0, 0, 0]
        for r in rows:
            tot = D.add(tot, r)
        return tot

    out = {}
    idx = list(range(N.PARTICIPANTS))
    for e in REPORTED:
        po, pn = pooled([t[e] for t in obs_t]), pooled([t[e] for t in null_t])
        res = {"K": po[1] + po[2],
               "est": D.rate(po, "exclude") - D.rate(pn, "exclude"),
               "true": D.rate(pooled([t[e] for t in dep_t]), "exclude")
                       - D.rate(pooled([t[e] for t in nodep_t]), "exclude")}
        ds = dict((p, []) for p in PROCS)
        for _ in range(boot):
            pick = [rng.choice(idx) for _ in idx]
            a = D.rate(pooled([obs_t[i][e] for i in pick]), "exclude")
            b = D.rate(pooled([null_t[i][e] for i in pick]), "exclude")
            c = D.rate(pooled([rng.choice(refit_t[i])[e] for i in pick]), "exclude")
            if a == a and b == b:
                ds["plug_in"].append(a - b)
            if a == a and c == c:
                ds["nested"].append(a - c)
        for p in PROCS:
            v = sorted(ds[p])
            if len(v) >= boot // 2:
                res[p] = (v[int(0.05 * len(v))], v[int(0.95 * len(v)) - 1])
            else:
                res[p] = (float("nan"), float("nan"))
        out[e] = res
    return delta, out


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 200
    m_refits = int(argv[2]) if len(argv) > 2 else 20
    refit_reps = int(argv[3]) if len(argv) > 3 else 10
    reps = int(argv[4]) if len(argv) > 4 else 30
    boot = int(argv[5]) if len(argv) > 5 else 1000
    seed = argv[6] if len(argv) > 6 else "nullinterval"
    workers = int(argv[7]) if len(argv) > 7 else max(1, (os.cpu_count() or 2) - 1)
    print("studies/cell={} M={} refit_reps={} reps={} boot={} seed={} workers={}".format(
        studies, m_refits, refit_reps, reps, boot, seed, workers))
    tasks = [(seed, d, i, m_refits, refit_reps, reps, boot) for d in DELTAS for i in range(studies)]
    res = dict((d, []) for d in DELTAS)
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for d, v in pool.imap_unordered(run_study, tasks, chunksize=1):
            res[d].append(v)
    print("elapsed {:.0f} s".format(time.time() - t0))

    for e in REPORTED:
        print("\n== {} ==".format(e))
        print("  delta  true_d   K(med)  proc     med_width  P(excess)  P(no excess)  P(indet)  undefined")
        for d in DELTAS:
            rs = [r[e] for r in res[d]]
            n = float(len(rs))
            tr = [r["true"] for r in rs if r["true"] == r["true"]]
            for p in PROCS:
                ok = [r for r in rs if r[p][0] == r[p][0]]
                exc = sum(1 for r in ok if r[p][0] > 0) / n
                noexc = sum(1 for r in ok if r[p][1] < MDI) / n
                print("  {:<5}  {:+.3f}   {:5.1f}   {:<8} {:.3f}      {:.3f}      {:.3f}         {:.3f}     {:.3f}".format(
                    d, sum(tr) / len(tr) if tr else float("nan"),
                    D.median([r["K"] for r in rs]), p,
                    D.median([r[p][1] - r[p][0] for r in ok]), exc, noexc,
                    1 - exc - noexc - (n - len(ok)) / n, (n - len(ok)) / n))
        rs = [r[e] for r in res[0.0]]
        fx = sum(1 for r in rs if r["nested"][0] == r["nested"][0] and r["nested"][0] > 0) / float(len(rs))
        se = (0.05 * 0.95 / len(rs)) ** 0.5
        print("  adoption rule: nested false excess {:.3f} vs bound {:.3f} -> {}".format(
            fx, 0.05 + 2 * se, "ADOPT nested" if fx <= 0.05 + 2 * se else "author decides"))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
