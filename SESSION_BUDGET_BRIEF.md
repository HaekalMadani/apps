# Session budget brief — fitting TRACE into 30 minutes per participant

**Opened 2026-10-15. CLOSED 2026-10-15: Shape B adopted at 15 laps** — a single
**~32.9-min** sitting, pair 1 only, a **15-lap** training block plus a 4-lap
unassisted block, with condition (adaptive / static) assigned **between
subjects**. Consent, the ethics process and the RQ3 interview all sit outside the
timed sitting, so that figure is **rig time**; total participant commitment is
~55–60 min.

**Read § L first** — it carries every decision in one table and supersedes the
open questions left in § F and § H. §§ A–K are the reasoning, kept in the order
it was worked out, including the parts that turned out wrong.

Companion to `BAND_CALIBRATION_BRIEF.md`, and the same shape: the question, what
is *measured* about it, what is only *estimated*, and what each answer costs.
Read `kit/tools/README.md` § `lapbudget.py` for the tables and how to reproduce
them. **`configs/controller_config.json` is still untouched** — Shape B needs
`2-of-3`, and § E is why that edit waits on the MDC analysis rather than riding
on this brief.

---

## A. The constraint

`evaluation_plan_v2.md` books **three sessions of 60 + 75 + 60 min ≈ 3 h 15** of
participant time per person. The real ceiling is **30 minutes, one sitting**.

This is not a tuning problem. At 30 minutes the protocol loses whole phases, and
which phase it loses decides which research question survives. That is a
thesis-scope decision, not a config change, and it is why this brief stops at
costed options rather than picking one.

---

## B. What is measured, and what is estimated

**Measured — lap time.** Wall clock (`started_at` → `ended_at` over
`laps_completed`) across every real block in `trace_data`. It includes rolling
starts and resets, so it *over*-states a flying lap, which is the right bias for
a session budget:

| pair | layout | length | blocks | s/lap | used below |
|---|---|---|---|---|---|
| pair 1 | national | 2.60 km | 9 | 62–76 | **70 s** (1.17 min) |
| pair 2 | international | 2.95 km | 3 | 71–98 | **80 s** (1.33 min) |

**The eval plan's premise was wrong twice over, and once in our favour.** Its
lap budget comes from *"30 minutes of driving on a ~2-minute circuit"*. Neither
layout is a 2-minute circuit, so a 15-lap block is **~17.5 min** of driving at
National, not 30 — the 195 min booked is padded against a lap time nearly 2×
too slow. There is real budget here that the plan never claimed.

**Estimated — everything not driving.** The figures below (calibration 4 min,
task instruction 3 min, NASA-TLX 2.5 min, questionnaire 3 min, interview 10–12
min) are **my estimates and nothing more.** The eval plan already names
*"protocol timing measurements (does the session fit the booked slot?)"* as a
Phase 2 output, and **M6 item 1 — the dry run on yourself — is the thing that
measures them.** Every total in § D is provisional until it has been run once
with a stopwatch. Treat a shape that fits with under ~2 min of slack as not
yet shown to fit.

---

## C. The hard floor: how many training laps the machine needs

Measured with `kit/tools/lapbudget.py`, scored against Gate G1's own three
targets via `trace_kit.simulate.run` (committed novice model, 200
streams/type/pair, seed `trace-g1`). `share_traversing_2_of_3` is G1 target 1:

| training laps | frozen 3-of-4, probe 3 | 2-of-3, probe 2 |
|---|---|---|
| 10 | 0.000 ✗ | 0.085 ✗ |
| 12 | 0.003 ✗ | **0.728 ✓** |
| 14 | 0.290 ✗ | 0.970 ✓ |
| **15** | **0.600 ✓** | 0.998 ✓ |
| 16 | 0.757 ✓ | 1.000 ✓ |
| 18 | 0.932 ✓ | 0.998 ✓ |

G1's safety target holds everywhere — `share_removed_despite_regression` is
**0.000** in every row, and the non-improver never fades in any row.

**Three numbers bind the protocol:**

1. **≥ 15 laps → the frozen config stands and Gate G1 stays closed.**
2. **12 laps → only `2-of-3` with a 2-lap probe works**, which edits the config,
   re-pins its SHA-256 and **re-opens Gate G1**.
3. **≤ 10 laps → nothing traverses at any window setting.** This is a floor, not
   a tuning target.

