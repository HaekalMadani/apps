# TRACE — Tolerance-band calibration: literature basis and limitations

**Version:** v1.0 · **Date:** 2026-10-14 · **Scope:** EVM, per-metric floors, 0.5 consistency ratio, 3-of-4 window, one-/two-sided gates
**Status of this document:** research memo, not thesis text. Section E is written to be lifted into the thesis. Section C.0 is new analysis on your own figures and is labelled as such.

## How verification is labelled

| Label | Meaning |
|---|---|
| **FT** | I read the full text (or the methods section) myself in this session |
| **ABS** | Abstract, publisher record or repository record only |
| **SEC** | Reported by a named secondary source that cites it; I did not see the primary |
| **MEM** | From my background knowledge; not re-fetched this session. Treat as a lead to verify, not a citation |
| **UNVERIFIED** | A specific number or claim I could not see in any accessible source |

Flags follow your convention: **[VERIFY]** = check before citing; **[CONFIRM]** = design decision that is yours to make.

---

## A. Direct answer (≤200 words)

No. There is no published, principled rule for setting bandwidth/tolerance widths for novices. In bandwidth-KR research the width is almost always a fixed percentage of the movement goal, typically 5%, 10%, 15% or 20%. It is justified by convention ("same as previous studies") rather than derivation. Studies that varied width as an independent variable contradict one another. In driving, the one recurring value (0.5 m from lane centre) is a design choice I could not trace to any calibration.

What *does* exist are general methods for drawing a pass/fail line on a noisy performance measure, mostly from medical-simulation and measurement science:

- **Contrasting-groups standard setting.** A cut-score placed between novice and proficient distributions, with false-pass/false-fail rates reported.
- **Expert-referenced proficiency criteria.** A criterion set from human expert performance, met on consecutive trials.
- **Minimal detectable change (MDC).** The smallest change distinguishable from measurement noise.
- **Sequential tests (LC-CUSUM / SPRT).** Tests that decide "learned" after accumulating evidence across trials.

None is specific to driving. Together they give you a defensible procedure.

On your apex numbers, the conclusion is not quite "no band works". **No *per-pass* criterion works.** A criterion on an aggregate of about 6–8 passes, or a sequential test, separates improvers from non-improvers in principle (Section C.0).

---

## B. Precedent table

### B.1 Bandwidth KR (laboratory motor learning)

