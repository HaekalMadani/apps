# Band calibration — literature brief

**Status: asked and answered, 2026-10-14.** Tracked as M6 item 8 in `CLAUDE.md`.
The answer is the last section of this file, **"The answer, 2026-10-14"** — read
that first; everything above it is the question as it was put, kept because what
was asked for bounds what the answer may be quoted as settling. The reply itself
is `TRACE_tolerance-calibration_lit-review_v1.0.md`. **The short version: there
is no published rule to copy, which is a citable finding rather than a dead end,
and the apex element's problem turned out to be the evidence WINDOW as much as
the band.** Setting the values is still Gate G2 work.

## Why this exists

TRACE's tolerance bands are `max(σ_reference × EVM, floor)`, and in practice the
floors set every band. The EVM (3.0), the floors (5 m braking / 4 km/h corner
speed / 0.5 m apex RMS), the 0.5 braking consistency ratio and the 3-of-4
qualification window were all **chosen by judgement and then tuned in a
Monte-Carlo simulation against a synthetic novice whose parameters are themselves
assumptions**. Gate G1 certifies that the controller behaves as designed against
*a plausible learner*; it does not certify that the learner is plausible.

Two things turned that from a tidiness concern into a real one:

1. **One of the synthetic novice's parameters is now measurably wrong.**
   `apex_sigma_m` is 0.30 m where 227 real passes measure a lap-to-lap SD of
   **1.86 m**, and `apex_offset0_m` is 1.2 m against a measured mean excess of
   2.49 m. The apex half of the G1 verdict is therefore optimistic.
2. **The apex element has no workable band at all.** The trial-to-trial noise
   (1.86 m) is about the size of the whole improvement available (~2.2 m), so any
   band an improved pass clears, an unimproved pass clears on a good lap —
   measured, and metric-independent (closest approach to the apex point has the
   same ratio). Widening the floor to 2.0 m makes Gate G1 fail outright: 100% of
   simulated non-improvers lose the apex scaffold.

That is currently written up as a limitation. **Before accepting it as one**, find
out whether the literature has a principled way to set these bands — and whether
it already knows what to do when noise is the size of the signal. If it does not,
the fallback is an **empirical** justification from data already recorded:
measure each band's discriminability between early-lap and late-lap passes
(ROC/AUC) rather than sweeping it against a synthetic learner.

Supporting evidence lives in `kit/tools/README.md` (`apexscan.py`, `rescore.py`,
`brakescan.py`) and `configs/simulation/G1_REVIEW.md`.

## The prompt

Self-contained — paste into an agent with literature-search access.

---

