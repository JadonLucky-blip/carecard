"""
Component 3 (STARRED).

NOTE on authorship (see AI_USAGE.md for the full disclosure): this file
was written by Claude at the student's explicit request after the student
said they couldn't write it unassisted under time pressure. This is a
deviation from the original plan ("student writes the first draft, AI
reviews"). The student's plan is to learn this file well enough to explain
every part of it to a judge - that's why the comments below are written as
a teaching explanation, not just a terse description.

WHAT THIS DOES: before any OCR'd text is sent to Claude for extraction, we
replace personally identifying information with placeholder tokens like
[NAME_1] or [MRN_1]. The mapping from token back to the real value is
returned too, but kept only in memory (the caller decides what to do with
it - we never write it to disk).

HOW: two different techniques, because PII shows up in two different ways
in a discharge document:

1. LABEL-PROXIMITY: things like a patient's name or address don't have a
   fixed format you could write a regex for, but they almost always appear
   right after a label, like "Patient: Jordan Rivera" or "DOB: 05/22/1990".
   So for each category, we keep a list of labels to look for, and if a
   line matches "<label>: <anything>", we treat <anything> (to the end of
   the line) as the value to redact.

   Important design point: dates are ONLY redacted when they follow a
   DOB-style label. A blanket "redact every date" rule would also wipe out
   the follow-up appointment date and medication duration, which the
   extraction step (component 4) needs to keep. Only the date of birth is
   actually PII here.

2. SHAPE-BASED: phone numbers have a recognizable shape (three digits,
   three digits, four digits) no matter where they appear in a line, so a
   regex finds them anywhere - e.g. a phone number sitting inside a
   sentence like "Call 555-201-4488 to schedule." gets redacted while the
   rest of that sentence (which the extraction step needs) stays intact.
   Addresses get a similar shape-based backstop: a "City, ST 12345" tail
   is distinctive enough that if we see one, we redact that whole line.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, Tuple

from app.schema import OCRDocument, OCRLine

# ---- shape-based patterns (no label needed) --------------------------------

# Matches (555) 201-4488, 555-201-4488, 555.201.4488, 555 201 4488.
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}")

# A "City, ST 12345" style tail - common at the end of an address line.
CITY_STATE_ZIP_RE = re.compile(r",\s*[A-Z]{2}\s+\d{5}(-\d{4})?\b")

# ---- label-based categories --------------------------------------------------
# Checked in this order per line. Each entry is a list of ways that label
# might be written (checked case-insensitively); the first one that matches
# wins for that category. A match requires "<label>" then optionally some
# spaces then ":" or "#" - that punctuation is what tells us "a label, not
# just a word that happens to appear in a sentence".

LABELS: Dict[str, list[str]] = {
    "NAME": [r"patient name", r"patient", r"name"],
    "DOB": [r"date of birth", r"dob"],
    "MRN": [r"mrn", r"medical record (?:number|#)", r"account (?:number|#)", r"acct\.?\s*#?"],
    "INSURANCE_ID": [r"insurance id", r"policy (?:number|#)", r"member id", r"insurance"],
    "ADDRESS": [r"address"],
}


@dataclass
class _Redactor:
    """Carries the running token<->value mapping across every line of
    every page, so the SAME value (e.g. the patient's name mentioned
    twice) always gets the SAME token instead of two different ones."""

    mapping: Dict[str, str] = field(default_factory=dict)
    _counters: Dict[str, int] = field(default_factory=dict)
    _seen: Dict[Tuple[str, str], str] = field(default_factory=dict)

    def token_for(self, category: str, value: str) -> str:
        value = value.strip()
        seen_key = (category, value.lower())
        if seen_key in self._seen:
            return self._seen[seen_key]

        self._counters[category] = self._counters.get(category, 0) + 1
        token = f"[{category}_{self._counters[category]}]"
        self._seen[seen_key] = token
        self.mapping[token] = value
        return token

    def redact_line(self, text: str) -> str:
        for category, label_patterns in LABELS.items():
            for label_pattern in label_patterns:
                match = re.search(rf"(?i)\b(?:{label_pattern})\s*[:#]\s*(.+)$", text)
                if match and match.group(1).strip():
                    value = match.group(1)
                    token = self.token_for(category, value)
                    text = text[: match.start(1)] + token
                    break  # found this category's label - don't try its other spellings

        text = PHONE_RE.sub(lambda m: self.token_for("PHONE", m.group(0)), text)

        if CITY_STATE_ZIP_RE.search(text):
            token = self.token_for("ADDRESS", text)
            text = token

        return text


def restore_pii(text: str, mapping: Dict[str, str]) -> str:
    """
    The reverse of redaction: replaces tokens like [PHONE_1] back with
    their real values. Used ONLY on fields the patient actually needs
    after extraction (e.g. a follow-up appointment's phone number) -
    never on anything sent to the LLM, and never on the source `quote`
    fields the grounding validator checks (those must stay exactly what
    the model saw, for the fuzzy-match against the OCR text to mean
    anything).

    Without this, a phone number mentioned only in a sentence like "Call
    555-201-4488 to schedule" would get redacted before extraction (so
    Claude never sees the real digits) and then silently come back empty
    on the card - breaking the tap-to-call feature for no good reason,
    since a clinic's phone number isn't the patient's own PII.
    """
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text


def redact_document(doc: OCRDocument) -> Tuple[OCRDocument, Dict[str, str]]:
    """
    Returns (redacted_doc, mapping) where:
      - redacted_doc is a copy of `doc` with PII replaced by tokens
      - mapping is {token: original_value}, e.g. {"[NAME_1]": "Jordan Rivera"}
    """
    redactor = _Redactor()
    redacted_pages = []
    for page in doc.pages:
        redacted_lines = [
            OCRLine(line_number=line.line_number, text=redactor.redact_line(line.text), bbox=line.bbox)
            for line in page.lines
        ]
        redacted_pages.append(page.model_copy(update={"lines": redacted_lines}))

    return OCRDocument(pages=redacted_pages), redactor.mapping
