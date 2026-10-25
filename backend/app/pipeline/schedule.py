"""
Component 6 (STARRED).

Authorship note (see AI_USAGE.md): written by Claude at the student's
request, same as components 3 and 5.

WHAT THIS DOES: turns sig abbreviations/phrases (BID, q8h, PRN, "x 7
days", "with food"...) into a concrete schedule - clock times, a date
range, as-needed limits.

WHY RULE-BASED, NOT AN LLM: medication timing has to be exactly right
every time, and a fixed set of rules either matches a known pattern or
honestly doesn't - it can't confidently guess wrong the way a language
model might. Anything that doesn't match a known pattern is flagged
`unparsed=True` rather than given a made-up schedule.

Runs on `frequency_as_written` + `duration` combined into one string,
because the extraction step (component 4) doesn't always split a sig
like "BID x 7 days" the same way every time - sometimes it's split
cleanly, sometimes it's all in `frequency_as_written`. Combining both
fields before parsing makes this robust to either case.
"""
import re
from datetime import date, timedelta

from app.schema import Medication, ScheduleEntry

# These clock times aren't literally written in a sig - a sig only says
# HOW OFTEN, never WHAT TIME - so these are reasonable defaults the UI
# shows the patient, who can edit them (not built in v1 - see README).
DEFAULT_WAKE_HOUR = 8
DEFAULT_BEDTIME_HOUR = 21

FIXED_FREQUENCY_TIMES = {
    "qd": [8],
    "bid": [8, 20],
    "tid": [8, 14, 20],
    "qid": [8, 12, 16, 20],
}

# Checked in order; first one that matches a word in the sig text wins.
# Multi-word phrases that CONTAIN "daily" (e.g. "twice daily") must be
# checked before the bare "\bdaily\b" -> qd pattern, or that generic
# pattern would match them first and misread "twice daily" as once a day.
FREQUENCY_WORD_PATTERNS = [
    (r"\btwice (?:a|per) day\b", "bid"),
    (r"\btwice daily\b", "bid"),
    (r"\bbid\b", "bid"),
    (r"\bthree times (?:a|per) day\b", "tid"),
    (r"\bthree times daily\b", "tid"),
    (r"\btid\b", "tid"),
    (r"\bfour times (?:a|per) day\b", "qid"),
    (r"\bfour times daily\b", "qid"),
    (r"\bqid\b", "qid"),
    (r"\bq\.?d\.?\b", "qd"),
    (r"\bonce (?:a|per) day\b", "qd"),
    (r"\bonce daily\b", "qd"),
    (r"\bdaily\b", "qd"),
]

QHS_RE = re.compile(r"\bqhs\b|\bat bedtime\b|\bhs\b", re.I)
PRN_RE = re.compile(r"\bprn\b|\bas needed\b", re.I)
Q_HOURS_RE = re.compile(r"\bq\.?\s*(\d{1,2})\s*h(?:r|rs|ours?)?\b", re.I)
EVERY_HOURS_RE = re.compile(r"\bevery\s+(\d{1,2})\s*hours?\b", re.I)
DURATION_DAYS_RE = re.compile(r"\b(?:x\s*|for\s*)?(\d{1,3})\s*days?\b", re.I)
MAX_PER_DAY_RE = re.compile(
    r"(?:max(?:imum)?|up to|not to exceed)\D{0,10}(\d{1,2})\D{0,15}(?:times?|doses?)", re.I
)
WITH_FOOD_RE = re.compile(r"\bwith food\b|\bwith meals\b|\bafter meals\b", re.I)


def _times_for_interval(hours_str: str, start_hour: int = DEFAULT_WAKE_HOUR) -> list[str]:
    """Evenly spaced clock times across 24h for a 'every N hours' pattern."""
    interval = int(hours_str)
    count = max(1, 24 // interval)
    return [f"{(start_hour + i * interval) % 24:02d}:00" for i in range(count)]


def parse_schedule(med: Medication, medication_index: int) -> ScheduleEntry:
    text = f"{med.frequency_as_written} {med.duration}".strip().lower()
    entry = ScheduleEntry(medication_index=medication_index)

    if WITH_FOOD_RE.search(text):
        entry.with_food = True

    duration_match = DURATION_DAYS_RE.search(text)
    if duration_match:
        num_days = int(duration_match.group(1))
        start = date.today()
        entry.start_date = start.isoformat()
        entry.end_date = (start + timedelta(days=num_days - 1)).isoformat()

    if PRN_RE.search(text):
        entry.as_needed = True
        max_match = MAX_PER_DAY_RE.search(text)
        if max_match:
            entry.max_per_day = int(max_match.group(1))
        return entry  # as-needed meds don't get fixed clock times

    if QHS_RE.search(text):
        entry.times_of_day = [f"{DEFAULT_BEDTIME_HOUR:02d}:00"]
        return entry

    hours_match = Q_HOURS_RE.search(text) or EVERY_HOURS_RE.search(text)
    if hours_match:
        entry.times_of_day = _times_for_interval(hours_match.group(1))
        return entry

    for pattern, code in FREQUENCY_WORD_PATTERNS:
        if re.search(pattern, text, re.I):
            entry.times_of_day = [f"{h:02d}:00" for h in FIXED_FREQUENCY_TIMES[code]]
            return entry

    # Nothing recognized - don't guess at a schedule for an unfamiliar sig.
    entry.unparsed = True
    return entry
