# TRACE dataset — README

This is the README that ships **with the released dataset**, not with the code.
It is kept in the repository so that the facts a reader needs in order to
interpret the data are written down when they are established, not reconstructed
at submission time. Sections marked *(pending)* are filled as the study runs.

Apparatus and design are described in the thesis; this file records what is in
the data files, how they were produced, and what is known to be wrong with them.

---

## 1. What the dataset contains

Per recorded block (a single ~30-minute drive by one participant in one
condition):

| File | Contents |
|---|---|
| `manifest_<block>.json` | Block provenance: participant, session, sequence, condition, pair, car, track, track length, app/CSP/AC versions, SHA-256 hashes of every config the block loaded, and whether the block was AI-driven. |
| `ticks_<block>.csv` | 20 Hz telemetry, one row per tick. Columns are described by `configs/ticks_columns.json`. |
| `passes_<block>.jsonl` | One record per corner pass: which corner, which lap, whether the pass was valid and why not; the three raw metrics (brake-initiation distance, minimum corner speed, apex RMS) plus the raw brake-initiation sample and a descriptive brake-modulation summary; the per-element criterion booleans, with the braking criterion's two gates logged separately; the corner's per-element qualification state; and the element-level controller stage — all as they stood **after** the pass was folded in. |
| `fades_<block>.jsonl` | One record per controller transition: element, transition type, lap, session-clock time, the triggering quorum statistics (qualified share, which corners were qualified, which flipped, how many were applicable) and the element's reversion count. Present on every block that ran with a reference loaded, including `static` blocks — where the controller runs invisibly. |

A metric or criterion of `null` means **not measurable on that pass**, which is
not the same as a failure: such a pass is dropped from that element's evidence
window entirely rather than counted against the driver. Analyses that treat a
null as a zero or a false will misread the data.

Supporting configuration, versioned alongside the code:

| File | Contents |
|---|---|
| `configs/annotations/annotation_<track>.json` | Per-corner gates and evaluation zones for one track layout. |
| `configs/references/reference_<pair>.json` | Per-corner expert reference for one car–track pair: brake point, apex line, corner-speed envelope, per-metric σ, and how many reference laps built each. |
| `configs/controller_config.json` | Every free parameter of the fading controller and the renderer: the EVM multipliers, the band floors, the qualification and quorum rules, the probe rules, the braking consistency delta, and the salience alphas and reduced form. Frozen at Gate G1 as `frozen-g1`. |
| `configs/simulation/` | The Gate G1 record: the design-target verdicts (`simulation_report.json`), the parameter sweep behind the frozen values (`sweep_report.json`), the feasibility figure, and the review (`G1_REVIEW.md`). |
| `golden_traces/` | The controller parity corpus: input traces with the exact event sequence both implementations of the state machine must reproduce. Published because it is the executable specification of the mechanism. |

Each block's manifest carries the SHA-256 hash of the config files it loaded, so
any row in the dataset can be traced to the exact parameters in force when it was
recorded.

---

## 2. How the expert reference was produced

The reference for each car–track pair is **12 laps driven by the Assetto Corsa AI
at 100% strength**, on the participants' car and default setup, recorded through
the same telemetry pipeline as participant data. Lap-time coefficient of
variation was 0.064% (pair 1) and 0.092% (pair 2). Per-corner provenance —
including how many laps contributed to each element of each corner — is stored in
the reference tables themselves and reviewed in
`configs/references/G0_REVIEW.md`.

Tolerance bands are not stored in the reference; they are derived as
`max(σ_ref × EVM_source, floor)`, with the multipliers and floors living only in
`controller_config.json`.

---

## 3. Known limitations of the data

### 3.1 The expert reference has no human validation

**The reference is AI-only.** The study design called for a set of validation
laps from an experienced human driver, used to substitute the reference on
corners where the AI's known biases (it brakes conservatively and does not trail
brake) put its line outside what a competent human would drive. **Those laps were
not recorded, and no corner is human-substituted.**

The reason is not that the step was skipped for convenience. No experienced sim
racer was available, and the researcher is a beginner. A reference recorded by a
beginner is not a weaker *expert* reference — it is a *novice* reference, and
substituting it would have pulled the target toward novice performance, so the
scaffold would fade precisely when a participant drove like a beginner. That
inverts the premise of the intervention, so recording it would have been worse
than omitting it.

Consequently: **the claim that the AI's brake points fall within a competent
human's tolerance is not established by this dataset.** Two things bound the cost
without removing it:

- The bias runs in the safe direction. The AI brakes early; novices brake early.
  An AI reference is therefore a *less* demanding target than a real expert's,
  which is the right direction to err for a scaffold a novice must reach. This
  makes the error benign, not absent.
- The bands are floor-dominated. Measured σ was 0.005–0.015 m (apex line),
  0.58–1.14 m (brake point) and 0.15–1.04 km/h (corner speed), against the
  frozen floors of 0.5 m / 5 m / 4 km/h. **All 27 bands** (9 corners × 3 metrics)
  are set by their floor, so `EVM_AI` currently has no effect on any criterion at
  all. A bias smaller than a floor is absorbed by the band. Note the limit of
  that argument: a floor *widens* a band, it does not *re-centre* it, so a bias
  larger than the floor still bites.

The empirical check that the reference is reachable by real novices therefore
falls entirely to the pilot (Gate G2), where the band floors are calibrated
against real novice distributions. The comparison and substitution tooling
(`trace_kit.reference compare`) is built and tested, so restoring the validation
is two commands if an experienced driver becomes available.

