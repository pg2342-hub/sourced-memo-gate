import pytest

from memo import numbers as N


def test_parses_money_percent_and_commas():
    assert N.values("$22.8 million, 18,400 cases, 62%, 4.5%") == [22.8e6, 18400, 62, 4.5]


def test_skips_years():
    assert N.values("from 2022 to 2025, 1,450 joints") == [1450]


def test_face_values_offer_both_scales():
    assert 9.0 in N.face_values("$9 million") and 9e6 in N.face_values("$9 million")


@pytest.mark.parametrize(
    "value,decimals,cands,ok",
    [
        (43, 0, [42.93], True),
        (22.8e6, -5, [22.8e6], True),
        (76000, -3, [76017.1], True),
        (44, 0, [42.93], False),
        (58, 0, [55], False),
    ],
)
def test_matches_respects_shown_rounding(value, decimals, cands, ok):
    assert N.matches(value, decimals, cands) is ok


def test_evaluate_only_arithmetic():
    assert N.evaluate("61000 * (1 + 4.5 / 100) ** 5") == pytest.approx(76017.1, rel=1e-4)
    with pytest.raises(ValueError):
        N.evaluate("__import__('os').system('true')")
