# Anonymised advisor responses

**Response A:**

Pick B. It costs nothing to adopt: only the RQs get re-ranked and reworded, and no code changes. A is the same content with the weakest claim (C1) still at the front. D throws away a system that's already built. E is underpowered by your own numbers. F is unsearched, so it's a second literature dive before you can start anything.

Monday:

1. **Write a one-page pre-registration for B before anything else.** State Δ = P_obs − P_null per element. Mark apex as expected-uninformative now (null 0.53), so it isn't a post-hoc excuse later. Commit to ~42 pooled probes at ±0.12, and say in writing that only a large Δ is detectable. Freeze it in git.
2. **Submit ethics this week.** It's the real long pole. Nothing in RQ1 or RQ2 exists until real novices drive, and the sitting can't be re-run on the same person.
3. **Fix the null's weakest input before the main study.** Brake and speed sigmas are assumptions, and corner speed's 0.00 null rests entirely on one of them. Run 2–3 pilot novices first. Measure their lap-to-lap sigmas, re-run the null, then lock it. Calibrating a "calibrated null" on numbers you made up is the first thing an examiner will ask about. This is also the only way RQ1 actually becomes the null's calibration input, which is what B depends on.
4. **Treat C as filler work, time-boxed to one week, and only after step 1.** It needs no participants, so do it while ethics is pending or between sessions. Start with TRACE's quorum plus Hsieh's EMA-clamp, which is easy to re-implement. Shen's rule only goes in if the paper specifies it precisely enough; if it doesn't, drop it rather than guess. Run a quick novelty search on "false-fade rate under a non-learner" before you write any of it up. If C slips, B still stands on its own.
5. **Cut RQ4 today.** It's one fewer analysis to freeze before you see the data.

The risk to plan around is time, not novelty. B with a pilot-calibrated null is something you can defend. B with assumed sigmas is the v6 failure again, just spotted later.

**Response B:**

The weak point in every option except D is that RQ2 only produces data if real novices reach probes, and nothing so far shows they will. The figure of 2.83 probes per participant comes from a novice model you already know is wrong: apex sigma is off by about 6x, and the brake and speed sigmas are assumed. The only real driving data is n = 1, a researcher who is faster than a novice, and even his blocks showed near-zero criterion passes at the earlier floors. If real novices reach about 0.5 probes each, you get roughly 7 events in total and Δ cannot be estimated. A single sitting cannot be re-run, so you would find this out too late.

Second, C3 carries all the novelty, and it has the same weakness that killed v6. A noise-only parametric null is a Monte Carlo baseline. An examiner from biostatistics or EDM will call it a standard permutation or bootstrap null applied to a controller. A search for "simulated null for mastery or fade decision rules" has not been run, and that is how v6 died. Run that search before you commit.

Third, the null is calibrated on live data that was recorded with the cue on. The lap-to-lap sigma you feed it already contains whatever stabilisation the guidance provides. That shrinks or inflates P_null in a direction you cannot know, so the null is not free of guidance dependency, only of explicit guidance dependency. Say this, or calibrate it only on the probe and unassisted laps.

Fourth, the per-element nulls make pooling meaningless:
- **Corner speed:** a null of 0.00 resting on an assumed sigma means any failure counts as "dependency". That is an artefact of the assumption, not a finding.
- **Apex:** a null of 0.53 swamps any dependency.
- **Braking:** at about 15 events and a null of 0.16, the CI is roughly ±0.2.

So no single element yields an interpretable Δ, and pooling them averages things that are not comparable.

**Verdict:** take B, but make RQ1 the floor that survives zero probes. Run a 2–3 novice pilot before you freeze RQ2's wording. Reject C: its re-implemented rules invite fidelity attacks and it has not been novelty-searched.

**Response C:**

The undervalued asset is C3, and every option except C treats it as a supporting method when it could be the headline. Pick C, and push it further than the framing does.

Right now the null simulator is one study's internal control. Make it a general audit instrument: a noise-only benchmark that takes any fade, mastery or assist-withdrawal rule and returns its false-fade rate for a learner who is not learning. That changes the contribution from "my controller has an error rate" to "here is how to price any adaptive-withdrawal rule before a human touches it." Hsieh's EMA ghost, Shen's assisted-score rule and TRACE's quorum are the first three entries. ARRS's 3-in-a-row and Forza's assist-disable heuristic are obvious next ones, and they cost no participants.

