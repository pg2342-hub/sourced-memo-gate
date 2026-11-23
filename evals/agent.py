"""Agents for golive-gate. golive calls each with case.input and grades what comes back.

- recorded_v2 / recorded_v1: replay the last live run of each prompt version (no key; CI and the demo)
- live_v2 / live_v1:         call Claude now and record each section to recordings/ (needs ANTHROPIC_API_KEY)
- extractive_agent:          the no-model baseline the gate must block
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from golive_gate import Response

from memo.baseline import extractive_agent as _extractive
from memo.recorded import ROOT, Tape, recording_agent, replay_agent

TAPES = {"v1": Tape(ROOT / "agent_v1.jsonl"), "v2": Tape(ROOT / "agent_v2.jsonl")}
_live = {}


def _as_response(section):
    return Response(section, cost_usd=section.get("_meta", {}).get("cost_usd", 0.0))


def _recorded(version):
    return lambda case_input: _as_response(replay_agent(TAPES[version])(case_input))


def _live_agent(version):
    def call(case_input):
        if version not in _live:  # created on first use, so importing this file needs no key
            from memo.agent import ClaudeAnalyst

            _live[version] = recording_agent(ClaudeAnalyst(version), TAPES[version])
        return _as_response(_live[version](case_input))

    return call


recorded_v1, recorded_v2 = _recorded("v1"), _recorded("v2")
live_v1, live_v2 = _live_agent("v1"), _live_agent("v2")


def extractive_agent(case_input):
    return _extractive(case_input)
