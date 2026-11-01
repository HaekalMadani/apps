"""Does the RQ2 model-check rule keep delta when the null is fine and drop it when not?

Written 2026-10-30 for ARS review roadmap R3/R4
(`novelty_audit/review/round1/synthesis.md`). The rule is the one in
`novelty_audit/review/CONCEPT_BRIEF_v9.md` section 5.

The PRIMARY NULL is fitted on FULL-salience laps only (author decision
2026-10-30, after `nullabsorption.py` showed that reduced salience, a partial
withdrawal, leaks dependency into a full + reduced fit). It is a per-driver
exponential trend with per-driver Gaussian sigma. Three checks on those laps,
none of which the fit targets:

  S1  5-fold-by-lap 80% predictive coverage;
  S2  the criterion pass rate on the pass after a 2-of-3 qualifying run at a
      corner (the regression to the mean the null exists to model);
  S3  lag-1 autocorrelation of the trend residuals.

A check fails at |z| > 2.39 against M studies simulated from the fitted null
(95% Bonferroni over three; the real analysis should use M >= 1000 and the
empirical 98.3% interval).

THE RULE, revised 2026-10-30 after the first power run (README, `nullcheck.py`)
showed the plain "fail -> descriptive" rule rejecting harmless misspecifications
and missing half of the harmful one:

  1. ESCALATE, don't abandon. S3 failing -> refit the noise as AR(1); S1 failing
     -> refit it as Student-t; both -> AR(1) with t innovations. rho and nu are
     pooled over the study's participants and bias-corrected against the plain
     null's simulated statistic. Re-run all three checks against the escalated
     null. S2 has no escalation: if S2 fails, delta is descriptive.
  2. TREND BRACKET. Fit a power-law trend as well and compute P_null under both
     forms (same noise, common random numbers). If they differ by more than
     0.045 (R2's criterion), the trend form matters and delta is descriptive.
  3. Delta is reported as a dependency ESTIMATE only if the checks pass (after
     at most one escalation) AND the bracket agrees.

  RESULT (2026-10-30, README): the escalation works, and the BRACKET DOES NOT.
  The bracket rejected 69% of correct nulls and agreed more often under the
  wrong truth, so the ADOPTED rule is steps 1 and 3 without the bracket. The
  power-law P_null is reported as a sensitivity analysis only. The bracket is
  still computed here so that the rejection can be reproduced.

Truths (no dependency, so this tests the rule, not delta): `correct` (the null's
own form), `ar1` (rho = 0.5), `heavy` (t3 noise), `power` (a power-law trend).
Reported per truth and element: the share of studies where delta would be an
estimate, the error of the P_null that would then be used, and the error of the
estimates that were kept.

Never writes `controller_config.json`; not a Gate run.

    python kit/tools/nullcheck.py [studies-per-truth] [M] [replicates] [seed] [workers]
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

TRUTHS = ("correct", "ar1", "heavy", "power")
FIT_STAGES = ("full",)
Z_CRIT = 2.39          # two-sided 1.7% = 0.05 / 3
FOLDS = 5
PI80 = 1.2816
BRACKET = 0.045        # R2's recovery criterion
POWER_GRID = [i * 0.04 for i in range(51)]   # exponent 0 .. 2.0
GAUSS = {"rho": 0.0, "nu": None}


# --- noise -------------------------------------------------------------------

def _t(rng, nu):
    chi = rng.gammavariate(nu / 2.0, 2.0)
    return rng.gauss(0.0, 1.0) / math.sqrt(chi / nu) * math.sqrt((nu - 2.0) / nu)


def noise_z(rng, spec, corner_ids, laps):
    """z[lap][corner][element], unit variance; spec[element] = {rho, nu}."""
    nc = len(corner_ids)
    z = []
    for lap in range(laps):
        row = []
        for c in range(nc):
            cell = []
            for ei, e in enumerate(ELEMENTS):
                s = spec[e]
                eps = _t(rng, s["nu"]) if s["nu"] else rng.gauss(0.0, 1.0)
                if s["rho"] and lap:
                    eps = s["rho"] * z[lap - 1][c][ei] + math.sqrt(1 - s["rho"] ** 2) * eps
                cell.append(eps)
            row.append(cell)
        z.append(row)
    return z


def truth_spec(kind):
    s = {"rho": 0.5 if kind == "ar1" else 0.0, "nu": 3.0 if kind == "heavy" else None}
    return dict((e, s) for e in ELEMENTS)


def _t3(rng):
    # nu = 3 has unit variance only in the limit; scale by 1/sqrt(3) as before.
    chi = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(3))
    return rng.gauss(0.0, 1.0) / math.sqrt(chi / 3.0) / math.sqrt(3.0)


def truth_z(rng, kind, corner_ids, laps):
    if kind == "heavy":
        return [[[_t3(rng) for _ in ELEMENTS] for _ in corner_ids] for _ in range(laps)]
    return noise_z(rng, truth_spec(kind), corner_ids, laps)


# --- the null ----------------------------------------------------------------

def fit_power_driver(obs):
    best = None
    for b in POWER_GRID:
        g = [(1.0 + l) ** -b for l in range(N.TOTAL_LAPS)]
        a = N._amps_mult(obs, g)
        sse = N._sse_mult(obs, g, a)
        if best is None or sse < best[0]:
            best = (sse, g, a)
    _, g, a = best
    return dict((c, [a[c] * g[l] for l in range(N.TOTAL_LAPS)]) for c in a), len(a) + 1


def fit(obs, form="exp"):
    mean, p = (N.fit_exp_driver if form == "exp" else fit_power_driver)(obs)
    sse = sum((y - mean[c][l]) ** 2 for l, c, y, _ in obs)
    return {"mean": mean, "sigma": math.sqrt(sse / max(len(obs) - p, 1))}


def fitted(obs_e):
    return [o for o in obs_e if o[3] in FIT_STAGES]


def statistics(obs_all, crit_all):
    """element -> (S1, S2, S3, kurtosis); the 4th only feeds the escalation."""
    out = {}
    for e in ELEMENTS:
        cover, post = [0, 0], [0, 0]
        num, den, m2, m4, nres = 0.0, 0.0, 0.0, 0.0, 0
        for obs, crit in zip(obs_all, crit_all):
            g = fitted(obs[e])
            if len(g) < 6:
                continue
            for k in range(FOLDS):
                train = [o for o in g if o[0] % FOLDS != k]
                test = [o for o in g if o[0] % FOLDS == k]
                if not test or len(train) < 6:
                    continue
                f = fit(train)
                for l, c, y, _ in test:
                    if c in f["mean"]:
                        cover[1] += 1
                        cover[0] += abs(y - f["mean"][c][l]) <= PI80 * f["sigma"]
            f = fit(g)
            res = dict(((c, l), y - f["mean"][c][l]) for l, c, y, _ in g)
            for (c, l), r in res.items():
                den += r * r
                if (c, l + 1) in res:
                    num += r * res[(c, l + 1)]
                if f["sigma"] > 0:
                    u = r / f["sigma"]
                    m2 += u * u
                    m4 += u ** 4
                    nres += 1
            trained = [o for o in obs[e] if o[3] != "unassisted"]
            seq = {}
            for o, v in zip(trained, crit[e]):
                if o[3] in FIT_STAGES and v is not None:
                    seq.setdefault(o[1], []).append(v)
            for vs in seq.values():
                for i in range(3, len(vs)):
                    if sum(vs[i - 3:i]) >= 2:
                        post[1] += 1
                        post[0] += vs[i]
        nan = float("nan")
        out[e] = (cover[0] / float(cover[1]) if cover[1] else nan,
                  post[0] / float(post[1]) if post[1] else nan,
                  num / den if den else nan,
                  (m4 / nres) / (m2 / nres) ** 2 - 3.0 if nres and m2 else nan)
    return out


def drive(ctx, params_list, zs):
    cfg, reference, applicable = ctx
    obs_all, crit_all = [], []
    for params, z in zip(params_list, zs):
        crit = dict((e, []) for e in ELEMENTS)
        _, obs = N.run_stream(cfg, reference, applicable, params, z, True, None, crit)
        obs_all.append(obs)
        crit_all.append(crit)
    return obs_all, crit_all


def simulate_stats(ctx, rng, nulls, spec, corner_ids, m):
    return [statistics(*drive(ctx, nulls, [noise_z(rng, spec, corner_ids, N.TOTAL_LAPS)
                                           for _ in nulls])) for _ in range(m)]


def judge(observed, sims, e):
    """[fail S1, fail S2, fail S3] (None = not computable), plus sim means."""
    fails, means = [], []
    for i in range(4):
        xs = [s[e][i] for s in sims if s[e][i] == s[e][i]]
        x = observed[e][i]
        mu = sum(xs) / len(xs) if xs else float("nan")
        means.append(mu)
        if i == 3:
            continue
        if len(xs) < 5 or x != x:
            fails.append(None)
            continue
        sd = math.sqrt(sum((v - mu) ** 2 for v in xs) / (len(xs) - 1))
        fails.append(abs(x - mu) > Z_CRIT * sd if sd > 0 else x != mu)
    return fails, means


def p_rate(ctx, params_list, zs):
    cfg, reference, applicable = ctx
    tot = dict((e, [0, 0, 0, 0]) for e in ELEMENTS)
    for params, zp in zip(params_list, zs):
        for z in zp:
            t, _ = N.run_stream(cfg, reference, applicable, params, z, False)
            for e in ELEMENTS:
                for k in range(4):
                    tot[e][k] += t[e][k]
    return dict((e, N.rate(tot[e])) for e in ELEMENTS)


def run_study(task):
    seed, kind, study, m, reps = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    ctx = (cfg, reference, applicable)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    rng = random.Random("{}|{}|{}".format(seed, kind, study))

    truths = [N.true_participant(rng, "power" if kind == "power" else "exp", 1.0, applicable)
              for _ in range(N.PARTICIPANTS)]
    obs_all, crit_all = drive(ctx, truths, [truth_z(rng, kind, corner_ids, N.TOTAL_LAPS)
                                            for _ in truths])
    exp_nulls = [dict((e, fit(fitted(o[e]))) for e in ELEMENTS) for o in obs_all]
    pow_nulls = [dict((e, fit(fitted(o[e]), "power")) for e in ELEMENTS) for o in obs_all]
    observed = statistics(obs_all, crit_all)

    gauss = dict((e, GAUSS) for e in ELEMENTS)
    sims0 = simulate_stats(ctx, rng, exp_nulls, gauss, corner_ids, m)

    # Step 1: one escalation per element, then re-check.
    spec, first, final, escalated = {}, {}, {}, {}
    for e in ELEMENTS:
        fails, means = judge(observed, sims0, e)
        first[e] = fails
        s1, s2, s3 = (bool(f) for f in fails)
        rho, nu = 0.0, None
        if s3:
            rho = min(max(observed[e][2] - means[2], 0.0), 0.9)
        if s1 and observed[e][3] == observed[e][3]:
            excess = observed[e][3] - means[3]
            nu = min(max(4.0 + 6.0 / excess, 4.2), 30.0) if excess > 0 else None
        spec[e] = {"rho": rho, "nu": nu}
        escalated[e] = (s1 or s3) and not s2
    if any(escalated.values()):
        sims1 = simulate_stats(ctx, rng, exp_nulls, spec, corner_ids, m)
    for e in ELEMENTS:
        if escalated[e]:
            final[e] = judge(observed, sims1, e)[0]
        else:
            final[e] = first[e]

    # Step 2: the trend bracket, on the noise the checks settled on. Truth and
    # both nulls share draws in the null's noise form; P_true uses the truth's.
    zs = [[noise_z(rng, spec, corner_ids, S.BLOCK_LAPS) for _ in range(reps)] for _ in truths]
    p_exp = p_rate(ctx, exp_nulls, zs)
    p_pow = p_rate(ctx, pow_nulls, zs)
    p_true = p_rate(ctx, truths, [[truth_z(rng, kind, corner_ids, S.BLOCK_LAPS)
                                   for _ in range(reps)] for _ in truths])

    out = {}
    for e in ELEMENTS:
        checks_ok = not any(f for f in final[e] if f)
        agree = abs(p_exp[e] - p_pow[e]) <= BRACKET if p_exp[e] == p_exp[e] and p_pow[e] == p_pow[e] else False
        out[e] = {"first_fail": any(f for f in first[e] if f), "escalated": escalated[e],
                  "checks_ok": checks_ok, "agree": agree, "estimate": checks_ok and agree,
                  "err": p_exp[e] - p_true[e]}
    return kind, out


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 100
    m = int(argv[2]) if len(argv) > 2 else 60
    reps = int(argv[3]) if len(argv) > 3 else 20
    seed = argv[4] if len(argv) > 4 else "nullcheck2"
    workers = int(argv[5]) if len(argv) > 5 else max(1, (os.cpu_count() or 2) - 1)
    print("studies/truth={} M={} replicates={} seed={} workers={}  fit stages={}".format(
        studies, m, reps, seed, workers, FIT_STAGES))
    tasks = [(seed, k, i, m, reps) for k in TRUTHS for i in range(studies)]
    res = dict((k, []) for k in TRUTHS)
    t0 = time.time()
    with multiprocessing.Pool(workers) as pool:
        for kind, v in pool.imap_unordered(run_study, tasks):
            res[kind].append(v)
    print("elapsed {:.0f} s".format(time.time() - t0))

    def rmse(xs):
        xs = [x for x in xs if x == x]
        return math.sqrt(sum(x * x for x in xs) / len(xs)) if xs else float("nan")

    print("\ntruth    element       1st-fail escal  checksOK bracketOK ESTIMATE |"
          " P_null RMSE all  kept  dropped")
    for k in TRUTHS:
        for e in ELEMENTS:
            vs = [v[e] for v in res[k]]
            n = float(len(vs))
            share = lambda key: sum(1 for x in vs if x[key]) / n
            print("{:<8} {:<13}  {:.2f}    {:.2f}   {:.2f}     {:.2f}      {:.2f}   |"
                  "   {:.3f}   {:.3f}  {:.3f}".format(
                      k, e, share("first_fail"), share("escalated"), share("checks_ok"),
                      share("agree"), share("estimate"), rmse([x["err"] for x in vs]),
                      rmse([x["err"] for x in vs if x["estimate"]]),
                      rmse([x["err"] for x in vs if not x["estimate"]])))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
