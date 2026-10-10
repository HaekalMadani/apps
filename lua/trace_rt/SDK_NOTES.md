# CSP Lua SDK notes (TRACE)

Verified signatures for every CSP/AC API the `trace_rt` runtime actually calls,
plus the runtime quirks that have bitten us. **This is a cache, not the source.**
The authority is the shipped SDK on disk:

    extension/internal/lua-sdk/ac_apps/lib.lua   (the context TRACE runs in)

When adding a new API call, grep that file for the `function`/`---@field` line and
copy the real signature here — don't trust memory or this note if they disagree.
Per CLAUDE.md: only call APIs that exist in the SDK; verify, don't assume.

Line numbers below are from the SDK as of CSP at the time of writing — treat them
as hints, re-grep if they've drifted. M0–M1 surface confirmed 2026-06-13; M3 surface (sim state, AI control,
rendering) confirmed 2026-09-07.

---

## Filesystem / config I/O (M0–M1)

    io.load(filename, fallbackData)            -> string        (whole-file read)
    io.save(filename, data, ensure)            -> boolean       (whole-file write; true on success)
    io.saveAsync(filename, data, callback, ensure)
    io.createDir(filename)                                     (mkdir; safe if exists)

- **No append / streaming write API.** This is *why* the logger buffers every row
  in memory and rewrites the whole CSV on each lap-boundary flush (`logger.lua`,
  `flush_ticks`). Don't go looking for `io.open`/append — it isn't there.
- `io.save` returns `false` (not an error) on failure — check the boolean.
  `trace_rt.lua` raises on `false` so the block freezes as a fault.

## Folders

    ac.getFolder(folderID)                     -> string        (absolute path, no trailing slash)
    ac.FolderID.ACDocuments  = 31    -> <Documents>/Assetto Corsa   (output root; may be OneDrive-redirected!)
    ac.FolderID.ACApps       = 23    -> .../assettocorsa/apps        (repo root for reading configs)
    ac.FolderID.ACAppsLua    = 1029
    ac.FolderID.ACAppsPython = 24