```
ROLE
You are a research assistant with literature-search access, working for a
master's thesis in human–computer interaction / motor skill learning. Your job is
to find and evaluate the PUBLISHED, CITABLE basis for one specific engineering
decision, and to tell me honestly if there isn't one. I do not want a general
essay on motor learning. I want sourced methods I can apply, with page-level
provenance.

THE SYSTEM (enough context to answer precisely)
TRACE is an adaptive driving-assistance system for novice sim racers (Assetto
Corsa, Silverstone National/International, touring cars). Three visual scaffolds
fade independently as competence is demonstrated, and are restored on regression:
  1. a braking-point marker on the road
  2. a corner-speed target readout (HUD)
  3. an apex marker on the road
Each scaffold has a per-corner-pass PASS/FAIL criterion computed against an
expert reference (the game's AI driver at 85% strength, 12 laps, whose own
lap-to-lap variability is near zero). The criteria:
  - braking: |brake-initiation distance − expert point| ≤ band, AND within
    0.5 × band of the driver's own rolling mean of recent passes
  - corner speed: minimum speed in the corner ≥ expert minimum − band
    (one-sided: faster than the expert is not an error)
  - apex: RMS lateral deviation from the expert line over a ±15–20 m window
    centred on the apex ≤ expert's own RMS + band (one-sided)
Bands are computed as:  band = max(σ_reference × EVM, floor)
where EVM ("expertise variance multiplier", = 3.0 for an AI-sourced reference) is
meant to compensate for the AI's missing human motor noise, and `floor` is a
hard minimum per metric. Because the AI is so repeatable, THE FLOORS SET EVERY
BAND in practice: 5 m (braking), 4 km/h (corner speed), 0.5 m (apex RMS).
Decisions are then aggregated: a corner "qualifies" when its criterion holds in 3
of the last 4 passes, and de-qualifies on 2 consecutive failures; a scaffold fades
one stage when ≥75% of corners qualify and reverts below 50%. Design bias is
explicitly conservative: premature withdrawal of a scaffold is treated as worse
than delayed withdrawal.

WHY I'M ASKING
The EVM (3.0), the floors (5 m / 4 km/h / 0.5 m), the 0.5 consistency ratio and
the 3-of-4 window were all chosen by judgement and then tuned in a Monte-Carlo
simulation against a synthetic novice whose parameters are themselves assumptions.
That is "we tried values until the machine behaved", and it is the weakest part of
the thesis. I need either a principled, published way to set these, or a defensible
account of why no such method exists and what the honest limitation statement is.

THE CONCRETE PROBLEM THAT PROMPTED THIS (please answer question 4 with this in mind)
Measured on 227 real novice corner passes:
  - apex RMS deviation from the expert line: mean excess 2.49 m, median 1.52 m
  - the SAME driver's lap-to-lap SD within a single corner: 1.86 m
  - total improvement available at the apex from first lap to plateau: ~2.2 m
  - the expert reference's own RMS: 0.014–0.024 m
So the trial-to-trial noise is roughly the size of the entire learnable
improvement. Consequences measured: at the current 0.5 m floor the apex criterion
holds on 11% of passes (unreachable); at 2.0–3.0 m it holds on 61–74% — but in
simulation a band that wide also fades the scaffold for a learner who never
improves at all, which violates the system's conservatism requirement. There
appears to be NO band width that separates an improving learner from a
non-improving one on this metric. Braking and corner speed do not have this
problem (braking: the driver converged from 10.6 m to 2.4 m mean error within
three laps once given feedback).

YOUR QUESTIONS, IN PRIORITY ORDER

1. BANDWIDTH-KR BAND WIDTHS: HOW WERE THEY ACTUALLY SET?
   The system's tolerance bands are modelled on bandwidth knowledge of results
   (feedback given only when error exceeds a tolerance; silence inside it). I know
   the foundational strand — Sherwood (1988), Lee & Carnahan (1990), Lee, White &
   Carnahan (1990), Butler/Reeve/Fischman (1996), Cauraugh/Chen/Radlo, Goodwin &
   Meeuwsen, plus Winstein & Schmidt (1990) on feedback withdrawal. For each study
   you report, tell me CONCRETELY:
     - the exact bandwidth used, in the task's own units AND as a proportion
       (of the target value? of baseline error? of the learner's own SD?)
     - the stated JUSTIFICATION for that number, quoted or closely paraphrased
     - whether it was arbitrary, pilot-derived, copied from an earlier paper, or
       empirically optimised
     - whether more than one width was compared, and what the comparison showed
   I specifically want to know whether anyone has studied bandwidth WIDTH as an
   independent variable, and whether any principled scaling rule emerged
   (e.g. "x% of the target", "k × the learner's within-session SD",
   "k × the expert's SD").

2. TOLERANCE/ASSIST BANDS IN DRIVING AND SIMULATOR TRAINING
   How are error tolerances set in vehicle-control training and driver-assistance
   research aimed at NOVICES? Known starting points: de Groot et al. (2011,
   haptic/vibration feedback outside ~0.5 m of lane centre), van Leeuwen et al.
   (2011, continuous visual guidance in a driving simulator), plus racing-line /
   braking-point guidance work (including Bugeja et al. 2017 — see the warning
   below). Look also at: haptic shared control and guidance-force tuning, error
   amplification, racing/driving-line tutoring systems, flight-simulator training
   tolerances, and any sports-science work on braking-point or cornering-line
   coaching tolerances. For each: the tolerance value, the units, and how it was
   justified.

3. CALIBRATING A CRITERION AGAINST AN ARTIFICIAL (NON-HUMAN) EXPERT
   Our reference is a game AI with essentially zero variability, so the criterion
   is "within X of a performer who has no motor noise". Is there published
   precedent for:
     - using an artificial/optimal-control/computed reference as the target for
       human skill assessment, and
     - INFLATING that reference's variability to account for irreducible human
       motor noise (our EVM)?
   Our current justification for the multiplier is Cohen & Sternad (2009) on
   persistent motor noise, which supports the premise but gives no multiplier.
   Is there any empirical basis for a specific value, or for deriving it from a
   measured human performer instead? Also: is there literature on expert-novice
   variability RATIOS in continuous motor tasks that would give a defensible
   multiplier?

4. THE CORE METHODOLOGICAL QUESTION: A PER-TRIAL CRITERION ON A NOISY METRIC
   What does the literature say about deciding that a learner has improved when
   trial-to-trial variability is comparable to the total available improvement?
   I want citable methods, not encouragement. Specifically search for:
     - measurement-theoretic approaches: standard error of measurement, minimal
       detectable change (MDC/SDC), reliability (ICC) of per-trial motor measures,
       and how many trials are needed before a mean is stable enough to threshold
     - whether criteria of this kind should be applied to a SINGLE trial at all,
       or to an aggregate (and what aggregation windows are used in practice)
     - sequential / statistical-process-control methods for detecting a shift in
       a noisy process: CUSUM, EWMA, Shewhart rules, SPRT — has anyone used these
       for skill-acquisition or adaptive-training decisions?
     - signal-detection / ROC framing: setting a threshold by its measured
       discriminability between skilled and unskilled performance, and reporting
       sensitivity/specificity of a mastery criterion
     - mastery thresholds in intelligent tutoring systems and adaptive training
       (e.g. Bayesian knowledge tracing's p(mastery) conventions, adaptive
       difficulty algorithms, the Challenge Point Framework of Guadagnoli & Lee
       2004 as a basis for setting difficulty relative to current skill)
     - scaffolding/fading literature: how do faded-guidance systems decide WHEN
       to remove support, and do any of them use a measured criterion rather
       than a fixed schedule?
   If the honest answer is "a per-trial pass/fail on a metric with this
   noise-to-signal ratio cannot discriminate, and the literature says so", I want
   that stated plainly with the citations that establish it, because that is a
   publishable limitation rather than a bug.

5. DOES A DIFFERENT APEX/LINE METRIC HAVE BETTER DISCRIMINABILITY?
   How is cornering line accuracy quantified in published work — RMS lateral
   deviation over a window, distance at a single apex point, time-to-line-crossing,
   area between curves, curvature or steering-signal measures, dynamic time
   warping against a reference trajectory? Report the reliability or
   discriminability of each where published. I have already measured that
   closest-approach-to-the-apex-point has the same noise-to-signal ratio as our
   windowed RMS, so I am looking for metrics with EVIDENCE of being more stable
   trial-to-trial, not merely different.

6. ONE-SIDED VS TWO-SIDED CRITERIA
   Is there precedent for one-sided tolerance in bandwidth feedback — i.e.
   treating "better than the reference" as not an error? Our corner-speed and apex
   gates are one-sided and our braking gate is two-sided, and I would like that
   asymmetry to be defensible rather than ad hoc.

EVIDENCE STANDARDS (important — a previous citation in this project did not
survive checking)
  - Give full citations: authors, year, title, venue, DOI/URL.
  - State for each claim whether you verified it in the FULL TEXT, in the
    abstract only, or from a secondary source citing it. Never present an
    abstract-level inference as a methods detail. If a specific number (a
    bandwidth, a tolerance, a multiplier) is only visible in the full text and
    you could not access it, say so explicitly and mark it UNVERIFIED.
  - Flag anything where the commonly-cited claim about a paper appears not to be
    supported by the paper itself. In particular, check whether Bugeja et al.
    (2017) actually reports empirically-set slip-ratio/racing-line tolerances;
    this project currently cites it for that and the claim is in doubt.
  - Prefer peer-reviewed work. Theses, preprints and technical reports are
    acceptable if clearly labelled as such.
  - Note replication status or contradicting findings where they exist, and say
    where the literature is simply thin rather than filling the gap with
    plausible-sounding synthesis.

DELIVERABLE (please use this structure)
  A. Direct answer, ≤200 words: is there a principled, published method for
     setting tolerance bands of this kind for novices, and what is it?
  B. Precedent table: study | task | population | band/tolerance (units and
     proportional form) | how it was justified | verification level.
  C. Candidate calibration methods for THIS system, ranked by how well-supported
     they are. For each: the method, its citation, exactly what I would have to
     measure to apply it (I have 227 novice corner passes with per-pass metrics
     and full 20 Hz telemetry, plus a 12-lap expert reference), and what it would
     likely give for braking / corner speed / apex.
  D. Your recommendation: which method to adopt, and the one or two analyses to
     run on my existing data to justify the chosen values empirically.
  E. The honest limitation paragraph, written as I could put it in a methods or
     limitations chapter, for whatever remains unjustifiable — especially the
     apex element.
  F. Reading list: the 5–10 sources most worth my reading in full, with a
     one-line reason each.
```