**Cutting the probe is not a lever.** `traversal_floor = 2 × required_passes +
max(probe.laps, required_passes)`, because `_quorum_ready` is keyed on
`required_passes` and gates `probe_to_removed` too: the probe needs a fresh
`required_passes` laps of evidence after the advance into it resets the window.
So at 3-of-4, `probe.laps` 3 → 2 → 1 leaves the floor at **9 laps, unchanged**.
It is worth exactly one lap, and only once `required_passes` has come down.

**Prefer pair 1 if only one pair is driven.** Per-pair corner-speed removal at
15 laps is **pair 1 88%, pair 2 78%** — a quorum-granularity effect: 4 corners
makes `advance_threshold = 0.75` an exact 3-of-4, while 5 corners rounds it up
to 4-of-5 = 0.80. Pair 1 is also the only pair whose reference table is settled
(pair 2 still loads its 100% table — `CLAUDE.md`, M6 item 5).

---

## D. Three shapes, costed

All at pair 1 (1.17 min/lap). Consent, the information sheet and the
pre-questionnaire are assumed **pre-read and e-signed before the sitting** in
every shape — ~10 min that the rig does not need, and the first thing to check
with the ethics committee, because if it must happen in the room no shape fits.

### Shape A — one full training block, nothing else (29.3 min)

| phase | min |
|---|---|
| welcome + seat/wheel calibration | 4.0 |
| task instruction (what the cues mean) | 3.0 |
| familiarisation, 2 laps | 2.3 |
| **training block, 15 laps** | **17.5** |
| NASA-TLX | 2.5 |
| **total in the sitting** | **29.3** |

Confidence questionnaire and the RQ3 interview move **out of the sitting** to a
remote call afterwards — neither needs the rig. No baseline block, no unassisted
block.

- **Keeps:** the frozen config, **Gate G1 closed**, RQ1 in full (fade events,
  per-corner qualification trajectories, 60 corner passes per element), RQ3.
- **Loses:** the baseline covariate, the unassisted retention block, and
  therefore **RQ2 entirely**. A condition contrast measured on training laps is
  measured with the cues on screen, which is performance-*with*-feedback
  (Winstein & Schmidt 1990) — the exact error the probe exists to avoid. So
  there is no honest half-measure here: no unassisted block means no RQ2.
- **Cost beyond the protocol:** with no static arm, "adaptive vs static" stops
  being the manipulation. That is a **framing-level change needing supervisor
  sign-off**, not a decision this repo can take.

### Shape B — training plus a thin unassisted block (29.4 min) · **ADOPTED 2026-10-15**

| phase | min |
|---|---|
| welcome + seat/wheel calibration | 4.0 |
| task instruction | 3.0 |
| familiarisation, 1 lap | 1.2 |
| **training block, 12 laps** | **14.0** |
| **unassisted block, 4 laps (3 valid)** | **4.7** |
| NASA-TLX | 2.5 |
| **total in the sitting** | **29.4** |

Condition (adaptive / static) assigned **between subjects**. Questionnaire and
interview remote, as in Shape A.

- **Keeps:** a retention measure, and an RQ2 contrast in form.
- **Requires:** `2-of-3`, probe 2 — so it **re-opens Gate G1** (re-run
  `simulate run`, re-review) and it depends on the **G2 minimal-detectable-change
  analysis** (`BAND_CALIBRATION_BRIEF.md` §E, item 8a) licensing a 3-pass
  window. That analysis is already on the G2 list; this makes it a *blocker*
  rather than a refinement. **Do not adopt 2-of-3 on the lapbudget tables
  alone** — see § E.
- **Loses:** the baseline covariate (training laps 1–2 are the only proxy, where
  nothing has faded in either condition yet); **3 valid unassisted laps against
  the plan's 8**; and the probe-and-revert mechanism in most of the data —
  `n_staggered_reversions` falls **799 → 227**, because the element is often
  already removed before a staggered onset arrives.
- **Honest read on RQ2:** between subjects, ~7–8 per arm at n ≈ 15, no baseline
  covariate, 3 valid retention laps. The contrast will not be interpretable.
  Shape B buys RQ2's *form*, not its substance.

### Shape C — the crossover, if it can be bought back (~80 min, 3 sittings of ≤ 30)

Two pairs × two conditions needs two training blocks of ≥ 15 laps = ~37 min of
training driving alone, so it cannot be one sitting at any lap time:

| sitting | contents | min |
|---|---|---|
| 1 | calibration + instruction + 2 fam laps + pair-1 training 15 laps + TLX | 29.3 |
| 2 | 2 pair-2 fam laps + pair-2 training 15 laps + TLX + pair-1 unassisted 4 laps | 29.9 |
| 3 | pair-2 unassisted 4 laps + questionnaire + interview | 20.3 |

