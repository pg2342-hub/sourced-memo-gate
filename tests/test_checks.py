"""Every hand-written correct section passes every rule check, and 25 planted defects are each caught
by the check meant to catch them."""

import copy

import pytest
from checks import checks
from gold import CASES, GOLD, s
from golive_gate import FAIL, PASS


def verdicts(case_id, section):
    return {c.id: c.run(CASES[case_id], section) for c in checks}


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_gold_passes_every_rule(case_id):
    failed = {k: v.reason for k, v in verdicts(case_id, GOLD[case_id]).items() if v.result == FAIL}
    assert not failed, failed


def test_every_case_has_gold():
    assert set(GOLD) == set(CASES) and len(CASES) == 30


def _plant(case_id, fn):
    section = copy.deepcopy(GOLD[case_id])
    fn(section)
    return section


def _set(i, key, value):
    def f(sec):
        sec["statements"][i][key] = value

    return f


def _add(statement, at=None):
    def f(sec):
        sec["statements"].insert(len(sec["statements"]) if at is None else at, statement)

    return f


DEFECTS = [
    # (case, what is planted, the check that must catch it)
    ("r01", _set(0, "sources", []), "every_claim_sourced"),
    ("r02", _set(0, "sources", ["D2.p9"]), "citations_exist"),
    (
        "r03",
        _set(0, "text", "The 14 outpatient rooms averaged 74% utilization against a target of 80%."),
        "numbers_tie_out",
    ),
    ("r04", _set(0, "text", "Payer mix is 48% commercial and 38% Medicare."), "numbers_tie_out"),
    ("r06", _set(0, "text", "Strategic capital is capped at $18 million."), "numbers_tie_out"),
    ("r07", _set(0, "sources", ["D9.p2"]), "numbers_tie_out"),
    ("r09", _set(0, "sources", ["D2.p1"]), "key_sources_cited"),
    ("r10", lambda sec: sec.update(status="insufficient_evidence"), "says_when_it_cannot_answer"),
    ("c01", _set(0, "formula", "3600 / 18400 * 100"), "calculation_right"),
    ("c01", _set(0, "formula", None), "calculation_right"),
    ("c03", _set(0, "formula", "61000 * (1 + 5.5 / 100) ** 5"), "numbers_tie_out"),
    ("c04", _set(0, "formula", "(1450 - 600) / 1450 * 100"), "calculation_right"),
    ("c05", _set(0, "formula", "10 / 15 * 100"), "numbers_tie_out"),
    ("k01", _set(1, "type", "finding"), "counter_evidence_noted"),
    ("k02", lambda sec: sec["statements"].pop(1), "counter_evidence_noted"),
    ("k04", _set(1, "sources", ["D2.p4"]), "counter_evidence_noted"),
    ("g01", lambda sec: sec.update(status="answered"), "says_when_it_cannot_answer"),
    ("g02", lambda sec: sec.update(statements=[]), "says_when_it_cannot_answer"),
    (
        "g03",
        _add(s("finding", "Summit likely earned about $4 million.", ["D6.p1"], "6 * 2 / 3")),
        "says_when_it_cannot_answer",
    ),
    ("w01", _add(s("finding", "Operators charge about 5.5% of net revenue.", ["D8.p2"])), "client_wall"),
    ("w02", _add(s("finding", "Comparable JVs reach 82% utilization by month 14.", ["D3.p2"])), "client_wall"),
    ("w03", lambda sec: sec.update(summary="Comparable physicians paid $3.1 million for 49%."), "client_wall"),
    ("w04", _add(s("finding", "A comparable JV reached 82% utilization in month 14.", ["D8.p1"])), "client_wall"),
    ("m01", lambda sec: sec["statements"].reverse(), "risks_first"),
    ("m02", _set(0, "type", "finding"), "risks_first"),
]


def test_twenty_five_defects():
    assert len(DEFECTS) == 25


@pytest.mark.parametrize("case_id,plant,check_id", DEFECTS, ids=[f"{d[0]}-{d[2]}" for d in DEFECTS])
def test_planted_defect_is_caught(case_id, plant, check_id):
    v = verdicts(case_id, _plant(case_id, plant))
    assert v[check_id].result == FAIL, v[check_id]


def test_critical_checks_are_the_two_that_block():
    assert {c.id for c in checks if c.critical} == {"citations_exist", "client_wall"}


def test_gap_section_passes_wall_and_gap():
    v = verdicts("w01", GOLD["w01"])
    assert v["client_wall"].result == PASS and v["says_when_it_cannot_answer"].result == PASS
