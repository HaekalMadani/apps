-- hud.lua — the corner-speed indicator's logic (framing v6's third UI element).
--
-- The other two elements are world-anchored markers standing at a coordinate;
-- this one is a HUD readout, so its hard question is not "where" but "WHICH
-- CORNER, and what do I say about it right now". That decision is pure and lives
-- here; trace_rt.lua does the drawing, exactly as it does for the markers. The
-- CLAUDE.md principle again: rendering swappable, fading independent of it.
--
-- What it shows (impl plan section 7's default, adopted): target-versus-actual
-- minimum corner speed for the UPCOMING annotated corner. Three phases as the
-- car moves through a corner, because a single readout that never changes is
-- not feedback:
--
--   approach   the target speed for the corner ahead, and the car's current
--              speed, so the driver can see how much they still have to lose
--   in_zone    the target, and the running MINIMUM so far -- which is the
--              metric the criterion is actually computed on
--   settled    the target and the achieved minimum, held briefly past the zone
--              so the driver gets to read the result of the corner they just
--              drove rather than losing it the instant they exit
--
-- Nothing here is a criterion. The controller consumes the closed pass's
-- minimum from lib/pass_metrics; this shows the same quantity live, and the
-- band it is judged against, so the two can never disagree about what "on
-- target" means -- both come from the reference table and the same band
-- arithmetic in lib/evaluator.
--
-- Style: plain imperative Lua 5.1, helpers called directly (CSP table-closure
-- gotcha; see CLAUDE.md). No ac.* / ui.* / render.* — headless-testable.

local evaluator = require('lib/evaluator')
local markers = require('lib/markers')

local M = {}

-- How far ahead of a corner-speed zone the readout appears, in metres of track.
-- Long enough to be useful on the approach to a heavy braking zone, short
-- enough that it is unambiguous which corner is meant. The markers' own view
-- cull uses the same idea for the same reason.
local LOOKAHEAD_M = 300.0

-- How far past a zone the achieved minimum stays on screen, in metres. The
-- driver has just finished the corner; taking the number away at the exit gate
-- would make the one moment it means something the one moment it is not there.
local LINGER_M = 80.0

-- --- spline arithmetic (wrap-aware, like everything else in this project) ---

local function forward_span(a, b)
  return (b - a) % 1.0
end

local function in_zone(spline, start, finish)
  return forward_span(start, spline) <= forward_span(start, finish)
end

-- --- plan -------------------------------------------------------------------

-- Precompute, once per block, what the readout needs per corner: the zone to
-- watch, the expert target, and the band the criterion uses. Built from the
-- SAME reference table and the SAME band arithmetic the evaluator uses, so the
-- number on screen and the number in the pass record cannot drift apart.
--
-- A corner in the annotation but not in the reference gets no entry: there is no
-- target to show, and inventing one would be worse than showing nothing.
function M.plans(corners, reference, cfg)
  local ref_by_id = {}
  for i = 1, #reference.corners do
    ref_by_id[reference.corners[i].corner_id] = reference.corners[i]
  end
  local out = {}
  for i = 1, #corners do
    local c = corners[i]
    local ref = ref_by_id[c.id]
    if ref ~= nil then
      local bands = evaluator.bands(cfg, ref)
      out[#out + 1] = {
        corner_id = c.id,
        zone = c.zones.corner_speed,
        target_kmh = ref.corner_speed.mean_kmh,
        band_kmh = bands.corner_speed_kmh,
      }
    end
  end
  return out
end

-- --- per-frame state --------------------------------------------------------

-- Running state the readout needs across frames: which corner's zone we are in
-- and the minimum speed seen inside it. Separate from lib/pass_metrics's
-- accumulator on purpose -- that one is evidence and must follow the pass
-- bracket exactly; this one is a display and may linger past it. Sharing them
-- would tie what the driver sees to what the controller records in a way that
-- would make either one awkward to change.
function M.new()
  return { corner_id = nil, min_kmh = nil, last_corner_id = nil, last_min_kmh = nil }
end

-- Fold one frame into the running minimum. `plans` is M.plans's output.
function M.update(state, plans, car_spline, speed_kmh)
  local inside = nil
  for i = 1, #plans do
    local p = plans[i]
    if in_zone(car_spline, p.zone.start, p.zone["end"]) then
      inside = p
      break
    end
  end

  if inside == nil then
    -- Left the zone: keep the achieved minimum as the "last" result so the
    -- settled phase has something to show, and clear the live accumulator.
    if state.corner_id ~= nil then
      state.last_corner_id = state.corner_id
      state.last_min_kmh = state.min_kmh
      state.corner_id = nil
      state.min_kmh = nil
    end
    return state
  end

  if state.corner_id ~= inside.corner_id then
    state.corner_id = inside.corner_id
    state.min_kmh = speed_kmh
  elseif speed_kmh < state.min_kmh then
    state.min_kmh = speed_kmh
  end
  return state
end

-- --- what to show -----------------------------------------------------------

-- Find the plan whose zone the car is inside, or the nearest one ahead within
-- LOOKAHEAD_M, or the one just left within LINGER_M. Returns (plan, phase,
-- distance_m) or nil.
local function select_corner(plans, state, car_spline, track_length_m)
  local best, best_phase, best_distance = nil, nil, nil
  for i = 1, #plans do
    local p = plans[i]
    if in_zone(car_spline, p.zone.start, p.zone["end"]) then
      return p, 'in_zone', 0.0
    end
    -- Distance to the zone's start, forward along the track.
    local ahead = forward_span(car_spline, p.zone.start) * track_length_m
    if ahead <= LOOKAHEAD_M and (best_distance == nil or ahead < best_distance) then
      best, best_phase, best_distance = p, 'approach', ahead
    end
    -- ...and how far we are PAST its end, for the settled phase.
    local behind = forward_span(p.zone["end"], car_spline) * track_length_m
    if behind <= LINGER_M and p.corner_id == state.last_corner_id
      and (best_distance == nil or behind < best_distance) then
      best, best_phase, best_distance = p, 'settled', behind
    end
  end
  return best, best_phase, best_distance
end

-- Decide the readout for this frame.
--
--   stage = the PRESENTED stage (markers.presented_stage has already applied
--           the block's mode), so 'hidden' here really means draw nothing.
--
-- Returns nil when nothing should be drawn, otherwise:
--   { corner_id, phase, target_kmh, band_kmh, actual_kmh, deviation_kmh,
--     within_band, distance_m, alpha, show_label, show_actual }
--
-- `show_label` / `show_actual` are the HUD's answer to the reduced-salience form
-- question impl plan section 7 asks about the markers, resolved the same way and
-- from the same config value: at `minimal` the reduced readout keeps the target
-- NUMBER and drops the corner label and the achieved/live speed. The reasoning
-- is identical -- a dimmer copy of the whole readout still does the driver's
-- comparing for them, and it is the comparing that has to be internalised.
function M.readout(plans, state, car_spline, speed_kmh, track_length_m, stage, salience)
  local visual = markers.visual(stage, salience)
  if visual.level == 'hidden' then return nil end
  if #plans == 0 or track_length_m == nil or track_length_m <= 0 then return nil end

  local plan, phase, distance = select_corner(plans, state, car_spline, track_length_m)
  if plan == nil then return nil end

  local actual = nil
  if phase == 'in_zone' then
    actual = state.min_kmh
  elseif phase == 'settled' then
    actual = state.last_min_kmh
  else
    actual = speed_kmh
  end

  local out = {
    corner_id = plan.corner_id,
    phase = phase,
    target_kmh = plan.target_kmh,
    band_kmh = plan.band_kmh,
    actual_kmh = actual,
    distance_m = distance,
    alpha = visual.alpha,
    -- At full salience everything shows. At reduced, the form decides -- and
    -- `minimal` keeps only the target the driver is aiming at.
    show_label = visual.label,
    show_actual = visual.cross,
  }
  if actual ~= nil then
    out.deviation_kmh = actual - plan.target_kmh
    -- Only meaningful once the minimum has actually been taken; on the approach
    -- the car is still slowing and "outside the band" would be the normal case.
    if phase ~= 'approach' then
      local d = out.deviation_kmh
      out.within_band = (d < 0 and -d or d) <= plan.band_kmh
    end
  end
  return out
end

return M