| Study | Task | Pop. | Band (units / proportional form) | Justification given | Width as IV? Result | Verif. |
|---|---|---|---|---|---|---|
| Sherwood (1988). *Effect of bandwidth knowledge of results on movement consistency.* Percept. Mot. Skills 66(2):535–542. doi:10.2466/pms.1988.66.2.535 | Rapid timed limb movement | Students | 0%, 5%, 10% **of goal movement time** | **UNVERIFIED** (full text not accessed) | Yes: wider (10%) → more consistent (lower VE) | SEC (Ugrinowitsch et al. 2018, below); width values SEC |
| Lee & Carnahan (1990). *Bandwidth KR and motor learning: more than just a relative frequency effect.* QJEP 42A(4):777–789. doi:10.1080/14640749008401249 | Timing task | Students | Goal-centred % bands; exact values **UNVERIFIED** | **UNVERIFIED** | Yoked-frequency controls; BW effect > frequency effect, mainly consistency | ABS |
| Lee, White & Carnahan (1990). *On the role of KR in motor learning: exploring the guidance hypothesis.* J. Mot. Behav. 22(2):191–208. doi:10.1080/00222895.1990.10735510 | Timing | Students | 5% vs 10% (SEC) | **UNVERIFIED** | Wider → more consistent (SEC) | ABS + SEC |
| Lee & Maraj (1994). *Effects of bandwidth goals and bandwidth KR on motor learning.* RQES 65(3):244–249. doi:10.1080/02701367.1994.10607625 | Timing | Students | Specific vs bandwidth KR × specific vs bandwidth goal; secondary says 5% narrow band was most accurate | **UNVERIFIED** | BW KR helps regardless of goal type | ABS + SEC |
| Cauraugh, Chen & Radlo (1993). *Effects of traditional and reversed bandwidth KR on motor learning.* RQES 64(4):413–417. doi:10.1080/02701367.1993.10607594 | Timing, 60 trials | n=48 | Traditional (KR outside band) vs **reversed** (KR inside band); width **UNVERIFIED** | **UNVERIFIED** | Both BW groups beat yoked controls in retention | ABS |
| Goodwin & Meeuwsen (1995). *Using bandwidth KR to alter relative frequencies during motor skill acquisition.* RQES 66(2):99–104 | Golf putting | Students | Expanding (0→20%) vs contracting (20→0%) vs fixed bands: **values UNVERIFIED** (only a non-academic coaching page paraphrases them) | **UNVERIFIED** | Width *schedule* manipulated | SEC (weak) |
| Butler, Reeve & Fischman (1996). *Effects of the instructional set in the bandwidth feedback paradigm.* RQES 67(3):355–359 | — | — | Secondary: narrow 5% most accurate | **UNVERIFIED** | Instruction about the band manipulated | SEC |
| Lai & Shea (1999). *Bandwidth KR enhances generalized motor program learning.* RQES 70(1):79–83 | Keypress sequence, relative timing | Students | 10% or 15% of goal. **Secondary sources disagree on which** [VERIFY] | **UNVERIFIED** | Wider better for relative-timing learning (SEC) | SEC |
| Chen (2002). *Catching the learner doing right versus doing wrong: effects of bandwidth KR orientations and tolerance range sizes.* J. Hum. Mov. Stud. 42(2):141–154 | — | — | **Tolerance range size is an explicit IV**; secondary: 15% gave most consistency | **UNVERIFIED** | Yes | SEC — **read this one in full** |
| Colen & Zubiaur (2008/2010). *Effects of different bandwidths KR on the acquisition of a serial motor skill.* Eur. J. Hum. Mov. 21:87–98 | Serial ball-placement timing | n=45 | 0%, 5%, 10% **of total time** | Not stated in abstract | Yes: **no differences between widths** | ABS |
| Junqueira et al. (2015). *Thin bandwidth KR improves performance consistency.* Am. J. Sports Sci. 3(6):115–119. doi:10.11648/j.ajss.20150306.13 | Keypress timing | — | 5% vs 20% vs increasing 5→20% vs decreasing 20→5% | — | Yes: **narrow (5%) more consistent**, i.e. the opposite of Sherwood | ABS |
| Cruz et al. (2018). *Bandwidth KR persists on motor skills acquisition.* Motricidade 14(2–3):107–114. doi:10.6063/motricidade.14294 | Keypress, 850 ms, relative timing | n=22 | 15% of goal, applied to **relative error** | "This percentage is the same observed in previous studies" (copied from Lai & Shea; Ugrinowitsch et al. 2010) | No (15% vs 0%). BW improved relative-timing consistency up to 1 week | **FT** |
| Ugrinowitsch, Cruz & Ugrinowitsch (2018). *Bandwidth feedback increases performance consistency of motor skills.* ConScientiae Saúde 17(2):155–163. doi:10.5585/ConsSaude.v17n2.8029 | Keypress, 900 ms | n=30 | 15% of goal | Adopted "to allow comparison with existing studies" (paraphrased from Portuguese) | No. Their review: 5%/10% best in some studies, 15% in others; **width effect "remains to be investigated"**; future work should relate width to learner skill level | **FT** |
| **Ishikura (2009).** *The effects of KR by bandwidth method on acquisition of timing skill: validity of the bandwidth method based on the stability of performance.* Doshisha J. Health Sports Sci. 1:39–44. doi:10.14988/pa.2017.0000011621 | Mouse timing, 1200 ms | n=52 | **Band = SD of the learner's own preceding 5 trials** ("fluctuating range"), vs yoked fixed band and yoked fluctuating band | Designed to track performance stability | Yes: **SD-based band beat both yoked controls on total variability**, but was only equal to 100% KR. Author calls for more testing | ABS (JP+EN) |
| **Yabuki et al. (2022).** *Effectiveness of adjusted bandwidth KR in motor learning.* Cogent Psychology 9(1). doi:10.1080/23311908.2022.2131039 | Grip-force adjustment | n=47 | Narrow vs wide vs **adjusted** (individualised) | States that previous BW studies did not set width from individual performance | Yes: adjusted < wide on VE in immediate retention ("partially" supported) | ABS; adjustment rule **UNVERIFIED** |
| Agethen & Krause (2016). *Effects of bandwidth feedback on the automatization of an arm movement sequence.* Hum. Mov. Sci. 45:71–83. doi:10.1016/j.humov.2015.11.005 | Arm sequence, 5 sessions | — | **Performance-adaptive bandwidth**. Lab page: tuned to give equal positive/negative feedback | — | — | ABS / lab page; rule **UNVERIFIED** |
| Winstein & Schmidt (1990). *Reduced frequency of KR enhances motor skill learning.* JEP:LMC 16(4):677–691 | Lever trajectory | — | Not a bandwidth study: faded **frequency** schedule | — | — | MEM / SEC |

