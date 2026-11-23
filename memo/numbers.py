"""Find the numbers in a sentence and decide whether they tie out to a source.

"$22.8 million", "22.8M", "18,400", "62%" and "4.5%" all become floats. Years (1900-2100) are
skipped, because a date is not a figure that has to tie out. A whole number of 1,000 or more
with trailing zeros ("about 76,000") is read as rounded to that place only when the sentence says so
("about", "roughly", ...) or the figure was computed. A number ties out when a cited paragraph
contains the same value, allowing for the rounding the sentence itself shows.
"""

from __future__ import annotations

import ast
import math
import operator
import re

_NUM = re.compile(
    r"(?<![\w.])\$?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s*(?:%|percent|million|billion|thousand|[mMbBkK]\b))?"
)
_SCALE = {"million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9, "thousand": 1e3, "k": 1e3}
_APPROX = re.compile(r"\b(about|approximately|roughly|around|nearly|almost|some|close to|~)\W*$", re.I)


def figures(text: str, scaled: bool = True, rounded_ok: bool = False) -> list[tuple[float, int, str]]:
    """(value, decimals shown, kind) for each figure in text, years excluded.

    kind is "%" for a percentage, "$" for a scaled amount ("$9 million") and "" otherwise.
    With scaled=False, "$9 million" reads as 9, the way a formula writes it.
    """
    out = []
    for m in _NUM.finditer(text):
        raw, unit = m.group(1).replace(",", ""), (m.group(2) or "").strip().lower()
        value = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        if not unit and "." not in raw and 1900 <= value <= 2100:
            continue  # a year
        approx = rounded_ok or bool(_APPROX.search(text[max(0, m.start() - 16) : m.start()]))
        if not unit and "." not in raw and value >= 1000 and approx:
            decimals = -(len(raw) - len(raw.rstrip("0")))  # "about 76,000" is rounded to the thousand
        kind = "%" if unit in ("%", "percent") else "$" if unit in _SCALE else ""
        if unit in _SCALE and scaled:
            value *= _SCALE[unit]
            decimals -= int(math.log10(_SCALE[unit]))
        out.append((value, decimals, kind))
    return out


def numbers(text: str, scaled: bool = True, rounded_ok: bool = False) -> list[tuple[float, int]]:
    """(value, decimals shown) for each figure in text, years excluded."""
    return [(v, d) for v, d, _ in figures(text, scaled, rounded_ok)]


def matches(value: float, decimals: int, candidates: list[float]) -> bool:
    """True if value equals a candidate, or equals it once rounded half-up to the precision shown."""
    half = 0.5 * 10 ** (-decimals)
    return any(abs(value - c) <= half * (1 + 1e-9) + 1e-9 for c in candidates)


_WORDS = {
    w: float(i)
    for i, ws in enumerate(
        [
            (),
            ("one", "first", "single"),
            ("two", "second", "twice"),
            ("three", "third"),
            ("four", "fourth"),
            ("five", "fifth"),
            ("six", "sixth"),
            ("seven",),
            ("eight",),
            ("nine",),
            ("ten",),
            ("eleven",),
            ("twelve",),
        ]
    )
    for w in ws
}
_WORD_RE = re.compile(r"\b(" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")\b", re.I)
_MONTHS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:to|-|–)?\s*(?:(\d+(?:\.\d+)?)\s*)?months?\b", re.I)


def derived(text: str) -> list[float]:
    """Figures a source states in words or other units: "four-room" is 4, "18 to 24 months" is 1.5 to 2 years."""
    out = [_WORDS[w.lower()] for w in _WORD_RE.findall(text)]
    for m in _MONTHS.finditer(text):
        out += [float(g) / 12 for g in m.groups() if g]
    return out


def differences(text: str) -> list[float]:
    """Gaps between two figures of the same kind in text, for "a 3-point difference" between 55% and 58%."""
    fs = figures(text)
    return [abs(a[0] - b[0]) for i, a in enumerate(fs) for b in fs[i + 1 :] if a[2] == b[2]]


def scaled_results(result: float) -> list[float]:
    """A formula result as the sentence may state it: 6 (million) as $6 million, 0.43 as 43%."""
    return [result * f for f in (1, 100, 1e3, 1e6, 1e9)]


def input_forms(x: float) -> list[float]:
    """The source figure a formula input may stand for: 0.34 or 34 for 34%, 1.045 or 0.045 for 4.5%."""
    return [x, x * 100, x / 100, (x - 1) * 100, (1 - x) * 100]


def values(text: str) -> list[float]:
    return [v for v, _ in numbers(text)]


def face_values(text: str) -> list[float]:
    """Every figure as written and as scaled, so "$9 million" offers both 9 and 9,000,000."""
    return [v for v, _ in numbers(text)] + [v for v, _ in numbers(text, scaled=False)]


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def evaluate(formula: str) -> float:
    """Evaluate plain arithmetic (+ - * / ** and parentheses) and nothing else."""

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.operand))
        raise ValueError(f"not plain arithmetic: {ast.dump(node)[:80]}")

    return walk(ast.parse(formula.replace(",", ""), mode="eval"))


def formula_inputs(formula: str) -> list[float]:
    return [float(t) for t in re.findall(r"\d+(?:\.\d+)?", formula.replace(",", ""))]
