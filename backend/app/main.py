"""
FastAPI entrypoint. Wires the pipeline stages together:

  photo(s) -> preprocess -> OCR -> redact -> extract -> ground -> schedule

No data is persisted: everything lives in memory for the duration of one
request and is discarded when the response is sent.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import MAX_PHOTOS_PER_UPLOAD, USE_MOCK_EXTRACTION
from app.pipeline.extract import extract_card
from app.pipeline.grounding import ground_card
from app.pipeline.mock_extract import extract_card_mock
from app.pipeline.ocr import run_ocr, ocr_document_to_text
from app.pipeline.preprocess import preprocess_image
from app.pipeline.redact import redact_document, restore_pii
from app.pipeline.schedule import parse_schedule
from app.schema import CareCardResult

app = FastAPI(title="CareCard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/process", response_model=CareCardResult)
async def process_discharge_papers(photos: list[UploadFile] = File(...)):
    if not photos:
        raise HTTPException(400, "Upload at least one photo.")
    if len(photos) > MAX_PHOTOS_PER_UPLOAD:
        raise HTTPException(400, f"Upload at most {MAX_PHOTOS_PER_UPLOAD} photos.")

    try:
        pages = [preprocess_image(await photo.read()) for photo in photos]
        ocr_doc = run_ocr(pages)
        redacted_doc, _pii_mapping = redact_document(ocr_doc)
        transcript = ocr_document_to_text(redacted_doc)
        card = extract_card_mock(transcript) if USE_MOCK_EXTRACTION else extract_card(transcript)
        # Ground against the ORIGINAL (unredacted) OCR text so quotes that
        # include a patient's real name still match - only the LLM saw the
        # redacted version.
        grounded_card, grounding_score = ground_card(card, ocr_doc)
        # Phone numbers were redacted before extraction (so the LLM never
        # saw them), but a clinic's callback number isn't the patient's own
        # PII and the patient needs it for tap-to-call - restore it now
        # that the real pipeline work (extraction, grounding) is done.
        for appt in grounded_card.follow_up_appointments:
            appt.phone = restore_pii(appt.phone, _pii_mapping)
        schedules = [
            parse_schedule(med, i) for i, med in enumerate(grounded_card.medications)
        ]
    except NotImplementedError as exc:
        raise HTTPException(501, f"Pipeline stage not implemented yet: {exc}")
    except Exception as exc:
        # An uncaught exception here would otherwise bypass CORSMiddleware's
        # header-adding entirely (it sits inside Starlette's error handler in
        # the middleware stack), which makes the browser report an opaque
        # "Failed to fetch" instead of a real error message. Converting
        # everything into an HTTPException keeps the response inside
        # FastAPI's normal (CORS-safe) error handling path.
        raise HTTPException(502, f"Couldn't process these photos: {exc}")

    return CareCardResult(
        card=grounded_card,
        grounding_score=grounding_score,
        schedules=schedules,
        ocr=ocr_doc,
        ocr_used="tesseract",
    )
