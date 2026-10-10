-- sampler.lua — pure sampling/serialisation logic for the 20 Hz per-tick log.
--
-- This is the headless-testable half of impl-plan module 2 ("Sampler"). It owns
-- NO ac.* / io.* / render.* — those live in trace_rt.lua, which reads car state
-- each frame, builds a plain `snapshot` table, and hands it here. Keeping the
-- arithmetic pure is what lets kit/tests run it under lupa (LuaJIT 2.1), exactly
-- as the M0 validator does.
--
-- Two responsibilities:
--   1. Downsampling — a fixed-step accumulator that turns a variable per-frame
--      dt stream into a steady tick cadence (default 20 Hz) independent of the
--      render frame rate.
--   2. CSV serialisation — header + one row per tick, column order and types
--      driven entirely by the decoded configs/ticks_columns.json descriptor, so
--      the file the runtime writes and the file trace-kit validates can never
--      drift apart.
--
-- Style: plain imperative Lua, helpers called directly (never stored in tables
-- and dispatched as t.fn(...) — that pattern crashes in-game; see CLAUDE.md).
-- Pure Lua 5.1.

local M = {}

-- ---------------------------------------------------------------------------
-- 1. Downsampling
-- ---------------------------------------------------------------------------

-- Create accumulator state for a given tick rate (Hz). Stored in a plain table;
-- the caller owns it and passes it back into tick().
function M.new(tick_rate_hz)
  if type(tick_rate_hz) ~= "number" or tick_rate_hz <= 0 then
    error("sampler.new: tick_rate_hz must be a positive number")
  end
  return {
    period = 1.0 / tick_rate_hz,  -- seconds between ticks
    acc = 0.0,                    -- unspent time carried between frames
  }
end

-- Advance the accumulator by one frame's dt and return how many ticks are due
-- this frame (0 in the common case of a frame shorter than the period; >1 only
-- if a frame ran longer than the tick period). The carry keeps the long-run
-- cadence exact rather than drifting with frame time. dt <= 0 (paused frame)
-- contributes nothing, so paused time is simply not logged.
function M.tick(state, dt)
  if type(dt) ~= "number" or dt <= 0 then return 0 end
  state.acc = state.acc + dt
  local n = 0
  -- Guard against a pathological dt (huge stall) producing thousands of rows:
  -- cap the catch-up at a small number; a real gap is the integrity checker's
  -- job to flag, not the sampler's to paper over.
  while state.acc >= state.period and n < 8 do
    state.acc = state.acc - state.period
    n = n + 1
  end
  if state.acc >= state.period then
    -- We hit the catch-up cap: drop the backlog so we don't drift forever.
    state.acc = 0.0
  end
  return n
end

-- ---------------------------------------------------------------------------
-- 2. CSV serialisation (driven by the ticks_columns descriptor)
-- ---------------------------------------------------------------------------

-- The descriptor is the decoded configs/ticks_columns.json: { schema_version,
-- columns = { { name, type, ... }, ... } }. We only consume `columns`.

-- Comma-separated header line from the column names, in order.
function M.header(descriptor)
  local cols = descriptor.columns
  local names = {}
  for i = 1, #cols do
    names[i] = cols[i].name
  end
  return table.concat(names, ",")
end

-- Format one value per its declared column type. Floats use a fixed 6 decimals
-- (ample for spline ~5 mm, world position sub-mm) so the CSV is plain and
-- locale-independent; ints are %d; bools are 0/1. A missing or wrong-typed
-- value is a programming error and raises — the log must never silently carry
-- a blank or a guessed default.
local function format_value(col, v)
  local t = col.type
  if t == "float" then
    if type(v) ~= "number" then
      error("sampler: column '" .. col.name .. "' expected number, got " .. type(v))
    end
    return string.format("%.6f", v)
  elseif t == "int" then
    if type(v) ~= "number" then
      error("sampler: column '" .. col.name .. "' expected number, got " .. type(v))
    end
    return string.format("%d", v)
  elseif t == "bool" then
    if type(v) ~= "boolean" then
      error("sampler: column '" .. col.name .. "' expected boolean, got " .. type(v))
    end
    return v and "1" or "0"
  end
  error("sampler: column '" .. col.name .. "' has unknown type '" .. tostring(t) .. "'")
end

-- Build one CSV row from a snapshot table keyed by column name. Column order
-- follows the descriptor, not the snapshot's table order (Lua tables are
-- unordered). A snapshot missing a declared column raises.
function M.format_row(descriptor, snapshot)
  local cols = descriptor.columns
  local cells = {}
  for i = 1, #cols do
    local col = cols[i]
    local v = snapshot[col.name]
    if v == nil then
      error("sampler: snapshot missing column '" .. col.name .. "'")
    end
    cells[i] = format_value(col, v)
  end
  return table.concat(cells, ",")
end

return M
