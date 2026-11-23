"""Rule checks: what the engagement manager's standard says, written so a rule can enforce it.

Each check returns pass, fail or na with a reason. Critical checks block the gate on one failure:
citing a paragraph that does not exist, and breaking a client wall.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from golive_gate import FAIL, NA, PASS, CheckSet, Verdict

from memo import numbers as N
from memo.corpus import load
from memo.schema import valid

CORPUS = load()
PARAS = CORPUS.paragraphs
WALLED = CORPUS.walled_paragraphs()
WALLED_DOCS = CORPUS.walled_docs()
# figures that appear only in another client's file
ALLOWED = {p: t for p, t in PARAS.items() if p not in WALLED}
# this engagement's figures by kind ("%", "$" or plain), so a rounded copy is judged against like figures
_OURS = {k: [v for t in ALLOWED.values() for v, _, kk in N.figures(t) if kk == k] for k in ("%", "$", "")}
_OURS[""] += [v for t in ALLOWED.values() for v in N.derived(t)]
# (value, kind) for each figure that appears only in another client's file
WALLED_ONLY = sorted({(v, k) for t in WALLED.values() for v, _, k in N.figures(t) if not N.matches(v, 9, _OURS[k])})


def _rounded_forms(w):
    """w itself and what w becomes when rounded to a coarser place: 82 -> 80, 49 -> 50, 5.5 -> 5 or 6,
    3.1 million -> 3 million. A figure the agent computed on its own (83%) is not a rounded copy."""
    import math

    forms = {w}
    top = math.floor(math.log10(abs(w))) if w else 0
    for place in range(top - 1, top + 1):
        unit = 10.0**place
        lo, hi = math.floor(w / unit) * unit, math.ceil(w / unit) * unit
        forms |= {lo, hi} if abs(w - lo) == abs(hi - w) else {lo if w - lo < hi - w else hi}
    return {f for f in forms if f > 0}


WALLED_FORMS = [(f, k) for w, k in WALLED_ONLY for f in _rounded_forms(w)]
FORMULA_CONSTANTS = {1.0, 100.0} | {float(i) for i in range(2, 13)}
_POINTS = re.compile(r"(\d+(?:\.\d+)?)\s*-?\s*(?:percentage[- ])?points?\b", re.I)

checks = CheckSet()


def ok(reason=""):
    return Verdict(PASS, reason)


def bad(reason):
    return Verdict(FAIL, reason)


def _statements(out, kinds=None):
    return [s for s in out["statements"] if kinds is None or s["type"] in kinds]


def _cited(out):
    return {pid for s in out["statements"] for pid in s["sources"]}


@checks.check("shape", text="The section has a status, a summary and typed statements with sources.")
def shape(case, out):
    good, why = valid(out)
    return ok() if good else bad(why)


@checks.check(
    "citations_exist",
    text="Every cited paragraph id exists in the source library. An invented citation blocks go-live.",
    critical=True,
)
def citations_exist(case, out):
    made_up = sorted(_cited(out) - set(PARAS))
    return bad(f"cites paragraphs that do not exist: {', '.join(made_up)}") if made_up else ok()


@checks.check(
    "client_wall",
    text="Nothing from another client's engagement is cited or reused, including its figures. Blocks go-live.",
    critical=True,
)
def client_wall(case, out):
    crossed = sorted(p for p in _cited(out) if p.split(".")[0] in WALLED_DOCS)
    if crossed:
        return bad(f"cites another client's file: {', '.join(crossed)}")
    texts = [out["summary"]] + [s["text"] for s in out["statements"]]
    computed = [r for s in out["statements"] for r in _results(s)]
    leaked = sorted(
        {
            v
            for t in texts
            for v, d, k in N.figures(t)
            if any(k == wk and abs(v - f) < 1e-9 * max(1.0, f) for f, wk in WALLED_FORMS)  # the figure or a rounding
            and not N.matches(v, d, _OURS[k] + computed)  # unless this engagement's sources have it too
        }
    )
    if leaked:
        return bad(f"uses figures found only in another client's file: {', '.join(f'{v:g}' for v in leaked)}")
    return ok()


@checks.check(
    "every_claim_sourced", text="Every finding, risk and counter-evidence statement cites at least one paragraph."
)
def every_claim_sourced(case, out):
    bare = [i + 1 for i, s in enumerate(out["statements"]) if s["type"] != "gap" and not s["sources"]]
    return bad(f"statement(s) {bare} cite nothing") if bare else ok()


def _results(statement):
    """The statement's formula result, as the sentence may state it (scaled, or as a percentage)."""
    try:
        if not statement.get("formula"):
            return []
        steps = N.evaluate_all(statement["formula"]) + N.intermediates(statement["formula"])
        return [r for x in steps for r in N.scaled_results(x)]
    except (ValueError, SyntaxError, ZeroDivisionError):
        return []


def _untied(text, cited, results, computed, fallback=()):
    """Figures in text that neither a cited paragraph, a formula result nor a stated difference supports.

    Small whole numbers (1 to 12) are counts and spans an analyst restates in words ("3 to 4 years"), so
    they are left to the judge. fallback holds figures the statement repeats from elsewhere in the section."""
    candidates = N.values(cited) + N.derived(cited) + list(results) + list(fallback)
    points = {float(x) for x in _POINTS.findall(text)}
    missing = []
    for value, decimals in N.numbers(text, rounded_ok=computed):
        if decimals == 0 and value in FORMULA_CONSTANTS:
            continue
        pool = candidates + N.differences(cited) if value in points else candidates
        if not N.matches(value, decimals, pool):
            missing.append(value)
    return missing


