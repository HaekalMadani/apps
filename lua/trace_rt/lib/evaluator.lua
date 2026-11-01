-- evaluator.lua — per-pass competency criteria (impl-plan module 2.1.4).
--
-- Converts one closed pass's raw metrics into the PER-PASS, PER-ELEMENT BOOLEANS
-- the controller's 3-of-4 rule consumes. Nothing window-level leaves this
-- module: v5's "variance below threshold over the qualification window" gate was
-- withdrawn in v6 because it cannot be a per-pass boolean and a variance from
-- 3-4 samples is a coin flip in both directions.
--
-- Like the controller, this exists twice (kit/trace_kit/evaluator.py) and is
-- pinned by the golden-trace parity suite. It is pure arithmetic: reference
-- table in, config in, metrics in, booleans out. The messy half — turning a
-- stream of per-frame car samples INTO those metrics — lives in
-- lib/pass_metrics.lua, which has no counterpart offline because offline that
-- job belongs to trace_kit.reference.
--
-- Style: plain imperative Lua 5.1, helpers called directly (CSP table-closure
-- gotcha; see CLAUDE.md).
--
-- ---------------------------------------------------------------------------
-- The three criteria (framing v6)
-- ---------------------------------------------------------------------------
--
-- Every band is FLOORED and SOURCE-DEPENDENT:
--
--     band = max(sigma_ref x EVM_source, floor)
--
-- The EVM compensates for the AI reference's missing motor noise (Cohen &
-- Sternad, 2009: inherent motor noise persists at every human skill level), and
-- the floor exists because the AC AI is consistent by construction — sigma_ref
-- can be near zero, and any multiple of nearly nothing is still nearly nothing.
-- Which multiplier applies is decided per corner by the reference table's own
-- `source` field, since a human-substituted corner's sigma already contains
-- motor variability and must not be inflated twice. Measured at M3, the study's
-- sigmas sit far under the floors, so in practice the FLOORS set every band —
-- which is what makes floor calibration the load-bearing part of Gate G2.
--
--   BRAKING — two gates, both required for the pass:
--     accuracy:    |distance from the expert brake point| <= band
--     consistency: |distance - rolling mean of this corner's recent passes|
--                  <= consistency_delta_ratio x band
--   Consistency alone is insufficient BY DESIGN: a learner who brakes reliably
--   30 m early sits tight to their own mean (consistent) but outside the band
--   (inaccurate), so the marker stays. On a corner's first pass there is no
--   prior sample, so the consistency gate is vacuously met and the criterion
--   reduces to accuracy for that pass.
--
--   CORNER SPEED — ONE-SIDED from 2026-10-14 (`criteria.corner_speed_gate`):
--   the pass fails only when the minimum is more than a band BELOW the expert's.
--   Carrying MORE speed than the reference is not an error.
--     slow_only:  min corner speed - expert mean >= -band     (the default)
--     two_sided:  |min corner speed - expert mean| <= band     (kept, see below)
--   It was two-sided, justified as "too fast is an error too (the car runs
--   wide)". The shortHUDtest block refuted that on its own data: 15 of 24
--   corner-speed failures were for carrying more speed than the 85% reference,
--   1 of those 15 put a wheel outside (against 2 of 9 on the slow side), and
--   within the fast passes more speed went with a BETTER apex line (r = -0.26).
--   Two further reasons: the apex gate below is already one-sided on exactly
--   this argument, and the metric is a MINIMUM over the corner-speed window --
--   an unsustainably hot entry shows up as a LOWER minimum later in the same
--   window, so the only way to post a high minimum is to have carried the speed
--   through. `two_sided` stays available because it is the comparison case for
--   the argument, and because the residual risk is real: a driver who sustains
--   an over-the-limit minimum and ruins the EXIT is caught only by the apex
--   element and by the pass's own track-limits flags.
--
--   APEX — ONE-SIDED: rms <= mean_rms_m + band. The metric is RMS lateral
--   deviation from the expert LINE over the apex window, i.e. a deviation from
--   an ideal rather than a two-sided quantity about a mean, so the threshold is
--   the reference's own mean RMS plus the band. Driving closer to the expert
--   line than the AI itself managed is not an error.

local M = {}

-- --- applicable corner sets -------------------------------------------------