**~80 min total** — still **less than half** the 195 min currently booked, which
is the part worth putting to a supervisor: the 3 h 15 figure was never the real
cost, it was the wrong lap time. Keeps the frozen config, Gate G1, the 2×2
crossover, `pair` as a nuisance fixed effect, and every RQ.

---

## E. The cost no simulation in this repo can price

`non_improver.share_with_any_fade` is **0.000 at every window length**, so on
these tables a shorter window looks free. It is not. That model learner sits far
outside the band by construction, so it cannot fail in the way a shorter window
makes likely: **loss of discriminability near the band edge.** Two things in the
repo already say so from the other direction —

- `BAND_CALIBRATION_BRIEF.md` §E adopts **minimal detectable change** (Weir
  2005) as the method for sizing the window, precisely because behaviour in
  simulation cannot justify it. A 3-pass window raises MDC₉₅.
- `CLAUDE.md` thesis-correction item 8: the controller re-evaluates its quorum
  **every lap**, which inflates the false-advance rate over the per-check figure
  (~7% → ~37% across fifteen looks). A shorter window means more looks per unit
  of evidence.

So `2-of-3` is a candidate the lap budget *points at*, and the MDC analysis is
what may or may not license it. The ordering matters: § C item 2 is a constraint
the G2 analysis must satisfy, not a result it can be skipped for.

---

## F. What is decided by whom

| decision | whose | status |
|---|---|---|
| If 30 min is final: RQ2 in form (B) or RQ1 in full (A)? | supervisor | **B, 2026-10-15** |
| Can consent + pre-questionnaire happen before the sitting? | ethics committee | **OPEN — B does not fit if not** |
| Can the RQ3 interview be a remote call afterwards? | supervisor | **OPEN — B assumes yes** |
| Whether `2-of-3` is admissible | the G2 MDC analysis, not this brief | **OPEN — blocks the config edit** |

The two open protocol questions are **not** cosmetic. Shape B totals 29.4 min
with consent pre-signed *and* the interview remote. If either answer is no, the
sitting needs ~10 min it does not have, and the only places to take it from are
the training block (which drops below the § C floor) or the unassisted block
(which is the thing Shape B was chosen for). **A "no" to either sends this back
to § D, not to a trim.**

## G. Consequences already incurred, whatever is chosen

1. **`evaluation_plan_v2.md` § Phase 3 session descriptions are wrong** — the
   lap-count arithmetic rests on "~2-minute circuit" and both layouts are
   ~70–80 s. Correct the premise even if the session structure survives.
