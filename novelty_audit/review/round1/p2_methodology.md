contract_role: methodology
## Dimension Scores

### D1: methodology_rigor
score: block
trigger: "A core inferential quantity depends on a model that cannot be identified or separated from its alternative with the stated data volume"
block_class: repairable

### D2: domain_accuracy
score: not_assessed

### D3: argumentative_coherence
score: warn
trigger: "disconfirming outcomes are stated only for some hypotheses"

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

This is a pre-data design brief, and I judge it as one: the question is whether the design as specified can produce the inference RQ2 is built to make, not whether results exist. The brief is unusually candid. It names regression to the mean under selection as the rival explanation, labels the probe-failure excess as model-based, and commits in advance to withholding the dependency reading if the null fails its model check. Those are the right instincts for a selection-effect problem. The difficulty is that the whole weight of RQ2 rests on P_null, and P_null rests on a learning-plus-noise model whose form is still open, whose calibration data overlap the outcome it is used to judge, whose calibration laps are a mixture of conditions and times chosen by the rule itself, and whose model check is aimed at a quantity the brief's own rationale expects the model to miss. Each of these is repairable before any participant drives, mostly by simulation. Until they are addressed, D1 sits at a repairable block: the core quantity has not been shown to be identifiable from the stated data volume. D3 is a warn: the question-measurement-analysis chain is coherent in outline, but no pre-data outcome is stated that would count against the braking prediction, and the interpretive step from Δ to guidance dependency is exposed to the probe-as-intervention rival the brief itself raises.

On arithmetic: the brief reports no test statistics, degrees of freedom or p-values, and its proportions are simulation outputs with no stated stream count. The counts it does give agree with each other (about 2.8 probes times 15 participants is about 42, and 16 + 15 + 11 = 42), so I see no internal arithmetic inconsistency. The receipt section below records that no bounded procedure applies.

### S1: The rival explanation is named in the form a selection-effects analyst would state it
**Evidence Anchor**: text: §1 "the rule removes a cue right after a run of good passes"

Framing the competitor as regression to the mean conditioned on the removal rule, rather than as generic "noise", is what makes a simulated null through the same controller the right comparator in principle. The design question is correctly posed.

### S2: A pre-committed non-report rule tied to the model check
**Evidence Anchor**: text: §5 "Otherwise Δ is not reported as a dependency estimate."

Committing before data to suppress the dependency reading when the null fails its check is the kind of pre-specification the field asks for. W2 is about what the check tests, not about whether one exists.

### S3: Δ is labelled as model-based and as an interpretation
**Evidence Anchor**: text: §4 "it is not measured as such"

The brief does not present the model-derived difference as an observed causal effect, and §6 states why the randomised timing arm that would license that was not run.

### S4: The per-element decision unit is defended by a simulated alternative
**Evidence Anchor**: text: §2 "A per-corner controller was simulated and rejected: it faded cues for 79% of non-improvers."

A design choice backed by a stated, simulated failure of its alternative is better practice than an asserted unit of analysis.

### S5: Clustering is acknowledged in the uncertainty plan
**Evidence Anchor**: text: §5 "a participant cluster bootstrap for P_obs; simulation plus parameter uncertainty for P_null."

Probes are nested in participants, and the plan resamples at the participant level rather than treating 42 probes as independent. Propagating parameter uncertainty into P_null, not just simulation error, is also correct.

### S6: Logging is complete enough to re-run the controller offline
**Evidence Anchor**: text: §3 "metric values, cue and KR state, qualification events, probe start / end and outcome, reversions, censoring."

With this record, P_null can be recomputed under alternative null forms without new data, which is what makes the remedies below cheap.

### W1: The null model is not shown to be identifiable from the cue-off data volume
**Severity**: Critical
**Evidence Anchor**: text: §5 "per element (form still open: F5/F6)" and "a practice trend (per-driver slope or saturating curve);"
**Confidence**: 4 — direct competence in random-intercept/trend models and simulation-based nulls; the data volumes are read from the brief, not measured

P_null is the denominator of the core claim, and its model has three per-element components (driver intercept, driver trend, residual variability), with the trend's functional form and the residual pooling still undecided. They are to be fitted only on cue-off laps. Per participant and element, that is the 4-lap unassisted block plus whatever probe laps that element happened to receive (2 laps per probe, about 2.8 probes per participant across all elements, so often zero or one probe for a given element). Separating a per-driver slope from a per-driver intercept and a residual σ needs observations spread over time. Here they are concentrated at the session end (the unassisted block) and at moments the controller picks (probes). A saturating curve adds at least one more parameter. Nothing in the brief shows that this volume can recover the trend and σ well enough for P_null to be stable, and the brief lists the question as open (§8 item 4). A simple illustration: if a driver's trend is under-estimated, part of the learning goes into the residual σ; if it is over-estimated, the opposite happens. Either error moves P_null directly, because whether a probe fails turns on noise relative to the band. Uncorrected, the defect leaves Δ without a defined reference, so it alone invalidates RQ2's core claim. It is repairable before any participant drives.

