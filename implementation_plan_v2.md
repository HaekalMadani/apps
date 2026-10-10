# Implementation Plan — TRACE (v2)

> **Changes from v1.** (1) Evaluator emits true per-pass booleans; the braking consistency gate is a per-pass delta against the corner's rolling mean, replacing the windowed variance gate that was incompatible with the 3-of-4 rule. (2) Controller spec gains the re-qualification-on-advance reset. (3) The §5 "shadow dataset" claim corrected — static-mode controller states are counterfactually valid only up to the first would-have-faded transition. (4) Golden-trace corpus explicitly includes the alternating pass/fail corner and mid-window re-qualification resets. (5) Config carries EVM_AI/EVM_human, band floors, and the consistency delta.

**TRACE** — *Telemetry-driven Reversible Adaptive Cue Engine*. The software that realises the framing document (v6) and feeds the evaluation plan (v2). This document fixes the architecture, the build order, the data contracts between components, and the engineering practices that keep the study's credibility claims true in code.

---

## 1. The architecture decision that everything follows from

The red-team review identified an unspecified seam: the renderer is CSP Lua inside the game, the telemetry pipeline was implicitly an external process, and the controller had no home — implying a real-time IPC bridge with latency, ordering, and failure-mode problems.

**Decision: there is no seam.** Everything real-time lives in **one CSP Lua app** running inside Assetto Corsa. CSP Lua can read full car state, run per-frame logic, draw in world space (proven by the spike), and write files. Python exists only **offline** — before sessions (reference extraction, simulation) and after sessions (integrity checks, analysis). The two worlds communicate exclusively through **files**: configs go in, logs come out. No sockets, no shared memory bridge, no second process to crash mid-block.

This buys: zero IPC latency and zero IPC failure modes; the controller sees the exact same car state, in the same frame, as the renderer; the static condition and the adaptive condition run the *same binary* with different config (so logging is identical across conditions); and a session cannot be half-recorded because one of two processes died.

It costs: controller and metric logic must be written in Lua, and the Phase 1 simulator (Python) must implement *the same logic*. That duplication is a real divergence risk, and §6 deals with it head-on (golden-trace parity tests).

## 2. Components

### 2.1 `trace-rt` — the in-game runtime (CSP Lua app)

Seven modules, one process, explicit data flow:

1. **Config loader.** Reads the three static inputs at session start: corner annotation file (per track), per-corner reference table, controller config (qualification window, quorum thresholds, probe rules, reversion cap, re-qualification rule flag, consistency delta, and tolerance bands = max(σ_ref × source-dependent EVM, floor)). Validates against schema; refuses to start a block on any validation error. Logs the SHA-256 of each config into the session manifest.
2. **Sampler.** Per-frame read of car state (`ac.getCar(0)`): spline position, world position, speed, brake/throttle/steering, gear, wheels-outside count, lap/sector counters. Maintains the current-frame snapshot for other modules; downsamples to the 20 Hz per-tick log.
3. **Corner-pass tracker.** Watches spline position against annotation gates. On entry-gate crossing: opens a pass, begins accumulating raw samples for that corner's evaluation zones (braking zone, apex gate, corner-speed zone). On exit-gate crossing: closes the pass, hands the accumulated samples to the evaluator, sets the validity flag (wheels-outside, wall contact, pit transitions).
4. **Evaluator.** Converts a closed pass into **per-pass, per-element criterion booleans** — the unit the controller's 3-of-4 rule consumes; nothing window-level leaves this module. Braking is two-gate per pass: brake-initiation distance within the accuracy band of the reference point, AND within the consistency delta of the rolling mean of that corner's recent passes (the evaluator keeps a small per-corner history buffer for the rolling mean; window-level variance gates were removed as incompatible with a per-pass rule and statistically meaningless at 3–4 samples). The other gates: minimum-corner-speed deviation vs envelope; RMS lateral deviation over the apex window vs band. Owns the brake-initiation event definition (first brake application above the pressure threshold inside the braking zone — see §7, open decisions); the raw brake-initiation sample (timestamp, spline position, distance) is stamped into the pass record so the pilot's event-log audit can reconstruct the gate's exact input from logs alone.
5. **Fading controller.** The state machine exactly as specified in framing v6: per-corner qualification (3-of-4, de-qualify on 2 consecutive failures), element-level quorum (advance ≥ 75%, revert < 50%), **re-qualification on advance (every stage advance resets all corner qualification states and evidence windows for that element; reversions do not reset)**, probe rules (3 laps, one-stage reversion, cap 2, block-scoped permanence, censoring on block end). Pure function of (previous state, new pass result) → (new state, events). **No rendering, no I/O inside this module** — purity is what makes the golden-trace tests possible.
6. **Renderer.** The spike's `render.*` path, generalised: iterates the reference table, draws braking/apex markers at their world coordinates and the corner-speed HUD element, with per-element salience from the controller (full / reduced / hidden). In the static condition the controller is bypassed and salience is constant-full. Depth mode per the spike.
7. **Logger + experimenter panel.** Buffered writers for the four output streams (§3); flush on lap completion and block end. The panel (app window) is the only human interface: participant ID, condition, pair, block start/stop, live status (current stage per element, qualified-corner count, laps completed, probe countdown), and a big red abort. Block metadata is entered here and stamped into the manifest — the protocol never depends on editing files mid-session.