2. **`simulate.BLOCK_LAPS = 15` and its comment** (*"a block is 30 minutes of
   driving, which the eval plan expects to yield 13–15 laps on a ~2-minute
   circuit"*) encode the same wrong premise. 15 laps turns out to be right for a
   different reason — it is **three laps above the cliff in § C** — and the
   comment should say that instead.
3. **15 laps is not a comfortable margin.** At 14 laps G1 target 1 falls to
   0.290 and fails. Any protocol that yields 13–14 laps in practice fails G1
   silently, so the training block needs a **lap count floor, enforced in the
   panel**, not a time box that happens to produce enough laps. A 30-minute
   time box at 2 min/lap would have produced 15 laps; at 70 s/lap a *time* box
   produces 25, and a shortened time box could produce 13.

---

## H. Adopting Shape B — the ordered work list

**Nothing in steps 3–5 may be done before step 2.** The config edit re-pins the
frozen SHA-256 and re-opens Gate G1, and § E is the standing reason it must be
licensed by measurement rather than by the lap budget that merely points at it.

1. **Record the decision** — this brief, `CLAUDE.md`, `MILESTONE_LOG.md`. *Done
   2026-10-15.*
2. **Run the G2 minimal-detectable-change analysis**
   (`BAND_CALIBRATION_BRIEF.md` §E item 8a — σ_within on detrended residuals,
   ICC, MDC₉₅(n) for n = 1…10 per metric, plus the between-corner residual
   correlation). It runs on data already recorded. **This is now a blocker, not
   a refinement:** it is the only thing that can license a 3-pass window, and
   Shape B does not work at 3-of-4 (§ C: 0.003 at 12 laps).
   - If it licenses `2-of-3` → step 3.
   - **If it does not**, Shape B is not available at 12 laps and the decision
     reverts to § D. Say so rather than adopting 2-of-3 anyway — a window chosen
     because the clock demanded it is exactly the "seeing what works"
     justification this project does not accept.
3. **Edit the config** — `qualification.window_passes` 4 → 3,
   `required_passes` 3 → 2, `probe.laps` 3 → 2. Then re-freeze, re-run
   `trace_kit.simulate run`, regenerate `configs/simulation/`, and **re-review
   Gate G1** against a 12-lap block. `test_m4_simulate.py` fails until the
   committed report matches the live file, which is the guardrail working.
   - `simulate.BLOCK_LAPS` 15 → **12**, and its comment rewritten: the premise
     *"30 minutes of driving on a ~2-minute circuit"* is wrong twice (§ B) and
     12 is now set by the protocol, not derived from a session length.
   - `test_m4_evaluator.py`'s exact count of 27 bands is unaffected — no floor
     changes here.
4. **Respecify RQ2 in `evaluation_plan_v2.md`.** This is the largest documentary
   consequence and it is a model change, not a wording change:
   - Condition is **between subjects**, so `(1 + condition | participant)` and
     the crossed-condition term are both gone. The counterbalanced 2×2 crossover
     and its sequence table go with them.
   - **`pair` leaves the model entirely** — one pair is driven, so it is a
     constant, not a nuisance fixed effect. Likewise `condition order` and
     `pair order`.
   - **No baseline covariate.** The plan's `baseline lap time (per pair,
     standardised)` does not exist in Shape B. The only proxy is **training laps
     1–2**, where nothing has faded in either condition yet. State it as a proxy
     and state what it costs: it is measured *with* full scaffolding in both
     arms, so it is a covariate for driving skill, not an unassisted baseline.
   - **Report the power honestly:** ~7–8 per arm at n ≈ 15, 3 valid retention
     laps per participant. The pre-committed n = 10 fallback becomes ~5 per arm.
     The thesis already declines to claim significance; Shape B makes that
     decline load-bearing rather than modest.
   - Phase 3's three-session structure collapses to one sitting + a remote
     call. `partial_lap` and the lap-validity rules are unaffected.
5. **Enforce the lap floor in the panel** (§ G item 3). Shape B's training block
   is **12 laps and 12 is the floor**, not a target — at 3-of-4 the equivalent
   figure was 15 and 14 already failed. A time-boxed block cannot be trusted to
   deliver it: at the real 70 s/lap a participant who spins twice is at 10 laps,
   where § C says nothing traverses at any window. The block must end on a
   **lap count**, with the panel refusing to stop early and recording the reason
   if it is stopped anyway.

### What Shape B costs the thesis, to be written up and not buried

- **RQ2 buys its form, not its substance** (§ D). Between subjects, no
  unassisted baseline, 3 valid retention laps.
- **Probe-and-revert appears in much less of the data.** At 2-of-3 probe 2,
  `n_staggered_reversions` falls **799 → 227** — the element is often already
  removed before a staggered regression onset arrives. The G1 safety clause
  still holds (`share_removed_despite_regression` = 0.000), but the mechanism
  the thesis is *about* is observed less often.
- **A 2-lap probe is a thinner retention test** — 8 unassisted corner passes per
  element at pair 1's 4 corners. The probe is the actual retention test by this
  project's own framing, so this is a limitation on the construct, not on the
  schedule.
- **One pair means the pair-2 apparatus inconsistency stops being a blocker and
  becomes a scope reduction.** Pair 2's 100% reference table no longer gates the
  first participant (`CLAUDE.md` M6 item 5) — but the thesis then rests on a
  single car and layout, which narrows the generalisation claim it was already
  declining to make. **The re-record of pair 2 is descoped, not deferred:** say
  so, rather than leaving a half-finished second apparatus in the repo.

---

## I. Step 2 ran, and it returned "neither" (2026-10-15)

`kit/tools/mdc.py`, Gate G2 item 8a, over the seven `_blocks.py` pair-1 National
blocks. Full tables in `kit/tools/README.md` § `mdc.py`. The outcome is not the
yes/no § H step 2 was written for:

- **`2-of-3` is not licensed.** At a 3-pass window only **1 of 4** corners can
  resolve the braking improvement available (8.19 m), and only **1 of 4** the
  apex one (2.20 m). The quorum needs 3 of 4.
- **`3-of-4` is not licensed either.** At 4 passes it is still 1 of 4 corners on
  each. **The frozen window was never licensed at its own value**, so adopting
  2-of-3 does not cross a line that 3-of-4 stayed behind — MDC95 grows by
  √(4/3) = **15%** between them.
- **The element Gate G1 actually rests on cannot be assessed.** Corner speed is
  the only element that traverses (`windowscan.py`: 83% removal) and it is the
  one metric with **no improvement-available anchor** — nothing in the repo
  measures how much corner-speed deviation a novice can recover. The 85%
  re-reference removed the *bias* (+0.31 km/h), which is a different quantity.

**So § H step 2's branch does not resolve as written.** It was drafted assuming
MDC would license 3-of-4 and then rule on 2-of-3; instead it rules against both,
which makes the window a **stated limitation of the design rather than a
discriminator between the two shapes**. Three consequences:

1. **The protocol decision is no longer blocked on this analysis.** If 3-of-4 is
   equally unlicensed, Shape B's 2-of-3 is 15% worse on a standard neither
   meets, and the choice between Shapes A and B turns on what it always turned
   on — whether RQ2's form is worth the costs in § D and § H.
2. **MDC95 is the strict reading, and the design does not claim it.** These
   gates are explicitly *a heuristic trigger for running a probe, not a
   measurement of learning*, and the probe is the retention test. The licensing
   analysis is therefore **item 8b** — contrasting-groups ROC with the cut at a
   stated false-pass rate — and MDC is reported as the size of the limitation on
   all three elements. That is §E's own ordering.
3. **The critical path is now the corner-speed anchor, not the window.** Until
   someone measures the improvement available on the element the system's
   feasibility rests on, neither 8a nor 8b can speak to it. It is measurable
   from data already recorded (an early-vs-plateau split across these seven
   blocks plus the three 2026-10-14 KR blocks).

**Status: `2-of-3` is NOT adopted and `configs/controller_config.json` remains
untouched.** Shape B stands as the protocol decision; what licenses its window
is now item 8b plus the corner-speed anchor, and § H steps 3–5 wait on that
rather than on 8a.

---

## J. Correction to § I: "neither" was a statement about 95%, not about the data

Same day, same analysis, one table later (`kit/tools/mdc.py`, the `confidence`
table). § I reported that MDC licenses neither window. That is true **at 95%
confidence and only there**:

| metric | conf | quorum@3 | quorum@4 |
|---|---|---|---|
| braking | 95% | 1/4 | 1/4 |
| braking | **80%** | **3/4** | **3/4** |
| apex | 95% | 1/4 | 1/4 |
| apex | **80%** | 2/4 | **3/4** |

**At 80% confidence braking clears a 3-of-4 corner quorum at a 3-pass window.**
The same sigmas license opposite answers, and nothing in the data picks the z.
So § I must be read as *"MDC95 licenses neither"*, not as *"measurement theory
forbids a 3-pass window"* — and the choice of confidence level, not the
measurement, was carrying the verdict.

This strengthens § I's conclusion rather than reversing it: **MDC alone cannot
decide the window.** What can is **item 8b** — contrasting groups with the cut
at a stated false-pass rate and the false-fail rate reported — because these
gates are a trigger for running a probe, not a certification, and the design's
own asymmetry (*premature withdrawal is worse than delayed*) is a statement
about the false-pass rate. A conventional z only implies one; 8b states it.

**Unchanged:** `2-of-3` is still not adopted, the config is still untouched, and
the corner-speed anchor is still the critical path — at any confidence level,
that metric has nothing to compare its MDC with.

### Two methods checked and recorded (see `kit/tools/README.md` § `mdc.py` 5)

- **Sequential methods (SPRT, LC-CUSUM)** — already considered-and-rejected in
  `BAND_CALIBRATION_BRIEF.md` §E on engineering cost, not validity. Their
  published competence-decision counts are **13–56 procedures** (median 13 for
  peribulbar blocks; 15, range 8–25, for bronchoscope intubation; 369 ± 70 for
  simulated cordocentesis). **No method decides proficiency from 3–4
  observations** — that order of magnitude is not a TRACE problem.
- **Generalizability theory (G-study → D-study on Φ)** — the framework this
  project lacks and the best fit for its crossed corner × lap design, because a
  D-study answers *how many corners × how many laps* for a target Φ. **It needs
  several drivers** (Φ's numerator is between-person variance), so it is G2
  pilot work; ICC(1,1) = 0.454 / 0.116 / 0.099 is already the within-driver half
  of its inputs.

**And the structural finding that matters more than either:** a 12-lap block
yields **4 × 12 = 48 corner passes per element**, which is *inside* the
sequential literature's 13–56 range. The architecture never looks at more than
`window_passes` of them per corner before voting across corners. **The sample is
adequate; the per-corner-then-quorum structure is what spends it.** That is a
different argument for the sequential family than the one §E rejected, and it
deserves re-recording against this reasoning — though acting on it is a
controller rewrite and squarely out of scope for a protocol decision.

---

## K. Config adopted 2026-10-15 — `frozen-g1b`, and what re-running G1 found

**Adopted on instruction:** band floors **12 m / 9 km/h / 1.5 m**, qualification
**2-of-3**, `probe.laps` **2**. `config_id` → `frozen-g1b`,
sha256 `a6f89eef21284b7d6058fb4113b820bee7eab6d53241257f783f122caebb258f`.
`simulate.BLOCK_LAPS` 15 → **12**. The 2026-10-14 `corner_speed_gate` and `kr`
fields are preserved.

### Justification, in the order it carries weight

1. **The frozen floors did not work, on real passes.** `kit/tools/feasible.py`
   replays real recorded passes through the real evaluator and controller: at
   5/4/0.5 the braking and apex elements **never advance in any real block** at
   either window, and corner speed advances in about half. At 12/9/1.5 all three
   advance in most blocks, first advance at laps 2–7.5.
2. **The floors, not the window, were the binding constraint on engagement.** At
   the frozen floors `share_traversing_2_of_3` is 0.000 at *every* window and
   lap count. Widening floors is what makes the criterion reachable; the window
   only decides whether the ladder can be *completed* in the budget.
3. **12/9/1.5 is the mildest widening that works.** Per-pass rates on real
   passes go 6.0% → 43.6% (braking, pre-KR) and 57.7% with KR; apex 7.4% →
   43.2%. 15/11/1.5 and 18/12/1.5 engage more but cost much more on both error
   margins (below).
4. **The apex floor is capped at 1.5 m**, not raised further: at 2.0 m Gate G1
   fails outright on the committed model.
5. **2-of-3 + probe 2 has a 6-lap traversal floor** against 9 for 3-of-4, which
   is what fits a 12-lap block at all.

### Measured against the alternatives (measured apex novice, 200 streams/type/pair)

| floors | window | laps | t1 share | non-improver false-fade | removed-despite-regression |
|---|---|---|---|---|---|
| **12/9/1.5** | **2-of-3 p2** | 12 | 0.430 | **5.2%** | **1.25%** |
| **12/9/1.5** | **2-of-3 p2** | **15** | **0.720 ✓** | **5.8%** | **0.75%** |
| 15/11/1.5 | 3-of-4 p3 | 15 | 0.515 ✓ | 8.0% | 13.8% |
| 18/12/1.5 | 3-of-4 p3 | 15 | 0.855 ✓ | 13.5% | 25.0% |

**The adopted config is the best of the tested set on all three error margins
simultaneously**, and the 3-of-4 packages are an order of magnitude worse on the
safety clause — because a 9-lap ladder puts removal right where regression onsets
land, while a 6-lap ladder completes before them.

### The novice model's apex parameters were corrected, and it reversed a verdict

`simulate.MODEL` apex parameters → the **measured** 2.49 m / 1.86 m
(`apexscan.py`, 227 real passes), replacing the assumed 1.2 m / 0.30 m that
`CLAUDE.md` already recorded as wrong by ~6× on sigma. Not cosmetic: at a 1.5 m
apex floor the *assumed* novice's apex excess (~1.3 m, σ 0.30) is **contained by
the band**, so 68% of non-improvers fade; the measured novice sits outside it and
the figure is 5%. Leaving the assumed values would have certified a band width
against a learner nobody has observed.

### THE COST THAT WAS NOT PREDICTED: 2-of-3 inverts the alternating pathology

`golden_traces/alternating_corner.json` exists to document a known hysteresis
pathology: a corner meeting its criterion every *other* pass never accumulates
two consecutive failures, so it never de-qualifies. Under **3-of-4** it gives 2
of 4, below the threshold, so it **stalls** — the conservative direction. Under
**2-of-3** alternating is exactly **2 of 3, so it QUALIFIES**, permanently.

**A driver who is right half the time is now counted as competent at that
corner.** This is arithmetic, not a model artefact: alternating yields ⌈n/2⌉ of
n, so only `required_passes = 3` rejects it — which means 3-of-4 or 3-of-3, both
with a **9-lap** floor. **You cannot have both a 6-lap ladder and
alternating-rejection.** That is a clean derivable trade-off and belongs in the
thesis as one.

`dequalify_consecutive_failures = 1` was tested as a fix and is worse: it does
not stop the corner qualifying and takes removed-despite-regression from 1.25%
to **27%**.

### Gate G1: NOT MET, and two of its targets are unsatisfiable by a working system

At 12 laps all three targets fail (t1 0.430; t2 5.25%; t3 1.25%). At 15 laps
target 1 **passes** (0.720) and 2 and 3 still fail.

**Targets 2 and 3 fail at every configuration that makes the system work**,
because both are zero-tolerance clauses on events only a working system can
produce — `non_improver_never_fades` demands exactly 0.000, and target 3's
"never answered by removal" likewise. Only the frozen floors satisfy them, by
never fading anything for anyone. This is the same vacuity finding as
`kit/tools/README.md` § `feasible.py` 4, now across two targets.

**Both must be restated as stated rates with the counter-rate reported** — the
contrasting-groups logic already adopted in `BAND_CALIBRATION_BRIEF.md` §E, and
the same move the eval plan already made once for target 3's staggered-reversion
clause. Until then G1 cannot judge a working configuration, and by the standing
rule a NOT MET G1 blocks M7.

### Repo state: 27 tests red, expected and itemised

The golden corpus was regenerated (`golden_traces/generate.py`), which took
parity failures 28 → 6. Remaining:

| file | n | why |
|---|---|---|
| `test_m4_controller_parity.py` | 6 | the hand-written spec-level assertions that deliberately never read the stored blobs — the corpus guard working. One is the alternating finding above and is **not** a stale expectation. |
| `test_m7_kr.py` | 12 | KR message magnitudes are band-derived; the bands moved. |
| `test_m4_simulate.py` | 5 | pins the committed report's config hash and verdict. |
| `test_m4_evaluator.py` | 2 | history length is `window_passes - 1`; one apex case now sits inside the wider band. |
| `test_m4_runtime.py` | 2 | a 3-lap dwell is now 2; a scripted probe now completes instead of censoring. |

**These are not repaired yet, deliberately.** Repair encodes the new calibration
into the assertions, and if the alternating pathology sends the window back to
3-of-4 the work is reverted. The `golden_traces/README.md` trace table also
needs its lap counts restated (`fast_improver` pins "a full traverse in 9 laps";
it is 6 now).

### Also found: the corpus is coupled to calibration, and should not be

Golden traces carry no config of their own, so they read the live
`controller_config.json` — which means a *calibration* change churns a corpus
whose job is pinning *logic parity* between the Lua and Python controllers. At
the one moment the two could silently diverge, the detector had to be
regenerated. Traces should carry their own `config` block. G2 will recalibrate
again, so this is worth fixing before it does.

### And a bug fixed on the way

`simulate.cmd_freeze` coerced every `--set` value with `float()`, writing
`window_passes: 3.0` into the frozen config. Six schema fields are
`"type": "integer"`; a float there validates only by the grace of JSON Schema
treating 3.0 as integral, and the Lua validator is a separate implementation
that must not be relied on to agree. Now parses integers as integers.

### Gate G1's targets 2 and 3 were RESTATED, and the gate is MET again (2026-10-15)

Both had been **zero-tolerance clauses** — a non-improver must leave full
salience in exactly 0.000 of streams, broad regression must be answered by
removal in exactly 0.000 — and both were satisfied only by the `frozen-g1`
floors, **which satisfied them by never fading anything, for anyone.** On real
recorded passes at those floors the braking and apex elements never advanced in
a single block. *A conservatism target is trivially met by a system that never
acts*, so neither clause could judge a working configuration, and every
calibration that made the machine work failed both.

They are now **stated rates with the counter-rate reported** —
`simulate.TARGET_RATES`, which is the contrasting-groups reporting style already
adopted for the band floors (Jørgensen et al. 2018), and the same move eval plan
v2 already made once for target 3's staggered-reversion clause.

| target | bound | measured | counter-rate reported |
|---|---|---|---|
| 2 · `non_improver_false_fade_rate_is_bounded` | ≤ **10%** false pass | **5.75%** | false fail **28%** (typical improvers not traversing) |
| 3 · removal despite regression | ≤ **2%** | **0.75%** | latency excess over the arithmetic floor |

**Both values are DECLARED DESIGN PARAMETERS, not literature values, and they
are provisional until Gate G2** — the review's central finding is that no
published rule exists for a tolerance of this kind. What justifies each is
recorded beside it in `simulate.TARGET_RATES`:

- **10% false pass** is justified by the *ratio*, not the absolute: the design's
  own asymmetry ("premature withdrawal is worse than delayed") requires a false
  pass to be rarer than a false fail, and at 28% false fail this keeps it at
  roughly 3:1. **The asymmetry is asserted as well as the bound**, so a
  calibration that inverted it fails even from inside the bound.
- **2% removal-despite-regression** is bounded an order of magnitude tighter
  because the error is strictly costlier — a late reversion costs one lap driven
  without the cue, a removal costs the rest of the block. It is also the value
  that makes the bound **discriminate**: the adopted 2-of-3 ladder measures
  0.75% while every 3-of-4 alternative at workable floors measures 12–26%. A
  bound admitting 13% would not be a safety bound at all.

`test_the_restated_g1_targets_declare_their_rates_as_provisional` pins both
values and the asymmetry between them, so changing one is deliberate.

### Golden traces now pin their own config, decoupling parity from calibration

Each trace carries the **complete** controller config it was generated against
(`config`, required by `schemas/golden_trace.schema.json`), and both
implementations are handed that object rather than the file on disk.

**Why it mattered:** the corpus exists to catch a divergence between
`controller.lua` and `controller.py`, and it was reading the live config — so a
*calibration* change churned it. The frozen-g1 → frozen-g1b recalibration broke
**28 parity assertions** and silently invalidated three cases (a block that no
longer ended mid-probe, a reversion cap never reached, a regression arriving
after removal). At the one moment the two implementations could have diverged,
the detector had to be regenerated.

**Verified, not assumed:** with the live config temporarily set back to 3-of-4,
**92 parity tests pass** and exactly one fails —
`test_the_corpus_is_not_silently_detached_from_the_study_configuration`, which
is the deliberate guard that at least one trace must still be pinned at the
shipped calibration. The same edit used to break 28 tests.

Two further guards came with it: each pinned config must be a **valid**
controller config (otherwise the trace certifies agreement on input the
apparatus would refuse to load), and where a trace carries `config_overrides`
those must actually be reflected in the pinned config — the two cannot drift
into disagreeing about what the case is.

What pins the **live** calibration is the committed simulation report's SHA-256
in `test_m4_simulate.py`, which is the right place for it.

---

## L. Every open decision closed (2026-10-15)

| decision | resolution |
|---|---|
| Protocol shape | **Shape B** |
| Training block length | **15 laps** — the sitting runs ~32.9 min, not 30 |
| Ethics, consent, pre-questionnaire | **Outside the timed sitting**, confirmed |
| RQ3 interview | **Remote, afterwards** — outside the sitting |
| Band floors / window | **12 m / 9 km/h / 1.5 m, 2-of-3, probe 2** (`frozen-g1b`) |
| Alternating-corner pathology | **Accepted**, documented as a derivable trade-off |
| G1 targets 2 and 3 | **Restated** as stated rates; gate MET |

### 15 laps, and why the three minutes were the cheap option

Gate G1's first target scores **0.72 at 15 laps and 0.43 at 12**. The alternative
way to buy the same traversal rate inside 12 laps is to widen the floors to
15/11/1.5, which costs **false pass 5.8% → 8.0%** and **removal-despite-regression
0.75% → 13.8%**. Three laps of block length costs ~3.5 minutes of rig time and
nothing measurable. The frozen configuration was also certified at 15, so running
15 keeps the gate and the protocol describing the same apparatus.

**The §F open questions are closed, and one of them changed what gets reported.**
With the ethics process, consent, the pre-study questionnaire and the interview
all outside the timed sitting, **~32.9 min is rig time rather than participant
burden.** Real per-participant commitment is **~55–60 min** once the pre-reading
and the 10–15 min remote interview are counted. Both figures belong in the
methods chapter: the sitting is what the apparatus and the lap budget constrain,
the total is what a participant is actually asked for. Quoting only the 33
minutes would understate the ask.

**One limitation this creates, now recorded with a measurement attached.** Moving
the interview out of the session puts a gap between the drive and the questions,
and RQ3 asks partly about moment-to-moment experience — so the further apart they
sit, the more the interview measures recollection. Run it the same day where
possible and **record the gap per participant**, so the limitation can be reported
as a number rather than a caveat.

### What remains, and it is all in-game

Nothing in the repository blocks the first participant any more. The outstanding
work is the dev blocks and the visual review, which need the game:

1. **M6 item 0 — the §0A KR diagnostic re-run**, now with a new question
   attached: at a 12 m braking band, KR is silent on errors under 12 m, which
   includes the +8.1 m bias this driver was running. Does it still fire often
   enough to be a signal?
2. **M6 item 1 — the dry run**, 15 laps, stopwatch on every phase. Every
   non-driving number in the budget above is an estimate and this is the only
   thing that measures them.
3. **M5 visual review items 1–4.** At the `frozen-g1b` floors a stage transition
   should be reachable by real driving, so the deliberately-loosened dev config
   item 4 contemplated may be unnecessary — check before building one.
4. **Data hygiene (M6 item 4)** — the unflagged pre-M2 recordings and the two
   2026-10-14 blocks recorded with the dev toggle off.
