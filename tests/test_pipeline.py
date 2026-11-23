"""The live path end to end with a fake Anthropic client, then the same run replayed from the recording.

The fake agent returns the hand-written gold section and the judge always passes, so both runs must
reach GO, and the replay must make no API calls at all.
"""

import json
import sys
import types

import agent as agent_mod
import judge_checks
import pytest
from gold import CASES, GOLD
from golive_gate import Gate, evaluate, load_cases, run_eval

from memo import prompts
from memo.recorded import Tape


class FakeMessages:
    def __init__(self):
        self.by_user = {prompts.user_message(c.input): GOLD[c.id] for c in CASES.values()}
        self.calls = 0
        self.systems = []

    def create(self, **kw):
        self.calls += 1
        if "system" in kw:
            self.systems.append(kw["system"])
            text = json.dumps(self.by_user[kw["messages"][0]["content"]])
        else:
            text = "VERDICT: PASS - meets the criterion"
        usage = types.SimpleNamespace(
            input_tokens=300, output_tokens=200, cache_creation_input_tokens=0, cache_read_input_tokens=4000
        )
        return types.SimpleNamespace(
            model=kw["model"],
            stop_reason="end_turn",
            content=[types.SimpleNamespace(type="text", text=text)],
            usage=usage,
        )


def test_live_then_replay(tmp_path, monkeypatch):
    fake = FakeMessages()
    client = types.SimpleNamespace(beta=types.SimpleNamespace(messages=fake))
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=lambda **kw: client))
    monkeypatch.setenv("GOLIVE_LIVE", "1")
    tape = Tape(tmp_path / "agent_v2.jsonl")
    monkeypatch.setitem(agent_mod.TAPES, "v2", tape)
    monkeypatch.setattr(agent_mod, "_live", {})
    monkeypatch.setitem(judge_checks.TAPES, "v2", Tape(tmp_path / "judge_v2.jsonl"))
    monkeypatch.setattr(judge_checks, "_judges", {})

    cases = load_cases("evals/cases.yml")
    gate = Gate.load("evals/gate.yml")
    live = run_eval(agent_mod.live_v2, cases, judge_checks.make_checks("v2"), runs=2)
    assert evaluate(gate, live).decision == "go"
    assert live.total_cost_usd > 0 and live.total_judge_cost_usd > 0
    # the library is sent once per call as a cached system block, and v2 carries the house rules
    assert fake.systems[0][0]["cache_control"] == {"type": "ephemeral"}
    assert "Client walls" in fake.systems[0][0]["text"]
    live_calls = fake.calls

    monkeypatch.delenv("GOLIVE_LIVE")
    monkeypatch.setitem(agent_mod.TAPES, "v2", Tape(tmp_path / "agent_v2.jsonl"))
    monkeypatch.setitem(judge_checks.TAPES, "v2", Tape(tmp_path / "judge_v2.jsonl"))
    monkeypatch.setattr(judge_checks, "_judges", {})
    replay = run_eval(agent_mod.recorded_v2, cases, judge_checks.make_checks("v2"), runs=2)
    assert fake.calls == live_calls  # no API calls on replay
    assert evaluate(gate, replay).decision == "go"


def test_baseline_is_blocked():
    from checks import checks

    result = run_eval(agent_mod.extractive_agent, load_cases("evals/cases.yml"), checks, runs=1)
    outcome = evaluate(Gate.load("evals/gate.yml"), result)
    assert outcome.decision == "no-go"


def test_wall_notice_is_in_the_library_but_v1_has_no_rules():
    v1, v2 = prompts.system_prompt("v1"), prompts.system_prompt("v2")
    assert 'engagement="northgate"' in v1 and "Do not cite or reuse" in v1  # the file itself carries its label
    assert "Client walls" not in v1 and "Client walls" in v2


def test_changed_prompt_finds_no_recording(tmp_path):
    from memo.recorded import Tape, recording_agent, replay_agent

    tape = Tape(tmp_path / "t.jsonl")
    recording_agent(lambda x: {"ok": 1}, tape, "prompt-a")({"request": "q"})
    assert replay_agent(Tape(tape.path), "prompt-a")({"request": "q"}) == {"ok": 1}
    with pytest.raises(LookupError):
        replay_agent(Tape(tape.path), "prompt-b")({"request": "q"})