**What this establishes:**

1. Width is conventionally a **percentage of the target value** (a timing goal). It is not a fraction of baseline error, and not a multiple of expert SD.
2. The numbers are inherited, not derived. Cruz et al. 2018 and Ugrinowitsch et al. 2018 say so explicitly (FT).
3. Width-as-IV studies conflict. Sherwood and Lee et al. favour wider bands; Junqueira 2015 and Lee & Maraj 1994 favour narrower; Colen & Zubiaur found no difference. The 2018 Ugrinowitsch review calls it open.
4. The only "learner-SD" scaling precedents are **Ishikura (2009)** (band = SD of last 5 trials) and **Yabuki et al. (2022)**, plus Agethen & Krause's adaptive band. All are small, lightly replicated, and none is in a continuous-control task.

> **Caveat that matters for TRACE.** These bands are *feedback* bands. They decide when to *give KR*, not when to *withdraw a scaffold*. Using them as a mastery/withdrawal criterion is an analogy, and the thesis should say so. Bandwidth-KR theory itself assumes that errors inside the band are partly **motor noise the learner cannot correct** (Cruz et al. 2018, FT, citing Winstein & Schmidt 1990). That premise supports making the band at least as wide as the noise, which is the opposite of your 0.5 m apex floor.

### B.2 Driving / vehicle control / training tolerances

| Study | Task | Pop. | Tolerance | Justification | Verif. |
|---|---|---|---|---|---|
| de Groot, de Winter, López García, Mulder & Wieringa (2011). *The effect of concurrent bandwidth feedback on learning the lane-keeping task in a driving simulator.* Human Factors 53(1):50–62 | Lane keeping, 5 × 8 min | Unlicensed novices | Seat vibration when > **0.5 m from lane centre** (via Petermeijer 2015 secondary) | **UNVERIFIED** | ABS + SEC. Result: off-target > on-target feedback |
| van Leeuwen, de Groot, Happee & de Winter (2011). *Effects of concurrent continuous visual feedback on learning the lane keeping task.* Proc. Driving Assessment 6:482–488. doi:10.17077/drivingassessment.1436 | Lane keeping | n=30 students | **No band**: continuous compensatory display | n/a | ABS. Gain vanished in retention; guidance-hypothesis support |
| Petermeijer, Abbink & de Winter (2015). *Should drivers be operating within an automation-free bandwidth?* Human Factors 57(1):5–20. doi:10.1177/0018720814563602 | Haptic steering guidance | n=32 | Guidance outside a **0.5 m** band; hysteresis variant re-centres once triggered | Full text blocked; justification **UNVERIFIED** | ABS. Note the **hysteresis** variant: precedent for asymmetric enter/exit rules |
| Marchal-Crespo & Reinkensmeyer (2008). *Haptic guidance can enhance motor learning of a steering task.* J. Mot. Behav. 40(6):545–557. doi:10.3200/JMBR.40.6.545-557 | Robotic steering wheel | Young adults | "Guidance-as-needed": firmness adapted online from ongoing error. Deadband value **UNVERIFIED** | Algorithmic | ABS |
| Marchal-Crespo, McHughen, Cramer & Reinkensmeyer (2010). Exp. Brain Res. 201:209–220. doi:10.1007/s00221-009-2026-8 | Same | Young + old | Same controller | — | ABS. Guidance helps **less-skilled** people most |
| **Bugeja, Spina & Buhagiar (2017).** *Telemetry-based optimisation for user training in racing simulators.* VS-Games 2017, pp. 31–38 (IEEE) | Racing sim (Silverstone), auditory suggestions | n=27, 2 groups | Heuristic rules: braking too hard/too light, braking in corner (binary), divergence from racing line in a corner section, oversteer, gear. **No tolerance values visible** | Paper describes "a system of heuristics" | ABS + text fragments (ResearchGate). Full text restricted (UM OAR: "Restricted Access") |
| FAA Airman Certification Standards, Private Pilot (FAA-S-ACS-6), Area V Task A, steep turns | Flight maneuver | Applicants | Altitude **±100 ft**, airspeed **±10 kt**, bank ±5°, rollout heading ±10° | Regulatory/expert consensus; no empirical derivation published with it | SEC (multiple flight-school reproductions of the ACS text) |

**Bugeja et al. (2017): the claim does not hold up on accessible evidence. [VERIFY before keeping it]**

