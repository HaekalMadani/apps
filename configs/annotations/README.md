# Per-track corner annotations (M2)

Real, version-controlled corner annotation files live here, one per track
**full id** (folder + layout, joined by `-` — the key `trace_rt` resolves via
`ac.getTrackFullID('-')`). The in-game runtime loads
`annotation_<trackFullID>.json` at block start; if it's missing the block still
records ticks but pass tracking is OFF (the window says so).

Study tracks for M2 — the two experiment pairs are **two layouts of
Silverstone** (decided 2026-09-07, replacing the earlier Red Bull Ring plan):

| Pair | File | AC folder | Layout | AI-line length | Corner complexes |
|---|---|---|---|---|---|
| 1 | `annotation_ks_silverstone-national.json` | `ks_silverstone` | `national` | 2600 m | 4 (all with braking) |
| 2 | `annotation_ks_silverstone-international.json` | `ks_silverstone` | `international` | 2943 m | ~5–6 (8 curvature segments) |

Silverstone is the folder `ks_silverstone` plus a separate layout folder
(`national`, `international`, `gp`) — *not* a `ks_silverstone_national` folder.

**Why two layouts of one venue.** The two layouts share **no tarmac** in AC: they
sit in disjoint world-space regions (National `z ∈ [−869, −198]`, International
`z ∈ [−149, +851]`; the nearest National landmark is 235 m from the
International racing line). So Pair 2 is not pre-learned while driving Pair 1 —
the crossover design's requirement. Both are also short enough for the
evaluation plan's "~2-minute circuit, 13–15 laps per 30-minute block" lap
budget, which Silverstone GP (5901 m) would break. (`ui_track.json` reports 3619 m
for International; that field is wrong — the real circuit and the AI line are
~2.94 km. Nothing in TRACE reads it.)

**Consequence for the controller — quorum granularity.** Corner count sets the
resolution of the element-level quorum (advance ≥ 75% qualified, revert < 50%).
**Both annotations were re-derived at M3 from the AI reference laps** (2026-09-08)
and the picture improved substantially: National now has **4 corners, all with
braking** (corner 1 is *not* taken flat at racing pace, and the old compound
corner 3 is genuinely two corners — it has two braking events with 113 m of
acceleration between them), and International has **5 corners, all with braking**.

So the braking element's denominator is 4 on National and 5 on International,
rather than the 2 the July annotation implied. On 4 corners ≥ 75% means 3/4 and
reversion needs 3 of 4 to fail — a real quorum rather than the all-or-nothing
2/2 that the earlier note flagged as a weakness. M4's simulation and golden
traces should still cover small denominators (4 is not large), alongside the
zero-applicable-corners guard (impl plan §7).

**The lesson that produced this:** drive-and-mark captures are made *slowly*, so
their braking zones and even their "this corner is taken flat" judgements reflect
a crawl, not racing pace. Every braking zone in both files was wrong against the
expert reference — one ended before the AI braked at all, others opened after it
had already started (clamping every lap to the zone start and manufacturing a
fake near-zero σ). Treat drive-and-mark braking zones as a **starting point, not
a contract**, and always re-derive them from the expert reference; impl plan §7
already gives the reference the deciding vote where in doubt.

**Thesis limitation to state explicitly:** with both pairs at one venue, the
`pair` fixed effect in the primary model is a *layout* contrast, not a *venue*
contrast. It is not evidence of generalisation across tracks — which the
evaluation plan already places out of scope.

## How to produce one

1. In game, open the TRACE app on the chosen track, switch the window to
   **annotate** mode, and **Begin annotating**.
2. Drive slowly; at each landmark press the matching role button
   (`entry`, `brake_start`, `brake_end`, `apex`, `cs_start`, `cs_end`, `exit`)
   after setting the corner id / type / compound flag. Press `apex` more than
   once on a compound corner. **Write marks file** → `marks_<track>_<stamp>.jsonl`
   in `<Documents>/Assetto Corsa/trace_data/`.

   `entry`/`exit` are **pass brackets, not driving landmarks**: entry goes on
   the approach straight before anything measurable (before even a cautious
   novice would brake/lift), exit on the following straight after the
   corner-speed zone — they only bound the pass and must not overlap the
   neighbouring corners' gates. Nothing is measured *at* them, so generous is
   fine.

   **Corners taken flat (no braking): skip `brake_start`/`brake_end` entirely**
   (all-or-neither — one without the other is an assembler error). A corner
   without a braking zone is simply not applicable to the braking-point
   element: no marker, no braking criterion, excluded from that element's
   quorum denominator. The apex and corner-speed roles still apply.

   **But be sceptical of "flat" at marking speed.** National's corner 1 was
   marked flat in July and turned out to be the second-heaviest braking zone on
   the lap (205 → 146 km/h) once a car ran it at pace. Mark what you see, then
   let the M3 expert reference settle it — annotations are versioned and G0
   reviews every gate on track anyway.
3. Offline: `conda activate ac_dev && cd kit &&
   python -m trace_kit.annotate "<…>/marks_<track>_<stamp>.jsonl"` →
   a draft `annotation_<track>.json` next to the marks. It validates against the
   schema and reports any corner missing a role, plus **geometry** problems the
   schema cannot see: landmarks out of driving order (`entry → brake_start →
   brake_end → exit` and `entry → cs_start → apex(es) → cs_end → exit`), an
   apex gate outside its corner-speed window, and pass brackets overlapping
   between corners. The two chains are checked separately because trail braking
   legitimately puts `brake_end` after `cs_start`. Exit code is non-zero if
   anything is reported.
4. Hand-clean the draft (names, nudge spline values), then commit it here.

**`zones.apex_window_half_m` has no button** (added M3, required since). The apex
criterion is *RMS lateral deviation from the expert line over a window centred on
the apex gate* — never a single sample at the gate, which is noisy and gameable
(framing v6). This field is that window's half-width, **in metres of track
length**, converted to spline by the runtime and the extractor using
`ac.getSim().trackLengthM`. `annotate.py` seeds every corner with the impl-plan
§7 default of 20.0 m; G0's on-track review confirms or adjusts it per corner —
it should span the part of the corner where the line actually matters, and must
not run into the neighbouring corner. A compound corner has one half-width
shared by all its apex gates, and still yields **one** apex criterion boolean per
pass, taken over the union of its windows.

The schema is `schemas/annotation.schema.json`; `configs/examples/annotation_example_track.json`
is a FAKE fixture for tests, not a real track — do not load it in game.
