"""
Unit tests for component 5 (grounding validator).

Same authorship note as test_redact.py applies - see AI_USAGE.md.
"""
from app.pipeline.grounding import ground_card
from app.schema import (
    ExtractedCard,
    Medication,
    OCRDocument,
    OCRLine,
    OCRPage,
    Source,
)


def _ocr_doc(*lines: str) -> OCRDocument:
    return OCRDocument(
        pages=[
            OCRPage(
                page_number=1,
                lines=[OCRLine(line_number=i, text=t) for i, t in enumerate(lines, start=1)],
            )
        ]
    )


def _med(quote: str, line: int = 1) -> Medication:
    return Medication(
        name_as_written="Nitrofurantoin",
        source=Source(page=1, lines=[line], quote=quote),
    )


def test_exact_quote_passes():
    doc = _ocr_doc("Nitrofurantoin 100 mg tab PO BID x 7 days")
    card = ExtractedCard(medications=[_med("Nitrofurantoin 100 mg tab PO BID x 7 days")])

    graded, score = ground_card(card, doc)

    assert len(graded.medications) == 1
    assert graded.medications[0].grounding.status == "pass"
    assert score == 100.0


def test_partial_quote_is_flagged_not_dropped():
    doc = _ocr_doc("Nitrofurantoin 100 mg tab PO BID x 7 days")
    card = ExtractedCard(medications=[_med("Nitrofurantoin tab BID x 7 days")])

    graded, score = ground_card(card, doc)

    assert len(graded.medications) == 1  # kept, not dropped
    assert graded.medications[0].grounding.status == "check"
    assert 60 <= graded.medications[0].grounding.match_score < 90
    assert score == 100.0  # "check" still counts as kept for the score


def test_fabricated_quote_is_dropped():
    doc = _ocr_doc("Nitrofurantoin 100 mg tab PO BID x 7 days")
    # not in the source document at all - this is the hallucination case
    card = ExtractedCard(medications=[_med("Take ibuprofen every 4 hours for pain")])

    graded, score = ground_card(card, doc)

    assert graded.medications == []  # dropped - never reaches the patient
    assert score == 0.0


def test_grounding_score_averages_across_mixed_items():
    doc = _ocr_doc("Nitrofurantoin 100 mg tab PO BID x 7 days")
    card = ExtractedCard(
        medications=[
            _med("Nitrofurantoin 100 mg tab PO BID x 7 days"),  # pass
            _med("Take ibuprofen every 4 hours for pain"),  # dropped
        ]
    )

    graded, score = ground_card(card, doc)

    assert len(graded.medications) == 1
    assert score == 50.0  # 1 of 2 originally-extracted items survived


def test_wrong_line_number_is_dropped():
    """Citing a real quote but the WRONG line number should fail too -
    the quote is checked against what's actually at the cited line(s),
    not searched for anywhere in the document."""
    doc = _ocr_doc(
        "Nitrofurantoin 100 mg tab PO BID x 7 days",
        "Drink plenty of water.",
    )
    card = ExtractedCard(medications=[_med("Nitrofurantoin 100 mg tab PO BID x 7 days", line=2)])

    graded, _ = ground_card(card, doc)

    assert graded.medications == []
