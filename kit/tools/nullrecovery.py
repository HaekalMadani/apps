"""Can the RQ2 null be identified from the cue-off data the study yields?

Written 2026-10-30 for roadmap item R2 of the ARS methodology review
(`novelty_audit/review/round1/synthesis.md`; methodology seat W1). The null of
framing v9 section 7.3 is a per-element noise model -- a driver intercept, a
practice trend and a lap-to-lap sigma -- fitted on CUE-OFF laps, which per
participant and element is the 4-lap unassisted block plus whatever probe laps
the controller happened to schedule. The review's question: is that little data,
bunched at the session end and at moments the selection rule picks, enough to
recover the trend and sigma well enough that P_null is a stable reference?

This is a PARAMETER-RECOVERY study. Synthetic participants are drawn from a
known generating model, driven through the REAL controller and evaluator for a
15-lap block plus the 4-lap unassisted block, and only what the study would see
is kept. Each candidate null form is fitted to it, the fitted null is driven
through the same controller under the same lap budget, and its probe-failure
rate P_hat is compared with the rate the TRUE parameters produce for the same
participants (P_true). Truth and every fitted null use common random numbers, so
the comparison is paired and the residual Monte Carlo noise is small.

"Known" means known to the simulation, not true of novices. The generating model
is swept rather than trusted: two trend forms (the committed exponential, and a
power law -- Newell & Rosenbloom 1981; Heathcote, Brown & Mewhort 2000 found
exponential fits individuals better, so both are plausible) and three noise
levels (0.5x, 1x, 2x the committed sigmas; braking 2 / 4 / 8 m). A form that
recovers P_null across that whole grid does not depend on the committed model
being right. The power-law cells are also the misspecification test: every
candidate trend below is exponential or linear.

The generating learner has NO guidance dependency. So this measures
identifiability only; whether dependency is absorbed into P_null (roadmap R5) is
a separate question, and the fit sets below are reported for both.

Candidate nulls (form x sigma pooling x fit set):
  exp_driver   per-driver exponential: per-corner amplitude, per-driver rate
  lin_driver   per-driver linear: per-corner intercept, per-driver slope
  exp_pooled   per-corner amplitudes per driver, ONE rate shared by the study's
               participants (complete pooling of the trend's shape -- the
               hierarchical option at its extreme)
  sigma        `driver` (each participant's own residual SD) or `pooled`
  fit set      `cueoff`     probe + removed-stage + unassisted laps (the brief)
               `unassisted` the 4-lap unassisted block only (an R5 option)
               `hybrid`     trend from ALL laps, sigma from cue-off residuals

"Cue-off" includes laps an element spent at `removed`, which the brief does not
list: they are equally withdrawn, so leaving them out would only discard data.

PRE-STATED PASS CRITERION (fixed before the first run): a null passes if, for
the braking element, RMSE(P_hat - P_true) <= 0.045 in EVERY cell of the grid.
0.045 is half the binomial SE of P_obs at the brief's ~16 braking probes and
P = 0.16 (sqrt(.16 x .84 / 16) = 0.092), so a passing null adds at most
sqrt(1.25) - 1 = 12% to the standard error of delta. Braking is the element the
pre-registered prediction rests on; apex and corner speed are reported.

It never writes `controller_config.json` and is not a Gate run.

    python kit/tools/nullrecovery.py [studies-per-cell] [replicates] [seed] [workers]
"""
import math
import multiprocessing
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import evaluator as ev
from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS, Controller

PARTICIPANTS = 15          # v9's n
UNASSISTED_LAPS = 4        # the unassisted block after the training block
TOTAL_LAPS = S.BLOCK_LAPS + UNASSISTED_LAPS
RMSE_BOUND = 0.045         # see the module docstring

SIGMA_KEY = {"braking": "brake_sigma_m", "corner_speed": "speed_sigma_kmh",
             "apex": "apex_sigma_m"}
OFFSET_KEY = {"braking": "brake_offset0_m", "corner_speed": "speed_offset0_kmh",
              "apex": "apex_offset0_m"}

TRUTH_FORMS = ("exp", "power")
SIGMA_SCALES = (0.5, 1.0, 2.0)
FORMS = ("exp_driver", "lin_driver", "exp_pooled")
POOLINGS = ("driver", "pooled")
FIT_SETS = ("cueoff", "unassisted", "hybrid")
COMBOS = [(f, p, s) for s in FIT_SETS for f in FORMS for p in POOLINGS]
RATE_GRID = [i * 0.02 for i in range(51)]   # 0 .. 1.0 per lap
CUE_OFF = ("probe", "removed", "unassisted")


