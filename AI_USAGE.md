# AI Usage Disclosure

CareCard was built with Claude (Anthropic) as a pair-programming assistant.
Congressional App Challenge rules require AI use to be disclosed and
require that the app show significant personal work. This file logs what
Claude generated, what I wrote, and what I changed, in the order things
were built, so I can speak to any of it directly.

---

## Project scaffolding

Claude generated the repo layout, dependency lists, and the non-starred
pipeline steps:
- `backend/app/schema.py` - data models for the pipeline (field
  names/structure are from my own project spec; the Pydantic code is
  Claude's)
- `backend/app/config.py` - environment variable loading
- `backend/app/pipeline/preprocess.py` (component 1: image grayscale/
  threshold/blur-detection)
- `backend/app/pipeline/ocr.py` (component 2: Tesseract wrapper that
  reconstructs numbered lines with bounding boxes)
- `backend/app/pipeline/extract.py` (component 4: the Claude API call that
  does structured extraction, including the system prompt and schema)
- `backend/app/main.py` - FastAPI endpoint wiring the pipeline together
- `eval/run_eval.py` and one worked example packet/gold pair
- Frontend scaffold (Vite/React/TypeScript/Tailwind/PWA config) and the
  card UI components (upload flow, warning banner, med checklist,
  appointments, source-highlight viewer, print view)
- `.gitignore`, `CREDITS.md`, this file

These aren't the three starred components the rules require me to author
personally (PII redaction, grounding validator, medication schedule
parser) - they're the infrastructure around my design. I can explain how
each of these works.

**Notable decision:** the demo's key moment - tap a medicine, see its
source sentence highlighted on the photo - needs OCR bounding boxes to
stay aligned with the original photo. Rotating the photo to de-skew it
(a step preprocess.py has code for) would move those boxes out of
alignment, so de-skew is written but not called in v1. Tradeoff: OCR
quality on a visibly tilted photo is worse than it could be.

**Environment notes:** `textstat` was dropped from requirements.txt (its
pinned version needs `pkg_resources`, which current `setuptools` doesn't
ship, and it wasn't being used since the plain-language rewrite step is
out of scope for this build). The backend runs on Python 3.13, not this
machine's default 3.14, because several packages don't have 3.14 wheels
yet.

## Component 3: PII Redaction (`backend/app/pipeline/redact.py`)

Written by Claude. The original plan was for me to write the first draft
myself; under time pressure I asked Claude to write it directly after it
explained the design first.

How it works: label-proximity matching for things without a fixed format
(name, DOB, MRN, insurance ID, address - look for a label like "DOB:" and
redact what follows it on that line), plus regex for things with a fixed
shape regardless of label (phone numbers). Dates are only redacted next to
a DOB-style label, never on a blanket date pattern, because a blanket rule
would also wipe out the follow-up appointment date that the extraction
step needs to keep.

Known limitations:
- A label needs a colon or `#` right after it to be recognized.
- The generic "name" label also catches non-name values after lines like
  "Pharmacy Name:" - it over-redacts rather than under-redacts.
- Addresses without an "Address:" label are only caught by a "City, ST
  12345" shape.
- The same name only gets the same token if it's labeled each time; a bare
  mention later in a sentence isn't linked to the earlier one (see
  `test_repeated_name_gets_the_same_token`, which documents this directly).

9/9 tests pass (`pytest tests/test_redact.py`).

## Component 5: Grounding Validator (`backend/app/pipeline/grounding.py`)

Written by Claude, same basis as component 3.

How it works: every extracted item cites a page/line/quote. This step
fuzzy-matches (`rapidfuzz.partial_ratio`) the claimed quote against the
actual OCR text at that page/line. Score >= 90 keeps the item normally,
60-89 keeps it flagged "please check" in the UI, below 60 drops it from
the card entirely before the patient sees it. The card's grounding score
is the percentage of everything originally extracted that survived (pass
or check) rather than being dropped.

