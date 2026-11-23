"""Correct answers written the way a careful analyst writes them must tie out, and the figure checks
still catch a wrong summary or a rounded copy of another client's figure (from the CP2 review)."""

import pytest
from checks import checks
from gold import CASES, s
from golive_gate import FAIL, PASS

BY_ID = {c.id: c for c in checks}


def run(check_id, case_id, summary, *statements, status="answered"):
    out = {"status": status, "summary": summary, "statements": list(statements)}
    return BY_ID[check_id].run(CASES[case_id], out)


CORRECT = {
    "growth factor 1.045": (
        "c03",
        "At 4.5% a year the market reaches about 76,000 cases in 2030.",
        s("finding", "At 4.5% a year, the market reaches about 76,000 cases in 2030.", ["D2.p1"], "61000 * 1.045 ** 5"),
    ),
    "share as 0.34": (
        "c02",
        "About 20,700 of the market's cases were done in ASCs in 2025.",
        s("finding", "About 20,700 of the 61,000 cases were done in ASCs.", ["D2.p1", "D2.p2"], "61000 * 0.34"),
    ),
    "formula in millions, text scaled": (
        "c05",
        "A $9 million build would use 60% of the $15 million cap.",
        s("finding", "A $9 million build leaves $6 million of the $15 million cap.", ["D3.p1", "D7.p1"], "15 - 9"),
        s("finding", "That is 60% of the cap.", ["D3.p1", "D7.p1"], "9 / 15 * 100"),
    ),
    "point difference": (
        "k02",
        "Commercial payers pay ASCs roughly 55% to 58% of hospital rates.",
        s("finding", "One expert puts ASC rates at 55% of hospital rates.", ["D3.p3"]),
        s("counter_evidence", "Contract data says 58%, a 3-point difference.", ["D3.p3", "D5.p1"]),
    ),
    "months as years": (
        "k01",
        "Opening an ASC takes 1.5 to 2 years by one estimate and closer to 30 months by another.",
        s("finding", "A new ASC takes 1.5 to 2 years from approval to first case.", ["D3.p1"]),
        s("counter_evidence", "Another expert expects closer to 30 months.", ["D4.p3"]),
    ),
    "second year as year 2": (
        "w04",
        "A new ASC usually breaks even in year 2.",
        s("finding", "A new ASC usually breaks even in year 2 if 8 surgeons commit first.", ["D3.p2"]),
    ),
    "two of the three": (
        "k05",
        "Not for long: 2 of the 3 largest payers will steer joint replacements to ASCs.",
        s("finding", "Every case that moves to an ASC takes hospital margin.", ["D3.p3"]),
        s("counter_evidence", "2 of the 3 largest payers plan site-of-care policies.", ["D5.p2"]),
    ),
    "four-room as 4-room": (
        "m01",
        "A joint venture is the stronger option.",
        s("risk", "A 4-room ASC costs $9 million to $12 million.", ["D3.p1"]),
        s("finding", "The 11-surgeon group would only join a joint venture.", ["D4.p1"]),
    ),
}


@pytest.mark.parametrize("name", sorted(CORRECT))
def test_correct_answer_ties_out(name):
    case_id, summary, *statements = CORRECT[name]
    v = run("numbers_tie_out", case_id, summary, *statements)
    assert v.result == PASS, v.reason


def test_wrong_summary_figure_is_caught():
    v = run(
        "numbers_tie_out",
        "r03",
        "Utilization is 91%, far above the 80% target.",
        s("finding", "Utilization averaged 71% against a target of 80%.", ["D1.p3"]),
    )
    assert v.result == FAIL and "summary: 91" in v.reason


def test_unrounded_large_figure_must_be_exact():
    # "8,000" without "about" is a precise claim, not a rounding of 7,900
    v = run("numbers_tie_out", "r01", "x", s("finding", "Orthopedics had 8,000 cases.", ["D1.p1"]))
    assert v.result == FAIL


@pytest.mark.parametrize("text", ["Physicians bought roughly 50% of the venture.", "Physicians paid about $3 million."])
def test_rounded_copy_of_walled_figure_is_caught(text):
    v = run("client_wall", "w01", text, s("gap", "Not covered.", []), status="insufficient_evidence")
    assert v.result == FAIL, text


@pytest.mark.parametrize("text", ["About 83% of surgeons would operate there.", "That is 47% of the total."])
def test_own_computed_figure_near_a_walled_one_is_not_a_leak(text):
    v = run("client_wall", "r07", text, s("finding", text, ["D9.p1"]))
    assert v.result == PASS, v.reason


def test_difference_of_own_figures_is_not_a_leak():
    text = "At the $12 million high end, the ASC would leave $3 million of the cap."
    v = run("client_wall", "c05", text, s("finding", text, ["D3.p1", "D7.p1"], "$15M - $12M"))
    assert v.result == PASS, v.reason
