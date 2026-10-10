"""The fading state machine, Python side (impl-plan section 2.1.5 / section 6).

This is a **port, not a reimplementation**. The authoritative statement of the
machine — every rule, and the reasoning behind the four that are decisions
rather than transcriptions — lives in ``lua/trace_rt/lib/controller.lua``, which
is the code participants actually drive. Read that file first; this module
follows it function for function, deliberately, so a diff between the two is
readable.

Why it exists twice: the runtime is CSP Lua inside Assetto Corsa and the Phase 1
simulator is offline Python. Impl plan section 6 names the resulting divergence
risk as the one that silently invalidates Gate G1 — the simulation would certify
a controller that is not the one participants experience. The mitigation is the
golden-trace corpus in ``golden_traces/``: a shared set of input traces with
expected event and state sequences that BOTH implementations must reproduce
exactly, run by ``kit/tests/test_m4_controller_parity.py`` on every change to
either side.

Pure, like the Lua: no clocks, no I/O, no randomness. All inputs are arguments,
all outputs are return values.

Stdlib only.
"""

# Fixed iteration order. Two implementations must emit events in the same order,
# so nothing here may iterate a dict's insertion order by accident.
ELEMENTS = ("braking", "corner_speed", "apex")

STAGES = ("full", "reduced", "probe", "removed")


class _Corner:
    """One corner's evidence for one element."""

    __slots__ = ("window", "consec_fail", "qualified")

    def __init__(self):
        self.window = []
        self.consec_fail = 0
        self.qualified = False


class _Element:
    __slots__ = ("name", "stage", "applicable", "corners", "disabled", "pinned",
                 "reversions", "probe_start_lap", "revert_armed")

    def __init__(self, name, corner_ids):
        self.name = name
        self.stage = "full"
        self.applicable = list(corner_ids)
        self.corners = {cid: _Corner() for cid in self.applicable}
        # Zero applicable corners: the element is DISABLED, pinned at full
        # salience and never evaluated. Without this the quorum share is a
        # division by zero (impl plan section 7).
        self.disabled = not self.applicable
        self.pinned = False
        self.reversions = 0
        self.probe_start_lap = None
        # Rule 3 (one regression, one stage): a reversion disarms the revert
        # check until the share recovers. Armed at block start.
        self.revert_armed = True