- The abstract and repository record describe a **heuristic** rule system. None of the accessible text mentions slip ratio, empirically set tolerances, or how thresholds were chosen.
- The visible fragments describe **two feedback tiers**: racing-line feedback first, advanced feedback once the user "masters the racing line". The mastery rule itself is not visible.
- The headline result is that improvement **dissipated when feedback was removed**. That is a guidance-hypothesis (dependency) finding. It is not evidence for a working fade-and-revert scheme.
- **Recommendation:**
  - Cite Bugeja et al. for "a telemetry heuristic feedback system for sim racing, whose gains did not survive feedback removal".
  - Do **not** cite it for empirically set tolerances unless you obtain the full text. Use UM OAR "Request a copy" on handle 123456789/106531, or the 2016 B.Sc. dissertation, handle 123456789/14720.
  - Your memory file has Bugeja as the "load-bearing precedent for probe-and-revert". Check that use too. The two-tier switch may support "staged feedback", but nothing visible supports *revert*.

### B.3 Expert-referenced and standard-setting precedents (medical simulation)

| Study | Method | Criterion | Verif. |
|---|---|---|---|
| Gallagher et al. (2004). *Discriminative validity of MIST-VR using criteria levels based on expert performance.* Surg. Endosc. 18(4):660–665. doi:10.1007/s00464-003-8176-z | Experienced surgeons (n=12) as benchmark | Criterion = **2 SD from the expert mean**; 7–27% of student scores fell outside it after 3 trials | ABS |
| Gallagher et al. (2005). *Virtual reality simulation for the operating room: proficiency-based training as a paradigm shift.* Ann. Surg. 241(2):364–372 | Review | Trainees must reach an objective proficiency criterion **and perform at it consistently** | ABS |
| Ahlberg et al. (2007). Am. J. Surg. 193(6):797–804. doi:10.1016/j.amjsurg.2006.06.050 | RCT, proficiency-based VR | Train until predefined expert level reached | ABS |
| Larsen et al. (2009). BMJ 338:b1802 | RCT | Expert criterion reached in **two consecutive** sessions | SEC (fragment) |
| Jørgensen, Konge & Subhi (2018). *Contrasting groups' standard setting for consequences analysis in validity studies.* Adv. Simul. 3:5. doi:10.1186/s41077-018-0064-7 | Cut-score at intersection of novice and expert distributions | Report **theoretical** false-pass/false-fail from fitted distributions, not only observed counts, because groups are small | ABS + figure captions |
| Biau et al. (2008). *Quantitative and individualized assessment of the learning curve using LC-CUSUM.* Br. J. Surg. 95(7):925–929 | Sequential test that starts from "not learned" and signals when performance reaches a predefined acceptable level | Used for continuous outcomes too: two LC-CUSUMs run simultaneously (navigated TKR) | ABS |
| Biau & Porcher (2010). *A method for monitoring a process from an out of control to an in control state: application to the learning curve.* Stat. Med. 29 [pages VERIFY] | Statistical derivation of LC-CUSUM | — | SEC |

---

## C. Candidate calibration methods for TRACE

### C.0 New analysis on your apex figures (labelled: my computation, not literature)

The model uses σ = 1.86 m within-driver per-pass SD and Δ = 2.2 m improvement start→plateau. Per-pass excess is assumed i.i.d. normal around a mean that is either flat (non-improver) or decays by Δ with τ = 3 laps (improver). Script: `disc.py` (available on request).

| Quantity | Value |
|---|---|
| Single-pass effect size d = Δ/σ | **1.18** |
| Best symmetric error, single pass, midpoint threshold | **28%** each way |
| Same, mean of n passes | n=4: 12% · n=6: 7% · n=8: 5% |
| MDC₉₅ = 1.96·√2·σ/√n | n=1: 5.2 m · n=4: 2.6 m · n=6: **2.1 m** · n=8: 1.8 m |
| n for MDC₉₅ ≤ Δ | **≥ 6 passes** (5.5) |
| n for α = β = 0.05, midpoint cut, fixed window | **8** passes |
| SPRT expected sample size (α = β = 0.05, known σ, simple hypotheses) | **≈ 3.8 passes** on average |

**Your current 3-of-4 rule on one corner over 15 laps.** The threshold *c* is in metres below the non-improver's mean.

| Rule | Non-improver *ever* qualifies | Non-improver qualified at lap 15 | Improver qualified at lap 15 |
|---|---|---|---|
| 3-of-4, c = 0.5 | **67%** | 23% | 90% |
| 3-of-4, c = 1.1 (midpoint) | 37% | 10% | 78% |
| 3-of-4, c = 1.9 | 9% | 2% | 50% |
| mean of 6, c = 1.5 | 12% | 2% | 80% |
| mean of 8, c = 1.5 | **4%** | 1% | **83%** |

