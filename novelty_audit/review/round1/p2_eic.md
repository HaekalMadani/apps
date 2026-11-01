contract_role: eic

## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: not_assessed

### D3: argumentative_coherence
score: not_assessed

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: warn
trigger: "jargon or internal shorthand left unexplained for an outside reader"

### D6: venue_fit_and_contribution
score: warn
trigger: "its significance to adaptive-system designers is asserted rather than shown, or what will be reported if the result is null or inconclusive is left unclear"

## Review Body

I read this as a pre-data research-design brief for a thesis, not as a results paper. I judged it on whether its logic holds, how clear it is, and whether the contribution it claims is defensible and reportable. No target venue is bound (criteria_binding_unavailable), so I make no fit claim about any specific venue. Fit is judged only against a generic thesis-level and CHI-class HCI standard.

Overall: the brief is compact and well ordered. Its novelty claim is unusually disciplined. It states what is claimed, what is explicitly not new, and what is never claimed, and the claim that remains is narrow enough to defend. My concerns are about significance and reportability rather than originality. The brief's own feasibility table and predictions leave one element (braking, about 16 clustered probes) as the only place where the core quantity Δ is expected to be informative. The model-check gate in §5 can withdraw Δ entirely. The brief does not say what the thesis reports in that case, or what an adaptive-system designer would do differently given a non-zero Δ or a null one. Both points can be fixed by rewriting and re-scoping the argument. Neither needs new data, so D6 is a warn rather than a block. On D5, the structure works, but internal project shorthand (F-codes, "v9 threat" numbers, unexpanded system and paper names) is left for an outside reader to decode.

### S1: Narrow, bounded novelty claim
**Evidence Anchor**: text: §7 "the first use, among works found, of a calibrated learning-plus-noise null to"
The claim is limited to what the prior-art search found, and to one use: attributing failures after a cue is withdrawn. It sits next to an explicit list of neighbouring ideas that are not claimed (simulated nulls, regression-to-the-mean corrections, probe-gated withdrawal, catch trials). This is the right shape for a defensible contribution, and it answers my Phase 1 question of whether the claim is narrow enough given what the brief disclaims.

### S2: The problem is framed as a confound designers actually face
**Evidence Anchor**: text: §1 "A rule that reads only cue-on performance cannot separate the two."
§1 sets out two competing explanations for doing worse after a cue is removed: guidance dependency, and regression to the mean under selection. An HCI or adaptive-training reader will recognise this as a real interpretive problem in fading systems. That gives the audit a reason to exist beyond being a statistical add-on.

### S3: Honest gate on reporting Δ
**Evidence Anchor**: text: §5 "Otherwise Δ is not reported as a dependency estimate."
Making the dependency reading conditional on the null reproducing the observed cue-on statistics is a credible safeguard against overclaiming. It fits the "Never claimed" list in §7.

### S4: Clear organisation and collected open questions
**Evidence Anchor**: text: §8 "Known open questions (for the reviewers to press on)"
The order is problem, system, design, RQs, null, feasibility, novelty, then open threats. That is the order a reviewer needs. Collecting the known weaknesses in one section makes the brief easy to assess.

### W1: No stated reportable result for the branches where Δ is withheld or uninformative
**Severity**: Major
**Evidence Anchor**: text: §6 "apex uninformative by design; braking the candidate for a detectable excess; corner speed no claim until the pilot."
**Confidence**: 4 — editorial judgement of reportability against the brief's own feasibility figures
By the brief's own predictions, two of the three elements cannot yield an interpretable Δ. Apex is swamped by the null, and corner speed rests on an assumed sigma. The core claim therefore rests on the braking element, at about 16 probes clustered within roughly 15 participants. On top of that, the §5 model check can remove Δ as a dependency estimate altogether. The brief never says what the core contribution is if the check fails, or if braking's Δ is indistinguishable from zero. Does it fall back to RQ1 reliability, to the attribution method as a method, or to a documented negative result? That decision decides whether a ~40-probe, one-condition study has a reportable result. It should be written down before data, ideally as part of the pre-registered predictions already planned in §6. Minimum remedy: add a short "what is reported under each outcome" paragraph covering Δ > 0, Δ ≈ 0, and model check failed. Stronger, costlier option: give the method contribution its own validation (for example, recovery of a known injected dependency in simulation), so the method stands even if the empirical Δ is withheld. This is the author's choice and adds simulation work.

### W2: What a designer would do with Δ is asserted, not shown
**Severity**: Major
**Evidence Anchor**: absence: §1–§8 — expected a statement of what an adaptive-system designer would change in a fading rule given a positive or a null probe-failure excess; checked §1 problem, §4 RQ2, §5 null, §6 predictions, §7 claimed novelty, §8 open questions
**Confidence**: 4 — this is the eic card's stated focus on whether a one-condition design answers a question designers act on
The brief shows that a cue-on rule cannot tell dependency from regression to the mean. It does not close the loop: if Δ for braking is positive, should designers lengthen qualification windows, add probes, or keep KR during probes? If Δ is null, may they trust cue-on gating? With no static arm and no learning-benefit claim, this designer-facing implication is what makes the result matter to an HCI reader. Its absence is what my Phase 1 warn trigger describes. Minimum remedy: one paragraph linking each Δ outcome to a concrete design implication for fading controllers, worded within the §7 "Never claimed" limits.

### W3: Demoting the system to supporting evidence narrows the HCI-visible contribution
**Severity**: Minor
**Evidence Anchor**: text: §4 "Supporting evidence, not a research contribution."
**Confidence**: 3 — judgement about how HCI readers weigh system and method contributions
With RQ3 explicitly not a contribution, the paper's contribution is a statistical attribution procedure. An HCI reader may then read it as statistics attached to a system, which is the risk named on the eic card. The brief could reduce this by stating that the per-element probe-and-revert controller is what makes post-withdrawal evidence exist at all, so the audit is the system's design rationale and not an analysis added afterwards. This is a framing choice and does not change the core claim.

### W4: Internal shorthand left undecoded for an outside reader
**Severity**: Minor
**Evidence Anchor**: text: §5 "form still open: F5/F6"
**Confidence**: 5 — direct reading of the text
Several references point to documents the reader does not have: "F5/F6", "F2", "v9 threat 6", "v9 threat 2", "the committed novice model", "ARRS", and "TRACK 2026" (named as a recent sim-racing paper but not cited in full). A methodological reviewer from an adjacent field cannot decode these without the source documents. Expand each one at first use, or add a short glossary.

### W5: Source reconciliation is stated but not itemised
**Severity**: Minor
**Evidence Anchor**: text: header "Where v9's text is stale (3-of-4 window, two tracks, per-corner controller), this brief uses the repository's settled values."
**Confidence**: 4 — direct reading of the text
The header says some values replace stale v9 text, but the body does not mark which numbers are repository-settled and which come from the framing document. Simulator rates (8.5%, 0%, 79%) and the feasibility counts in §6 are where a reader would want the provenance. A one-line source tag per figure, or a footnote, would let reviewers check the numbers against the right document.
