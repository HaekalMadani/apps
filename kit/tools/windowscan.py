"""Which ELEMENT traverses the machine, and does a longer evidence window make
the apex element decidable?

Written 2026-10-14 to answer the tolerance-calibration review
(`TRACE_tolerance-calibration_lit-review_v1.0.md`), whose central methodological
claim is that a per-pass pass/fail vote over a 4-pass window throws away
information that a longer window keeps -- so the apex element's problem may be
the WINDOW rather than the band. The committed Phase 1 report cannot answer
either question: it aggregates `elements_removed` as a count, so it never says
WHICH element moved, and `configs/simulation/sweep_report.json` sweeps the four
band parameters only, because `simulate.SWEEP_GRID`'s own comment rules the
qualification window out as structural rather than calibratable.

Three tables, each a different question:

  elements      per element, the share of streams that left `full` and the share
                that reached `removed`, under the COMMITTED novice model and
                under one with the apex parameters replaced by the measured ones
                (apexscan.py: mean excess 2.49 m, lap-to-lap SD 1.86 m against
                the committed assumption of 1.2 m / 0.30 m). This is the
                breakdown behind Gate G1's first target.
  windows       the apex floor crossed with the qualification window, scored on
                the two targets that bound the design from both sides: a typical
                improver must advance, a non-improver must not.
  consistency   the braking element against `criteria.consistency_delta_ratio`,
                because the first table shows braking never traverses at all and
                the consistency gate is the suspect.

It never writes `controller_config.json` -- same rule as rescore.py and
apexscan.py: every override is in memory, because an edit there re-pins the
frozen hash and re-opens Gate G1. It is NOT a Gate G1 run and its numbers are
not a verdict: `trace_kit.simulate run` against the committed config is, and
this script deliberately runs configurations that config does not hold.

    python kit/tools/windowscan.py [streams-per-type-per-pair] [seed]

Run it as `200 trace-g1` to reproduce the tables in README.md. That seed and
stream count are the committed report's own, which is the point: the committed
novice model then reproduces `simulation_report.json`'s `mean_elements_removed`
for every learner type exactly, so the per-element split beside it is the same
streams rather than a different sample. The default seed is this script's own and
is only for poking at the grid.

Reproduced figures are tabulated in README.md.
"""
import copy
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS

# The measured apex novice. Both figures are apexscan.py's, over 227 real pair-1
# passes against the committed 85% reference; the committed model's 1.2 m / 0.30 m
# are assumptions, and the sigma is wrong by about six times.
MEASURED_APEX = {"apex_offset0_m": 2.49, "apex_sigma_m": 1.86}

# window_passes -> required_passes. The pairs worth asking about: the frozen
# 3-of-4, then the lengths the review's minimal-detectable-change argument
# points at (n >= 6), at two strictnesses each.
WINDOWS = [(4, 3), (6, 4), (6, 5), (8, 6), (8, 7), (10, 8)]
APEX_FLOORS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
RATIOS = [0.5, 1.0, 2.0, 10.0]

# The learner types each table is read on. `non_improver` is the bar that binds
# from above in every one of them: the design's conservatism says the learner who
# never improves must never lose a cue.
TYPES = ["typical_improver", "non_improver", "erratic", "staggered_regressor"]


def learner(name):
    return next(l for l in S.LEARNER_TYPES if l.name == name)


def shares(cfg, references, name, streams, seed):
    """Per-element share of streams that left `full`, and that reached `removed`.

    Disabled elements are skipped rather than counted as never-faded, for the
    same reason RQ1 excludes them: a zero denominator is not a failure to fade.
    """
    left_full = dict((e, 0) for e in ELEMENTS)
    removed = dict((e, 0) for e in ELEMENTS)
    seen = dict((e, 0) for e in ELEMENTS)
    per_stream_removed = []
    for pair_index, reference in enumerate(references):
        rng = random.Random("{}|{}|{}".format(seed, name, pair_index))
        for _ in range(streams):
            stream = S.simulate_stream(cfg, reference, learner(name), rng)
            count = 0
            for element in ELEMENTS:
                if element in stream["disabled"]:
                    continue
                seen[element] += 1
                if stream["final_stages"][element] != "full":
                    left_full[element] += 1
                if stream["final_stages"][element] == "removed":
                    removed[element] += 1
                    count += 1
            per_stream_removed.append(count)
    pct = lambda d, e: (100.0 * d[e] / seen[e]) if seen[e] else 0.0
    return {
        "left_full": dict((e, pct(left_full, e)) for e in ELEMENTS),
        "removed": dict((e, pct(removed, e)) for e in ELEMENTS),
        "mean_removed": statistics.fmean(per_stream_removed) if per_stream_removed else 0.0,
        "streams": len(per_stream_removed),
    }


def with_model(apex):
    """Set the apex model parameters, returning the previous values."""
    before = dict((k, S.MODEL[k]) for k in apex)
    for k, v in apex.items():
        S.MODEL[k] = v
    return before



