-- trace_rt : TRACE in-game runtime (CSP Lua app).
--
-- M0 state: config loader only. Loads the three runtime input files, runs them
-- through lib/validate.lua, and shows per-file PASS/FAIL in the app window.
-- This is the seed of impl-plan module 1 ("refuses to start a block on any
-- validation error"). No sampling, no logging, no rendering yet - that is
-- M1/M2/M5.
--
-- NOTE (M0): the annotation and reference files loaded here are the FAKE
-- fixtures from configs/examples/. Real files replace them in M2 (annotation)
-- and M3 (reference); the paths then move out of examples/.
--
-- Defensive by design: CSP draws app windows in immediate mode, so if any call
-- in windowMain raises, CSP silently abandons the rest of that frame's draw
-- (you see the lines printed so far and nothing after). Every fallible step
-- here is therefore wrapped in pcall and its error surfaced as on-window text,
-- so the window can never go half-blank without saying why. ASCII only.

local json = require('lib/json')
local validate = require('lib/validate')

-- Built during init(); see below. Kept module-scoped so a load failure is
-- reportable rather than fatal.
local INPUTS = nil
local results = nil      -- list of { ok, message } aligned to INPUTS
local init_error = nil   -- string set if init() itself failed

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
  for i, input in ipairs(INPUTS) do
    local ok, res = pcall(loadAndValidate, input)
    if ok then
      results[i] = res
    else
      results[i] = { ok = false, message = 'validator crashed: ' .. tostring(res) }
    end
  end
end

-- One-time setup: resolve the apps folder, build the input list, do a first
-- load. Anything that can raise lives here under a pcall in windowMain.
local function init()
  local root = ac.getFolder(ac.FolderID.ACApps)
  INPUTS = {
    {
      label = 'controller_config',
      path = root .. '/configs/controller_config.json',
      check = validate.controller_config,
    },
    {
      label = 'annotation (example fixture)',
      path = root .. '/configs/examples/annotation_example_track.json',
      check = validate.annotation,
    },
    {
      label = 'reference (example fixture)',
      path = root .. '/configs/examples/reference_example_pair.json',
      check = validate.reference,
    },
  }
  reload()
end

local function allValid()
  if results == nil then return false end
  for _, r in ipairs(results) do
    if not r.ok then return false end
  end
  return true
end

function windowMain(dt)
  -- Lazy init on first frame, with the error captured for display.
  if INPUTS == nil and init_error == nil then
    local ok, err = pcall(init)
    if not ok then
      init_error = tostring(err)
    end
  end

  ui.text('TRACE runtime - M0 (config validation only)')
  ui.separator()

  if init_error ~= nil then
    ui.textColored('INIT ERROR:', rgbm(1, 0.3, 0.3, 1))
    ui.text(init_error)
    if ui.button('Retry') then
      init_error = nil
      INPUTS = nil
    end
    return
  end

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

  ui.separator()
  if allValid() then
    ui.textColored('All configs valid.', rgbm(0.3, 1, 0.3, 1))
  else
    ui.textColored('Validation errors - block start would be refused.', rgbm(1, 0.6, 0.2, 1))
  end

  if ui.button('Reload configs') then
    local ok, err = pcall(reload)
    if not ok then
      init_error = 'reload failed: ' .. tostring(err)
    end
  end
end