### 2.2 `trace-kit` — the offline toolkit (Python)

- **Annotator helper.** Drive-and-mark workflow: a small companion mode in `trace-rt` records spline positions on keypress while an experimenter drives slowly; `trace-kit` turns the marks into a draft annotation file for manual cleanup. Avoids hand-typing spline numbers.
- **Reference extractor.** Consumes logged AI laps and human validation laps (Phase 0), produces the per-corner reference table: brake-point world coordinates, apex coordinates, speed envelopes, per-metric σ_ref, bands = σ_ref × EVM. Emits the AI-vs-human comparison report and records per-corner source (AI / human-substituted).
- **Simulator.** Phase 1: synthetic learner streams through a Python port of the controller. Tunes the controller config against the design targets; outputs the feasibility figure and the frozen config.
- **Integrity checker.** The post-session script from the evaluation plan: telemetry gap scan, lap-count reconciliation, fade-event log parse, manifest completeness.
- **Analysis.** Frozen analysis scripts (Bayesian model, RQ1 figures including qualification heatmaps, alignment table). Dry-run against pilot + simulated data per the evaluation plan.

## 3. Data contracts (the file formats are the API)

All formats versioned with a `schema_version` field; JSON for configs, JSON-Lines for event streams, CSV for the per-tick log (volume).

| File | Direction | Producer → Consumer | One row/record per |
|---|---|---|---|
| `annotation_<track>.json` | in | annotator → rt, extractor, sim | corner |
| `reference_<pair>.json` | in | extractor → rt, sim | corner × element |
| `controller_config.json` | in | simulator (frozen) → rt, sim | — (single object; includes EVM_AI, EVM_human, per-metric band floors, consistency delta, re-qualification flag, and all controller constants) |
| `session_manifest.json` | out | rt | block (participant, condition, pair, config hashes, app/CSP/AC versions, timestamps) |
| `ticks_<block>.csv` | out | rt → kit | 20 Hz sample |
| `passes_<block>.jsonl` | out | rt → kit | corner pass (metrics, criterion booleans, qualification state, stage) |
| `fades_<block>.jsonl` | out | rt → kit | controller event (incl. censoring, cap hits, quorum stats) |

Rule: **runtime and simulator never share state except through `controller_config.json` and the golden traces.** Anything not in a file does not exist.

## 4. Build order (milestones with exit criteria)

