-- pass_tracker.lua — pure corner-pass detection state machine (impl-plan §2.1.3).
--
-- Watches the car's normalized spline position against each annotated corner's
-- entry/exit gates and emits exactly one pass record per corner per lap. It owns
-- NO ac.* / io.*: trace_rt.lua reads car state, builds a plain `snap` table once
-- per 20 Hz tick (the same cadence as the ticks log) and feeds it here. That
-- purity is what lets kit/tests drive it headless under lupa (LuaJIT 2.1).
--
-- What M2 detects: gate crossings + per-pass validity. What it does NOT do:
-- metrics, criteria, qualification, controller stage — those are M4. Each closed
-- pass becomes a schema-valid record via lib/pass_record (placeholders for the
-- M4 fields). The in-zone raw-sample accumulation the evaluator will need is the
-- documented M4 seam; M2 deliberately does not buffer metric samples.
--
-- Two hazards this module exists to get right (the M2 exit test + risk register):
--   1. The spline wraps 1->0 at start/finish, and zones may straddle the line
--      (a corner with entry_gate 0.97, exit_gate 0.03 like the fixture's T4).
--      forward_crossed() distinguishes a real forward wrap from a small backward
--      jitter by the size of the jump.
--   2. Spline jitter at a gate must not double-count. A corner is `armed` (ready
--      to open) only until its entry fires, and re-arms only after its exit, so
--      oscillating across a gate yields a single pass.
--
-- Style: plain imperative Lua 5.1, helpers called directly (never stored in
-- tables and dispatched as t.fn(...) — that crashes in CSP in-game; see CLAUDE.md
-- and lib/validate.lua).

local pass_record = require('lib/pass_record')

local M = {}

-- --- tunables (M2 protocol constants) ---------------------------------------
-- A pass is invalidated when this many wheels leave the track surface at any
-- sample inside it. 3 == AC's standard "more than two wheels off" track-limits
-- rule. These are pass-tracking/validity constants, NOT controller/golden-trace
-- parameters, so they live here for M2; promote to controller_config at the M4
-- config freeze if the protocol wants them tunable per study.
local WHEELS_OUTSIDE_INVALID_MIN = 3

-- Minimum collision depth (metres) that counts as WALL CONTACT for validity.
--
-- Not zero, deliberately. The eval plan invalidates a lap when "the car
-- contacts a wall"; `collisionDepth > 0` reads that far too literally and fires
-- on any contact of any depth. The first International reference block flagged
-- 6 of 13 passes at corner 5 as wall_contact while the car never put a wheel
-- off and lost no speed at all (min speed 74.5-75.1 km/h on flagged and clean
-- passes alike) — the AI's floor grazing the kerb through a compound corner,
-- which is fast driving, not an incident. A real barrier strike is both deep
-- and expensive in speed.
--
-- PROVISIONAL. `max_collision_depth_m` is now stamped into every pass record,
-- so this threshold is calibrated from observed distributions at Gate G0 rather
-- than left as a guess. Like WHEELS_OUTSIDE_INVALID_MIN it is a pass-validity
-- constant, not a controller/golden-trace parameter, so it lives here for now;
-- promote both to controller_config at the M4 config freeze if the protocol
-- wants them tunable per study.
local WALL_CONTACT_DEPTH_M = 0.05

-- A backward spline change larger than this is read as a forward wrap over the
-- start/finish line rather than the car physically reversing. At 20 Hz even
-- 300 km/h on a short track moves < 0.001 spline per tick, so 0.5 is a wide,
-- safe separator between "jittered/reversed a little" and "crossed the line".
local WRAP_THRESHOLD = 0.5

-- --- gate crossing ----------------------------------------------------------

-- True iff driving forward from `prev` to `cur` (consecutive samples) passes
-- through `gate`. Forward = the normal increasing-spline direction, including
-- the single 1->0 wrap per lap. `gate` is hit inclusively at `cur` and
-- exclusively at `prev` (so sitting exactly on a gate does not re-trigger it).
function M.forward_crossed(prev, cur, gate)
  if cur >= prev then
    -- Monotonic forward step (the common case). A jump bigger than the wrap
    -- threshold would mean the car went *backward* across the line; no forward
    -- crossing of an ordinary gate in that frame.
    if (cur - prev) > WRAP_THRESHOLD then return false end
    return prev < gate and gate <= cur
  else
    -- cur < prev: either a forward wrap over start/finish or a small reverse.
    if (prev - cur) > WRAP_THRESHOLD then
      -- Forward arc prev -> 1.0 -> 0.0 -> cur; gate lies in (prev,1] or [0,cur].
      return gate > prev or gate <= cur
    end
    return false  -- small backward movement: no forward crossing
  end
end

-- --- construction -----------------------------------------------------------

-- Build tracker state from an annotation's `corners` array and the owning
-- block_id (stamped into every emitted record). Corner order is preserved.
function M.new(corners, block_id)
  local state = {
    block_id = block_id,
    start_lap = nil,     -- lap recording began on (set on first update)
    prev_spline = nil,   -- previous tick's spline (set on first update)
    corners = {},
  }
  for i = 1, #corners do
    local c = corners[i]
    state.corners[i] = {
      id = c.id,
      entry_gate = c.entry_gate,
      exit_gate = c.exit_gate,
      armed = true,    -- ready to open a pass
      open = false,    -- a pass is in progress
      t_entry = nil,
      entry_lap = nil,
      worst_wheels = 0,
      saw_pit = false,
      worst_collision = 0,   -- deepest collision this pass, metres
    }
  end
  return state
end

-- --- per-pass validity ------------------------------------------------------

-- Fold one sample's hazards into an open corner's accumulators.
local function accumulate(c, snap)
  local w = snap.wheels_outside or 0
  if w > c.worst_wheels then c.worst_wheels = w end
  if snap.in_pit then c.saw_pit = true end
  -- Keep the DEPTH, not a boolean: the validity gate is a threshold on it, and
  -- the raw value is stamped into the pass record so the decision stays
  -- auditable from the logs alone.
  local d = snap.collision_depth or 0
  if d > c.worst_collision then c.worst_collision = d end
end

-- Assemble the ordered invalid_reasons list for a corner about to close.
-- `extra` is an optional leading reason (e.g. "incomplete" on block end).
local function invalid_reasons(state, c, extra)
  local reasons = {}
  if extra ~= nil then reasons[#reasons + 1] = extra end
  if c.worst_wheels >= WHEELS_OUTSIDE_INVALID_MIN then reasons[#reasons + 1] = "wheels_outside" end
  if c.worst_collision >= WALL_CONTACT_DEPTH_M then reasons[#reasons + 1] = "wall_contact" end
  if c.saw_pit then reasons[#reasons + 1] = "pit_transition" end
  if c.entry_lap == state.start_lap then reasons[#reasons + 1] = "first_lap" end
  return reasons
end

local function reset_pass(c)
  c.worst_wheels = 0
  c.saw_pit = false
  c.worst_collision = 0
  c.t_entry = nil
  c.entry_lap = nil
end

local function close_record(state, c, t_exit, extra)
  local reasons = invalid_reasons(state, c, extra)
  local valid = (#reasons == 0)
  return pass_record.build(state.block_id, c.id, c.entry_lap, c.t_entry, t_exit, valid, reasons,
    c.worst_wheels, c.worst_collision)
end

-- --- update -----------------------------------------------------------------

-- Advance the tracker by one tick. `snap` carries: spline, lap, t,
-- wheels_outside, in_pit (bool), collision_depth (number, metres). Returns a list of events,
-- each { kind = "open"|"close", corner_id = <id>, record = <table?> } (record
-- present only on close). The first call only seeds prev_spline/start_lap (no
-- crossing can be known without a previous sample) and returns no events.
function M.update(state, snap)
  if state.prev_spline == nil then
    state.start_lap = snap.lap
    state.prev_spline = snap.spline
    return {}
  end

  local events = {}
  local prev = state.prev_spline
  local cur = snap.spline

  for i = 1, #state.corners do
    local c = state.corners[i]

    if c.open then
      accumulate(c, snap)
      if M.forward_crossed(prev, cur, c.exit_gate) then
        local rec = close_record(state, c, snap.t, nil)
        c.open = false
        c.armed = true
        reset_pass(c)
        events[#events + 1] = { kind = "close", corner_id = c.id, record = rec }
      end
    elseif c.armed and M.forward_crossed(prev, cur, c.entry_gate) then
      c.open = true
      c.armed = false
      c.worst_wheels = 0           -- fresh validity accumulators for this pass
      c.saw_pit = false
      c.worst_collision = 0
      c.t_entry = snap.t
      c.entry_lap = snap.lap
      accumulate(c, snap)          -- the entry sample itself counts toward validity
      events[#events + 1] = { kind = "open", corner_id = c.id }
    end
  end

  state.prev_spline = cur
  return events
end

-- Close any still-open passes when the block ends, flagging them incomplete /
-- right-censored. Returns close events. `t_now` stamps t_exit.
function M.close_open(state, t_now)
  local events = {}
  for i = 1, #state.corners do
    local c = state.corners[i]
    if c.open then
      local rec = close_record(state, c, t_now, "incomplete")
      c.open = false
      c.armed = true
      reset_pass(c)
      events[#events + 1] = { kind = "close", corner_id = c.id, record = rec }
    end
  end
  return events
end

return M
