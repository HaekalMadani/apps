-- markers.lua — pure marker geometry and salience logic (impl-plan module 6).
--
-- Turns a loaded reference table into a flat draw list, and answers the two
-- questions the renderer asks each frame: *which* markers are in view, and at
-- *what* alpha. It owns NO render.* / ac.* / io.* — trace_rt.lua's draw3d walks
-- the list this module builds and issues the actual render calls. That split is
-- the CLAUDE.md principle "keep rendering swappable and fading independent of
-- it": the Python->Lua renderer swap was cheap precisely because nothing but the
-- draw calls knew about the renderer, and the fading is just an alpha the
-- controller sets.
--
-- Marker world positions are precomputed once per corner from the expert
-- reference — never hardcoded, never derived at run time from the car. At run
-- time the controller only sets a stage; this module maps stage -> what is
-- drawn, and the drawing itself is trace_rt.lua's draw3d.
--
-- Style: plain imperative Lua 5.1, helpers called directly (never stored in
-- tables and dispatched as t.fn(...) — that crashes in CSP in-game; see
-- CLAUDE.md). Headless-testable through lupa, like every other lib/ module.

local M = {}

-- --- draw list --------------------------------------------------------------

-- Flatten a validated reference table into markers, in corner order.
-- Each entry: { element = 'braking'|'apex', corner_id, spline, x, y, z }.
--
-- A corner with no braking zone contributes no braking marker at all: it is not
-- applicable to the braking-point element (no marker, no criterion, out of that
-- element's quorum denominator). A compound corner contributes one apex marker
-- per apex gate, even though it yields only one apex criterion per pass.
function M.build(reference)
  local out = {}
  local corners = reference.corners
  for i = 1, #corners do
    local c = corners[i]
    if c.braking ~= nil then
      out[#out + 1] = {
        element = 'braking',
        corner_id = c.corner_id,
        spline = c.braking.spline_pos,
        x = c.braking.world_pos[1],
        y = c.braking.world_pos[2],
        z = c.braking.world_pos[3],
      }
    end
    local gates = c.apex.gates
    for g = 1, #gates do
      out[#out + 1] = {
        element = 'apex',
        corner_id = c.corner_id,
        spline = gates[g].spline_pos,
        x = gates[g].world_pos[1],
        y = gates[g].world_pos[2],
        z = gates[g].world_pos[3],
      }
    end
  end
  return out
end

-- --- salience ---------------------------------------------------------------
--
-- Three steps, deliberately separate, because they answer different questions
-- and change for different reasons:
--
--   presented_stage(mode, stage)  the CONDITION switch: what the participant is
--                                 shown, given what the controller decided.
--   level_of(stage)               stage -> salience LEVEL (full/reduced/hidden).
--   visual(stage, salience)       level -> the drawing description.
--
-- Keeping them apart is the CLAUDE.md principle in practice: the controller
-- knows nothing about drawing, the renderer knows nothing about evidence, and
-- the experiment's condition is a config field rather than a code path.

-- What the participant is shown for an element, given the block's mode and the
-- controller's stage for it (impl plan section 5: "the condition is a config
-- field, not a code path").
--
--   adaptive  the controller's stage, as computed
--   static    pinned at full salience -- the pipeline still runs and the
--             controller still computes and LOGS its stage invisibly, so static
--             blocks produce the same per-pass records as adaptive ones
--   off       nothing rendered at all (sessions 1 and 3); the controller still
--             runs, for the same reason
--
-- The controller's own stage is never rewritten by this: only what is drawn.
-- The pass record keeps logging the real stage, which is what makes the
-- static-condition trajectory analysable at all.
function M.presented_stage(mode, stage)
  if mode == 'off' then return 'hidden' end
  if mode == 'static' then return 'full' end
  return stage
end

-- Salience level for a controller stage. `probe` and `removed` are both hidden:
-- a probe IS the withdrawal, and removal is its permanent form. They stay
-- distinct in the controller and in the logs, where the difference matters, and
-- collapse only here, where it does not.
function M.level_of(stage)
  if stage == 'probe' or stage == 'removed' or stage == 'hidden' then return 'hidden' end
  if stage == 'reduced' then return 'reduced' end
  return 'full'
end

-- Alpha for a salience LEVEL. The constants live in controller_config.json (one
-- source of constants); this only selects between them.
function M.alpha(level, salience)
  if level == 'hidden' then return 0.0 end
  if level == 'reduced' then return salience.reduced_alpha end
  return salience.full_alpha
end

-- The full drawing description for a controller stage: what alpha, and which
-- parts of the cue survive.
--
-- The reduced-salience FORM was the open decision impl plan section 7 left for
-- M5. Its default -- and the study's choice -- is `minimal`: the disc alone at
-- reduced alpha, with the label and the vertical stalk removed. The reasoning
-- is that reducing salience should reduce how much the cue TELLS you, not just
-- how bright it is: a dimmer copy of the same annotated marker still hands the
-- learner the corner id and a precise point, so it tests less than it looks.
-- Stripping to the disc leaves a positional hint and takes away the reading.
--
-- The alternatives section 7 lists are kept as config values rather than deleted
-- (`salience.reduced_form`), because the choice is an RQ3 interview topic and
-- has to be frozen and hashed before the pilot -- and because "pick by eye on
-- track" is much easier when it is not a code edit:
--
--   minimal       disc only                      (the default, and the choice)
--   intermediate  disc + cross, no stalk/label
--   dimmed        everything, just at lower alpha
--
-- `dimmed` exists mainly as the control case for the argument above: it is what
-- "reduced salience" would mean if it meant brightness alone.
function M.visual(stage, salience)
  local level = M.level_of(stage)
  local v = {
    stage = stage,
    level = level,
    alpha = M.alpha(level, salience),
    disc = false, cross = false, stalk = false, label = false,
  }
  if level == 'hidden' then return v end
  if level == 'full' then
    v.disc, v.cross, v.stalk, v.label = true, true, true, true
    return v
  end
  local form = salience.reduced_form or 'minimal'
  if form == 'dimmed' then
    v.disc, v.cross, v.stalk, v.label = true, true, true, true
  elseif form == 'intermediate' then
    v.disc, v.cross = true, true
  else
    v.disc = true
  end
  return v
end

-- --- view culling -----------------------------------------------------------

-- Forward distance along the track from `from` to `to`, in spline units [0, 1).
local function forward_span(from, to)
  return (to - from) % 1.0
end

-- True if a marker should be drawn for a car at `car_spline`.
--
-- Without this every marker on the circuit draws every frame: a braking cue for
-- a corner a kilometre away is visual noise at best and a misleading cue at
-- worst, and the study's claim is about a cue for the corner being approached.
-- Distances are in metres of track length, so the window is track-independent.
-- `behind_m` keeps a marker visible slightly past it rather than blinking out
-- at the moment the car crosses it.
function M.in_view(marker_spline, car_spline, track_length_m, ahead_m, behind_m)
  local ahead = forward_span(car_spline, marker_spline) * track_length_m
  if ahead <= ahead_m then return true end
  local behind = forward_span(marker_spline, car_spline) * track_length_m
  return behind <= behind_m
end

return M
