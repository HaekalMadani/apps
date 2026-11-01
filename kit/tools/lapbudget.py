"""What a SHORTER session buys and costs: lap budget x evidence requirement.

Written 2026-10-15 against a hard protocol constraint that arrived after Gate
G1 was met: the eval plan books ~3 h 15 of participant time across three
sessions (60 + 75 + 60) and the real ceiling is 30-60 min for the WHOLE study.
Every committed figure -- the G1 verdict, `windowscan.py`'s tables, the
traversal arithmetic -- is computed at `simulate.BLOCK_LAPS = 15`, which the
eval plan derived from "30 minutes of driving on a ~2-minute circuit". Both
halves of that are now wrong: the block is shorter, and the circuit is not
2 minutes (measured wall-clock below).

Three questions, three tables:

  floors     the traversal arithmetic over candidate (window, probe) pairs,
             converted to minutes at the MEASURED lap time rather than the eval
             plan's assumed one. This is where the load-bearing result is:
             cutting `probe.laps` alone buys NOTHING while probe.laps <=
             required_passes, because `_quorum_ready` gates `probe_to_removed`
             too. The lever is `required_passes`.
  budget     per element, the share of streams removed / censored at each
             candidate lap budget, under the committed novice model and the
             measured apex one, at the frozen 3-of-4 window.
  shorter    the same at shortened windows (3-of-4 -> 2-of-3 and friends),
             scored on BOTH margins: a typical improver must advance and a
             non-improver must not. A shorter window is a weaker test, and the
             false-advance column is what it costs.

It never writes `controller_config.json` -- same rule as rescore.py, apexscan.py
and windowscan.py: every override is in memory, because an edit there re-pins
the frozen hash and re-opens Gate G1. It is NOT a Gate G1 run.

    python kit/tools/lapbudget.py [streams-per-type-per-pair] [seed]

Run it as `200 trace-g1` to reproduce the tables in README.md -- the committed
report's own seed and stream count, so the 15-lap 3-of-4 row is comparable with
`simulation_report.json` and with windowscan's.

MEASURED LAP TIMES (wall clock, started_at -> ended_at over laps_completed,
every real block in trace_data; includes rolling start and any resets, so it is
an over-estimate of a flying lap and the right number for a session budget):
  national      (2.60 km, M235i)   62-76 s/lap over 9 blocks, median ~70 s
  international (2.95 km, TT Cup)   71-98 s/lap over 3 blocks, median ~80 s
The eval plan's "~2-minute circuit" is wrong by nearly 2x in TRACE's favour.
"""
import copy
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS

# windowscan.py's figures, from apexscan.py over 227 real pair-1 passes. The
# committed model's apex parameters are assumptions and the sigma is wrong by
# about six times, so every apex row is reported both ways.
MEASURED_APEX = {"apex_offset0_m": 2.49, "apex_sigma_m": 1.86}
COMMITTED_APEX = {"apex_offset0_m": 1.2, "apex_sigma_m": 0.30}

# Seconds per lap, measured (see the module docstring). Used only to turn laps
# into minutes in the floors table.
LAP_S = {"national": 70.0, "international": 80.0}

# (window_passes, required_passes, probe.laps). The frozen config first, then
# the cheaper ladders, then one longer window for contrast with windowscan.
LADDERS = [(4, 3, 3), (4, 3, 2), (4, 3, 1),
           (3, 2, 3), (3, 2, 2), (3, 2, 1),
           (2, 2, 2), (4, 2, 2), (6, 4, 3)]

# Lap budgets worth asking about: what a real block is said to yield (15-18),
# and what a 30/45-minute total study leaves for one training block.
BUDGETS = [8, 10, 12, 15, 18]


def learner(name):
    return next(l for l in S.LEARNER_TYPES if l.name == name)


def with_model(apex):
    before = dict((k, S.MODEL[k]) for k in apex)
    for k, v in apex.items():
        S.MODEL[k] = v
    return before


def traversal_floor(window, required, probe_laps):
    """Earliest lap a full traversal can COMPLETE. windowscan.traversal_floor,
    with probe.laps a parameter instead of read off the config.

    `_quorum_ready` is keyed on required_passes, not window_passes, and it gates
    EVERY transition including probe_to_removed -- so the probe costs the longer
    of its lap count and a fresh evidence window, and `window` does not appear.
    """
    return 2 * required + max(probe_laps, required)


def table_floors():
    print("## floors -- the arithmetic, in laps and in minutes\n")
    print("Lower bound and a loose one: it assumes every applicable corner")
    print("qualifies on its first `required_passes` passes at every stage. The")
    print("frozen 3-of-4 floor is 9 laps and the earliest removal actually")
    print("observed in simulation is lap 11.\n")
    print("  {:<9s} {:>5s}   {:>5s}   {:>12s} {:>14s}".format(
        "window", "probe", "laps", "national min", "international min"))
    for window, required, probe_laps in LADDERS:
        need = traversal_floor(window, required, probe_laps)
        print("  {:<9s} {:5d}   {:5d}   {:12.1f} {:14.1f}".format(
            "{}-of-{}".format(required, window), probe_laps, need,
            need * LAP_S["national"] / 60.0, need * LAP_S["international"] / 60.0))
    print("")
    print("  NOTE the (4,3,2) and (4,3,1) rows: cutting the probe from 3 laps to")
    print("  2 or 1 changes the floor by NOTHING, because max(probe.laps,")
    print("  required_passes) is already required_passes. Shortening the probe")
    print("  without shortening the window buys zero laps and costs the probe")
    print("  its status as a retention test.")
    print("")


