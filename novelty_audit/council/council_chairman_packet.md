# Chairman packet

## De-anonymised mapping

- A = The Executor
- B = The Contrarian
- C = The Expansionist
- D = The First Principles Thinker
- E = The Outsider

The full responses are in `council/council_responses_anon.md` under those letters.

## Peer reviews (5)

**Review 1.**
- Strongest: B. Only B sees the null is calibrated on cue-on laps, so σ already
  contains guidance stabilisation. Only B prices a zero-probe outcome (~0.5
  probes each, ~7 events) and asks for a novelty search on C3 itself.
- Factual error in B: "apex sigma off by ~6x". The apex parameters are the ONLY
  measured set; brake and speed are assumed. D is a close second ("guidance
  dependency" overclaims).
- Blind spot: C. It ignores the assumed sigmas, n = 1 and the pilot, and claims a
  "clean" braking Δ (~15 events against a 0.16 null gives ±0.2). Forza's
  disables were player-initiated, and ARRS ran between sessions.
- All missed:
  - clustering (42 probes nested in 15 people, so ±0.12 is too narrow);
  - right-censoring (mid-probe block ends bias P_obs);
  - detrending.

**Review 2.**
- Strongest: B, for the cue-on contamination of σ (fix: calibrate on cue-off
  laps), the yield risk, and the C3 novelty search. Same apex factual error.
- Blind spot: C. "Clean braking" contradicts the figures. Re-reading Forza and
  ARRS misfits both: Forza's disables are player-initiated (F's construct);
  ARRS uses a one-week retest, where forgetting dominates.
- All missed:
  - **the 4-lap unassisted block.** Every participant gets it, so it is a
    cue-off σ source (answering B's contamination point) and a guided-vs-unguided
    contrast that survives zero probes;
  - within-session learning and fatigue break stationarity.

**Review 3.**
- Strongest: B (contamination, the zero-probe failure mode, RQ1 as the floor).
  Same apex factual error.
- Blind spot: C. Assumed sigmas ignored, braking "clean" contradicted, no pilot,
  fidelity attacks ignored.
- All missed:
  - **non-stationarity**: novices learn within 15 laps, so a stationary null is
    mis-specified and needs a trend;
  - **clustering**: a participant-level bootstrap is needed;
  - **the 4-lap unassisted block** as a fallback cue-off measure.

**Review 4.**
- Strongest: B (yield risk, contamination, pooling across very different nulls).
  Same apex error. D is a close second ("probe-failure excess").
- Blind spot: C. Re-reading Forza and ARRS would need their learners' noise
  parameters, and Forza is player-initiated. "Clean braking" again.
- All missed: the null models a NON-improving learner. Real novices improve, so
  the right comparison is "learning, no dependency", not "no learning".

**Review 5.**
- Strongest: B (contamination, yield, pooling, C3 search). Same apex error.
- Blind spot: C. Assumed sigmas, n = 1, yield; it would need each system's own
  noise parameters.
- All missed:
  - clustering (2.83 per participant with state carried over);
  - the per-corner analysis option (8 cue-off corner passes per probe);
  - pilot novices are counted against n ≈ 15.

## Facts from the repository the council did not have (the convener's corrections)

1. **v9's null already includes learning.** Framing v9 §7.2 specifies the noise
   model as driver random intercept + **practice trend** + residual, with
   detrending, precisely so improvement is not mistaken for noise. The
   simulated null rates quoted (0.00 / 0.16 / 0.53) came from **typical
   improvers**, i.e. "learning, no dependency". The phrase "noise-only" in the
   framed question undersold this. **Review 4's and Review 3's objection is
   answered by the existing design; the residual risk is trend
   misspecification.** v9 §10 already lists it as threat 2.
2. **Apex sigma:** measured (227 real passes). Brake and speed sigmas are
   assumed. B's "6x" refers to the OLD assumed apex value, already corrected.
3. **A pilot is already in the plan** (milestone M7 / Gate G2, before the main
   study). It recalibrates band floors on real novices. 2–3 pilot novices are
   therefore not a new cost, but whether pilot participants count against
   n ≈ 15 is a recruitment decision for the author.
4. **The 4-lap unassisted block exists** in the protocol for every participant.
5. **Probes are already analysed with a planned cluster bootstrap by
   participant** (v9 §7.3 step 4). Clustering is acknowledged in the plan, but
   the ±0.12 quoted in the question ignored it.
6. **C3's own novelty search has been run only as step 1 (broad).** The formal
   narrow search (step 4) is next in the author's plan. It is exactly what B
   asks for.
