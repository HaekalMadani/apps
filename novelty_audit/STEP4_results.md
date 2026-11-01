# Step 4 — narrow search on C3: results

**Date:** 2026-10-30 · **Protocol:** `STEP4_protocol.md` (fixed before searching) ·
**Form:** rapid review, one screener (Claude), no second reviewer ·
**Raw logs:**
- `logs/step4_log.txt` (OpenAlex + Semantic Scholar)
- `logs/step4_log_s2.txt` (Semantic Scholar retry)
- `logs/step4_citechase.txt` (forward citations)

**Naming used throughout (author, 2026-10-30):** the measured quantity is the
**probe-failure excess**; **guidance dependency** is its interpretation.

---

## Verdicts

| Claim | Verdict | Why |
|---|---|---|
| **C3:** interpreting post-withdrawal outcomes against a learning-plus-noise null with no guidance dependency | **SURVIVES: not found** in OpenAlex, partial Semantic Scholar, or web, across 8 query families plus citation chasing. No H grade. | Closest work either (a) prices a *decision's* false-positive rate under a null, without touching what happens after withdrawal; or (b) corrects selection at a mastery cutoff by design (RDD), not with a null; or (c) uses simulated learners that all learn, as ground truth |
| **C-lite:** a published fade rule's false-withdrawal rate under a never-improving simulated learner | **PRE-EMPTED for tutoring systems (Ye et al. 2016, read in full); survives only as a narrow application** | Ye et al. calibrate learning-detection rules by "generating responses for **perpetual non-learners**" so that the "chance of detection prior to learning is equal to .01". They do this for CUSUM, Shiryaev, Shiryaev–Roberts **and the ad hoc M-in-a-row heuristic** (ASSISTments' rule), and compare them at matched false-detection rates. LC-CUSUM (Biau et al. 2008, read) sets its limit from simulated ARL₀. Sims et al. 2013 simulate 10,000-trainee cohorts for type I/II rates. What survives: the same exercise for **HCI / motor adaptive-guidance fade rules** (Hsieh, Shen) on continuous metrics with a cross-corner quorum. **Recommendation: drop C-lite as a contribution claim.** If it is run at all, run it as positioning, citing Ye 2016 as the method |
| **C3-cal:** calibrating the null on cue-off laps, not cue-on laps | **SURVIVES (nothing on point)**, and the council's worry is **supported** | Postural-control work reports that concurrent feedback *reduces* variability during acquisition, with the effect absent at retention. So a σ fitted on cue-on laps is plausibly biased **low**, which makes the null fail too rarely and **inflates** the probe-failure excess. Calibrate on probe and unassisted laps |

### What this means for how C3 is stated

The Contrarian's warning holds **in part**. A reviewer from biostatistics will
recognise the move: a stated null, and an error rate under it. **The null as an
idea is not the novelty, and v9 must not imply that it is.** What nothing in the
search does is take the *outcome after support is withdrawn* (here, the probe)
and ask how much of the observed failure rate a learner with **no guidance
dependency, but with learning and lap-to-lap noise**, would produce under the
same selection rule. Sequential monitoring prices the decision; it never
interprets the post-withdrawal outcome. The ITS retention literature (ARRS,
ALEKS) observes post-mastery outcomes but corrects selection by design or not at
all, never with a simulated null.

So the surviving claim is:

> the first use of a calibrated learning-plus-noise null to attribute
> post-withdrawal (probe) failures in an adaptive guidance system, separating a
> **probe-failure excess**, read as guidance dependency, from regression to the
> mean under the system's own selection rule.

**Cite the LC-CUSUM / sequential-detection family as its methodological
ancestor.** That converts the Contrarian's objection into a lineage.

---

## Evidence table (graded per protocol)

**H:** none.

