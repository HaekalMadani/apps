-- trace_rt : TRACE in-game runtime (CSP Lua app).
--
-- M4 state: config loader (M0) + per-frame sampler + buffered 20 Hz CSV logger
-- + per-block session manifest with SHA-256 config hashes (M1) + corner-pass
-- tracking and a drive-and-mark annotator mode (M2) + per-pair reference loading,
-- world-anchored braking/apex markers, and a reference-lap (autopilot) mode (M3)
-- + the evaluator, the fading controller and the fade-event log (M4)
-- + salience staging on all three elements and the corner-speed HUD (M5).
--
-- The M4 loop, per closed corner pass: lib/pass_metrics has been accumulating
-- the pass's samples since its entry gate; lib/evaluator turns its three metrics
-- into per-element criterion booleans against the reference bands; lib/controller
-- folds that into per-corner qualification and, on a quorum, moves an element's
-- stage and emits a fade event. The controller is a PURE function and lives
-- twice (here and in trace_kit for the simulator) — golden_traces/ is what keeps
-- the two identical, so nothing in this file may make a controller decision of
-- its own.
--
-- M5 closes the loop: the controller's stage now reaches the screen. What is
-- drawn for an element is decided in two pure steps before any render call —
-- lib/markers.presented_stage applies the block's CONDITION (adaptive shows the
-- controller's stage, static pins full, off draws nothing) and
-- lib/markers.visual turns that stage into an alpha and a set of parts. This
-- file only executes the result. That is what keeps the condition a config
-- field rather than a code path, and it is why the whole staging layer is
-- headless-testable while the drawing is not.
-- The block controls here are a MINIMAL stand-in for the M6 experimenter panel:
-- just enough to enter block metadata, start/stop a recording, and capture
-- annotation marks. Polished panel is M6.
--
-- Two hard gates, one soft behaviour. A PARTICIPANT block refuses to start
-- without both a valid annotation for the loaded track and a valid reference
-- for the selected pair — a block that silently records no passes, or renders
-- markers at another car's coordinates, cannot be re-run on the same person. A
-- DEV block (explicit toggle, stamped `dev_block: true`) opts out of both and
-- records ticks only, which is how the reference laps themselves are recorded:
-- the reference table cannot exist before the laps that produce it.
--
-- Boundary discipline (CLAUDE.md): all the testable arithmetic lives in
-- lib/sampler, lib/logger, lib/manifest, lib/hash and is exercised headless by
-- kit/tests. This file is the thin ac.*/io.* wiring around them. Helpers are
-- called directly, never stored in tables and dispatched as t.fn(...).
--
-- Defensive by design: CSP draws windows in immediate mode and silently
-- abandons the rest of a frame's draw if a call raises, and a raise inside the
-- per-frame sampler would otherwise kill logging. Every fallible step is
-- pcall-wrapped; sampler faults freeze the block and surface on the window
-- rather than crashing it. ASCII only.

local json = require('lib/json')
local validate = require('lib/validate')
local sampler = require('lib/sampler')
local logger = require('lib/logger')
local manifest = require('lib/manifest')
local hash = require('lib/hash')
local pass_tracker = require('lib/pass_tracker')
local annotator = require('lib/annotator')
local markers = require('lib/markers')
local pass_metrics = require('lib/pass_metrics')
local hud = require('lib/hud')
local evaluator = require('lib/evaluator')
local controller = require('lib/controller')
local pass_record = require('lib/pass_record')

-- Keep in sync with manifest.ini [ABOUT] VERSION.
local APP_VERSION = '0.4.0'

-- ---------------------------------------------------------------------------
-- module state
-- ---------------------------------------------------------------------------

-- Config inputs (M0 carryover). Built in init().
local INPUTS = nil
local results = nil           -- list of { ok, message } aligned to INPUTS
local init_error = nil        -- string set if init() itself failed
local ticks_descriptor = nil  -- decoded configs/ticks_columns.json
local data_dir = nil          -- output folder for ticks/manifest files
local annotations_dir = nil   -- configs/annotations/ (per-track annotation files)
local references_dir = nil    -- configs/references/ (per-pair reference tables)
local ac_version = nil        -- detected AC version (see detect_ac_version)
-- Cached annotation lookup for the loaded track: { track, ok, err }. Avoids
-- re-reading the file every frame while the idle controls are drawn. Cleared by
-- reload() and whenever the track changes.
local ann_status = nil
-- Same, for the selected pair's reference table: { pair, track, car, ok, err }.
local ref_status = nil

-- M3 rendering: the draw list built once from the loaded reference table, and
-- an on-window toggle so the G0 review can flip markers on and off while
-- standing on track. Salience staging is M4/M5; M3 draws at 'full'.
local marker_list = nil
local show_markers = true
-- M5: the corner-speed HUD's per-corner plan (built with the marker list) and
-- its running-minimum state.
local hud_plans = nil
local hud_state = hud.new()
local hud_readout = nil        -- last computed readout, for the cue window
-- REVIEW-ONLY stage override, for M5's exit test ("scripted controller states
-- produce the intended visuals"). Stepping an element through full -> reduced ->
-- probe by driving takes ~9 laps; this makes it a button press. nil means "use
-- the controller". Cleared whenever a block starts, so it can never be live in a
-- participant block -- see start_block.
local stage_override = nil
local salience = { full_alpha = 1.0, reduced_alpha = 0.4 }  -- replaced from config in init()
-- The decoded controller_config. M0-M3 only ever needed two numbers out of it;
-- the evaluator and controller need the whole document, and neither may hold a
-- threshold as a literal (impl plan section 6.3), so it is decoded once here and
-- passed down.
local controller_cfg = nil

-- UI mode: 'record' (block recording), 'annotate' (drive-and-mark), or
-- 'reference' (Phase 0 reference-lap setup: AI strength + autopilot).
local ui_mode = 'record'
-- Active annotator buffer; nil unless in annotate mode with a started capture.
local annot = nil
-- Current corner being marked + a transient capture confirmation line.
local amark = { corner_id = '', corner_type = 'medium', compound = false }
local last_capture = nil
-- Summary of the last written marks file, for on-window confirmation.
local last_marks = nil

-- Block metadata entered on the window (the M6 panel will own this properly).
-- Crossover sequences the protocol defines (eval plan: 4 sequences). Blank
-- means "not set" and is omitted from the manifest. Free text here produced a
-- schema-invalid manifest that only failed at the offline integrity check, so
-- the UI offers exactly these and start_block re-checks.
local SEQUENCES = { '', 'A', 'B', 'C', 'D' }

local function valid_sequence(v)
  for i = 1, #SEQUENCES do
    if SEQUENCES[i] == v then return true end
  end
  return false
end

-- The car-track pairs the study defines. Like `sequence`, this was free text and
-- is now a radio group: pair_id selects which reference table loads, so a typo
-- would have silently started a block against the wrong pair's brake points.
-- Constrain at the UI, re-check at start_block (the M2 decision).
local PAIRS = { 'pair1', 'pair2' }

local function valid_pair(v)
  for i = 1, #PAIRS do
    if PAIRS[i] == v then return true end
  end
  return false
end

local meta = {
  participant_id = '',
  pair_id = PAIRS[1],
  session = 2,            -- 1 baseline, 2 training, 3 unassisted, 4 retention
  condition = 'adaptive', -- adaptive | static | off
  sequence = '',          -- optional crossover sequence (A..D); blank = omit
  -- Dev/scratch block: opts out of the hard annotation gate below, so an
  -- un-annotated track can still be used for tick-only recording. Default false
  -- so the safe path is the one you get without thinking about it. Recorded in
  -- the manifest, so a dev block is never mistaken for study data.
  dev_block = false,
  -- Protocol-rehearsal block (M6). NOT a dev block: both gates still apply and
  -- the controller still runs, because the point of the rehearsal is to
  -- exercise the real path. The flag only keeps the rehearsal data out of the
  -- participant dataset. Default false, like dev_block.
  dry_run = false,
}

-- Active recording state; nil when idle. See start_block().
local block = nil

-- Summary of the last finished block, for on-window confirmation.
local last_summary = nil

-- ABORT is a two-click control: this is the armed flag. Reset on start_block so
-- a block can never begin with the abort half-pressed from the previous one.
local abort_armed = false

-- ---------------------------------------------------------------------------
-- config validation (M0)
-- ---------------------------------------------------------------------------

