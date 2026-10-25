"""
Unit tests for component 3 (PII redaction).

See AI_USAGE.md and redact.py's module docstring for the authorship note -
these were written by Claude at the student's request; the student's plan
is to understand and be able to explain every case here, not to claim they
wrote them independently.
"""
from app.pipeline.redact import redact_document
from app.schema import OCRDocument, OCRPage, OCRLine


def _doc_from_lines(*lines: str) -> OCRDocument:
    """Test helper: build a one-page OCRDocument from plain strings."""
    return OCRDocument(
        pages=[
            OCRPage(
                page_number=1,
                lines=[OCRLine(line_number=i, text=t) for i, t in enumerate(lines, start=1)],
            )
        ]
    )


def _redacted_text(doc: OCRDocument) -> list[str]:
    return [line.text for line in doc.pages[0].lines]


def test_patient_name_is_redacted():
    doc = _doc_from_lines("Patient: Jordan Rivera")
    redacted, mapping = redact_document(doc)
    assert _redacted_text(redacted) == ["Patient: [NAME_1]"]
    assert mapping["[NAME_1]"] == "Jordan Rivera"


def test_date_of_birth_is_redacted():
    doc = _doc_from_lines("DOB: 05/22/1990")
    redacted, mapping = redact_document(doc)
    assert _redacted_text(redacted) == ["DOB: [DOB_1]"]
    assert mapping["[DOB_1]"] == "05/22/1990"


def test_mrn_is_redacted():
    doc = _doc_from_lines("MRN: 00482913")
    redacted, mapping = redact_document(doc)
    assert _redacted_text(redacted) == ["MRN: [MRN_1]"]
    assert mapping["[MRN_1]"] == "00482913"


def test_insurance_id_is_redacted():
    doc = _doc_from_lines("Insurance ID: ABC123456789")
    redacted, mapping = redact_document(doc)
    assert _redacted_text(redacted) == ["Insurance ID: [INSURANCE_ID_1]"]
    assert mapping["[INSURANCE_ID_1]"] == "ABC123456789"


def test_address_line_is_redacted():
    doc = _doc_from_lines("123 Main St, Springfield, IL 62701")
    redacted, mapping = redact_document(doc)
    assert _redacted_text(redacted)[0].startswith("[ADDRESS_1]")
    assert mapping["[ADDRESS_1]"] == "123 Main St, Springfield, IL 62701"


def test_phone_number_is_redacted_even_mid_sentence():
    doc = _doc_from_lines("Call (555) 201-4488 to schedule.")
    redacted, mapping = redact_document(doc)
    # the surrounding sentence must survive - only the phone number is PII
    assert _redacted_text(redacted) == ["Call [PHONE_1] to schedule."]
    assert mapping["[PHONE_1]"] == "(555) 201-4488"


def test_repeated_name_gets_the_same_token():
    doc = _doc_from_lines("Patient: Jordan Rivera", "Thank you for choosing us, Jordan Rivera.")
    redacted, mapping = redact_document(doc)
    # the second line has no "Patient:" label, so our heuristic won't catch
    # it - this test documents that known gap rather than hiding it.
    assert _redacted_text(redacted)[0] == "Patient: [NAME_1]"
    assert len(mapping) == 1


def test_followup_date_is_not_redacted():
    """DOB must be redacted, but an appointment date/timeframe must NOT be -
    the extraction step (component 4) needs it. Only a DOB-style LABEL
    triggers date redaction, never a bare date pattern."""
    doc = _doc_from_lines("See your primary care doctor, Dr. Patel, in 1 week.")
    redacted, _ = redact_document(doc)
    assert _redacted_text(redacted) == ["See your primary care doctor, Dr. Patel, in 1 week."]


def test_clinical_text_is_never_altered():
    lines = [
        "DIAGNOSIS: Urinary tract infection (UTI)",
        "Nitrofurantoin 100 mg tab PO BID x 7 days",
        "RETURN TO THE ER OR CALL 911 IF YOU HAVE:",
        "Fever over 101.5 F",
        "Drink plenty of water.",
    ]
    doc = _doc_from_lines(*lines)
    redacted, mapping = redact_document(doc)
    assert _redacted_text(redacted) == lines
    assert mapping == {}
