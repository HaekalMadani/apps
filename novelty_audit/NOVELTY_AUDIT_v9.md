# Novelty audit — thesis framing v9

**Date:** 2026-10-30 · **Scope:** step 1 (broad scan), not a systematic review ·
**Tool:** ARS `deep-research`, lit-review mode, run inline · **Status:** second pass
(full texts supplied by the author, `Academic Papers/`; extracted text in
`novelty_audit/papers_txt/`)

Evidence for the author, not chapter prose. A verdict says what v9's claim survives
as, **given what was read**. The read-scope column says how much of each source was
actually read. An abstract-level read can rule a claim *out*. It cannot rule it *in*.

**Date rule (author, 2026-10-30):** recent work (2022–2026) is preferred for
*positioning*. For *novelty threats* any date counts, and each work carries its year.
Pelánek & Řihák (2017/18) is therefore a threat to check against, **not** a paper to
build the thesis on. The recent positioning anchor for C2 is Zhang et al. (EDM 2025).

**Databases:** web search; OpenAlex API (`novelty_audit/tools/oa.py`); Crossref API (`novelty_audit/tools/cr.py`).
**Not searched:** Scopus, Web of Science, ACM DL native index, IEEE Xplore native
index. A claim that something does not exist must say this.

---

## What changed in pass 2

1. **C1 narrowed again.** The SSRN laparoscopy preprint (Eneano et al. 2026)
   *proposes* the same rule: advance one level only when common unaided probes meet
   criteria, and reinstate one level on deterioration. It also makes v9's circularity
   argument in almost the same words. It is an unimplemented proposal and not peer
   reviewed, but v9 can no longer say the *idea* is new.
2. **C3 holds after full-text reads.** None of the 12 Pelánek & Řihák scenarios is a
   no-learning learner. Their simulation is a ground-truth benchmark, not a null.
3. **C4 holds in its narrow form, and §2.4 is now supported.** Irwin 2019 tested
   reliability with t-tests and CV only (no ICC, SEM or MDC). TRACK says outright
   that within-day repeatability, its "first rung", was never implemented.
4. **F9 is reversed. Bugeja *does* describe empirically set tolerances.** The
   `[CORRECTED]` brackets in framing v6 §163 and eval plan L68/L136, and CLAUDE.md
   item 6, are wrong on this point (see Citation checks).
5. **Debeauvais 2014 is closer than the abstract suggested.** It has an observed
   rate of premature self-removal, broken down by assist, including the brake line.

---

## Verdicts

| Claim | v9 says | Verdict | Load-bearing threat |
|---|---|---|---|
| **C1** (F11, §3) | No system uses cue-off probe performance as the fading decision | **NARROWED (further)** | Eneano et al. 2026 *propose* probe-gated adaptive withdrawal with one-level reinstatement (laparoscopy, unimplemented). ASSISTments and ARRS implement unaided gating and retest-and-relearn (cognitive) |
| **C2** (RQ2, §2.3) | How often a guided rule fades prematurely has not been measured | **NARROWED** | Pelánek & Řihák 2017/18 (simulated ground truth); ARRS 1-week retention by mastery speed; Debeauvais 2014 observed self-removal "failures"; Zhang et al. 2025 |
| **C3** (§3, contribution 2) | Calibrated noise-only null separates dependency from regression to the mean | **SURVIVES step-4 narrow search (2026-10-30, `novelty_audit/STEP4_results.md`)**: not found in OpenAlex / partial S2 / web. The null *idea* is standard (LC-CUSUM type I error); the novelty is attributing **post-withdrawal** outcomes with a learning-plus-noise null. Measured quantity: **probe-failure excess**; interpretation: **guidance dependency** | No direct hit. Pelánek uses ground truth, not a null. TRACK calibrates *clustering* against a null. Linden 2026 gives a closed-form RTM correction (abstract only) |
| **C4** (RQ1, §2.4) | Within-session reliability of per-corner sim-racing metrics is unmeasured | **NARROWED, gap confirmed** | Irwin 2019: one corner, t-test plus CV, position CV > 50%. TRACK: cross-car and day-to-day repeatability measured, within-day **explicitly not** measured |
| **C5** (§2.2 table) | Four systems fade on guided performance | **MOSTLY VERIFIED** | Three checked in full text and confirmed (Hsieh, Shen, Li). Kinesthetic-CPR still abstract-level only |

