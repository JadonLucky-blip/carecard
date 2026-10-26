# CareCard

Turns a photo of hospital discharge papers into a one-page plan: what
medicine to take and when, which warning signs mean go back, and when to
follow up - in the patient's own language.

Built for the Congressional App Challenge. See [AI_USAGE.md](AI_USAGE.md)
for the AI-use disclosure and [CREDITS.md](CREDITS.md) for third-party
licenses. [WRITTEN_ANSWERS.md](WRITTEN_ANSWERS.md) and
[DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md) are drafts to personalize
before submitting, not final text.

## Why

In one study of ER patients, 50.7% had severe gaps in understanding when
to return to the hospital, and 40.1% in understanding home care (Engel et
al., *Acad Emerg Med*, 2012). Patients leave with dense paper packets and
forget most of what they were told.

## What makes this different from "ChatGPT with a camera"

1. **Nothing is invented.** Every item on the card cites the exact
   sentence it came from in the original document. A separate grounding
   step fuzzy-matches every extracted quote against the real OCR text -
   anything that doesn't match closely enough is dropped before the
   patient ever sees it.
2. **Medicine schedules are parsed by rules, not guessed by an LLM.**
   "Take 1 tab PO BID x 7 days" becomes a real checked schedule, or - if
   the sig text isn't recognized - an honest "check with your
   pharmacist" instead of an invented time.
3. **Personal info is redacted before anything reaches an AI model.**
   Names, dates of birth, MRNs, phone numbers, addresses, and insurance
   IDs are tokenized server-side first.

## Tech stack

- **Frontend:** React + TypeScript + Vite, Tailwind, PWA
- **Backend:** Python + FastAPI
- **OCR:** Tesseract (`pytesseract`) + OpenCV preprocessing
- **Extraction:** Claude API (Anthropic), forced tool-use for structured
  output
- **Testing:** `pytest` + a custom evaluation harness

## Project structure

```
backend/
  app/
    schema.py             data models shared across the pipeline
    pipeline/
      preprocess.py        component 1 - image prep, blur detection
      ocr.py                component 2 - Tesseract wrapper, bounding boxes
      redact.py             component 3 (STARRED) - PII redaction
      extract.py            component 4 - Claude structured extraction
      mock_extract.py        dev-only stand-in for extract.py (no API cost)
      grounding.py          component 5 (STARRED) - source validation
      schedule.py            component 6 (STARRED) - sig string -> schedule
    main.py                 FastAPI endpoint wiring it all together
  tests/                    pytest - 49 tests across the 3 starred components
frontend/
  src/
    components/             upload flow, card UI, source-highlight viewer
    api.ts, types.ts, ics.ts
eval/
  packets/, gold/            synthetic test packets + hand-labeled expected output
  run_eval.py                 precision/recall/hallucination-rate harness
```

## Running it locally

```bash
git clone https://github.com/JadonLucky-blip/carecard.git
cd carecard
```

**Python version matters**: use Python 3.11-3.13. Python 3.14 is too new
for several dependencies (rapidfuzz, opencv) to have prebuilt wheels yet
as of this writing - `pip install` will fail trying to compile them from
source. Check with `python --version` first; if you're on 3.14, install
3.13 from python.org or via your package manager and use that instead
(e.g. `py -3.13 -m venv .venv` on Windows).

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Tesseract's binary also needs to be installed separately (not pip-
installable):
- Windows: `winget install UB-Mannheim.TesseractOCR`
- macOS: `brew install tesseract`
- Linux (Debian/Ubuntu): `sudo apt install tesseract-ocr`

Set **your own** Claude API key (get one at console.anthropic.com - never
commit this, and never use someone else's key):

```bash
set ANTHROPIC_API_KEY=sk-ant-...        # Windows cmd
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # PowerShell
export ANTHROPIC_API_KEY=sk-ant-...     # macOS/Linux
```

Real extraction costs about $0.01-0.02 per discharge photo (Sonnet 5).

Then run the server:

```bash
python -m uvicorn app.main:app --port 8000
```

(Deliberately no `--reload` flag - we found it unreliable during
development, occasionally serving stale code silently after a file
change. Restart the process manually after editing backend files.)

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open the printed `localhost:5173` URL. Upload a synthetic discharge photo
to see the card.

### Testing without spending on the API

Set `CARECARD_MOCK_EXTRACTION=1` before starting the backend to use a
rule-based mock instead of a real Claude call (see
[mock_extract.py](backend/app/pipeline/mock_extract.py)). This exercises
the whole rest of the pipeline - redaction, grounding, schedule parsing,
the card UI - for free. **The mock is dev-only and should never stand in
for the real pipeline in a demo or judged evaluation** - it only
understands this project's own synthetic packet format and has none of
an LLM's generality.

## Evaluation

```bash
python eval/run_eval.py
```

Current results, **real Claude API** (Sonnet 5), 3 synthetic packets:

| Packet | Grounding | Medications | Warning signs | Appointments | Home care | Diet/activity |
|---|---|---|---|---|---|---|
| er_ankle_fracture | 100% | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 |
| example_uti_er_visit | 100% | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 |
| hospital_chf_admission | 100% | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 |

15/15 category checks at 100% precision/recall, 100% grounding, 0%
hallucination rate across all 3 packets. Worth reading
[AI_USAGE.md](AI_USAGE.md)'s "Real Claude API results" section before
quoting these numbers, though - getting here involved fixing a real bug
in my own gold label (not an extraction bug), and that distinction is
exactly the kind of thing a judge might ask about. These are also still
only 3 clean, typed synthetic packets, not the messier/handwriting-
adjacent documents real discharge papers often are - a useful next step,
not a claim that extraction is perfect on harder inputs.

## Known limitations / scope cuts for the 6-hour build

- RxNorm drug-name normalization, Spanish translation + back-translation
  check, browser notifications/reminders, the teach-back quiz, and a
  fancier PDF export are all out of scope for this build - see
  `AI_USAGE.md` and inline comments for specifics.
- Photo de-skew is implemented but not applied (see `preprocess.py`) so
  OCR bounding boxes stay aligned with the original photo for the
  tap-to-source feature; a visibly tilted photo will OCR worse than it
  could.
- The "Add to calendar" date is a best-effort guess from phrases like "in
  1 week" (see `ics.ts`) - CareCard doesn't invent a precise date it
  wasn't given, but it also can't always resolve a vague one, so the
  literal source text always stays visible for the patient to confirm.
- Results aren't persisted anywhere (by design, for privacy) - refreshing
  the page loses the current card.

## Privacy and safety

- No real patient documents - testing uses synthetic discharge packets.
- No server-side storage; nothing is retained after the response is sent.
- PII is redacted before any text reaches the Claude API.
- The app never adds advice that isn't in the document - no drug-
  interaction checking or dosing advice.
- If a document has no warning signs listed, the card says so explicitly
  rather than leaving that section blank or guessing.

---

CareCard helps you understand your instructions. It does not replace
your doctor or pharmacist.
