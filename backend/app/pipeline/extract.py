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
of that line (copy it character-for-character, don't paraphrase it).
4. If you cannot find an exact source line for something, don't extract it.

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


EXTRACTION_TOOL = {
    "name": "record_discharge_card",
    "description": "Records the structured discharge card extracted from the document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "diagnosis_plain": _item_schema({"text": {"type": "string"}}, ["text"]),
            "medications": {
                "type": "array",
                "items": _item_schema(
                    {
                        "name_as_written": {"type": "string"},
                        "dose": {"type": "string"},
                        "route": {"type": "string"},
                        "frequency_as_written": {"type": "string"},
                        "duration": {"type": "string"},
                        "purpose": {"type": "string"},
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
                        "text": {"type": "string"},
                        "urgency": {"type": "string", "enum": ["call_911", "go_to_ER", "call_doctor"]},
                    },
                    ["text", "urgency"],
                ),
            },
            "follow_up_appointments": {
                "type": "array",
                "items": _item_schema(
                    {
                        "with": {"type": "string"},
                        "when": {"type": "string"},
                        "phone": {"type": "string"},
                    }
                ),
            },
            "home_care_instructions": {
                "type": "array",
                "items": _item_schema({"text": {"type": "string"}}, ["text"]),
            },
            "activity_and_diet_limits": {
                "type": "array",
                "items": _item_schema({"text": {"type": "string"}}, ["text"]),
            },
        },
    },
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
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
