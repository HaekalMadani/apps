-- hash.lua — SHA-256 config hashing for the session manifest.
--
-- impl-plan M1: "Logs the SHA-256 of each config into the session manifest."
-- The manifest schema requires 64-char lowercase hex. ac.checksumSHA256 returns
-- a `string?` of UNSPECIFIED encoding (the SDK doc doesn't say hex vs raw
-- bytes), so to_hex normalises both possibilities and is the headless-testable
-- core; sha256_hex is the thin ac.* boundary called only in-game.

local M = {}

-- Normalise ac.checksumSHA256's return into 64-char lowercase hex. Accepts:
--   * 32 raw bytes  -> hex-encode each byte (the likely binary-digest case);
--   * 64 hex chars  -> validate + lowercase (if CSP already returns hex).
-- Anything else is an error rather than a silently malformed hash.
function M.to_hex(raw)
  if type(raw) ~= "string" then
    error("hash.to_hex: expected string, got " .. type(raw))
  end
  if #raw == 32 then
    local out = {}
    for i = 1, 32 do
      out[i] = string.format("%02x", string.byte(raw, i))
    end
    return table.concat(out)
  elseif #raw == 64 then
    local lower = string.lower(raw)
    if string.match(lower, "^[0-9a-f]+$") then
      return lower
    end
    error("hash.to_hex: 64-char input is not hexadecimal")
  end
  error("hash.to_hex: unexpected SHA-256 length " .. #raw)
end

-- Hash a string with CSP's SHA-256 and return 64-hex. In-game only (ac is the
-- injected runtime global); to_hex above carries the testable logic.
function M.sha256_hex(data)
  local raw = ac.checksumSHA256(data)
  if raw == nil then
    error("hash.sha256_hex: ac.checksumSHA256 returned nil")
  end
  return M.to_hex(raw)
end

return M
