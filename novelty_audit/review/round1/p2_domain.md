contract_role: domain
## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: warn
trigger: "a relevant rival account from the feedback-removal literature goes unmentioned"

### D3: argumentative_coherence
score: not_assessed

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

I read this brief as a motor-learning reviewer working on augmented feedback and the guidance hypothesis. Most of the domain vocabulary is used correctly. The brief cites Salmoni et al. (1984) as the origin of the guidance hypothesis, describes bandwidth KR as error information given only outside a tolerance band, and separates "guidance" (cue plus KR) from "cue". Its list of non-claims is unusually disciplined: it claims no retention benefit, no causal dependency estimate, and it notes that probe failure need not be harmful (desirable difficulty). It also recognises that withdrawing a cue may change behaviour through surprise or a shift of attention, and lists that as an open question.

I score D2 warn rather than block for two reasons. The brief says outright that the excess Δ is interpreted as dependency and "not measured as such", and the domain problems below can be fixed by relabelling and recalibrating without redesigning the study. What stops a pass is that one rival account is missing, and it is the one this field treats as basic: the learning–performance distinction. An immediate, within-acquisition decrement on feedback withdrawal is a performance effect. In the guidance-hypothesis literature, dependency is a claim about learning, judged on retention or transfer after transient feedback effects have had time to dissipate, and usually against a comparison group that received less feedback. Two consequences follow. The interpretive label for Δ is too strong (W1). And the calibration choice the brief defends on domain grounds can carry the dependency signal into the null (W2).

### S1: The core inferential problem is framed correctly
The brief sets guidance dependency against regression to the mean under selection, which is the right pair. Feedback-withdrawal studies seldom say plainly that a rule which withdraws feedback after a good run will see worse performance next, whether or not any dependency exists. Here it is said plainly.
**Evidence Anchor**: text: §1 "the rule removes a cue right after a run of good passes, so the following passes are worse on average even if the guidance did nothing"

### S2: The non-claims match what the domain can support
The brief does not claim a learning or retention benefit, a causal dependency estimate, or dependency on the cue alone, and it notes that probe failure may be a desirable difficulty rather than harm. A within-session design with no delayed test and no comparison arm cannot support more than this.
**Evidence Anchor**: text: §7 "Nor that a probe failure harms learning (desirable difficulty)."

### S3: Joint cue-and-KR withdrawal is acknowledged and the construct is narrowed to match
Because KR is suppressed together with the cue during a probe, the brief names the construct "guidance", not "cue". The label therefore matches what is actually withdrawn.
**Evidence Anchor**: text: §8 item 6 "KR is withdrawn with the cue during a probe"

### W1: A within-acquisition probe decrement is labelled with a learning construct
**Severity**: Major
**Evidence Anchor**: text: §4 RQ2 "It is *interpreted* as **guidance dependency** (cue plus KR, withdrawn together); it is not measured as such."
**Confidence**: 4 — direct expertise in guidance-hypothesis and retention-test conventions

Salmoni et al. (1984) and the studies that followed (Winstein & Schmidt 1990; Schmidt & Wulf 1997) define dependency through retention or transfer performance after acquisition with frequent or concurrent feedback. That performance is measured once the transient effects of the feedback schedule have dissipated, typically on a delayed no-feedback test, and is compared against a lower-feedback schedule. The 2-lap probe has neither feature. It sits inside acquisition with no delay, and the comparison is a simulated learner, not a group trained differently. A decrement on such a probe mixes three things: dependency in the field's sense (no internal reference has formed); a temporary performance effect of losing information the learner is still using; and the attentional effects the brief already lists under §8.1. In the brief's own logic, the null removes only regression to the mean and the practice trend. The temporary performance effect is part of Δ by construction.

Minimum remedy: name Δ for what it measures, such as "excess immediate withdrawal decrement" or "probe-failure excess attributable to guidance withdrawal". Reserve "guidance dependency" for the field's retention-based construct, and state the learning–performance distinction explicitly (Kantak & Winstein 2012 is a citable review), with the 4-lap unassisted block identified as an immediate, not delayed, no-feedback test. A stronger but costlier option is a short delayed no-feedback test. Even then, the brief's single-condition design means the comparison would be with the null, not with a lower-feedback group. That choice belongs to the author.

### W2: Fitting the null on cue-off laps absorbs the effect Δ is meant to detect
**Severity**: Major
**Evidence Anchor**: text: §5 "**Fitted on cue-off laps** (probe laps plus the unassisted block)."
**Confidence**: 4 — the direction of the bias follows from the guidance hypothesis itself

