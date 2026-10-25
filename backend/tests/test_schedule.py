"""
Unit tests for component 6 (medication schedule parser).

Same authorship note as test_redact.py / test_grounding.py applies - see
AI_USAGE.md. 30 sig strings covered, across every pattern family the
parser supports (spec asked for at least 25).
"""
from datetime import date, timedelta

import pytest

from app.pipeline.schedule import parse_schedule
from app.schema import Medication, Source


def _med(frequency: str = "", duration: str = "") -> Medication:
    return Medication(
        name_as_written="Test Drug",
        frequency_as_written=frequency,
        duration=duration,
        source=Source(page=1, lines=[1], quote="n/a"),
    )


# ---- fixed daily-frequency sig strings -> expected times_of_day -----------

FREQUENCY_CASES = [
    ("daily", ["08:00"]),
    ("QD", ["08:00"]),
    ("once a day", ["08:00"]),
    ("once daily", ["08:00"]),
    ("BID", ["08:00", "20:00"]),
    ("twice a day", ["08:00", "20:00"]),
    ("twice daily", ["08:00", "20:00"]),
    ("TID", ["08:00", "14:00", "20:00"]),
    ("three times a day", ["08:00", "14:00", "20:00"]),
    ("three times daily", ["08:00", "14:00", "20:00"]),
    ("QID", ["08:00", "12:00", "16:00", "20:00"]),
    ("four times a day", ["08:00", "12:00", "16:00", "20:00"]),
    ("four times daily", ["08:00", "12:00", "16:00", "20:00"]),
    ("q4h", ["08:00", "12:00", "16:00", "20:00", "00:00", "04:00"]),
    ("every 4 hours", ["08:00", "12:00", "16:00", "20:00", "00:00", "04:00"]),
    ("q6h", ["08:00", "14:00", "20:00", "02:00"]),
    ("q8h", ["08:00", "16:00", "00:00"]),
    ("q12h", ["08:00", "20:00"]),
    ("QHS", ["21:00"]),
    ("at bedtime", ["21:00"]),
]


@pytest.mark.parametrize("frequency,expected_times", FREQUENCY_CASES)
def test_frequency_pattern_produces_expected_times(frequency, expected_times):
    schedule = parse_schedule(_med(frequency=frequency), medication_index=0)
    assert schedule.times_of_day == expected_times
    assert schedule.unparsed is False
    assert schedule.as_needed is False


# ---- as-needed (PRN) ---------------------------------------------------

def test_prn_is_as_needed_with_no_fixed_times():
    schedule = parse_schedule(_med(frequency="PRN"), medication_index=0)
    assert schedule.as_needed is True
    assert schedule.times_of_day == []
    assert schedule.max_per_day is None


def test_as_needed_phrase_is_recognized():
    schedule = parse_schedule(_med(frequency="as needed"), medication_index=0)
    assert schedule.as_needed is True


def test_prn_with_explicit_max_times_a_day():
    schedule = parse_schedule(_med(frequency="PRN, max 4 times a day"), medication_index=0)
    assert schedule.as_needed is True
    assert schedule.max_per_day == 4


def test_prn_with_not_to_exceed_doses():
    schedule = parse_schedule(_med(frequency="PRN pain, not to exceed 3 doses in 24 hours"), medication_index=0)
    assert schedule.as_needed is True
    assert schedule.max_per_day == 3


def test_prn_without_a_stated_max_leaves_it_none():
    schedule = parse_schedule(_med(frequency="PRN for pain"), medication_index=0)
    assert schedule.as_needed is True
    assert schedule.max_per_day is None


# ---- duration ("x N days") ----------------------------------------------

def test_duration_sets_start_and_end_date():
    schedule = parse_schedule(_med(frequency="BID", duration="x 7 days"), medication_index=0)
    today = date.today()
    assert schedule.start_date == today.isoformat()
    assert schedule.end_date == (today + timedelta(days=6)).isoformat()
    assert schedule.times_of_day == ["08:00", "20:00"]


def test_duration_without_x_prefix_still_parses():
    """The extraction step may put just '10 days' in the duration field,
    without the sig's literal 'x' - both must work."""
    schedule = parse_schedule(_med(frequency="TID", duration="10 days"), medication_index=0)
    today = date.today()
    assert schedule.end_date == (today + timedelta(days=9)).isoformat()


# ---- with food ------------------------------------------------------------

def test_with_food_is_detected():
    schedule = parse_schedule(_med(frequency="daily with food"), medication_index=0)
    assert schedule.with_food is True


def test_with_meals_phrase_is_detected():
    schedule = parse_schedule(_med(frequency="QID with meals"), medication_index=0)
    assert schedule.with_food is True


def test_without_food_mention_defaults_false():
    schedule = parse_schedule(_med(frequency="BID"), medication_index=0)
    assert schedule.with_food is False


# ---- combined real-world sig strings --------------------------------------

def test_bid_x_7_days_combined_in_one_field():
    """Sometimes the extraction step doesn't split frequency/duration at
    all - everything lands in frequency_as_written."""
    schedule = parse_schedule(_med(frequency="BID x 7 days"), medication_index=0)
    assert schedule.times_of_day == ["08:00", "20:00"]
    assert schedule.end_date == (date.today() + timedelta(days=6)).isoformat()


def test_tid_with_food_for_10_days():
    schedule = parse_schedule(_med(frequency="TID with food", duration="10 days"), medication_index=0)
    assert schedule.times_of_day == ["08:00", "14:00", "20:00"]
    assert schedule.with_food is True
    assert schedule.end_date == (date.today() + timedelta(days=9)).isoformat()


# ---- unparseable sigs - must flag, never guess ----------------------------

def test_unrecognized_sig_is_flagged_not_guessed():
    schedule = parse_schedule(_med(frequency="take as directed by physician"), medication_index=0)
    assert schedule.unparsed is True
    assert schedule.times_of_day == []


def test_empty_frequency_is_flagged():
    schedule = parse_schedule(_med(frequency="", duration=""), medication_index=0)
    assert schedule.unparsed is True


def test_medication_index_is_preserved():
    schedule = parse_schedule(_med(frequency="BID"), medication_index=3)
    assert schedule.medication_index == 3
