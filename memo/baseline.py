"""A no-model baseline: pull the two paragraphs that share the most words with the request.

It cites real paragraphs and copies their numbers, so it looks sourced. It never notices a
conflict, never admits a gap, and has no idea which documents belong to another client.
The gate must block it.
"""

from __future__ import annotations

import re

from .corpus import load

_STOP = set(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "has",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "what",
        "which",
        "who",
        "why",
        "with",
        "would",
        "should",
        "could",
    ]
)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP and len(w) > 2}


def extractive_agent(case_input: dict) -> dict:
    paras = load().paragraphs
    want = _words(case_input["request"])
    ranked = sorted(paras, key=lambda pid: (-len(want & _words(paras[pid])), pid))[:2]
    statements = [{"type": "finding", "text": paras[pid], "sources": [pid], "formula": None} for pid in ranked]
    return {"status": "answered", "summary": paras[ranked[0]], "statements": statements}