### The surviving shape, stated as narrowly as the evidence allows

- **C1.** The **rule** is no longer novel as an idea: gating withdrawal on unaided
  probes, with one-level reinstatement, is proposed for laparoscopy (Eneano et al.
  2026) and implemented between sessions for cognitive skills (ARRS, 2012). What
  survives:
  - an **implemented, real-time** version for **concurrent visual cues in a
    continuous motor task**;
  - running **within one session**;
  - applied **per element**;
  - with the **null-calibrated reading of the probe outcome** (that part is C3).

  Cite Eneano et al. as the closest statement of the idea. v9 then claims the
  implementation and the measurement, not the idea.
- **C2.** Decision accuracy *has* been measured in four forms:
  - simulated ground truth (Pelánek);
  - delayed unaided retest (ARRS: 18–41% wrong on the first 1-week retest after a
    3-in-a-row mastery);
  - observed re-enabling after self-removal (Debeauvais: of the players whose
    removal "failed", 38–80% switched the assist back on after the very next race);
  - downstream lesson performance (Zhang et al. 2025).

  What survives: the rate for **system-initiated withdrawal of concurrent visual
  cues in a motor task**, and its **split into dependency vs. variability**. C2's
  novelty still rests on C3.
- **C3.** Unchanged and now checked in full text. No paper read applies a
  calibrated no-dependency (no-learning, no-change) null to a fading or mastery
  decision. The contribution is the **application and calibration**, not the idea
  of a null. **This remains the load-bearing novelty and the step-4 target.**
- **C4.** Within-session reliability in sim racing has been tested once (Irwin
  2019), but only on one corner, with a weak statistic (no significant mean
  difference, plus within-drive CV), and with a target-marker metric rather than a
  reference-relative one. TRACK names within-day repeatability as the unmeasured
  ceiling for its own analysis. What survives:
  - **per-element ICC / SEM / MDC across many corners**;
  - for **novices**;
  - for brake point, apex line RMS and minimum corner speed;
  - **with the practice trend removed** (detrended).

  v9 §2.4's TRACK sentence is now supported, so keep it.

---

## C1 — cue-off probe as the fading decision

| Work | Year | What it does | Bearing | Read scope |
|---|---|---|---|---|
| **Eneano, Chuwa, Olokpo, Omigbodun, Kolawole, Okpere & Oladapo**, *Feedback Withdrawal and Independent Competence in AI-Assisted Laparoscopic Surgical Training*, SSRN, doi:10.2139/ssrn.7571293 | 2026 | Narrative evidence synthesis plus a **proposed** 4-arm trial (continuous / scheduled / adaptive withdrawal / instructor). Adaptive arm: "advances by one level only when both common probes satisfy prespecified quality and error criteria… a predefined deterioration rule permits one level of reinstatement. Reinstatement takes priority over advancement." Two unaided probes after each of 4 blocks of 5 attempts. Also: "Performance measured during assistance may also determine whether that assistance is still needed, creating circular evidence of readiness." | **Closest statement of v9's rule and of its motivation.** Not implemented ("The design has not been implemented"), preprint not peer reviewed, between-block not real-time, one aggregate level not per element, **no null**. Its "bounded gap": no study shows adaptive withdrawal beats scheduled withdrawal with unaided assessment held constant | full text |
| ASSISTments Skill Builders | ongoing | Mastery = 3 consecutive correct on first attempt; a hint resets the streak | Unaided-only mastery decision | vendor page + teacher review |
| **Li, S.**, *Modeling Student Retention in an Environment with Delayed Testing*, MS thesis, WPI (ARRS) | 2013 | After a 3-in-a-row mastery, retests at 7/14/28/56 days; **a wrong answer triggers a relearning assignment, then a retest** | **Probe-and-revert gated on unaided performance**, cognitive, between sessions, deployed (6,292 students) | full text |
| Debeauvais, Zimmermann, Nagappan, Carter, Cooper, Greenawalt & Solberg, FDG | 2014 | Forza 4: logistic models predict whether a player is ready to disable an assist (Scenario 1), and whether a disable will stick given **one race driven without it** (Scenario 2) | Scenario 2 is a **post-removal-race readiness prediction**, offline and observational, on player-initiated removal. Not a controller | full text |
| Hsieh et al., CHI '26 | 2026 | Ghost opacity from EMA of guided score, clamped to [0.08, 0.8] | Confirms v9 §2.2 | full text (first 100k chars) |
| Shen et al., Cyber Racing Coach | 2025 | Assistance from the score of the current *assisted* trial | Confirms v9 §2.2 / §2.3 | full text |
| Li, Minto, Dölling, Boschetti & Zanotto, TNSRE 34 | 2026 | RL assist-as-needed. **12 catch trials per session (assistance and perturbation removed), excluded from the LMM, analysed separately on N = 6 subset**; controller not driven by them | **v9's "catch trials for analysis only" VERIFIED** | full text |
| Dong et al., Kinesthetic-CPR, UIST '26 | 2026 | "Predefined three-stage fading schedule" across training rounds (schedule, not performance). In Phase 2 the faded visual "reappears only when the system detects substantial degradation in average rate or depth", then fades again once stable. Unassisted tests only pre/post, outside the loop | **Schedule-based fade, with a performance-triggered reinstatement during cue-off practice**: a small revert-on-unaided-degradation precedent. No probe gates the fade | HTML full text, first 100k of 137k chars |
| Emken et al., JNER | 2007 | Catch trials as measurement | Consistent with v9 credit line | abstract |

