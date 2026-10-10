-- pass_record.lua — builds one corner-pass record matching passes.schema.json.
--
-- The single place that knows the shape of a pass record, in two steps:
--
--   build()   the pass-TRACKING facts, known the moment the exit gate is
--             crossed: identity, timing, validity and the raw inputs to the two
--             validity gates. Called by lib/pass_tracker.
--   attach()  the M4 fields — metrics, criterion booleans, per-corner
--             qualification and the element-level stage — folded in once the
--             evaluator and controller have seen the pass. Called by trace_rt.
--
-- Split that way because they are known at different moments and by different
-- modules, but they still share ONE definition of the record: a record that has
-- not been through attach() is the M2 placeholder shape (every metric an
-- explicit null, nothing qualified, every element at 'full'), which is exactly
-- right for a block with no reference loaded and remains schema-valid.
--
-- Pure: no ac.* / io.*. json.null is the sentinel that survives table storage
-- and serialises to `null` (see lib/json.lua) — a plain nil would make the key
-- vanish, and the schema requires these keys present. That distinction carries
-- meaning here: a null metric is NO EVIDENCE (the controller drops the pass from
-- that element's window entirely), not a failure, so it has to be visible in the
-- log rather than absent from it.
--
-- Style: plain Lua 5.1, helpers called directly (CSP table-closure gotcha).

local json = require('lib/json')

local M = {}

local ELEMENTS = { "braking", "corner_speed", "apex" }

-- Per-element table with the same value for every element (e.g. all json.null,
-- all false, all "full"). Built fresh each call so records never alias state.
local function per_element(value)
  local t = {}
  for i = 1, #ELEMENTS do
    t[ELEMENTS[i]] = value
  end
  return t
end

-- json.null for a nil number, the number otherwise.
local function or_null(v)
  if v == nil then return json.null end
  return v
end

-- Build a pass record. `invalid_reasons` is an array of reason strings (only
-- meaningful when valid == false); omitted from the record when empty so a valid
-- pass carries no reasons key.
-- `max_wheels_outside` and `max_collision_depth_m` are the RAW INPUTS to the two
-- validity gates, stamped alongside the verdict so the decision can be
-- reconstructed from the logs alone — the same discipline the brake-initiation
-- sample follows (impl plan section 2.1.4). Without the collision depth a
-- wall_contact flag can only be second-guessed by inference from speed traces.
function M.build(block_id, corner_id, lap, t_entry, t_exit, valid, invalid_reasons,
                 max_wheels_outside, max_collision_depth_m)
  local rec = {
    schema_version = 1,
    block_id = block_id,
    corner_id = corner_id,
    lap = lap,
    t_entry = t_entry,
    t_exit = t_exit,
    valid = valid,
    metrics = {
      brake_initiation_distance_m = json.null,
      brake_initiation = json.null,
      brake_rolling_mean_distance_m = json.null,
      brake_modulation = json.null,
      min_corner_speed_kmh = json.null,
      speed_envelope_deviation_kmh = json.null,
      apex_rms_m = json.null,
    },
    criteria = per_element(json.null),
    braking_gates = { accuracy = json.null, consistency = json.null },
    qualified = per_element(false),
    stage = per_element("full"),
  }
  if invalid_reasons ~= nil and #invalid_reasons > 0 then
    rec.invalid_reasons = invalid_reasons
  end
  if max_wheels_outside ~= nil then rec.max_wheels_outside = max_wheels_outside end
  if max_collision_depth_m ~= nil then rec.max_collision_depth_m = max_collision_depth_m end
  return rec
end

-- Fold the M4 fields into a built record, in place.
--
--   metrics    = lib/pass_metrics.close(...)      (nil-valued where unmeasurable)
--   evaluation = lib/evaluator.evaluate(...)      (criteria + the two braking gates)
--   qualified  = lib/controller.qualified(state, corner_id)
--   stage      = lib/controller.stages(state)
--
-- Note what is recorded even when the pass fed nothing to the controller: a null
-- criterion, a null metric and the gates that produced them. The Gate G2 audit
-- has to be able to tell "the driver failed this corner" from "we never measured
-- it", and only the log can say which.
function M.attach(rec, metrics, evaluation, qualified, stage)
  local m = rec.metrics
  m.brake_initiation_distance_m = or_null(metrics.brake_initiation_distance_m)
  m.min_corner_speed_kmh = or_null(metrics.min_corner_speed_kmh)
  m.apex_rms_m = or_null(metrics.apex_rms_m)
  if metrics.brake_initiation ~= nil then
    m.brake_initiation = {
      t = metrics.brake_initiation.t,
      spline_pos = metrics.brake_initiation.spline_pos,
    }
  end
  if metrics.brake_modulation ~= nil then
    m.brake_modulation = {
      peak = metrics.brake_modulation.peak,
      releases = metrics.brake_modulation.releases,
    }
  end

  if evaluation ~= nil then
    m.speed_envelope_deviation_kmh = or_null(evaluation.speed_envelope_deviation_kmh)
    m.brake_rolling_mean_distance_m = or_null(evaluation.rolling_mean_m)
    for i = 1, #ELEMENTS do
      rec.criteria[ELEMENTS[i]] = or_null(evaluation.criteria[ELEMENTS[i]])
    end
    rec.braking_gates.accuracy = or_null(evaluation.braking_gates.accuracy)
    rec.braking_gates.consistency = or_null(evaluation.braking_gates.consistency)
  end

  if qualified ~= nil then
    for i = 1, #ELEMENTS do
      rec.qualified[ELEMENTS[i]] = qualified[ELEMENTS[i]] and true or false
    end
  end
  if stage ~= nil then
    for i = 1, #ELEMENTS do
      rec.stage[ELEMENTS[i]] = stage[ELEMENTS[i]]
    end
  end
  return rec
end

-- Build one fades_<block>.jsonl record from a controller event. The controller
-- is pure and does not know its block, so the two stamps the schema requires
-- beyond its output are added here — the same seam, and the same reason, as
-- attach() above.
function M.fade_record(block_id, event)
  local rec = {
    schema_version = 1,
    block_id = block_id,
    t = event.t,
    lap = event.lap,
    element = event.element,
    transition = event.transition,
    quorum = {
      qualified_share = event.quorum.qualified_share,
      qualified_corners = event.quorum.qualified_corners,
      applicable_corners = event.quorum.applicable_corners,
      flipped_corners = event.quorum.flipped_corners,
    },
  }
  if event.reversion_count ~= nil then rec.reversion_count = event.reversion_count end
  return rec
end

return M
