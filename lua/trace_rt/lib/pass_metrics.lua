-- pass_metrics.lua — per-frame sample stream -> one closed pass's raw metrics.
--
-- The M2 seam, filled in at M4. lib/pass_tracker.lua answers "is a pass open?";
-- this answers "what did the driver do inside it?", producing the three numbers
-- lib/evaluator.lua turns into criterion booleans:
--
--   brake_initiation_distance_m   signed metres from the expert brake point
--                                 (POSITIVE = earlier than the reference)
--   min_corner_speed_kmh          minimum over the annotated corner-speed zone
--   apex_rms_m                    RMS lateral deviation from the expert LINE
--                                 over the corner's apex window(s)
--
-- ---------------------------------------------------------------------------
-- Why this is streaming, and why that is not an optimisation
-- ---------------------------------------------------------------------------
--
-- The offline extractor (kit/trace_kit/reference.py) has every sample of a pass
-- in a list and can scan it freely. In the game the same job runs inside the
-- render loop, per frame, on up to a handful of simultaneously open corners.
-- Buffering every sample of every open pass would churn thousands of small
-- tables per second through the Lua GC on the hot path, which is exactly the
-- frame cost the M1 exit test was built to protect. Every accumulator below is
-- therefore O(1) per sample: a brake-initiation detector with one pending
-- candidate, a running minimum, and a cursor walking each apex line.
--
-- ---------------------------------------------------------------------------
-- Parity with the extractor is the whole point
-- ---------------------------------------------------------------------------
--
-- The reference table says where the expert braked and what line they took; the
-- criteria compare a participant against it. If the runtime detects the
-- brake-initiation EVENT differently from the extractor that built the
-- reference, the comparison is between two different measurements and every
-- band is quietly wrong. So each detector here is written to reproduce its
-- offline counterpart exactly, and kit/tests/test_m4_pass_metrics.py pins them
-- against each other over a shared corpus — the same discipline that already
-- pins forward_crossed() to the extractor's copy.
--
-- One difference is deliberate and noted where it happens: a compound corner
-- whose pass covers some apex windows but not all yields NO apex value here,
-- where the extractor keeps the covered gates. A partial union is not
-- comparable to the reference's mean_rms_m, which was built over the whole
-- union. Every corner in both study annotations has exactly one apex gate, so
-- the two behave identically on the study's own data.
--
-- Style: plain imperative Lua 5.1, helpers called directly (CSP table-closure
-- gotcha; see CLAUDE.md). No ac.* / io.* / render.* — headless-testable.

local M = {}

-- --- spline arithmetic ------------------------------------------------------
--
-- The spline wraps 1 -> 0 at start/finish and annotated zones may straddle the
-- line, so nothing below subtracts spline positions directly. These mirror
-- trace_kit.reference's forward_span / signed_delta / in_zone.

-- Forward distance from `a` to `b`, always in [0, 1).
local function forward_span(a, b)
  return (b - a) % 1.0
end

-- Shortest signed delta a -> b, in (-0.5, 0.5].
local function signed_delta(a, b)
  return ((b - a + 0.5) % 1.0) - 0.5
end

-- True if `spline` lies in the forward interval [start, finish], wrap included.
local function in_zone(spline, start, finish)
  return forward_span(start, spline) <= forward_span(start, finish)
end

-- A backward step larger than this is a forward wrap over start/finish, not the
-- car reversing. Same separator, for the same reason, as pass_tracker's
-- WRAP_THRESHOLD and the extractor's pass_axis.
local WRAP_THRESHOLD = 0.5

-- --- plans ------------------------------------------------------------------

