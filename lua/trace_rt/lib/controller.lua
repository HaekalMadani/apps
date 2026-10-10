-- controller.lua — the fading state machine (impl-plan module 2.1.5, framing v6).
--
-- A PURE function of (previous state, one closed corner pass) -> (new state,
-- controller events). No clocks, no I/O, no randomness, no rendering: every
-- input arrives as an argument and every output is a return value. That purity
-- is not tidiness, it is what makes the golden-trace parity suite possible —
-- this logic exists TWICE, here for the runtime and in kit/trace_kit/controller.py
-- for the Phase 1 simulator, and a divergence between them silently invalidates
-- Gate G1 (the simulation would certify a controller participants never drive).
-- The shared corpus in golden_traces/ is the agreement test.
--
-- No threshold below is a literal: every constant comes from controller_config
-- (impl plan section 6.3).
--
-- Style: plain imperative Lua 5.1, helpers called DIRECTLY — never stored in
-- tables and dispatched as t.fn(...), which crashes inside CSP (see CLAUDE.md).
--
-- ---------------------------------------------------------------------------
-- The machine, stated once
-- ---------------------------------------------------------------------------
--
-- Two levels of evidence, per element, independently:
--
--   PER CORNER (evidence). A corner QUALIFIES for an element when the element's
--   per-pass criterion held in `required_passes` of that corner's last
--   `window_passes` passes, and DE-QUALIFIES on `dequalify_consecutive_failures`
--   consecutive failures. Computed continuously whether or not the element is
--   currently visible: withdrawal removes the scaffold, never the measurement.
--
--   PER ELEMENT (presentation). The stage advances when the qualified share
--   across applicable corners reaches `quorum.advance_threshold` and reverts one
--   stage below `quorum.revert_threshold`. The element changes everywhere at
--   once, so the display stays coherent while the evidence stays local.
--
-- Stages: full -> reduced -> probe -> removed, one step at a time in either
-- direction. `removed` is terminal within the block; permanence is block-scoped
-- (a fresh state is built for every block, so nothing carries across).
--
-- ---------------------------------------------------------------------------
-- Four rules that are decisions, not transcriptions
-- ---------------------------------------------------------------------------
--
-- 1. RE-QUALIFICATION ON ADVANCE (framing v6, structural). Every stage ADVANCE
--    resets all corner qualification states and evidence windows for that
--    element; quorum must be rebuilt from passes driven under the new salience.
--    Reversions do NOT reset — the depleted evidence that fell below quorum is
--    exactly what the learner has to rebuild. Config-flagged
--    (`qualification.requalify_on_advance`) only so the simulator can show the
--    degenerate machine it prevents; the frozen study config sets it true.
--
-- 2. QUORUM READINESS (M4 decision, forced by rule 1). An element's quorum is
--    not evaluated AT ALL until every applicable corner holds at least
--    `required_passes` passes in its current evidence window. Without this the
--    machine is broken in the other direction: the reset in rule 1 drops the
--    qualified share to zero, which is below the revert threshold, so the very
--    next pass would revert the advance that just happened. Suppressing the
--    quorum until the evidence can support a verdict fixes that, applies
--    symmetrically to advances and reversions, and is the conservative
--    direction the design asks for (premature withdrawal is worse than delayed).
--    It also makes the probe's "3 laps with quorum maintained" meaningful: the
--    readiness point lands after `required_passes` probed passes at every
--    corner, so the probe's completion check is always preceded by a real
--    quorum verdict rather than by an empty one.
--
-- 3. ONE REGRESSION, ONE STAGE (M4 decision, found by the golden traces). After
--    a REVERSION the element's revert check is DISARMED until the qualified
--    share recovers to the revert threshold; after an ADVANCE it is armed
--    immediately. Without this the machine reverts two stages for one
--    regression: a probe reversion leaves the element at reduced with the same
--    sub-threshold share that caused it, so the very next pass reverts it again
--    to full — and because a deep collapse always cascades that way, the
--    reversion cap could never be reached at all. Disarming after a reversion
--    stops one regression being counted twice; leaving it armed after an
--    advance is what still lets a PREMATURE advance be undone when the learner
--    cannot produce the evidence at the new salience level, which is the whole
--    point of probe-and-revert.
--
-- 4. A NULL CRITERION IS NO EVIDENCE (M4 decision). When a pass yields no value
--    for an element's metric — no sustained brake application inside the
--    braking zone, an apex window the pass did not cover, a pass cut short at
--    block end — the criterion is nil and the pass does not enter that
--    element's window at all. It is neither a success nor a failure and cannot
--    contribute a consecutive failure. Scoring a null as a failure would punish
--    the learner for an annotation-zone fit problem (the very fault
--    trace_kit.reference's check_braking_zone_fit exists to catch), and novices
--    brake EARLIER than the reference, so a zone that fits the AI can miss
--    them. The residual risk is the mirror image and is stated rather than
--    engineered away: a corner that yields nothing but nulls keeps whatever
--    qualification it last had, and never becomes ready, so it stalls its
--    element instead of fading it — a stall, not a false fade. Null counts are
--    stamped into every pass record so the Gate G2 audit can see it happening.
--    (Invalid passes — off-track, wall contact — are NOT nulls: their metrics
--    are real and they feed the controller normally, per eval plan v2.)
--
-- ---------------------------------------------------------------------------

local M = {}

-- Fixed iteration order. Two implementations must emit events in the same
-- order, so nothing here may iterate a hash table's natural order.
M.ELEMENTS = { 'braking', 'corner_speed', 'apex' }

M.STAGES = { 'full', 'reduced', 'probe', 'removed' }

-- --- construction -----------------------------------------------------------

-- Build controller state for one block.
--
--   cfg        = decoded controller_config.json
--   applicable = { braking = { corner_id, ... }, corner_speed = {...}, apex = {...} }
--                the corners each element applies to, in a fixed order. A
--                corner with no braking zone is absent from `braking` (impl
--                plan section 7): no marker, no criterion, out of that
--                element's quorum denominator.
--
-- An element with ZERO applicable corners is DISABLED: pinned at full salience,
-- never evaluated, flagged so the runtime can record it in the block manifest.
-- Without this the quorum share is a division by zero (impl plan section 7).
function M.new(cfg, applicable)
  local state = { cfg = cfg, elements = {} }
  for i = 1, #M.ELEMENTS do
    local e = M.ELEMENTS[i]
    local ids = applicable[e] or {}
    local el = {
      name = e,
      stage = 'full',
      applicable = {},        -- ordered list of corner ids
      is_applicable = {},     -- id -> true, for O(1) membership
      corners = {},           -- id -> { window = {...}, consec_fail = n, qualified = bool }
      disabled = (#ids == 0),
      pinned = false,         -- reversion cap reached: stays at reduced
      reversions = 0,
      probe_start_lap = nil,
      -- Rule 3: a reversion disarms the revert check until the share recovers.
      -- Armed at block start so the machine is never in a state it cannot leave.
      revert_armed = true,
    }
    for j = 1, #ids do
      el.applicable[j] = ids[j]
      el.is_applicable[ids[j]] = true
      el.corners[ids[j]] = { window = {}, consec_fail = 0, qualified = false }
    end
    state.elements[e] = el
  end
  return state
end

-- Corner ids of every element that is disabled (zero applicable corners), in
-- element order. The runtime stamps these into the session manifest; nothing is
-- logged to the fade stream, because a disabled element never transitions and a
-- fade record with a zero denominator would be a fiction.
function M.disabled_elements(state)
  local out = {}
  for i = 1, #M.ELEMENTS do
    local el = state.elements[M.ELEMENTS[i]]
    if el.disabled then out[#out + 1] = el.name end
  end
  return out
end

-- --- per-corner qualification ----------------------------------------------

local function count_true(list)
  local n = 0
  for i = 1, #list do
    if list[i] then n = n + 1 end
  end
  return n
end

-- Fold one criterion boolean into a corner's evidence. Returns true if the
-- corner's qualification state changed.
local function update_corner(cfg, corner, met)
  local q = cfg.qualification
  local w = corner.window
  w[#w + 1] = met and true or false
  -- Keep only the last window_passes entries (a rolling window, oldest dropped).
  while #w > q.window_passes do
    table.remove(w, 1)
  end

  if met then
    corner.consec_fail = 0
  else
    corner.consec_fail = corner.consec_fail + 1
  end

  local was = corner.qualified
  -- De-qualification is checked FIRST and wins any conflict. With the study
  -- defaults the two rules cannot both fire (two consecutive failures leave at
  -- most 2 of 4 met, short of the 3 required), but a hand-tuned config could
  -- make them overlap, and losing qualification is the conservative resolution.
  if corner.qualified and corner.consec_fail >= q.dequalify_consecutive_failures then
    corner.qualified = false
  elseif not corner.qualified and count_true(w) >= q.required_passes then
    -- A partly-filled window counts: 3 of 3 satisfies "3 of the last 4".
    corner.qualified = true
  end
  return corner.qualified ~= was
end

-- --- element quorum ---------------------------------------------------------

-- True once every applicable corner holds at least required_passes of evidence
-- in its CURRENT window. See rule 2 in the header.
local function quorum_ready(cfg, el)
  local need = cfg.qualification.required_passes
  for i = 1, #el.applicable do
    if #el.corners[el.applicable[i]].window < need then return false end
  end
  return true
end

-- Qualified share and the qualified ids, in applicable order.
local function quorum_stats(el)
  local ids = {}
  for i = 1, #el.applicable do
    local id = el.applicable[i]
    if el.corners[id].qualified then ids[#ids + 1] = id end
  end
  return (#ids / #el.applicable), ids
end

-- Wipe every applicable corner's qualification and evidence (rule 1).
local function reset_evidence(el)
  for i = 1, #el.applicable do
    el.corners[el.applicable[i]] = { window = {}, consec_fail = 0, qualified = false }
  end
end

local function make_event(el, transition, pass, share, qualified_ids, flipped)
  local ev = {
    element = el.name,
    transition = transition,
    t = pass.t,
    lap = pass.lap,
    quorum = {
      qualified_share = share,
      qualified_corners = qualified_ids,
      applicable_corners = #el.applicable,
      flipped_corners = flipped,
    },
  }
  return ev
end

-- --- the step ---------------------------------------------------------------

-- Advance one element by one closed pass. Appends any events to `events`.
local function step_element(state, el, pass, events)
  if el.disabled then return end
  if not el.is_applicable[pass.corner_id] then return end

  local met = pass.criteria and pass.criteria[el.name]
  -- Rule 4: nil is no evidence. The pass does not enter the window at all.
  if met == nil then return end

  local corner = el.corners[pass.corner_id]
  local flipped = {}
  if update_corner(state.cfg, corner, met) then
    flipped[1] = pass.corner_id
  end

  -- No transitions once removed (terminal within the block) or pinned by the
  -- reversion cap. Qualification above still updates: withdrawal removes the
  -- scaffold, never the measurement, and RQ1 reads those states.
  if el.stage == 'removed' or el.pinned then return end
  if not quorum_ready(state.cfg, el) then return end

  local share, qualified_ids = quorum_stats(el)
  local qu = state.cfg.quorum
  local requalify = state.cfg.qualification.requalify_on_advance

  -- Rule 3: re-arm the revert check as soon as the share recovers to the
  -- threshold, so the NEXT fall below it is a fresh regression rather than the
  -- tail of the one already acted on.
  if share >= qu.revert_threshold then el.revert_armed = true end

  -- AT MOST ONE TRANSITION PER ELEMENT PER PASS. Evaluating again after a
  -- transition would let an advance and the reversion of that same advance fire
  -- on one pass.
  if el.stage == 'full' then
    -- No reversion below full; it is already the most supportive stage.
    if share >= qu.advance_threshold then
      el.stage = 'reduced'
      el.revert_armed = true   -- an advance must stay undoable (rule 3)
      events[#events + 1] = make_event(el, 'full_to_reduced', pass, share, qualified_ids, flipped)
      if requalify then reset_evidence(el) end
    end

  elseif el.stage == 'reduced' then
    if share >= qu.advance_threshold then
      el.stage = 'probe'
      el.probe_start_lap = pass.lap
      el.revert_armed = true   -- an advance must stay undoable (rule 3)
      events[#events + 1] = make_event(el, 'reduced_to_probe', pass, share, qualified_ids, flipped)
      if requalify then reset_evidence(el) end
    elseif el.revert_armed and share < qu.revert_threshold then
      -- Reversions do not reset (framing v6): the depleted evidence is what the
      -- learner must rebuild.
      el.stage = 'full'
      el.revert_armed = false  -- one regression, one stage (rule 3)
      events[#events + 1] = make_event(el, 'reduced_to_full', pass, share, qualified_ids, flipped)
    end

  elseif el.stage == 'probe' then
    -- The revert check comes FIRST: a quorum collapse on the very pass that
    -- would complete the probe is a regression, not a success.
    if el.revert_armed and share < qu.revert_threshold then
      el.stage = 'reduced'
      el.probe_start_lap = nil
      el.revert_armed = false  -- one regression, one stage (rule 3)
      el.reversions = el.reversions + 1
      local ev = make_event(el, 'probe_to_revert', pass, share, qualified_ids, flipped)
      ev.reversion_count = el.reversions
      events[#events + 1] = ev
      -- "At most 2 reversion cycles per element per block; after the second the
      -- element stays at reduced salience for the remainder of the block and is
      -- logged as such." Pinned means pinned in BOTH directions — the element is
      -- out of the machine, which is what makes the rest of the block
      -- interpretable rather than an oscillation.
      if el.reversions >= state.cfg.probe.reversion_cap then
        el.pinned = true
        local cap = make_event(el, 'cap_reached', pass, share, qualified_ids, flipped)
        cap.reversion_count = el.reversions
        events[#events + 1] = cap
      end
    elseif pass.lap >= el.probe_start_lap + state.cfg.probe.laps then
      -- Probe held for its full length. Reaching here means the quorum was
      -- READY and at or above the revert threshold, so "3 laps with quorum
      -- maintained" is a verdict on real evidence, not on an empty window.
      -- Counting the probe from the entry PASS rather than the next lap
      -- boundary is what gives every applicable corner exactly probe.laps
      -- passes driven with the element hidden.
      el.stage = 'removed'
      el.probe_start_lap = nil
      events[#events + 1] = make_event(el, 'probe_to_removed', pass, share, qualified_ids, flipped)
      -- Deliberately NO reset here even though this is an advance: the reset
      -- exists to force fresh evidence before the NEXT advance, and `removed`
      -- is terminal. Wiping the states would only destroy what RQ1 reads.
    end
  end
end

-- Advance the controller by one closed corner pass.
--
--   pass = { corner_id, lap, t, criteria = { braking = <bool|nil>,
--            corner_speed = <bool|nil>, apex = <bool|nil> } }
--
-- Returns a list of controller events (possibly empty), in element order. Each
-- event matches schemas/fades.schema.json except for `schema_version` and
-- `block_id`, which the caller stamps — the controller does not know its block.
function M.step(state, pass)
  local events = {}
  for i = 1, #M.ELEMENTS do
    step_element(state, state.elements[M.ELEMENTS[i]], pass, events)
  end
  return events
end

-- Close the block. Any element still mid-probe is logged as incomplete /
-- right-censored: in RQ1's probe-outcome tabulation it counts as neither held
-- nor reverted, and the element's final state stays `probe`.
function M.finish(state, lap, t)
  local events = {}
  for i = 1, #M.ELEMENTS do
    local el = state.elements[M.ELEMENTS[i]]
    if el.stage == 'probe' then
      local share, ids = quorum_stats(el)
      local ev = make_event(el, 'censored', { t = t, lap = lap }, share, ids, {})
      ev.reversion_count = el.reversions
      events[#events + 1] = ev
    end
  end
  return events
end

-- --- readers (for pass records, the panel, and the golden-trace tests) -------

-- Per-element stage, as the pass record's `stage` object.
function M.stages(state)
  local out = {}
  for i = 1, #M.ELEMENTS do
    local e = M.ELEMENTS[i]
    out[e] = state.elements[e].stage
  end
  return out
end

-- Laps of probe withdrawal still to run for `element`, or nil when that element
-- is not probing. `current_lap` is the raw lap counter the controller is fed on
-- each pass (`pass.lap`), NOT a block-relative count — the probe's completion
-- test is `pass.lap >= probe_start_lap + probe.laps`, so the countdown has to be
-- read in that same space or it will disagree with the machine it is reporting.
--
-- Deliberately NOT part of `snapshot`: the golden traces pin the snapshot field
-- for field, so a panel-only reader added there would churn the whole G1 parity
-- corpus to display a number.
function M.probe_remaining(state, element, current_lap)
  local el = state.elements[element]
  if el == nil or el.stage ~= 'probe' or el.probe_start_lap == nil then return nil end
  local remaining = (el.probe_start_lap + state.cfg.probe.laps) - current_lap
  if remaining < 0 then remaining = 0 end
  return remaining
end

-- Per-element qualification of ONE corner, as the pass record's `qualified`
-- object. A corner an element does not apply to reads false — the element has
-- no opinion about it and the schema wants a boolean.
function M.qualified(state, corner_id)
  local out = {}
  for i = 1, #M.ELEMENTS do
    local e = M.ELEMENTS[i]
    local el = state.elements[e]
    local c = el.corners[corner_id]
    out[e] = (c ~= nil) and c.qualified or false
  end
  return out
end

-- Full inspectable snapshot, used by the golden-trace parity suite and the
-- experimenter panel. Ordered lists only, so two implementations can be
-- compared field for field.
function M.snapshot(state)
  local out = {}
  for i = 1, #M.ELEMENTS do
    local e = M.ELEMENTS[i]
    local el = state.elements[e]
    local qualified = {}
    local windows = {}
    for j = 1, #el.applicable do
      local id = el.applicable[j]
      local c = el.corners[id]
      if c.qualified then qualified[#qualified + 1] = id end
      windows[#windows + 1] = { corner_id = id, window = c.window, consec_fail = c.consec_fail }
    end
    local share = (#el.applicable > 0) and (#qualified / #el.applicable) or 0
    out[e] = {
      stage = el.stage,
      disabled = el.disabled,
      pinned = el.pinned,
      revert_armed = el.revert_armed,
      reversions = el.reversions,
      applicable_corners = #el.applicable,
      qualified_corners = qualified,
      qualified_share = share,
      corners = windows,
    }
  end
  return out
end

return M
