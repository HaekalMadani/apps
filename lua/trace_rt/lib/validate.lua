-- validate.lua — pure-Lua validators for TRACE's three runtime input formats:
-- controller_config, annotation, reference (see schemas/*.schema.json).
--
-- This is the Lua half of the M0 validation-parity pair: the Python side
-- validates with jsonschema against schemas/, this side hand-checks the same
-- rules. The shared corpus in configs/ (valid fixtures + configs/examples/
-- invalid/) is the agreement test — both sides must accept/reject identically.
--
-- Style note: deliberately plain and imperative. An earlier version expressed
-- the schema as combinator closures stored in tables and dispatched via
-- `spec.check(...)`; that pattern validated fine under headless LuaJIT but
-- crashed inside CSP's in-game Lua ("attempt to call field 'check' (a number
-- value)"). Direct function calls and explicit walks are immune to whatever
-- CSP does to table-stored closures, so the runtime validator is written that
-- way. Pure Lua 5.1, no ac.*, no render.*, no I/O — callable headless (via lupa
-- in kit/tests) and in-game alike. Decoded JSON tables come from lib/json.lua.

local M = {}

-- ---------------------------------------------------------------------------
-- low-level helpers (all called directly, never stored in tables)
-- ---------------------------------------------------------------------------

local function add_err(errs, path, msg)
  errs[#errs + 1] = path .. ": " .. msg
end

-- A decoded JSON array is a table keyed 1..n with no other keys. Returns
-- (true, n) for arrays, false otherwise. An empty table counts as an array.
local function array_len(t)
  if type(t) ~= "table" then return false end
  local n = 0
  for k in pairs(t) do
    if type(k) ~= "number" or k % 1 ~= 0 or k < 1 then return false end
    n = n + 1
  end
  for i = 1, n do
    if t[i] == nil then return false end
  end
  return true, n
end

-- Object = table that is not a non-empty array.
local function is_object(t)
  if type(t) ~= "table" then return false end
  local arr, n = array_len(t)
  if arr and n > 0 then return false end
  return true
end

local function check_number(errs, path, v, opts)
  if type(v) ~= "number" then
    add_err(errs, path, "must be a number")
    return
  end
  opts = opts or {}
  if opts.integer and v % 1 ~= 0 then add_err(errs, path, "must be an integer") end
  if opts.min and v < opts.min then add_err(errs, path, "must be >= " .. opts.min) end
  if opts.max and v > opts.max then add_err(errs, path, "must be <= " .. opts.max) end
  if opts.ex_min and v <= opts.ex_min then add_err(errs, path, "must be > " .. opts.ex_min) end
  if opts.ex_max and v >= opts.ex_max then add_err(errs, path, "must be < " .. opts.ex_max) end
end

local function check_string(errs, path, v, min_len)
  if type(v) ~= "string" then
    add_err(errs, path, "must be a string")
  elseif min_len and #v < min_len then
    add_err(errs, path, "must not be empty")
  end
end

local function check_bool(errs, path, v)
  if type(v) ~= "boolean" then add_err(errs, path, "must be a boolean") end
end

local function check_const(errs, path, v, expected)
  if v ~= expected then add_err(errs, path, "must equal " .. tostring(expected)) end
end

local function check_enum(errs, path, v, values)
  for _, x in ipairs(values) do
    if v == x then return end
  end
  add_err(errs, path, "must be one of: " .. table.concat(values, ", "))
end

local function check_spline(errs, path, v)
  check_number(errs, path, v, { min = 0, max = 1 })
end

-- Reject any key on `obj` not present in the `allowed` set (additionalProperties: false).
local function check_no_extra_keys(errs, path, obj, allowed)
  for k in pairs(obj) do
    if type(k) ~= "string" or not allowed[k] then
      add_err(errs, path, "unknown key '" .. tostring(k) .. "'")
    end
  end
end

-- Confirm `obj` is an object and every name in `required` is present.
-- Returns true if it is at least an object (so the caller can keep walking).
local function require_object(errs, path, obj, required)
  if not is_object(obj) then
    add_err(errs, path, "must be an object")
    return false
  end
  for _, name in ipairs(required) do
    if obj[name] == nil then
      add_err(errs, path, "missing required key '" .. name .. "'")
    end
  end
  return true
end

local function check_zone(errs, path, z)
  if not require_object(errs, path, z, { "start", "end" }) then return end
  check_no_extra_keys(errs, path, z, { start = true, ["end"] = true })
  if z.start ~= nil then check_spline(errs, path .. ".start", z.start) end
  if z["end"] ~= nil then check_spline(errs, path .. ".end", z["end"]) end
end

-- Exactly three numbers (AC world coordinate).
local function check_vec3(errs, path, v)
  local arr, n = array_len(v)
  if not arr or n == 0 then
    add_err(errs, path, "must be an array")
    return
  end
  if n ~= 3 then
    add_err(errs, path, "must have exactly 3 elements")
    return
  end
  for i = 1, 3 do
    check_number(errs, path .. "[" .. i .. "]", v[i])
  end
end

-- The expert line across one apex window: >= 2 samples of { spline_pos, world_pos }.
-- Two is the minimum that can be interpolated between; the extractor writes many
-- more. A single point would put us back at the gate-sample metric v6 rejected.
local function check_apex_line(errs, path, line)
  local arr, n = array_len(line)
  if not arr or n < 2 then
    add_err(errs, path, "must be an array of at least 2 samples")
    return
  end
  for i = 1, n do
    local sp = path .. "[" .. i .. "]"
    local s = line[i]
    if require_object(errs, sp, s, { "spline_pos", "world_pos" }) then
      check_no_extra_keys(errs, sp, s, { spline_pos = true, world_pos = true })
      if s.spline_pos ~= nil then check_spline(errs, sp .. ".spline_pos", s.spline_pos) end
      if s.world_pos ~= nil then check_vec3(errs, sp .. ".world_pos", s.world_pos) end
    end
  end
end

-- ---------------------------------------------------------------------------
-- controller_config
-- ---------------------------------------------------------------------------

local function validate_controller_config(errs, cfg)
  local p = "controller_config"
  if not require_object(errs, p, cfg, {
    "schema_version", "config_id", "mode", "evm", "band_floors",
    "qualification", "criteria", "quorum", "probe", "brake_initiation", "salience", "logging",
  }) then return end

  check_no_extra_keys(errs, p, cfg, {
    schema_version = true, config_id = true, mode = true, evm = true, band_floors = true,
    qualification = true, criteria = true, quorum = true, probe = true,
    brake_initiation = true, salience = true, logging = true,
  })

  if cfg.schema_version ~= nil then check_const(errs, p .. ".schema_version", cfg.schema_version, 1) end
  if cfg.config_id ~= nil then check_string(errs, p .. ".config_id", cfg.config_id, 1) end
  if cfg.mode ~= nil then check_enum(errs, p .. ".mode", cfg.mode, { "adaptive", "static", "off" }) end

  -- EVM is source-dependent: which multiplier applies is decided per corner by
  -- the reference table's `source` field (eval plan v2).
  local ev = cfg.evm
  if ev ~= nil and require_object(errs, p .. ".evm", ev, { "ai", "human" }) then
    check_no_extra_keys(errs, p .. ".evm", ev, { ai = true, human = true })
    if ev.ai ~= nil then check_number(errs, p .. ".evm.ai", ev.ai, { ex_min = 0 }) end
    if ev.human ~= nil then check_number(errs, p .. ".evm.human", ev.human, { ex_min = 0 }) end
  end

  local bf = cfg.band_floors
  if bf ~= nil and require_object(errs, p .. ".band_floors", bf,
    { "braking_m", "corner_speed_kmh", "apex_m" }) then
    check_no_extra_keys(errs, p .. ".band_floors", bf,
      { braking_m = true, corner_speed_kmh = true, apex_m = true })
    if bf.braking_m ~= nil then check_number(errs, p .. ".band_floors.braking_m", bf.braking_m, { ex_min = 0 }) end
    if bf.corner_speed_kmh ~= nil then check_number(errs, p .. ".band_floors.corner_speed_kmh", bf.corner_speed_kmh, { ex_min = 0 }) end
    if bf.apex_m ~= nil then check_number(errs, p .. ".band_floors.apex_m", bf.apex_m, { ex_min = 0 }) end
  end

  local q = cfg.qualification
  if q ~= nil and require_object(errs, p .. ".qualification", q,
    { "window_passes", "required_passes", "dequalify_consecutive_failures", "requalify_on_advance" }) then
    check_no_extra_keys(errs, p .. ".qualification", q,
      { window_passes = true, required_passes = true, dequalify_consecutive_failures = true,
        requalify_on_advance = true })
    if q.window_passes ~= nil then check_number(errs, p .. ".qualification.window_passes", q.window_passes, { integer = true, min = 1 }) end
    if q.required_passes ~= nil then check_number(errs, p .. ".qualification.required_passes", q.required_passes, { integer = true, min = 1 }) end
    if q.dequalify_consecutive_failures ~= nil then check_number(errs, p .. ".qualification.dequalify_consecutive_failures", q.dequalify_consecutive_failures, { integer = true, min = 1 }) end
    if q.requalify_on_advance ~= nil then check_bool(errs, p .. ".qualification.requalify_on_advance", q.requalify_on_advance) end
  end

  -- Per-pass criterion parameters that are neither bands nor floors. Currently
  -- just the braking consistency delta, expressed as a ratio of the accuracy
  -- band so it scales with each corner's own band rather than being a second
  -- absolute constant to calibrate.
  local cr = cfg.criteria
  if cr ~= nil and require_object(errs, p .. ".criteria", cr, { "consistency_delta_ratio" }) then
    check_no_extra_keys(errs, p .. ".criteria", cr, { consistency_delta_ratio = true })
    if cr.consistency_delta_ratio ~= nil then
      check_number(errs, p .. ".criteria.consistency_delta_ratio", cr.consistency_delta_ratio, { ex_min = 0 })
    end
  end

  local qu = cfg.quorum
  if qu ~= nil and require_object(errs, p .. ".quorum", qu, { "advance_threshold", "revert_threshold" }) then
    check_no_extra_keys(errs, p .. ".quorum", qu, { advance_threshold = true, revert_threshold = true })
    if qu.advance_threshold ~= nil then check_number(errs, p .. ".quorum.advance_threshold", qu.advance_threshold, { ex_min = 0, max = 1 }) end
    if qu.revert_threshold ~= nil then check_number(errs, p .. ".quorum.revert_threshold", qu.revert_threshold, { min = 0, ex_max = 1 }) end
  end

  local pr = cfg.probe
  if pr ~= nil and require_object(errs, p .. ".probe", pr, { "laps", "reversion_cap" }) then
    check_no_extra_keys(errs, p .. ".probe", pr, { laps = true, reversion_cap = true })
    if pr.laps ~= nil then check_number(errs, p .. ".probe.laps", pr.laps, { integer = true, min = 1 }) end
    if pr.reversion_cap ~= nil then check_number(errs, p .. ".probe.reversion_cap", pr.reversion_cap, { integer = true, min = 0 }) end
  end

  local bi = cfg.brake_initiation
  if bi ~= nil and require_object(errs, p .. ".brake_initiation", bi, { "threshold", "debounce_ms" }) then
    check_no_extra_keys(errs, p .. ".brake_initiation", bi, { threshold = true, debounce_ms = true })
    if bi.threshold ~= nil then check_number(errs, p .. ".brake_initiation.threshold", bi.threshold, { ex_min = 0, max = 1 }) end
    if bi.debounce_ms ~= nil then check_number(errs, p .. ".brake_initiation.debounce_ms", bi.debounce_ms, { min = 0 }) end
  end

  local s = cfg.salience
  if s ~= nil and require_object(errs, p .. ".salience", s,
    { "full_alpha", "reduced_alpha", "reduced_form" }) then
    check_no_extra_keys(errs, p .. ".salience", s,
      { full_alpha = true, reduced_alpha = true, reduced_form = true })
    if s.full_alpha ~= nil then check_number(errs, p .. ".salience.full_alpha", s.full_alpha, { ex_min = 0, max = 1 }) end
    if s.reduced_alpha ~= nil then check_number(errs, p .. ".salience.reduced_alpha", s.reduced_alpha, { ex_min = 0, max = 1 }) end
    -- The reduced-salience FORM (impl plan section 7's open M5 decision) is a
    -- config value, not a literal in the renderer: it is an RQ3 interview topic
    -- and has to be frozen and hashed before the pilot like everything else.
    if s.reduced_form ~= nil then
      check_enum(errs, p .. ".salience.reduced_form", s.reduced_form,
        { "minimal", "intermediate", "dimmed" })
    end
  end

  local lg = cfg.logging
  if lg ~= nil and require_object(errs, p .. ".logging", lg, { "tick_rate_hz" }) then
    check_no_extra_keys(errs, p .. ".logging", lg, { tick_rate_hz = true })
    if lg.tick_rate_hz ~= nil then check_number(errs, p .. ".logging.tick_rate_hz", lg.tick_rate_hz, { ex_min = 0 }) end
  end
end

-- ---------------------------------------------------------------------------
-- annotation
-- ---------------------------------------------------------------------------

local CORNER_TYPES = { "slow", "medium", "fast", "hairpin", "chicane", "kink" }

local function validate_annotation_corner(errs, path, c)
  if not require_object(errs, path, c, { "id", "type", "compound", "entry_gate", "exit_gate", "zones" }) then return end
  check_no_extra_keys(errs, path, c,
    { id = true, name = true, type = true, compound = true, entry_gate = true, exit_gate = true, zones = true })

  if c.id ~= nil then check_string(errs, path .. ".id", c.id, 1) end
  if c.name ~= nil then check_string(errs, path .. ".name", c.name) end
  if c.type ~= nil then check_enum(errs, path .. ".type", c.type, CORNER_TYPES) end
  if c.compound ~= nil then check_bool(errs, path .. ".compound", c.compound) end
  if c.entry_gate ~= nil then check_spline(errs, path .. ".entry_gate", c.entry_gate) end
  if c.exit_gate ~= nil then check_spline(errs, path .. ".exit_gate", c.exit_gate) end

  local z = c.zones
  -- zones.braking is optional: a corner taken flat has no braking zone and is
  -- simply not applicable to the braking-point element (see annotation schema).
  if z ~= nil and require_object(errs, path .. ".zones", z, { "apex_gates", "apex_window_half_m", "corner_speed" }) then
    check_no_extra_keys(errs, path .. ".zones", z,
      { braking = true, apex_gates = true, apex_window_half_m = true, corner_speed = true })
    if z.braking ~= nil then check_zone(errs, path .. ".zones.braking", z.braking) end
    if z.corner_speed ~= nil then check_zone(errs, path .. ".zones.corner_speed", z.corner_speed) end
    if z.apex_window_half_m ~= nil then
      check_number(errs, path .. ".zones.apex_window_half_m", z.apex_window_half_m, { ex_min = 0, max = 100 })
    end
    if z.apex_gates ~= nil then
      local arr, n = array_len(z.apex_gates)
      if not arr or n < 1 then
        add_err(errs, path .. ".zones.apex_gates", "must be a non-empty array")
      else
        for i = 1, n do
          check_spline(errs, path .. ".zones.apex_gates[" .. i .. "]", z.apex_gates[i])
        end
      end
    end
  end
end

local function validate_annotation(errs, ann)
  local p = "annotation"
  if not require_object(errs, p, ann, { "schema_version", "track", "corners" }) then return end
  check_no_extra_keys(errs, p, ann, { schema_version = true, track = true, notes = true, corners = true })

  if ann.schema_version ~= nil then check_const(errs, p .. ".schema_version", ann.schema_version, 1) end
  if ann.track ~= nil then check_string(errs, p .. ".track", ann.track, 1) end
  if ann.notes ~= nil then check_string(errs, p .. ".notes", ann.notes) end

  if ann.corners ~= nil then
    local arr, n = array_len(ann.corners)
    if not arr or n < 1 then
      add_err(errs, p .. ".corners", "must be a non-empty array")
    else
      for i = 1, n do
        validate_annotation_corner(errs, p .. ".corners[" .. i .. "]", ann.corners[i])
      end
    end
  end
end

-- ---------------------------------------------------------------------------
-- reference
-- ---------------------------------------------------------------------------

local function validate_reference_corner(errs, path, c)
  -- braking is optional, mirroring the annotation: no braking zone annotated
  -- means no braking reference extracted and no braking marker for the corner.
  if not require_object(errs, path, c,
    { "corner_id", "source", "contributing_laps", "apex", "corner_speed" }) then return end
  check_no_extra_keys(errs, path, c,
    { corner_id = true, source = true, contributing_laps = true, braking = true,
      apex = true, corner_speed = true })

  if c.corner_id ~= nil then check_string(errs, path .. ".corner_id", c.corner_id, 1) end
  if c.source ~= nil then check_enum(errs, path .. ".source", c.source, { "ai", "human" }) end

  -- How many reference passes built each element. Not read at run time; carried
  -- so Gate G0's minimum contributing-lap clause is checkable from the table.
  local cl = c.contributing_laps
  if cl ~= nil and require_object(errs, path .. ".contributing_laps", cl,
    { "clean_passes", "apex", "corner_speed" }) then
    check_no_extra_keys(errs, path .. ".contributing_laps", cl,
      { clean_passes = true, braking = true, apex = true, corner_speed = true })
    if cl.clean_passes ~= nil then
      check_number(errs, path .. ".contributing_laps.clean_passes", cl.clean_passes, { integer = true, min = 1 })
    end
    if cl.braking ~= nil then
      check_number(errs, path .. ".contributing_laps.braking", cl.braking, { integer = true, min = 0 })
    end
    if cl.apex ~= nil then
      check_number(errs, path .. ".contributing_laps.apex", cl.apex, { integer = true, min = 0 })
    end
    if cl.corner_speed ~= nil then
      check_number(errs, path .. ".contributing_laps.corner_speed", cl.corner_speed, { integer = true, min = 0 })
    end
  end

  local b = c.braking
  if b ~= nil and require_object(errs, path .. ".braking", b, { "world_pos", "spline_pos", "sigma_ref_m" }) then
    check_no_extra_keys(errs, path .. ".braking", b, { world_pos = true, spline_pos = true, sigma_ref_m = true })
    if b.world_pos ~= nil then check_vec3(errs, path .. ".braking.world_pos", b.world_pos) end
    if b.spline_pos ~= nil then check_spline(errs, path .. ".braking.spline_pos", b.spline_pos) end
    if b.sigma_ref_m ~= nil then check_number(errs, path .. ".braking.sigma_ref_m", b.sigma_ref_m, { min = 0 }) end
  end

  local a = c.apex
  if a ~= nil and require_object(errs, path .. ".apex", a, { "gates", "mean_rms_m", "sigma_ref_m" }) then
    check_no_extra_keys(errs, path .. ".apex", a, { gates = true, mean_rms_m = true, sigma_ref_m = true })
    if a.mean_rms_m ~= nil then check_number(errs, path .. ".apex.mean_rms_m", a.mean_rms_m, { min = 0 }) end
    if a.sigma_ref_m ~= nil then check_number(errs, path .. ".apex.sigma_ref_m", a.sigma_ref_m, { min = 0 }) end
    if a.gates ~= nil then
      local arr, n = array_len(a.gates)
      if not arr or n < 1 then
        add_err(errs, path .. ".apex.gates", "must be a non-empty array")
      else
        for i = 1, n do
          local gp = path .. ".apex.gates[" .. i .. "]"
          local g = a.gates[i]
          if require_object(errs, gp, g, { "world_pos", "spline_pos", "line" }) then
            check_no_extra_keys(errs, gp, g, { world_pos = true, spline_pos = true, line = true })
            if g.world_pos ~= nil then check_vec3(errs, gp .. ".world_pos", g.world_pos) end
            if g.spline_pos ~= nil then check_spline(errs, gp .. ".spline_pos", g.spline_pos) end
            if g.line ~= nil then check_apex_line(errs, gp .. ".line", g.line) end
          end
        end
      end
    end
  end

  local cs = c.corner_speed
  if cs ~= nil and require_object(errs, path .. ".corner_speed", cs, { "mean_kmh", "sigma_ref_kmh" }) then
    check_no_extra_keys(errs, path .. ".corner_speed", cs, { mean_kmh = true, sigma_ref_kmh = true })
    if cs.mean_kmh ~= nil then check_number(errs, path .. ".corner_speed.mean_kmh", cs.mean_kmh, { ex_min = 0 }) end
    if cs.sigma_ref_kmh ~= nil then check_number(errs, path .. ".corner_speed.sigma_ref_kmh", cs.sigma_ref_kmh, { min = 0 }) end
  end
end

local function validate_reference(errs, ref)
  local p = "reference"
  if not require_object(errs, p, ref,
    { "schema_version", "pair_id", "track", "car", "track_length_m", "corners" }) then return end
  check_no_extra_keys(errs, p, ref,
    { schema_version = true, pair_id = true, track = true, car = true, track_length_m = true,
      source_laps = true, corners = true })

  if ref.schema_version ~= nil then check_const(errs, p .. ".schema_version", ref.schema_version, 1) end
  if ref.pair_id ~= nil then check_string(errs, p .. ".pair_id", ref.pair_id, 1) end
  if ref.track ~= nil then check_string(errs, p .. ".track", ref.track, 1) end
  if ref.car ~= nil then check_string(errs, p .. ".car", ref.car, 1) end
  if ref.track_length_m ~= nil then check_number(errs, p .. ".track_length_m", ref.track_length_m, { ex_min = 0 }) end

  local sl = ref.source_laps
  if sl ~= nil and require_object(errs, p .. ".source_laps", sl, {}) then
    check_no_extra_keys(errs, p .. ".source_laps", sl,
      { ai_laps = true, human_laps = true, ai_strength_pct = true, human_driver = true,
        setup = true, lap_time_cov_pct = true })
    if sl.ai_laps ~= nil then check_number(errs, p .. ".source_laps.ai_laps", sl.ai_laps, { integer = true, min = 0 }) end
    if sl.human_laps ~= nil then check_number(errs, p .. ".source_laps.human_laps", sl.human_laps, { integer = true, min = 0 }) end
    if sl.ai_strength_pct ~= nil then check_number(errs, p .. ".source_laps.ai_strength_pct", sl.ai_strength_pct, { min = 0, max = 100 }) end
    if sl.human_driver ~= nil then check_string(errs, p .. ".source_laps.human_driver", sl.human_driver) end
    if sl.setup ~= nil then check_string(errs, p .. ".source_laps.setup", sl.setup) end
    if sl.lap_time_cov_pct ~= nil then
      check_number(errs, p .. ".source_laps.lap_time_cov_pct", sl.lap_time_cov_pct, { min = 0 })
    end
  end

  if ref.corners ~= nil then
    local arr, n = array_len(ref.corners)
    if not arr or n < 1 then
      add_err(errs, p .. ".corners", "must be a non-empty array")
    else
      for i = 1, n do
        validate_reference_corner(errs, p .. ".corners[" .. i .. "]", ref.corners[i])
      end
    end
  end
end

-- ---------------------------------------------------------------------------
-- public API: each returns (ok, errors-list)
-- ---------------------------------------------------------------------------

function M.controller_config(tbl)
  local errs = {}
  validate_controller_config(errs, tbl)
  return #errs == 0, errs
end

function M.annotation(tbl)
  local errs = {}
  validate_annotation(errs, tbl)
  return #errs == 0, errs
end

function M.reference(tbl)
  local errs = {}
  validate_reference(errs, tbl)
  return #errs == 0, errs
end

return M