---

## What to do with the answer

- **Section C is the part that earns its keep.** It is deliberately phrased as
  "what would I have to measure", because the data to calibrate empirically is
  already recorded: 227 novice passes with per-pass metrics, full 20 Hz
  telemetry, and a 12-lap expert reference per pair.
- **Anything adopted changes `controller_config.json`**, which re-pins the frozen
  hash and means re-running the Phase 1 simulation and re-reviewing Gate G1. Band
  floors are a **Gate G2** decision, so the natural place to land this is G2
  rather than a mid-M6 edit.
- **The Bugeja et al. (2017) check is folded into the evidence standards** because
  it is already outstanding as thesis-correction item 6 in `CLAUDE.md`.
- Record what comes back here, under a dated heading, including the questions that
  came back empty — a search that found nothing is itself the evidence for the
  limitation paragraph.

---

# The answer, 2026-10-14

The prompt above was run. The reply is committed as
**`TRACE_tolerance-calibration_lit-review_v1.0.md`** (sections A–H, with a
per-claim verification label: full text / abstract / secondary / unverified).
This section records what it settled, what it broke, where it was wrong, and
what was measured in response. Per the instruction above, **the questions that
came back empty are recorded too** — a search that found nothing is the evidence
for the limitation paragraph.

## A. The direct answer: there is no rule to copy