### 3.2 Scope of the apparatus

Two car–track pairs, both Silverstone layouts, both road/touring cars. No claim is
made that thresholds, schedule, or effects generalise beyond the tested cars,
tracks, and population.

### 3.3 What the competency gates do and do not measure

The per-pass criteria are a **heuristic trigger for when to run an unassisted
probe**, not a measurement of learning. The probe stage is the retention test.
Nothing in this dataset certifies that a participant internalised anything.

### 3.4 What to expect in the fade logs

These are properties of the mechanism established by the Phase 1 simulation
(Gate G1, 2,800 synthetic streams — `configs/simulation/G1_REVIEW.md`), recorded
here because they shape how the fade-event stream should be read rather than
being findings about participants.

- **Partial traversal is the expected case.** No simulated learner cleared all
  three elements inside a 15-lap block. The design target asks for 2 of 3, and
  the block is time-boxed. A participant whose braking marker never fades is
  ordinary, not an outlier.
- **A substantial share of probes end censored.** About 38% of typical-improver
  streams finished mid-probe. Right-censored probes count as neither held nor
  reverted, so the probe-outcome tabulation has a large censored cell by design.
- **The reversion cap was never reached** in simulation, including by the erratic
  learner type. If a real participant hits it, that is a genuinely novel
  observation and worth reporting as an individual case.
- **An element can stall.** If a corner never yields a measurable metric for an
  element — the shape a mis-fitted evaluation zone takes — that element never
  becomes quorum-ready and stays at full salience for the whole block, emitting
  no fade events. A block with no events for one element and normal events for
  the others should be checked against that corner's null counts before being
  read as "this participant never improved".
- **`static` blocks carry a full fade log too.** The controller runs in every
  condition; only the rendering is pinned. Those transitions describe what the
  controller *would* have done under static visibility and are counterfactually
  valid only up to the first would-have-faded transition — beyond that point an
  adaptive participant's behaviour is endogenous to the fade. Report them as
  *controller state under static visibility* and nothing stronger.

### 3.5 Exclusions *(pending)*

Every excluded participant or block is listed here with the reason, per the
pre-committed exclusion rules in the evaluation plan.

**How a block is excluded mechanically.** Three markers in the block manifest
each mean "never pool this with participant data", and each is present *only*
when true — a participant block carries none of them, so the absence of all
three is what makes a block study data. They are not interchangeable and the
reasons differ:

| Marker | Meaning | Added at |
|---|---|---|
| `dev_block` | Scratch recording that opted out of the annotation gate; may have no passes at all. Reference laps are recorded this way. | M2 |
| `aborted` + `abort_reason` | The experimenter discarded the block from the panel. `abort_reason` is a closed enum (`participant_request`, `sim_or_app_crash`, `hardware_fault`, `experimenter_error`, `protocol_deviation`, `other`). | M6 |
| `dry_run` | Protocol-rehearsal block (M6), the researcher driving as a fake participant. A full study block in every other respect — both gates pass and the controller runs — so this flag is the only thing keeping the rehearsal out of the dataset. | M6 |

An **aborted** block keeps its partial logs: the abort discards the block, never
the record of what happened, so the files stay on disk and stay auditable.
`trace_kit.analysis` reports every excluded block with its kind and, for aborts,
its reason — which is what populates this section.

### 3.5.1 Instrument responses

Questionnaire responses are schema-validated JSON files stored alongside the
block files (`schemas/instrument.schema.json`; drafts and administration notes
in `instruments/`). One file per administration:

- `pre_study` — session 1 intake, per participant
- `nasa_tlx` — **raw/unweighted (RTLX)**, per session-2 training *block*
- `post_study` — session-3 confidence and perceived dependence, per participant
- `interview` — session-3 interview metadata and file references

The NASA-TLX variant is recorded in every file as `responses.variant: "raw"`, so
the unweighted form is a documented fact about the data rather than something a
reader has to infer. Reverse-scored items are stored **raw, as the participant
marked them**; reversing happens in analysis, so the stored data always matches
the paper they saw.

### 3.6 Recruitment fallbacks invoked *(pending)*

If the pre-committed degraded fallback (dropping the retention probe, or
accepting n = 10) is invoked, it is recorded here with the date and the reason.

---

## 4. Reproducing the checks

With the toolkit installed (`kit/`, conda env `ac_dev`):

    python -m trace_kit.integrity "<path to trace_data>"

checks, for every block in a directory: manifest schemas; tick gaps and lap
reconciliation; the per-pass and fade-event streams (schema validity, block-id
match, one pass per corner per lap, and a **replay of the fade sequence** that
rejects any ordering no state machine could have produced); and apparatus drift
(CSP/AC/app versions and track length) across blocks. Over a directory it also
checks that each recorded session's **instrument files are saved** — the
evaluation plan's fourth after-every-session clause. (`--no-instruments`
suppresses that one, for scanning an archive of old test recordings that predate
the instrument format.)

    cd kit && python -m trace_kit.analysis rq1 "<path to trace_data>" --out <dir>

ingests the blocks into flat tables and writes the RQ1 descriptive report, the
fade-trajectory figure and the RQ3 alignment table. `analysis ingest` emits the
tables alone. Both exclude non-participant blocks by default; `--include
dry_run` analyses the protocol rehearsal instead.

    cd kit && python -m trace_kit.simulate run --streams 200 --out ../configs/simulation

re-runs the Gate G1 simulation. It is deterministic from its seed, so it should
reproduce `configs/simulation/simulation_report.json` exactly.