-- Which corners each element applies to, in reference-table order, ready for
-- controller.new(). A corner with no `braking` entry was annotated without a
-- braking zone (taken flat): no marker, no criterion, and OUT of the braking
-- element's quorum denominator (impl plan section 7). The other two elements
-- apply to every annotated corner.
function M.applicable(reference)
  local out = { braking = {}, corner_speed = {}, apex = {} }
  local corners = reference.corners
  for i = 1, #corners do
    local c = corners[i]
    if c.braking ~= nil then out.braking[#out.braking + 1] = c.corner_id end
    out.corner_speed[#out.corner_speed + 1] = c.corner_id
    out.apex[#out.apex + 1] = c.corner_id
  end
  return out
end

-- Index a reference table's corners by id, so the per-pass path is a lookup
-- rather than a scan.
function M.index_corners(reference)
  local out = {}
  local corners = reference.corners
  for i = 1, #corners do
    out[corners[i].corner_id] = corners[i]
  end
  return out
end

-- --- bands ------------------------------------------------------------------

local function band_for(sigma, evm, floor)
  local scaled = sigma * evm
  if scaled > floor then return scaled end
  return floor
end

-- The three tolerance bands for one corner. `braking_m` is nil when the corner
-- has no braking reference. Exposed (not just used internally) because the
-- experimenter panel and the Gate G2 audit both need to see the numbers a
-- criterion was judged against.
--
-- The FLOOR wins every time in practice (the AI's sigma_ref is ~0.02 m, so
-- sigma_ref x 3.0 is ~0.06 m and all 27 bands are floors). Keep the EVM term for
-- the human-substitution path, but do not describe it as a mechanism doing work:
-- see BAND_CALIBRATION_BRIEF.md, 2026-10-14.
function M.bands(cfg, corner_ref)
  -- EVM is chosen by the CORNER's source, never globally: an AI-sourced corner
  -- and a human-substituted one in the same table take different multipliers.
  local evm = (corner_ref.source == 'human') and cfg.evm.human or cfg.evm.ai
  local floors = cfg.band_floors
  local b = {
    corner_speed_kmh = band_for(corner_ref.corner_speed.sigma_ref_kmh, evm, floors.corner_speed_kmh),
    apex_m = band_for(corner_ref.apex.sigma_ref_m, evm, floors.apex_m),
  }
  if corner_ref.braking ~= nil then
    b.braking_m = band_for(corner_ref.braking.sigma_ref_m, evm, floors.braking_m)
  end
  return b
end

-- --- the corner-speed verdict, in one place ---------------------------------

-- Does this deviation from the expert minimum meet the corner-speed criterion?
--
-- A small function for a small comparison, because it has TWO callers and they
-- must never disagree: M.evaluate records the verdict in the pass record, and
-- lib/hud colours the live readout with it. The gate's SHAPE changed on
-- 2026-10-14 and this is the only place in the Lua runtime that knows it.
--
--   gate = 'slow_only' (the default) or 'two_sided'; nil reads as 'slow_only'.
function M.corner_speed_ok(deviation_kmh, band_kmh, gate)
  if gate == 'two_sided' then
    local d = deviation_kmh
    if d < 0 then d = -d end
    return d <= band_kmh
  end
  -- slow_only: only the slow side fails. Deliberately NOT `>= -band or faster`
  -- with a second ceiling -- there is no ceiling, which is the whole decision.
  return deviation_kmh >= -band_kmh
end

-- --- rolling mean (the consistency gate's datum) ----------------------------

-- Mean of a list, or nil when empty.
local function mean_of(list)
  local n = #list
  if n == 0 then return nil end
  local s = 0
  for i = 1, n do s = s + list[i] end
  return s / n
end

-- Append a brake-initiation distance to a corner's history, keeping only the
-- passes that share the qualification window with the NEXT pass — i.e. up to
-- window_passes - 1 entries, the other members of the window the next pass will
-- join. Framing v6 ties the consistency datum to "the same passes that form the
-- qualification window", and the current pass must not be in its own mean or
-- the gate would partly measure the pass against itself.
--
-- Only measured passes are appended: a null distance is no evidence (see the
-- controller's rule 3), so it neither enters the history nor displaces an
-- earlier value from it.
function M.push_history(history, distance_m, window_passes)
  history[#history + 1] = distance_m
  local keep = window_passes - 1
  if keep < 1 then keep = 1 end
  while #history > keep do
    table.remove(history, 1)
  end
  return history
end

-- --- the evaluation ---------------------------------------------------------

-- Judge one closed pass.
--
--   corner_ref = this corner's row of the reference table
--   metrics    = { brake_initiation_distance_m = <number|nil>,
--                  min_corner_speed_kmh        = <number|nil>,
--                  apex_rms_m                  = <number|nil> }
--   history    = this corner's prior brake-initiation distances (oldest first),
--                as maintained by push_history; nil or empty on the first pass
--
-- Returns:
--   { criteria      = { braking = <bool|nil>, corner_speed = <bool|nil>, apex = <bool|nil> },
--     braking_gates = { accuracy = <bool|nil>, consistency = <bool|nil> },
--     rolling_mean_m = <number|nil>,
--     speed_envelope_deviation_kmh = <number|nil>,
--     bands = <as M.bands> }
--
-- A nil criterion means the metric was not measurable on this pass. That is NO
-- EVIDENCE, not a failure: the controller drops such a pass from the element's
-- evidence window entirely (rule 3 in lib/controller.lua).
function M.evaluate(cfg, corner_ref, metrics, history)
  local bands = M.bands(cfg, corner_ref)
  local criteria = {}
  local gates = {}
  local out = { criteria = criteria, braking_gates = gates, bands = bands }

  -- --- braking: accuracy AND consistency ---
  local d = metrics.brake_initiation_distance_m
  if corner_ref.braking ~= nil and d ~= nil then
    gates.accuracy = (d < 0 and -d or d) <= bands.braking_m
    local mean = mean_of(history or {})
    if mean == nil then
      -- No prior sample: nothing to be consistent WITH. Vacuously met, so the
      -- first pass at a corner is judged on accuracy alone. Harmless — a corner
      -- needs required_passes of evidence to qualify at all.
      gates.consistency = true
    else
      out.rolling_mean_m = mean
      local delta = d - mean
      gates.consistency = (delta < 0 and -delta or delta)
        <= cfg.criteria.consistency_delta_ratio * bands.braking_m
    end
    criteria.braking = gates.accuracy and gates.consistency
  end

  -- --- corner speed: two-sided band about the expert mean ---
  local v = metrics.min_corner_speed_kmh
  if v ~= nil then
    local dev = v - corner_ref.corner_speed.mean_kmh
    out.speed_envelope_deviation_kmh = dev
    criteria.corner_speed = M.corner_speed_ok(dev, bands.corner_speed_kmh,
                                              cfg.criteria.corner_speed_gate)
  end

  -- --- apex: one-sided, against the reference's own mean RMS ---
  local rms = metrics.apex_rms_m
  if rms ~= nil then
    criteria.apex = rms <= corner_ref.apex.mean_rms_m + bands.apex_m
  end

  return out
end

return M
