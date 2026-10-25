"""App-wide settings, loaded from environment variables."""
import os
import shutil

# Claude model used for structured extraction (component 4).
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

# Dev-only: use the rule-based mock in pipeline/mock_extract.py instead of a
# real Claude API call, so the rest of the pipeline can be tested without
# spending anything. Never set this for the actual judged submission - see
# mock_extract.py's module docstring.
USE_MOCK_EXTRACTION = os.environ.get("CARECARD_MOCK_EXTRACTION", "") == "1"

# On Windows, pytesseract needs the tesseract.exe path explicitly if it
# isn't on PATH yet (true right after a fresh winget install).
_DEFAULT_WIN_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract") or _DEFAULT_WIN_PATH

# Blurry-photo rejection threshold for the variance-of-Laplacian sharpness
# check in preprocess.py. Lower = stricter. Tuned by eye against a few
# synthetic test photos; adjust if real test photos get rejected too often.
BLUR_VARIANCE_THRESHOLD = 100.0

MAX_PHOTOS_PER_UPLOAD = 6
