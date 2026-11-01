-- kr.lua — bandwidth knowledge of results: the terminal error signal.
--
-- WHY THIS EXISTS (the literature finding of 2026-10-10, review section 0A).
--
-- TRACE's three elements show *where* to brake, *what* speed to carry and
-- *where* the apex is. All three are PRESCRIPTIVE, CONCURRENT GUIDANCE: they
-- tell the driver what to do, while they are doing it. None of them is
-- KNOWLEDGE OF RESULTS -- terminal information about how far off the attempt
-- actually was. Until this module existed the only outcome-related signal in
-- the whole system was the stage machine, and "nothing faded" carries almost no
-- information: it does not say which element, which corner, which direction, or
-- by how much.
--
-- That matters for three separate reasons, each from the review:
--
--   * Bandwidth KR (Sherwood 1988; Lee & Carnahan 1990) is the closest
--     published analogue to TRACE's tolerance bands -- but in that paradigm the
--     learner RECEIVES QUANTITATIVE ERROR whenever they fall outside the band,
--     and silence inside the band is itself the message ("correct enough").
--     TRACE had the band and never fired the signal. Lee & Carnahan showed the
--     benefit is more than reduced feedback frequency: the band carries
--     information about correctness.
--   * de Groot et al. (2011) is a bandwidth-feedback study in DRIVING (seat
--     vibration outside 0.5 m of lane centre), and off-target feedback beat
--     on-target feedback for learning. van Leeuwen et al. (2011) is the
--     contrast: continuous visual guidance in the same task improved
--     performance while present and did not survive retention.
--   * The guidance hypothesis (Salmoni, Schmidt & Walter 1984) warns against
--     exactly what TRACE was: a marker the driver can track by eye, with no
--     terminal error to learn from.
--
-- So this module is not a fourth UI element and must not be read as one. It is
-- an APPARATUS property, present identically in BOTH conditions, and it never
-- fades -- see rule 5. The adaptive-vs-static manipulation remains exactly what
-- it was: whether the guidance elements fade.
--
-- ---------------------------------------------------------------------------
-- The rules
-- ---------------------------------------------------------------------------
--
-- 1. TERMINAL, PER CORNER PASS. A message is produced when a pass CLOSES, from
--    that pass's own metrics, and is held briefly. Nothing here runs per frame;
--    concurrent delivery would make it a fourth piece of guidance rather than
--    knowledge of results.
--
-- 2. BANDWIDTH DELIVERY. A message fires only when the pass fell OUTSIDE that
--    element's tolerance band -- the same band, resolved by the same
--    lib/evaluator arithmetic, that the fading criterion gates on. Inside the
--    band the system is silent, and the silence means "correct enough". This is
--    what makes the band informative rather than merely a threshold the learner
--    never sees, and it reduces KR frequency naturally as the learner improves,
--    which is the guidance hypothesis's own argument for choosing bandwidth
--    delivery over every-corner KR.
--
-- 3. SIGNED AND IN THE METRIC'S OWN UNITS, IN THE PAST TENSE. "BRAKED 14 m
--    early", "CARRIED 9 km/h slow". The direction is the whole point: the
--    measured novice error is a systematic BIAS (CE), not scatter, and an
--    unsigned magnitude cannot be acted on. The tense is load-bearing too --
--    see message_for, where a bare "14 m early" was read in game as an
--    instruction to brake earlier.
--
-- 4. WITHDRAWN WITH THE SCAFFOLD, NEVER WITH THE MEASUREMENT. An element's KR
--    is suppressed exactly when that element is not being shown -- in `probe`
--    and `removed`, and in the `off` condition (sessions 1 and 3). The probe
--    stage is this project's retention test, and a retention test with feedback
--    running measures performance-WITH-feedback instead (Winstein & Schmidt
--    1990; every bandwidth study in the review's section 2). The measurement
--    continues underneath regardless, exactly as it already did: withdrawal
--    removes the scaffold, never the measurement.
--
--    This is one rule, not a condition check: the caller passes the per-element
--    salience LEVEL that lib/markers already computed for the renderer, so KR
--    visibility is derived from cue visibility and cannot drift from it. In
--    `static` every element is pinned at full, so static blocks get KR
--    throughout -- which is what keeps the only difference between conditions
--    "whether the guidance elements fade".
--
-- 5. KR DOES NOT FADE. At `reduced` salience the cue drops parts of itself; the
--    KR message does not change at all. Making KR fade too would turn it into a
--    second fading channel and the manipulation would no longer be the one the
--    study claims to run. A message is either delivered in full or withdrawn.
--
-- 6. ONE MESSAGE BY DEFAULT, IN THE CORNER'S CAUSAL ORDER. `kr.elements` is an
--    ORDERED priority list and `kr.max_messages` caps how many fire per pass.
--    The order is braking -> corner speed -> apex because that is the causal
--    chain through a corner: the brake point sets the entry speed, which sets
--    the line through the apex. Telling a learner "0.9 m off line" when they
--    arrived 14 m early and 9 km/h slow reports a consequence and hides the
--    cause. The cap exists because per-component bandwidth KR on a multi-part
--    task can overload the learner (review section 11), and because a single
--    message is what the section 0A diagnostic asks for.
--
--    KNOWN CONSEQUENCE, recorded rather than engineered away: at the
--    `frozen-g1` floors braking is outside its band on ~94% of novice passes,
--    so with max_messages = 1 braking monopolises KR and the other two elements
--    are effectively silent. That is precisely the braking diagnostic the review
--    specifies as its step 2, so it is right for now -- but it means two of
--    three elements currently fade on a criterion the learner gets no
--    information about. REVISIT AT G2: with the calibrated floors braking
--    passes ~59-71% of passes and the priority list actually distributes.
--
-- 7. A NULL METRIC PRODUCES NO MESSAGE. The same rule as the controller's: a
--    pass with no measurable metric is NO EVIDENCE. Inventing a number for it
--    would be a fabrication, and reporting "no reading" would tell the learner
--    about an annotation-zone fit problem rather than about their driving.
--
-- 8. A CLAMPED MEASUREMENT PRODUCES NO MESSAGE EITHER (added 2026-10-14).
--    A braking zone bounds where the initiation event is SEARCHED for, so a
--    driver already hard on the brakes when they enter it has their initiation
--    clamped to the zone's first sample and the reported distance is a FLOOR --
--    "at least 83 m early", not 83 m early. lib/pass_metrics flags it and the
--    outcome is `clamped`: the number is logged, nothing is said, and the
--    channel passes to the next element as it does for a null. Saying the floor
--    out loud would be the one thing bandwidth KR must never do, which is
--    report a quantity the apparatus did not measure. Found in game by the
--    KRtest block (2026-10-14), where two deliberately very early passes were
--    told "83 m early" and "79 m early" within 0.3 m of their zones' openings.
--
--    The CRITERION is deliberately left alone: the driver did brake at least
--    that early, so failing is the truth, and turning the pass into a null
--    would withhold real evidence from the controller. This is about what may
--    be SAID and what may be AVERAGED, not about what counts as evidence.
--
-- Every one of those outcomes is recorded per element on the pass record, so
-- the log can distinguish "told, and this is what we said" from "silent because
-- correct", "silent because withdrawn" and "silent because unmeasured". The
-- section 0A diagnostic rests entirely on that distinction.
--
-- NOTE, an overlap worth knowing about: lib/hud's `settled` phase already
-- lingers past a corner-speed zone showing the achieved minimum, coloured by
-- band membership -- which is KR-like, for one element only, and is NOT
-- bandwidth-gated. The two are complementary (the settled readout is dropped at
-- reduced salience, and corner-speed KR rarely wins the priority order), but
-- the asymmetry across elements is a confound to state rather than to assume
-- away.
--
-- Style: plain imperative Lua 5.1, helpers called directly (never stored in
-- tables and dispatched as t.fn(...) -- that crashes in CSP in-game; see
-- CLAUDE.md). No ac.* / ui.* / render.* -- headless-testable, like every other
-- lib/ module. The controller and the evaluator are untouched by this file:
-- nothing here feeds evidence, so the golden-trace parity corpus is unaffected.

local M = {}

-- Fixed order for the OUTCOME map, so every pass record carries all three
-- elements whatever `kr.elements` contains. The DELIVERY order comes from the
-- config (rule 6), not from here.
M.ELEMENTS = { 'braking', 'corner_speed', 'apex' }

-- Why no message was sent, when none was. Mirrored in passes.schema.json.
--   delivered     a message went out; `text` is verbatim what was shown
--   inside_band   the pass was within tolerance -- silence IS the signal
--   withdrawn     the element is hidden (probe, removed, or the off condition)
--   not_measured  null metric: no evidence, so nothing to report
--   capped        outside the band but it lost the max_messages priority order
--   off           KR disabled, or this element is not in kr.elements
M.OUTCOMES = { 'delivered', 'inside_band', 'withdrawn', 'not_measured',
               'clamped', 'capped', 'off' }

local function abs(v)
  if v < 0 then return -v end
  return v
end

-- --- per-element error ------------------------------------------------------

-- The signed error for one element, the band it is judged against, and WHICH
-- SIDE of the band fails. Returns nil when the metric was not measurable.
--
-- The shape is one of:
--   'two_sided'  either side of the band fails (|err| > band)
--   'high_side'  only err > band fails
--   'low_side'   only err < -band fails
--
-- It must track lib/evaluator exactly. KR is bandwidth KR: the silence inside
-- the band is as much a message as the text outside it, so if the criterion
-- stops failing on one side and KR does not, the system says "you were wrong"
-- about a pass it has just recorded as right.
--
-- All three read exactly what lib/evaluator gated on, so a message can never
-- describe a different quantity from the criterion that produced the stage:
--
--   braking       signed metres from the expert brake point (+ = earlier),
--                 two-sided against the accuracy band. The CONSISTENCY gate is
--                 deliberately not reported: it is a statement about the
--                 learner's own recent passes, and "you were 3 m from your own
--                 rolling mean" is not knowledge of results about this corner.
--                 Returns a fourth value, CLAMPED, when lib/pass_metrics
--                 clamped the initiation to the braking zone's opening -- see
--                 rule 8.
--   corner_speed  signed km/h from the expert minimum (- = slower). The SIDE
--                 follows `criteria.corner_speed_gate`: under `slow_only` (the
--                 default from 2026-10-14) only the slow side fails, so
--                 'CARRIED n km/h fast' can never be delivered and a driver
--                 quicker than the reference now gets the same silence as one
--                 exactly on it. That is the intended claim -- beating the
--                 reference is not an error -- and it is a claim, so it is
--                 written down here as well as in the config.
--   apex          RMS lateral deviation MINUS the reference's own mean RMS, so
--                 the number reported is the excess over what the reference
--                 itself managed -- which is the quantity the criterion gates
--                 on. High side only: driving closer to the expert line than
--                 the AI did is not an error. Unsigned by construction, because an RMS
--                 has no direction; whether to report signed lateral offset
--                 instead is an open question in the review's section 10.2.
local function error_for(cfg, element, corner_ref, metrics, evaluation)
  local bands = evaluation.bands
  if element == 'braking' then
    local d = metrics.brake_initiation_distance_m
    if d == nil or bands.braking_m == nil then return nil end
    return d, bands.braking_m, 'two_sided', metrics.brake_initiation_clamped == true
  elseif element == 'corner_speed' then
    local dev = evaluation.speed_envelope_deviation_kmh
    if dev == nil then return nil end
    local shape = 'low_side'
    if cfg.criteria.corner_speed_gate == 'two_sided' then shape = 'two_sided' end
    return dev, bands.corner_speed_kmh, shape
  elseif element == 'apex' then
    local rms = metrics.apex_rms_m
    if rms == nil then return nil end
    return rms - corner_ref.apex.mean_rms_m, bands.apex_m, 'high_side'
  end
  return nil
end

-- The message for one element's signed error. Returns (label, text).
--
-- Rounding is coarse on purpose: metres and km/h to the whole unit, the apex to
-- a tenth of a metre. A driver cannot act on a tenth of a metre of brake point,
-- and a short number reads in the moment a longer one does not. The label
-- matches the on-road cue's own wording ('BRAKE 3', 'APEX 3') so the message
-- and the marker it is about are obviously the same thing.
--
-- EVERY MESSAGE OPENS WITH A PAST-TENSE VERB (2026-10-14), and that is not a
-- stylistic choice. The text was '6 m early' under a label reading 'BRAKE 2',
-- and the first person to see it in game -- the person who specified and built
-- it -- read the pair as the INSTRUCTION "brake 6 m earlier", which is the
-- opposite of what it reports. An imperative label beside a bare magnitude
-- invites that reading, and a bandwidth-KR manipulation whose sign a
-- participant may invert measures nothing at all. 'BRAKED', 'CARRIED' and 'RAN'
-- put the message in the past, which is exactly the distinction the whole
-- module rests on: knowledge of RESULTS about a corner already behind the car,
-- not guidance for the corner ahead (rule 1). Found by the KRtest block,
-- 2026-10-14; the pass records from that block carry the old wording.
local function message_for(element, corner_id, err)
  if element == 'braking' then
    local word = (err >= 0) and 'early' or 'late'
    return 'BRAKE ' .. corner_id, string.format('BRAKED %.0f m %s', abs(err), word)
  elseif element == 'corner_speed' then
    -- 'fast' is unreachable under the default `slow_only` gate, because a fast
    -- pass is inside the band there and never gets a message. Kept, rather than
    -- deleted, because the gate is a config value and `two_sided` has to keep
    -- working: deleting the branch would turn a config switch into a silent
    -- wrong-sign message.
    local word = (err >= 0) and 'fast' or 'slow'
    return 'SPEED ' .. corner_id, string.format('CARRIED %.0f km/h %s', abs(err), word)
  end
  return 'APEX ' .. corner_id, string.format('RAN %.1f m off line', err)
end

-- --- the decision -----------------------------------------------------------

local function outcome_entry(outcome, err, band)
  local e = { outcome = outcome }
  if err ~= nil then e.error_value = err end
  if band ~= nil then e.band = band end
  return e
end

-- Decide this pass's KR.
--
--   cfg         the whole controller_config (reads cfg.kr only)
--   corner_ref  this corner's row of the reference table
--   metrics     lib/pass_metrics.close(...)
--   evaluation  lib/evaluator.evaluate(...)   (for the bands and the deviation)
--   levels      per-element salience LEVEL as lib/markers.level_of returned it
--               ('full' | 'reduced' | 'hidden'); nil means visible
--
-- Returns:
--   { delivered = { { element, label, text, error_value, band }, ... },
--     outcomes  = { braking = { outcome, error_value?, band?, text? }, ... } }
--
-- `delivered` is in delivery order and never longer than max_messages.
-- `outcomes` always has an entry for all three elements.
function M.evaluate(cfg, corner_ref, metrics, evaluation, levels)
  local kcfg = cfg.kr
  local outcomes = {}
  for i = 1, #M.ELEMENTS do
    outcomes[M.ELEMENTS[i]] = outcome_entry('off')
  end
  local out = { delivered = {}, outcomes = outcomes }
  if kcfg == nil or not kcfg.enabled then return out end

  local budget = kcfg.max_messages
  for i = 1, #kcfg.elements do
    local element = kcfg.elements[i]
    -- Rule 4: withdrawn with the scaffold. Checked before the metric, because
    -- a hidden element's KR is suppressed whether or not it was measurable and
    -- "withdrawn" is the more informative outcome to log.
    local level = levels and levels[element] or 'full'
    if level == 'hidden' then
      outcomes[element] = outcome_entry('withdrawn')
    else
      local err, band, shape, clamped = error_for(cfg, element, corner_ref,
                                                  metrics, evaluation)
      if err == nil then
        outcomes[element] = outcome_entry('not_measured')
      elseif clamped then
        -- Rule 8: a floor is not a measurement. The error_value and band are
        -- still logged (the floor is a real lower bound and the analysis wants
        -- to count these) but nothing is said, and the channel passes to the
        -- next element exactly as a null metric does.
        outcomes[element] = outcome_entry('clamped', err, band)
      else
        local outside
        if shape == 'high_side' then
          outside = err > band
        elseif shape == 'low_side' then
          outside = err < -band
        else
          outside = abs(err) > band
        end
        if not outside then
          -- Rule 2: silence is the signal.
          outcomes[element] = outcome_entry('inside_band', err, band)
        elseif budget <= 0 then
          outcomes[element] = outcome_entry('capped', err, band)
        else
          local label, text = message_for(element, corner_ref.corner_id, err)
          local entry = outcome_entry('delivered', err, band)
          entry.text = text
          outcomes[element] = entry
          out.delivered[#out.delivered + 1] = {
            element = element, label = label, text = text,
            error_value = err, band = band,
          }
          budget = budget - 1
        end
      end
    end
  end
  return out
end

return M