def shares(cfg, references, name, streams, seed, laps):
    """Per-element share removed / left full / censored, and mean removed."""
    left_full = dict((e, 0) for e in ELEMENTS)
    removed = dict((e, 0) for e in ELEMENTS)
    censored = dict((e, 0) for e in ELEMENTS)
    seen = dict((e, 0) for e in ELEMENTS)
    per_stream = []
    for pair_index, reference in enumerate(references):
        rng = random.Random("{}|{}|{}".format(seed, name, pair_index))
        for _ in range(streams):
            stream = S.simulate_stream(cfg, reference, learner(name), rng, laps=laps)
            count = 0
            for element in ELEMENTS:
                if element in stream["disabled"]:
                    continue
                seen[element] += 1
                stage = stream["final_stages"][element]
                if stage != "full":
                    left_full[element] += 1
                if stage == "removed":
                    removed[element] += 1
                    count += 1
                if stage == "probe":
                    censored[element] += 1
            per_stream.append(count)
    pct = lambda d, e: (100.0 * d[e] / seen[e]) if seen[e] else 0.0
    return {
        "left_full": dict((e, pct(left_full, e)) for e in ELEMENTS),
        "removed": dict((e, pct(removed, e)) for e in ELEMENTS),
        "censored": dict((e, pct(censored, e)) for e in ELEMENTS),
        "mean_removed": statistics.fmean(per_stream) if per_stream else 0.0,
    }


def candidate(cfg, window, required, probe_laps):
    c = copy.deepcopy(cfg)
    c["qualification"]["window_passes"] = window
    c["qualification"]["required_passes"] = required
    c["probe"]["laps"] = probe_laps
    return c


def _row(label, t, n):
    return "  {:<11s}  {:>21s}   {:>21s}   {:>9s}  {:5.3f}".format(
        label,
        "{:3.0f}% /{:3.0f}% /{:3.0f}%".format(*[t["removed"][e] for e in ELEMENTS]),
        "{:3.0f}% /{:3.0f}% /{:3.0f}%".format(*[t["censored"][e] for e in ELEMENTS]),
        "{:3.0f}% /{:3.0f}%".format(n["left_full"]["corner_speed"], n["left_full"]["apex"]),
        t["mean_removed"])


def _header(first):
    print("  {:<11s}  {:>21s}   {:>21s}   {:>9s}  {:>5s}".format(
        first, "removed  b / s / a", "censored  b / s / a", "false s/a", "mean"))


def table_budget(cfg, references, streams, seed):
    print("## budget -- the frozen 3-of-4 window at shorter lap budgets\n")
    print("`removed` is a completed traversal, `censored` a block that ended")
    print("mid-probe (right-censored -- RQ1's own outcome, not a failure).")
    print("`false s/a` is the NON-improver leaving full on corner speed / apex,")
    print("which is the margin that bounds the design from above.\n")
    for label, apex in (("committed apex model", COMMITTED_APEX),
                        ("MEASURED apex model", MEASURED_APEX)):
        before = with_model(apex)
        print("{} -- typical improver, 3-of-4, probe 3".format(label))
        _header("laps")
        for laps in BUDGETS:
            t = shares(cfg, references, "typical_improver", streams, seed, laps)
            n = shares(cfg, references, "non_improver", streams, seed, laps)
            print(_row(str(laps), t, n))
        with_model(before)
        print("")


def table_shorter(cfg, references, streams, seed):
    print("## shorter -- cheaper ladders, measured apex, at 12 and 15 laps\n")
    print("A shorter window is a weaker test before it is a cheaper one. Read")
    print("the `false s/a` column against the `removed` column: the question is")
    print("not whether a shortened ladder completes but whether it completes")
    print("for the learner who has not improved.\n")
    before = with_model(MEASURED_APEX)
    for laps in (12, 15):
        print("{} laps".format(laps))
        _header("window/probe")
        for window, required, probe_laps in LADDERS:
            c = candidate(cfg, window, required, probe_laps)
            t = shares(c, references, "typical_improver", streams, seed, laps)
            n = shares(c, references, "non_improver", streams, seed, laps)
            print(_row("{}-of-{} p{}".format(required, window, probe_laps), t, n))
        print("")
    with_model(before)


def main(argv):
    streams = int(argv[1]) if len(argv) > 1 else 200
    seed = argv[2] if len(argv) > 2 else "lapbudget"
    cfg = S.load_config()
    references = S.load_references()
    print("lapbudget -- config_id {}, {} streams/type/pair, seed {}\n".format(
        cfg["config_id"], streams, seed))
    table_floors()
    table_budget(cfg, references, streams, seed)
    table_shorter(cfg, references, streams, seed)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
