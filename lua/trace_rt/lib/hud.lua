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

-- How long before a corner-speed zone the readout appears, and how long after
-- it leaves, in SECONDS OF TRAVEL at the car's current speed -- not metres of
-- track. Same lesson the braking zones learned at M6: a flat metre budget buys
-- 1.1 s at Copse and 1.9 s at corner 4, so the same number means two different
-- things at two corners of one lap.
--
-- WHY THESE ARE SHORT (2026-10-14). They were 300 m of lookahead and 80 m of
-- linger, flat. Measured against the real National annotation that is 1,979 m
-- of a 2,600 m lap: THE READOUT WAS ON SCREEN FOR 76% OF EVERY LAP. A cue that
-- is up three quarters of the time is not a cue, it is furniture -- and it
-- costs the fading manipulation its meaning twice over: the participant stops
-- reading a thing that is always there, and withdrawing it at `reduced` changes
-- the whole screen rather than one corner's worth of help. At 1.5 s / 2.0 s the
-- same lap comes to about 36%, of which 18% is the zones themselves.
--
-- The lookahead is deliberately NOT zero. Inside the zone the car is already at
-- or near its minimum, so a readout that only appears there can report but
-- cannot change anything -- it would be knowledge of results wearing a cue's
-- clothes, and `lib/kr` already does that job properly. 1.5 s is about where
-- the brake point is, which is the last moment the number can still be acted
-- on.
local LOOKAHEAD_S = 1.5
local SETTLED_S = 2.0

-- Floors, for the slow corners and for a car crawling out of a spin: a window
-- scaled from speed alone collapses to nothing at low speed, and the readout
-- would flicker off in the one place a novice most needs it.
local LOOKAHEAD_MIN_M = 30.0
local SETTLED_MIN_M = 25.0

-- Metres of track that `seconds` of travel at `speed_kmh` covers, floored.
local function travel_m(speed_kmh, seconds, floor_m)
  local m = (speed_kmh or 0.0) / 3.6 * seconds
  if m < floor_m then return floor_m end
  return m
end

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
        -- Carried per corner so the readout's colour is decided by the same
        -- gate shape the criterion uses, resolved once from the config at block
        -- start rather than read per frame.
        gate = cfg.criteria.corner_speed_gate,
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
-- the lookahead window, or the one just left within the settled window. Both
-- windows are the car's own speed times a fixed number of seconds. Returns
-- (plan, phase, distance_m) or nil.
local function select_corner(plans, state, car_spline, track_length_m, speed_kmh)
  local lookahead_m = travel_m(speed_kmh, LOOKAHEAD_S, LOOKAHEAD_MIN_M)
  local settled_m = travel_m(speed_kmh, SETTLED_S, SETTLED_MIN_M)
  local best, best_phase, best_distance = nil, nil, nil
  for i = 1, #plans do
    local p = plans[i]
    if in_zone(car_spline, p.zone.start, p.zone["end"]) then
      return p, 'in_zone', 0.0
    end
    -- Distance to the zone's start, forward along the track.
    local ahead = forward_span(car_spline, p.zone.start) * track_length_m
    if ahead <= lookahead_m and (best_distance == nil or ahead < best_distance) then
      best, best_phase, best_distance = p, 'approach', ahead
    end
    -- ...and how far we are PAST its end, for the settled phase.
    local behind = forward_span(p.zone["end"], car_spline) * track_length_m
    if behind <= settled_m and p.corner_id == state.last_corner_id
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
--
-- `show_actual` gates the COLOUR-CODED BOX as well as the number in it
-- (2026-10-15): the box *is* the live-speed display, and its fill colour is the
-- in-band verdict, so showing the box at `minimal` would hand back exactly the
-- comparison `minimal` exists to withdraw. The semantics are therefore
-- unchanged by the redesign -- full salience shows the live number and the
-- verdict, `minimal` shows the target and neither -- which matters because
-- `salience.reduced_form` is frozen config and an RQ3 interview topic.
function M.readout(plans, state, car_spline, speed_kmh, track_length_m, stage, salience)
  local visual = markers.visual(stage, salience)
  if visual.level == 'hidden' then return nil end
  if #plans == 0 or track_length_m == nil or track_length_m <= 0 then return nil end

  local plan, phase, distance = select_corner(plans, state, car_spline,
                                              track_length_m, speed_kmh)
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
      -- Asked of lib/evaluator rather than restated here. The readout and the
      -- criterion must not be two rules about one number: the gate's shape
      -- changed on 2026-10-14 (slow side only -- carrying more speed than the
      -- reference is no longer a failure), and a duplicated comparison here
      -- would have gone on colouring a fast pass red while the pass record said
      -- it met the criterion. Note what `within_band` now means for this
      -- element: "met the criterion", not "between two edges".
      out.within_band = evaluator.corner_speed_ok(out.deviation_kmh,
                                                  plan.band_kmh, plan.gate)
    end
  end
  return out
end

-- --- screen layout ----------------------------------------------------------

-- Where the readout sits on screen and how big its lines are, as pure
-- arithmetic from the AC window size.
--
-- It lives here, with the rest of the decisions, for the reason the whole
-- renderer/decision split exists: this is the one element a participant stares
-- at, and its geometry is part of the instrument. It must be the same for every
-- participant at every resolution, which it cannot be while it is an app window
-- somebody drags into place -- the first cue window was never opened at all, and
-- imgui would have persisted whatever size it was first given.
--
-- Two properties the arithmetic has to have:
--
--   * everything scales with the window HEIGHT, so the cue subtends the same
--     angle at the same seating distance whatever the display is;
--   * the block GROWS DOWNWARD from a fixed top. A KR message appearing must
--     not move the speed readout under the driver's eyes, which is the same
--     reason manifest.ini keeps the cue window fixed-size instead of
--     AUTO_RESIZE.
--
-- Centre of the UPPER half (2026-10-15, from the dry run). It was centre-bottom
-- per impl plan section 7, which put it straight into the stock HUD's territory
-- -- the speedometer, the gear and the pedal bars all live along the bottom of
-- an AC screen, so the one element a participant is meant to stare at was
-- competing with native instruments for the same strip of screen. Above the
-- horizon it has that strip to itself. It stays horizontally centred.
--
-- A SECOND property the arithmetic has to have, added with the box below:
-- `box_w` is FIXED, not measured from the text. A box sized to its contents
-- changes width when the speed crosses 100 km/h, which is a twitch at exactly
-- the moment the driver is reading it -- the same class of fault as a
-- resizing cue window, and the reason manifest.ini pins SIZE.
function M.layout(screen_w, screen_h)
  local h = screen_h or 0
  if h < 320 then h = 320 end
  return {
    centre_x = (screen_w or 0) * 0.5,
    top_y = h * 0.17,
    size_label = h * 0.019,
    -- The CURRENT speed, inside the box: the big number now. The target used to
    -- hold this size and the dry run found it was taking the attention the live
    -- number should have -- the driver needs to read what they are doing, and
    -- know the target by having been shown it.
    size_speed = h * 0.044,
    -- The target, as a caption just OUTSIDE the bottom of the box. Small on
    -- purpose: reference, not focus.
    size_target = h * 0.020,
    size_kr = h * 0.026,
    line_gap = h * 0.004,
    box_w = h * 0.150,
    box_h = h * 0.062,
    box_radius = h * 0.008,
    box_border = math.max(1.0, h * 0.0015),
  }
end

return M