| Grade | Work | Year | Why it is not an H | Read scope |
|---|---|---|---|---|
| **P (C-lite)** | Biau, Williams, Schlup, Nizard & Porcher, *Quantitative and individualized assessment of the learning curve using LC-CUSUM*, Br J Surg 95:925–929, doi:10.1002/bjs.6056 | 2008 | **Read in full.** H0 is a stationary *unacceptable* failure rate (P0 = 0.175 vs P1 = 0.10); the limit h = 1.25 is chosen from **simulated ARL₀ = 74 / ARL₁ = 32**. It decides when competence is declared; nothing is withdrawn. **Key passage for C3:** after the signal at procedure 79, continued monitoring "would have gone over the lower boundary line for a few more procedures, indicating that performance had not reached the required level". The authors recommend a standard CUSUM afterwards (a "retention curve"). So the **post-decision dip is observed in the founding paper and never attributed against a null**. Cite it as C3's lineage and as a statement of its gap | full text |
| **P (C-lite)** | LC-CUSUM users, e.g. peribulbar block (Braz J Anesthesiol 2023, doi:10.1016/j.bjane.2023.11.003); hysteroscopy (Ginekol Pol 2017) | 2017–2023 | Set the h limit **by simulation** at stated type I/II errors (10% / 10%). The same idea as C-lite, applied to procedures | search snippets |
| **I/P (C-lite)** | Sims, Keltie, Burn & Robson, *Assessment of competency in clinical measurement: comparison of two forms of sequential test and sensitivity of test error rates to parameter choice*, Int J Qual Health Care 25(3):322–330, doi:10.1093/intqhc/mzt028 | 2013 | Simulated cohorts of 10,000 trainees. Type I = simulated competent trainees not certified; type II = simulated incompetent trainees certified. True error rates differ from nominal between R-SPRT and LC-CUSUM | abstract |
| **P (strong, C-lite)** | Ye, Fellouris, Culpepper & Douglas, *Sequential detection of learning in cognitive diagnosis*, BJMSP 69:139–158, doi:10.1111/bmsp.12065 | 2016 | **Read in full. The closest prior work to C-lite.** Thresholds calibrated on **simulated perpetual non-learners** to a .01 false-detection rate, including for the M-in-a-row heuristic. Frames the cost as an ITS that "may prematurely advance… if the outer loop falsely concludes learning has occurred". Decision-side only: no support withdrawn, no post-decision outcome interpreted, binary items. **Not a C3 hit** | full text |
| **I** | McNamee, Keraidi, McDonnell, Kelly, Wall, Darwish & Butler, *Learning curve analyses in spine surgery: a systematic simulation-based critique of methodologies*, Spine J 24:1789–1810, doi:10.1016/j.spinee.2024.05.014 | 2024 | **Read in full: not a C-lite pre-emption.** Every simulated surgeon *learns* (linear, log, exponential and quadratic descending curves plus N(0, 20) noise; binomial accuracy 0.85 → 0.95). It compares interval, regression and CUSUM methods **qualitatively** against the known curve. **No no-learning arm, no false-detection rate.** It does separate "tautological" CUSUM (deviation from the sample mean, which always peaks) from Biau's "rigorous" LC-CUSUM. A useful citation for why a stated null matters | full text |
| **P (weak, C-lite) / I (C3)** | Eyezo'o, M. H. B., *When Difficulty Adaptation Reshapes Mastery Dynamics: A Closed-Loop Simulation of Bayesian Knowledge Tracing in a Cameroonian Tutoring Prototype*, SSRN, doi:10.2139/ssrn.7578618 (single-author preprint, not peer reviewed) | 2026 | Open loop: learners at **fixed** success rates (no learning), 54 parameter settings × 300 runs; at 80% success the BKT estimate saturates near 1.0 in 90–98% of runs. Closed loop: a ZPD difficulty rule keeps the learner where the estimate fluctuates most. **A mastery estimator run on non-learners**, so it is adjacent to C-lite, but framed as an estimator mechanism with **no false-mastery rate**, no support withdrawn, and no post-decision outcome. Its closed-loop finding (the decision rule shapes the evidence it later reads) is the same selection logic C3 corrects for. Cite it as a recent neighbour | full text (extracted) |
| **I** | Matayoshi, Cosyn & Uzun, *Does Practice Make Perfect?…*, EDM 2022 short; and Matayoshi, Cosyn, Uzun & Kurd-Misto, *Using a Randomized Experiment to Compare Mastery Learning Thresholds*, JEDM 17(1) (2025) | 2022 / 2025 | Closest **selection-at-a-mastery-cutoff** work: a regression discontinuity at the threshold (2022), then a randomised A/B test of two thresholds (2025). Retention is the outcome. A design-based correction, not a null; no support withdrawn; RTM not named in either | abstract + page |
| **I** | Pelánek & Řihák | 2017 / 2018 | Simulated learning learners as ground truth; wMAD with premature mastery weighted 5×. Not a null (pass 2) | full text |
| **I** | Doroudi, *Mastery Learning Heuristics and Their Hidden Models*, AIED 2020, LNAI 12164:86–91, doi:10.1007/978-3-030-52240-7_16 | 2020 | **Read in full.** N-in-a-row is the optimal policy of a BKT model with **P(slip) = 0**; a simplified ALEKS heuristic is likewise model-based. Positioning: TRACE's 2-of-3 window tolerates one miss, i.e. it implicitly assumes a non-zero slip rate | full text |
| **I** | Käser & Alexandron, *Simulated Learners in Educational Technology: A Systematic Literature Review…*, IJAIED, doi:10.1007/s40593-023-00337-2 | 2023 | "Almost half of the studies using simulated learners do not provide any evidence that… the model [is] valid." **Cite it for v9 §7.3 step 5** (the null must reproduce observed cue-on statistics, or Δ is not reported) | abstract |
| **I** | Lin, Zheng, Shin, Liu & Oh, *CUSUM learning curves: what they can and can't tell us*, Surg Endosc, doi:10.1007/s00464-023-10252-1 | 2023 | The CUSUM "proficiency" peak is an artefact of how many cases are included. Empirical, no null | abstract |
| **I** | Linden, *Regression to the Mean-Adjusted Sample-Size Determination for Cutoff-Selected Single-Arm Pre-Post Studies*, arXiv 2609.27919 | 2026 | **Read in full.** One baseline cutoff, one follow-up, bivariate normal. No sequential or windowed selection, so it is the closed-form special case TRACE's simulated null generalises | full text |
| **I (not read)** | Goldenholz et al. 2023 (cited by Linden) | 2023 | *Simulated* RTM under eligibility cutoffs in clinical trials. Shows that simulating a no-effect null under a selection rule is **established trials practice**, which confirms C3's novelty is the application to post-withdrawal outcomes, not the device | cited only |
| **I** | Ahmadi Nadi, Steiner & Stevens, *Risk-Adjusted learning curve assessment using comparative probability metrics*, arXiv 2501.11637 / Stat Med 2026 | 2025 | Estimation instead of a threshold test; "expecting improvement over time" (weights recent outcomes). Background for the trend term | abstract |
| **I** | Sapountzi, PhD thesis (doi:10.5463/thesis.650); Sapountzi et al. EDM'21 (arXiv 2103.03766) | 2021 / 2024 | Bayesian stopping rules, including wheel-spinning learners | abstract |
| **I** | Noh, Chowdhary, Ooge, Aleven & Borchers, EDM '26 short, arXiv 2605.21613 | 2026 | Simulated learners (AFM + BKT) in closed-loop mastery; measures overpractice, not premature mastery. **Recent positioning** | abstract |
| **I (C1-adjacent)** | Hou et al., *Adaptive Scaffolding Needs Contingency…* (CoMeT), arXiv 2609.22993 | 2026 | An AI tutor fades on learner "take-up", with 131 adults. No probe, no null. Note for C1 | abstract |
| **I** | Pashler & Mozer, *When Does Fading Enhance Perceptual Category Learning?*, JEP:LMC | 2013 | Adaptive fading helped training performance, not the final test | snippet |
| **I (C3-cal)** | Concurrent feedback and postural variability (METU theses; Frontiers 2025, doi:10.3389/fpsyg.2025.1638827) | 2025 | Variability is lower *with* concurrent feedback during acquisition, which supports calibrating on cue-off laps | snippets |

