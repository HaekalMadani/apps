# Per-pair reference tables (M3)

Real, version-controlled per-corner reference tables live here, one per
**car-track pair**, named `reference_<pair_id>.json`. The in-game runtime loads
`reference_<pair_id>.json` at block start for the pair selected on the panel; a
participant block **refuses to start** without one (same hard gate as the
annotation — a block that renders markers at no coordinates, or at the wrong
car's coordinates, cannot be re-run on the same person). Dev blocks opt out, and
recording the reference laps themselves *is* a dev block.

| Pair | File | Track | Layout | Car | Corners | Lap-time CoV |
|---|---|---|---|---|---|---|
| 1 | `reference_pair1.json` | `ks_silverstone` | `national` | `ks_bmw_m235i_racing` | 4 | 0.064% |
| 2 | `reference_pair2.json` | `ks_silverstone` | `international` | `ks_audi_tt_cup` | 5 | 0.092% |

Both tables are recorded and committed. The Gate G0 review of them — what is
already checked automatically, and what still has to be checked on track — is
`G0_REVIEW.md` in this folder.

The pairs use **different cars** (decided 2026-09-07). Both layouts are one
venue and share no tarmac, so the layout already separates them; a different car
per pair adds the second separator against the skill carryover framing v6 §63
flags as this design's known cost. `pair` is a nuisance fixed effect in the
primary model, never interpreted, so the car/layout confound costs nothing.

The reference is **per car-track pair**: brake points, speed envelopes and
tolerance bands do not transfer between cars. The table records its `car` and
`track`, and the runtime refuses a block whose loaded car or track disagrees.

## What is in the table

Per corner: the expert **brake-initiation point** (world coordinate for the
marker, spline datum for the metric, σ_ref in metres along the track), the
expert **apex line** (a *sampled line* across each apex window — not a point,
because the metric is RMS lateral deviation over the window), the **minimum
corner-speed envelope** (mean + σ_ref), and the corner's **`source`** (`ai` or
`human`), which is what selects EVM_AI vs EVM_human at run time.

Each corner also records **`contributing_laps`**: how many clean passes actually
built its braking, apex and corner-speed references. Nothing at run time reads
it; it exists because Gate G0 requires every corner to meet the extractor's
minimum contributing-lap count, and a count that lives only in the console output
of the run that produced the table cannot be re-checked later. `source_laps`
carries `lap_time_cov_pct` for the same reason. Both are asserted against the
committed tables by the test suite. A small count next to a tiny `sigma_ref` is
the signature of a mis-fitted zone, not of a repeatable driver.

Tolerance bands are **not** stored here. They are derived as
`band = max(σ_ref × EVM_source, floor)` with the multipliers and floors living
only in `controller_config.json` — one source of constants.

`configs/examples/reference_example_pair.json` is a FAKE fixture for tests, not
a real pair — do not load it in game.

## How to produce one

Everything runs through the study's own pipeline; Phase 0 doubles as its
end-to-end test.

1. **Record the AI laps.** Load the pair, open TRACE, switch to **reference**
   mode, set AI strength to 95–100%, and engage autopilot. Start a **dev block**
   (the annotation/reference gates are for participant blocks; a dev block is
   stamped `dev_block: true` so these laps can never read as study data). Record
   12 clean laps under the fixed setup, then stop.
2. **(Not currently done) Record human validation laps** the same way with
   autopilot off. See "Why the reference is AI-only" below — this step is
   deliberately skipped, and the tooling for it is kept for the day it can be
   done properly.
3. **Extract**, once per source:

       conda activate ac_dev && cd kit
       python -m trace_kit.reference extract "<…>/trace_data/manifest_<ai block>.json" \
         --annotation ../configs/annotations/annotation_ks_silverstone-national.json \
         --pair pair1 --source ai --ai-strength 98 \
         -o ../configs/references/reference_pair1_ai.json

   The extractor prints the **lap-time CoV** (Gate G0 wants < 1%) and the
   per-corner contributing-lap count, and exits non-zero if anything is wrong.
   Re-record rather than accepting a corner built from too few laps.