## C2 — decision accuracy of mastery / removal rules

| Work | Year | Bearing | Read scope |
|---|---|---|---|
| **Zhang, Vanacore, Baker, Ch, Mills & Henkel**, *How Much Mastery is Enough Mastery?*, EDM '25 short | 2025 | Rori (Africa, WhatsApp math tutor). BKT P(Ln) at end of lesson N, in 8 buckets, vs performance on lesson N+1. 0.95 is still useful; ≥ 0.98 adds benefit. **Recent positioning anchor**: validates thresholds against *later* performance, not against an unaided probe or a null. *(Correction: authors are not Bosch et al.)* | full text (extracted) |
| Pelánek & Řihák, UMAP '17 / NRHM 24(3) | 2017 / 2018 | Mastery criteria (NCC, EMA, BKT, logistic) on 12 simulated scenarios with known mastery moment, scored by **wMAD (premature mastery weighted 5×)**. On real data: agreement and "score after mastery", with an explicit attrition-bias caveat | full text (both) |
| Pelánek, *Conceptual Issues in Mastery Criteria* | ~2018 | High guess and slip parameters cause premature mastery for all learners | full text (extracted) |
| ARRS (Li 2013, Table 3.1) | 2013 | 1-week unaided retention after 3-in-a-row mastery: **82%** (mastered in 3–4 attempts), **70%** (5–8), **59%** (> 8), **44%** (never mastered). The abstract says 55% for > 8; the table says 59% (inconsistent within the thesis) | full text |
| Debeauvais et al. | 2014 | Disable outcomes: **success / failure / yo-yo**. Of the players whose removal "failed", 38% (stability), 56% (clutch), 69% (autobrake) and **80% (brake line)** re-enabled the assist after the very next race. "Disabling an assist seems to be an immediate hit-or-miss." Model precision .61–.83 | full text |
| Kelly, Wang, Thompson et al., EDM '15 poster | 2015 | NCC vs knowledge tracing against a transfer item | snippets only; **not supplied** |
| Sapountzi et al., EDM '21 | 2021 | Bayesian stopping rules, simulation | abstract |
| Shen et al. | 2025 | Score plateaus ~85 under fading | full text |

## C3 — calibrated noise-only null

| Work | Year | Bearing | Read scope |
|---|---|---|---|
| Pelánek & Řihák 2017 / 2018 | 2017 / 2018 | **Not a null.** All 12 generators learn (BKT Pl 0.05–0.35; logistic Δ > 0). Simulation provides ground truth, so error is measured against the true mastery moment, not against a no-change baseline. Their "score after mastery" on real data has no counterfactual | full text |
| ARRS (Li 2013) | 2013 | The never-mastered group (44% at 1 week) is an informal empirical baseline for the mastered groups. Not a null model, and confounded with ability | full text |
| Çangırılı & Kurt, TRACK | 2026 | "We calibrate each clustering result against a null, and when one does not separate from chance, we say so." **A null-calibration habit in sim-racing telemetry, applied to clustering, not to a fade decision.** Cite as a methodological ally | full text |
| Linden, arXiv 2609.27919 | 2026 | Closed-form RTM for **one baseline cutoff, one follow-up**, under a bivariate-normal model. It is a sample-size tool (Stata `power onemean_rtm`). No sequential or repeated decisions, and no multiple measures. **Answer to "why not use it":** TRACE's selection is sequential (2-of-3 windows, re-evaluated every lap), quorum-gated across corners, and runs over a trending series, so no single-cutoff closed form applies. Cite it as the analytic special case the simulation generalises | abstract + metadata (full text not served) |
| Barnett et al. 2005 | 2005 | RTM background | not re-checked |

