-- manifest.lua — assembles the per-block session manifest (pure).
--
-- impl-plan data contract `session_manifest.json` (schema:
-- schemas/session_manifest.schema.json). Written once per block by trace_rt.lua;
-- this module only builds the Lua table, so it is headless-testable: a kit test
-- builds a manifest here, json.encode's it, and validates it against the schema
-- in Python (the same cross-language agreement pattern as the M0 validators).
--
-- The SHA-256 config hashing and the ISO timestamps are produced at the AC
-- boundary (ac.checksumSHA256, os.date) and passed in as plain strings — none
-- of that lives here. No ac.* / io.*.

local json = require('lib/json')   -- for json.null only

local M = {}

-- Build the manifest written at block start. All fields the schema marks
-- required must be present here.
--   meta     = { block_id, participant_id, session(int 1..4),
--                condition("adaptive"|"static"|"off"), pair_id, sequence?,
--                dev_block? }
--   hashes   = { annotation, reference, controller_config }  (64-hex strings;
--              annotation and reference may each be nil on a dev block started
--              without one)
--   versions = { app, csp, ac }                              (strings)
--   started_at = ISO-8601 local timestamp string
--   meta may also carry track_id, car_id, track_length_m (M3 apparatus
--   provenance); each is stamped only when supplied.
function M.build(meta, hashes, versions, started_at)
  local m = {
    schema_version = 1,
    block_id = meta.block_id,
    participant_id = meta.participant_id,
    session = meta.session,
    condition = meta.condition,
    pair_id = meta.pair_id,
    config_hashes = {
      -- A nil hash would make the key vanish, but the schema requires it
      -- present; json.null keeps it present and explicitly empty. Only ever
      -- reached on a dev block started without a valid annotation/reference —
      -- which is exactly how the reference laps themselves are recorded.
      annotation = hashes.annotation or json.null,
      reference = hashes.reference or json.null,
      controller_config = hashes.controller_config,
    },
    versions = {
      app = versions.app,
      csp = versions.csp,
      ac = versions.ac,
    },
    started_at = started_at,
  }
  -- sequence is optional (only meaningful for session-2 training blocks); set
  -- it only when supplied so json.encode omits the key otherwise.
  if meta.sequence ~= nil then
    m.sequence = meta.sequence
  end
  -- Apparatus provenance (M3). track_id/car_id make a block's pair_id
  -- verifiable against the reference table it hashed; track_length_m pins the
  -- scale every spline-to-metre conversion in the analysis depends on.
  if meta.track_id ~= nil then m.track_id = meta.track_id end
  if meta.car_id ~= nil then m.car_id = meta.car_id end
  if meta.track_length_m ~= nil then m.track_length_m = meta.track_length_m end
  -- dev_block marks a scratch/dev recording that opted out of the annotation
  -- gate. Set only when true, so study blocks carry no such key at all and a
  -- dev block can never be read as participant data.
  if meta.dev_block then
    m.dev_block = true
  end
  -- dry_run marks a protocol-rehearsal block (M6). Unlike a dev block it is a
  -- full study block in every other respect -- it passes both gates and runs
  -- the controller -- so the flag is the only thing that keeps the rehearsal
  -- dataset out of the participant dataset.
  if meta.dry_run then
    m.dry_run = true
  end
  return m
end

-- Record that the AC AI drove this block, and at what strength.
--
-- Whether a block is an AI reference recording or a human one is the single
-- most load-bearing fact about a reference block, and it was previously not
-- recorded anywhere — the first real reference block could only be identified
-- as AI-driven by noticing its lap times agreed to within one 20 Hz tick. That
-- is an inference, not provenance. The caller polls `car.isAIControlled` during
-- the block (ground truth from the sim, not the UI toggle, so engaging
-- autopilot after the start is still caught) and stamps it here.
--
-- Set only when the AI actually drove, so a human-driven block carries no key
-- at all and the field never has to be read as three-valued.
function M.stamp_autopilot(m, ai_level_pct)
  m.autopilot = true
  if type(ai_level_pct) == 'number' and ai_level_pct >= 0 then
    m.ai_level_pct = ai_level_pct
  end
  return m
end

-- Valid abort reasons, in panel display order. A closed list here and a radio
-- group on the panel: the M2 sequence-field typo wrote a schema-invalid manifest
-- that only surfaced hours later at the integrity check, so a manifest field is
-- never free text.
M.ABORT_REASONS = {
  'participant_request',
  'sim_or_app_crash',
  'hardware_fault',
  'experimenter_error',
  'protocol_deviation',
  'other',
}

function M.is_abort_reason(v)
  for i = 1, #M.ABORT_REASONS do
    if M.ABORT_REASONS[i] == v then return true end
  end
  return false
end

-- Mark a block as aborted by the experimenter. Follows the `dev_block` pattern:
-- the key is present only when true, so its mere presence excludes the block
-- from participant data. The caller still finalizes and still flushes every
-- stream — an abort discards the BLOCK, never the record of what happened, so
-- the partial logs stay auditable (and the integrity checker still reads them).
function M.mark_aborted(m, reason)
  m.aborted = true
  m.abort_reason = M.is_abort_reason(reason) and reason or 'other'
  return m
end

-- Stamp the closing fields onto a built manifest. `faults` is a list of
-- { at = <iso>, message = <string> }; attached only when non-empty so the
-- manifest never carries an empty array (which the json encoder would emit as
-- "[]" — harmless here, but we keep the document minimal).
function M.finalize(m, ended_at, laps_completed, faults)
  m.ended_at = ended_at
  m.laps_completed = laps_completed
  if faults ~= nil and #faults > 0 then
    m.faults = faults
  end
  return m
end

return M