Minimum remedy: a pre-data parameter-recovery study. Generate cue-off data under the committed novice model at the brief's own cue-off lap counts and probe timings, fit each candidate null form, and report how well slope and σ are recovered and how much P_null spreads across fits. Then pre-register a form-selection rule (for example, a stated information criterion or a pre-chosen default with sensitivity forms). Stronger and costlier: a hierarchical model that partially pools trends across drivers, which trades per-driver fidelity for identifiability and needs the pooling assumption defended; or a few fixed-schedule cue-off catch laps, independent of qualification, which buys timing spread at a cost in lap budget (the author must weigh this against the 15-lap traversal constraint).

### W2: The model check targets a statistic the fitting rationale predicts the null will miss
**Severity**: Major
**Evidence Anchor**: text: §5 "the null must reproduce observed cue-on statistics (lap-to-lap SD, qualification rate, timing of first qualification)"
**Confidence**: 4 — the logical conflict is internal to the brief; how large it is in practice depends on the unmeasured cue-on/cue-off variance ratio

The null is fitted on cue-off laps because "a cue-on σ is plausibly biased low". If that premise holds, a null with the larger cue-off σ should over-predict cue-on lap-to-lap SD and under-predict cue-on qualification rate, and so fail the check. If it passes the check, that suggests cue-on and cue-off variability are similar, which removes the stated reason for fitting on cue-off laps alone. The check therefore cannot pass in exactly the case the design was built for, and passing it partly undercuts the design. The check also has no stated tolerance (no interval, no distance, no rule for which of the three statistics must match), so "reproduce" is not yet a decision rule. Remedy: either (a) check against statistics not expected to differ under guidance (for example cue-off statistics held out of the fit, see W3), or (b) model guidance-on variability explicitly as a separate parameter estimated from cue-on laps and check the full model, stating the tolerance (for example a posterior-predictive or simulation interval) before data.

### W3: Probe laps calibrate the null and also supply the failures it judges
**Severity**: Major
**Evidence Anchor**: text: §8 item 2 "The null is fitted on cue-off laps from the same participants whose probe failures it judges."
**Confidence**: 4 — standard double-use argument; the direction of bias follows from the brief's own definitions

The brief acknowledges this overlap but gives no correction and does not say which way it biases Δ. If dependency exists, it shows up as worse or more variable probe-lap passes. Those passes enter the fit, inflate the fitted σ (or depress the fitted trend), raise P_null, and shrink Δ toward zero. The design is therefore biased against detecting the effect it is built to detect. That is conservative, not self-sealing, but a null Δ would be uninterpretable. Minimum remedy: fit P_null with each participant's own probe laps held out (leave-own-probes-out), or fit on the unassisted block only, as the primary analysis or a pre-registered sensitivity analysis, and state the expected direction of bias. Stronger: a leave-one-participant-out fit, so that no participant's data calibrates their own null.

### W4: The calibration laps mix conditions and are timed by the selection rule
**Severity**: Major
**Evidence Anchor**: text: §5 "(probe laps plus the unassisted block)"
**Confidence**: 3 — inferred from the per-element fading description in §2; the brief does not say whether other elements' cues stay on during an element's probe

Because fading is per element, a probe lap for element X is presumably a lap where the other two elements' cues and KR are still on, while the unassisted block has everything off and comes after the 15 guided laps. These two sources differ in condition (partial vs total guidance withdrawal) and in time (mid-session at selected moments vs session end). Pooling them into one noise model assumes that neither difference matters. Probe laps also occur only after a qualification run, which is the selection event whose regression the null exists to model; a trend fitted partly on post-selection laps can absorb some of that regression into the trend. Remedy: state whether the noise model includes a condition indicator (probe vs unassisted) and how the trend is extrapolated back over the cue-on laps, and include the selection timing in the recovery study of W1.

### W5: No pre-data outcome is stated that would count against the braking prediction
**Severity**: Major
**Evidence Anchor**: text: §6 "braking the candidate for a detectable excess; corner speed no claim until the pilot."
**Confidence**: 4 — the absence of a decision rule is read directly; the precision estimate is a rough binomial calculation from the brief's counts, not a fitted result

The predictions are labelled pre-registered but are qualitative. There is no decision rule on Δ (an interval excluding zero? a minimum Δ of interest?), and no statement of the smallest excess the design could resolve. At about 16 clustered braking probes and a P_null near 0.16, the binomial standard error alone is about 0.09 before any clustering inflation and before P_null's own parameter uncertainty is added. So the plausible-excess range the design can resolve may be wide, and the brief should say how wide before data. Without that, any braking Δ can be read as "a candidate excess" or "underpowered", and no outcome counts against the prediction. Remedy: pre-specify the inferential rule for Δ per element, the minimum Δ of interest, and a simulated design-sensitivity figure (the distribution of the Δ interval width under the null, at the expected probe counts and clustering). Do this without asserting any value for the real data.