Each milestone has a binary exit test; nothing starts on participants until M7. The order front-loads the remaining unknowns the way the rendering spike did.

**M0 — Skeleton (½ week).** Repo layout (`apps/lua/trace_rt/`, `kit/`), schema files for all seven formats, CI running schema validation and the Lua tests headless where possible. *Exit:* configs round-trip through validation in both Lua and Python.

**M1 — Sampler + logger (1 week).** Extend the spike into per-frame sampling and buffered 20 Hz logging with the manifest. *Exit:* a 30-minute solo drive produces gap-free logs (integrity checker passes) with no measurable frame cost.

**M2 — Annotation + pass tracking (1 week).** Drive-and-mark annotator, annotation files for both tracks, gate-crossing pass tracker with validity flags. *Exit:* a driven lap yields exactly one pass per annotated corner, with correct validity flags on deliberate off-tracks, on both tracks.

**M3 — Reference pipeline (1 week).** Record AI laps (and human validation laps), reference extractor, AI-vs-human report. This *is* evaluation Phase 0; Gate G0 closes here. *Exit:* G0 criteria met; markers render at extracted (not hardcoded) world coordinates.

**M4 — Controller + simulator (1–1.5 weeks). ✓ done 2026-09-08; Gate G1 met.** Implement the controller in Lua and its Python port; golden-trace parity suite (§6); then run Phase 1 tuning. Gate G1 closes here. *Exit:* parity suite green; G1 design targets met; config frozen and hashed.

**M5 — Full rendering + salience stages (1 week). ◐ code complete 2026-09-08; the on-track exit check is outstanding.** Three elements with full/reduced/hidden states wired to the controller; the reduced-salience visual design decided and implemented (§7); static-condition config path verified. *Exit:* scripted controller states produce the intended visuals for all elements on both tracks; static blocks render constant-full while logging identically.

**M6 — Experimenter panel + protocol dry run (½–1 week).** Panel complete; one full three-session protocol executed on yourself end-to-end, including questionnaires and the integrity checker after each "session". *Exit:* a complete fake-participant dataset that the frozen analysis scripts ingest without manual fixes.

**M7 — Pilot (evaluation Phase 2).** Two pilots, EVM calibration, event-log audit, re-frozen config. Gate G2 closes; main study begins.

Total: ~6–8 weeks of build before the pilot, assuming part-time thesis pace. The long pole is M4; if the schedule slips, cut from M5's visual polish, never from M4's parity suite.

*[amended 2026-09-09]* M0–M4 are complete and M5 is code-complete. The parity suite was not cut and is the reason two controller bugs were found before any participant saw them. One thing this build order did not anticipate: M4 has **no in-game exit test** — its criteria are all headless — so the controller has never run at frame rate inside CSP. That check is folded into M5's on-track review rather than deferred further.

## 5. Condition switching and the experiment's integrity

The condition is a **config field, not a code path**: `mode: adaptive | static | off`. Static mode runs the identical pipeline — sampler, tracker, evaluator, even the controller (computing qualification invisibly) — but pins salience to full. This means static blocks produce the *same per-pass records and qualification states* as adaptive blocks. One claim an earlier version of this plan made about that is withdrawn: the invisible controller states are **not** "what the controller would have done" under adaptive training. They are counterfactually valid only up to the first would-have-faded transition — beyond that point, an adaptive participant's behaviour is endogenous to the fade (the cue they would no longer see shapes the very telemetry the controller reads), and the static-block trajectory diverges from any real adaptive trajectory. The states are still logged, at zero extra cost, and reported in RQ1 strictly as *"controller state under static visibility"* — useful for time-to-first-would-be-fade comparisons and nothing stronger. `off` mode (no elements, logging on) is session 1 and session 3.

## 6. The parity problem (one logic, two languages)

The controller exists twice: Lua (runtime) and Python (simulator). Divergence here silently invalidates Gate G1 — the simulation would certify a controller that isn't the one participants experience.