**Three interpretive points. Please check these against your own simulation before accepting them.**

1. **A single 3-of-4 evaluation is not the weak point. Repeated looks are.**
   - One 3-of-4 check at the midpoint false-passes a non-improver only 7% of the time.
   - Re-evaluated every lap, the probability of *ever* qualifying climbs to 37%.
   - This is the classic sequential-testing (multiple-looks) inflation. It is very likely what your Monte-Carlo is detecting, more than the band width itself. [VERIFY against `sim-spec.md`]
2. **The dichotomise-then-vote rule throws information away.** A window *mean* (or median) of the continuous metric dominates "≥3 of 4 binary passes" at the same window length. The mean-of-8 row beats every 3-of-4 row on both error types.
3. **Corner quorum hides or creates the problem depending on correlation.**
   - With *independent* corners, the ≥75% quorum almost never fades a non-improver in my model: 0.00 for K = 6 and K = 10.
   - That your simulation *does* fade one means its synthetic novice has strongly **correlated** errors across corners (a lap-level or driver-level factor), or that its band is wider than my c.
   - Real data probably are correlated. Estimate the between-corner correlation of per-pass apex excess from your 227 passes. It determines whether the quorum adds protection. [VERIFY]

**Measurement caveats on the inputs:**

- **σ = 1.86 m.** If it was computed across laps *during learning*, it contains the learning trend and overstates noise. Recompute it on detrended residuals or on plateau laps only. [VERIFY]
- **Skew.** Mean excess 2.49 m vs median 1.52 m means a heavy right tail (excursions). Use a **window median** or log-transformed RMS. Normal-theory numbers above are then approximations.
- **Δ = 2.2 m** is a group figure. Individual Δ varies, so some learners will have Δ < σ and remain undetectable at any practical n.

### C.1 Ranked methods

#### Rank 1: Contrasting-groups / expert-referenced cut-score on an aggregated metric (best supported)

- **Citations:** Jørgensen et al. 2018; Gallagher et al. 2004, 2005. Standard-setting practice in simulation-based assessment.
- **What to measure:**
  1. Per-corner, per-pass metrics for a *novice-start* group (laps 1–2 of each novice).
  2. The same for a *proficient* group. Ideally 3–5 competent **human** drivers on the same car/track, 8–12 laps each.
  3. If you cannot recruit humans, the *plateau* laps of your fastest-converging novices are a weak proxy, which you must declare.
- **How to apply:** Fit the two distributions of the **window statistic** (median of n passes), not the single pass. Place the cut where theoretical false-pass ≤ your conservatism target (e.g. ≤5%). Report false-fail.
- **Likely outcome:**
  - Braking: a narrow band works. Your 10.6 m → 2.4 m convergence implies d ≫ 3 at n = 3.
  - Corner speed: probably fine. [VERIFY with per-pass SD]
  - Apex: a cut near the midpoint of the start/plateau distributions at n ≈ 6–8. In absolute terms roughly 1–1.5 m below start-level excess, not 0.5 m.

#### Rank 2: MDC / SEM to set the minimum window length

- **Citations** (MEM; standard, verify page numbers):
  - Weir JP (2005). *Quantifying test–retest reliability using the ICC and the SEM.* J. Strength Cond. Res. 19(1):231–240.
  - Hopkins WG (2000). *Measures of reliability in sports medicine and science.* Sports Med. 30(1):1–15.
  - Haley SM & Fragala-Pinkham MA (2006). *Interpreting change scores of tests and measures used in physical therapy.* Phys. Ther. 86(5):735–743.
- **What to measure:** ICC and SEM of each metric on plateau laps. Repeated passes of the same corner by the same driver give a two-way random-effects ICC.
- **What it gives:** the n at which MDC drops below the change you need to detect (n ≥ 6 for apex). It replaces "3-of-4 because it behaved" with "n = 6 because MDC₉₅(6) < Δ". It does not set the threshold itself.

#### Rank 3: Sequential decision (LC-CUSUM or SPRT) in place of window voting

- **Citations:**
  - Biau et al. 2008 and Biau & Porcher 2010 (LC-CUSUM, including continuous outcomes).
  - Wald's SPRT. Sequential mastery testing in psychometrics is a further lead (MEM: Eggen 1999, Appl. Psych. Meas.; Vos 2000). [VERIFY]
- **What it gives:**
  - Principled control of the multiple-looks false-pass rate (point 1 of C.0). Expected decision time is ~4 passes in the ideal case.
  - Re-qualification and regression detection map naturally onto a standard CUSUM run after the LC-CUSUM signals. That is your restore-on-regression rule with a statistical basis.