-- Precompute, once per block, everything a corner's metric accumulation needs:
-- the annotated zones and the expert data the metrics are measured against.
-- Nothing here is recomputed per frame, and nothing is a hardcoded coordinate.
--
--   corners        = the annotation's `corners` array
--   reference      = the loaded reference table
--   track_length_m = ac.getSim().trackLengthM
--   cfg            = controller_config (brake threshold + debounce)
--
-- Returns corner_id -> plan. A corner present in the annotation but missing
-- from the reference gets no plan: without expert data there is nothing to
-- measure against, and inventing a datum would be worse than a null metric.
function M.plans(corners, reference, track_length_m, cfg)
  local ref_by_id = {}
  for i = 1, #reference.corners do
    ref_by_id[reference.corners[i].corner_id] = reference.corners[i]
  end

  local out = {}
  for i = 1, #corners do
    local c = corners[i]
    local ref = ref_by_id[c.id]
    if ref ~= nil then
      local plan = {
        corner_id = c.id,
        track_length_m = track_length_m,
        brake_threshold = cfg.brake_initiation.threshold,
        brake_debounce_s = cfg.brake_initiation.debounce_ms / 1000.0,
        corner_speed_zone = c.zones.corner_speed,
        apex_lines = {},
      }
      -- Braking is measured only where BOTH the annotation has a zone to search
      -- and the reference has a point to measure from.
      if c.zones.braking ~= nil and ref.braking ~= nil then
        plan.braking_zone = c.zones.braking
        plan.brake_ref_spline = ref.braking.spline_pos
      end
      -- The apex line comes straight off the reference table, at the spline
      -- stations the extractor sampled. Rebuilding the grid here from
      -- apex_window_half_m would be a second implementation of the same
      -- arithmetic, and any drift between them would silently compare the
      -- driver against stations the expert line was never measured at.
      for g = 1, #ref.apex.gates do
        plan.apex_lines[g] = ref.apex.gates[g].line
      end
      out[c.id] = plan
    end
  end
  return out
end

-- --- accumulation -----------------------------------------------------------

-- Begin accumulating a pass. `snap` is the entry sample (the same one the
-- tracker opened on); the caller feeds it back through M.update afterwards.
function M.open(plan, snap)
  local st = {
    plan = plan,
    start_spline = snap.spline,
    axis = 0.0,                 -- monotone forward distance from the entry sample
    prev = nil,                 -- previous sample: { axis, x, y, z }
    -- braking
    candidate = nil,            -- pending sustained-brake candidate
    brake_init = nil,           -- confirmed { t, spline }
    brake_peak = 0.0,
    brake_releases = 0,
    brake_was_above = false,
    -- corner speed
    min_speed = nil,
    -- apex: one cursor per gate line
    gates = {},
  }
  local lines = plan.apex_lines
  for g = 1, #lines do
    local grid = {}
    for k = 1, #lines[g] do
      grid[k] = forward_span(st.start_spline, lines[g][k].spline_pos)
    end
    st.gates[g] = { line = lines[g], grid = grid, idx = 1, se = 0.0, n = 0 }
  end
  return st
end

-- Fold one apex grid point into a gate's running squared error, interpolating
-- the car's position between the two samples that bracket it.
--
-- Horizontal (X/Z) only: at a fixed spline the two positions share a
-- longitudinal station, so their separation IS the lateral error, and an
-- elevation difference is not line error. Same reasoning as the extractor's
-- rms_lateral.
local function accumulate_gate(gate, k, f, prev, snap)
  local x = prev.x + f * (snap.pos_x - prev.x)
  local z = prev.z + f * (snap.pos_z - prev.z)
  local ref = gate.line[k].world_pos
  local dx, dz = x - ref[1], z - ref[3]
  gate.se = gate.se + dx * dx + dz * dz
  gate.n = gate.n + 1
end