Known limitation: grounding checks the cited line number(s), not the
whole document - an item that cites the wrong line fails even if the
quote is real and exists elsewhere in the document. That's intentional
(it's stricter), but worth being able to explain.

5/5 tests pass (`pytest tests/test_grounding.py`).

## Component 6: Medication Schedule Parser (`backend/app/pipeline/schedule.py`)

Written by Claude, same basis as component 3.

How it works: rule-based (not an LLM) pattern matching over the
frequency/duration text extracted in component 4 - covers QD/daily, BID,
TID, QID, q4h/q6h/q8h/q12h, QHS/at bedtime, PRN (with optional max-per-day),
"x N days" duration, and "with food". Anything that doesn't match a known
pattern is flagged `unparsed` rather than given a guessed schedule - this
is the main design point worth being able to explain: a wrong guess about
medication timing is worse than admitting "we don't know."

One real bug caught while testing: "twice daily" was initially being
read as "once daily" because the generic `\bdaily\b` pattern matched
before the more specific "twice daily" pattern got a chance to. Fixed by
checking the specific multi-word phrases first. Worth mentioning if asked
about testing, since it's a genuine example of a test catching a bug.

30+ sig strings tested, 49/49 backend tests pass overall
(`pytest tests/`).

## Frontend / Card UI

Written by Claude (upload flow, warning banner, medicine checklist with
tap-to-source, appointments with calendar export, print view, source
photo highlighting). Not one of the three starred components.

During review, Claude also caught that the Diagnosis section was being
rendered before the red warning banner - a real violation of the spec's
"warning section always comes first" requirement, not just a style
preference - and fixed the ordering.

## Hardening extract.py before its first real run

Since `extract.py` is the one component that genuinely can't be tested
without spending money, Claude gave it a closer review rather than
leaving it untouched: raised `max_tokens` (4096 -> 8192, so a document
with many medications/warnings can't get silently truncated mid-response),
added explicit handling for `stop_reason == "refusal"` and `"max_tokens"`
and for a missing tool-use block (previously these would have surfaced as
an unhelpful generic error).

**Correction found on the first real API test**: this same pass had also
added `output_config={"effort": "medium"}` as a cost optimization, but
the installed `anthropic` SDK (0.42.0, pinned in requirements.txt)
predates that parameter entirely - `messages.create()` raised
`TypeError: unexpected keyword argument 'output_config'` immediately,
before any network call was made (so this cost nothing to find). Removed
it rather than risk upgrading the SDK untested with real money on the
line. Good reminder that code written against current API docs still
needs to be checked against the actually-pinned dependency version, not
just assumed compatible.

**Second issue found on the next real API test, more serious**: the
request didn't fail with an API error - it got routed to the wrong
server entirely. The response body was openrouter.ai's website HTML, not
anything from Anthropic. This machine has an `ANTHROPIC_BASE_URL`
environment variable set (from some other tool/project, unrelated to
CareCard) pointing at a third-party proxy, and since the backend never
pinned its own `base_url`, the Anthropic SDK picked up that ambient
setting instead of defaulting to the real API. Fixed by passing
`base_url="https://api.anthropic.com"` explicitly in `extract.py` so
CareCard's behavior doesn't depend on whatever else happens to be
configured on the machine it runs on. No Anthropic API cost was incurred
by either failed attempt - neither one actually reached Anthropic's
servers.

## Written answers and demo video script

`WRITTEN_ANSWERS.md` and `DEMO_VIDEO_SCRIPT.md` are Claude-written drafts,
explicitly marked as drafts to personalize, not text to submit as-is. The
technical-problems section is grounded in bugs actually found and fixed
during this build (see above); the inspiration section is deliberately
left as a placeholder for my own story rather than invented.

## End-to-end testing and the API budget constraint

I don't have budget to spend on the Claude API right now, so real
end-to-end testing of component 4 (the actual Claude call) hasn't
happened yet - that still needs to happen before the submission is final,
since the eval table and demo video need to show genuine AI extraction,
not a stand-in. In the meantime, Claude built `backend/app/pipeline/
mock_extract.py`: a crude, heading-based rule-based parser that stands in
for the real Claude call during development, toggled with
`CARECARD_MOCK_EXTRACTION=1`. It only works on documents shaped like this
project's own synthetic packets and is clearly marked as dev-only - it
should never be what's shown to a judge as "the AI."

Using the mock, the full pipeline was run end to end (synthetic photo ->
preprocess -> OCR -> redact -> extract -> ground -> schedule -> card UI)
through the actual browser, not just unit tests. This caught real bugs
worth being able to describe:

- **CORS/error-handling bug**: an uncaught exception in the FastAPI
  endpoint bypassed `CORSMiddleware`'s header-adding, so the browser
  reported a generic "Failed to fetch" instead of the real error. Fixed
  by catching broadly in `main.py` and re-raising as `HTTPException`,
  which stays inside FastAPI's normal (CORS-safe) error path.
- **Mock parser state-leak bug**: the mock's heading-based state machine
  didn't reset between pages, so a second page's repeated letterhead
  text got misclassified as whatever section was active at the end of
  the previous page. Fixed by resetting state on every page change.
  (This is specific to the mock's design, not something that affects the
  real Claude-based extraction, which reads the whole document at once.)
- **Eval harness bug**: `model_dump()` wasn't passed `by_alias=True`, so
  `follow_up_appointments` serialized under the Python attribute name
  (`with_`) instead of the schema's alias (`with`), making every
  appointment compare as empty against the gold file. Also found my own
  gold JSON had medication `name_as_written` set to the full sig string
  instead of just the drug name, inconsistent with the schema's separate
  dose/route/frequency fields - fixed both.
- Confirmed the demo's key moment (tap a medicine -> its exact source
  sentence highlights on the original photo) actually works, including
  the bounding-box math.
- **Real design gap, not just a bug**: a follow-up appointment's phone
  number was coming back empty on the card. Cause: the phone number gets
  redacted (as `[PHONE_1]`) before extraction, same as any other PII -
  correct, since the LLM shouldn't see it - but nothing ever restored it
  afterward, so the patient's "tap to call your doctor" feature was
  silently broken. A clinic's callback number isn't the patient's own
  PII, though, so it's safe to show it back to them. Fixed by adding
  `restore_pii()` to `redact.py` (the reverse of redaction, using the
  same in-memory token map) and calling it on `appt.phone` after
  extraction in `main.py` - this is the exact mechanism the original
  project spec described for restoring a patient's first name, applied
  to a second field once testing surfaced the need. Also caught a
  genuine OCR quirk while debugging this: Tesseract read "Patel in 1
  week" as "Patelin 1 week" (merged, no space) on the synthetic test
  photo, which is why the doctor's name shows a run-on word in the demo
  screenshot - a real OCR limitation on tightly-kerned synthetic text,
  left as-is rather than "fixed" by hand-tuning the test image.

- **Heading-detection bug (found while adding packets 2 and 3)**: the
  mock's section-heading check matched a keyword as a substring anywhere
  in a line, not just in an actual heading. Two ordinary content lines -
  a warning sign that says "...or call 911 immediately", and a diet limit
  that says "...sodium diet" - were each silently swallowed and treated
  as a new section heading instead of being extracted as items, because
  they happened to contain "call 911" / "diet". This is exactly the kind
  of thing a real, naturally-phrased discharge document does constantly,
  so it's a good example of why a crude heuristic parser needs real test
  variety, not just one clean packet. Fixed by requiring a heading line
  to actually look like a heading (fully uppercase, like real packets'
  "HOME CARE" / "ACTIVITY AND DIET LIMITS") instead of matching a keyword
  anywhere.
- Also fixed the mock capturing only the *first* frequency keyword on a
  line (e.g. reading "q6h PRN muscle spasm" as fixed-every-6-hours
  instead of as-needed, because "q6h" appeared before "PRN"). Now it
  captures every frequency keyword on the line, in order, so `schedule.py`
  (which already correctly prioritizes PRN over a fixed interval when
  both are present) gets the full picture instead of a truncated one.

With the bugs fixed, 3 synthetic packets (an ER UTI visit, a hospital CHF
admission, and an ER ankle fracture with abbreviation-heavy, two-PRN-drug
sigs) each score 100% precision/recall on every field and 100% grounding
using the mock. That's expected for clean synthetic packets matching the
mock's assumptions - it demonstrates the harness and pipeline wiring work
correctly, not real-world Claude extraction quality.

## Real Claude API results

After setting a real `ANTHROPIC_API_KEY`, two more real bugs turned up
immediately (both caught before any API cost, since both failed locally):

- `output_config={"effort": "medium"}` (added as a cost optimization)
  isn't supported by the pinned `anthropic` SDK version (0.42.0) -
  `TypeError` on the first call. Removed it.
- The second attempt returned **openrouter.ai's website HTML**, not an
  Anthropic response - this machine has an `ANTHROPIC_BASE_URL` env var
  set by some other, unrelated tool, pointing at a third-party proxy, and
  the SDK picked that up since our code never pinned its own base URL.
  Fixed by passing `base_url="https://api.anthropic.com"` explicitly in
  `extract.py`, so CareCard's behavior doesn't depend on whatever else is
  configured on the machine running it.

With both fixed, real Claude extraction worked, including a case that
shows *why* the "nothing is invented" + grounding design matters: for one
packet, the real model combined two separate OCR lines (a medication's
sig line and its purpose line on the line below) into a single accurate
citation spanning both - something the crude mock could never do, since
it only ever reads one line at a time.

Running the full eval harness against the real API (3 packets, ~$0.03
total) scored 14 of 15 category checks at 100% precision/recall. The one
exception (`er_ankle_fracture`'s follow-up appointment) looked at first
like a real miss - 0% precision, 100% "hallucination rate" - but turned
out to be **a gold-label bug, not an extraction bug**: Claude correctly
extracted `"orthopedics, Dr. Nguyen"` (the source line literally reads
"See orthopedics, Dr. Nguyen..."), which is more complete than my gold
file's narrower `"Dr. Nguyen"`, and didn't fuzzy-match closely enough to
count. Confirmed via a small debug script
(`eval/_debug_appt.py`) that printed the raw extracted value before
fixing the gold label - rather than assuming the discrepancy was Claude's
fault. This is worth being able to explain to a judge directly: this
eval harness's "hallucination rate" measures distance from a hand-written
gold label, which itself can be wrong or just narrower than a correct
answer - it is not an infallible ground truth, and a 0% score on one
field doesn't automatically mean the AI invented something.
