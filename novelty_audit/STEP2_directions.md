# Step 2 — candidate directions from the gap map

**Date:** 2026-10-30 · **Input:** `NOVELTY_AUDIT_v9.md` (pass 2, full texts) ·
**Next:** step 3 puts v9 and these alternatives through the `llm-council`.

Evidence and options for the author, not chapter prose. Each direction is scored on
three things: what survives the audit, what the built system already gives it, and
whether it is feasible in **one ~33-min sitting at n ≈ 15**. The sitting length comes
from CLAUDE.md "Protocol and session budget".

---

## 1. The gap map in one table

| Gap | Status after pass 2 | Who names it | Cost to fill |
|---|---|---|---|
| **G-null:** no calibrated no-dependency null for fade or mastery decisions | **Open.** Checked in full text against Pelánek & Řihák, ARRS, Zhang 2025 and Eneano. Linden covers only the single-cutoff case | none; strongest because nobody has framed it | low: the simulator exists (`trace_kit.simulate`, `non_improver` model) |
| **G-impl:** probe-gated withdrawal never *implemented* for real-time motor cues | **Open, but the idea is taken.** Eneano 2026 proposes it, ARRS implements it for cognitive skills, Kinesthetic-CPR reverts on cue-off degradation | Eneano: adaptive vs scheduled withdrawal "with unaided assessment held constant" is untested | already built (M4–M6) |
| **G-rel:** within-session per-corner reliability in sim racing | **Open.** Irwin 2019 used t-tests plus CV on one corner; TRACK: "the first rung was never implemented" | TRACK, explicitly | very low: `kit/tools/mdc.py` already computes ICC / MDC (n = 1 driver) |
| **G-rate:** premature-withdrawal rate for system-initiated removal of motor cues | **Open in this form.** Measured elsewhere: ARRS 18–41%, Debeauvais 38–80% re-enabling after the next race, Pelánek wMAD | Shen (plateau), Hsieh (floor clamp) handle it heuristically | needs probe events (see §3) |
| **G-valid:** is the *source of adaptation* accurate? | **Supported as a stance.** Nickl 2024 found adaptivity gave no benefit and proposes validating the adaptation source | Nickl 2024 | free: it is how RQ2 is framed |

Closed or weak: novelty of the learning/performance distinction, catch trials,
reversible fading, fading in racing (v9 §9 already disclaims all four). Telemetry
coaching in AC (Bugeja 2017; Bugeja is also the AC precedent for tolerances tightened
as the driver improves).

---

## 2. Directions

### A. v9 as written, with the audit's repairs

v9 already aims at G-null + G-rel + G-impl. The audit does not overturn it. Required
repairs:

1. §3 "no system uses cue-off probe performance as the fading decision" must
   become "**no implemented** real-time motor system…". Cite Eneano (idea), ARRS
   (cognitive analogue) and Kinesthetic-CPR (revert on cue-off degradation).
2. §11: cite Nickl as the adaptation-validation precedent. Bugeja's "fades or
   reverts?" is answered no, but the tolerances *are* empirical.
3. Add Linden as the closed-form special case the simulation generalises.

**Novelty:** C3 is carried, C1 is narrowed to "first implementation". **Risk:** four
RQs, and the core RQ (RQ2) is starved of events (§3).

### B. Audit-first (re-ranked v9). **Recommended**

Same data, same system, same RQs, re-ranked so the surviving novelty leads.

- **Headline contribution = the method (G-null):** a calibrated no-dependency null
  for auditing *any* guided-qualification fade rule, plus the probe as its
  observation. TRACE is the instrument that makes the audit possible.
- **RQ1 (G-rel) is the calibration input, reported as a finding in its own right.**
  It fills TRACK's named gap, and the null cannot be built without it. Ordering it
  first is logical, not cosmetic.
- **RQ2 is framed through Nickl:** "is the adaptation source accurate?", not "does
  adaptivity help?". That is the stance the recent literature asks for.
- **External anchors, as context only:** ARRS's 18–41% and Debeauvais's 80%
  brake-line re-enable rate are the only measured premature-removal rates in
  neighbouring domains. They are not comparable populations, so report them beside
  Δ, never against it.
- **RQ4 (desynchrony) goes to an appendix or is cut.** It was v8's core and the audit
  found nothing that makes it novel. RQ3 (parity, real time) stays as the system
  chapter's evidence, not a research question. That leaves two RQs.

