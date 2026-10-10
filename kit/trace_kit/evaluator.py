"""Per-pass competency criteria, Python side (impl-plan section 2.1.4).

A **port** of ``lua/trace_rt/lib/evaluator.lua``, which is the authoritative
statement of the three criteria and carries the reasoning for each. Read that
file first; this one follows it function for function so a diff is readable.

It exists here because the Phase 1 simulator generates synthetic novice
*metrics* — brake-initiation distance, minimum corner speed, apex RMS — and must
turn them into criterion booleans through exactly the arithmetic the runtime
uses, or Gate G1 would tune the controller against a different evaluator than
the one participants drive. The golden-trace corpus pins both.

What is NOT here: turning a stream of per-frame car samples into those metrics.
In the runtime that is ``lib/pass_metrics.lua``; offline it is
``trace_kit.reference``, whose detectors ``pass_metrics`` is pinned against.

Stdlib only.
"""


def applicable(reference):
    """Corners each element applies to, in reference-table order.

    A corner with no ``braking`` entry was annotated without a braking zone
    (taken flat): no marker, no criterion, and out of the braking element's
    quorum denominator (impl plan section 7).
    """
    out = {"braking": [], "corner_speed": [], "apex": []}
    for c in reference["corners"]:
        if c.get("braking") is not None:
            out["braking"].append(c["corner_id"])
        out["corner_speed"].append(c["corner_id"])
        out["apex"].append(c["corner_id"])
    return out


def index_corners(reference):
    """Reference corners keyed by id."""
    return {c["corner_id"]: c for c in reference["corners"]}


# --- bands ------------------------------------------------------------------

def _band(sigma, evm, floor):
    scaled = sigma * evm
    return scaled if scaled > floor else floor


def bands(cfg, corner_ref):
    """The three tolerance bands for one corner; ``braking_m`` absent if flat.

    band = max(sigma_ref x EVM_source, floor). The EVM is chosen by the CORNER's
    own ``source``, never globally: a human-substituted corner's sigma already
    contains motor variability and must not be inflated twice.
    """
    evm = cfg["evm"]["human"] if corner_ref["source"] == "human" else cfg["evm"]["ai"]
    floors = cfg["band_floors"]
    out = {
        "corner_speed_kmh": _band(corner_ref["corner_speed"]["sigma_ref_kmh"],
                                  evm, floors["corner_speed_kmh"]),
        "apex_m": _band(corner_ref["apex"]["sigma_ref_m"], evm, floors["apex_m"]),
    }
    if corner_ref.get("braking") is not None:
        out["braking_m"] = _band(corner_ref["braking"]["sigma_ref_m"],
                                 evm, floors["braking_m"])
    return out


# --- rolling mean (the consistency gate's datum) ----------------------------

def push_history(history, distance_m, window_passes):
    """Append a measured brake distance, keeping up to window_passes - 1 entries.

    Those are the other members of the qualification window the NEXT pass will
    join; the current pass is never in its own mean. Null distances are never
    appended — no evidence means no evidence here too.
    """
    history.append(distance_m)
    keep = max(1, window_passes - 1)
    while len(history) > keep:
        history.pop(0)
    return history


# --- the evaluation ---------------------------------------------------------

def evaluate(cfg, corner_ref, metrics, history=None):
    """Judge one closed pass. See lua/trace_rt/lib/evaluator.lua for the rules.

    A criterion of ``None`` means the metric was not measurable on this pass:
    NO EVIDENCE, not a failure. The controller drops such a pass from that
    element's evidence window entirely.
    """
    b = bands(cfg, corner_ref)
    criteria = {"braking": None, "corner_speed": None, "apex": None}
    gates = {"accuracy": None, "consistency": None}
    out = {"criteria": criteria, "braking_gates": gates, "bands": b,
           "rolling_mean_m": None, "speed_envelope_deviation_kmh": None}

    # --- braking: accuracy AND consistency ---
    d = metrics.get("brake_initiation_distance_m")
    if corner_ref.get("braking") is not None and d is not None:
        gates["accuracy"] = abs(d) <= b["braking_m"]
        hist = history or []
        if not hist:
            # No prior sample: nothing to be consistent WITH. Vacuously met, so
            # the first pass at a corner is judged on accuracy alone.
            gates["consistency"] = True
        else:
            mean = sum(hist) / len(hist)
            out["rolling_mean_m"] = mean
            gates["consistency"] = abs(d - mean) <= (
                cfg["criteria"]["consistency_delta_ratio"] * b["braking_m"])
        criteria["braking"] = gates["accuracy"] and gates["consistency"]

    # --- corner speed: two-sided band about the expert mean ---
    v = metrics.get("min_corner_speed_kmh")
    if v is not None:
        dev = v - corner_ref["corner_speed"]["mean_kmh"]
        out["speed_envelope_deviation_kmh"] = dev
        criteria["corner_speed"] = abs(dev) <= b["corner_speed_kmh"]

    # --- apex: one-sided, against the reference's own mean RMS ---
    rms = metrics.get("apex_rms_m")
    if rms is not None:
        criteria["apex"] = rms <= corner_ref["apex"]["mean_rms_m"] + b["apex_m"]

    return out
