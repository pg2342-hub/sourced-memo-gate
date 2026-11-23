"""The synthesis agent: one Claude call per memo section, returned as structured JSON.

The model reads the whole source library (cached across calls) and writes the section. The checks in
evals/ then grade it; the model is never asked to grade itself.
"""

from __future__ import annotations

import json
import time
from typing import Any

from .prompts import system_prompt, user_message
from .schema import SECTION_SCHEMA

MODEL = "claude-opus-5-5"
EFFORT = "low"
# USD per million tokens (input, output), first-party list prices.
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}


class ClaudeAnalyst:
    """Calls Claude through the Anthropic SDK. Reads the key from ANTHROPIC_API_KEY."""

    def __init__(self, version: str = "v2", model: str = MODEL, effort: str = EFFORT, client: Any = None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(max_retries=5)
        self.client = client
        self.version = version
        self.model = model
        self.effort = effort
        self._system = system_prompt(version)

    def __call__(self, case_input: dict) -> dict:
        start = time.perf_counter()
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": SECTION_SCHEMA}},
            system=[{"type": "text", "text": self._system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_message(case_input)}],
        )
        latency = time.perf_counter() - start
        if response.stop_reason == "refusal":
            raise RuntimeError("the model declined this request")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("the section was cut off at max_tokens")
        text = next(b.text for b in response.content if b.type == "text")
        section = json.loads(text)
        section["_meta"] = {
            "model": getattr(response, "model", self.model),
            "prompt": self.version,
            "cost_usd": self.cost(response),
            "latency_s": round(latency, 3),
        }
        return section

    def cost(self, response: Any) -> float:
        price = PRICES.get(getattr(response, "model", self.model)) or PRICES.get(self.model, (0.0, 0.0))
        usage = response.usage
        written = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        tokens_in = (usage.input_tokens or 0) + written * 1.25 + cached * 0.05
        return (tokens_in * price[0] + (usage.output_tokens or 0) * price[1]) / 1e6