# --- the generating model ----------------------------------------------------
#
# Error is expressed in each element's NOVICE direction, positive = worse:
# metres early for braking, km/h slow for corner speed, metres of excess RMS for
# apex -- the same directions `simulate.MODEL` uses.

def true_participant(rng, form, scale, applicable):
    """One participant's true mean table and sigmas, per element."""
    corners = sorted(set(c for ids in applicable.values() for c in ids))
    diff = dict((c, rng.uniform(S.MODEL["difficulty_min"], S.MODEL["difficulty_max"]))
                for c in corners)
    if form == "exp":
        rate = rng.uniform(0.0, 0.6)
        g = [math.exp(-rate * l) for l in range(TOTAL_LAPS)]
    else:
        b = rng.uniform(0.0, 1.5)
        g = [(1.0 + l) ** -b for l in range(TOTAL_LAPS)]
    # A driver-level noise trait, shared across elements: some people are
    # noisier than others, which is what makes pooled-vs-driver sigma (F6) a
    # real question.
    smult = math.exp(rng.uniform(-0.5, 0.5))
    params = {}
    for e in ELEMENTS:
        params[e] = {
            "mean": dict((c, [S.MODEL[OFFSET_KEY[e]] * diff[c] * g[l]
                              for l in range(TOTAL_LAPS)]) for c in applicable[e]),
            "sigma": S.MODEL[SIGMA_KEY[e]] * scale * smult,
        }
    return params


def draw_z(rng, corner_ids, laps):
    return [[[rng.gauss(0.0, 1.0) for _ in ELEMENTS] for _ in corner_ids]
            for _ in range(laps)]


def _metric(e, ref_corner, y):
    """Error -> the metric the evaluator reads, and the error the analyst sees back."""
    if e == "braking":
        return "brake_initiation_distance_m", y, y
    if e == "corner_speed":
        return "min_corner_speed_kmh", ref_corner["corner_speed"]["mean_kmh"] - y, y
    # RMS is a magnitude, folded at zero exactly as simulate_stream does, so the
    # analyst's view of a near-line pass is distorted the same way a real one is.
    ref = ref_corner["apex"]["mean_rms_m"]
    rms = abs(ref + y)
    return "apex_rms_m", rms, rms - ref


