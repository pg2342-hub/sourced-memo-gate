"""Rule checks plus two Claude judge checks for what a rule cannot state exactly.

A rule can tell that a statement cites D3.p1 and that its numbers appear there. It cannot tell
whether the paragraph actually says what the statement claims. The judge does, one statement
set and its cited paragraphs per call.

The judge runs live (and records each reply) when GOLIVE_LIVE=1, and replays the recorded
replies otherwise, so CI and the demo page need no API key.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checks import PARAS
from checks import checks as rule_checks
from golive_gate import NA, CheckSet, judge_check

from memo.recorded import ROOT, Tape, recording_judge, replay_judge

TAPES = {"v1": Tape(ROOT / "judge_v1.jsonl"), "v2": Tape(ROOT / "judge_v2.jsonl")}
_judges = {}


def judge_for(version):
    """One judge (and one recording) per prompt version, so the two runs replay independently."""

    def judge(prompt):
        if version not in _judges:
            if os.environ.get("GOLIVE_LIVE") == "1":
                from golive_gate import ClaudeJudge

                TAPES[version].clear()
                _judges[version] = recording_judge(ClaudeJudge(model="claude-opus-5-5", effort="low"), TAPES[version])
            else:
                _judges[version] = replay_judge(TAPES[version])
        return _judges[version](prompt)

    return judge


def _request(case):
    return f"Memo section request: {case.input['request']}"


def _with_sources(out):
    # fixed order and wording, so a replayed section renders the same prompt as the live one
    lines = []
    for i, s in enumerate(out["statements"], 1):
        lines.append(f"Statement {i} ({s['type']}): {s['text']}")
        for pid in s["sources"]:
            lines.append(f"  cited {pid}: {PARAS.get(pid, '(no such paragraph)')}")
    return "\n".join(lines) or "(no statements)"


def _summary(out):
    return f"Status: {out['status']}\nSummary: {out['summary']}"


SUPPORTED = (
    "Each statement says only what its cited paragraphs support: no claim, figure or attribution goes "
    "beyond them, and nothing is stated as fact that a source gives only as an estimate or an opinion. "
    "Gap statements, which say what the sources do not cover, pass."
)
ANSWERS = (
    "The summary's first sentence answers the request directly, or says plainly that the engagement's "
    "sources cannot answer it."
)


def make_checks(version):
    """The rule checks plus the two judge checks, judged (or replayed) for one prompt version."""
    judge = judge_for(version)
    supported = judge_check(
        "claims_supported", SUPPORTED, judge=judge, render_case=_request, render_output=_with_sources
    )
    answers = judge_check("answers_the_question", ANSWERS, judge=judge, render_case=_request, render_output=_summary)
    cs = CheckSet(rule_checks)

    @cs.check("claims_supported", text=SUPPORTED)
    def claims_supported(case, out):
        if not out["statements"]:
            return NA
        return supported.run(case, out)

    @cs.check("answers_the_question", text=ANSWERS)
    def answers_the_question(case, out):
        return answers.run(case, out)

    return cs


checks_v1 = make_checks("v1")
checks_v2 = make_checks("v2")