Empty: see the search log.

## C4 — reliability of sim-racing metrics

| Work | Year | Bearing | Read scope |
|---|---|---|---|
| Irwin, Mollica & Desbrow, IJES 12(6) | 2019 | n = 36 (20 fast subset), one session, four 5-lap drives (2 normal, 2 visual-impairment goggles), laps 2–5. **Reliability = no significant initial vs repeat difference (paired t), plus within-drive CV.** CV: lap time 1.5%, sector 3.1–3.6%, **position displacement at a corner-1 marker 52.7–58.6%**, speed there 5.9–7.6%. No ICC, SEM or MDC. Metric is distance to a painted marker, not to a reference line | full text |
| Irwin, Shum, Leveritt & Desbrow, Driving Assessment | 2013 | **Road driving, not racing** (lane keeping, TTC, reaction time, stop-light inhibition). n = 27; 3 drives (same day ×2, +7 days). ICC 0.69–0.92 for control measures; inhibition measures unreliable. Precedent for ICC-based simulator reliability, not for racing | full text |
| Çangırılı & Kurt, TRACK | 2026 | ACGym data, 13 drivers in restricted population. **Cross-car** repeatability: best metric mean apex speed, 0.53; median 0.04–0.07. Day-to-day identification rung too small to resolve. Conclusion: "**the first rung was never implemented. Within-day repeatability… was not measured**… it can be estimated… by splitting the laps within a single session. It is the cheapest of the requirements" | full text |
| Hojaji, Toth, Joyce, Murphy & Campbell, SSRN | 2025 | "Consistency" = **the same ML-identified KPIs across tracks** (Laguna Seca vs Brands Hatch; 135 participants, 1,180 laps). **Not test-retest reliability.** No threat to C4 | full text |
| Hojaji et al., CHB Reports 14 | 2024 | Lap-time-predictive metrics | bib only |

**v9 §2.4's TRACK sentence is SUPPORTED** (Conclusions, §6). The earlier flag is withdrawn.

---

## Citation checks (F9, F10, F12 and others)

| Item | Finding |
|---|---|
| **F9** Bugeja, Spina & Buhagiar 2017, VS-Games 31–38 | **REVERSED by the full text.** "The tolerance_f value changes as the user improves; through empirical observation it is initially set to 7%" (braking slip ratio, target 15% ± tolerance). The racing-line tolerance "is initially set to 10 metres, and is decreased as the user improves." Feedback is audio and **fires only when the driver is wrong**. Fixed schedule: feedback group off in session 4; gains dissipated (lap time Mann-Whitney p = .057 / .054 / **.029** / .539 across sessions 1–4). Built on **Assetto Corsa** via UDP. **So framing v6 §163's "tolerances… set by empirical observation" is correct.** The `[CORRECTED 2026-10-14]` brackets at v6 §163 and eval plan L68/L136, and CLAUDE.md "Thesis-document corrections" item 6, withdraw a claim the paper supports. They need reverting by the author. Still true: it neither fades nor reverts, and the tolerance-tightening rule is unspecified ("as the user improves"). |
| **F10** Nickl et al. 2024 | **VERIFIED.** Nickl, Sommerhoff, Radkowitsch, Huber, Bauer, Ufer, Plass & Seidel (2024). Effects of real-time adaptivity of scaffolding. *Learning and Instruction* 94, 101994. doi:10.1016/j.learninstruc.2024.101994. N = 245 pre-service teachers, three arms (none / non-adaptive / adaptive scaffolding from real-time NLP of text). **No significant benefit of adaptive over non-adaptive.** Proposes a scheme to validate adaptivity design decisions: **is the *source of adaptation* measured accurately**, and are the support mechanisms right? **Keep it.** It is the recent precedent for auditing the adaptation decision rather than only the learning outcome, which is RQ2's stance |
| F12 Salmoni 1984; Klasnja 2015 | ✓ (see pass 1) |
| Debeauvais et al. 2014 | **v9's "players repeatedly re-enable assists" is SUPPORTED** (yo-yo category, and the 38–80% next-race re-enable rates). Title: "…Forza Motorsport 4" in the PDF header |
| Dyer et al. 2017 | Venue wrong in v9: *Front. Neurosci.* 11:463 |
| RL-AAN (TNSRE) | Li et al. 2026, 34:532–542. **Catch-trial claim verified** |
| TRACK | Çangırılı & Kurt 2026, arXiv:2610.10061. "Missing first step" **verified** |
| EDM '25 short paper | **Zhang, J., Vanacore, K., Baker, R. S., Ch, N., Mills, C., & Henkel, O.** (2025). Not Bosch |
| ARRS | Li, S. (2013). *Modeling Student Retention in an Environment with Delayed Testing* (MS thesis). Worcester Polytechnic Institute. Advisor J. E. Beck |
| Eneano et al. 2026 | First author Grace A. Eneano. **Preprint, not peer reviewed.** Cite as such |