Mitigation, in order of importance:

1. **Golden-trace tests.** A shared corpus of input traces (sequences of per-pass criterion booleans, including pathological cases: **the alternating pass/fail corner that never accumulates two consecutive failures and so never de-qualifies despite a 50% failure rate**, mid-window re-qualification resets (a stage advance landing while corners are partway through their 3-of-4 windows), block-end-mid-probe, cap-triggering erratics) with expected state/event sequences, stored as JSON. Both implementations must reproduce every trace exactly; the suite runs in CI on every change to either side.
2. **The controller is a pure function** in both languages — no clocks, no I/O, no randomness. All inputs arrive as arguments; all outputs are return values.
3. **One source of constants.** Both sides read `controller_config.json`; no threshold is ever written as a literal in code.
4. If a divergence is ever found after G1, the gate re-opens: re-run the simulation against the fixed implementation before any further participant.

## 7. Open design decisions (defaults proposed, decide before the milestone that needs them)

> *[amended 2026-09-09]* **Every decision in this section is now closed.** Each
> is marked **DECIDED** below with what was chosen and where it lives. The
> defaults survived in every case except the corner-speed band floor, which
> Phase 1 moved (3.0 → 4.0 km/h; see the evaluation plan's Gate G1). Two rules
> the controller needed but this plan did not anticipate — quorum readiness, and
> one-regression-one-stage — are recorded in `lua/trace_rt/lib/controller.lua`
> and in the framing document's fading-mechanism section, not here, because they
> are mechanism rather than open questions.

- **Reduced-salience visual (needed by M5). DECIDED at M5: the default, `salience.reduced_form = "minimal"`.** Marker at 40% alpha, label and vertical stalk removed, disc only; the corner-speed readout keeps its target number alone. Held as a config enum rather than a code change, with `intermediate` and `dimmed` as the alternatives — `dimmed` (the whole cue, just dimmer) is kept deliberately as the control case for the argument that reducing salience should reduce what the cue *tells* the learner, not just how bright it is. Original text follows: Default: marker at 40% alpha, label and vertical stalk removed, disc only. Alternatives (smaller radius, outline-only) are one-line changes; pick by eye during M5 and record the choice. This is also an RQ3 interview topic, so freeze it before the pilot.
- **Brake-initiation event (needed by M4). DECIDED at M4: the default, unchanged** (`brake_initiation.threshold` 0.1, `debounce_ms` 100). Implemented as a streaming detector in `lib/pass_metrics.lua` and pinned by test against the offline extractor's, so the runtime detects the event exactly as the reference table was built — a divergence there would have made every band quietly wrong. Original text follows: Default: first sample inside the braking zone where brake input crosses 10% and remains above it for ≥ 100 ms (debounce against pedal taps). The load-cell pedal makes the signal clean, but the debounce constant goes in the controller config like everything else.
- **Corner-speed HUD element placement and form (needed by M5). DECIDED at M5: the default, with the mechanism named.** A second app window (`[WINDOW_...] ID = cue`), separate from the experimenter panel because that panel must never be on the participant's screen; positioned centre-bottom once by the experimenter, which AC persists. Target-vs-actual in three phases — the target and live speed on approach, the target and the *running minimum* inside the corner-speed zone, and the achieved minimum held briefly past the zone so the number is still there when it first means something. `ui.beginTransparentWindow` would give a chrome-free overlay and is the upgrade path if the window frame distracts at the pilot; it was not taken at M5 because it would be an unverified API on the one element a participant looks at. Original text follows: Default: small fixed HUD readout near the centre-bottom showing target-vs-actual minimum corner speed for the upcoming annotated corner, rendered in the same Lua app (no second UI technology).
- **Tick rate (needed by M1). DECIDED at M1: the default, unchanged** (20 Hz logged, sampler per-frame). The brake-initiation debounce was not under-resolved: the evaluator consumes per-frame samples, and the raw brake-initiation sample is stamped into each pass record as planned. Original text follows: Default 20 Hz logged; sampler runs per-frame regardless. Raise only if the brake-initiation debounce proves under-resolved at 20 Hz. Note the evaluator consumes per-frame samples, not the 20 Hz log — which is why the raw brake-initiation sample is stamped into each pass record (§2.1.4): the offline audit must be able to reconstruct gate inputs the log alone cannot resolve.
- **Consistency delta (needed by M4). DECIDED at M4: the default, and it survived tuning** (`criteria.consistency_delta_ratio` = 0.5). Phase 1's sweep found configurations meeting every target at ratios from 0.5 to 1.5 and selected the tightest. The rolling mean is taken over the corner's *prior* passes in the window — never including the pass being judged, which would partly measure it against itself — and on a corner's first pass the gate is vacuously met, so the criterion reduces to accuracy there. Original text follows: Default 0.5 × the accuracy band per corner; a named constant in `controller_config.json`, tuned in Phase 1 with everything else.
- **Apex window half-width (needed by M2/M3). DECIDED at M3: per corner, default 20 m**, reduced to 15 m at National's corner 3 so the window fits inside its shortened pass bracket. The extractor now refuses a window that does not fit its bracket rather than reporting it as an opaque coverage failure. Original text follows: A per-corner spline half-width recorded in the annotation file, defaulting to roughly 20 m of track length; the evaluator computes RMS lateral deviation over the window, never a single-point sample.
- **Per-element applicable-corner sets (decided at M2, guard needed by M4). DECIDED at M4: the proposed answer.** An element with zero applicable corners is disabled, pinned at full salience, never evaluated, and recorded in the manifest's `disabled_elements` — not in the fade log, since a fade record with a zero denominator would be a fiction. Covered by the `zero_applicable_braking` golden trace. Neither study track exercises it: all corners on both layouts have braking zones. Original text follows: A corner annotated without a braking zone (taken flat) is not applicable to the braking-point element: no marker, no braking criterion, excluded from that element's quorum denominator (annotation + reference schemas make `braking` optional accordingly). The M4 controller must define the degenerate case of an element with **zero** applicable corners on a track (proposed: element disabled, pinned at full salience, logged as such) — division by zero in the quorum is otherwise possible. Whether a corner has a braking zone follows the expert reference where in doubt; revisit at G0's on-track review.

## 8. Risk register (implementation-specific)

| Risk | Exposure | Mitigation |
|---|---|---|
| Lua runtime error mid-block | lost participant block | every callback wrapped (`pcall`); on error: log, freeze salience at current stage, keep logging; experimenter panel shows fault state; pre-written restart procedure; gap recorded in manifest |
| File I/O stalls the render thread | frame hitches visible to participant | buffered writes, flush on lap boundaries only; M1 exit test measures frame cost |
| CSP/AC update changes API mid-study | apparatus drift | pin CSP + AC versions at M3; versions stamped into every manifest; updates forbidden until data collection ends |
| Spline position quirks on a chosen track (resets, pit-lane splines) | broken pass detection | M2 exit test on both real tracks, including pit transitions; choose tracks partly on spline sanity |
| Controller divergence Lua vs Python | invalidated G1 | §6 parity regime |
| Annotation errors discovered late | invalid per-corner data | G0 requires on-track visual review of every gate and zone; annotation files versioned so any fix is traceable |
| Scope creep into the renderer (pretty markers) | schedule | M5 exit criteria are functional, not aesthetic; polish is explicitly post-pilot if ever |

## 9. What this plan deliberately does not include

No networking, no database, no real-time dashboard, no automatic corner detection, no machine learning, no support for tracks beyond the two annotated ones, and no cross-session state. Each of these was considered and excluded because it serves engineering pride rather than the three research questions. The framing document's last line applies to the code too: drift toward sprawl is the most likely failure mode.
