"""Find the numbers in a sentence and decide whether they tie out to a source.

"$22.8 million", "22.8M", "18,400", "62%" and "4.5%" all become floats. Years (1900-2100) are
skipped, because a date is not a figure that has to tie out. A whole number of 1,000 or more
with trailing zeros ("76,000") is read as rounded to that place. A number ties out when a cited
paragraph contains the same value, allowing for the rounding the sentence itself shows.
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


def numbers(text: str, scaled: bool = True) -> list[tuple[float, int]]:
    """(value, decimals shown) for each figure in text, years excluded.

    With scaled=False, "$9 million" reads as 9, the way a formula writes it.
    """
    out = []
    for m in _NUM.finditer(text):
        raw, unit = m.group(1).replace(",", ""), (m.group(2) or "").strip().lower()
        value = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        if not unit and "." not in raw and 1900 <= value <= 2100:
            continue  # a year
        if not unit and "." not in raw and value >= 1000:
            decimals = -(len(raw) - len(raw.rstrip("0")))  # "76,000" is rounded to the thousand
        if unit in _SCALE and scaled:
            value *= _SCALE[unit]
            decimals -= int(math.log10(_SCALE[unit]))
        out.append((value, decimals))
    return out


def matches(value: float, decimals: int, candidates: list[float]) -> bool:
    """True if value equals a candidate, or equals it once rounded to the precision shown."""
    for c in candidates:
        if math.isclose(value, c, rel_tol=1e-9, abs_tol=1e-9):
            return True
        if round(c, decimals) == round(value, decimals) and abs(value - c) <= 0.5 * 10 ** (-decimals) + 1e-9:
            return True
    return False


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
