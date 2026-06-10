# projspike_lua — world-anchored marker spike

A throwaway technical spike that de-risks the **world-anchored braking-point
marker** before the main study is built. It draws one marker, frozen to a fixed
point on the track, that stays locked to its spot as the car approaches at speed
and as the camera swings through a corner.

**Status: PASSED.** World-anchored rendering is viable in Assetto Corsa, via
**Custom Shaders Patch (CSP) Lua**. This document records what was tested, what
failed, why, and the resulting design decision, so it can be folded into the
main write-up.

---

## 1. What the spike had to answer

The braking-point and apex markers are two of the study's three UI elements, so
their rendering had to be proven before anything else. "There is no lag to
accumulate" was a *prediction* resting on the engine actually exposing a usable,
current camera transform every render frame. Three questions:

1. **Current camera in the render callback** — is the marker projected with the
   *same* camera the scene is drawn with, in the same pass (not a frame-stale
   copy)?
2. **Lock at speed** — does the marker stay glued to its world point during a
   200+ km/h approach and through camera rotation?
3. **Per-frame cost** — one projection plus a few draw calls per marker must be
   cheap enough to run several markers per frame.

---

## 2. Two implementations were attempted

### 2a. Python (`apps/python/projspike/`) — abandoned

The first attempt used Assetto Corsa's legacy **Python** app API: take the
camera matrices, project a world point to screen pixels by hand, and draw a 2D
dot in the per-frame render callback. Findings, in order of discovery:

- **Stock AC Python has no world-to-screen transform at all.** The hoped-for
  `getCameraTransform` is an *unfulfilled feature request* on the Kunos forum,
  never shipped. Stock Python only offers camera *control* and 2D GL draw calls.
- **CSP extends Python** with `ac.ext_getCameraView/Proj/Matrix()` etc., so the
  matrices *are* reachable — but the bindings are fragile:
  - The matrices are returned **column-major**, the transpose of the row-major
    layout assumed by textbook projection (the perspective `-1` lands at flat
    index 11 instead of 14). Required transposing at the boundary.
  - The matrix tuple's **elements are a custom numeric type whose `__float__`
    *and* `__repr__` are broken** under AC's bundled Python 3.3 — calling either
    on a single element raises `TypeError: function takes exactly 1 argument
    (0 given)`. (Camera *position* vec3s are plain floats and convert fine; only
    the matrices are affected.) The only reliable extraction was to `repr()` the
    whole tuple and parse the numbers out of the resulting string.
- **Even when it works, it is a depth-less screen overlay.** The Python layer
  draws 2D over the scene with no depth test, so a marker draws over intervening
  hills and walls and must be manually hidden once its point passes behind the
  camera. It can never be occluded correctly by track geometry.

The Python spike is kept only as a record of *why* Python is the wrong layer; it
is superseded by the Lua version and can be deleted.

### 2b. CSP Lua (`apps/lua/projspike_lua/`, this folder) — adopted

The reference app **Spatial Hud** (b6n), which does production-quality
world-anchored rendering, is a **CSP Lua** app. The decisive insight: CSP's Lua
`render` API draws primitives **directly in 3D world space**. You hand it world
coordinates; the engine projects them with the real scene camera during the
transparent render pass.

This inverts every Python problem:

| Concern | Python overlay | CSP Lua `render` |
|---|---|---|
| Camera transform | fetch + parse + transpose, fragile | engine-side, never exposed |
| Frame-staleness | possible | impossible (same pass as scene) |
| Lock at speed | depends on matrix freshness | guaranteed by construction |
| Depth test / occlusion | none (manual behind-camera cull) | **free** (real depth buffer) |
| Math | manual world→clip→screen | none |

---

## 3. How this spike works

- **Manifest** (`manifest.ini`) registers a 3D render callback:
  `[RENDER_CALLBACKS] TRANSPARENT = draw3d`. CSP invokes `draw3d()` in the
  transparent scene pass.