class Controller:
    """The state machine for one block. See lua/trace_rt/lib/controller.lua."""

    def __init__(self, cfg, applicable):
        self.cfg = cfg
        self.elements = {e: _Element(e, applicable.get(e, ())) for e in ELEMENTS}

    # --- per-corner qualification -------------------------------------------

    def _update_corner(self, corner, met):
        """Fold one criterion boolean into a corner. True if qualification changed."""
        q = self.cfg["qualification"]
        corner.window.append(bool(met))
        while len(corner.window) > q["window_passes"]:
            corner.window.pop(0)

        corner.consec_fail = 0 if met else corner.consec_fail + 1

        was = corner.qualified
        # De-qualification is checked first and wins any conflict; losing
        # qualification is the conservative resolution.
        if corner.qualified and corner.consec_fail >= q["dequalify_consecutive_failures"]:
            corner.qualified = False
        elif not corner.qualified and sum(corner.window) >= q["required_passes"]:
            # A partly-filled window counts: 3 of 3 satisfies "3 of the last 4".
            corner.qualified = True
        return corner.qualified != was

    # --- element quorum ------------------------------------------------------

    def _quorum_ready(self, el):
        """Every applicable corner holds required_passes of evidence (rule 2)."""
        need = self.cfg["qualification"]["required_passes"]
        return all(len(el.corners[cid].window) >= need for cid in el.applicable)

    @staticmethod
    def _quorum_stats(el):
        ids = [cid for cid in el.applicable if el.corners[cid].qualified]
        return len(ids) / len(el.applicable), ids

    @staticmethod
    def _reset_evidence(el):
        for cid in el.applicable:
            el.corners[cid] = _Corner()

    @staticmethod
    def _event(el, transition, lap, t, share, qualified_ids, flipped):
        return {
            "element": el.name,
            "transition": transition,
            "t": t,
            "lap": lap,
            "quorum": {
                "qualified_share": share,
                "qualified_corners": list(qualified_ids),
                "applicable_corners": len(el.applicable),
                "flipped_corners": list(flipped),
            },
        }

    # --- the step ------------------------------------------------------------

    def _step_element(self, el, pass_, events):
        if el.disabled or pass_["corner_id"] not in el.corners:
            return

        met = (pass_.get("criteria") or {}).get(el.name)
        # Rule 4: None is NO EVIDENCE. The pass does not enter the window at all.
        if met is None:
            return

        corner = el.corners[pass_["corner_id"]]
        flipped = [pass_["corner_id"]] if self._update_corner(corner, met) else []

        # No transitions once removed (terminal within the block) or pinned by
        # the reversion cap. Qualification above still updates: withdrawal
        # removes the scaffold, never the measurement.
        if el.stage == "removed" or el.pinned:
            return
        if not self._quorum_ready(el):
            return

        share, qualified_ids = self._quorum_stats(el)
        qu = self.cfg["quorum"]
        requalify = self.cfg["qualification"]["requalify_on_advance"]
        lap, t = pass_["lap"], pass_["t"]

        # Rule 3: re-arm as soon as the share recovers to the threshold, so the
        # NEXT fall below it is a fresh regression rather than the tail of the
        # one already acted on.
        if share >= qu["revert_threshold"]:
            el.revert_armed = True

        # AT MOST ONE TRANSITION PER ELEMENT PER PASS.
        if el.stage == "full":
            # No reversion below full; it is already the most supportive stage.
            if share >= qu["advance_threshold"]:
                el.stage = "reduced"
                el.revert_armed = True   # an advance must stay undoable (rule 3)
                events.append(self._event(el, "full_to_reduced", lap, t, share,
                                          qualified_ids, flipped))
                if requalify:
                    self._reset_evidence(el)

        elif el.stage == "reduced":
            if share >= qu["advance_threshold"]:
                el.stage = "probe"
                el.probe_start_lap = lap
                el.revert_armed = True   # an advance must stay undoable (rule 3)
                events.append(self._event(el, "reduced_to_probe", lap, t, share,
                                          qualified_ids, flipped))
                if requalify:
                    self._reset_evidence(el)
            elif el.revert_armed and share < qu["revert_threshold"]:
                # Reversions do not reset: the depleted evidence is what the
                # learner must rebuild.
                el.stage = "full"
                el.revert_armed = False  # one regression, one stage (rule 3)
                events.append(self._event(el, "reduced_to_full", lap, t, share,
                                          qualified_ids, flipped))

        elif el.stage == "probe":
            # The revert check comes FIRST: a quorum collapse on the very pass
            # that would complete the probe is a regression, not a success.
            if el.revert_armed and share < qu["revert_threshold"]:
                el.stage = "reduced"
                el.probe_start_lap = None
                el.revert_armed = False  # one regression, one stage (rule 3)
                el.reversions += 1
                ev = self._event(el, "probe_to_revert", lap, t, share, qualified_ids, flipped)
                ev["reversion_count"] = el.reversions
                events.append(ev)
                if el.reversions >= self.cfg["probe"]["reversion_cap"]:
                    # Pinned means pinned in BOTH directions — the element is out
                    # of the machine for the rest of the block.
                    el.pinned = True
                    cap = self._event(el, "cap_reached", lap, t, share, qualified_ids, flipped)
                    cap["reversion_count"] = el.reversions
                    events.append(cap)
            elif lap >= el.probe_start_lap + self.cfg["probe"]["laps"]:
                # Reaching here means the quorum was READY and at or above the
                # revert threshold, so "3 laps with quorum maintained" is a
                # verdict on real evidence. No reset: `removed` is terminal.
                el.stage = "removed"
                el.probe_start_lap = None
                events.append(self._event(el, "probe_to_removed", lap, t, share,
                                          qualified_ids, flipped))

    def step(self, pass_):
        """Advance by one closed corner pass; return the controller events.

        ``pass_`` = {corner_id, lap, t, criteria: {braking, corner_speed, apex}},
        each criterion True / False / None. Events match
        schemas/fades.schema.json except ``schema_version`` and ``block_id``,
        which the caller stamps.
        """
        events = []
        for e in ELEMENTS:
            self._step_element(self.elements[e], pass_, events)
        return events

    def finish(self, lap, t):
        """Close the block; elements mid-probe are logged right-censored."""
        events = []
        for e in ELEMENTS:
            el = self.elements[e]
            if el.stage == "probe":
                share, ids = self._quorum_stats(el)
                ev = self._event(el, "censored", lap, t, share, ids, [])
                ev["reversion_count"] = el.reversions
                events.append(ev)
        return events

    # --- readers -------------------------------------------------------------

    def disabled_elements(self):
        return [e for e in ELEMENTS if self.elements[e].disabled]

    def stages(self):
        return {e: self.elements[e].stage for e in ELEMENTS}

    def probe_remaining(self, element, current_lap):
        """Laps of probe withdrawal still to run, or None if not probing.

        `current_lap` is the raw lap counter fed to `observe` (``pass.lap``), not
        a block-relative count: the probe completion test is
        ``pass.lap >= probe_start_lap + probe.laps``, so the countdown must be
        read in that same space. Mirrors `controller.lua`'s `M.probe_remaining`.

        Deliberately not part of `snapshot()` — the golden traces pin the
        snapshot field for field, so a reader added there would churn the whole
        G1 parity corpus to display a number.
        """
        el = self.elements.get(element)
        if el is None or el.stage != "probe" or el.probe_start_lap is None:
            return None
        return max(0, (el.probe_start_lap + self.cfg["probe"]["laps"]) - current_lap)

    def qualified(self, corner_id):
        """Per-element qualification of one corner (False where inapplicable)."""
        out = {}
        for e in ELEMENTS:
            c = self.elements[e].corners.get(corner_id)
            out[e] = bool(c and c.qualified)
        return out

    def snapshot(self):
        """Inspectable state, field-comparable against the Lua snapshot."""
        out = {}
        for e in ELEMENTS:
            el = self.elements[e]
            qualified = [cid for cid in el.applicable if el.corners[cid].qualified]
            out[e] = {
                "stage": el.stage,
                "disabled": el.disabled,
                "pinned": el.pinned,
                "revert_armed": el.revert_armed,
                "reversions": el.reversions,
                "applicable_corners": len(el.applicable),
                "qualified_corners": qualified,
                "qualified_share": (len(qualified) / len(el.applicable)) if el.applicable else 0,
                "corners": [
                    {
                        "corner_id": cid,
                        "window": list(el.corners[cid].window),
                        "consec_fail": el.corners[cid].consec_fail,
                    }
                    for cid in el.applicable
                ],
            }
        return out
