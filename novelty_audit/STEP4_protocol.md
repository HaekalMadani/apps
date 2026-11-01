# Step 4 — narrow search on C3: protocol

**Date:** 2026-10-30 · **Fixed before searching.** Deviations made while running it
are logged at the end, with their reasons.

## The claim under test (C3, as v9 will state it)

> No prior work interprets the outcome of a decision to **withdraw support**
> (fade, remove an assist, or declare mastery so that help ends) against a
> **simulated or analytic null of learners who learn and vary but have no
> dependency on the support**, in order to separate dependency from regression
> to the mean and selection.

**Naming (author decision, 2026-10-30):** the measured quantity is the
**probe-failure excess** (observed probe-failure rate minus the null's).
**Guidance dependency** is its interpretation. Guidance means the cue and its KR,
withdrawn together.

Two adjacent claims ride along, because a hit on either changes the plan:

- **C-lite:** no prior work prices a published fade or withdrawal rule's
  false-withdrawal rate under a simulated learner who never improves.
- **C3-cal:** calibrating the null on support-off data rather than support-on
  data (the council's open point) is unremarked in prior work.

## What counts as a hit

| Grade | Definition | Consequence |
|---|---|---|
| **H (direct hit)** | Meets all three: (a) a support-withdrawal or mastery decision; (b) its post-decision outcome or decision rate is compared with a simulated or analytic null in which the learner has no dependency on the support; (c) the comparison is used to attribute the observed rate | C3 falls or narrows; RQ1 becomes the fallback headline (council verdict) |
| **P (partial)** | (a) and (b) without (c), **or** a simulated-null false-positive rate for a learning/competence decision rule | C3 narrows; cite as closest work. A P on decision rules is a C-lite threat |
| **I (ingredient)** | RTM correction, simulated-student policy evaluation, or a permutation null, used in a learning context but not on a withdrawal decision | cite as background; does not narrow C3 |

Any date counts for a threat (author's date rule). Each work is labelled with its
year.

## Query families

| ID | Family | Why it could hit |
|---|---|---|
| Q1 | Simulated / null learners for mastery criteria, stopping rules, knowledge tracing | EDM evaluates criteria on simulated learners (Pelánek, already P-adjacent) |
| Q2 | Regression to the mean / selection after threshold-based advancement, fading or adaptive training | The core mechanism, in any training domain |
| Q3 | Simulated students for evaluating adaptive instructional policies (Doroudi et al.; simulated learners in AIED) | General method family; could subsume C-lite |
| Q4 | Sequential competence monitoring with simulated false-signal rates (LC-CUSUM, CUSUM, SPRT in surgical training) | Prices a competence decision's false-declaration rate under a null learner: **the strongest C-lite threat** |
| Q5 | Motor learning / rehab: guidance withdrawal or catch trials, with a baseline or noise model for the drop | The domain closest to TRACE |
| Q6 | Just-in-time adaptive interventions / micro-randomised trials: RTM in tailoring decisions | A cutoff-triggered intervention, with a known RTM literature |
| Q7 | Games: dynamic difficulty adjustment or assist removal evaluated against a simulated player null | Debeauvais-adjacent |
| Q8 | Support-off vs support-on calibration of variability (C3-cal) | Narrow; likely empty |

## Sources

- OpenAlex API (`tools/oa.py`): relevance search, recorded with counts.
- Semantic Scholar Graph API (new script `tools/s2.py`): relevance search.
- Crossref (`tools/cr.py`): verification of anything graded H or P.
- arXiv via web search, and general web search (Google Scholar not accessible).
- **Citation chasing** (forward and backward) on the three closest works so far:
  - Pelánek & Řihák 2017;
  - Biau et al. 2008 (LC-CUSUM);
  - Eneano et al. 2026.

**Not searched (stated, not hidden):** Scopus, Web of Science, PsycINFO, IEEE Xplore
and the ACM DL native indexes. A clean result is therefore "**not found in
OpenAlex / Semantic Scholar / web**", never "does not exist".

## Screening

- Titles and abstracts first. Anything that could be H or P is read in full,
  where accessible, before it is graded.
- **One screener (Claude), no second reviewer.** This is a rapid review, not a
  systematic one, and the write-up must say so. The author may spot-check any
  exclusion; every record is logged.

## Output

`STEP4_results.md`:
- the search log (query, source, count, hits by grade);
- an evidence table of everything graded H, P or I;
- the verdict on C3, C-lite and C3-cal.

`NOVELTY_AUDIT_v9.md` is then updated.

## Deviations log

See `STEP4_results.md` § Deviations from protocol.
