"""Does the PRIMARY null recover across noise and trend form, and where should the sigma gate sit?

Written 2026-11-01 for the round 2 re-review (`novelty_audit/review/round2/
verification_report.md`): R2's residual and NEW-2.
- R2: `nullrecovery.py` recovery-tested the CUE-OFF candidates across noise
  and trend form, but the primary null adopted under R5 (per-driver
  exponential, per-driver sigma, fitted on FULL-salience laps,
  `nullcheck.fit`) was only checked at 1x noise with an exponential truth.
  The brief's "the highest level at which the null recovered" was therefore
  never shown for it.
- NEW-2: the pilot gate "braking sigma > 4 m" had no laps, estimator or
  uncertainty rule, and its threshold equalled the committed value. With 2
  pilot drivers it would trip about half the time at a true 4 m.

What this measures, per trend form (exp, power) and noise scale s (brake and
speed sigma x s; apex stays measured), n = 15 per study, real controller,
common random numbers between truth and fit:
  - RMSE and bias of P_hat - P_true per element (R2's criterion: braking
    RMSE <= 0.045);
  - recovery of the PARAMETERS: sigma_hat / sigma, and the trend's error in
    sigma units on the guided laps and on the laps AFTER the fit window
    (probe, removed, unassisted), which is the extrapolation S6 asks about;
  - the GATE STATISTIC: the study's pooled full-salience residual SD,
    sigma_study = sqrt(mean over participants of sigma_hat^2), per element.

THE GATE, re-specified. It is applied at ANALYSIS to the main sample's own
sigma_study (full-salience laps only, so it reads no probe outcome and is
untouched by a withdrawal effect), not to the 2-driver pilot. The pilot's
sigma_study becomes a FORECAST of eligibility for G2.

PRE-STATED GATE CRITERION (fixed before the first run). Pool every simulated
study across forms and scales and bin it by its braking sigma_study (bins of
0.5 m). The cut sigma_max is the upper edge of the highest bin such that every
bin from the lowest up to and including it has RMSE(P_hat - P_true) <= 0.045
with at least 30 studies. Braking delta is a dependency estimate only if the
main sample's sigma_study <= sigma_max. The same rule is computed for corner
speed (0.25 km/h bins); it is reported and adopted only if some bin fails.

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nullprimary.py [studies-per-cell] [replicates] [seed] [workers]
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

FORMS = ("exp", "power")
SCALES = (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
SCALED = ("braking", "corner_speed")
REPORTED = ("braking", "corner_speed")
BIN_W = {"braking": 0.5, "corner_speed": 0.25}
RMSE_BOUND = N.RMSE_BOUND


def participant(rng, form, scale, applicable):
    p = N.true_participant(rng, form, 1.0, applicable)
    for e in SCALED:
        p[e]["sigma"] *= scale
    return p


def diag(fitted, truth, fit_obs, all_obs):
    """sigma ratio; trend error (sigma units) on fit laps and on laps after the fit window."""
    fit_laps = set(l for l, _, _, _ in fit_obs)
    after = sorted(set(l for l, _, _, s in all_obs if s != "full" and l > max(fit_laps)))

    def err(laps):
        sq = [(fitted["mean"][c][l] - truth["mean"][c][l]) ** 2
              for c in truth["mean"] for l in laps]
        return math.sqrt(sum(sq) / len(sq)) / truth["sigma"] if sq else float("nan")

    return fitted["sigma"] / truth["sigma"], err(sorted(fit_laps)), err(after), len(after)


def run_study(task):
    seed, form, scale, study, reps = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    rng = random.Random("{}|{}|{}|{}".format(seed, form, scale, study))

    truths, nulls, dg = [], [], dict((e, []) for e in ELEMENTS)
    for _ in range(N.PARTICIPANTS):
        tp = participant(rng, form, scale, applicable)
        _, obs = N.run_stream(cfg, reference, applicable, tp,
                              N.draw_z(rng, corner_ids, N.TOTAL_LAPS), True)
        fit_obs = dict((e, C.fitted(obs[e])) for e in ELEMENTS)
        null = dict((e, C.fit(fit_obs[e])) for e in ELEMENTS)
        for e in ELEMENTS:
            dg[e].append(diag(null[e], tp[e], fit_obs[e], obs[e]))
        truths.append(tp)
        nulls.append(null)

    tot = dict((k, dict((e, [0, 0, 0, 0]) for e in ELEMENTS)) for k in ("truth", "null"))
    for tp, nl in zip(truths, nulls):
        for _ in range(reps):
            z = N.draw_z(rng, corner_ids, S.BLOCK_LAPS)   # common random numbers
            for key, params in (("truth", tp), ("null", nl)):
                t, _ = N.run_stream(cfg, reference, applicable, params, z, False)
                for e in ELEMENTS:
                    tot[key][e] = [a + b for a, b in zip(tot[key][e], t[e])]
    out = {}
    for e in ELEMENTS:
        out[e] = {"p_true": N.rate(tot["truth"][e]), "p_hat": N.rate(tot["null"][e]),
                  "sigma_study": math.sqrt(sum(nl[e]["sigma"] ** 2 for nl in nulls) / len(nulls)),
                  "diag": dg[e]}
    return (form, scale), out


def rmse(rows):
    d = [r["p_hat"] - r["p_true"] for r in rows if r["p_hat"] == r["p_hat"] and r["p_true"] == r["p_true"]]
    return (math.sqrt(sum(x * x for x in d) / len(d)) if d else float("nan"),
            sum(d) / len(d) if d else float("nan"), len(d))


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 100
    reps = int(argv[2]) if len(argv) > 2 else 30
    seed = argv[3] if len(argv) > 3 else "nullprimary"
    workers = int(argv[4]) if len(argv) > 4 else max(1, (os.cpu_count() or 2) - 1)
    print("studies/cell={} n={} replicates={} seed={} workers={}".format(
        studies, N.PARTICIPANTS, reps, seed, workers))
    tasks = [(seed, f, s, i, reps) for f in FORMS for s in SCALES for i in range(studies)]
    res = {}
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for key, v in pool.imap_unordered(run_study, tasks, chunksize=2):
            res.setdefault(key, []).append(v)
    print("elapsed {:.0f} s".format(time.time() - t0))

    for e in REPORTED:
        print("\n== {} ==".format(e))
        print("  form   s     sigma  RMSE   bias    pass  sigma_ratio(med)  trend_err_fit  trend_err_after  laps_after  sigma_study(med)")
        for f in FORMS:
            for s in SCALES:
                rows = [r[e] for r in res[(f, s)]]
                m, b, _ = rmse(rows)
                dg = [d for r in rows for d in r["diag"]]
                sig = S.MODEL[N.SIGMA_KEY[e]] * s
                print("  {:<6} {:<5} {:5.2f}  {:.3f}  {:+.3f}  {:<5} {:.3f}             {:.2f}           {:.2f}             {:4.1f}        {:.2f}".format(
                    f, s, sig, m, b, "yes" if m <= RMSE_BOUND else "NO",
                    N.median([d[0] for d in dg]), N.median([d[1] for d in dg]),
                    N.median([d[2] for d in dg if d[2] == d[2]]),
                    sum(d[3] for d in dg) / float(len(dg)),
                    N.median([r["sigma_study"] for r in rows])))
        # The gate: bin every study by its own sigma_study.
        allrows = [r[e] for v in res.values() for r in v]
        w = BIN_W[e]
        lo_bin = int(min(r["sigma_study"] for r in allrows) / w)
        hi_bin = int(max(r["sigma_study"] for r in allrows) / w)
        print("  gate bins by sigma_study:")
        sigma_max, broken = None, False
        for k in range(lo_bin, hi_bin + 1):
            br = [r for r in allrows if k * w <= r["sigma_study"] < (k + 1) * w]
            m, b, n = rmse(br)
            ok = n >= 30 and m <= RMSE_BOUND
            print("    [{:.2f}, {:.2f})  n={:4d}  RMSE {:.3f}  bias {:+.3f}  {}".format(
                k * w, (k + 1) * w, n, m, b, "pass" if ok else ("thin" if n < 30 else "FAIL")))
            if n < 30:
                continue
            if ok and not broken:
                sigma_max = (k + 1) * w
            elif not ok:
                broken = True
        print("  sigma_max (pre-stated criterion) = {}".format(sigma_max))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