- **What you need:** acceptable and unacceptable performance levels, which come from Rank 1, plus σ.
- **Cost:** more machinery in the CSP Lua runtime. Parity tests need to cover it.

#### Rank 4: EWMA mastery score (ITS precedent)

- **Citation:** Pelánek & Řihák (2017), *Experimental analysis of mastery learning criteria*, UMAP '17, pp. 156–163, doi:10.1145/3079628.3079667; extended in New Rev. Hypermedia Multimedia 24(3):133–159 (2018), doi:10.1080/13614568.2018.1476596 (ABS).
- **Findings:**
  - Threshold and data choice matter more than the learner model.
  - A simple exponential moving average is a suitable mastery criterion.
- **Related:** N-consecutive-correct conventions in ITSs (Kelly et al. 2015, EDM; ABS via Matayoshi). BKT's p(L) ≥ 0.95 convention (Corbett & Anderson 1995; MEM).
- **Fit:** an EWMA on the continuous metric is cheap and Lua-friendly. It inherits the multiple-looks issue unless its threshold is calibrated by simulation for a target false-pass rate. Calibration here is legitimate: you are calibrating a *decision rule* against a stated error rate, not tuning until the machine behaves.

#### Rank 5: Learner-SD bandwidth (Ishikura 2009; Yabuki et al. 2022)

- **Status:** the only direct "k × learner's own SD" precedent. Small, unreplicated, timing/force tasks.
- **Use:** possibly for the **braking consistency sub-criterion** (your 0.5 × band of rolling mean). Not as a mastery threshold.

#### Rank 6: EVM (AI σ × 3) (not supportable as specified)

- **No precedent found** for inflating an artificial reference's variance by a fixed multiplier.
- **Nearest neighbours:**
  - Fitts-law **effective width**, W_e = 4.133·σ of *human* endpoints (MEM: MacKenzie 1992; Soukoreff & MacKenzie 2004, IJHCS 61:751–789). This scales tolerance to measured human spread, not to a model's.
  - TRACK (Çangırılı & Kurt, arXiv:2610.10061, preprint, FT). Normalises human metrics *as ratios* to an RL agent. Explicitly excludes dispersion metrics from that normalisation, and notes that a ranking does not supply a recommendation threshold.
  - Cohen & Sternad (2009, Exp. Brain Res. 193:69–83) supports the premise that noise persists, not any value.
- **Operational problem.** With σ_ref ≈ 0.02 m, 3·σ_ref = 0.06 m ≪ 0.5 m floor. The same holds for braking and speed. **The EVM currently changes no decision.** The thesis should not present it as a mechanism doing work.

---

## D. Recommendation

1. **Reframe the parameters.**
   - Bands become *cut-scores on a window statistic*, set by contrasting groups (Rank 1).
   - Window length is set by MDC (Rank 2).
   - Re-evaluation every lap is controlled by a sequential rule or a simulation-calibrated EWMA (Ranks 3/4).
   - Retire the EVM from the AI path. Keep the field, defaulting to the human-reference path [CONFIRM], so `controller_config.json` stays backward compatible. State that floors were the operative parameters in all reported runs.
2. **Analysis 1 on existing data (no new collection): reliability and MDC per metric.**
   - Mixed model: per-pass metric ~ lap (or exponential learning term) + (1 | driver) + (1 | corner).
   - Take the residual SD as σ_within, and compute ICC.
   - Compute MDC₉₅(n) for n = 1…10 for braking, corner speed and apex.
   - Also compute the between-corner residual correlation within a lap, to settle the quorum question.
   - **Output:** a table with one row per metric giving σ_within, ICC, MDC₉₅(4), MDC₉₅(6) and MDC₉₅(8). This replaces the 3-of-4 justification.
3. **Analysis 2 on existing data: contrasting-groups ROC on the window statistic.**
   - Groups: early laps (1–2) vs each driver's plateau laps (detrended).
   - For window sizes n ∈ {1, 4, 6, 8}, plot ROC and AUC.
   - Choose the cut at ≤5% theoretical false-pass (Jørgensen et al. 2018 reporting style). Report false-fail.
   - If AUC for apex at n = 8 is still < ~0.8, that is your empirical evidence for the limitation in E.
4. **If you can collect anything new:** 3–5 competent human drivers × 10 laps. This gives a human proficient group for Rank 1, and makes the "expert" a human with motor noise rather than an AI with none.

---

## E. Limitation paragraph (draft for the thesis)