**Novelty:** the strongest surviving set. **Cost:** a framing rewrite, no new code.
**Risk:** inherits A's event-count problem in full (§3). B does not solve it; it
just stops pretending RQ4 compensates.

### C. B plus a simulated multi-rule audit ("C-lite")

> **Step 4 update (2026-10-30): pre-empted for tutoring systems** by Ye et al. 2016,
> who calibrate rules (including M-in-a-row) on simulated perpetual non-learners.
> Keep it as positioning only, citing Ye, not as a contribution.

Run the null simulator against the **published fade rules**, not only TRACE's:
- Hsieh's EMA-clamped opacity;
- Shen's assisted-score rule with its lower-bound curve;
- Bugeja's tighten-as-you-improve tolerance;
- TRACE's 2-of-3 quorum.

The question for each is: *under a learner who does not change, how often does this
rule withdraw the cue?* That is each rule's false-fade rate, which is exactly what
G1 target 2 already measures for TRACE (5.75%).

- **What it buys:** demonstrates contribution 2's "reusable for other adaptive
  guidance systems" claim instead of asserting it, and it is the first comparative
  number on any of these rules' specificity. **No participants needed.**
- **Constraint:** the rules are re-implemented from papers, so state that each is a
  faithful reading, not the authors' code. Hsieh and Shen are specified in their full
  texts. Bugeja's tightening rule is not ("decreased as the user improves"), so it
  needs an assumed form or should be left out.
- **Why this is not v8's policy replay, dropped in v9 §13:** replay on *participant*
  data has no probe outcome for laps where TRACE's own rule did not probe
  (off-policy, missing outcomes). C-lite runs on *simulated* noise only, where
  ground truth is known by construction. The off-policy problem does not arise.
- **Novelty check owed:** I have not searched for "false-positive rate of adaptive
  guidance rules under simulated non-learners". That belongs in step 4's protocol
  alongside C3.

### D. Reliability-first (fallback)

Make G-rel the thesis: per-element ICC / SEM / MDC for novice sim racing, with TRACE
as the measurement apparatus. Cheapest and safest, since the tooling exists and TRACK
asks for it by name. **But** it is thin for a thesis on its own, and it orphans the
controller, which CLAUDE.md treats as a first-class contribution. Keep it as the
**publishable first chapter or short paper inside B**, and as the fallback if the
step-4 search finds a prior null.

### E. Outcome trial: adaptive probe-gated vs scheduled withdrawal (rejected)

This is Eneano's proposed trial transplanted to motor cues: it would fill their named
gap directly. Rejected:
- It needs ≥ 2 arms with matched unaided probes and a retention test, at
  n ≈ 15 (~7 per arm).
- CLAUDE.md and v9 §9 both rule out learning or significance claims.
- Eneano themselves call for a powered, multi-centre trial.

Name it as **future work**, citing Eneano.

### F. Self- vs system-initiated cue removal (parked)

Debeauvais is the observational precedent for player-initiated removal, with an 80%
next-race re-enable rate for the brake line. A learner-controlled arm would be
interesting, but **the self-controlled feedback literature is large and was not
searched**, so its novelty is unknown. Park it unless the author wants a novelty pass
on it.

---

## 3. The problem every direction except D inherits: probe events

RQ2 is a rate, and a rate needs events. Estimate from the committed Phase 1 report
(`configs/simulation/simulation_report.json`):