def traversal_floor(cfg, required):
    """The earliest lap a full traversal can COMPLETE, in laps of evidence.

    Derived from the code, not from the prose, because the prose got it wrong
    once: `Controller._quorum_ready` is keyed on `required_passes`, NOT on
    `window_passes` (a partly-filled window counts -- 4 of 4 satisfies "4 of the
    last 6"), so a stage costs `required_passes` laps and not a whole window.
    And the readiness check gates EVERY transition including `probe_to_removed`,
    so a probe cannot complete on `probe.laps` alone: after the advance into it
    resets the evidence, it also needs `required_passes` of fresh passes. Hence

        2 x required_passes + max(probe.laps, required_passes)

    two advances plus a probe that is the longer of its lap count and its
    evidence requirement. It is a LOWER BOUND and a loose one: it assumes every
    applicable corner qualifies on its first `required_passes` passes at every
    stage, which a learner on a learning curve does not do -- the committed
    3-of-4 config has an arithmetic floor of 9 laps and its earliest observed
    corner-speed removal is lap 11.
    """
    return 2 * required + max(cfg["probe"]["laps"], required)


def print_floor(cfg):
    laps = S.BLOCK_LAPS
    print("  Traversal arithmetic (see traversal_floor): a full traversal needs")
    print("  2 x required_passes + max(probe.laps, required_passes) laps, because")
    print("  readiness is keyed on required_passes and it gates the probe's own")
    print("  completion too. Lower bound -- a real learner needs more:")
    for window, required in WINDOWS:
        need = traversal_floor(cfg, required)
        print("    {}-of-{}: needs {:2d} laps, block has {:2d}  {}".format(
            required, window, need, laps,
            "AT THE LIMIT" if need == laps else ("OK" if need < laps else "IMPOSSIBLE")))
    print("")


def table_elements(cfg, references, streams, seed):
    print("## elements -- which one actually traverses, committed config\n")
    print("The committed report gives `mean_elements_removed` only. This is the")
    print("same number split by element, which is what says whether Gate G1's")
    print("'2 of 3 elements' rests on the element whose model is known wrong.\n")
    for label, apex in (("committed model", {"apex_offset0_m": 1.2, "apex_sigma_m": 0.30}),
                        ("MEASURED apex", MEASURED_APEX)):
        before = with_model(apex)
        print("{} (apex offset {:.2f} m, sigma {:.2f} m)".format(
            label, S.MODEL["apex_offset0_m"], S.MODEL["apex_sigma_m"]))
        print("  {:<21s} {:>6s}   {:>22s}   {:>22s}".format(
            "learner", "mean", "left full  b / s / a", "removed  b / s / a"))
        for name in TYPES:
            r = shares(cfg, references, name, streams, seed)
            print("  {:<21s} {:6.3f}   {:>22s}   {:>22s}".format(
                name, r["mean_removed"],
                "{:3.0f}% /{:3.0f}% /{:3.0f}%".format(*[r["left_full"][e] for e in ELEMENTS]),
                "{:3.0f}% /{:3.0f}% /{:3.0f}%".format(*[r["removed"][e] for e in ELEMENTS])))
        with_model(before)
        print("")


def table_windows(cfg, references, streams, seed):
    print("## windows -- apex floor x qualification window, measured apex novice\n")
    print("Read on the two targets that bound the design from both sides: a")
    print("typical improver must advance, a non-improver must not. 'advanced'")
    print("is left-full rather than removed, because at these window lengths")
    print("nothing reaches `removed` inside a block -- see the arithmetic below.\n")
    before = with_model(MEASURED_APEX)
    print("  {:<9s} {:>7s}   {:>24s}   {:>24s}".format(
        "window", "apex_m", "advanced: typical improver", "advanced: non-improver"))
    print("  {:<9s} {:>7s}   {:>8s}{:>8s}{:>8s}   {:>8s}{:>8s}{:>8s}".format(
        "k-of-n", "", "brake", "speed", "apex", "brake", "speed", "apex"))
    for window, required in WINDOWS:
        for floor in APEX_FLOORS:
            candidate = copy.deepcopy(cfg)
            candidate["qualification"]["window_passes"] = window
            candidate["qualification"]["required_passes"] = required
            candidate["band_floors"]["apex_m"] = floor
            t = shares(candidate, references, "typical_improver", streams, seed)
            n = shares(candidate, references, "non_improver", streams, seed)
            print("  {:<9s} {:7.1f}   {:>24s}   {:>24s}".format(
                "{}-of-{}".format(required, window), floor,
                "{:7.0f}%{:7.0f}%{:7.0f}%".format(*[t["left_full"][e] for e in ELEMENTS]),
                "{:7.0f}%{:7.0f}%{:7.0f}%".format(*[n["left_full"][e] for e in ELEMENTS])))
        print("")
    with_model(before)
    print_floor(cfg)


