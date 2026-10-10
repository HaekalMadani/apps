"""M6: the instrument response format and the "questionnaire files saved" clause.

The evaluation plan's after-every-session integrity check lists four things it
verifies, and three of them were already real: telemetry gaps, expected lap
counts, and the fade-event log parsing. The fourth — "questionnaire files
saved" — had nothing to check, because instrument responses had no format. This
is that clause.

The point of checking it the same day is that a missing questionnaire is
recoverable for about an hour and unrecoverable afterwards: the participant has
gone home, and a TLX answered from memory a week later is not a TLX. So the
checker has to know which instruments each session owes, which is the bulk of
what is tested here.
"""

import json

import pytest

from trace_kit import integrity
from trace_kit import validate as pyval

COLUMNS = integrity.expected_columns()


def manifest(block_id, session=2, **overrides):
    doc = {
        "schema_version": 1,
        "block_id": block_id,
        "participant_id": block_id.split("_")[0],
        "session": session,
        "condition": "adaptive",
        "pair_id": "pair1",
        "config_hashes": {"annotation": "a" * 64, "reference": "b" * 64,
                          "controller_config": "c" * 64},
        "versions": {"app": "0.3.0", "csp": "0.2.11", "ac": "1.16.4"},
        "started_at": "2026-09-08T12:00:00",
        "laps_completed": 2,
    }
    doc.update(overrides)
    return doc


def write_manifest(directory, block_id, **overrides):
    doc = manifest(block_id, **overrides)
    (directory / "manifest_{}.json".format(block_id)).write_text(
        json.dumps(doc), encoding="utf-8")
    return ("manifest_{}.json".format(block_id), doc)


def write_instrument(directory, instrument, key, **overrides):
    doc = {
        "schema_version": 1,
        "instrument": instrument,
        "participant_id": key.split("_")[0],
        "session": overrides.pop("session", 2),
        "recorded_at": "2026-09-08T13:00:00",
        "responses": overrides.pop("responses", {}),
    }
    doc.update(overrides)
    (directory / "instrument_{}_{}.json".format(instrument, key)).write_text(
        json.dumps(doc), encoding="utf-8")
    return doc


TLX = {"variant": "raw", "mental_demand": 60, "physical_demand": 30,
       "temporal_demand": 45, "performance": 50, "effort": 65, "frustration": 25}

PRE_STUDY = {"age_years": 24, "sim_racing_hours_total": 6.0,
             "league_participation": False, "eligibility_confirmed": True}

POST_STUDY = {"confidence_overall": 5, "confidence_braking": 5,
              "confidence_corner_speed": 4, "confidence_apex": 4,
              "dependence_braking": 3, "dependence_corner_speed": 3,
              "dependence_apex": 2, "noticed_fading": True}

INTERVIEW = {"consent_to_record": True, "duration_min": 12.5}


# --- the schema -------------------------------------------------------------

def test_every_instrument_type_has_a_valid_example():
    for instrument, session, responses in (
            ("pre_study", 1, PRE_STUDY),
            ("post_study", 3, POST_STUDY),
            ("interview", 3, INTERVIEW)):
        doc = {"schema_version": 1, "instrument": instrument, "participant_id": "P01",
               "session": session, "recorded_at": "2026-09-08T13:00:00",
               "responses": responses}
        assert pyval.validate_data("instrument", doc) == [], instrument


def test_tlx_requires_a_block_id():
    """Block-scoped: RQ3 compares TLX between conditions, and condition is a
    property of the block, so a TLX with no block cannot answer its own question."""
    doc = {"schema_version": 1, "instrument": "nasa_tlx", "participant_id": "P01",
           "session": 2, "recorded_at": "2026-09-08T13:00:00", "responses": TLX}
    assert pyval.validate_data("instrument", doc) != []
    doc["block_id"] = "P01_s2_pair1_adaptive_20260908_120000"
    assert pyval.validate_data("instrument", doc) == []


@pytest.mark.parametrize("bad", [
    {"mental_demand": 101},        # above the scale
    {"mental_demand": -5},         # below it
    {"variant": "weighted"},       # the weighting procedure was not used
])
def test_tlx_item_bounds(bad):
    responses = dict(TLX)
    responses.update(bad)
    doc = {"schema_version": 1, "instrument": "nasa_tlx", "participant_id": "P01",
           "session": 2, "block_id": "P01_b", "recorded_at": "2026-09-08T13:00:00",
           "responses": responses}
    assert pyval.validate_data("instrument", doc) != []


@pytest.mark.parametrize("value", [0, 8, -1])
def test_likert_items_are_bounded_1_to_7(value):
    responses = dict(POST_STUDY)
    responses["confidence_overall"] = value
    doc = {"schema_version": 1, "instrument": "post_study", "participant_id": "P01",
           "session": 3, "recorded_at": "2026-09-08T13:00:00", "responses": responses}
    assert pyval.validate_data("instrument", doc) != []


