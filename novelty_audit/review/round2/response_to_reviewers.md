# Response to Reviewers, round 1 -> round 2

Author's resolution notes, moved verbatim from the round 1 checklist. Only R1-R9 have responses at this point; S20 is added after its simulation.
S1-S19 have no author response.

## R1

**Resolved 2026-10-30.** A pre-specified per-element table (brief §6) runs in order: ineligible → too few probes (floor set with S20) → model check failed → excess (construct read from the R8 time profile) → no excess (< MDI 0.10) → indeterminate (expected for braking at n = 15). The fallback is decided by the author: the headline is the attribution method, validated in simulation before data (the eic's "stronger option"), so it stands under every outcome. RQ1 is the second result. The claims sheet was updated to match (K1 scope, null fit, censoring, braking resolution).

## R2

**Resolved 2026-10-30.** Evidence: a parameter-recovery study, `kit/tools/nullrecovery.py`, with results in `kit/tools/README.md`. Decision: the primary null is an exponential trend with a pooled rate, per-driver amplitudes and per-driver σ, fitted on cue-off laps. The all-laps-trend fit is the sensitivity analysis. Braking Δ is gated on the pilot's braking σ ≤ 4 m. *Amended the same day by R5: the primary is now the cue-on null, and this cue-off null is reported as the lower bound.* The brief's prose still needs updating by the author.

## R3

**Resolved 2026-10-30.** The cue-off rationale is gone: the primary null is fitted on guided laps (see R5). The check now uses held-out guided-lap features, never cue-off statistics, which would reject the null exactly when dependency exists. See `CONCEPT_BRIEF_v9.md` §5. Its power was simulated (`kit/tools/nullcheck.py`): false alarm ~5%, and a wrong trend form is caught in ~40–50% of studies, stated as a limitation.

## R4

**Resolved 2026-10-30.** All three checks must pass, each inside the central 98.3% (95% Bonferroni over three) of the fitted null's simulated distribution. There is one pre-specified escalation first (AR(1) / Student-t; none for check 2). An element that still fails has its Δ reported descriptively. A trend-form agreement gate was simulated and rejected. See `CONCEPT_BRIEF_v9.md` §5.

## R5

**Resolved 2026-10-30.** Evidence: an absorption simulation, `kit/tools/nullabsorption.py`, with results in `kit/tools/README.md`. Decisions: a mean shift and a variance increase on withdrawal both count as dependency. The primary null is fitted on cue-on laps (unbiased: braking attenuation 1.01–1.04, RMSE 0.027). It was narrowed the same day to full-salience laps only, because reduced salience is a partial withdrawal and leaks 11–26% of braking Δ into the fit (RMSE 0.032). The cue-off null is reported as a lower bound, because it absorbs 20–80% of the effect. This supersedes R2's choice of primary. The brief's §5 and §8 item 2 still need updating by the author, and so does the construct text under R8/R9.

## R6

**Resolved 2026-10-30.** Rule, per element, on a 90% participant cluster bootstrap: excess if the lower bound is above 0; no excess if the upper bound is below MDI 0.10 (tied to G1's ≤ 10% false-pass bound, author decision); otherwise indeterminate. Design sensitivity was simulated (`kit/tools/nulldecision.py`), with no value asserted for real data. For braking: false excess 4%; detection 45% at Δ 0.24 and 67% at Δ 0.37 (80% needs Δ ≳ 0.4); indeterminate is the expected verdict under no dependency. Brief updated: §6, §8 item 5.

## R7

**Resolved 2026-10-30.** Censored probes are excluded from P_obs and P_null alike, the count is reported, and as-pass and as-fail are sensitivity analyses (author decision). Simulated: 12–20% of braking probes are censored, and every rule is unbiased against its own true Δ when applied identically (|bias| ≤ 0.02). The feared trend-dependent bias cancels; the rules differ only in Δ's scale. Brief updated: §4.

## R8

**Resolved 2026-10-30.** Δ is reported as a probe-failure excess. Guidance dependency is a **sustained** withdrawal deficit, and the withdrawal-as-intervention rival is a **transient** one. A pre-specified time profile decides between them: probe decay (first probe lap − second) and the late-unassisted level. Simulated (`kit/tools/nulltransient.py`): for braking it separates them in 74–100% of studies at ~5% false alarm. The reading is asymmetric (a decay is also consistent with fast re-acquisition), and apex gets no reading. Brief updated: §1, §4 RQ2, §5, §7, §8 item 1.

## R9

**Resolved 2026-10-30, by scoping, with no protocol change (author decision).** The probe and unassisted block are named as immediate, within-session no-feedback tests. The construct is *immediate* guidance dependency, i.e. a deficit sustained across the ~4-lap window. It is performance-level, and dependency in the learning sense is explicitly never claimed (Salmoni et al. 1984; Winstein & Schmidt 1990; Kantak & Winstein 2012). A delayed retention block was considered and not adopted. Brief updated: §3, §4 RQ2, §5, §7. CLAUDE.md's "retention test" wording for the probe is corrected.

## S20

**Resolved 2026-11-01.** Evidence: `kit/tools/nullyield.py`, results in `kit/tools/README.md`. Probe yield is reported per element across braking σ 2–8 m and speed σ 1–4 km/h. Braking yield is σ-sensitive: a median of 10 uncensored probes at n = 15 at the committed 4 m, 7 at 5 m, and 2 at 8 m. Corner speed and apex are insensitive. The gate-1 floor is **7 pooled uncensored probes**, chosen post hoc. The pre-stated false-excess criterion was vacuous. The real small-K failure is a false "no excess" from a degenerate cluster bootstrap (53% at K 0–2 with true Δ 0.23; ≤ 3% from K 7; plateau ~5–8% near the MDI). Stopping rule: the pilot's probe count is uninformative (P(0) = 0.16 at n = 2). The existing pilot gate, braking σ ≤ 4 m, already gives P(K ≥ 7) ≥ 0.93, so it serves as the yield rule, and gate 1 is applied to the observed count at analysis. Brief updated: §6 (yield bullet, outcome table gate 1, floor-and-stopping-rule bullet).
