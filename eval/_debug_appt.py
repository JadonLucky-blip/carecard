import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.pipeline.extract import extract_card  # noqa: E402
from app.pipeline.ocr import ocr_document_to_text  # noqa: E402
from app.pipeline.redact import redact_document  # noqa: E402
from run_eval import parse_transcript  # noqa: E402

transcript_text = (Path(__file__).parent / "packets" / "er_ankle_fracture.txt").read_text(encoding="utf-8")
ocr_doc = parse_transcript(transcript_text)
redacted_doc, _ = redact_document(ocr_doc)
card = extract_card(ocr_document_to_text(redacted_doc))

for appt in card.follow_up_appointments:
    print("with:", repr(appt.with_))
    print("when:", repr(appt.when))
    print("phone:", repr(appt.phone))
    print("quote:", repr(appt.source.quote))
