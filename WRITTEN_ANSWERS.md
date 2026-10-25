# Written Answers - Draft

This is a draft to edit into your own voice before submitting - not
something to paste in as-is. Everything here is grounded in what's
actually in the repo (see `AI_USAGE.md` for the full build log); the
inspiration section especially needs your own words, not mine.

---

## App purpose

CareCard turns a photo of hospital discharge papers into a one-page plan:
what medicine to take and when, which warning signs mean go back to the
hospital, and when to follow up - in the patient's own language. Every
item on the card links back to the exact sentence it came from in the
original document, and anything that can't be traced back is dropped
before the patient ever sees it.

## Inspiration

*[This needs to be your own words - was there a personal experience, a
family member's hospital stay, something you noticed? Don't let me
invent a story here.]*

The problem is real and documented, not just a guess: in one study of ER
patients, 50.7% had severe gaps in understanding when to return to the
hospital, and 40.1% in understanding home care instructions (Engel et
al., *Academic Emergency Medicine*, 2012). Patients leave with dense
paper packets, often while still stressed or in pain, and forget most of
what they were told within minutes.

## Technical problems and how I solved them

**Problem: how do you stop an LLM from inventing something that isn't in
the document?** A system prompt telling the model to "only extract what's
written" isn't a guarantee - it's a request the model could still get
wrong. The real answer was a separate, deterministic check: the grounding
validator fuzzy-matches every extracted item's quoted source text against
the actual OCR text at the cited page and line. Anything that doesn't
match closely enough gets dropped before the patient ever sees it. The
"nothing is invented" claim isn't a prompt instruction - it's a
measurable, testable guarantee enforced in code.

**Problem: medication timing has to be exactly right, every time.** An
LLM could misread "BID" as "once daily" under the wrong prompt, and
getting that wrong is worse than most mistakes an app can make. So the
schedule parser is rule-based, not AI - it either matches a known sig
pattern (BID, TID, q6h, PRN, QHS...) or honestly says "check with your
pharmacist" instead of guessing. [Optional: mention the real bug you
found - e.g. if you add your own test cases and find one like the
"twice daily" vs "once daily" pattern-ordering bug documented in
AI_USAGE.md, that's a genuinely good story about why testing something
like this matters.]

**Problem: redacting PII before sending text to an AI model breaks
things the patient still needs.** Phone numbers, for instance, got
redacted along with real patient PII before extraction - correct, since
the AI model shouldn't see them - but that also meant a follow-up
appointment's callback number came back empty on the final card, quietly
breaking the "tap to call your doctor" feature. The fix: keep the
token-to-value mapping in memory (never written to disk) and restore
non-patient information like a clinic's phone number after extraction is
done, while still never showing the AI model the real number. This is a
concrete example of the tension between privacy and usability that a
real healthcare app has to resolve deliberately, not by accident.

**Problem: the demo's key visual moment - tapping a medicine to see its
exact source highlighted on the photo - needed pixel-accurate bounding
boxes to survive the whole pipeline.** Rotating a tilted photo to
straighten it (a normal preprocessing step) would have moved those boxes
out of alignment with the photo shown on screen. I chose to disable that
rotation for this version rather than ship a feature that looks broken
on a slightly tilted photo - a real example of trading one kind of
quality (OCR accuracy on tilted photos) for another (correctness of the
core feature).

## Biggest takeaway

*[Your own reflection goes here - but one honest thing worth including:
under real time pressure, I ended up asking Claude to write more of the
three "starred" components directly than the original plan called for,
instead of writing the first draft myself with Claude reviewing. That's
disclosed honestly in AI_USAGE.md rather than hidden. If judges ask about
this, the honest answer is: time pressure, logged accurately, and a
closer read-through of exactly those files before presenting so I could
actually explain them - not a claim that I wrote them from scratch.]*

A technical takeaway worth keeping regardless: testing against real
(if synthetic) data surfaced bugs that would never show up from reading
the code alone - a heading-detection bug where a warning sign that
happened to say "...or call 911" got mistaken for a new section header,
a date-parsing edge case, a redaction/usability tradeoff that only
becomes visible when you actually try to tap "call your doctor" and
nothing happens. Grounding-truth testing against an eval harness, not
just unit tests in isolation, is what caught these.

## What's in 2.0

- **Caregiver sync** - a shareable (not publicly linked) view an adult
  child or caregiver can check without the patient re-explaining
  everything.
- **Pharmacy pickup lookup** - connect prescriptions to the patient's
  actual pharmacy for refill status, instead of just a static schedule.
- **More languages**, with the back-translation accuracy check the
  original design called for but this build's time budget didn't reach.
- **RxNorm medication normalization** - generic/brand name lookup via the
  NLM's free API, cut from this build for time.
- **A real clinical pilot** - the eval harness here is 3 synthetic
  packets scored against a crude rule-based mock; the real test is
  whether this holds up against messy real-world discharge paperwork and
  actual patient feedback, ideally with a nurse or clinician reviewing
  the extracted cards for safety before any real deployment.