The hidden prize sits in the published rates the audit flags as "measured elsewhere." Forza's 38–80% switch-back and ARRS's 18–41% retest failure are being read as evidence of dependency or forgetting. Run a calibrated null against those rules and you can say how much of each figure regression to the mean predicts on its own. That re-reads someone else's well-known result, which is the kind of finding that gets cited. Linden only handles a single cutoff, so the gap is real.

RQ1 is bigger than "the calibration input." Release the per-corner ICC/SEM/MDC table as an open within-session reliability dataset for sim racing. TRACK 2026 named it as the missing "first rung," so publishing it puts the thesis underneath future work in that community.

The n = 15 live study then does one job: an existence proof that the method runs on real data, giving one empirical Δ estimate, likely clean on braking and honestly swamped on apex. The swamped apex result is a finding, not an embarrassment, because it shows the null doing exactly what it is for.

Novelty-search C's rule comparison this week. If it is clear, that is where the thesis is.

**Response D:**

You're asking "which framing", but the question underneath is: **what claim can 15 people, one sitting each, actually support?** Rebuild from that and most of the options fall away.

Strip it down. Every fade rule, whether TRACE's, Hsieh's, Shen's or Forza's, is a decision made from a handful of noisy passes. Your own MDC work showed that a 3–4 pass window cannot resolve the improvement on offer. So the basic problem is not "does TRACE fade well". It is **"nobody can tell whether any fade decision was earned, because nobody separates learning from noise at the moment of decision."** That is the thesis. TRACE is the instrument that shows it, not the claim.

Now look at what your feasibility numbers say about RQ2 as written:
- The braking and corner-speed noise models are assumed. Corner speed's null of 0.00 is fully set by an assumed sigma.
- Apex's null of 0.53 swamps any signal.
- Per-element counts of 11–16 events give Δ intervals wider than any effect you could hope to see.

So Δ = P_obs − P_null is currently mostly a property of your simulator, not your participants. RQ2 cannot lead until the null is grounded.

The order that follows:
1. **RQ1 is what gives the null its validity, not a side study.** Within-session σ, ICC and MDC from real novices are the only thing that turns the null from an assumption into a measurement. Design the single sitting first and foremost to estimate σ per corner per metric, because you cannot re-run it.
2. **The null-audit method is the contribution.** Option C is the natural endpoint: one method gives a false-fade rate for any rule under a non-learner. That generalises, needs no learning claim, and fills the "validate the source of adaptation" gap Nickl names. Implement the rules faithfully from the papers and state where you had to guess.
3. The observed probe failures then *test* the null. They are not the headline.

Pick **C, ordered RQ1 → null → audit → probe check.** Cut RQ4. One more point: "guidance dependency" names a construct your probe cannot isolate, because the cue and the KR are withdrawn together. Call it "probe-failure excess" and say plainly what it bundles.

**Response E:**

Read cold, the pitch is: "we hide the help for two laps, and if they get worse, we call it dependency." An examiner outside sim racing will hear "the guidance hypothesis" (decades old) and stop listening. The only thing that keeps their attention is that you can tell dependency apart from ordinary lap-to-lap noise. So B's instinct is right: the null has to lead. But B as written has a problem the author may be too close to see.

**The headline method may produce no clear answer on its only real use.** ~42 probes. Apex null 0.53, so apex is swamped. The corner-speed null of 0.00 rests entirely on an *assumed* sigma. The real data so far is n=1, the builder. An outsider will ask: "Your null is calibrated on the live data. Which live data? The same 15 people whose probe failures you're testing?" If yes, that sounds circular unless you explain it in one plain sentence. If Δ comes back with a wide interval and one element is undefined, the thesis's main method has shown nothing on the system it was built for.

**That is why C matters more than it looks.** Running the null against other people's published fade rules gives a result that doesn't depend on recruitment: "rule X fades a non-learner Y% of the time." Anyone can understand that number, and it shows the method transfers. Caveat: re-implementing rules from papers invites "you built a strawman," so publish the re-implementations and their own test cases.

**Vocabulary that will lose a reviewer:** "quorum," "traverses," "pair 1," "G1," "frozen-g1b." And "guidance dependency" overclaims when the cue and the KR message are withdrawn together. Call it "probe failure beyond noise," and treat dependency as an interpretation, not a label.

**Verdict:** B plus a small C. The null method leads, the published-rule comparison is the result that doesn't need participants, and the live Δ is reported as a demonstration, not the proof. Do not lead with "first implementation." To an outsider that is the weakest kind of novelty there is.
