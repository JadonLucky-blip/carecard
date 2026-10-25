"""
Component 4: structured extraction via Claude.

Sends the already-redacted OCR transcript to Claude with a forced tool
call, so the response is guaranteed to match CareCard's schema instead
of hoping the model formats JSON correctly on its own. Every item must
carry an exact source quote - that's what the grounding validator
(component 5, written separately) checks before anything reaches the
patient.
"""
import anthropic

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from app.schema import ExtractedCard

SYSTEM_PROMPT = """You are extracting structured information from a hospital \
discharge document that has already had personal identifying information \
replaced with tokens like [NAME_1] and [MRN]. The document text is given to \
you as numbered lines in the form "[page P line L] text".

Rules, followed exactly:
1. Extract only what is written in the document. Never add medical advice, \
never infer a warning sign or instruction that isn't explicitly stated.
2. If a field isn't present in the document, omit it or leave its list \
empty. Do not guess or fill in a plausible-sounding value.
3. Every extracted item MUST include a "source" object with the exact page \
number, the line number(s) it came from, and "quote": the exact substring \
of that line (copy it character-for-character, don't paraphrase it). The \
"quote" field is always the verbatim original text, never simplified.
4. If you cannot find an exact source line for something, don't extract it.
5. For "text" and "purpose" fields specifically (diagnosis, warning signs, \
home care instructions, activity/diet limits, a medication's purpose): \
rewrite them in plain language at about a 6th-grade reading level - short \
sentences, everyday words instead of medical jargon, one idea per item. \
Never change what it means or add anything not in the source - only \
simplify how it's worded. A patient can always see the original exact \
wording by tapping the item, via the "quote" field, so simplifying "text" \
never loses information.
6. Do NOT simplify name_as_written, dose, route, frequency_as_written, or \
duration for medications - keep those exactly as written, since a separate \
rule-based system parses them and needs the original abbreviations (e.g. \
"BID", "PRN", "q6h") to work correctly.

Call the record_discharge_card tool exactly once with everything you found."""

SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "page": {"type": "integer"},
        "lines": {"type": "array", "items": {"type": "integer"}},
        "quote": {"type": "string", "description": "Exact substring copied from the source line(s)."},
    },
    "required": ["page", "lines", "quote"],
}


def _item_schema(extra_properties: dict, required_extra: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": {**extra_properties, "source": SOURCE_SCHEMA},
        "required": ["source"] + (required_extra or []),
    }


_PLAIN_LANGUAGE_DESC = (
    "Plain-language rewrite at about a 6th-grade reading level (short "
    "sentences, everyday words, same meaning) - NOT a verbatim quote. "
    "The exact original wording belongs in this item's source.quote instead."
)
_AS_WRITTEN_DESC = "Keep exactly as written in the document - do not simplify or paraphrase."

EXTRACTION_TOOL = {
    "name": "record_discharge_card",
    "description": "Records the structured discharge card extracted from the document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "diagnosis_plain": _item_schema(
                {"text": {"type": "string", "description": _PLAIN_LANGUAGE_DESC}}, ["text"]
            ),
            "medications": {
                "type": "array",
                "items": _item_schema(
                    {
                        "name_as_written": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "dose": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "route": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "frequency_as_written": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "duration": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "purpose": {"type": "string", "description": _PLAIN_LANGUAGE_DESC},
                        "new_changed_or_stopped": {
                            "type": "string",
                            "enum": ["new", "changed", "stopped", "continue"],
                        },
                    },
                    ["name_as_written"],
                ),
            },
            "return_now_warning_signs": {
                "type": "array",
                "items": _item_schema(
                    {
                        "text": {"type": "string", "description": _PLAIN_LANGUAGE_DESC},
                        "urgency": {"type": "string", "enum": ["call_911", "go_to_ER", "call_doctor"]},
                    },
                    ["text", "urgency"],
                ),
            },
            "follow_up_appointments": {
                "type": "array",
                "items": _item_schema(
                    {
                        "with": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "when": {"type": "string", "description": _AS_WRITTEN_DESC},
                        "phone": {"type": "string", "description": _AS_WRITTEN_DESC},
                    }
                ),
            },
            "home_care_instructions": {
                "type": "array",
                "items": _item_schema({"text": {"type": "string", "description": _PLAIN_LANGUAGE_DESC}}, ["text"]),
            },
            "activity_and_diet_limits": {
                "type": "array",
                "items": _item_schema({"text": {"type": "string", "description": _PLAIN_LANGUAGE_DESC}}, ["text"]),
            },
        },
    },
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # base_url is pinned explicitly, on purpose: the Anthropic SDK
        # reads ANTHROPIC_BASE_URL from the environment if present, and
        # this dev machine has some other tool configured with that env
        # var pointing at a third-party proxy (discovered while testing -
        # see AI_USAGE.md). Without this, requests meant for the real
        # Claude API could silently go somewhere else entirely.
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, base_url="https://api.anthropic.com")
    return _client


def extract_card(redacted_transcript: str) -> ExtractedCard:
    response = _get_client().messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_discharge_card"},
        messages=[{"role": "user", "content": redacted_transcript}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to process this document.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude's response was cut off (too long) - try fewer or shorter photos.")

    tool_use = next((block for block in response.content if block.type == "tool_use"), None)
    if tool_use is None:
        raise RuntimeError("Claude didn't return structured data - please try again.")

    return ExtractedCard.model_validate(tool_use.input)
