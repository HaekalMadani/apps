## Contract Paraphrase

D1 (methodology_rigor). From a methodology seat, this dimension asks whether the proposed design can actually produce the inference it is built to make: whether the sampling and measurement units are stated, whether data handling (exclusions, censoring, clustering, detrending) is specified before data are seen, whether the statistical procedures are identifiable and adequately powered or bounded for the stated sample, whether calibration data are independent of the data they are used to judge, and whether enough is specified (models, parameters, seeds, decision rules) for another analyst to reproduce the analysis. The bar is the field's ordinary peer-review standard for a design or concept brief, not for a finished empirical paper.

D2 (domain_accuracy). This dimension concerns whether the document's claims about the subject domain match current evidence and whether prior work and domain terminology are represented correctly. It is owned by the domain reviewer; from a methodology perspective it matters only insofar as a misread construct would make a measurement procedure answer a different question than claimed, and I will not score it.

D3 (argumentative_coherence). From a methodology seat, this dimension asks whether the inferential chain holds together: whether the stated questions, the measurements, and the planned analyses line up so that the evidence the design can produce would actually bear on the claims made; whether the design states in advance what outcome would count against its hypotheses; and whether any step relies on circular reasoning, such as validating a criterion with the same data or the same model that defined it, or treating a model-based quantity as if it were directly observed.

D4 (cross_disciplinary_relevance). This dimension concerns whether framing, definitions and implications are legible to readers in adjacent fields and whether interdisciplinary claims are supported. It is owned by the perspective reviewer; methodologically it is relevant only where an undefined term hides an analysis choice, and I will not score it.

D5 (writing_and_structure). This dimension covers organisation, clarity, figure and table quality, and adherence to venue conventions. It is owned by the editor seat; I will note only cases where unclear exposition prevents a method from being reproduced, under D1, and will not score D5.

D6 (venue_fit_and_contribution). This dimension asks whether the work suits its venue and makes an original, significant contribution for that readership. It is owned by the editor seat; no target venue is bound for this review, and I will not score it or make any venue claim.

## Scoring Plan

### D1: methodology_rigor
dimension_id: D1
what_to_look_for: Pre-specified units of analysis, sample size and its justification, handling of clustering and repeated measures, explicit censoring and exclusion rules, identifiability of any noise or null model from the available observations, independence of calibration data from evaluation data, a stated model-adequacy check, and enough parameter and procedure detail for reproduction.
what_triggers_block: A core inferential quantity depends on a model that cannot be identified or separated from its alternative with the stated data volume, or calibration and evaluation share data without any correction or acknowledgement, or clustered observations are analysed as independent with no stated remedy.
what_triggers_warn: Methods are sound in outline but leave an analysis choice unspecified before data (censoring treatment, detrending method, model check criterion, multiplicity across repeated looks), or the sample is acknowledged as small without stating what precision is achievable.
what_triggers_fatal: The design as specified cannot in principle produce the inference it claims, for example the decisive statistic is defined by the same data and model it is used to validate with no independent check, so no outcome could count against the hypothesis.

### D3: argumentative_coherence
dimension_id: D3
what_to_look_for: Alignment between each stated question, the measurement that answers it, and the planned analysis; a pre-data statement of which results would count against each hypothesis; claims scoped to what the design supports; model-based estimates presented as model-based rather than as direct observations.
what_triggers_block: A central claim rests on an inference step the design cannot support, such as interpreting a model-derived difference as a causal or construct-level effect without the assumptions being stated and defended, or a research question has no analysis that could answer it.
what_triggers_warn: The chain from question to analysis is coherent but some claims overreach the evidence the design can yield, or disconfirming outcomes are stated only for some hypotheses, or a limitation that weakens an inference is noted without its consequence being drawn.
what_triggers_fatal: The core argument is circular or self-sealing: the criterion of success is the same quantity used to define the construct, so every possible outcome is read as support and the thesis cannot be falsified by the planned study.

criteria_binding_unavailable

[CONTRACT-ACKNOWLEDGED]