def table_consistency(cfg, references, streams, seed):
    print("## consistency -- the braking element against the consistency gate\n")
    print("The first table shows braking never reaching `removed`. This varies")
    print("`criteria.consistency_delta_ratio` alone, committed apex model, to")
    print("separate 'the consistency gate holds braking at full' from 'the")
    print("accuracy band cannot be held at this brake sigma either'.")
    print("  sigma/band: braking {:.2f}, corner speed {:.2f}\n".format(
        S.MODEL["brake_sigma_m"] / cfg["band_floors"]["braking_m"],
        S.MODEL["speed_sigma_kmh"] / cfg["band_floors"]["corner_speed_kmh"]))
    print("  {:>6s}   {:<21s} {:>10s} {:>9s}".format(
        "ratio", "learner", "left full", "removed"))
    for ratio in RATIOS:
        candidate = copy.deepcopy(cfg)
        candidate["criteria"]["consistency_delta_ratio"] = ratio
        for name in ("typical_improver", "non_improver"):
            r = shares(candidate, references, name, streams, seed)
            print("  {:6.1f}   {:<21s} {:9.0f}% {:8.0f}%".format(
                ratio, name, r["left_full"]["braking"], r["removed"]["braking"]))
    print("")



# The candidate configurations table 4 walks the ladder for. Table 2 answers
# "does the element advance at all"; this one answers "can it finish", which is
# a different question once the window is long enough to eat the lap budget.
STAGE_CASES = [(4, 3, 0.5), (4, 3, 1.5), (4, 3, 2.0),
               (6, 4, 1.5), (6, 4, 2.0), (6, 4, 2.5), (6, 5, 1.5)]


def ladder(cfg, references, element, name, streams, seed):
    """Final-stage shares for one element, plus probe entries and removals."""
    final = {}
    entered_probe = removed = censored = n = 0
    for pair_index, reference in enumerate(references):
        rng = random.Random("{}|{}|{}".format(seed, name, pair_index))
        for _ in range(streams):
            stream = S.simulate_stream(cfg, reference, learner(name), rng)
            if element in stream["disabled"]:
                continue
            stage = stream["final_stages"][element]
            final[stage] = final.get(stage, 0) + 1
            for e in stream["events"]:
                if e["element"] != element:
                    continue
                if e["transition"] == "reduced_to_probe":
                    entered_probe += 1
                elif e["transition"] == "probe_to_removed":
                    removed += 1
                elif e["transition"] == "censored":
                    censored += 1
            n += 1
    pct = lambda v: 100.0 * v / n if n else 0.0
    return {"full": pct(final.get("full", 0)), "reduced": pct(final.get("reduced", 0)),
            "probe": pct(final.get("probe", 0)), "removed": pct(final.get("removed", 0)),
            "entered_probe": pct(entered_probe), "removals": pct(removed),
            "censored": pct(censored)}


def table_stages(cfg, references, streams, seed):
    print("## stages -- how far up the ladder it gets, not just whether it moves\n")
    print("A longer window buys discriminability and spends lap budget. Table 2")
    print("reads `left full`, which is one advance; this reads the whole ladder.")
    print("The last two rows are the COST: what a global window change does to")
    print("corner speed, the one element that traverses at the frozen window.\n")
    print("  {:<8s} {:>6s} {:<13s} {:>6s} {:>8s} {:>6s} {:>8s} {:>9s}".format(
        "window", "apex_m", "element", "full", "reduced", "probe", "removed", "censored"))
    before = with_model(MEASURED_APEX)
    rows = [(w, r, f, "apex") for (w, r, f) in STAGE_CASES]
    rows += [(4, 3, 0.5, "corner_speed"), (6, 4, 0.5, "corner_speed")]
    for window, required, floor, element in rows:
        candidate = copy.deepcopy(cfg)
        candidate["qualification"]["window_passes"] = window
        candidate["qualification"]["required_passes"] = required
        candidate["band_floors"]["apex_m"] = floor
        s = ladder(candidate, references, element, "typical_improver", streams, seed)
        print("  {:<8s} {:6.1f} {:<13s} {:5.0f}% {:7.0f}% {:5.0f}% {:7.0f}% {:8.0f}%".format(
            "{}-of-{}".format(required, window), floor, element,
            s["full"], s["reduced"], s["probe"], s["removed"], s["censored"]))
    with_model(before)
    print("")
    print("  Final stage of a TYPICAL IMPROVER's block. `probe` means the block")
    print("  ended mid-probe (right-censored, which RQ1 already reports as its")
    print("  own outcome); `removed` means the traversal completed.")
    print("")


def main(argv):
    streams = int(argv[1]) if len(argv) > 1 else 200
    seed = argv[2] if len(argv) > 2 else "windowscan"
    cfg = S.load_config()
    references = S.load_references()
    print("windowscan -- config_id {}, {} streams/type/pair, {} laps/block, seed {}\n".format(
        cfg["config_id"], streams, S.BLOCK_LAPS, seed))
    table_elements(cfg, references, streams, seed)
    table_windows(cfg, references, streams, seed)
    table_stages(cfg, references, streams, seed)
    table_consistency(cfg, references, streams, seed)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