def run_stream(cfg, reference, applicable, params, z, record, dep=None, crit=None):
    """One block through the real controller; probe tallies and (optionally) data.

    ``dep`` = {element: (shift, kappa)} injects a guidance dependency for
    `nullabsorption.py`: on every pass driven with that element HIDDEN (probe,
    removed, unassisted) its mean error moves by ``shift`` in the novice
    direction and its noise is scaled by ``kappa``. None = no dependency. An
    optional third value ``r`` applies the fraction r of that effect on passes
    driven at REDUCED salience, which is a partial withdrawal (default 0).

    A 4th value ``k`` (0 = sustained) confines the hidden-pass effect to the
    first k laps of each withdrawal episode: the withdrawal-transient rival.

    ``crit`` = {element: []} is filled with each training-block pass's criterion,
    in the same order as that element's non-unassisted ``obs`` entries
    (`nullcheck.py` needs them for the post-qualification check).
    """
    by_id = ev.index_corners(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    ctrl = Controller(cfg, applicable)
    history = dict((c, []) for c in corner_ids)
    window = cfg["qualification"]["window_passes"]
    tally = dict((e, [0, 0, 0, 0]) for e in ELEMENTS)  # probes, reverted, removed, censored
    hidden_since = dict((e, None) for e in ELEMENTS)   # lap the current withdrawal began
    obs = dict((e, []) for e in ELEMENTS)

    def tally_events(events):
        for x in events:
            t = tally[x["element"]]
            kind = x["transition"]
            if kind == "reduced_to_probe":
                t[0] += 1
            elif kind == "probe_to_revert":
                t[1] += 1
            elif kind == "probe_to_removed":
                t[2] += 1
            elif kind == "censored":
                t[3] += 1

    for lap in range(TOTAL_LAPS if record else S.BLOCK_LAPS):
        unassisted = lap >= S.BLOCK_LAPS
        for ci, cid in enumerate(corner_ids):
            # The stage a pass was DRIVEN under is the one in force before the
            # controller sees it: the pass that triggers a probe was driven with
            # the cue visible, the one that ends it with the cue hidden.
            before = None if unassisted else ctrl.stages()
            metrics, seen = {}, {}
            for ei, e in enumerate(ELEMENTS):
                if cid not in params[e]["mean"]:
                    continue
                shift, kappa = 0.0, 1.0
                hidden = unassisted or before[e] in ("probe", "removed")
                if not hidden:
                    hidden_since[e] = None
                elif hidden_since[e] is None:
                    hidden_since[e] = lap
                if dep is not None and hidden:
                    shift, kappa = dep[e][0], dep[e][1]
                    # A 4th value k makes the effect TRANSIENT: it acts only on
                    # the first k laps of each withdrawal (`nulltransient.py`).
                    if len(dep[e]) > 3 and dep[e][3] and lap - hidden_since[e] >= dep[e][3]:
                        shift, kappa = 0.0, 1.0
                elif dep is not None and len(dep[e]) > 2 and before[e] == "reduced":
                    r = dep[e][2]
                    shift, kappa = r * dep[e][0], 1.0 + r * (dep[e][1] - 1.0)
                y = (params[e]["mean"][cid][lap] + shift
                     + params[e]["sigma"] * kappa * z[lap][ci][ei])
                key, value, seen[e] = _metric(e, by_id[cid], y)
                metrics[key] = value
            if record:
                for e in seen:
                    obs[e].append((lap, cid, seen[e], "unassisted" if unassisted else before[e]))
            if unassisted:
                continue
            result = ev.evaluate(cfg, by_id[cid], metrics, history[cid])
            if crit is not None:
                for e in seen:
                    crit[e].append(result["criteria"][e])
            if "brake_initiation_distance_m" in metrics:
                ev.push_history(history[cid], metrics["brake_initiation_distance_m"], window)
            tally_events(ctrl.step({"corner_id": cid, "lap": lap, "t": float(lap * 120 + 10),
                                    "criteria": result["criteria"]}))
    tally_events(ctrl.finish(S.BLOCK_LAPS, float(S.BLOCK_LAPS * 120)))
    return tally, obs


# --- the candidate nulls -----------------------------------------------------

def _select(obs, fit_set, role):
    """Which observations fit the trend (role 't') and the sigma (role 's')."""
    if fit_set == "unassisted":
        return [o for o in obs if o[3] == "unassisted"]
    if fit_set == "hybrid" and role == "t":
        return list(obs)
    return [o for o in obs if o[3] in CUE_OFF]


def _amps_mult(obs, g):
    num, den = {}, {}
    for l, c, y, _ in obs:
        num[c] = num.get(c, 0.0) + y * g[l]
        den[c] = den.get(c, 0.0) + g[l] * g[l]
    return dict((c, num[c] / den[c] if den[c] > 0 else 0.0) for c in num)


def _sse_mult(obs, g, a):
    return sum((y - a[c] * g[l]) ** 2 for l, c, y, _ in obs)


def _gexp(rate):
    return [math.exp(-rate * l) for l in range(TOTAL_LAPS)]


def fit_exp_driver(obs):
    best = None
    for r in RATE_GRID:
        g = _gexp(r)
        a = _amps_mult(obs, g)
        sse = _sse_mult(obs, g, a)
        if best is None or sse < best[0]:
            best = (sse, g, a)
    _, g, a = best
    return dict((c, [a[c] * g[l] for l in range(TOTAL_LAPS)]) for c in a), len(a) + 1


def fit_lin_driver(obs):
    by_c = {}
    for l, c, y, _ in obs:
        by_c.setdefault(c, []).append((l, y))
    means = dict((c, (sum(l for l, _ in v) / len(v), sum(y for _, y in v) / len(v)))
                 for c, v in by_c.items())
    sxy = sum((l - means[c][0]) * (y - means[c][1]) for c, v in by_c.items() for l, y in v)
    sxx = sum((l - means[c][0]) ** 2 for c, v in by_c.items() for l, _ in v)
    b = sxy / sxx if sxx > 0 else 0.0
    return dict((c, [means[c][1] + b * (l - means[c][0]) for l in range(TOTAL_LAPS)])
                for c in by_c), len(by_c) + 1


def fit_exp_pooled(obs_by_participant):
    best = None
    for r in RATE_GRID:
        g = _gexp(r)
        total = 0.0
        for obs in obs_by_participant:
            total += _sse_mult(obs, g, _amps_mult(obs, g))
        if best is None or total < best[0]:
            best = (total, g)
    g = best[1]
    out = []
    for obs in obs_by_participant:
        a = _amps_mult(obs, g)
        out.append((dict((c, [a[c] * g[l] for l in range(TOTAL_LAPS)]) for c in a), len(a)))
    return out


def fit_nulls(obs_all, true_params):
    """Every candidate null for every participant: combo -> [params per participant]."""
    out = {}
    for form, pooling, fit_set in COMBOS:
        per_e = {}
        for e in ELEMENTS:
            t_sets = [_select(o[e], fit_set, "t") for o in obs_all]
            s_sets = [_select(o[e], fit_set, "s") for o in obs_all]
            if form == "exp_pooled":
                fits = fit_exp_pooled(t_sets)
            elif form == "exp_driver":
                fits = [fit_exp_driver(t) for t in t_sets]
            else:
                fits = [fit_lin_driver(t) for t in t_sets]
            sses, dofs = [], []
            for (mean, p), t, s in zip(fits, t_sets, s_sets):
                sse = sum((y - mean[c][l]) ** 2 for l, c, y, _ in s)
                # Residual dof: the trend's parameters were spent on these
                # observations only when the sigma set IS the trend set.
                dof = (len(s) - p) if s is t or fit_set != "hybrid" else len(s)
                sses.append(sse)
                dofs.append(max(dof, 1))
            pooled = math.sqrt(sum(sses) / sum(dofs))
            per_e[e] = [{"mean": mean,
                         "sigma": pooled if pooling == "pooled" else math.sqrt(sse / dof)}
                        for (mean, _), sse, dof in zip(fits, sses, dofs)]
        out[(form, pooling, fit_set)] = [dict((e, per_e[e][i]) for e in ELEMENTS)
                                         for i in range(len(obs_all))]
    return out


# --- one synthetic study -----------------------------------------------------

def _diag(fitted, truth):
    """sigma_hat / sigma, and the trend's error over the GUIDED laps in sigma units."""
    ratio = fitted["sigma"] / truth["sigma"]
    sq = [(fitted["mean"][c][l] - truth["mean"][c][l]) ** 2
          for c in truth["mean"] for l in range(S.BLOCK_LAPS)]
    return ratio, math.sqrt(sum(sq) / len(sq)) / truth["sigma"]


def run_study(task):
    seed, form, scale, study, reps = task
    cfg = S.load_config()
    reference = S.load_references()[0]   # pair 1 only; pair 2 is descoped
    applicable = ev.applicable(reference)
    corner_ids = [c["corner_id"] for c in reference["corners"]]
    rng = random.Random("{}|{}|{}|{}".format(seed, form, scale, study))

    truths = [true_participant(rng, form, scale, applicable) for _ in range(PARTICIPANTS)]
    observed, obs_all = [], []
    for tp in truths:
        tally, obs = run_stream(cfg, reference, applicable, tp,
                                draw_z(rng, corner_ids, TOTAL_LAPS), True)
        observed.append(tally)
        obs_all.append(obs)
    nulls = fit_nulls(obs_all, truths)

    def null_tally(param_list, zs):
        tot = dict((e, [0, 0, 0, 0]) for e in ELEMENTS)
        for params, zp in zip(param_list, zs):
            for z in zp:
                t, _ = run_stream(cfg, reference, applicable, params, z, False)
                for e in ELEMENTS:
                    for k in range(4):
                        tot[e][k] += t[e][k]
        return tot

    # Common random numbers: truth and every fitted null see the same draws.
    zs = [[draw_z(rng, corner_ids, S.BLOCK_LAPS) for _ in range(reps)] for _ in truths]
    result = {"truth": null_tally(truths, zs), "combos": {}, "diag": {},
              "observed": dict((e, [sum(o[e][k] for o in observed) for k in range(4)])
                               for e in ELEMENTS),
              "cueoff_laps": dict((e, sum(len(set(l for l, _, _, s in o[e] if s in CUE_OFF))
                                          for o in obs_all) / float(PARTICIPANTS))
                                  for e in ELEMENTS)}
    for combo, plist in nulls.items():
        result["combos"][combo] = null_tally(plist, zs)
        result["diag"][combo] = dict(
            (e, [_diag(p[e], t[e]) for p, t in zip(plist, truths)]) for e in ELEMENTS)
    return (form, scale), result


# --- aggregation -------------------------------------------------------------

def rate(t):
    decided = t[1] + t[2]
    return t[1] / float(decided) if decided else float("nan")


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return float("nan") if not n else (xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2]))


