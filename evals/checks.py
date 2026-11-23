"""Rule checks: what the engagement manager's standard says, written so a rule can enforce it.

Each check returns pass, fail or na with a reason. Critical checks block the gate on one failure:
citing a paragraph that does not exist, and breaking a client wall.
"""

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
_OUR_VALUES = {v for t in ALLOWED.values() for v in N.values(t)}
WALLED_ONLY = sorted({v for t in WALLED.values() for v in N.values(t)} - _OUR_VALUES)
FORMULA_CONSTANTS = {1.0, 100.0} | {float(i) for i in range(2, 13)}

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
    leaked = sorted({v for t in texts for v in N.values(t) if any(N.matches(v, 9, [w]) for w in WALLED_ONLY)})
    if leaked:
        return bad(f"uses figures found only in another client's file: {', '.join(f'{v:g}' for v in leaked)}")
    return ok()


@checks.check(
    "every_claim_sourced", text="Every finding, risk and counter-evidence statement cites at least one paragraph."
)
def every_claim_sourced(case, out):
    bare = [i + 1 for i, s in enumerate(out["statements"]) if s["type"] != "gap" and not s["sources"]]
    return bad(f"statement(s) {bare} cite nothing") if bare else ok()


@checks.check(
    "numbers_tie_out",
    text="Every figure in a statement appears in a paragraph it cites, or is the result of its formula, "
    "and every input to a formula appears in a cited paragraph.",
)
def numbers_tie_out(case, out):
    problems = []
    for i, s in enumerate(_statements(out, ("finding", "risk", "counter_evidence"))):
        cited = " ".join(PARAS.get(p, "") for p in s["sources"])
        candidates = N.values(cited)
        if s.get("formula"):
            try:
                candidates.append(N.evaluate(s["formula"]))
            except (ValueError, SyntaxError, ZeroDivisionError) as exc:
                problems.append(f"statement {i + 1}: formula does not evaluate ({exc})")
                continue
            face = N.face_values(cited)
            for x in N.formula_inputs(s["formula"]):
                if x not in FORMULA_CONSTANTS and not N.matches(x, 9, face):
                    problems.append(f"statement {i + 1}: formula input {x:g} is not in its cited paragraphs")
        for value, decimals in N.numbers(s["text"]):
            if not N.matches(value, decimals, candidates):
                problems.append(
                    f"statement {i + 1}: {value:g} does not tie out to {', '.join(s['sources']) or 'any source'}"
                )
    return bad("; ".join(problems)) if problems else ok()


@checks.check(
    "says_when_it_cannot_answer",
    text="When this engagement's sources cannot answer, the section says so with a gap statement and does "
    "not compute an estimate; when they can, it answers.",
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
    text="When sources disagree, a counter-evidence statement cites the other source.",
)
def counter_evidence_noted(case, out):
    want = set((case.expected or {}).get("conflict", []))
    if not want:
        return NA
    for s in _statements(out, ("counter_evidence",)):
        if want & set(s["sources"]):
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
                results.append(N.evaluate(s["formula"]))
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
