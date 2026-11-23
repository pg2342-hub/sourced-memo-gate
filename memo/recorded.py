"""Record live agent and judge calls once, then replay them with no API key.

CI and the demo page grade recorded runs, so they are free and repeatable; the
record workflow (.github/workflows/record.yml) refreshes them with real calls.
Recordings are keyed by a hash of the input (agent) or the full prompt (judge);
repeated keys replay in the order they were recorded, one per run.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent / "recordings"


def key(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


class Tape:
    """An append-only JSONL file of (key, value) pairs, replayed in order per key."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._queues: dict[str, list[Any]] | None = None

    def append(self, k: str, value: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({"key": k, "value": value}, sort_keys=True) + "\n")

    def next(self, k: str) -> Any:
        if self._queues is None:
            self._queues = defaultdict(list)
            if self.path.exists():
                for line in self.path.read_text().splitlines():
                    if line.strip():
                        row = json.loads(line)
                        self._queues[row["key"]].append(row["value"])
        queue = self._queues.get(k)
        if not queue:
            raise LookupError(f"no recording left for key {k} in {self.path.name}; run the record workflow")
        return queue.pop(0)


def recording_agent(agent: Callable[[dict], dict], tape: Tape) -> Callable[[dict], dict]:
    def call(case_input: dict) -> dict:
        record = agent(case_input)
        tape.append(key(case_input), record)
        return record

    return call


def replay_agent(tape: Tape) -> Callable[[dict], dict]:
    return lambda case_input: tape.next(key(case_input))


def recording_judge(judge: Callable[[str], Any], tape: Tape) -> Callable[[str], Any]:
    from golive_gate import JudgeReply

    def call(prompt: str) -> JudgeReply:
        reply = judge(prompt)
        if isinstance(reply, str):
            reply = JudgeReply(reply)
        tape.append(key(prompt), {"text": reply.text, "cost_usd": reply.cost_usd})
        return reply

    return call


def replay_judge(tape: Tape) -> Callable[[str], Any]:
    from golive_gate import JudgeReply

    def call(prompt: str) -> JudgeReply:
        row = tape.next(key(prompt))
        return JudgeReply(row["text"], row["cost_usd"])

    return call
