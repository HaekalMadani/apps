# novelty_audit/ — the v6 → v9 transition record

**Status (2026-10-30): the v9 transition is DONE.** Steps 1–4 are complete, the
direction is chosen, the claims are fixed, and CLAUDE.md is updated. Nothing here
is a to-do unless "Still open" says so.

## Why this folder exists

Framing v6 (adaptive vs static fading) lost its novelty: the author confirmed it
was "too common in learning-science engineering", and the problem was discovered
late. v9 (`../thesis_framing_v9.md`) re-aims the thesis at **auditing fade
decisions**. This folder is the prior-art audit that tested v9 *before* building
toward it, so the same failure cannot happen silently twice.

## Read in this order

1. **`CLAIMS_SHEET_v9.md`**: what the thesis may and may not claim, what to cite
   for each, the limitations it must state, and the edits v9's prose still needs.
   **This is the binding output.**
2. `NOVELTY_AUDIT_v9.md`: step 1, the broad scan. Per-claim verdicts (C1–C5) and
   citation checks, updated through pass 2 (full texts).
3. `STEP2_directions.md`: the candidate directions A–F, scored. §3a holds the
   priced per-corner controller (ruled out).
4. `council/`: step 3, an llm-council run on the directions. It contains the
   framed question, the five anonymised advisor answers, and the chairman's
   packet (peer reviews plus repo corrections). The verdict itself was given in
   the session: **direction B; fit the null on cue-off laps; per-element
   predictions to pre-register.** Its caveat: all advisors are the same model.
5. `STEP4_protocol.md` → `STEP4_results.md`: step 4, the narrow search on the
   load-bearing claim (C3). The protocol was fixed before searching.

## The outcome in five lines

- **Lead claim (K1):** a calibrated learning-plus-noise null attributes
  post-withdrawal (probe) failures. The **probe-failure excess** is read as
  **guidance dependency** (cue plus KR).
- **The null as an idea is standard** (LC-CUSUM / Biau 2008, Ye et al. 2016,
  Linden 2026). Only its use on post-withdrawal outcomes is claimed.
- **RQ1 reliability survives** (TRACK 2026's missing "first rung").
- **Probe-gated fading is narrowed** to "first implemented, real-time, motor
  cues": the idea is in Eneano et al. 2026 (a proposal) and in ARRS (cognitive
  skills).
- **Dropped:** RQ4 desynchrony, the randomised arm (out of reach at n ≈ 15),
  the published-rule audit "C-lite" (pre-empted by Ye 2016), and the per-corner
  controller.

## Layout

| Path | What |
|---|---|
| `tools/` | `oa.py` (OpenAlex search), `cr.py` (Crossref lookup), `s2.py` (Semantic Scholar), `cites.py` (OpenAlex forward citations). Run with the `ac_dev` interpreter and `-I` |
| `logs/` | Raw search output per step. Also the **last uncommitted edits to the deleted framing v6** as a patch (`thesis_framing_v6_uncommitted_edits_20261030.patch`); v6 itself is at `git show 110156e:thesis_framing_v6.md` |
| `papers_txt/` | `pdftotext` extracts of the full texts in `../Academic Papers/`. **Copyrighted: git-ignored, never commit.** Regenerate with `pdftotext -layout` |
| `../kit/tools/percornerscan.py` | The simulation behind RQ2's probe counts and noise-only probe-failure rates (`kit/tools/README.md`) |

## Concept review (2026-10-30)

`review/`: an ARS `academic-paper-reviewer` full-mode panel on
`review/CONCEPT_BRIEF_v9.md`. The editorial letter, roadmap (R1–R9 must-fix,
S1–S20 suggested) and attachments are in `review/round1/synthesis.md`.

- **Decision: MAJOR REVISION** (mechanical; condition F2; recomputation check
  PASS). Two repairable blocks, no fatal ones.
- **DA C1 VALIDATED:** a cue-off-fitted null absorbs dependency, so Δ is biased
  toward zero. **CLAUDE.md's cue-off calibration rule is therefore under
  review.**
- **Provenance.** All seats ran on one model family; the typed provenance
  artifact could not be built because the installed plugin's contract file has
  CRLF line endings (`review/round1/PROVENANCE_NOTE.md`). This is a structured
  stress test, not independent review.

## Still open

- **Search coverage.** Semantic Scholar was rate-limited on 17 of 19 queries, and
  Scopus/WoS were not searched. K1's "not found" would be firmer after a re-run of
  query families Q2 and Q5 with an S2 API key or a library Scopus run.
- **Author prose (not done here, by design):**
  - the v9 edits in `CLAIMS_SHEET_v9.md` §5;
  - reverting the Bugeja `[CORRECTED]` brackets in `evaluation_plan_v2.md`
    L68/L136 (the v6 copies went with v6);
  - v9 flags F1, F2, F4, F5, F6;
  - whether NASA-TLX and the interview stay (v9 omits them).
