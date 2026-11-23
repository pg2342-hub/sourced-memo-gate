"""The shape of one memo section, enforced with structured output on the live agent."""

STATEMENT_TYPES = ("finding", "risk", "counter_evidence", "gap")

SECTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "summary", "statements"],
    "properties": {
        "status": {"type": "string", "enum": ["answered", "insufficient_evidence"]},
        "summary": {"type": "string"},
        "statements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "text", "sources", "formula"],
                "properties": {
                    "type": {"type": "string", "enum": list(STATEMENT_TYPES)},
                    "text": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "formula": {"type": ["string", "null"]},
                },
            },
        },
    },
}


def valid(section) -> tuple[bool, str]:
    """A light shape check for outputs that did not come through structured output (baseline, tests)."""
    if not isinstance(section, dict):
        return False, "output is not an object"
    for key in ("status", "summary", "statements"):
        if key not in section:
            return False, f"missing {key}"
    if section["status"] not in ("answered", "insufficient_evidence"):
        return False, f"unknown status {section['status']!r}"
    for i, s in enumerate(section["statements"]):
        if s.get("type") not in STATEMENT_TYPES:
            return False, f"statement {i + 1} has unknown type {s.get('type')!r}"
        if not isinstance(s.get("sources"), list) or not isinstance(s.get("text"), str):
            return False, f"statement {i + 1} is missing text or sources"
    return True, ""
