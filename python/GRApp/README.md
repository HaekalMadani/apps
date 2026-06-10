# GR App

An in-game Assetto Corsa HUD app.

> Folder/module id is `GRApp` (no space — AC imports a Python app by its folder
> name, and module names can't contain spaces). The in-game display name is
> **GR App** (set via `ac.newApp` / `ac.setTitle` / the `acMain` return value).

## How it runs
AC loads this app from `assettocorsa\apps\python\GRApp\`. At launch the game
boots its own **Python 3.3** interpreter and injects the built-in `ac` and
`acsys` modules. There is no pip/conda at runtime — keep all in-game code
(`GRApp.py`, `GRApp_core.py`) Python 3.3 compatible (no f-strings, no type
hints, no modern stdlib-only features).

## Files
- `GRApp.py`       Entry point. AC calls `acMain` / `acUpdate` / `acShutdown`.
- `GRApp_core.py`  Pure logic, no `ac` imports — unit-testable locally.
- `tests/`         pytest suite for `GRApp_core`, runs in the conda env.
- `dev_stubs/`     Fake `ac` / `acsys` for editor autocomplete + linting only.
                   NEVER ship this on sys.path in-game (it would shadow the
                   real modules).

## Enabling the app in-game
1. Launch Assetto Corsa.
2. Main menu -> Settings -> General -> UI Modules -> enable **GRApp**.
3. Start a session (practice/hotlap). Open the right-side app sidebar in-car
   and click the **GR App** icon to show the window.
4. After editing code you must restart the *session* (return to menu and go
   back on track) for changes to reload; a full game restart is safest.

## Local dev workflow (conda env: ac_dev)
Run the logic tests without launching the game:

    conda activate ac_dev
    cd "D:\SteamLibrary\steamapps\common\assettocorsa\apps\python\GRApp"
    pytest -q

For editor autocomplete, point your IDE's extra paths at `dev_stubs/` so
`import ac` / `import acsys` resolve while editing.

## Debugging in-game
`print(...)` and errors go to AC's Python log:
`Documents\Assetto Corsa\logs\py_log.txt`