- **OneDrive gotcha:** `ACDocuments` resolves to the *real* Documents, which on
  this machine is redirected to `C:\Users\haeka\OneDrive\Documents\...`. Hence the
  app prints the resolved output path to `py_log.txt` and shows it on-window
  (don't assume `C:\Users\...\Documents`).

## Hashing (config manifest)

    ac.checksumSHA256(data)                    -> string?       (binary; can contain zero bytes)

- Doc says "Computes SHA-256 checksum for given binary data" and `@return string?`.
  **Returns raw bytes (32), not hex** — `hash.lua:to_hex` normalises: 32 raw bytes
  → hex-encode; 64 hex chars → validate+lowercase; else error. May return `nil`,
  so the wrapper raises if so.

## Version / time

    ac.getPatchVersion()                       -> string        (CSP version string, into manifest)
    os.date(fmt)                                                (standard Lua; ISO timestamps)

## Track id (M2 annotation selection)

    ac.getTrackID()                            -> string        (track FOLDER id, e.g. 'ks_silverstone')
    ac.getTrackLayout()                        -> string        (layout folder, '' if none, e.g. 'national')
    ac.getTrackFullID(separator)               -> string        (folder+layout joined; default sep '-')

- **Use `getTrackID()` (capital D).** `ac.getTrackId()` (lowercase d) is marked
  `@deprecated` in the SDK — it still works but points you at the new name.
- TRACE keys annotation files by `getTrackFullID('-')` so layouts get distinct
  files: `configs/annotations/annotation_ks_silverstone-national.json`,
  `annotation_ks_silverstone-international.json`. The study tracks are **both
  layouts of `ks_silverstone`** — `national` (pair 1) and `international`
  (pair 2), decided 2026-09-07. (An earlier draft of this note named Red Bull
  Ring; that plan was dropped — see `configs/annotations/README.md`.)

## Car state (M1 sampler, M2 pass tracker)

    ac.getCar(index)                           -> ac.StateCar?  (index 0 = player; CAN be nil — guard it)
    .collisionDepth  number    depth of current collision in metres; 0 when not
                               colliding. TRACE polls `> 0` per frame as the
                               `wall_contact` validity signal for a corner pass
                               (lib/pass_tracker). There is also a one-shot
                               collision callback (onCollision) but polling depth
                               fits the per-tick snapshot the tracker already gets.

Fields TRACE reads off `ac.StateCar` (all verified on the StateCar block, NOT a
controls-override struct that shares some names):

    .lapCount        integer   completed laps this session (use math.floor; see note)
    .splinePosition  number    0 = start line, 1 = finish line
    .position        vec3      world position (.x/.y/.z) — 0 coord in model space
    .speedKmh        number
    .gas             number    throttle 0..1   <- logged as `throttle`
    .brake           number    0..1
    .steer           number    **DEGREES**, not normalized (the -1..1 `steer` is on a
                               different physics-controls struct). ticks_columns.json's
                               steer unit="deg" reflects this.
    .gear            integer   0 = neutral, -1 = reverse
    .wheelsOutside   integer   count of wheels off the allowed area
    .isInPitlane     boolean   -> logged as `in_pit` (0/1)

- `lapCount` is documented integer but TRACE `math.floor`s it defensively before
  comparisons/logging; keep that.

## UI (immediate-mode window)

Used in `windowMain`: `ui.text`, `ui.textColored`, `ui.button`, `ui.inputText`,
`ui.radioButton`, `ui.sameLine`, `ui.separator`.

Added for the corner-speed cue window (M5):

    ui.pushFont(fontType)                      -- fontType is a ui.Font value
    ui.popFont()                    -> boolean
    ui.Font.Small = 1, .Main = 4, .Title = 6, .Huge = 7

- **TWO windows, not one.** `manifest.ini` declares `[WINDOW_...] ID = main`
  (the experimenter panel) and `ID = cue` (the corner-speed indicator). They are
  separate because the panel must never be on the participant's screen and the
  cue must be. A CSP app may declare any number of windows; each names its own
  `FUNCTION_MAIN`.
- **An app window's draw function stops being called when the window is
  closed.** That is why `lib/hud`'s running minimum is accumulated from `draw3d`
  (a render callback, which runs every frame regardless) and `windowCue` only
  renders the last computed readout. Never keep state that must advance per
  frame inside a window function.
- Not used, but the upgrade path if the window chrome proves distracting at the
  G2 review: `ui.beginTransparentWindow(id, pos, size, noPadding, inputs)` /
  `ui.transparentWindow(id, pos, size, noPadding, inputs, content)` draw an
  undecorated overlay at an absolute screen position, with
  `ac.getUI().windowSize` giving the UI-space screen size to position against.
  Deliberately NOT adopted at M5: it would be an unverified API on the one
  element a participant stares at.

---

## Runtime quirks (these cost real time — not signature issues, an SDK index won't catch them)

1. **No functions stored as table fields + dispatched via `t.fn(...)`.** CSP returns
   the stored closure as a *number* in-game ("attempt to call field … (a number
   value)"), though it passes headless under lupa LuaJIT 2.1. Write helpers called
   **directly**. Bit M0 (`lib/validate.lua`); will bite the M4 controller. See the
   `csp-lua-no-table-stored-closures` memory.

2. **Immediate-mode draw abandons the frame silently on an uncaught error.** A throw
   mid-`windowMain` leaves the window half-blank with no message. Wrap fallible
   work in `pcall` and surface the error as on-window `ui.text` (pattern in
   `trace_rt.lua`).

3. **lupa returns `pcall`'s `(ok, err)` as a tuple** with `unpack_returned_tuples=True`.
   In parity tests capture `local ok = pcall(...); return ok` — don't assert on the
   raw return.

---

## Session / sim state (M3)

    ac.getSim()                                -> ac.StateSim
    .trackLengthM    number    Track length in metres, **as defined by the AI
                               spline**. This is the ONLY spline-to-metre scale
                               in the project: brake-initiation distance, the
                               apex window half-width and the marker view cull
                               all convert through it. Stamped into every
                               manifest and into the reference table so the
                               offline extractor uses the value the runtime saw.
                               (Note it disagrees with `ui_track.json`'s length
                               field on Silverstone International; that field is
                               wrong and nothing in TRACE reads it.)

    ac.getCarID(carIndex)                      -> string   (car folder id; pair identity)
    ac.getCarName(carIndex, includeYearPostfix) -> string   (display name; unused)
    ac.isInReplayMode()                        -> boolean
    ac.getFolder(ac.FolderID.Root)             -> .../assettocorsa

- **AC's own version has no API** (`ac.getPatchVersion()` is CSP's, not AC's).
  `<Root>/changelog.txt` opens with the version number (`1.16.4` here), which is
  what `detect_ac_version()` in `trace_rt.lua` parses so the apparatus pin is
  self-reporting rather than a literal that goes stale.
- `StateCar.physicsAvailable` is `false` for cars in replays and remote cars —
  some fields go missing there. `.brake` / `.gas` are **not** marked physics-only
  (unlike `.load`), so replay-sourced logging is plausible; it is not used.

## AI control (M3 reference laps)

    physics.allowed()                          -> boolean  (false => only raycastTrack works)
    physics.setCarAutopilot(active, chooseTyres)          (AI drives the USER car; invalidates the lap)
    physics.setAILevel(carIndex, level)                   (level 0..1; read back via car.aiLevel)
    .isAIControlled  boolean on ac.StateCar

- Autopilot on the **player car** is deliberate: the reference laps then share
  the participant's car, setup and `ac.getCar(0)` sampling path, so AI laps,
  human reference laps and participant laps differ only in who is driving.
  Recording a separate AI *opponent* would run AC's own car entry and setup, and
  the brake points would not be comparable.
- `physics.*` is gated by `physics.allowed()`, which is session-dependent. Every
  call in `trace_rt.lua` is `pcall`-wrapped and the panel reports when scripting
  is not permitted, rather than silently doing nothing.
- Autopilot invalidates the AC lap. That does not matter: TRACE counts laps from
  `lapCount` itself and derives lap times from its own tick clock.

## Rendering — world-anchored markers (M3)

Markers are drawn directly in **3D world space**; the engine projects them with
the real scene camera in the transparent pass. That is *not* screen-projection.
(`render.projectPoint(pos, faceID)` exists for world→screen but is **not** the
marker approach — don't reach for it.)

Registered in `manifest.ini`:

    [RENDER_CALLBACKS]
    TRANSPARENT = draw3d          -- CSP calls the global draw3d() in that pass

Calls TRACE uses (all confirmed against the SDK and proven by the spike):

    render.circle(pos, dir, radius, color, borderColor)   -- pos/dir are vec3
    render.debugCross(center, size, color)                -- size is a number
    render.debugLine(from, to, color, colorEnd)
    render.debugText(pos, text, color, scale, align)
    render.setDepthMode(render.DepthMode.Normal)          -- occluded by geometry
                        .Off (always on top) / .ReadOnly / .LessEqual

- Colours are `rgbm(r, g, b, a)`, components 0..1. **Fading is exactly this
  alpha** — `lib/markers.lua`'s `alpha(level, salience)` maps a salience level
  onto `full_alpha` / `reduced_alpha` / 0. From M5 the draw call also consults
  `markers.visual(stage, salience)`, which says which PARTS of the cue survive
  (`disc` / `cross` / `stalk` / `label`), because the study's reduced form
  strips the marker to its disc rather than only dimming it. Both are pure
  functions computed before any `render.*` call, so the whole staging layer is
  headless-testable while the drawing is not.
- `car.position` sits at the model origin, which is only **approximately** road
  level — and how approximately is a property of the car, not a constant. A disc
  drawn depth-tested at exactly that height came out coplanar with the tarmac in
  `ks_bmw_m235i_racing` (invisible: swallowed by the road) but cleared it in
  `ks_audi_tt_cup` (visible). Anything flat built from logged car positions needs
  a few centimetres of lift; `MARKER_DISC_LIFT_M` in `trace_rt.lua` is it. The
  earlier note here said no offset was needed — that held only for the car it was
  written against.
- Same caveat as the window: a raise inside the render callback abandons the rest
  of that frame's drawing, so `draw3d` is `pcall`-wrapped and surfaces the error
  on the window instead.
