"""
Pydantic models for CareCard's data pipeline.

These mirror the JSON schema in the project spec exactly, so the Claude
extraction call (pipeline/extract.py) can request this shape as a tool
and get it back type-checked for free.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---- OCR output (component 2) ---------------------------------------------

class BoundingBox(BaseModel):
    """Pixel box on the ORIGINAL uploaded photo (same W/H as OCRPage,
    since preprocessing only grayscales/thresholds, never resizes or
    rotates - see preprocess.py for why deskew is not applied)."""
    x: int
    y: int
    width: int
    height: int


class OCRLine(BaseModel):
    """One line of OCR text, numbered so later steps can cite it."""
    line_number: int
    text: str
    bbox: Optional[BoundingBox] = None


class OCRPage(BaseModel):
    page_number: int
    lines: List[OCRLine]
    width: int = 0
    height: int = 0
    blurry: bool = False
    sharpness_score: float = 0.0


class OCRDocument(BaseModel):
    pages: List[OCRPage]


# ---- Source citation, used by every extracted item -------------------------

class Source(BaseModel):
    page: int
    lines: List[int]
    quote: str


# ---- Extracted card (component 4) ------------------------------------------

class UrgencyLevel(str, Enum):
    call_911 = "call_911"
    go_to_er = "go_to_ER"
    call_doctor = "call_doctor"


class MedChangeStatus(str, Enum):
    new = "new"
    changed = "changed"
    stopped = "stopped"
    continue_ = "continue"


# ---- Grounding validator output (component 5, STARRED) --------------------
# Every extracted item below carries its own `grounding` field so the
# validator can annotate items in place instead of juggling a separate
# parallel array per category.

class GroundingStatus(str, Enum):
    pass_ = "pass"
    check = "check"       # weak match - flagged "please check" in the UI
    dropped = "dropped"   # no match - removed from the card entirely before it's shown


class GroundingResult(BaseModel):
    status: GroundingStatus
    match_score: float    # rapidfuzz partial_ratio, 0-100


class Groundable(BaseModel):
    """Base class: anything with a `source` citation can be grounded."""
    source: Source
    grounding: Optional[GroundingResult] = None


class DiagnosisPlain(Groundable):
    text: str


class Medication(Groundable):
    name_as_written: str
    dose: str = ""
    route: str = ""
    frequency_as_written: str = ""
    duration: str = ""
    purpose: str = ""
    new_changed_or_stopped: Optional[MedChangeStatus] = None


class WarningSign(Groundable):
    text: str
    urgency: UrgencyLevel


class FollowUpAppointment(Groundable):
    model_config = ConfigDict(populate_by_name=True)

    with_: str = Field("", alias="with")
    when: str = ""
    phone: str = ""


class HomeCareInstruction(Groundable):
    text: str


class ActivityDietLimit(Groundable):
    text: str


class ExtractedCard(BaseModel):
    diagnosis_plain: Optional[DiagnosisPlain] = None
    medications: List[Medication] = []
    return_now_warning_signs: List[WarningSign] = []
    follow_up_appointments: List[FollowUpAppointment] = []
    home_care_instructions: List[HomeCareInstruction] = []
    activity_and_diet_limits: List[ActivityDietLimit] = []


# ---- Medication schedule parser output (component 6, STARRED) -------------

class ScheduleEntry(BaseModel):
    medication_index: int          # which item in ExtractedCard.medications
    times_of_day: List[str] = []   # e.g. ["08:00", "20:00"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    as_needed: bool = False
    max_per_day: Optional[int] = None
    with_food: bool = False
    unparsed: bool = False         # True -> show "check with your pharmacist"
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None


# ---- Final assembled card returned to the frontend -------------------------

class CareCardResult(BaseModel):
    card: ExtractedCard           # items already grounded; dropped ones removed
    grounding_score: float        # overall score for the whole card, 0-100
    schedules: List[ScheduleEntry]
    ocr: OCRDocument              # original (unredacted) OCR, with bbox per line,
                                   # so the frontend can highlight a source line on
                                   # the photo it already has in memory
    ocr_used: str                 # "tesseract" or "claude_vision"