-- Advance by one sample. `snap` carries: t, spline, brake, speed_kmh,
-- pos_x, pos_y, pos_z.
function M.update(st, snap)
  local plan = st.plan

  -- --- the monotone pass axis (mirrors the extractor's pass_axis) ---
  local d = forward_span(st.start_spline, snap.spline)
  -- A sample a hair BEHIND the anchor — spline jitter at the entry gate — would
  -- otherwise wrap to ~1.0 and look like most of a lap.
  if d > WRAP_THRESHOLD then d = 0.0 end
  if d < st.axis then d = st.axis end

  -- --- braking ---
  local brake = snap.brake or 0.0
  if brake > st.brake_peak then st.brake_peak = brake end
  if plan.braking_zone ~= nil then
    local above = brake >= plan.brake_threshold
    if st.brake_init == nil then
      if above then
        if st.candidate == nil and in_zone(snap.spline, plan.braking_zone.start, plan.braking_zone["end"]) then
          st.candidate = { t = snap.t, spline = snap.spline }
        end
        -- The zone bounds where the event is SEARCHED for, not where braking
        -- must stay: a trail-braking driver is legitimately still on the
        -- brakes past the zone's end, so the hold is checked over the rest of
        -- the pass.
        if st.candidate ~= nil and (snap.t - st.candidate.t) >= plan.brake_debounce_s then
          st.brake_init = st.candidate
        end
      else
        -- Released before the debounce elapsed: a pedal tap, not an
        -- initiation. Drop the candidate and keep scanning.
        st.candidate = nil
      end
    elseif st.brake_was_above and not above then
      -- Descriptive only (framing v6 logs modulation and does not gate on it).
      st.brake_releases = st.brake_releases + 1
    end
    st.brake_was_above = above
  end

  -- --- minimum corner speed ---
  if in_zone(snap.spline, plan.corner_speed_zone.start, plan.corner_speed_zone["end"]) then
    if st.min_speed == nil or snap.speed_kmh < st.min_speed then
      st.min_speed = snap.speed_kmh
    end
  end

  -- --- apex line ---
  local prev = st.prev
  if prev ~= nil and d > prev.axis then
    for g = 1, #st.gates do
      local gate = st.gates[g]
      -- The grid is in driving order, so one forward cursor covers it. A frame
      -- long enough to step over several stations consumes them all.
      while gate.idx <= #gate.grid do
        local gd = gate.grid[gate.idx]
        if gd < prev.axis or gd > d then break end
        accumulate_gate(gate, gate.idx, (gd - prev.axis) / (d - prev.axis), prev, snap)
        gate.idx = gate.idx + 1
      end
    end
  end

  st.axis = d
  st.prev = { axis = d, x = snap.pos_x, y = snap.pos_y, z = snap.pos_z }
  return st
end

-- Finish a pass and return its metrics. Every field may be nil: a nil metric is
-- NO EVIDENCE (the pass simply does not enter that element's evidence window),
-- never a failure — see rule 4 in lib/controller.lua.
--
--   { brake_initiation_distance_m, brake_initiation = { t, spline_pos },
--     brake_modulation = { peak, releases },
--     min_corner_speed_kmh, apex_rms_m }
function M.close(st)
  local plan = st.plan
  local out = { brake_modulation = { peak = st.brake_peak, releases = st.brake_releases } }

  if st.brake_init ~= nil then
    out.brake_initiation = { t = st.brake_init.t, spline_pos = st.brake_init.spline }
    -- Signed forward distance FROM the driver's brake point TO the expert's:
    -- positive when the driver braked earlier, which is the sign convention
    -- passes.schema.json states and the direction novice error runs in.
    out.brake_initiation_distance_m =
      signed_delta(st.brake_init.spline, plan.brake_ref_spline) * plan.track_length_m
  end

  out.min_corner_speed_kmh = st.min_speed

  -- Apex: one value per pass, over the UNION of the corner's windows. A window
  -- the pass did not cover completely yields no value at all rather than a
  -- partial one — a partial union is not comparable with the reference's
  -- mean_rms_m, which was built over the whole union.
  local se, n, complete = 0.0, 0, (#st.gates > 0)
  for g = 1, #st.gates do
    local gate = st.gates[g]
    if gate.idx <= #gate.grid then
      complete = false
    else
      se = se + gate.se
      n = n + gate.n
    end
  end
  if complete and n > 0 then
    out.apex_rms_m = math.sqrt(se / n)
  end

  return out
end

return M