- **Anchor capture** (`captureAnchor`): on the first 3D frame, the marker is
  frozen `ANCHOR_DISTANCE` (25 m) straight ahead of the car
  (`car.position + car.look * 25`), at road level. This lets the spike run on
  any track without knowing its coordinates — the point freezes in the world and
  you drive past it.
- **Drawing** (`draw3d`): a flat disc on the track (`render.circle`), a cross
  and vertical stalk (`render.debugCross`, `render.debugLine`), and a floating
  label (`render.debugText`) — all in world `vec3` coordinates.
  `render.setDepthMode(render.DepthMode.Normal)` makes it occluded by geometry.
- **Diagnostics** (`windowMain`): the app window shows the anchor coordinate,
  live distance to anchor, current speed, and the 3D frame count, so the
  200 km/h lock test is self-reporting.

### Verdict against the three questions

1. **Current camera** — N/A by design: projection is engine-side, so the marker
   is drawn from the same camera, in the same pass, as the scene. No staleness
   is possible.
2. **Lock at speed** — holds; confirmed driving at the marker. Same reason.
3. **Per-frame cost** — a handful of `render.*` calls per marker; negligible.

---

## 4. API used (verified against this install)

From CSP's shipped SDK, `extension/internal/lua-sdk/ac_apps/lib.lua`:

- `render.circle(pos, dir, radius, color, borderColor)` — pos/dir are `vec3`.
- `render.rectangle(pos, dir, width, height, color)`
- `render.quad(p1, p2, p3, p4, color, texture)` — four `vec3` corners.
- `render.debugCross(center, size, color)` — `size` is a number.
- `render.debugSphere(center, radius, color)`
- `render.debugLine(from, to, color, colorEnd)`
- `render.debugText(pos, text, color, scale, align)`
- `render.setDepthMode(mode)` with `render.DepthMode.Normal` (0, occluded) /
  `.Off` (2, always on top) / `.ReadOnly` (1) / `.LessEqual` (3) / ...
- `render.setCullMode(mode)`
- `ac.getCar(0)` → car state with `.position`, `.look`, `.up`, `.side`
  (all `vec3`), `.speedKmh` (number), `.velocity` (`vec3`, m/s).
- Globals: `vec3`, `vec2`, `rgbm`, `quat`, `ui.*`.

Colors are `rgbm(r, g, b, a)` with components in 0..1.

---

## 5. Run it

1. Restart Content Manager so it scans `apps/lua/projspike_lua/`.
2. Settings → Assetto Corsa → Apps → enable **projspike lua**.
3. Start a session, open the right sidebar, click **projspike lua**.
4. Pull out of the pit; the green marker sits ~25 m ahead, frozen to the world.
   Drive at it (fast), swerve, and watch it stay locked and get occluded by
   geometry.

### Config (top of `projspike_lua.lua`)

- `ANCHOR_DISTANCE` — metres ahead of the car where the marker freezes.
- `MARKER_RADIUS` — marker size in metres.
- `OCCLUDE` — `true` for real depth testing (hidden behind geometry), `false`
  for an always-on-top overlay look.

---

## 6. Implication for the main study

- **The world-anchored rendering is a CSP Lua app. CSP is a documented
  dependency.** This is the decision the spike produces.
- **The thesis contribution — the *fading* of the cue — is unaffected and lives
  in this same layer.** Fading is just modulating the marker's `rgbm` alpha
  (and/or radius) as a function of distance-to-brake-point; the rendering call
  is the same. Keeping the *rendering* swappable and the *fading* independent
  was the design principle, and it still holds — we simply swapped to the
  rendering path that works.
- **The depth-less-overlay limitation noted in the original design is gone.**
  CSP Lua gives true depth-tested in-world drawing without a material override
  or any extra toolchain.

### Next step (not part of this spike)

Replace the fixed anchor with a per-corner braking point (precomputed once from
the expert reference lap / AI line) and key the marker's alpha to
distance-to-brake-point — that is the fading study, built on this rendering.
