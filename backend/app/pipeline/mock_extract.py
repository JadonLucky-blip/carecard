"""
MOCK extraction - for local development only, so the rest of the pipeline
(grounding validator, schedule parser, card UI) can be tested without
spending on the Claude API. This is NOT part of the submission's real
extraction step and is never the thing a judge should be shown as "the
AI." The real component 4 is extract_card() in extract.py, which calls
Claude. This file's parser only works on documents shaped like this
project's own synthetic test packets (DIAGNOSIS: / MEDICATIONS /
RETURN TO THE ER... / FOLLOW UP / HOME CARE / ACTIVITY AND DIET LIMITS
headings) - it has none of the generality an LLM has.

Toggle with the CARECARD_MOCK_EXTRACTION=1 environment variable (see
config.py); main.py picks between this and the real extract_card().
"""
import re

from app.schema import (
    ActivityDietLimit,
    DiagnosisPlain,
    ExtractedCard,
    FollowUpAppointment,
    HomeCareInstruction,
    Medication,
    Source,
    UrgencyLevel,
    WarningSign,
)

LINE_RE = re.compile(r"^\[page (\d+) line (\d+)\]\s?(.*)$")

FREQUENCY_HINT_RE = re.compile(r"\b(BID|TID|QID|QD|QHS|PRN|daily|q\d{1,2}h)\b", re.I)
DOSE_RE = re.compile(r"\b\d+\s?(?:mg|mcg|g|ml)\b", re.I)
ROUTE_RE = re.compile(r"\b(PO|IV|IM|topical|SC)\b", re.I)
DURATION_RE = re.compile(r"\bx\s*(\d+\s*days?)\b", re.I)
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}|\[PHONE_\d+\]")
DOCTOR_RE = re.compile(r"\bDr\.?\s+[A-Za-z]+")
TIMEFRAME_RE = re.compile(r"\bin \d+\s*(?:day|week|month)s?\b", re.I)

HEADING_STATE = {
    "medications": "MEDS",
    "return to": "WARNINGS",
    "call 911": "WARNINGS",
    "follow up": "FOLLOWUP",
    "home care": "HOMECARE",
    "activity": "ACTIVITYDIET",
    "diet": "ACTIVITYDIET",
}


def _parsed_lines(transcript: str):
    for raw in transcript.splitlines():
        match = LINE_RE.match(raw.strip())
        if match:
            yield int(match.group(1)), int(match.group(2)), match.group(3)


def _heading_state(text: str) -> str | None:
    lower = text.lower()
    if lower.startswith("diagnosis"):
        return "DIAGNOSIS"

    # Section headings in these packets are short, fully-uppercase lines
    # (letters only - digits/punctuation don't count against str.isupper())
    # - e.g. "HOME CARE" or "RETURN TO THE ER OR CALL 911 IF YOU HAVE:".
    # Requiring that, instead of matching the keyword as a substring
    # anywhere, avoids misreading an ordinary sentence that happens to
    # mention one of these words - e.g. a warning sign that says "...or
    # call 911 immediately", or a diet limit that says "...sodium diet"
    # - as a brand new section heading and silently swallowing it.
    if not text.isupper():
        return None

    for keyword, state in HEADING_STATE.items():
        if keyword in lower:
            return state
    return None


def extract_card_mock(redacted_transcript: str) -> ExtractedCard:
    card = ExtractedCard()
    state = None
    last_med: Medication | None = None
    current_page = None

    for page, line, text in _parsed_lines(redacted_transcript):
        if page != current_page:
            # A new page's letterhead/header lines shouldn't inherit
            # whatever section was active at the end of the previous page.
            current_page = page
            state = None

        if not text.strip():
            continue

        new_state = _heading_state(text)
        if new_state:
            state = new_state
            if new_state == "DIAGNOSIS" and ":" in text:
                value = text.split(":", 1)[1].strip()
                if value:
                    card.diagnosis_plain = DiagnosisPlain(
                        text=value, source=Source(page=page, lines=[line], quote=text)
                    )
            continue

        source = Source(page=page, lines=[line], quote=text)

        if state == "MEDS":
            freq_matches = FREQUENCY_HINT_RE.findall(text)
            if freq_matches:
                dose = DOSE_RE.search(text)
                route = ROUTE_RE.search(text)
                duration = DURATION_RE.search(text)
                name = text.split()[0] if text.split() else text
                # A line can mention more than one frequency keyword at once
                # (e.g. "q6h PRN") - capture all of them in order, not just
                # the first match, so a later "PRN" isn't silently dropped
                # in favor of an earlier interval keyword. schedule.py's
                # parser checks for PRN before interval patterns, so
                # keeping both words (in whatever order they appeared) lets
                # it make the right call either way.
                last_med = Medication(
                    name_as_written=name,
                    dose=dose.group(0) if dose else "",
                    route=route.group(0) if route else "",
                    frequency_as_written=" ".join(dict.fromkeys(freq_matches)),
                    duration=duration.group(1) if duration else "",
                    source=source,
                )
                card.medications.append(last_med)
            elif last_med is not None:
                last_med.purpose = re.sub(r"^for\s+", "", text.strip().rstrip("."), flags=re.I)

        elif state == "WARNINGS":
            urgency = UrgencyLevel.call_911 if "911" in text else UrgencyLevel.go_to_er
            card.return_now_warning_signs.append(WarningSign(text=text, urgency=urgency, source=source))

        elif state == "FOLLOWUP":
            doctor = DOCTOR_RE.search(text)
            phone = PHONE_RE.search(text)
            timeframe = TIMEFRAME_RE.search(text)
            card.follow_up_appointments.append(
                FollowUpAppointment(
                    with_=doctor.group(0) if doctor else "",
                    when=timeframe.group(0) if timeframe else "",
                    phone=phone.group(0) if phone else "",
                    source=source,
                )
            )

        elif state == "HOMECARE":
            card.home_care_instructions.append(HomeCareInstruction(text=text, source=source))

        elif state == "ACTIVITYDIET":
            card.activity_and_diet_limits.append(ActivityDietLimit(text=text, source=source))

    return card