**No principled, published method exists for setting bandwidth/tolerance widths
for novices.** In bandwidth-KR research the width is almost always a fixed
percentage **of the movement goal** — 5%, 10%, 15%, 20% — justified by
convention rather than derivation. Two of the review's full-text sources say so
in as many words: Cruz et al. (2018) give "this percentage is the same observed
in previous studies", and Ugrinowitsch, Cruz & Ugrinowitsch (2018) adopt 15% "to
allow comparison with existing studies" and state that the width effect "remains
to be investigated". Studies that manipulated width as an IV **contradict one
another**: Sherwood (1988) and Lee et al. favour wider, Junqueira et al. (2015)
and Lee & Maraj (1994) favour narrower, Colen & Zubiaur found no difference.

This is a better outcome than a rule would have been. It converts the weakest
sentence in the thesis from *"the values were chosen by judgement"* into *"the
paradigm these bands were modelled on has no calibration rule, so band setting
was treated as a standard-setting problem"* — which is citable, and which the
field's own reviews say is open.

### Empty-handed, and recorded as such

- **Q1, a scaling rule** (`x%` of target, `k x` learner SD, `k x` expert SD):
  none emerged. The only learner-SD precedents are **Ishikura (2009)** (band =
  SD of the learner's own preceding 5 trials) and **Yabuki et al. (2022)**
  (individualised "adjusted" bandwidth), plus Agethen & Krause's (2016)
  performance-adaptive band. All are small, lightly replicated, in timing or
  grip-force tasks, and none is in continuous vehicle control.
- **Q2, driving tolerances**: the one recurring value is **0.5 m from lane
  centre** (de Groot et al. 2011; Petermeijer et al. 2015) and the review could
  not trace it to any calibration — the full texts are paywalled. The FAA's
  Private Pilot ACS tolerances (±100 ft, ±10 kt) are regulatory consensus with
  no published derivation.
- **Q3, inflating an artificial reference's variance** (the EVM): **no precedent
  found, at all.** The nearest neighbours are Fitts-law *effective width*
  (`W_e = 4.133 σ` of **human** endpoints) and the TRACK preprint, which
  normalises human metrics as ratios to an RL agent and explicitly **excludes**
  dispersion metrics from that normalisation.
- **Q5, a better line metric**: **no published evidence** that DTW distance,
  area-between-curves, curvature or steering-based metrics are more reliable
  trial-to-trial than windowed RMS. SDLP is the only lateral metric with
  published test–retest reliability (~0.7–0.86), and it is lane keeping over
  minutes, not a ±20 m apex window.
- **Q6, one-sided bandwidth**: **no bandwidth-KR study uses a one-sided band.**
  Cauraugh et al. (1993) reverse *which side gets feedback*, which is a different
  manipulation. The defensible framing the review offers instead is equivalence
  vs non-inferiority testing: braking is an equivalence criterion (TOST), corner
  speed a non-inferiority one, and the apex gate is one-sided **by construction**
  because an RMS is non-negative — so it must not be presented as a design choice
  parallel to corner speed.

## B. What it broke, and what replaces it

1. **The EVM has no precedent and no effect.** Retire the mechanism claim: the
   floors set all 27 bands, so `σ_ref × EVM` has never decided anything. Keep the
   field for the human-reference path (schema compatibility, and `EVM_human` is
   the path where a measured σ actually exists). **Gallagher et al. (2004)** —
   criterion = **2 SD from the expert mean**, 12 experienced surgeons as the
   benchmark — is the published form of what the EVM was reaching for, and it
   needs a *human* reference to apply.
2. **Bugeja et al. (2017) is worse than thesis-correction item 6 said.** The
   accessible record describes a **heuristic** rule system; nothing visible
   mentions slip-ratio or racing-line tolerances, or how any threshold was
   chosen. **And nothing visible supports probe-and-revert either** — the paper's
   headline result is that gains *dissipated* when feedback was removed, which is
   a guidance-hypothesis finding. It is citable for "a telemetry heuristic
   feedback system for sim racing whose gains did not survive feedback removal"
   and for nothing else. (The review also claims this project's *memory file*
   cites Bugeja for probe-and-revert; it does not — the three sites are framing
   v6 §163, eval plan L68 and L136.)
3. **The bandwidth-KR analogy has to be stated as an analogy.** Those bands
   decide when to **give feedback**, not when to **withdraw a scaffold**. Using
   one as a mastery criterion is an extension the literature does not make. Worse
   for the apex floor: bandwidth theory assumes error *inside* the band is partly
   **motor noise the learner cannot correct** (Cruz et al. 2018 citing Winstein &
   Schmidt 1990), which argues the band should be **at least as wide as the
   noise** — so a 0.5 m floor against 1.86 m of lap-to-lap scatter is wrong on
   the paradigm's own terms, independently of discriminability.
4. **Repeated looks.** The controller re-evaluates 3-of-4 **every lap**. A single
   3-of-4 check at a midpoint threshold false-passes a non-improver ~7%; fifteen
   looks take that to ~37% in the review's model. Nothing in this repository had
   acknowledged per-lap re-evaluation as a statistical property. This is the one
   genuinely new methodological criticism and it belongs in the limitations.

### The replacement citation set

| parameter | was justified by | now |
|---|---|---|
| band floors | judgement + simulation sweep | contrasting-groups cut-score, **Jørgensen, Konge & Subhi (2018)**; report theoretical false-pass/false-fail |
| EVM | Cohen & Sternad (2009) on persistent motor noise (supports premise, gives no value) | retired on the AI path; **Gallagher et al. (2004)** "2 SD from expert mean" if a human reference is ever recorded |
| window length (3-of-4) | "it behaved" | minimal detectable change, **Weir (2005)**; size `n` so MDC95(n) < the available improvement |
| asymmetric enter/exit (one regression, one stage) | design reasoning | **Petermeijer, Abbink & de Winter (2015)** hysteresis variant |
| sequential proficiency decision | — | **Biau et al. (2008)** LC-CUSUM — considered, **not adopted**; record the reason |
| mastery threshold by simulation | "we tuned it" | **Pelánek & Řihák (2017/2018)**: threshold and data choice matter more than the learner model, and calibrating a *decision rule against a stated error rate* is legitimate |
| braking consistency sub-gate | judgement (0.5 × band) | **Ishikura (2009)**, **Yabuki et al. (2022)** — learner-own-SD band, as a weak precedent for *this* gate only |

## C. Where the review was wrong

- **Its C.0 point 3 infers that the simulation's corner errors must be
  correlated.** They are not: `simulate.py` draws `difficulty` independently per
  corner. The actual reason `apex_m = 2.0` fades a simulated non-improver is that
  that learner's apex excess is `1.2 × U(0.6,1.6)` ~ 1.3 m mean with σ 0.30 m, so
  a 2.0 m band simply **contains** it. The between-corner correlation question it
  raises is still worth answering on real passes, but it is not what the
  simulation was detecting.
- **Its own numbers are not reproducible.** Section C.0's MDC, SPRT and
  3-of-4 figures come from a `disc.py` that is "available on request". A number
  that cannot be recomputed is not evidence — the standing rule in
  `kit/tools/README.md`. So the load-bearing part was re-derived inside this
  project's own simulator instead (`kit/tools/windowscan.py`).
- **Its Rank 5 is already rejected here for a reason it does not address.** A
  learner-σ band needs session-1 state carried across blocks, against the
  block-scoped rule. Confining it to the braking consistency gate, as the review
  does, is consistent with that.
- Several B.1 rows are **ABS/SEC with the band value itself marked UNVERIFIED**,
  including Sherwood (1988) — the paper the design cites by name. **Chen (2002)**
  is the one study whose title names tolerance range size as an IV and it was not
  obtained. Three full texts would change something: Chen, Petermeijer (how 0.5 m
  was justified), and Bugeja (or drop it).

## D. What was measured in response (`kit/tools/windowscan.py`)

The review's central claim — that a pass/fail vote over four passes discards
information a longer window keeps — was testable in this project's own simulator
and had never been tested, because `SWEEP_GRID` excludes the qualification window
by design. Full tables in `kit/tools/README.md`; the consequences for the gate
are the third 2026-10-14 note in `configs/simulation/G1_REVIEW.md`. Harness
validated first: at the committed seed and stream count it reproduces
`simulation_report.json`'s `mean_elements_removed` for every learner type.

1. **Braking never completes a traversal — 0% of streams, every learner type.**
   Gate G1's "2 of 3 elements" is corner speed (83% removed) plus the **apex**
   element (74%). The G1 review's sentence saying braking carried it is now
   struck there.
2. **Correcting the apex model fails Gate G1's first target.** With the measured
   novice (2.49 m / 1.86 m) the typical improver drops from **1.565 to 0.828**
   elements removed and apex removal to 0%, leaving corner speed alone.
3. **"No band width works" was conditional on the 3-of-4 window.** At 4-of-6
   with a 1.5 m floor: 41% of typical improvers advance the apex element, **0%**
   of non-improvers. At 8-of-10 with 2.5 m: 87% and 0%, dominating 3-of-4 at
   2.0 m (82% and 4%) on both margins. The review's aggregation argument
   reproduces.
4. **The lap budget caps the window, and a 6-pass window buys ONE apex stage.**
   The floor is `2 × required_passes + max(probe.laps, required_passes) <= laps`
   — 9 laps at 3-of-4, 12 at 4-of-6, the whole block at 5-of-6, impossible from
   6-of-8 up. (Corrected 2026-10-14: first written as
   `2 × window_passes + probe.laps`; readiness is keyed on `required_passes` and
   it gates the probe's own completion too.) Measured: at **4-of-6, floor 1.5 m**
   the apex element reaches `reduced` in 40% of typical-improver blocks, enters a
   probe in 1% and completes in **0%**, at a 0% non-improver false-advance rate —
   while every floor that does complete also advances a non-improver (2.0 m:
   2% vs 4%; 2.5 m: 23% vs 13%). So MDC wants n >= 6 and the block cannot
   traverse at n >= 6: **within one block the apex element can be decided once,
   not traversed.** That is the limitation, stated with an arithmetic cause
   rather than as a noise complaint.
5. **The window change must be per element.** A global move to 4-of-6 takes
   corner-speed removal from 83% to 1%, with 94% of blocks ending mid-probe.
6. **σ/band per element predicts the whole verdict**: corner speed
   2.0/4.0 = 0.50 (traverses), braking 4.0/5.0 = 0.80 (never), apex measured
   1.86/0.5 = 3.7 (undecidable per pass). The braking consistency gate is most of
   braking's share — left-`full` 4% -> 51% -> 84% as the ratio goes 0.5 -> 1.0 ->
   2.0 — but with the gate off, removal still only reaches 2%.

## E. What is adopted

**The reframing, not the re-architecture.**

- Band floors become **cut-scores on recorded passes** (contrasting groups),
  window length comes from **MDC**, and the EVM is retired from the AI path.
- **Declined: EWMA, LC-CUSUM/SPRT and window-statistic gating** (the review's
  Ranks 3 and 4). They rewrite both controllers, churn the golden-trace parity
  corpus, and would be validated by the same simulation whose learner model is
  the thing in question. Framing v6 withdrew window-level gating in favour of a
  per-pass boolean and that still holds: the per-pass boolean plus a `k`-of-`n`
  window **is** an aggregation. What was never done is sizing `n` by measurement
  theory, and that is fixable without changing the mechanism. Record the
  sequential methods as considered-and-rejected with this reason — that is a
  stronger position than not knowing about them.
- **One structural change, at Gate G2, and it is now a PREREQUISITE rather than
  a refinement:** `qualification` becomes **per element**, so the apex element can
  run a 6-pass window while corner speed keeps 4 — because a global 6-pass window
  takes corner-speed removal from 83% to 1%. The floor arithmetic
  (`2 × required_passes + max(probe.laps, required_passes) <= laps`) is written
  out beside it, and with it the consequence that the apex element's realistic
  ladder inside one block is **full → reduced only**.
- **The braking consistency gate moves to the front of the G2 queue.** It is why
  one of three elements cannot traverse at all, and it is the element bandwidth
  KR demonstrably fixed in three laps.

### The two analyses that set the numbers (both on data already recorded)

1. **Reliability and MDC per metric.** Mixed model
   `per-pass metric ~ lap (or an exponential learning term) + (1|driver) +
   (1|corner)`; take the residual SD as σ_within and compute ICC, then
   MDC95(n) = 1.96 × sqrt(2) × σ_within / sqrt(n) for n = 1…10 for braking,
   corner speed and apex. Also the between-corner residual correlation within a
   lap, which decides whether the quorum adds protection. Output: one row per
   metric with σ_within, ICC, MDC95(4), MDC95(6), MDC95(8). **This replaces the
   3-of-4 justification.** Caveat the review flags and it is right: σ must be
   computed on **detrended** residuals or plateau laps only, or it contains the
   learning trend and overstates noise; and the apex distribution is
   right-skewed (mean 2.49 vs median 1.52), so a window **median** and a
   non-normal treatment are safer than the normal-theory arithmetic.
2. **Contrasting-groups ROC on the window statistic.** Early laps (1–2) vs each
   driver's plateau laps, for window sizes n in {1, 4, 6, 8}; place the cut at
   <=5% theoretical false-pass and **report false-fail** (Jørgensen et al. 2018's
   reporting style). If apex AUC at n = 6–8 is still < ~0.8, that is the empirical
   evidence for the limitation rather than an argument about it.

Both are Gate **G2** work: anything adopted changes `controller_config.json`,
which re-pins the frozen hash and re-opens Gate G1. **Nothing here changed a
config value.**

## F. The limitation paragraph

Section E of the review is a drafted limitation paragraph and it is close to
usable. Two corrections before it goes in the thesis: its "no band width
separates improving from non-improving learners" must be narrowed to the
**per-pass** criterion (point D.3 above), and its 28% / 6–8-pass figures come
from an unreproducible script and must be re-derived from the MDC analysis in E.1
before being quoted.

## G. Reading list, in the order it earns its keep

1. **Jørgensen, Konge & Subhi (2018)**, *Adv. Simul.* 3:5 — the method adopted,
   and how to report false-pass/false-fail with small groups. Open access.
2. **Weir (2005)**, *J. Strength Cond. Res.* 19(1):231–240 — the ICC/SEM/MDC
   arithmetic cited for window length.
3. **Pelánek & Řihák (2018)**, *New Rev. Hypermedia Multimedia* 24(3):133–159 —
   mastery-criterion design; the licence for calibrating a decision rule against
   a stated error rate.
4. **Chen (2002)**, *J. Hum. Mov. Stud.* 42:141–154 — the one bandwidth study
   with tolerance range size as an IV. Its actual numbers are still unseen.
5. **Ugrinowitsch, Cruz & Ugrinowitsch (2018)**, *ConScientiae Saúde*
   17(2):155–163 — the most explicit published statement that width is
   conventional and unresolved. Quotable. Open access.
6. **Gallagher et al. (2004)**, *Surg. Endosc.* 18:660–665 — "2 SD from the
   expert mean", the template for a human-expert replacement for the EVM.
7. **Petermeijer, Abbink & de Winter (2015)**, *Human Factors* 57(1):5–20 — how
   the 0.5 m band was justified, and the hysteresis variant as precedent for
   asymmetric enter/exit. Green OA via mediaTUM.
8. **Biau et al. (2008)**, *Br. J. Surg.* 95:925–929 — LC-CUSUM, to cite as the
   sequential alternative considered and not adopted.
9. **Bugeja, Spina & Buhagiar (2017)** — via UM OAR "request a copy", handle
   `123456789/106531`, or the 2016 B.Sc. dissertation, handle `123456789/14720`.
   **Mandatory before the citation is kept in any form.**
10. **Ishikura (2009)**, *Doshisha J. Health Sports Sci.* 1:39–44 — the only
    learner-SD band precedent; open access, Japanese original.
