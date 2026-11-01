# Response to Reviewers, round 2 -> round 3

Responses to the round 2 verification report (`round2/verification_report.md`).
So far they cover R6, R8, R2 and NEW-2. NEW-1 awaits an author decision. The
number and wording fixes (NEW-3 to NEW-10) and the open should_fix items are
not yet done.

## R6 (interval procedure)

**Addressed 2026-11-01.** There is now one procedure, a nested participant
cluster bootstrap:
- the outer level resamples participants;
- the inner level gives each sampled participant one of M = 20
  parametric-bootstrap refits of their own null.

It is stated in §5, and §6 uses it. The design sensitivity in §6 is now the
nested procedure's (`kit/tools/nullinterval.py`). It was measured on the same
studies as the round 1 plug-in interval:
- it is ~5% wider;
- every verdict rate moves by ≤ 0.03;
- braking detection is 0.47 at Δ 0.24 and 0.75 at Δ 0.37, and false excess is
  0.015.

The round 1 figures were therefore not materially optimistic. The selection of
the fit window is still not resampled, and that is stated.

**Correction to our S20 response:** we attributed the near-margin 5–8%
false-"no excess" plateau to the interval's optimism. That attribution is
refuted. The plateau is within ~2 MC SE of nominal, plus percentile-bootstrap
undercoverage at 15 clusters. It has been corrected in §6 and in the
`nullyield.py` notes.

## R8 (time-profile rule)

**Addressed 2026-11-01** (`kit/tools/nullprofile.py`). The test and α are
stated: a one-sided t over participants, α = 0.05. The reading rule is fully
specified, including the case where both statistics are significant:
- sustained if L is significant;
- decaying if only T_p is;
- neither otherwise.

Transients of 2 and 3 laps were simulated. Under the old L (unassisted laps
2–4), a 2-lap braking transient was read as sustained in 76% of studies. L is
therefore changed, under a pre-stated rule:
- **braking:** L = unassisted laps 3–4, which misreads that transient at 0.05
  and detects a sustained 0.25-band deficit at 0.90;
- **corner speed:** L = the second probe lap.

The horizons (2 laps and 1 lap) are stated limits in §4, §7 and §8. The
block-to-probe link is stated as an explicit assumption, with L_p reported as
probe-level corroboration.

## R2 (recovery of the primary null)

**Addressed 2026-11-01** (`kit/tools/nullprimary.py`). The primary
full-salience null was recovery-tested under exponential and power-law truths,
with σ scaled 0.5× to 2×. Parameter recovery (σ̂/σ, and trend error on and
after the fit window) is reported.

The results are an honest negative:
- under an exponential truth, recovery holds to 5 m;
- under a **power-law truth it fails at the committed σ** (RMSE 0.051 against
  0.045);
- §5 and §8.4 are corrected.

"The highest level at which the null recovered" is removed.

## NEW-2 (σ gate)

**Addressed 2026-11-01** (`kit/tools/nullprimary.py`). The gate is re-specified:
- **what it reads:** the main sample's pooled full-salience σ_study;
- **when:** at analysis, reading no probe outcome and no cue-off lap;
- **the cut:** braking ≤ 4.5 m and corner speed ≤ 4.75 km/h, both calibrated
  on simulated studies' own σ_study against R2's criterion, by a rule fixed
  before the run.

The 2-driver pilot is now only a forecast. Gate 0 in the §6 table and the S20
stopping-rule text are updated.

## NEW-1 (construct)

**Addressed 2026-11-01 by renaming the construct (author decision).** The
sustained reading is now **guidance-contingent performance**: performance that
holds with the guidance and not without it.

The brief now states that it covers both **dependency** and **ongoing benefit**
of the cue, which an immediate test cannot separate. For the RQ, which asks how
often a guided-performance rule fades *prematurely*, both read as a premature
fade. Guidance dependency is kept only as a candidate mechanism.

Where the change is carried:
- §1, where the first account is redefined and the two mechanisms are named;
- the RQ2 construct text in §4;
- the null's definition and the "what counts" bullet in §5, plus a
  terminology note for the simulation descriptions;
- the label of row 3 in the §6 outcome table;
- the braking prediction, which now notes that a cue that simply helps
  predicts Δ > 0, so the informative quantity is its size;
- §7, with a new never-claimed item: dependency rather than benefit;
- `CLAIMS_SHEET_v9.md` §0, K1 and §5;
- the naming decision in CLAUDE.md.