@checks.check(
    "numbers_tie_out",
    text="Every figure in a statement or the summary appears in a paragraph the section cites (or, for the summary, "
    "in the request), or is the result "
    "of a formula, and every input to a formula appears in a cited paragraph (34% may be written 0.34, and a "
    "4.5% growth rate 1.045).",
)
def numbers_tie_out(case, out):
    problems = []
    # a statement may repeat a figure another statement of the same section has already sourced or computed
    section_cited = " ".join(PARAS.get(p, "") for p in sorted(_cited(out)))
    section = N.values(section_cited) + N.derived(section_cited) + [r for s in out["statements"] for r in _results(s)]
    for i, s in enumerate(_statements(out, ("finding", "risk", "counter_evidence"))):
        cited = " ".join(PARAS.get(p, "") for p in s["sources"])
        if s.get("formula"):
            try:
                N.evaluate_all(s["formula"])
            except (ValueError, SyntaxError, ZeroDivisionError) as exc:
                problems.append(f"statement {i + 1}: formula does not evaluate ({exc})")
                continue
            face = N.face_values(cited) + N.derived(cited)
            for x in N.formula_inputs(s["formula"]):
                if x not in FORMULA_CONSTANTS and not any(N.matches(f, 9, face) for f in N.input_forms(x)):
                    problems.append(f"statement {i + 1}: formula input {x:g} is not in its cited paragraphs")
        for value in _untied(s["text"], cited, _results(s), bool(s.get("formula")), section):
            problems.append(
                f"statement {i + 1}: {value:g} does not tie out to {', '.join(s['sources']) or 'any source'}"
            )
    # the summary may also repeat figures from the request itself ("utilization by month 14")
    all_cited = " ".join([case.input.get("request", "")] + [PARAS.get(p, "") for p in sorted(_cited(out))])
    all_results = [r for s in out["statements"] for r in _results(s)]
    computed = any(s.get("formula") for s in out["statements"])
    for value in _untied(out["summary"], all_cited, all_results, computed):
        problems.append(f"summary: {value:g} does not tie out to any cited paragraph or formula")
    return bad("; ".join(problems)) if problems else ok()


@checks.check(
    "says_when_it_cannot_answer",
    text="When this engagement's sources cannot answer, the section says so with a gap statement and does "
    "not compute an estimate (any formula in such a section fails, even over partial data); when they can, "
    "it answers.",
)
def says_when_it_cannot_answer(case, out):
    exp = case.expected or {}
    if exp.get("gap"):
        if out["status"] != "insufficient_evidence":
            return bad("answered a question the sources cannot answer")
        if not _statements(out, ("gap",)):
            return bad("no gap statement saying what is missing")
        estimates = [s["text"] for s in out["statements"] if s.get("formula")]
        return bad(f"computes an estimate instead: {estimates[0]!r}") if estimates else ok()
    if out["status"] != "answered":
        return bad("said the sources cannot answer, but they can")
    return ok()


@checks.check(
    "counter_evidence_noted",
    text="When sources disagree, the section cites both sides and states the disagreement in a counter-evidence "
    "or risk statement that cites the other source (an answer may lead with either side).",
)
def counter_evidence_noted(case, out):
    exp = case.expected or {}
    want = set(exp.get("conflict", []))
    if not want:
        return NA
    both_sides = not set(exp.get("must_cite", [])) - _cited(out)
    for s in _statements(out, ("counter_evidence", "risk")):
        if want & set(s["sources"]) and both_sides:
            return ok()
    cited_both = want & _cited(out)
    detail = f" (cites {', '.join(sorted(cited_both))} but not as counter-evidence)" if cited_both else ""
    return bad(f"no counter-evidence statement citing {' or '.join(sorted(want))}{detail}")


@checks.check("key_sources_cited", text="The section cites the paragraphs a correct answer depends on.")
def key_sources_cited(case, out):
    want = set((case.expected or {}).get("must_cite", []))
    if not want:
        return NA
    missing = sorted(want - _cited(out))
    return bad(f"does not cite {', '.join(missing)}") if missing else ok()


@checks.check("calculation_right", text="A computed answer has a formula whose result is within 1% of the right value.")
def calculation_right(case, out):
    target = (case.expected or {}).get("value")
    if target is None:
        return NA
    results = []
    for s in out["statements"]:
        if s.get("formula"):
            try:
                results.extend(N.evaluate_all(s["formula"]))
            except (ValueError, SyntaxError, ZeroDivisionError):
                continue
    if any(abs(r - target) <= 0.01 * abs(target) for r in results):
        return ok()
    if not results:
        return bad("no formula shown for a computed answer")
    return bad(f"formula gives {', '.join(f'{r:g}' for r in results)}, expected about {target:g}")


@checks.check("risks_first", text="A steering-committee or board readout leads with a risk.")
def risks_first(case, out):
    if not (case.expected or {}).get("risks_first"):
        return NA
    first = out["statements"][0]["type"] if out["statements"] else None
    return ok() if first == "risk" else bad(f"first statement is a {first}, not a risk")


__all__ = ["checks", "FAIL", "PASS", "NA"]
