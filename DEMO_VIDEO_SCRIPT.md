# Demo Video Script - Draft (targets ~2:15, under the 3:00 limit)

Read this once before recording, then just talk naturally - don't read it
word for word on camera. Edit anything that doesn't sound like you.

**Before recording:** this needs `CARECARD_MOCK_EXTRACTION` unset and a
real `ANTHROPIC_API_KEY` set - never show the mock extractor on camera as
if it were the real AI. See README.md's "Running it locally" section.
Use one of the synthetic packets in `eval/packets/` (or a new photo of
one printed out) so there's no real patient data anywhere near the
recording.

---

## 0:00-0:15 - Intro

*(Face camera or voiceover over the CareCard logo/homepage)*

"Hi, I'm [your name], and this is CareCard. It turns a photo of hospital
discharge papers into a plan you can actually use: what medicine to take
and when, what warning signs mean go back to the hospital, and when to
follow up. It's for patients and family caregivers right after a hospital
or ER visit - exactly when they're too overwhelmed to read a dense paper
packet."

## 0:15-0:45 - The core flow

*(Screen recording: open CareCard on a phone or laptop browser)*

"Here's a synthetic discharge packet I made up for testing - no real
patient data anywhere in this demo. I take a photo..."

*(Upload the photo, show the loading state, card appears)*

"...and in a few seconds, CareCard builds a one-page plan. Here's the key
thing that makes this different from just asking ChatGPT to read the
photo: every single item links back to exactly where it came from."

*(Tap a medicine in the checklist)*

"When I tap this medication, it shows me the exact sentence from my
actual photo that it came from - highlighted right on the page. If
CareCard can't find a real source for something, it doesn't show it at
all."

## 0:45-1:15 - Safety features

*(Scroll to the top of the card - the red warning banner)*

"This red section always comes first, no matter what - the warning signs
that mean go back to the ER or call 911. That's deliberate: the most
urgent thing on the page is the first thing you see."

*(Scroll to appointments, tap "Add to calendar" and/or "Call")*

"Follow-up appointments export straight to your calendar, and you can
tap to call the office directly."

*(Optional, if time: show the Print view)*

"And the whole card prints cleanly, so you can hand a paper copy to a
caregiver who isn't on their phone."

## 1:15-1:50 - How it works

*(Cut to the code - `grounding.py` and `schedule.py`, briefly)*

"Under the hood, there are two things I'm proudest of. First, a grounding
validator - after the AI extracts information, this code fuzzy-matches
every single item back against the real text from the photo. Anything
that doesn't match closely enough gets dropped before it's ever shown to
the patient. That's not a prompt asking the AI to behave - it's a
separate check in my own code.

Second, a rule-based medication schedule parser - no AI involved at all.
It reads sig abbreviations like 'BID' or 'q6h PRN' and turns them into an
actual checked schedule. If it doesn't recognize the pattern, it says
'check with your pharmacist' instead of guessing - because a wrong guess
about medication timing is worse than admitting it doesn't know."

## 1:50-2:15 - Results and wrap-up

*(Show the eval table from README.md or a terminal running `python
eval/run_eval.py`)*

"I built an evaluation harness that scores CareCard against hand-labeled
test packets - precision, recall, and critically, the hallucination rate:
how often it shows something that isn't actually in the source document.
[Say your real numbers here once you've run this against the real API -
don't read the mock-mode placeholder numbers on camera.]"

*(Back to camera / voiceover)*

"This was built with Claude as a pair-programming assistant - disclosed
in full in AI_USAGE.md in the repo, including exactly what I wrote
myself versus what I had Claude write under time pressure. My biggest
takeaway was [your real takeaway - see WRITTEN_ANSWERS.md draft].

For 2.0, I'd want to add caregiver sync, pharmacy pickup lookup, more
languages, and ideally get this in front of an actual nurse for feedback
before anyone used it for real. Thanks for watching."

---

## Timestamp checklist (CAC requires all of these)

- [ ] Name, app name, one-sentence purpose, target audience - **0:00**
- [ ] Core feature demo (photo -> card -> tap-to-source) - **0:15**
- [ ] At least one more feature beyond the core demo - **0:45**
- [ ] How it works technically (show real code) - **1:15**
- [ ] Tools/languages used, takeaway, 2.0 plan - **1:50**
- [ ] Total under 3:00
