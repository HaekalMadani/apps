-- projspike_lua : CSP Lua world-anchored marker spike (THROWAWAY).
--
-- Why Lua instead of the Python app:
--   CSP's Lua `render` API draws primitives directly in 3D WORLD space. The
--   engine projects them with the real scene camera during the transparent
--   render pass, so a marker is frame-perfect at any speed AND depth-tested
--   (occluded by track geometry) for free. No camera matrices, no manual
--   world-to-screen, none of the broken Python ext_ matrix bindings.
--
-- This answers the same three spike questions as the Python attempt:
--   1. Current camera in the render callback?  -> guaranteed; projection is
--      engine-side, in the same pass as the scene.
--   2. Holds at 200+ km/h?                      -> drive at the marker; watch.
--   3. Per-frame cost?                          -> a handful of render.* calls.
--
-- Every render./ac. call below is from CSP's shipped Lua SDK
-- (extension/internal/lua-sdk).

-- ===== CONFIG =====
local ANCHOR_DISTANCE = 25.0   -- metres ahead of the car when the anchor freezes
local MARKER_RADIUS   = 1.5    -- metres
local OCCLUDE = true           -- true : depth-tested (hidden behind geometry)
                               -- false: drawn on top, overlay-style (no depth)

-- ===== STATE =====
local anchor = nil             -- frozen world position (vec3); set once
local frames = 0               -- 3D-callback frame counter
local distToAnchor = 0

-- Freeze the marker once: ANCHOR_DISTANCE metres straight ahead of the car.
-- car.position sits at the model origin (≈ road level), so no vertical drop.
local function captureAnchor()
  local car = ac.getCar(0)
  if not car then return end
  anchor = car.position + car.look * ANCHOR_DISTANCE
end

-- 3D render callback (see manifest [RENDER_CALLBACKS] TRANSPARENT = draw3d).
-- Draw in world space; CSP projects with the live scene camera.
function draw3d()
  frames = frames + 1
  if anchor == nil then
    captureAnchor()
    return
  end

  if OCCLUDE then
    render.setDepthMode(render.DepthMode.Normal)   -- occluded by geometry
  else
    render.setDepthMode(render.DepthMode.Off)      -- always on top
  end

  -- Flat disc on the track surface (orthogonal to world up)...
  render.circle(anchor, vec3(0, 1, 0), MARKER_RADIUS, rgbm(0, 1, 0, 0.45))
  -- ...a cross at the point, a stalk straight up, and a floating label.
  render.debugCross(anchor, MARKER_RADIUS, rgbm(0, 1, 0, 1))
  render.debugLine(anchor, anchor + vec3(0, 2, 0), rgbm(0, 1, 0, 1))
  render.debugText(anchor + vec3(0, 2.2, 0), "BRAKE", rgbm(1, 1, 1, 1), 1.0)
end

-- App window: live diagnostics so the spike is self-reporting.
function windowMain(dt)
  local car = ac.getCar(0)
  if car and anchor then
    distToAnchor = (car.position - anchor):length()
  end

  ui.text("projspike lua (world-anchored)")
  if anchor then
    ui.text(string.format("anchor: %.1f  %.1f  %.1f", anchor.x, anchor.y, anchor.z))
  else
    ui.text("anchor: capturing on first 3D frame...")
  end
  ui.text(string.format("dist to anchor: %.1f m", distToAnchor))
  if car then
    ui.text(string.format("speed: %.0f km/h", car.speedKmh))
  end
  ui.text(string.format("3D frames: %d", frames))
  ui.text("depth: " .. (OCCLUDE and "occluded by geometry" or "always on top"))
end