4. **Commit the extracted table as `reference_<pair>.json`** — with no human
   laps there is nothing to compare against, so the AI table *is* the table the
   runtime loads. Keep the `_ai` suffix on the extracted file and commit the
   loaded file alongside it, so the provenance chain stays explicit.

   If human laps are ever recorded, the substitution step is:

       python -m trace_kit.reference compare \
         ../configs/references/reference_pair1_ai.json \
         ../configs/references/reference_pair1_human.json \
         -o ../configs/references/reference_pair1.json \
         --report ../configs/references/comparison_pair1.json

   Then commit the AI table, the human table, the comparison report **and** the
   substituted table, so every substitution decision is reconstructible from the
   repository alone.

## Why the reference is AI-only (M3 decision, 2026-09-08)

Framing v6 planned a human validation step to bound the AI's known biases —
it brakes conservatively and does not trail brake. **That step is not being
carried out**, and the reason matters more than the omission:

- No experienced sim racer was available.
- The researcher is a **beginner**. A reference recorded by a beginner is not a
  weaker *expert* reference — it is a **novice** reference. Substituting it
  would move the target toward novice performance, so the scaffold would fade
  when a participant drove like a beginner. That inverts the entire premise of
  the intervention. Recording it would have been worse than not recording it.

So every corner keeps `source: "ai"`, `EVM_human` goes unused, and **the claim
that the AI's brake points fall within a competent human's tolerance is not
established.** State that as a limitation in the methods chapter — do not let it
pass silently. The dataset-side half of that obligation is written down in
`DATASET_README.md` at the repository root (Gate G0 clause 5).

What bounds the cost, honestly:

1. **The bias runs in the safe direction.** The AI brakes *early*; novices also
   brake early. An AI reference is therefore a less demanding target than a real
   expert's would be — which is the right direction to err for a scaffold a
   novice has to reach. This makes the error benign, not absent.
2. **The bands are floor-dominated.** Measured on the first recorded pair, the
   AI's per-corner σ was 0.005–0.015 m (apex line), 0.58–0.88 m (brake point)
   and 0.20–0.41 km/h (corner speed). Against floors of 0.5 m / 5 m / 3 km/h,
   **every band is set by its floor, not by σ × EVM_AI.** So the reference's
   precision is not what sets the criteria, and an AI bias smaller than a floor
   is absorbed by the band rather than transmitted to the criterion. Note the
   limit of this argument: a floor widens the band, it does not re-centre it, so
   a bias *larger* than the floor still bites.
3. **Gate G2 inherits the job.** The pilot compares real novice per-corner
   distributions against the reference and finalises the floors. That is now the
   only empirical check that the reference is reachable, so a G2 failure means
   recalibrating floors — or revisiting the car — not just nudging the EVM.

`trace_kit.reference compare` and its substitution rule (below) are built and
tested. If an experienced driver becomes available before the pilot, restoring
the validation is two commands, not a rebuild.

## The substitution rule (kept, currently unused)

If human laps are ever recorded, a corner's reference is **substituted with the
human reference when the human's reference falls outside the tolerance band the
AI reference would impose** — i.e. when

    |mean_human − mean_AI| > max(σ_AI × EVM_AI, floor)

for the braking point, the corner-speed envelope, or the mean offset between the
two apex lines.

The rationale is the criterion itself: if a competent human, driving the same car
on the same setup, would *fail* the AI-anchored criterion, that criterion is not
a usable target for a learner, and the marker would sit somewhere no human
drives. Anything narrower would be an arbitrary threshold; anything wider would
let the AI's conservatism set the learner's target.

**Substitution is per corner, not per element**, triggered by divergence on any
one element. Mixing a human brake point with an AI apex line inside one corner
would describe a corner nobody actually drove.

## Provenance

`source_laps` records the AI strength, the lap counts and the fixed setup; the
per-block manifest independently records `autopilot: true` and `ai_level_pct`,
read from the sim's own `car.isAIControlled` rather than from the panel toggle.
That matters because "was this block AI-driven?" is the most load-bearing fact
about a reference block: the first one recorded could only be identified as
AI-driven by noticing its lap times agreed to within one 20 Hz tick.

Should human laps ever be recorded, `source_laps.human_driver` names the
driver's **role, never a name**.