### W6: Treatment of censored probes is unspecified, and it changes P_obs
**Severity**: Major
**Evidence Anchor**: text: §8 item 5 "how censored blocks (ending mid-probe) enter P_obs"
**Confidence**: 4 — censoring handling for a rate over a fixed lap budget is squarely in competence

A 15-lap block with a 2-lap probe late in the block often ends mid-probe. Counting censored probes as passes, as failures, or excluding them gives different P_obs values, and the choice interacts with timing: probes that start late are both more likely to be censored and more likely to involve a practised driver. The comparison is fair only if P_null applies the identical rule to identically censored simulated probes, which the "same lap budget" phrase implies but does not state. Remedy: pre-specify one censoring rule (exclusion with a reported censoring count is the simplest), apply it identically in the simulator, and report sensitivity to the alternatives.

### W7: The unit of P_obs's denominator is ambiguous
**Severity**: Minor
**Evidence Anchor**: text: §4 "P_obs: the probe-failure rate over all guided-qualification events."
**Confidence**: 3 — may be a wording issue rather than a design one

Qualification is defined per corner (§2), while probes are entered per element on a quorum. "Guided-qualification events" could therefore mean corner qualifications or element-level probe entries, which give different denominators and different clustering structures. State the unit explicitly (presumably element-level probe entries), and use the same unit in P_null.

### W8: The interpretation of Δ is exposed to a rival the design cannot separate
**Severity**: Major
**Evidence Anchor**: text: §8 item 1 "Removing a cue may itself change behaviour (surprise, attention shift), apart from dependency."
**Confidence**: 3 — the statistical point is firm; how large any withdrawal-surprise effect is lies outside my competence (see card blind spot)

A null built from learning plus noise excludes both dependency and any transient effect of withdrawing the cue. A positive Δ is therefore consistent with either, and with no randomised timing arm the design has no internal contrast that separates them. The brief's hedge ("interpreted as") is honest, but RQ2 is still introduced as the place where Δ is read as guidance dependency. Minimum remedy: scope the reported construct to "probe-failure excess over a learning-plus-noise null" and list withdrawal-as-intervention as an unexcluded alternative beside it. A partial, low-cost discriminator is to pre-specify the within-probe time profile: a surprise effect would plausibly be concentrated in the first passes after withdrawal, while dependency would persist across the probe and into the unassisted block. This must be stated before data and not adopted after seeing the profile.

### W9: Two of three null parameter sets are assumed, and the third comes from a single non-representative driver
**Severity**: Minor
**Evidence Anchor**: text: §6 "the brake and speed sigmas are assumptions."
**Confidence**: 4 — read directly from the brief

The feasibility table's P_null values are conditional on the committed model, as the brief says. Two consequences should be drawn explicitly. First, the corner-speed P_null of 0.00 is a boundary value, so any observed failure becomes an "excess" and any ratio comparison is undefined. The brief already withholds a corner-speed claim, which is correct, but the table should not appear to give that element a working null. Second, the apex parameters come from n = 1 (the researcher), so the "apex uninformative by design" prediction is itself model-conditional and should be re-derived after the pilot.

### W10: Simulator gate figures lack the run size and uncertainty needed to reproduce them
**Severity**: Minor
**Evidence Anchor**: text: §2 "false fade for a non-improving learner: 8.5% (bound ≤ 10%);"
**Confidence**: 4 — reproducibility affordance

The gate figures (8.5%, 0%, 79%) are reported without the number of simulated streams, a seed, or a Monte Carlo interval. That information decides whether 8.5% sits clearly inside the 10% bound or within simulation error of it. Report the streams per learner type and an interval for each gated rate.

### W11: RQ1's role as calibration input conflicts with fitting the null on cue-off laps
**Severity**: Minor
**Evidence Anchor**: text: §4 "RQ1 is also the calibration input for RQ2."
**Confidence**: 3 — may resolve to a lap-subset statement

RQ1's reliability statistics are computed over the session, which is mostly cue-on laps, while §5 fits the null on cue-off laps only, precisely because cue-on σ is thought to be biased. State which laps RQ1 is computed on and which of its quantities feed P_null, so that the calibration path is unambiguous.

## Arithmetic Receipts

no_recomputable_statistics: checked §2, §4 and §6 — no test statistics, df or p-values are reported; the percentages (8.5%, 0%, 79%, P_null 0.00/0.16/0.53) are simulation outputs with no stated stream count and are not means of integer-scale items with a stated N, so neither p_from_test_statistic, grim, grimmer nor n_from_df applies; the probe counts (about 2.8 per participant, about 42 total, 16/15/11 per element) are mutually consistent.