def summarise(cell_results):
    """Per combo and element: bias, RMSE and undefined share of P_hat - P_true."""
    out = {}
    for combo in COMBOS:
        out[combo] = {}
        for e in ELEMENTS:
            diffs, undefined, ratios, trend = [], 0, [], []
            for r in cell_results:
                pt, ph = rate(r["truth"][e]), rate(r["combos"][combo][e])
                if pt != pt:
                    continue
                if ph != ph:
                    undefined += 1
                    continue
                diffs.append(ph - pt)
                for ratio, terr in r["diag"][combo][e]:
                    ratios.append(ratio)
                    trend.append(terr)
            n = len(diffs)
            out[combo][e] = {
                "bias": sum(diffs) / n if n else float("nan"),
                "rmse": math.sqrt(sum(d * d for d in diffs) / n) if n else float("nan"),
                "undefined": undefined,
                "sigma_ratio_med": median(ratios),
                "trend_err_med": median(trend),
            }
    return out


def main(argv):
    studies = int(argv[1]) if len(argv) > 1 else 100
    reps = int(argv[2]) if len(argv) > 2 else 30
    seed = argv[3] if len(argv) > 3 else "nullrecovery"
    workers = int(argv[4]) if len(argv) > 4 else max(1, (os.cpu_count() or 2) - 1)
    # Optional: a subset of noise scales, to re-run the binding cells at more
    # replicates and separate Monte Carlo noise from recovery error.
    scales = tuple(float(x) for x in argv[5].split(",")) if len(argv) > 5 else SIGMA_SCALES
    cfg = S.load_config()
    print("studies/cell={} participants={} replicates={} seed={} workers={}".format(
        studies, PARTICIPANTS, reps, seed, workers))
    print("block_laps={} unassisted={} window={}-of-{} probe_laps={}  pass: braking RMSE <= {}".format(
        S.BLOCK_LAPS, UNASSISTED_LAPS, cfg["qualification"]["required_passes"],
        cfg["qualification"]["window_passes"], cfg["probe"]["laps"], RMSE_BOUND))

    tasks = [(seed, f, s, i, reps) for f in TRUTH_FORMS for s in scales
             for i in range(studies)]
    t0 = time.time()
    cells = dict(((f, s), []) for f in TRUTH_FORMS for s in scales)
    with multiprocessing.Pool(workers) as pool:
        for key, res in pool.imap_unordered(run_study, tasks):
            cells[key].append(res)
    print("elapsed {:.0f} s".format(time.time() - t0))

    summaries = dict((k, summarise(v)) for k, v in cells.items())

    print("\nContext per cell: P_true pooled over studies; probes / participant (truth);"
          " distinct cue-off laps / participant (observed); SD of P_obs - P_true across studies")
    for (f, s), rs in sorted(cells.items()):
        line = []
        for e in ELEMENTS:
            tt = [sum(r["truth"][e][k] for r in rs) for k in range(4)]
            probes_pp = tt[0] / float(len(rs) * PARTICIPANTS * reps)
            d = [rate(r["observed"][e]) - rate(r["truth"][e]) for r in rs]
            d = [x for x in d if x == x]
            sd = math.sqrt(sum(x * x for x in d) / len(d)) if d else float("nan")
            cue = sum(r["cueoff_laps"][e] for r in rs) / len(rs)
            line.append("{} P={:.3f} pr={:.2f} off={:.1f} sdObs={:.3f}".format(
                e[:5], rate(tt), probes_pp, cue, sd))
        print("  {:<5} x{:<3} {}".format(f, s, " | ".join(line)))

    for e_focus in ELEMENTS:
        print("\n== {} ==  per cell: bias / RMSE / undefined studies;"
              " then median sigma_hat/sigma and trend error (sigma units) at exp x1".format(e_focus))
        print("form        sigma   fit set     cells: " +
              "  ".join("{}x{}".format(f, s) for f in TRUTH_FORMS for s in scales))
        for combo in COMBOS:
            parts, worst = [], 0.0
            for f in TRUTH_FORMS:
                for s in scales:
                    m = summaries[(f, s)][combo][e_focus]
                    parts.append("{:+.3f}/{:.3f}/{}".format(m["bias"], m["rmse"], m["undefined"]))
                    rm = m["rmse"] if m["rmse"] == m["rmse"] else float("inf")
                    if m["undefined"]:
                        rm = float("inf")
                    worst = max(worst, rm)
            m1 = summaries[("exp", 1.0 if 1.0 in scales else scales[0])][combo][e_focus]
            verdict = "PASS" if worst <= RMSE_BOUND else "fail"
            print("{:<11} {:<7} {:<11} {}  s/s={:.2f} trend={:.2f}  worst={:.3f} {}".format(
                combo[0], combo[1], combo[2], "  ".join(parts), m1["sigma_ratio_med"],
                m1["trend_err_med"], worst, verdict if e_focus == "braking" else ""))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main(sys.argv)