The case for cue-off calibration is domain-correct as far as it goes: concurrent feedback improves performance while it is present, so cue-on spread is plausibly understated. But the same literature predicts that withdrawal raises error and variability in learners who depend on the feedback. Probe laps, and the first laps of the unassisted block, are exactly where that rise would show. A noise model fitted there takes the dependency-driven spread into its residual σ. That raises P_null and pulls Δ toward zero. The bias is not neutral: if the effect is there, this design understates it. The brief raises the circularity under §8.2, but only as a question of sample reuse. It does not say that the bias has a known sign, and that sign is set by the domain theory it relies on. The planned model check (reproducing cue-on statistics) partly constrains this, but not fully, because a model that fits cue-on laps can still carry a withdrawal-inflated σ.

Minimum remedy: state the expected direction of the bias. Report Δ under both a cue-on-fitted σ and a cue-off-fitted σ, so a reader can see the range bracketed by the two known biases (understated in opposite directions). Consider excluding the first passes after any withdrawal from the fit. Stronger option: estimate σ from cue-off passes only after the post-withdrawal transient has been modelled explicitly. This is costlier and needs a pre-specified transient form.

### W3: LC-CUSUM is placed among regression-to-the-mean corrections
**Severity**: Minor
**Evidence Anchor**: text: §7 "regression-to-the-mean corrections (LC-CUSUM / Biau 2008; Ye et al. 2016; Linden 2026)"
**Confidence**: 3 — familiar with LC-CUSUM from the surgical learning-curve literature; Ye et al. 2016 and Linden 2026 not verified

Biau et al. (2008) is a sequential test for declaring when an individual has reached a competence level, with controlled error rates under a null of inadequate performance. It is not a regression-to-the-mean correction. It is closer prior art for the "decision accuracy" framing of RQ2: a competence declaration with a stated false-declaration rate. Grouping it with RTM corrections understates how much the decision-error framing overlaps with it. Recategorise it, and state how attributing post-withdrawal failures differs from declaring competence sequentially.

### W4: The guidance hypothesis is paraphrased as the learning–performance distinction
**Severity**: Minor
**Evidence Anchor**: text: §1 "Performance with guidance is not performance without it (the guidance hypothesis; Salmoni et al. 1984)."
**Confidence**: 4 — standard textbook construct

The guidance hypothesis says more than this. Frequent or concurrent feedback guides performance during acquisition, and that guidance creates a dependency that degrades performance when the feedback is withdrawn at retention. The one-line gloss is closer to the general learning–performance distinction. Restate it fully. The full version is also what makes W1 visible.

### W5: The claim that concurrent feedback lowers variability carries no citation, though it supports a design choice
**Severity**: Minor
**Evidence Anchor**: text: §5 "concurrent feedback reduces movement variability while it is on, so a cue-on σ is plausibly biased low"
**Confidence**: 4 — the claim is plausible and has support in the literature, but is uncited here

This premise is the stated reason for fitting the null on cue-off laps, which is the most consequential modelling choice in the brief. It needs a source: Schmidt & Wulf (1997) on concurrent feedback in acquisition, or the review by Sigrist et al. (2013). Note also that bandwidth KR has its own documented effect on consistency (Sherwood 1988; Lee & Carnahan 1990). The brief keeps KR on throughout cue-on laps, so the cue-on σ reflects cue plus KR, not cue alone. State this.

### W6: Several cited works have no full references, so their representation cannot be checked
**Severity**: Minor
**Evidence Anchor**: absence: manuscript reference list — expected full bibliographic entries for TRACK 2026, Eneano et al. 2026, Linden 2026, Ye et al. 2016 and ARRS; checked §1, §4, §6, §7, §8 and the document end
**Confidence**: 3 — I cannot verify these works independently

The novelty positioning in §7 rests on the claim that Eneano et al. propose probe-gated withdrawal and that ARRS implements it, and RQ1's motivation rests on how TRACK 2026 is characterised. With no references given, D2's requirement that prior work be represented correctly cannot be checked for these sources. Add full entries.

**Suggested references (only works I am confident exist).** Salmoni, Schmidt & Walter (1984), Psychological Bulletin, on KR and motor learning; Winstein & Schmidt (1990), Journal of Experimental Psychology: Learning, Memory, and Cognition, on reduced KR frequency; Schmidt & Wulf (1997), Human Factors, on continuous concurrent feedback degrading learning; Sherwood (1988), Perceptual and Motor Skills, on bandwidth KR and movement consistency; Lee & Carnahan (1990), Quarterly Journal of Experimental Psychology, on bandwidth KR; Kantak & Winstein (2012), Behavioural Brain Research, on the learning–performance distinction; Sigrist, Rauter, Riener & Wolf (2013), Psychonomic Bulletin & Review, a review of augmented feedback modalities; Biau et al. (2008), British Journal of Surgery, on LC-CUSUM.