> The tolerance bands in TRACE are modelled on bandwidth knowledge of results, but that literature offers no principled rule for setting band width. Bandwidths are conventionally fixed percentages of the movement goal (typically 5–20%), adopted for comparability with earlier studies rather than derived (e.g., Cruz et al., 2018; Ugrinowitsch et al., 2018), and studies manipulating width have produced conflicting results. Individualised bands based on the learner's own variability have been proposed (Ishikura, 2009; Yabuki et al., 2022) but remain sparsely tested and were developed for feedback delivery, not for scaffold withdrawal. We therefore treat band setting as a standard-setting problem: thresholds were placed between the distributions of early-practice and plateau performance using the contrasting-groups method (Jørgensen et al., 2018), and decision windows were sized so that the minimal detectable change of the windowed statistic falls below the observed learning effect (Weir, 2005). Because the expert reference is a game AI with negligible lap-to-lap variability, its dispersion could not inform tolerance width; the per-metric floors were the operative parameters, and the variance multiplier originally specified had no effect on any reported decision. For the apex element specifically, within-driver pass-to-pass variability (SD ≈ 1.9 m) is of the same order as the total improvement observed from first lap to plateau (≈ 2.2 m). A criterion applied to individual passes therefore cannot separate improving from non-improving learners at an acceptable error rate (≈ 28% misclassification at the best single-pass threshold under a normal approximation); separation requires aggregating approximately six to eight passes per corner, which delays apex-scaffold withdrawal by a corresponding number of laps. Apex-scaffold fading decisions should accordingly be interpreted as conservative and slow by design, and the apex results as characterising the measurement limits of lateral-line accuracy in short novice sessions rather than as evidence about the timing of learners' line acquisition.

Fill in the AUC/MDC numbers from D.2–D.3 before using it. The 28% and 6–8 figures are from C.0's normal approximation.

---

## F. Reading list (read in full)

1. **Jørgensen, Konge & Subhi (2018)**, Adv. Simul. 3:5. The method you should adopt, and how to report false-pass/false-fail with small groups. Open access.
2. **Pelánek & Řihák (2018)**, New Rev. Hypermedia Multimedia 24(3):133–159. Mastery-criterion design, including threshold choice by simulation and the EWMA argument.
3. **Biau et al. (2008)**, Br. J. Surg. 95:925–929, plus **Biau & Porcher (2010)**, Stat. Med. Sequential "has this learner reached proficiency?" with a controlled error rate.
4. **Weir (2005)**, J. Strength Cond. Res. 19(1):231–240. ICC/SEM/MDC computations you will cite for window length.
5. **Chen (2002)**, J. Hum. Mov. Stud. 42:141–154. The one bandwidth study whose title names tolerance range size as an IV. You need its actual numbers.
6. **Ishikura (2009)**, Doshisha J. Health Sports Sci. 1:39–44 (open access, Japanese). The only learner-SD band precedent. You can read the Japanese original.
7. **Ugrinowitsch, Cruz & Ugrinowitsch (2018)**, ConScientiae Saúde 17(2):155–163 (open). The most explicit statement that width is conventional and unresolved. Useful to quote.
8. **Petermeijer, Abbink & de Winter (2015)**, Human Factors 57(1):5–20 (green OA via TUM mediaTUM). Check how the 0.5 m band was justified, and use the hysteresis variant as precedent for asymmetric enter/exit.
9. **Bugeja, Spina & Buhagiar (2017)**, VS-Games, via UM OAR request. Mandatory before you keep citing it for tolerances or probe-and-revert.
10. **Gallagher et al. (2004)**, Surg. Endosc. 18:660–665. The simplest published expert-referenced criterion ("2 SD from expert mean") and a template for a human-expert replacement for the EVM.

---

## G. One-sided vs two-sided gates (Q6)

**Literature status: thin.**

- I found no bandwidth-KR study with a one-sided band.
- Cauraugh et al. (1993) reverses *which side of the band gets feedback* (inside vs outside). It does not make the band asymmetric.

The defensible framing comes from equivalence and non-inferiority testing (MEM, standard):

- **Braking is an equivalence criterion.** Both early and late braking cost time, so the gate is two-sided. The analogue is TOST (Schuirmann 1987, J. Pharmacokinet. Biopharm. 15:657–680; Lakens 2017, SPPS 8:355–362).
- **Corner speed is a non-inferiority criterion.** Carrying more minimum speed than the reference is not a deficit, so the gate is "≥ reference − margin" (FDA 2016, *Non-Inferiority Clinical Trials to Establish Effectiveness*).
  - Caveat [CONFIRM]: excess speed that causes a wide exit or a track-limits violation *is* an error. A one-sided speed gate should be paired with the apex/line gate, or with an exit-speed check, so that "too fast" does not pass silently.
