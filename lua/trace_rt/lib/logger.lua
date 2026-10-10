-- logger.lua — buffered writer for the block's output streams.
--
-- impl-plan module 7 (logging half). CSP's io has no append/handle API (only
-- whole-file io.save / io.saveAsync), so the strategy is: hold every row of the
-- block in memory and rewrite the whole file on flush. Flushing only on lap
-- boundaries (and block end) keeps that rewrite off the per-frame path — the
-- M1 risk register's answer to "file I/O stalls the render thread". A 30-min
-- block is ~36k rows / a few MB; rewriting that ~15 times over the block is
-- cheap and happens while the car is crossing the start/finish line.
--
-- Two stream shapes share this one buffer: the 20 Hz ticks CSV (a header line
-- then rows) and the per-pass JSONL stream (no header, one JSON object per row).
-- Pass `nil`/"" as the header for the headerless (JSONL) case.
--
-- The actual disk write is injected as `save_fn(path, text) -> bool` so the
-- buffer logic is pure and headless-testable; trace_rt.lua passes a thin
-- wrapper over io.save. No ac.* / io.* in this module.

local M = {}

-- Create a logger holding an optional header line and a growing list of row
-- strings. header nil or "" => headerless (JSONL): serialize emits rows only.
function M.new(header)
  if header == nil then header = "" end
  if type(header) ~= "string" then
    error("logger.new: header must be a string or nil")
  end
  return {
    header = header,
    rows = {},
    flushed_rows = 0,   -- rows successfully written to disk by the last flush
  }
end

-- Append one already-formatted CSV row (no trailing newline).
function M.add(logger, row)
  logger.rows[#logger.rows + 1] = row
end

-- Number of rows buffered (flushed + unflushed).
function M.count(logger)
  return #logger.rows
end

-- Full file text: optional header line, every row, trailing newline. Pure.
-- Headerless + no rows => "" (an empty file, not a stray blank line).
function M.serialize(logger)
  local has_header = logger.header ~= ""
  if #logger.rows == 0 then
    return has_header and (logger.header .. "\n") or ""
  end
  local body = table.concat(logger.rows, "\n") .. "\n"
  return has_header and (logger.header .. "\n" .. body) or body
end

-- Write the whole buffer through the injected save_fn. Returns true on success;
-- on success records how many rows are now durable. A failed flush leaves the
-- buffer intact so the next flush retries the same content.
function M.flush(logger, path, save_fn)
  local text = M.serialize(logger)
  local ok = save_fn(path, text)
  if ok then
    logger.flushed_rows = #logger.rows
  end
  return ok and true or false
end

-- True if there are rows not yet on disk (something to flush).
function M.dirty(logger)
  return #logger.rows > logger.flushed_rows
end

return M