---

## Search log

Unchanged from pass 1. Raw OpenAlex output is in `novelty_audit/logs/oa_batch1.txt`.

**Returned nothing on point (recorded as empty):**
- `"catch trials" robot-assisted training assistance adaptation unassisted performance`
- `robot training interleaved unassisted assessment trials used to update assistance level assist-as-needed fading`
- `adaptive guidance VR training fade cue then test without cue restore if performance drops 2024 2025`: only Hsieh
- `adaptive training aviation simulator remove training aid when trainee meets criterion without aid adaptive aiding withdrawal study`
- `regression to the mean adaptive training threshold selection bias apparent performance drop after criterion reached`
- `"regression to the mean" intelligent tutoring system mastery OR "knowledge tracing" OR "adaptive learning"`
- OpenAlex `regression to the mean mastery learning` (57k hits, none on RTM)
- `Nickl 2024 guidance fading motor learning visual feedback`

**Full texts read in pass 2:**
- Eneano 2026
- Pelánek & Řihák 2017 and 2018
- Pelánek, *Conceptual Issues in Mastery Criteria*
- Zhang 2025
- Li 2013 (ARRS thesis)
- Debeauvais 2014
- Bugeja 2017
- Li et al. 2026 (TNSRE)
- TRACK 2026
- Irwin 2013 and 2019
- Hojaji 2025

**Not supplied / not read:**
- Kelly et al. 2015
- Kinesthetic-CPR full text
- Linden 2026 full text
- Salden et al. 2010
- Nickl 2024 source

**Not covered:** psychophysics staircases; Keller PSI / Bloom mastery tests.

## Step 4 (2026-10-30)

The narrow C3 search is done; full record in `novelty_audit/STEP4_results.md`.
- **C3:** survives, re-stated as post-withdrawal attribution. Cite LC-CUSUM and sequential detection as its ancestors.
- **C-lite:** pre-empted for tutoring systems by Ye et al. 2016 (non-learner-calibrated false-detection rates, including for M-in-a-row). Drop it as a contribution.
- **Lineage for C3:** Biau 2008 observes the post-signal dip and never attributes it against a null. Ye 2016 and LC-CUSUM price the decision only.
- **C3-cal:** calibrate on cue-off laps. The literature suggests cue-on σ is biased low.

## Follow-ups, in priority order

1. **Author: revert the F9 `[CORRECTED]` brackets.** They are at framing v6 §163 and
   eval plan L68/L136. Also update CLAUDE.md item 6. Bugeja supports the
   empirical-tolerance claim.
2. **Step 4 (narrow systematic search) on C3.** Use a stated protocol across Scopus,
   WoS, ACM and IEEE. Query families:
   - null / counterfactual / placebo *learner* for mastery or fading decisions;
   - RTM in adaptive training and stopping rules;
   - permutation calibration of adaptive-withdrawal decisions.

   Also check how Eneano et al. propose to calibrate their probe criteria ("in a
   separate pilot"). No null is mentioned.
3. **Linden 2026 full text.** It is free on arXiv, so I can fetch it myself. The
   question is whether its closed form applies to a sequential quorum rule.
4. **Kinesthetic-CPR full text** (arXiv, fetchable) to find the fade trigger.
5. **Step 2:** candidate directions from the gaps above.