## Search log

| Family | Sources | Result |
|---|---|---|
| Q1 simulated / null learners, mastery criteria | OA ×2, S2 ×1 (1 rate-limited), web ×2 | I only (Sapountzi, Ye, Noh) |
| Q2 RTM after threshold advancement / fading | OA ×2, S2 (rate-limited), web ×3 | **empty on point**; Matayoshi RDD (I) |
| Q3 simulated students for policy evaluation | OA ×1, citation chase | I (Käser & Alexandron, Doroudi) |
| Q4 sequential competence monitoring | OA ×2, web ×2, citation chase (Biau, 200 of 216 citers screened; the OpenAlex cursor returned 401 on page 2) | **P for C-lite** (LC-CUSUM family, R-SPRT); McNamee unread |
| Q5 motor guidance withdrawal / catch trials | OA ×2, web ×1 | **empty on point**: the guidance-hypothesis literature never models the post-withdrawal drop against a statistical null |
| Q6 JITAI / MRT and RTM | OA ×1, S2 ×1 (0 results) | empty |
| Q7 games assist removal, simulated players | OA ×1, web ×1 | empty; Debeauvais only. F1Laps (non-academic) notes a selection confound in assist use |
| Q8 support-on vs support-off variability | web ×1 | I (supports C3-cal) |
| Citation chase: Pelánek 2017 (28 citers), 2018 (18), Biau 2008 (200 / 216) | OpenAlex `cites:` | 7 + 2 + 20 kept on title regex; graded above |

**Coverage limits, stated:**
- Semantic Scholar returned HTTP 429 on **17 of 19** queries (only 2 returned results, neither on point). No API key was
  available, so S2 coverage is partial.
- OpenAlex relevance ranking was noisy, as in step 1.
- Scopus, WoS, PsycINFO, IEEE Xplore and ACM DL were not searched.
- Eneano 2026 is too new to have citers.
- The two items that were unread at first (McNamee 2024; SSRN 7578618) have since been read in full; neither changes a verdict.

**A clean C3 is "not found in these sources", not "does not exist."**

## Deviations from protocol

1. **S2 rate limiting.** I retried with 12 s spacing; still mostly 429. Recorded
   as partial coverage rather than replaced by another source.
2. **The Biau citation chase stopped at page 1** (200 of 216) after an OpenAlex
   401 on the cursor. Not retried.
3. **The Eneano citation chase was skipped**: preprint dated 2026-10, no citers.
4. **Grading of the LC-CUSUM P items** rests on secondary descriptions; the
   original was not re-read in this step. It is already cited in
   `BAND_CALIBRATION_BRIEF.md`.

## Owed to the author

- ~~Two PDFs~~ **Read 2026-10-30.** McNamee 2024 does not pre-empt C-lite (learning
  surgeons only, qualitative). Eyezo'o 2026 is a weak C-lite neighbour and a C3
  ingredient. **Neither changes a verdict.**
- **Optional, for a fuller step 4:** a Semantic Scholar API key, or a library
  Scopus run, on Q2 and Q5, the two families C3 most depends on.