def test_an_unknown_response_key_is_rejected():
    """additionalProperties: false on every item set.

    A typo'd key would otherwise be silently stored and silently missing from
    analysis — the failure mode the M2 sequence field already demonstrated once.
    """
    responses = dict(POST_STUDY)
    responses["confidense_overall"] = 5
    doc = {"schema_version": 1, "instrument": "post_study", "participant_id": "P01",
           "session": 3, "recorded_at": "2026-09-08T13:00:00", "responses": responses}
    assert pyval.validate_data("instrument", doc) != []


# --- the integrity clause ---------------------------------------------------

def test_a_session_1_block_owes_a_pre_study(tmp_path):
    loaded = [write_manifest(tmp_path, "P01_s1_a", session=1)]
    problems = integrity.check_instruments(tmp_path, loaded)
    assert any("pre_study" in p for p in problems), problems

    write_instrument(tmp_path, "pre_study", "P01_s1", session=1, responses=PRE_STUDY)
    assert integrity.check_instruments(tmp_path, loaded) == []


def test_each_session_2_training_block_owes_its_own_tlx(tmp_path):
    """Two blocks, one TLX: the check must name the block that is missing one."""
    loaded = [write_manifest(tmp_path, "P01_s2_a", session=2),
              write_manifest(tmp_path, "P01_s2_b", session=2)]
    write_instrument(tmp_path, "nasa_tlx", "P01_s2_a", session=2,
                     block_id="P01_s2_a", responses=TLX)

    problems = integrity.check_instruments(tmp_path, loaded)
    assert len(problems) == 1
    assert "P01_s2_b" in problems[0]

    write_instrument(tmp_path, "nasa_tlx", "P01_s2_b", session=2,
                     block_id="P01_s2_b", responses=TLX)
    assert integrity.check_instruments(tmp_path, loaded) == []


def test_a_session_3_block_owes_both_instruments(tmp_path):
    loaded = [write_manifest(tmp_path, "P01_s3_a", session=3)]
    problems = integrity.check_instruments(tmp_path, loaded)
    assert any("post_study" in p for p in problems)
    assert any("interview" in p for p in problems)

    write_instrument(tmp_path, "post_study", "P01_s3", session=3, responses=POST_STUDY)
    write_instrument(tmp_path, "interview", "P01_s3", session=3, responses=INTERVIEW)
    assert integrity.check_instruments(tmp_path, loaded) == []


def test_a_dev_block_owes_nothing(tmp_path):
    """Scratch recordings answer no questionnaires."""
    loaded = [write_manifest(tmp_path, "dev_s1_a", session=1, dev_block=True)]
    assert integrity.check_instruments(tmp_path, loaded) == []


def test_an_aborted_block_owes_nothing(tmp_path):
    """The block was discarded, so the TLX that would have followed it was
    never administered. Demanding it would send the experimenter looking for a
    file that should not exist."""
    loaded = [write_manifest(tmp_path, "P01_s2_a", session=2,
                             aborted=True, abort_reason="sim_or_app_crash")]
    assert integrity.check_instruments(tmp_path, loaded) == []


def test_a_dry_run_block_owes_everything(tmp_path):
    """The whole point of the rehearsal.

    A dry run that skipped the questionnaires would be a rehearsal that could
    not catch a missing questionnaire — which is the specific failure this
    clause exists to prevent.
    """
    loaded = [write_manifest(tmp_path, "DRY01_s2_a", session=2, dry_run=True)]
    problems = integrity.check_instruments(tmp_path, loaded)
    assert any("nasa_tlx" in p for p in problems), problems


def test_an_instrument_pointing_at_an_unknown_block_is_flagged(tmp_path):
    """A filing error, and the same-day check is the cheap moment to catch it."""
    loaded = [write_manifest(tmp_path, "P01_s2_a", session=2)]
    write_instrument(tmp_path, "nasa_tlx", "P01_s2_a", session=2,
                     block_id="P01_s2_a", responses=TLX)
    write_instrument(tmp_path, "nasa_tlx", "P01_s2_typo", session=2,
                     block_id="P01_s2_typo", responses=TLX)

    problems = integrity.check_instruments(tmp_path, loaded)
    assert any("matches no manifest" in p for p in problems), problems


def test_a_schema_invalid_instrument_file_is_reported(tmp_path):
    loaded = [write_manifest(tmp_path, "P01_s1_a", session=1)]
    bad = dict(PRE_STUDY)
    bad["sim_racing_hours_total"] = "about six"
    write_instrument(tmp_path, "pre_study", "P01_s1", session=1, responses=bad)
    problems = integrity.check_instruments(tmp_path, loaded)
    assert any("instrument_pre_study_P01_s1.json" in p for p in problems), problems


def test_an_unreadable_instrument_file_is_reported(tmp_path):
    (tmp_path / "instrument_pre_study_P01_s1.json").write_text("{not json", encoding="utf-8")
    problems = integrity.check_instruments(tmp_path, [])
    assert any("unreadable" in p for p in problems), problems
