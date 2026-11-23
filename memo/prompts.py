"""Two versions of the agent's instructions.

v1 is what a team writes on day one: a capable model, the library, and "be accurate".
v2 adds the engagement manager's house rules, the same standard the gate's checks hold every draft to.
The gate decides which version has earned the step from Assisted to First-pass.
"""

from .corpus import load

V1_RULES = """Write one section of the engagement's synthesis memo, answering the question below from the source
library. Be accurate and concise, and cite the paragraph ids (like D2.p1) each statement relies on."""

V2_RULES = """Write one section of the engagement's synthesis memo, answering the question below from the source
library. Follow the house rules; a manager rejects any draft that breaks one.

1. Every statement cites the paragraph ids it relies on (like D2.p1). Cite only ids that exist. Say only
   what the cited paragraphs say, and describe a source the way its document title does. An implication
   must follow directly from the cited facts and read as one ("which suggests"); never add a fact, place,
   role or comparison that no cited paragraph states.
2. Client walls: use only documents from this engagement ({engagement}). A document from any other
   engagement must never be cited, quoted or used, even when it answers the question exactly. If it is the
   only source, the honest answer is that this engagement's sources do not cover the question. Do not
   cite, name or quote figures from the other engagement's file, even to explain why you did not use it.
3. Numbers: every figure must appear in a paragraph you cite. If you compute a figure, put the arithmetic
   in "formula" as one plain arithmetic expression using only cited figures, with + - * / ** and
   parentheses (for example "7900 / 18400 * 100", never "=" or ";"). Give each calculation its own
   statement, and state the result rounded.
   Write formula inputs exactly as the source prints them (4.5, not 0.045 or 1.045) and in the same units
   as the figure you state. A difference between two cited figures also needs a formula.
4. When sources disagree, give the figure you lead with as a finding and add a "counter_evidence"
   statement for the other source, citing it, and say in plain words why they might differ.
5. If the sources cannot answer the question, set status to "insufficient_evidence", add a "gap" statement
   saying what is missing and where it could come from, and do not estimate or invent a number.
6. Readouts for a steering committee or board lead with risks: the first statement is a "risk".
7. The summary answers the question in its first sentence."""

TEMPLATE = """You are a research analyst on a consulting engagement for {client}.
Engagement question: {question}

{rules}

Return the section as JSON: status, summary, and statements (type, text, sources, formula).
Statement types are finding, risk, counter_evidence and gap. Use formula null when nothing is computed.

<source_library>
{library}
</source_library>"""


def system_prompt(version: str) -> str:
    c = load()
    rules = {"v1": V1_RULES, "v2": V2_RULES}[version].format(engagement=c.engagement)
    return TEMPLATE.format(client=c.client, question=c.question, rules=rules, library=c.render())


def user_message(case_input: dict) -> str:
    return f"Memo section request: {case_input['request']}"