local function loadAndValidate(input)
  local content = io.load(input.path)
  if content == nil then
    return { ok = false, message = 'file not found: ' .. input.path }
  end
  local parsed, decoded = pcall(json.decode, content)
  if not parsed then
    return { ok = false, message = 'JSON parse error: ' .. tostring(decoded) }
  end
  local ok, errs = input.check(decoded)
  if not ok then
    local extra = (#errs > 1) and (' (+' .. (#errs - 1) .. ' more)') or ''
    return { ok = false, message = tostring(errs[1]) .. extra }
  end
  return { ok = true, message = 'PASS' }
end

local function reload()
  results = {}
  ann_status = nil
  ref_status = nil
  marker_list = nil
  for i, input in ipairs(INPUTS) do
    local ok, res = pcall(loadAndValidate, input)
    if ok then
      results[i] = res
    else
      results[i] = { ok = false, message = 'validator crashed: ' .. tostring(res) }
    end
  end
end

-- AC has no version API (only ac.getPatchVersion for CSP), but AC's own
-- changelog.txt opens with the version number, so the apparatus pin can be
-- SELF-REPORTING rather than a literal in this file that silently goes stale
-- while claiming the study is still on one AC build. Falls back to a marker
-- string, never to a guess: an unknown version must look unknown in the
-- manifest. Blocks are compared against each other for version drift offline
-- (trace_kit.integrity), which is what "pinned at M3" actually enforces.
local function detect_ac_version()
  local content = io.load(ac.getFolder(ac.FolderID.Root) .. '/changelog.txt')
  if content == nil then return 'unknown (changelog.txt unreadable)' end
  local first = string.match(content, '^%s*([%d%.]+)')
  if first == nil or #first < 3 then return 'unknown (changelog.txt unparsed)' end
  return first
end

local function init()
  local root = ac.getFolder(ac.FolderID.ACApps)
  -- Only genuinely global runtime inputs belong here. The annotation and the
  -- reference are per-track and per-pair, so they are resolved and shown
  -- dynamically below; validating the EXAMPLE FIXTURES here (as this did) put a
  -- reassuring PASS on the window for two files no block ever loads.
  INPUTS = {
    { label = 'controller_config', path = root .. '/configs/controller_config.json', check = validate.controller_config },
  }
  -- The 20 Hz CSV column descriptor: the contract trace-kit also validates
  -- against, so the runtime never invents its own column order.
  local tc = io.load(root .. '/configs/ticks_columns.json')
  if tc == nil then error('ticks_columns.json not found') end
  ticks_descriptor = json.decode(tc)
  -- Salience alphas come from the controller config, never from a literal in
  -- the renderer (impl plan section 6.3). The validator has already accepted
  -- the file; this re-reads only the numbers the renderer needs.
  local cc = io.load(root .. '/configs/controller_config.json')
  if cc ~= nil then
    local ok, cfg = pcall(json.decode, cc)
    if ok and cfg ~= nil then
      controller_cfg = cfg
      if cfg.salience ~= nil then salience = cfg.salience end
    end
  end
  -- Per-track annotation files (produced by the annotator + trace-kit) live here.
  annotations_dir = root .. '/configs/annotations'
  -- Per-pair reference tables (produced by trace_kit.reference) live here.
  references_dir = root .. '/configs/references'
  -- Outputs live under the user's AC Documents folder, out of the Steam tree.
  data_dir = ac.getFolder(ac.FolderID.ACDocuments) .. '/trace_data'
  ac_version = detect_ac_version()
  reload()
end

local function allValid()
  if results == nil then return false end
  for _, r in ipairs(results) do
    if not r.ok then return false end
  end
  return true
end

-- ---------------------------------------------------------------------------
-- block lifecycle
-- ---------------------------------------------------------------------------

local function iso_now()
  return os.date('%Y-%m-%dT%H:%M:%S')
end

-- Keep only filename-safe characters for ids embedded in output paths.
local function sanitize(s)
  return (string.gsub(tostring(s), '[^%w%-]', '_'))
end

local function save_file(path, text)
  return io.save(path, text)
end

local function write_manifest()
  return save_file(block.manifest_path, json.encode(block.manifest))
end

-- Record a runtime fault: freeze sampling, stamp it onto the manifest so a
-- crash still leaves the fault on disk, and surface it on the window.
local function record_fault(msg)
  if block == nil then return end
  block.fault = tostring(msg)
  block.faults[#block.faults + 1] = { at = iso_now(), message = block.fault }
  block.manifest.faults = block.faults
  pcall(write_manifest)
end

local function hash_file(path)
  local content = io.load(path)
  if content == nil then error('cannot hash missing file: ' .. path) end
  return hash.sha256_hex(content)
end

-- Build the SHA-256 hashes recorded in the manifest, as 64-hex strings.
--
-- The annotation and reference hashes are of the PER-TRACK and PER-PAIR files
-- this block actually loaded, not of the example fixtures — hashing a fixture
-- (as this did before M3) recorded provenance for a file no block ever used.
-- Either path is nil only on a dev block that started without one; the hash is
-- then nil too, which the manifest schema permits for exactly that case.
local function hash_inputs(annotation_path, reference_path)
  return {
    controller_config = hash_file(INPUTS[1].path),
    reference = reference_path ~= nil and hash_file(reference_path) or nil,
    annotation = annotation_path ~= nil and hash_file(annotation_path) or nil,
  }
end

-- Read the logged tick rate from the loaded controller_config
-- (logging.tick_rate_hz), falling back to 20 Hz. The validator already accepted
-- the file, so this only re-reads the one number the sampler needs.
local function configured_tick_rate()
  if controller_cfg ~= nil and controller_cfg.logging
    and type(controller_cfg.logging.tick_rate_hz) == 'number' then
    return controller_cfg.logging.tick_rate_hz
  end
  return 20
end

-- Current track's full id (folder + layout joined by '-'), the annotation-file
-- key. ac.getTrackFullID is the non-deprecated accessor (see SDK_NOTES).
local function track_full_id()
  return ac.getTrackFullID('-')
end

-- Load + validate the annotation for a track full id. Returns (corners, err):
-- corners is the decoded annotation's corner array on success, err a string on
-- failure (file absent, bad JSON, schema-invalid). No annotation is NOT an error
-- the caller must treat as fatal — recording proceeds with pass tracking off.
local function annotation_path(full_id)
  return annotations_dir .. '/annotation_' .. full_id .. '.json'
end

local function load_annotation(full_id)
  local path = annotation_path(full_id)
  local content = io.load(path)
  if content == nil then
    return nil, 'no annotation file (' .. path .. ')'
  end
  local ok, decoded = pcall(json.decode, content)
  if not ok then
    return nil, 'annotation JSON parse error: ' .. tostring(decoded)
  end
  local valid, errs = validate.annotation(decoded)
  if not valid then
    return nil, 'annotation invalid: ' .. tostring(errs[1])
  end
  return decoded.corners, nil
end

-- Annotation availability for the loaded track, cached per track id so the idle
-- controls can show it every frame without re-reading the file.
local function annotation_status()
  local full_id = track_full_id()
  if ann_status == nil or ann_status.track ~= full_id then
    local corners, err = load_annotation(full_id)
    ann_status = { track = full_id, ok = corners ~= nil, err = err }
  end
  return ann_status
end

-- Current car's AC id, the other half of the car-track pair the reference is
-- built for. ac.getCarID(0) is the player car (see SDK_NOTES).
local function car_id()
  return ac.getCarID(0)
end

local function reference_path(pair_id)
  return references_dir .. '/reference_' .. pair_id .. '.json'
end

-- Load + validate the reference table for a pair. Returns (doc, err).
--
-- Beyond schema validity this checks the table against the session actually
-- loaded: a reference is per CAR-track pair, and its brake points and bands are
-- meaningless for a different car or layout. Selecting pair1 while sitting in
-- pair2's car would otherwise start a block that renders markers at coordinates
-- from another circuit — schema-valid, silently wrong, unrepeatable on the same
-- participant. That is exactly the class of failure the annotation gate exists
-- for, so the reference gets the same treatment.
local function load_reference(pair_id)
  local path = reference_path(pair_id)
  local content = io.load(path)
  if content == nil then
    return nil, 'no reference file (' .. path .. ')'
  end
  local ok, decoded = pcall(json.decode, content)
  if not ok then
    return nil, 'reference JSON parse error: ' .. tostring(decoded)
  end
  local valid, errs = validate.reference(decoded)
  if not valid then
    return nil, 'reference invalid: ' .. tostring(errs[1])
  end
  local loaded_track = track_full_id()
  if decoded.track ~= loaded_track then
    return nil, 'reference is for track ' .. tostring(decoded.track)
      .. ' but this session is ' .. tostring(loaded_track)
  end
  local loaded_car = car_id()
  if decoded.car ~= loaded_car then
    return nil, 'reference is for car ' .. tostring(decoded.car)
      .. ' but this session is ' .. tostring(loaded_car)
  end
  return decoded, nil
end

-- Reference availability for the selected pair, cached per (pair, track, car)
-- so the idle controls can show it every frame without re-reading the file.
local function reference_status()
  local pair = meta.pair_id
  local full_id = track_full_id()
  local car = car_id()
  if ref_status == nil or ref_status.pair ~= pair
    or ref_status.track ~= full_id or ref_status.car ~= car then
    local doc, err = load_reference(pair)
    ref_status = { pair = pair, track = full_id, car = car, ok = doc ~= nil, err = err,
      corners = doc and #doc.corners or 0 }
    -- Marker world positions are precomputed once per reference load, straight
    -- from the extracted table — the M3 exit criterion is that nothing here is
    -- a hardcoded coordinate.
    marker_list = doc and markers.build(doc) or nil
    -- The HUD's targets come from the same reference table and the same band
    -- arithmetic the evaluator uses, so the number on screen and the number the
    -- criterion is judged on cannot drift apart. Needs the annotation too, for
    -- the corner-speed zones.
    hud_plans = nil
    if doc ~= nil and controller_cfg ~= nil then
      local corners = load_annotation(full_id)
      if corners ~= nil then
        local ok, plans = pcall(hud.plans, corners, doc, controller_cfg)
        hud_plans = ok and plans or nil
      end
    end
  end
  return ref_status
end

local function start_block()
  local full_id = track_full_id()
  local corners, ann_err = load_annotation(full_id)
  local reference, ref_err = load_reference(meta.pair_id)

  -- HARD GATE (impl plan §1: "refuses to start a block on any validation
  -- error"). A participant block will not start without a valid annotation for
  -- the loaded track: a block that silently records no passes cannot be re-run
  -- on the same person, and an orange line on the window is too easy to miss.
  -- Dev blocks opt out explicitly and keep the tick-only soft behaviour.
  if corners == nil and not meta.dev_block then
    error('refusing to start: ' .. tostring(ann_err)
      .. ' -- a participant block requires a valid annotation for this track.'
      .. ' Tick "dev block" to record ticks only.')
  end

  -- Same gate for the per-pair reference (M3). Without it there are no marker
  -- coordinates and no tolerance bands, so a participant block would render
  -- nothing and evaluate against nothing. Dev blocks opt out because the
  -- REFERENCE LAPS THEMSELVES are recorded before any reference table exists.
  if reference == nil and not meta.dev_block then
    error('refusing to start: ' .. tostring(ref_err)
      .. ' -- a participant block requires a valid reference for this pair.'
      .. ' Tick "dev block" to record reference laps.')
  end

  -- The reference's corners and the annotation's must be the SAME SET. They
  -- always are when the reference was extracted from that annotation, but the
  -- two files are hand-edited between recordings and nothing else checks it, so
  -- a drift would be silent and one-directional: a reference corner the
  -- annotation no longer has produces no passes, never accumulates evidence,
  -- and (by the quorum-readiness rule) STALLS its element at full salience for
  -- the whole block. That is a wasted participant block that looks like a
  -- participant who never improved. Refuse instead.
  if corners ~= nil and reference ~= nil then
    local annotated = {}
    for i = 1, #corners do annotated[corners[i].id] = true end
    local missing = {}
    for i = 1, #reference.corners do
      local id = reference.corners[i].corner_id
      if not annotated[id] then missing[#missing + 1] = id end
    end
    if #missing > 0 then
      error('refusing to start: reference for ' .. meta.pair_id .. ' has corner(s) '
        .. table.concat(missing, ', ') .. ' that the annotation for this track'
        .. ' does not.'
        .. ' The two files have drifted; re-extract the reference.')
    end
  end

  -- The UI only offers valid sequences and pairs; re-check here so the invariant
  -- holds at the one place that writes a manifest, rather than only at the
  -- offline check.
  if not valid_sequence(meta.sequence) then
    error('refusing to start: sequence must be A, B, C, D or blank (got '
      .. tostring(meta.sequence) .. ')')
  end
  if not valid_pair(meta.pair_id) then
    error('refusing to start: pair must be one of pair1, pair2 (got '
      .. tostring(meta.pair_id) .. ')')
  end

  -- The review override is a bench tool. A block that started with an element
  -- pinned by hand would render something the controller never asked for while
  -- logging as though it had, which is the one way the fade log and what the
  -- participant saw could disagree. Clearing it here rather than trusting the
  -- panel means it cannot survive into a recording by accident.
  stage_override = nil
  -- Same reasoning for the abort arm: a block must not begin one click from
  -- being stamped unusable.
  abort_armed = false

  local stamp = os.date('%Y%m%d_%H%M%S')
  local id = sanitize(meta.participant_id) .. '_s' .. meta.session
    .. '_' .. sanitize(meta.pair_id) .. '_' .. meta.condition .. '_' .. stamp

  -- Only hash inputs that actually loaded: on a dev block either may be absent
  -- or schema-invalid, and hashing a file the block did not use would be worse
  -- than recording no hash.
  local hashes = hash_inputs(
    corners ~= nil and annotation_path(full_id) or nil,
    reference ~= nil and reference_path(meta.pair_id) or nil)
  local versions = {
    app = APP_VERSION,
    csp = tostring(ac.getPatchVersion()),
    ac = ac_version,
  }
  local mmeta = {
    block_id = id,
    participant_id = meta.participant_id,
    session = meta.session,
    condition = meta.condition,
    pair_id = meta.pair_id,
    track_id = full_id,
    car_id = car_id(),
    track_length_m = ac.getSim().trackLengthM,
  }
  if meta.sequence ~= '' then mmeta.sequence = meta.sequence end
  if meta.dev_block then mmeta.dev_block = true end

  io.createDir(data_dir)

  block = {
    id = id,
    -- The block's own copy of the condition. `meta.condition` is the PANEL's
    -- current selection and an experimenter can change it mid-block by
    -- accident; what the renderer must obey is the condition this block
    -- started under, which is also the one stamped in the manifest.
    condition = meta.condition,
    ticks_path = data_dir .. '/ticks_' .. id .. '.csv',
    passes_path = data_dir .. '/passes_' .. id .. '.jsonl',
    manifest_path = data_dir .. '/manifest_' .. id .. '.json',
    sampler_state = sampler.new(configured_tick_rate()),
    log = logger.new(sampler.header(ticks_descriptor)),
    t = 0.0,
    start_lap = nil,          -- set on first sampled frame
    last_lap = nil,
    laps_completed = 0,
    faults = {},
    fault = nil,
    autopilot = false,        -- set true if the AI ever drove (reference blocks)
    ai_level_pct = nil,
    manifest = manifest.build(mmeta, hashes, versions, iso_now()),
    -- M2 pass tracking (nil tracker => off for this block).
    track_id = full_id,
    tracker = corners and pass_tracker.new(corners, id) or nil,
    ann_error = ann_err,      -- why tracking is off, if it is
    -- M3: the loaded reference table (nil on a dev block without one). The
    -- renderer reads marker world coordinates straight off this; nothing is
    -- hardcoded, which is the milestone's exit criterion.
    reference = reference,
    ref_error = ref_err,
    passlog = logger.new(nil),  -- headerless JSONL stream
    pass_counts = {},         -- corner_id -> { n, last_valid } for the window
    -- M4. All nil on a block with no reference (a dev block): the evaluator has
    -- nothing to judge against and the controller nothing to run over, so pass
    -- records keep their placeholder shape and no fades stream is written. That
    -- is the honest outcome, not a degraded one — a reference-lap recording has
    -- no criteria by definition.
    fades_path = data_dir .. '/fades_' .. id .. '.jsonl',
    fadelog = nil,
    controller = nil,
    metric_plans = nil,
    open_metrics = {},        -- corner_id -> in-progress pass_metrics state
    brake_history = {},       -- corner_id -> recent brake distances (rolling mean)
    ref_corners = nil,        -- corner_id -> reference row
    fade_events = 0,
    null_criteria = 0,        -- passes that fed NO evidence to an element
  }
  if reference ~= nil and corners ~= nil and controller_cfg ~= nil then
    local track_length_m = ac.getSim().trackLengthM
    block.metric_plans = pass_metrics.plans(corners, reference, track_length_m, controller_cfg)
    block.ref_corners = evaluator.index_corners(reference)
    block.controller = controller.new(controller_cfg, evaluator.applicable(reference))
    block.fadelog = logger.new(nil)
    -- An element with no applicable corners is disabled and pinned at full
    -- salience. It emits no fade events (a fade record with a zero denominator
    -- would be a fiction), so the manifest is where it gets recorded.
    local disabled = controller.disabled_elements(block.controller)
    if #disabled > 0 then block.manifest.disabled_elements = disabled end
    for i = 1, #corners do block.brake_history[corners[i].id] = {} end
  end
  -- Write the start manifest and an empty (header-only) ticks file up front so
  -- a crash leaves valid, parseable files rather than nothing.
  pcall(write_manifest)
  pcall(function() logger.flush(block.log, block.ticks_path, save_file) end)
  if block.tracker ~= nil then
    pcall(function() logger.flush(block.passlog, block.passes_path, save_file) end)
  end
  if block.fadelog ~= nil then
    pcall(function() logger.flush(block.fadelog, block.fades_path, save_file) end)
  end
  -- Echo the RESOLVED output path to py_log.txt. ac.getFolder(ACDocuments)
  -- follows the real (possibly OneDrive-redirected) Documents location, so this
  -- is the only reliable record of where the files actually landed.
  print('[TRACE] recording started -> ' .. block.ticks_path)
end

local function flush_ticks()
  local ok = logger.flush(block.log, block.ticks_path, save_file)
  if not ok then record_fault('tick flush failed (io.save returned false)') end
end

local function flush_passes()
  if block.tracker == nil then return end
  local ok = logger.flush(block.passlog, block.passes_path, save_file)
  if not ok then record_fault('pass flush failed (io.save returned false)') end
end

local function flush_fades()
  if block.fadelog == nil then return end
  local ok = logger.flush(block.fadelog, block.fades_path, save_file)
  if not ok then record_fault('fade flush failed (io.save returned false)') end
end

-- Write the controller's events to the fades stream. The controller is pure and
-- does not know its block, so pass_record stamps the two schema fields it cannot
-- supply. Flushed with the passes stream on lap boundaries, but a fade is rare
-- and interesting enough that losing one to a crash would hurt, so this also
-- flushes immediately.
local function log_fade_events(events)
  if block.fadelog == nil then return end
  for i = 1, #events do
    logger.add(block.fadelog, json.encode(pass_record.fade_record(block.id, events[i])))
    block.fade_events = block.fade_events + 1
  end
  if #events > 0 then flush_fades() end
end

-- Evaluate one closed pass and run it through the controller (M4).
--
-- The order matters and is the same order the golden traces assume: metrics ->
-- criteria -> controller. The record is stamped with the qualification and stage
-- AFTER the controller has seen the pass, so a pass record shows the state the
-- pass PRODUCED rather than the state it arrived in — which is what makes a fade
-- event line up with the pass record on the same corner and lap.
local function evaluate_pass(record)
  local st = block.open_metrics[record.corner_id]
  block.open_metrics[record.corner_id] = nil
  if st == nil or block.controller == nil then return end

  local ref_corner = block.ref_corners[record.corner_id]
  if ref_corner == nil then return end   -- annotated but not in the reference

  local metrics = pass_metrics.close(st)
  local history = block.brake_history[record.corner_id]
  local evaluation = evaluator.evaluate(controller_cfg, ref_corner, metrics, history)

  -- Only MEASURED passes enter the rolling mean: a null distance is no evidence,
  -- so it must not displace an earlier value out of the consistency datum.
  if metrics.brake_initiation_distance_m ~= nil then
    evaluator.push_history(history, metrics.brake_initiation_distance_m,
      controller_cfg.qualification.window_passes)
  end

  -- An invalid pass (off-track, wall contact) still feeds the controller: it has
  -- real metrics, and the controller must run on whatever the participant
  -- actually drove (eval plan v2). Only a NULL criterion is withheld, and the
  -- controller does that itself.
  log_fade_events(controller.step(block.controller, {
    corner_id = record.corner_id,
    lap = record.lap,
    t = record.t_exit,
    criteria = evaluation.criteria,
  }))

  for _, element in ipairs(controller.ELEMENTS) do
    if evaluation.criteria[element] == nil then
      block.null_criteria = block.null_criteria + 1
    end
  end

  pass_record.attach(record, metrics, evaluation,
    controller.qualified(block.controller, record.corner_id),
    controller.stages(block.controller))
end

-- Fold tracker events into the passes buffer + the per-corner window summary.
-- Only 'close' events carry a record; 'open' events start metric accumulation.
local function process_pass_events(events, snap)
  for i = 1, #events do
    local e = events[i]
    if e.kind == 'open' then
      -- Begin accumulating this pass's samples. The entry sample is fed here
      -- because the tracker consumed it before returning the event.
      local plan = block.metric_plans and block.metric_plans[e.corner_id]
      if plan ~= nil and snap ~= nil then
        block.open_metrics[e.corner_id] = pass_metrics.update(
          pass_metrics.open(plan, snap), snap)
      end
    else
      -- Evaluation is wrapped separately from logging: a fault in the evaluator
      -- or controller must not cost us the pass RECORD, which is the only
      -- durable evidence of what the driver did. On a raise the record is
      -- written with its M2 placeholder fields and the block is flagged.
      local ok, err = pcall(evaluate_pass, e.record)
      if not ok then record_fault('evaluator/controller error: ' .. tostring(err)) end
      logger.add(block.passlog, json.encode(e.record))
      local pc = block.pass_counts[e.corner_id] or { n = 0, last_valid = true }
      pc.n = pc.n + 1
      pc.last_valid = e.record.valid
      block.pass_counts[e.corner_id] = pc
    end
  end
end

-- The per-tick work, called from script.update. Raises on unexpected state;
-- the caller's pcall turns that into a frozen-block fault.
local function sample_frame(dt)
  local car = ac.getCar(0)
  if car == nil then return end

  local period = block.sampler_state.period
  local n = sampler.tick(block.sampler_state, dt)
  if n > 0 then
    if block.start_lap == nil then
      block.start_lap = math.floor(car.lapCount)
      block.last_lap = block.start_lap
    end
    for _ = 1, n do
      block.t = block.t + period
      logger.add(block.log, sampler.format_row(ticks_descriptor, {
        t = block.t,
        lap = math.floor(car.lapCount),
        spline = car.splinePosition,
        pos_x = car.position.x,
        pos_y = car.position.y,
        pos_z = car.position.z,
        speed_kmh = car.speedKmh,
        brake = car.brake,
        throttle = car.gas,
        steer = car.steer,
        gear = math.floor(car.gear),
        wheels_outside = math.floor(car.wheelsOutside),
        in_pit = car.isInPitlane and true or false,
      }))
    end
  end

  -- Provenance, polled rather than trusted to the panel toggle: if the AI drove
  -- at any point, this is an AI reference block and the manifest must say so.
  if car.isAIControlled then
    block.autopilot = true
    block.ai_level_pct = (car.aiLevel or -1) * 100
  end

  -- Drive the pass tracker once per frame (higher resolution than the 20 Hz log,
  -- which only matters for crossing precision). The tracker stamps entry/exit
  -- with the logged clock block.t. The raw collisionDepth goes through, not a
  -- boolean: the wall-contact gate is a threshold on it (a kerb graze is a
  -- collision too), and the depth is stamped into the pass record for audit.
  if block.tracker ~= nil then
    local snap = {
      spline = car.splinePosition,
      lap = math.floor(car.lapCount),
      t = block.t,
      wheels_outside = math.floor(car.wheelsOutside),
      in_pit = car.isInPitlane and true or false,
      collision_depth = car.collisionDepth or 0,
      -- M4 additions: what lib/pass_metrics accumulates from. Sampled per FRAME
      -- like the gate crossings, not at 20 Hz — the evaluator consumes per-frame
      -- samples, which is exactly why the raw brake-initiation sample is stamped
      -- into the pass record (impl plan section 2.1.4): the tick log cannot
      -- resolve it.
      brake = car.brake,
      speed_kmh = car.speedKmh,
      pos_x = car.position.x,
      pos_y = car.position.y,
      pos_z = car.position.z,
    }
    -- Feed every pass already open BEFORE advancing the tracker, so a pass that
    -- closes on this frame still gets this frame's sample (the exit-crossing
    -- sample belongs to the pass, exactly as it does in the offline extractor).
    -- Passes that OPEN on this frame are seeded inside process_pass_events.
    for _, st in pairs(block.open_metrics) do
      pass_metrics.update(st, snap)
    end
    process_pass_events(pass_tracker.update(block.tracker, snap), snap)
  end

  -- Flush on lap completion only (keeps the multi-MB rewrite off the hot path).
  if block.last_lap ~= nil and math.floor(car.lapCount) > block.last_lap then
    block.last_lap = math.floor(car.lapCount)
    block.laps_completed = block.last_lap - block.start_lap
    block.manifest.laps_completed = block.laps_completed
    flush_ticks()
    flush_passes()
    flush_fades()
    pcall(write_manifest)
  end
end

-- Close the block. `abort_reason` non-nil means the experimenter hit ABORT:
-- every stream is still closed and flushed exactly as on a normal stop (the
-- partial evidence of what happened is kept and stays auditable), and the
-- manifest is stamped `aborted` so no analysis can read the block as study data.
local function stop_block(abort_reason)
  pcall(flush_ticks)
  -- Close any pass still open at block end (logged incomplete / right-censored),
  -- then flush the passes stream.
  if block.tracker ~= nil then
    pcall(function() process_pass_events(pass_tracker.close_open(block.tracker, block.t)) end)
    pcall(flush_passes)
  end
  -- Close the controller: an element still mid-probe is logged censored
  -- (incomplete / right-censored), counting as neither held nor reverted in
  -- RQ1's probe-outcome tabulation. Its final stage stays `probe`.
  if block.controller ~= nil then
    pcall(function()
      log_fade_events(controller.finish(block.controller, block.last_lap or 0, block.t))
    end)
    pcall(flush_fades)
  end
  if block.autopilot then
    manifest.stamp_autopilot(block.manifest, block.ai_level_pct)
  end
  if abort_reason ~= nil then
    manifest.mark_aborted(block.manifest, abort_reason)
  end
  manifest.finalize(block.manifest, iso_now(), block.laps_completed, block.faults)
  pcall(write_manifest)
  last_summary = {
    id = block.id,
    aborted = abort_reason,
    laps = block.laps_completed,
    ticks = logger.count(block.log),
    passes = logger.count(block.passlog),
    tracking = block.tracker ~= nil,
    ann_error = block.ann_error,
    fault = block.fault,
    ticks_path = block.ticks_path,
    fades = block.fade_events,
    controller_on = block.controller ~= nil,
    null_criteria = block.null_criteria,
    stages = block.controller and controller.stages(block.controller) or nil,
  }
  if abort_reason ~= nil then
    print('[TRACE] block ABORTED (' .. abort_reason .. ') -> ' .. block.ticks_path)
  else
    print('[TRACE] recording stopped -> ' .. block.ticks_path)
  end
  block = nil
end

-- ---------------------------------------------------------------------------
-- per-frame callback (runs whenever the app is enabled, window open or not)
-- ---------------------------------------------------------------------------

function script.update(dt)
  if block == nil or block.fault ~= nil then return end
  local ok, err = pcall(sample_frame, dt)
  if not ok then
    record_fault('sampler error: ' .. tostring(err))
  end
end

-- ---------------------------------------------------------------------------
-- world-anchored markers (M3 rendering)
-- ---------------------------------------------------------------------------
--
-- The spike (lua/projspike_lua/) settled this approach: CSP's render.* API draws
-- primitives directly in 3D WORLD space, so the engine projects them with the
-- real scene camera in the transparent pass. Markers are frame-perfect at speed
-- and depth-tested (occluded by geometry) for free — no camera matrices, no
-- world-to-screen maths, no staleness.
--
-- What M3 proves here is narrow and specific: the markers stand at coordinates
-- EXTRACTED from the reference laps, not at coordinates typed into this file.
-- Salience staging (M4/M5) and the corner-speed HUD (M5) are not here; every
-- marker draws at the 'full' stage.

local MARKER_RADIUS_M = 1.5
local MARKER_AHEAD_M = 250.0    -- draw a corner's cue only on its approach
local MARKER_BEHIND_M = 30.0    -- ...and briefly past it, so it does not blink out
-- The disc is depth-tested at the marker's own height, and a marker's height is
-- the reference car's model origin, which is only APPROXIMATELY road level --
-- how approximately is a property of the car. At National (M235i) the disc came
-- out coplanar with the tarmac and disappeared into it; at International
-- (TT Cup) it cleared and drew. Lift it a few centimetres so it reads as a mark
-- ON the road for any car, without floating far enough to look detached.
local MARKER_DISC_LIFT_M = 0.06

local marker_draw_error = nil
local markers_drawn = 0

-- The presented stage for one element: the controller's, unless the block's
-- mode overrides it, unless the review override is set. Everything about the
-- decision is in lib/markers; this only supplies the inputs.
local function presented_stage(element)
  -- The review override deliberately bypasses the condition as well as the
  -- controller: its whole job is to show a stage's VISUAL on demand, and it is
  -- only reachable while idle (start_block clears it), so there is no block
  -- whose condition it could contradict.
  if stage_override ~= nil then return stage_override[element] end
  local stage = 'full'
  if block ~= nil and block.controller ~= nil then
    stage = controller.stages(block.controller)[element]
  end
  -- The mode is the block's when one is running, and the panel's selection
  -- otherwise, so an experimenter can check the `off` condition before starting.
  local mode = (block ~= nil) and block.condition or meta.condition
  return markers.presented_stage(mode, stage)
end

-- Draw one marker per its visual description. `v` comes from markers.visual and
-- says both how bright the cue is and which of its parts survive; nothing here
-- decides either.
local function draw_marker(m, v)
  -- Element colours are provisional -- they only have to be distinguishable and
  -- legible on track. The salience decision is in `v`, not in the colour.
  local col, label
  if m.element == 'braking' then
    col = rgbm(1.0, 0.35, 0.2, v.alpha)
    label = 'BRAKE ' .. m.corner_id
  else
    col = rgbm(0.3, 0.7, 1.0, v.alpha)
    label = 'APEX ' .. m.corner_id
  end
  local at = vec3(m.x, m.y, m.z)
  if v.disc then
    -- The disc is the part that survives to `minimal`, so it carries the whole
    -- cue at reduced salience and gets a little more of the alpha budget there
    -- than it does at full, where the cross and stalk are doing the pointing.
    local fill = v.label and 0.45 or 0.7
    render.circle(at + vec3(0, MARKER_DISC_LIFT_M, 0), vec3(0, 1, 0), MARKER_RADIUS_M,
      rgbm(col.r, col.g, col.b, v.alpha * fill))
  end
  if v.cross then render.debugCross(at, MARKER_RADIUS_M, col) end
  if v.stalk then render.debugLine(at, at + vec3(0, 2, 0), col) end
  if v.label then render.debugText(at + vec3(0, 2.2, 0), label, col, 1.0) end
end

local function draw_markers()
  local car = ac.getCar(0)
  if car == nil or marker_list == nil then return end
  local track_length_m = ac.getSim().trackLengthM
  if track_length_m == nil or track_length_m <= 0 then return end

  -- Per ELEMENT, not per block: the whole point of the design is that the three
  -- cues fade on independent trajectories, so braking can be hidden while apex
  -- is still at full.
  local braking = markers.visual(presented_stage('braking'), salience)
  local apex = markers.visual(presented_stage('apex'), salience)
  if braking.level == 'hidden' and apex.level == 'hidden' then
    markers_drawn = 0
    return
  end

  render.setDepthMode(render.DepthMode.Normal)   -- occluded by track geometry
  local n = 0
  for i = 1, #marker_list do
    local m = marker_list[i]
    local v = (m.element == 'braking') and braking or apex
    if v.level ~= 'hidden' and markers.in_view(m.spline, car.splinePosition,
                                               track_length_m, MARKER_AHEAD_M,
                                               MARKER_BEHIND_M) then
      draw_marker(m, v)
      n = n + 1
    end
  end
  markers_drawn = n
end

-- Recompute the corner-speed readout. Called from draw3d (which runs every
-- frame whether or not any window is open) so the cue window only ever renders
-- a value someone else already decided -- an immediate-mode window is a bad
-- place to keep a running minimum, because it stops being called the moment the
-- window is closed.
local function update_hud()
  local car = ac.getCar(0)
  if car == nil or hud_plans == nil then
    hud_readout = nil
    return
  end
  local track_length_m = ac.getSim().trackLengthM
  hud.update(hud_state, hud_plans, car.splinePosition, car.speedKmh)
  hud_readout = hud.readout(hud_plans, hud_state, car.splinePosition, car.speedKmh,
                            track_length_m, presented_stage('corner_speed'), salience)
end

-- CSP invokes this in the transparent scene pass (manifest.ini
-- [RENDER_CALLBACKS] TRANSPARENT = draw3d). Wrapped like every other fallible
-- step: a raise here would silently abandon the rest of the frame's drawing.
function draw3d()
  -- No condition check here. `off` is not a special case in the renderer:
  -- markers.presented_stage maps it to a hidden stage for every element, the
  -- same way it pins `static` to full. Handling the condition here as well was
  -- exactly the code path impl plan section 5 says it must not be.
  --
  -- Note also what is NOT gated on `show_markers`: the HUD's running minimum,
  -- below. The review toggle suppresses DRAWING, and suppressing a measurement
  -- with it would make the corner-speed readout wrong for the rest of the
  -- corner after any toggle -- the same distinction the probe stage rests on
  -- (withdrawal removes the scaffold, never the measurement).
  --
  -- CSP calls this render callback from the first frame, but init() only ran
  -- from windowMain -- so while the app window was still closed the lazy resolve
  -- below reached a nil `references_dir` and raised. Markers are meant to draw
  -- whether or not the window happens to be open, which means the render path
  -- has to be able to initialise too. Guarded on INPUTS, so whichever of the two
  -- entry points runs first does it and the other skips.
  if INPUTS == nil and init_error == nil then
    local ok, err = pcall(init)
    if not ok then init_error = tostring(err) end
  end
  if init_error ~= nil then return end
  if marker_list == nil then
    -- Resolve the reference lazily so markers appear whether or not the app
    -- window happens to be open.
    if ac.getCar(0) == nil then return end
    local ok, err = pcall(reference_status)
    if not ok then marker_draw_error = 'reference load: ' .. tostring(err); return end
    if marker_list == nil then return end
  end
  pcall(update_hud)
  if not show_markers then
    markers_drawn = 0
    return
  end
  local ok, err = pcall(draw_markers)
  if not ok then
    marker_draw_error = tostring(err)
  else
    -- Cleared on success. A draw error here can be transient (it was, for every
    -- frame before init ran), and a message that outlives the fault describes a
    -- state that no longer holds -- which is how a fixed fault reads as a live one.
    marker_draw_error = nil
  end
end

-- ---------------------------------------------------------------------------
-- window
-- ---------------------------------------------------------------------------

local function drawConfigStatus()
  for i, input in ipairs(INPUTS) do
    local r = results and results[i]
    if r == nil then
      ui.textColored(input.label .. ': (no result)', rgbm(1, 0.6, 0.2, 1))
    elseif r.ok then
      ui.textColored(input.label .. ': PASS', rgbm(0.3, 1, 0.3, 1))
    else
      ui.textColored(input.label .. ': FAIL', rgbm(1, 0.3, 0.3, 1))
      ui.text('  ' .. tostring(r.message))
    end
  end
end

local function drawIdleControls()
  ui.text('Block setup:')
  meta.participant_id = ui.inputText('Participant ID', meta.participant_id)

  -- Pair selects which reference table loads, so it is a radio group, not free
  -- text (the M2 lesson: constrain config fields at the UI, not just offline).
  ui.text('Pair:')
  for _, pr in ipairs(PAIRS) do
    if ui.radioButton(pr, meta.pair_id == pr) then meta.pair_id = pr end
    ui.sameLine()
  end
  ui.text('')

  ui.text('Sequence (opt):')
  for _, sq in ipairs(SEQUENCES) do
    if ui.radioButton(sq == '' and 'none' or sq, meta.sequence == sq) then
      meta.sequence = sq
    end
    ui.sameLine()
  end
  ui.text('')

  ui.text('Session:')
  for _, s in ipairs({ 1, 2, 3, 4 }) do
    if ui.radioButton('s' .. s, meta.session == s) then meta.session = s end
    ui.sameLine()
  end
  ui.text('')

  ui.text('Condition:')
  for _, c in ipairs({ 'adaptive', 'static', 'off' }) do
    if ui.radioButton(c, meta.condition == c) then meta.condition = c end
    ui.sameLine()
  end
  ui.text('')

  if ui.button('dev block: ' .. (meta.dev_block and 'YES' or 'no')) then
    meta.dev_block = not meta.dev_block
  end
  ui.sameLine()
  ui.text('(dev blocks may start without an annotation; ticks only)')

  if ui.button('dry run: ' .. (meta.dry_run and 'YES' or 'no')) then
    meta.dry_run = not meta.dry_run
  end
  ui.sameLine()
  ui.text('(M6 rehearsal: a full study block, flagged out of participant data)')

  ui.separator()

  -- Annotation (per track) and reference (per pair): both required unless this
  -- is a dev block.
  local in_session = ac.getCar(0) ~= nil
  local ann = in_session and annotation_status() or nil
  if ann ~= nil then
    if ann.ok then
      ui.textColored('annotation: OK (' .. ann.track .. ')', rgbm(0.5, 1, 0.5, 1))
    else
      ui.textColored('annotation: MISSING/INVALID -- ' .. tostring(ann.err), rgbm(1, 0.6, 0.2, 1))
    end
  end
  local ref = in_session and reference_status() or nil
  if ref ~= nil then
    if ref.ok then
      ui.textColored(string.format('reference: OK (%s, %d corner(s), %s)',
        ref.pair, ref.corners, ref.car), rgbm(0.5, 1, 0.5, 1))
      -- Marker toggle: G0 reviews every gate and zone on track, which is much
      -- easier with a way to flip the cues off and back on while parked there.
      -- Suppresses DRAWING of all three cues, for the on-track review. Not a
      -- condition and not logged: the controller, the evaluator and the HUD's
      -- running minimum all keep going underneath.
      if ui.button('draw cues: ' .. (show_markers and 'ON' or 'off')) then
        show_markers = not show_markers
      end
      ui.sameLine()
      ui.text(string.format('%d marker(s), %d in view', marker_list and #marker_list or 0,
        markers_drawn))
      if marker_draw_error ~= nil then
        ui.textColored('marker draw error: ' .. marker_draw_error, rgbm(1, 0.3, 0.3, 1))
      end
    else
      ui.textColored('reference: MISSING/INVALID -- ' .. tostring(ref.err), rgbm(1, 0.6, 0.2, 1))
    end
  end

  local inputs_ready = meta.dev_block or (ann ~= nil and ann.ok and ref ~= nil and ref.ok)
  local ready = allValid() and meta.participant_id ~= '' and valid_pair(meta.pair_id)
    and inputs_ready
  if not ready then
    if not inputs_ready and in_session then
      ui.textColored('Cannot start: a participant block needs a valid annotation for '
        .. 'this track AND a valid reference for this pair. Fix them and press '
        .. 'Reload configs, or tick "dev block" (which is how reference laps are recorded).',
        rgbm(1, 0.4, 0.4, 1))
    else
      ui.textColored('Need valid configs + participant + pair to start.', rgbm(1, 0.6, 0.2, 1))
    end
  end
  if ui.button('Start block') and ready then
    local ok, err = pcall(start_block)
    if not ok then
      block = nil
      init_error = 'start failed: ' .. tostring(err)
    end
  end
end

local function drawActiveStatus()
  ui.textColored('RECORDING: ' .. block.id, rgbm(0.3, 1, 0.3, 1))
  ui.text(string.format('laps: %d   ticks: %d   t: %.1f s',
    block.laps_completed, logger.count(block.log), block.t))
  ui.text('-> ' .. block.ticks_path)

  -- Pass tracking status.
  if block.tracker ~= nil then
    ui.textColored('pass tracking: ON (' .. block.track_id .. ')', rgbm(0.3, 1, 0.3, 1))
    local any = false
    for _, c in ipairs(block.tracker.corners) do
      local pc = block.pass_counts[c.id]
      if pc ~= nil then
        any = true
        local col = pc.last_valid and rgbm(0.7, 0.9, 0.7, 1) or rgbm(1, 0.7, 0.3, 1)
        ui.textColored(string.format('  %s: %d pass(es), last %s',
          c.id, pc.n, pc.last_valid and 'valid' or 'INVALID'), col)
      end
    end
    if not any then ui.text('  (no passes closed yet)') end
  else
    ui.textColored('pass tracking: OFF', rgbm(1, 0.6, 0.2, 1))
    ui.text('  ' .. tostring(block.ann_error))
  end

  -- M4 controller status. This is the live status line the M6 experimenter panel
  -- will own properly; it exists now because a block running an invisible state
  -- machine with no on-screen state is untestable in game.
  if block.controller ~= nil then
    ui.separator()
    ui.textColored('controller: ON   ' .. block.fade_events .. ' fade event(s)',
      rgbm(0.3, 1, 0.3, 1))
    local snap = controller.snapshot(block.controller)
    for _, element in ipairs(controller.ELEMENTS) do
      local el = snap[element]
      local note = ''
      if el.disabled then note = '  DISABLED (no applicable corners)'
      elseif el.pinned then note = '  PINNED (reversion cap)' end
      -- Probe countdown (impl plan section 7's panel spec). Read in the
      -- controller's own lap space -- block.last_lap is the raw car.lapCount the
      -- passes carry, NOT block.laps_completed, which is start-relative and
      -- would disagree with the machine it is reporting.
      local probe = ''
      if el.stage == 'probe' then
        local left = controller.probe_remaining(block.controller, element,
          block.last_lap or 0)
        if left ~= nil then
          probe = string.format('  PROBE: %d lap(s) left', left)
        end
      end
      ui.text(string.format('  %-13s %-8s %d/%d qualified%s%s%s',
        element, el.stage, #el.qualified_corners, el.applicable_corners,
        el.reversions > 0 and ('  ' .. el.reversions .. ' reversion(s)') or '',
        probe, note))
    end
    if block.null_criteria > 0 then
      -- A steady climb here means an element is starved of evidence and will
      -- stall rather than fade -- the residual risk of the null-is-no-evidence
      -- rule, and the thing to catch DURING a block rather than at analysis.
      ui.textColored('  ' .. block.null_criteria .. ' unmeasurable criterion/criteria '
        .. '(no evidence)', rgbm(1, 0.8, 0.4, 1))
    end
  elseif block.tracker ~= nil then
    ui.textColored('controller: OFF (no reference loaded)', rgbm(1, 0.6, 0.2, 1))
  end

  if block.fault ~= nil then
    ui.textColored('FAULT (sampling frozen):', rgbm(1, 0.3, 0.3, 1))
    ui.text('  ' .. block.fault)
    ui.text('  Stop to flush logs + write the fault into the manifest.')
  end
  ui.separator()
  if ui.button('Stop block') then
    local ok, err = pcall(stop_block)
    if not ok then init_error = 'stop failed: ' .. tostring(err) end
  end

  -- The abort (impl plan section 7). Two clicks, never one: a misclick on a
  -- single red button would stamp a participant's block unusable, and a block
  -- cannot be re-run on the same person. Arming shows the reason list, because
  -- an abort with no recorded reason is the one the dataset README cannot
  -- explain later.
  ui.separator()
  if not abort_armed then
    if ui.button('ABORT BLOCK') then abort_armed = true end
  else
    ui.textColored('ABORT: pick a reason (this marks the block unusable)',
      rgbm(1, 0.35, 0.35, 1))
    for _, reason in ipairs(manifest.ABORT_REASONS) do
      if ui.button('abort: ' .. reason) then
        local ok, err = pcall(stop_block, reason)
        if not ok then init_error = 'abort failed: ' .. tostring(err) end
        abort_armed = false
        return
      end
    end
    if ui.button('cancel abort') then abort_armed = false end
  end
end

-- Capture one landmark at the car's current spline + world position.
local CORNER_TYPES = { 'slow', 'medium', 'fast', 'hairpin', 'chicane', 'kink' }

local function capture_mark(role)
  local car = ac.getCar(0)
  if car == nil then
    last_capture = 'no car state'
    return
  end
  if amark.corner_id == '' then
    last_capture = 'set a corner id first'
    return
  end
  local pos = { car.position.x, car.position.y, car.position.z }
  annotator.add_mark(annot, amark.corner_id, amark.corner_type, amark.compound,
    role, car.splinePosition, pos)
  last_capture = string.format('%s %s @ spline %.4f', amark.corner_id, role, car.splinePosition)
end

local function write_marks()
  local stamp = os.date('%Y%m%d_%H%M%S')
  local path = data_dir .. '/marks_' .. sanitize(annot.track) .. '_' .. stamp .. '.jsonl'
  io.createDir(data_dir)
  local ok = io.save(path, annotator.to_jsonl(annot))
  if ok then
    last_marks = { path = path, count = annotator.count(annot) }
  else
    last_capture = 'WRITE FAILED (io.save returned false)'
  end
end

local function drawAnnotator()
  local car = ac.getCar(0)
  local track = (car ~= nil) and track_full_id() or '(no car / track yet)'
  ui.text('Drive-and-mark annotator')
  ui.text('track: ' .. track)
  if car ~= nil then
    ui.text(string.format('live spline: %.4f', car.splinePosition))
  end
  ui.separator()

  if annot == nil then
    if car == nil then
      ui.textColored('Enter a session (on track) to begin annotating.', rgbm(1, 0.6, 0.2, 1))
    elseif ui.button('Begin annotating ' .. track) then
      annot = annotator.new(track)
      last_capture = nil
    end
    return
  end

  ui.text('Corner:')
  amark.corner_id = ui.inputText('Corner id', amark.corner_id)
  for _, t in ipairs(CORNER_TYPES) do
    if ui.radioButton(t, amark.corner_type == t) then amark.corner_type = t end
    ui.sameLine()
  end
  ui.text('')
  if ui.button('compound: ' .. (amark.compound and 'YES' or 'no')) then
    amark.compound = not amark.compound
  end

  ui.separator()
  ui.text('Mark (captures current spline):')
  for _, role in ipairs(annotator.ROLES) do
    if ui.button(role) then
      local ok, err = pcall(capture_mark, role)
      if not ok then last_capture = 'capture error: ' .. tostring(err) end
    end
    ui.sameLine()
  end
  ui.text('')
  if last_capture ~= nil then ui.text('last: ' .. last_capture) end
  ui.text(string.format('marks buffered: %d', annotator.count(annot)))

  ui.separator()
  if ui.button('Write marks file') then
    local ok, err = pcall(write_marks)
    if not ok then last_capture = 'write error: ' .. tostring(err) end
  end
  ui.sameLine()
  if ui.button('Discard buffer') then annot = nil; last_capture = nil end
  if last_marks ~= nil then
    ui.textColored(string.format('wrote %d marks -> %s', last_marks.count, last_marks.path),
      rgbm(0.7, 0.8, 1, 1))
  end
end

-- ---------------------------------------------------------------------------
-- reference-lap recording (M3 / eval-plan Phase 0)
-- ---------------------------------------------------------------------------
--
-- The expert reference is "the AC AI at 95-100% strength, n laps, fixed setup,
-- logged through this project's own telemetry pipeline". Getting the AI to
-- drive THE PLAYER CAR (physics.setCarAutopilot) rather than recording a
-- separate AI opponent is the point: the reference laps then share the
-- participant's car, the participant's fixed setup, and the same ac.getCar(0)
-- sampling path, so AI laps, human reference laps and participant laps differ
-- only in who is driving. An AI opponent would run its own car entry on AC's
-- own setup, and the brake points would not be comparable.
--
-- Autopilot needs physics scripting to be permitted in the session
-- (physics.allowed()); if it is not, this panel says so rather than silently
-- doing nothing. Every call is pcall-wrapped: an unavailable physics API must
-- not take the window down mid-draw.

local AI_STRENGTHS = { 95, 98, 100 }   -- eval plan: 95-100%
local refrec = { strength = 98, autopilot = false, note = nil }

local function physics_allowed()
  local ok, allowed = pcall(function() return physics.allowed() end)
  return ok and allowed == true
end

local function apply_ai_strength()
  local ok, err = pcall(function() physics.setAILevel(0, refrec.strength / 100.0) end)
  refrec.note = ok and string.format('AI level set to %d%%', refrec.strength)
    or ('setAILevel failed: ' .. tostring(err))
end

local function set_autopilot(active)
  local ok, err = pcall(function() physics.setCarAutopilot(active) end)
  if ok then
    refrec.autopilot = active
    refrec.note = active and 'autopilot ON (AC marks the lap invalid; TRACE counts laps itself)'
      or 'autopilot OFF'
  else
    refrec.note = 'setCarAutopilot failed: ' .. tostring(err)
  end
end

local function drawReferenceMode()
  local car = ac.getCar(0)
  ui.text('Reference-lap recording (Phase 0)')
  if car == nil then
    ui.textColored('Enter a session (on track) first.', rgbm(1, 0.6, 0.2, 1))
    return
  end
  ui.text('track: ' .. track_full_id() .. '   car: ' .. tostring(car_id()))
  ui.text(string.format('track length: %.1f m', ac.getSim().trackLengthM))
  ui.separator()

  if not physics_allowed() then
    ui.textColored('physics scripting NOT allowed in this session -- autopilot is '
      .. 'unavailable. Drive the human reference laps by hand here, and record the '
      .. 'AI laps in a session that permits it.', rgbm(1, 0.6, 0.2, 1))
  end

  ui.text('AI strength:')
  for _, s in ipairs(AI_STRENGTHS) do
    if ui.radioButton(s .. '%', refrec.strength == s) then
      refrec.strength = s
      apply_ai_strength()
    end
    ui.sameLine()
  end
  ui.text('')
  if ui.button('Apply AI strength') then apply_ai_strength() end
  ui.sameLine()
  ui.text(string.format('(car reports aiLevel %.2f)', car.aiLevel or -1))

  ui.separator()
  if ui.button(refrec.autopilot and 'Autopilot: ON -> turn off' or 'Autopilot: off -> turn ON') then
    set_autopilot(not refrec.autopilot)
  end
  ui.textColored('AI-controlled: ' .. tostring(car.isAIControlled), rgbm(0.7, 0.8, 1, 1))
  if refrec.note ~= nil then ui.text(refrec.note) end

  ui.separator()
  ui.text('To record: switch to "record", tick DEV BLOCK, Start block, drive/watch')
  ui.text('12 clean laps, Stop. Then extract offline with trace_kit.reference.')
  ui.text('Dev block is required -- the reference table cannot exist yet, so the')
  ui.text('participant gate would (correctly) refuse to start.')
end

-- ---------------------------------------------------------------------------
-- the corner-speed indicator (M5) — the participant-facing window
-- ---------------------------------------------------------------------------
--
-- The third UI element, and the only one that is not world-anchored. It lives in
-- its OWN app window, separate from the experimenter panel, for the obvious
-- reason: the panel is for the researcher and must never be on the participant's
-- screen, while this is a study stimulus and must be.
--
-- Why an app window rather than a fixed screen overlay. It uses only the ui.*
-- calls already proven in this app, the experimenter positions it once
-- (AC persists app window positions, and the apparatus fixes the display and
-- seating across participants anyway), and it can be shown or hidden without a
-- code path. The alternative — `ui.beginTransparentWindow` at a computed
-- centre-bottom position — is a nicer HUD and is the upgrade path if the window
-- chrome proves distracting at the G2 review; it is NOT taken now because it
-- would be an unverified API on the one element a participant stares at.
-- Recorded here as an M5 decision so the choice is reviewable rather than
-- accidental.
--
-- Note what this function does NOT do: no minimum tracking, no corner
-- selection, no salience decision. All of that is lib/hud, computed every frame
-- from draw3d, because an immediate-mode window stops being called the moment
-- it is closed and a running minimum kept here would silently stop running.

local CUE_OK = rgbm(0.45, 0.95, 0.55, 1)
local CUE_OFF = rgbm(1.0, 0.75, 0.3, 1)

local function drawCueWindow()
  if INPUTS == nil and init_error == nil then
    local ok, err = pcall(init)
    if not ok then init_error = tostring(err) end
  end
  local r = show_markers and hud_readout or nil
  if r == nil then
    -- Deliberately blank rather than explanatory: a participant must not be
    -- shown apparatus state. Between corners, and whenever the element is
    -- withdrawn, this window is simply empty.
    return
  end

  local a = r.alpha
  if r.show_label then
    ui.textColored('CORNER ' .. r.corner_id, rgbm(0.75, 0.8, 0.9, a))
  end

  -- The target is the part that survives to `minimal`: it is the number the
  -- driver is trying to reach, and the one thing the cue exists to supply.
  ui.pushFont(ui.Font.Title)
  ui.textColored(string.format('%.0f', r.target_kmh), rgbm(1, 1, 1, a))
  ui.popFont()
  ui.sameLine()
  ui.textColored('km/h', rgbm(0.8, 0.8, 0.8, a))

  if r.show_actual and r.actual_kmh ~= nil then
    local col = rgbm(0.8, 0.85, 0.95, a)
    if r.within_band ~= nil then
      col = r.within_band and rgbm(CUE_OK.r, CUE_OK.g, CUE_OK.b, a)
        or rgbm(CUE_OFF.r, CUE_OFF.g, CUE_OFF.b, a)
    end
    if r.phase == 'approach' then
      -- Still slowing: show the live speed, with no verdict on it. A red/green
      -- judgement here would be judging a number that is not the metric.
      ui.textColored(string.format('now %.0f', r.actual_kmh), col)
    else
      ui.textColored(string.format('min %.0f  (%+.0f)', r.actual_kmh,
        r.deviation_kmh or 0), col)
    end
  end
end

function windowCue(dt)
  local ok, err = pcall(drawCueWindow)
  if not ok then
    -- Same defensive rule as the panel: an uncaught error mid-draw silently
    -- abandons the rest of the frame. On the participant's window a bare error
    -- string is still better than a window that mysteriously half-renders,
    -- because the experimenter can see it during a block.
    ui.textColored('cue error: ' .. tostring(err), rgbm(1, 0.3, 0.3, 1))
  end
end

function windowMain(dt)
  if INPUTS == nil and init_error == nil then
    local ok, err = pcall(init)
    if not ok then init_error = tostring(err) end
  end

  ui.text('TRACE runtime - M5 (sampler + passes + controller + staged cues)')
  ui.separator()

  if init_error ~= nil then
    ui.textColored('ERROR:', rgbm(1, 0.3, 0.3, 1))
    ui.text(init_error)
    if ui.button('Retry') then
      init_error = nil
      INPUTS = nil
    end
    return
  end

  drawConfigStatus()
  ui.separator()

  if block ~= nil then
    drawActiveStatus()
  else
    -- Mode switch: record a block, annotate the track, or set up reference laps.
    for _, m in ipairs({ 'record', 'annotate', 'reference' }) do
      if ui.radioButton(m, ui_mode == m) then ui_mode = m end
      ui.sameLine()
    end
    ui.text('')
    ui.separator()

    if ui_mode == 'annotate' then
      drawAnnotator()
      return
    end
    if ui_mode == 'reference' then
      drawReferenceMode()
      return
    end

    -- M5 exit test: "scripted controller states produce the intended visuals".
    -- Driving an element to `probe` takes ~9 laps, so the review pins stages by
    -- hand instead. Only offered while IDLE, and start_block clears it, so it
    -- can never be live in a recording.
    ui.separator()
    ui.text('Salience review (idle only; cleared on Start):')
    -- `mixed` pins the three elements to DIFFERENT stages on purpose. Per-element
    -- independence is the design's contribution (a), and it is the one thing on
    -- the review checklist a uniform override cannot show: with all three pinned
    -- alike, a renderer that ignored the element and used one global stage would
    -- look exactly right.
    local presets = { 'controller', 'full', 'reduced', 'probe', 'mixed' }
    for _, name in ipairs(presets) do
      local active = (name == 'controller' and stage_override == nil)
        or (stage_override ~= nil and stage_override.name == name)
      if ui.radioButton(name, active) then
        if name == 'controller' then
          stage_override = nil
        elseif name == 'mixed' then
          stage_override = { name = name, braking = 'full',
            corner_speed = 'reduced', apex = 'probe' }
        else
          stage_override = { name = name, braking = name, corner_speed = name, apex = name }
        end
      end
      ui.sameLine()
    end
    ui.text('')
    if stage_override ~= nil then
      ui.textColored(string.format(
        'OVERRIDE ACTIVE -- braking=%s corner_speed=%s apex=%s. Bench tool, not a condition.',
        stage_override.braking, stage_override.corner_speed, stage_override.apex),
        rgbm(1, 0.6, 0.2, 1))
    end
    if hud_readout ~= nil then
      ui.text(string.format('corner-speed cue: %s %s  target %.0f  band %.1f',
        hud_readout.corner_id, hud_readout.phase, hud_readout.target_kmh,
        hud_readout.band_kmh))
    else
      ui.text('corner-speed cue: (nothing to show here)')
    end
    ui.separator()

    if ui.button('Reload configs') then
      local ok, err = pcall(reload)
      if not ok then init_error = 'reload failed: ' .. tostring(err) end
    end
    drawIdleControls()
    if last_summary ~= nil then
      ui.separator()
      ui.textColored('Last block: ' .. last_summary.id, rgbm(0.7, 0.8, 1, 1))
      if last_summary.aborted ~= nil then
        ui.textColored('  ABORTED (' .. last_summary.aborted .. ') -- excluded '
          .. 'from participant data', rgbm(1, 0.35, 0.35, 1))
      end
      ui.text(string.format('  %d laps, %d ticks%s',
        last_summary.laps, last_summary.ticks,
        last_summary.fault and ('  (FAULTED: ' .. last_summary.fault .. ')') or ''))
      if last_summary.tracking then
        ui.text(string.format('  %d pass record(s) -> passes_*.jsonl', last_summary.passes))
        if last_summary.controller_on then
          ui.text(string.format('  %d fade event(s) -> fades_*.jsonl', last_summary.fades))
          local parts = {}
          for _, element in ipairs(controller.ELEMENTS) do
            parts[#parts + 1] = element .. '=' .. tostring(last_summary.stages[element])
          end
          ui.text('  final stages: ' .. table.concat(parts, '  '))
          if last_summary.null_criteria > 0 then
            ui.text(string.format('  %d unmeasurable criterion/criteria',
              last_summary.null_criteria))
          end
        else
          ui.text('  controller was OFF (no reference)')
        end
      else
        ui.text('  pass tracking was OFF (' .. tostring(last_summary.ann_error) .. ')')
      end
      ui.text('  -> ' .. last_summary.ticks_path)
    end
  end
end
