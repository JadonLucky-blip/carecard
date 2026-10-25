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

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # or: source .venv/bin/activate
pip install -r requirements.txt
```

Tesseract's binary also needs to be installed separately (not pip-
installable) - on Windows: `winget install UB-Mannheim.TesseractOCR`.

Set your Claude API key (never commit this):

```bash
set ANTHROPIC_API_KEY=sk-ant-...        # Windows cmd
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # PowerShell
```

Then run the server:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

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

Current results (mock-mode, 3 synthetic packets - see note below):

| Packet | Grounding | Medications | Warning signs | Appointments | Home care | Diet/activity |
|---|---|---|---|---|---|---|
| er_ankle_fracture | 100% | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 |
| example_uti_er_visit | 100% | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 |
| hospital_chf_admission | 100% | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 | P 1.00 / R 1.00 |

**This table is preliminary and run against the mock extractor, not real
Claude calls** - see [AI_USAGE.md](AI_USAGE.md) for why (API budget), and
treat these specific numbers as "the harness works correctly," not as a
measurement of real-world extraction quality. A clean synthetic packet
scoring 100% against a mock that reads line-by-line is expected; it isn't
evidence about how well Claude itself would do on messier, real
handwriting-adjacent documents. Re-running this table against the real
API, on more (and messier) packets, is the next step before this
submission is final.

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
