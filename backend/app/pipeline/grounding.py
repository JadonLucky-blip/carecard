"""
Component 5 (STARRED) - the project's core idea.

Authorship note (plain fact, see AI_USAGE.md): written by Claude at the
student's request, same as component 3. The student's plan is to study
this file well enough to explain it to a judge.

WHAT THIS DOES: the extraction step (component 4) asks Claude to quote the
exact source line for everything it extracts, but an LLM can still get
that wrong - misquote, paraphrase instead of quoting, or in the worst case
invent something that isn't in the document at all. This step is the
actual check: for every extracted item, it fuzzy-matches the claimed quote
against the real OCR text at the page/line(s) the item cites. If it
doesn't match well enough, the item is dropped before the patient ever
sees it. That's the "nothing is invented" guarantee - it isn't a prompt
instruction asking the model to behave, it's a separate, deterministic
check that doesn't trust the model's word for it.

THRESHOLDS (rapidfuzz partial_ratio, 0-100 - how well the quote aligns
with a substring of the real OCR text):
  >= 90           -> pass: kept normally
  60 <= score < 90 -> check: kept, but the UI flags it "please check"
  < 60            -> dropped: removed from the card entirely, not shown
"""
from typing import Tuple

from rapidfuzz import fuzz

from app.schema import ExtractedCard, GroundingResult, GroundingStatus, OCRDocument, Source

PASS_THRESHOLD = 90.0
CHECK_THRESHOLD = 60.0

# ExtractedCard fields that are lists of groundable items (every one has a
# `.source` and a `.grounding` field - see the Groundable base class in schema.py).
LIST_FIELDS = [
    "medications",
    "return_now_warning_signs",
    "follow_up_appointments",
    "home_care_instructions",
    "activity_and_diet_limits",
]


def _source_text(ocr_doc: OCRDocument, source: Source) -> str:
    """The actual OCR'd text at the page/lines an item claims to cite."""
    page = next((p for p in ocr_doc.pages if p.page_number == source.page), None)
    if page is None:
        return ""
    matching_lines = [line.text for line in page.lines if line.line_number in source.lines]
    return " ".join(matching_lines)


def _grade(source: Source, ocr_doc: OCRDocument) -> GroundingResult:
    real_text = _source_text(ocr_doc, source)
    score = fuzz.partial_ratio(source.quote, real_text) if real_text and source.quote else 0.0

    if score >= PASS_THRESHOLD:
        status = GroundingStatus.pass_
    elif score >= CHECK_THRESHOLD:
        status = GroundingStatus.check
    else:
        status = GroundingStatus.dropped

    return GroundingResult(status=status, match_score=score)


def _grade_list(items: list, ocr_doc: OCRDocument) -> list:
    """Grades every item in place, then filters out the dropped ones."""
    kept = []
    for item in items:
        item.grounding = _grade(item.source, ocr_doc)
        if item.grounding.status != GroundingStatus.dropped:
            kept.append(item)
    return kept


def ground_card(card: ExtractedCard, ocr_doc: OCRDocument) -> Tuple[ExtractedCard, float]:
    """
    Grades and filters every item on the card against the real OCR text.
    Returns (card, grounding_score) where grounding_score is the percentage
    of everything originally extracted that survived grounding (pass or
    check) rather than being dropped as unmatched.
    """
    total = 0
    kept_count = 0

    if card.diagnosis_plain is not None:
        total += 1
        card.diagnosis_plain.grounding = _grade(card.diagnosis_plain.source, ocr_doc)
        if card.diagnosis_plain.grounding.status == GroundingStatus.dropped:
            card.diagnosis_plain = None
        else:
            kept_count += 1

    for field_name in LIST_FIELDS:
        items = getattr(card, field_name)
        total += len(items)
        kept = _grade_list(items, ocr_doc)
        kept_count += len(kept)
        setattr(card, field_name, kept)

    grounding_score = (kept_count / total * 100) if total else 100.0
    return card, grounding_score
