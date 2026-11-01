"""What would a per element x corner controller buy, and what would it cost?

Written 2026-10-30 for step 2 of the v9 novelty audit
(`novelty_audit/STEP2_directions.md` section 3). Framing v9 section 5.2 describes
the controller as fading "per element x per corner"; the frozen controller fades
per ELEMENT on a cross-corner quorum. v9's core RQ (RQ2) is a probe-failure RATE,
so the question that decides it is how many probes each design produces in a
15-lap block, and what the false-fade rate does when the quorum's averaging is
taken away.

The per-corner variant is built from the REAL controller, not a rewrite: each
corner gets its own `Controller` whose only applicable corner is itself. With a
denominator of one, the quorum share is 0 or 1, so "advance at >= 0.75" means
"this corner is qualified" and "revert below 0.5" means "it is not", quorum
readiness is "this corner holds `required_passes` of evidence", and a 2-lap probe
is 2 passes of that corner. Every other rule (re-qualification on advance, one
regression one stage, the reversion cap, censoring) is the frozen code path.
What this does NOT price: a per-corner rewrite might choose different thresholds,
and the Lua side, the golden traces and G1 would all have to follow.

Both controllers see the SAME synthetic streams. `simulate_stream` draws every
random number before the controller is stepped, so swapping the controller class
leaves the stream byte-identical and the comparison is paired.

Note what the probe-failure rate means here: the simulated learner has NO cue
dependency (the model has no term for it), so every simulated probe failure is
lap-to-lap noise plus selection. It is the noise-only null of v9 section 7.3 in
miniature, under the committed novice model rather than a fitted one.

It never writes `controller_config.json`; like windowscan.py it is not a Gate G1
run and its numbers are not a verdict.

    python kit/tools/percornerscan.py [streams-per-type] [seed] [participants]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from trace_kit import simulate as S
from trace_kit.controller import ELEMENTS, Controller

TYPES = ["fast_improver", "typical_improver", "slow_improver", "non_improver",
         "erratic", "staggered_regressor"]


class PerCorner:
    """One frozen Controller per corner; quacks like Controller for simulate_stream."""

    def __init__(self, cfg, applicable):
        ids = []
        for e in ELEMENTS:
            for cid in applicable.get(e, ()):
                if cid not in ids:
                    ids.append(cid)
        self.ids = ids
        self.all_disabled = [e for e in ELEMENTS if not applicable.get(e)]
        self.sub = dict(
            (cid, Controller(cfg, dict((e, [cid]) for e in ELEMENTS
                                       if cid in applicable.get(e, ()))))
            for cid in ids)

    @staticmethod
    def _tag(events, cid):
        for ev in events:
            ev["corner_id"] = cid
        return events

    def step(self, pass_):
        return self._tag(self.sub[pass_["corner_id"]].step(pass_), pass_["corner_id"])

    def finish(self, lap, t):
        out = []
        for cid in self.ids:
            out.extend(self._tag(self.sub[cid].finish(lap, t), cid))
        return out

    def stages(self):
        # Only feeds simulate_stream's stage trace, which this script does not read.
        return dict((e, "full") for e in ELEMENTS)

    def disabled_elements(self):
        return list(self.all_disabled)


AFTER = {"full_to_reduced": "reduced", "reduced_to_probe": "probe",
         "reduced_to_full": "full", "probe_to_revert": "reduced",
         "probe_to_removed": "removed"}


def learner(name):
    return next(l for l in S.LEARNER_TYPES if l.name == name)


def tally(cfg, stream, per_corner):
    """Per element: probes started, and how each ended; plus the false-fade facts."""
    q = cfg["qualification"]["dequalify_consecutive_failures"]
    out = dict((e, {"probes": 0, "removed": 0, "reverted": 0, "censored": 0,
                    "left_full": 0, "late_removal": 0, "ends_off_full": 0}) for e in ELEMENTS)
    # Final stage per unit (element, or element x corner), replayed from events.
    # `ends_off_full` is the committed report's `share_any_fade` definition
    # (summarise_stream's `left_full` reads the FINAL stage); `left_full` here
    # counts any departure from full, including one later reverted.
    final = {}
    for ev in stream["events"]:
        to = AFTER.get(ev["transition"])
        if to is not None:
            final[(ev["element"], ev.get("corner_id"))] = to
    for (e, _), stage in final.items():
        if stage != "full":
            out[e]["ends_off_full"] += 1
    for ev in stream["events"]:
        t = out[ev["element"]]
        kind = ev["transition"]
        if kind == "reduced_to_probe":
            t["probes"] += 1
        elif kind == "probe_to_removed":
            t["removed"] += 1
            # Removed once the regression was already detectable: per corner the
            # floor is that corner's own onset; per element it is the quorum's.
            if per_corner:
                onset = stream["onsets"].get(ev["corner_id"])
                floor = None if onset is None else onset + q - 1
            else:
                floor = stream["earliest_reversion"].get(ev["element"])
            if floor is not None and ev["lap"] >= floor:
                t["late_removal"] += 1
        elif kind == "probe_to_revert":
            t["reverted"] += 1
        elif kind == "censored":
            t["censored"] += 1
        elif kind == "full_to_reduced":
            t["left_full"] += 1
    return out


def run(cfg, reference, name, streams, seed, per_corner):
    original = S.Controller
    S.Controller = PerCorner if per_corner else Controller
    try:
        rng = random.Random("{}|{}|0".format(seed, name))
        rows = []
        for _ in range(streams):
            stream = S.simulate_stream(cfg, reference, learner(name), rng)
            rows.append(tally(cfg, stream, per_corner))
        return rows
    finally:
        S.Controller = original


def wilson_half(p, n, z=1.96):
    if n <= 0:
        return float("nan")
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return half, centre


def summarise(rows):
    n = len(rows)
    s = {}
    for e in ELEMENTS + ("all",):
        keys = ELEMENTS if e == "all" else (e,)
        tot = dict((k, sum(r[x][k] for r in rows for x in keys))
                   for k in ("probes", "removed", "reverted", "censored", "left_full",
                             "late_removal", "ends_off_full"))
        decided = tot["removed"] + tot["reverted"]
        s[e] = {
            "probes_pp": tot["probes"] / n,
            "fail_rate": (tot["reverted"] / decided) if decided else float("nan"),
            "censored_share": (tot["censored"] / tot["probes"]) if tot["probes"] else float("nan"),
            "removed_pp": tot["removed"] / n,
            "share_ends_off_full": sum(1 for r in rows if any(r[x]["ends_off_full"] for x in keys)) / n,
            "share_any_left_full": sum(1 for r in rows if any(r[x]["left_full"] for x in keys)) / n,
            "share_any_removed": sum(1 for r in rows if any(r[x]["removed"] for x in keys)) / n,
            "share_late_removal": sum(1 for r in rows if any(r[x]["late_removal"] for x in keys)) / n,
        }
    return s


def main(argv):
    streams = int(argv[1]) if len(argv) > 1 else 400
    seed = argv[2] if len(argv) > 2 else "percorner"
    participants = int(argv[3]) if len(argv) > 3 else 15
    cfg = S.load_config()
    # Pair 1 only: pair 2 is descoped (CLAUDE.md, Protocol and session budget).
    # load_references() is sorted by file name, so index 0 is reference_pair1.json;
    # the seed's "|0" suffix then matches simulate.run_type's pair-1 stream.
    reference = S.load_references()[0]

    print("streams/type={} seed={} block_laps={} window={}-of-{} probe_laps={}".format(
        streams, seed, S.BLOCK_LAPS, cfg["qualification"]["required_passes"],
        cfg["qualification"]["window_passes"], cfg["probe"]["laps"]))
    print("apex model: offset0={} sigma={}".format(S.MODEL["apex_offset0_m"], S.MODEL["apex_sigma_m"]))

    results = {}
    for name in TYPES:
        for pc in (False, True):
            results[(name, pc)] = summarise(run(cfg, reference, name, streams, seed, pc))

    head = "{:<22} {:<8} {:<13} {:>6} {:>6} {:>7} {:>7} {:>8} {:>8} {:>8} {:>8}"
    print()
    print(head.format("learner", "ctrl", "element", "probes", "fail", "censor",
                      "removed", "endsoff", "everleft", "anyremov", "lateremov"))
    for name in TYPES:
        for pc in (False, True):
            s = results[(name, pc)]
            for e in ELEMENTS + ("all",):
                r = s[e]
                print(head.format(
                    name, "corner" if pc else "element", e,
                    "{:.2f}".format(r["probes_pp"]),
                    "{:.3f}".format(r["fail_rate"]) if r["fail_rate"] == r["fail_rate"] else "-",
                    "{:.3f}".format(r["censored_share"]) if r["censored_share"] == r["censored_share"] else "-",
                    "{:.2f}".format(r["removed_pp"]),
                    "{:.3f}".format(r["share_ends_off_full"]),
                    "{:.3f}".format(r["share_any_left_full"]),
                    "{:.3f}".format(r["share_any_removed"]),
                    "{:.3f}".format(r["share_late_removal"])))
        print()

    # What n participants buy for RQ2, pooled over elements, typical-improver rate.
    print("RQ2 precision at n={} participants (pooled probes; no clustering correction):".format(participants))
    for name in ("fast_improver", "typical_improver", "slow_improver"):
        for pc in (False, True):
            r = results[(name, pc)]["all"]
            events = r["probes_pp"] * participants
            decided = events * (1 - (r["censored_share"] if r["censored_share"] == r["censored_share"] else 0))
            p = r["fail_rate"] if r["fail_rate"] == r["fail_rate"] else 0.0
            half, _ = wilson_half(p, decided) if decided > 0 else (float("nan"), 0)
            need = (80.0 / r["probes_pp"]) if r["probes_pp"] else float("inf")
            print("  {:<18} {:<8} probes={:6.1f} decided={:6.1f} fail={:.3f} 95%CI +/-{:.3f}  "
                  "participants for 80 probes (F3, 2x40): {:.0f}".format(
                      name, "corner" if pc else "element", events, decided, p, half, need))


if __name__ == "__main__":
    main(sys.argv)