*(Superseded by §3a, which measures this directly. The estimate below is kept
because §3a's "more probes than estimated" refers to it.)*

- Typical improver: **1.85 elements removed per block**, with **38%** of blocks
  having any reversion. Each removal implies one completed probe, so that is
  **~2 probe events per participant**.
- **That is the committed model, which CLAUDE.md flags as optimistic.** With the
  measured apex novice it drops to ~0.83 removed, almost all of it corner speed.
- So at n ≈ 15 expect **~15–30 probe events pooled, mostly on one element**. RQ2's
  "per element" and "by corner type" breakdowns are not estimable at that count.
  A pooled proportion from ~20 events has a 95% CI of roughly ±0.2 before the null's
  own uncertainty is added.
- F3's "≥ 40 qualification events per arm" for the randomised arm is
  **out of reach** with this controller. The arm-B validation of the null
  (v9 §7.4) is therefore effectively off, which leaves Δ model-based only.

**The lever is v9 §5.2's per element × corner controller.** The frozen controller is
per *element*, with a cross-corner quorum (CLAUDE.md, "The fading mechanism"). Moving
to per element × corner fading would put up to ~4× more probe events per participant
on pair 1's four corners. That might make F3 reachable. It might also make the
per-corner gate lean on the per-pass noise the quorum was added to absorb (ICC 0.12 /
0.10 for corner speed / apex). **This is the single decision that most changes what
B can report**, and it is an implementation and research decision, not a framing one:

| | per element (frozen, `frozen-g1b`) | per element × corner (v9 §5.2) |
|---|---|---|
| Probe events / typical participant | **2.83** (measured, below) | **11.59** |
| Non-improver ends with a cue off full (G1 ≤ 0.10) | 0.085 ✓ | **0.790** ✗ |
| Non-improver has a cue *removed* | 0.005 | **0.295** |
| Removal despite regression (G1 ≤ 0.02) | 0.000 ✓ | **0.055** ✗ |
| Randomised arm (F3, 80 probes) | ~28 participants | ~7 participants |
| Cost | none | controller rewrite in Lua and Python, golden traces regenerated, G1 re-run |

### 3a. PRICED (2026-10-30, `kit/tools/percornerscan.py`, results in `kit/tools/README.md`)

Paired synthetic streams, pair 1, committed novice model (measured apex
parameters), 400 streams per learner type. Element mode reproduces
`simulation_report.json` exactly at its own seed.

- **Per corner is ruled out as the deployed controller.** It quadruples probes by
  fading on noise:
  - 79% of never-improving learners end with some cue off full, and 30% have one
    removed;
  - removal despite regression is 5.5%.

  **No per-corner window rescues it.** Across 2-of-3 … 5-of-5, false fades never
  fall below 22%, and removal-despite-regression rises to 6–16% as the window
  tightens, because the longer ladder lands removal after the regression onsets.
  It fails both G1 bounds at every setting tried. (For RQ2 this is a nice
  illustration: it is exactly the premature fading the null is built to expose.
  But it must not run on participants.)
- **The element controller yields more probes than estimated above.** It is 2.83
  per typical participant, not ~1–2, because the earlier figure came from
  CLAUDE.md's stale frozen-g1 numbers; the committed model already carries the
  measured apex parameters. At n = 15 that is ~42 probes pooled, a 95% CI of
  about ±0.12, and per element ~16 / 15 / 11 (braking / corner speed / apex),
  with CIs of ±0.2 or wider. F3's randomised arm (80 probes) would need ~28
  typical participants, so it stays off at n ≈ 15.
- **The noise-only null differs sharply by element.** This is the most useful
  output for B:

  | element | noise-only probe-fail rate | reading |
  |---|---|---|
  | corner speed | **0.00** | σ/band 0.5: any observed failure is dependency, *if* the speed sigma (an assumption) is right |
  | braking | **0.16** | **the element where Δ is best identified** |
  | apex | **0.53** | the null swamps any plausible dependency at these counts |

  So RQ2's per-element question has a predictable shape before any data exists.
  Pre-registering that prediction is cheap, and it is a good test of the method.

### 3b. What to do instead: per-element decisions, per-corner analysis

The probe is element-wide (the cue disappears at every corner at once), so each
probe already yields **4 corners × 2 laps = 8 cue-off corner passes**: roughly 23
per typical participant. RQ2's "by corner type" breakdown can be estimated from
those *within* the safe controller, as clustered observations, with no controller
change. The decision stays per element; the analysis goes per corner. v9 §5.2 should
say that, and CLAUDE.md is right on this point, not stale.

---

## 4. Recommendation

**B, with C-lite as a no-participant extension and D as its first chapter.**

- The order of evidence matches the order of dependence:
  reliability → noise model → null → Δ, then the same null applied to other
  published rules.
- Every claim it makes survived pass 2 in full text.
- It reuses the built system rather than orphaning it.

**Before step 3, two things would sharpen the council run:**

1. ~~Price the per-corner controller in simulation~~ **Done (§3a):** ruled out;
   use per-element decisions with per-corner analysis (§3b).
2. **Author decision: KR during probes.** v9 and the repo both switch KR off during
   a probe. So Δ measures dependency on *cue plus KR*, not on the cue alone.
   That is defensible (a retention test with feedback is not one; Winstein & Schmidt
   1990), but **RQ2's wording says "cue dependency"** and should say "guidance
   dependency", or the confound becomes a reviewer's first objection.