- **Apex RMS is one-sided by construction, not by design.** RMS is a non-negative magnitude, so "≤ expert RMS + band" is the only meaningful direction.
  - Don't present it as a design choice parallel to corner speed.
  - The real issue is that RMS discards **direction** (tight vs wide). A signed mean lateral offset in the apex window would be two-sided and may be more stable, since signed means average out symmetric noise. **Untested; no published reliability found.**

## H. Line-metric discriminability (Q5)

**Literature status: thin.**

- **SDLP** (standard deviation of lateral position) is the only lateral metric with published test–retest reliability. Correlations are ~0.7–0.86 over months (Iowa Driving Assessment proceedings; Verster & Roth 2011, Int. J. Gen. Med.; ABS). That is lane keeping over minutes, not a ±20 m apex window.
- **van Leeuwen et al. (2017)**, PLoS ONE 12:e0186871, doi:10.1371/journal.pone.0186871. Racing drivers showed a "more optimal racing line" than non-racers. The metric definition and its reliability could not be accessed (PMC blocked). [VERIFY: dataset is public at 4TU, doi:10.4121/uuid:9ab22c4c-1c68-4838-a752-e4ba4ddeec07]
- **TRACK** (arXiv 2610.10061, **preprint**, FT). Finds that in Assetto Corsa telemetry:
  - roughly 3/5–2/3 of lap-time variance is *within* session;
  - braking and strategy metrics were not repeatable across cars;
  - apex speed was the most repeatable metric.
  
  This is weak (n ≈ 13 drivers, unpublished) but domain-matched. It points the same way as your data: speed-type metrics are more stable than position-type metrics.

I found **no published evidence** that DTW distance, area-between-curves, curvature or steering-based line metrics are more reliable trial-to-trial than windowed RMS.

Two candidates worth testing on your telemetry, my suggestion only:

1. **Exit speed, or time lost through the corner sector vs reference.** This integrates line quality into an outcome that is closer to speed-type metrics.
2. **Signed mean offset** (G above).

Compute their ICC and MDC alongside RMS in Analysis 1 (D.2). That is a cheap, publishable comparison.

---

## Sources (accessed this session)

- Cruz et al. 2018 (FT): https://revistas.rcaap.pt/motricidade/article/download/14294/12582/50097
- Ugrinowitsch et al. 2018 (FT): https://www.redalyc.org/journal/929/92957928007/92957928007.pdf
- Ishikura 2009 (ABS): https://doshisha.repo.nii.ac.jp/records/20487
- Yabuki et al. 2022 (ABS): https://doaj.org/article/c2045bc4dcab4c19845556aceefa2cbf
- Colen & Zubiaur (ABS): https://doaj.org/article/d300202d7a124c1fb4cd1c21ab8fe963
- Junqueira et al. 2015 (ABS): https://lida.sport-iat.de/ta/Record/4038273
- Lee & Carnahan 1990 (ABS): https://experts.mcmaster.ca/scholarly-works/1313886
- Cauraugh et al. 1993 (ABS): https://www.bisp-surf.de/Record/PU199401069456
- Bugeja et al. 2017 record: https://www.um.edu.mt/library/oar/handle/123456789/106531 · fragments: https://www.researchgate.net/publication/318679405
- Petermeijer et al. 2015 (ABS): https://research.tudelft.nl/en/publications/should-drivers-be-operating-within-an-automation-free-bandwidth-e
- van Leeuwen et al. 2011 (ABS): https://pubs.lib.uiowa.edu/driving/article/id/28636/
- Marchal-Crespo & Reinkensmeyer 2008 (ABS): https://boris.unibe.ch/117034
- Jørgensen et al. 2018 (ABS): https://pmc.ncbi.nlm.nih.gov/articles/PMC5845294
- Gallagher et al. 2004 (ABS): https://interniche.org/en/studies/discriminative-validity-minimally-invasive-surgical-trainer-virtual-reality-mist-vr-using-cr
- LC-CUSUM (ABS): https://boneandjoint.org.uk/Article/10.1302/0301-620X.91BSUPP_I.0910045a
- Pelánek & Řihák (ABS): https://is.muni.cz/publication/1448676
- TRACK preprint (FT): https://arxiv.org/pdf/2610.10061
- Cohen & Sternad 2009 (ABS): https://pmc.ncbi.nlm.nih.gov/articles/PMC2756422
- FAA ACS tolerances (SEC): https://www.cfinotebook.net/lesson-plans/private-pilot-airplane/performance-and-ground-reference-maneuvers/private-pilot-airplane-steep-turns-lesson-plan
