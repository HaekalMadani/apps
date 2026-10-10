-- annotator.lua — pure capture buffer for the drive-and-mark annotator (§2.2).
--
-- The experimenter drives slowly and, at each landmark, presses a labelled
-- button in trace_rt's annotator mode. Each press calls add_mark() with the
-- current spline + world position and a role tag. to_jsonl() serialises the
-- buffer one mark per line; trace_rt hands that text to io.save, and the offline
-- kit/trace_kit/annotate.py groups marks by corner into a draft
-- annotation_<track>.json for manual cleanup. Keeping the *interpretation* in
-- Python (which roles map to which gates/zones) keeps this Lua side thin.
--
-- Pure: no ac.* / io.*. Plain Lua 5.1, helpers called directly.

local json = require('lib/json')

local M = {}

-- The landmark roles a mark can carry. annotate.py maps these to the annotation
-- schema (entry/exit gates, braking + corner_speed zone bounds, apex gates).
M.ROLES = {
  "entry", "brake_start", "brake_end", "apex", "cs_start", "cs_end", "exit",
}

function M.is_role(role)
  for i = 1, #M.ROLES do
    if M.ROLES[i] == role then return true end
  end
  return false
end

-- Fresh capture buffer for one track.
function M.new(track)
  return { track = track, marks = {} }
end

-- Record one landmark. `pos` is a 3-element {x,y,z} world position. Raises on an
-- unknown role or a missing/short corner id so a fat-fingered capture fails loud
-- rather than writing a silently-wrong annotation later.
function M.add_mark(state, corner_id, corner_type, compound, role, spline, pos)
  if type(corner_id) ~= "string" or #corner_id < 1 then
    error("annotator.add_mark: corner_id must be a non-empty string")
  end
  if not M.is_role(role) then
    error("annotator.add_mark: unknown role '" .. tostring(role) .. "'")
  end
  state.marks[#state.marks + 1] = {
    track = state.track,         -- self-describing so annotate.py needs no filename parsing
    corner_id = corner_id,
    type = corner_type,
    compound = compound and true or false,
    role = role,
    spline = spline,
    pos = { pos[1], pos[2], pos[3] },
  }
  return state.marks[#state.marks]
end

function M.count(state)
  return #state.marks
end

-- Serialise the buffer as JSON-Lines (one mark object per line, trailing
-- newline). Order is capture order, which annotate.py does not depend on.
function M.to_jsonl(state)
  local lines = {}
  for i = 1, #state.marks do
    lines[i] = json.encode(state.marks[i])
  end
  if #lines == 0 then return "" end
  return table.concat(lines, "\n") .. "\n"
end

return M
