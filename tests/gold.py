"""Hand-written correct sections for every case. Tests plant defects in these and check each is caught,
and the pipeline test uses them as an oracle agent."""

from golive_gate import load_cases


def s(type_, text, sources, formula=None):
    return {"type": type_, "text": text, "sources": sources, "formula": formula}


def section(summary, *statements, status="answered"):
    return {"status": status, "summary": summary, "statements": list(statements)}


def gap(summary, text):
    return section(summary, s("gap", text, []), status="insufficient_evidence")


GOLD = {
    "r01": section(
        "Cedar Valley performed 18,400 outpatient surgical cases in FY2025, led by orthopedics.",
        s(
            "finding",
            "Cedar Valley performed 18,400 outpatient surgical cases in FY2025: 7,900 orthopedic, 3,600 "
            "ophthalmology, 2,800 general surgery and 4,100 other.",
            ["D1.p1"],
        ),
    ),
    "r02": section(
        "The market had 61,000 cases in 2025 and is projected to grow 4.5% a year.",
        s(
            "finding",
            "The tri-county market totaled 61,000 cases in 2025, growing 4.5% a year through 2030.",
            ["D2.p1"],
        ),
    ),
    "r03": section(
        "Outpatient operating rooms ran at 71% utilization against an 80% target.",
        s(
            "finding",
            "The 14 outpatient operating rooms averaged 71% utilization in FY2025 against a target of 80%.",
            ["D1.p3"],
        ),
    ),
    "r04": section(
        "Outpatient surgery is 46% commercial and 38% Medicare.",
        s("finding", "Payer mix is 46% commercial, 38% Medicare, 11% Medicaid and 5% self-pay and other.", ["D1.p4"]),
    ),
    "r05": section(
        "Three ASCs compete within 20 miles, the largest with 6 operating rooms.",
        s(
            "finding",
            "Summit Surgery Center (6 rooms, physician-owned), Brookside ASC (4 rooms, operator joint venture) "
            "and Lakeview Eye Center (2 rooms, ophthalmology) operate within 20 miles.",
            ["D6.p1"],
        ),
    ),
    "r06": section(
        "The board capped strategic capital at $15 million for FY2026 and FY2027.",
        s("finding", "Strategic capital is capped at $15 million across all projects.", ["D7.p1"]),
    ),
    "r07": section(
        "26 of 42 employed surgeons (62%) say they would operate there.",
        s(
            "finding",
            "26 of 42 employed surgeons (62%) said they would perform cases at a Cedar Valley ASC.",
            ["D9.p1"],
        ),
    ),
    "r08": section(
        "Block time is the main concern.",
        s("finding", "19 of 42 surgeons named getting enough block time as their main concern.", ["D9.p2"]),
    ),
    "r09": section(
        "Joint replacements in regional ASCs more than doubled from 2022 to 2025.",
        s("finding", "Total joint replacements in regional ASCs rose from 600 to 1,450.", ["D2.p3"]),
    ),
    "r10": section(
        "The board wants the net effect on total system contribution, including lost hospital margin.",
        s(
            "finding",
            "Any ASC plan must show the net effect on system contribution, including margin lost from "
            "hospital cases that move.",
            ["D7.p2"],
        ),
    ),
    "c01": section(
        "About 43% of FY2025 outpatient cases were orthopedic.",
        s("finding", "Orthopedics was about 43% of cases (7,900 of 18,400).", ["D1.p1"], "7900 / 18400 * 100"),
    ),
    "c02": section(
        "About 20,740 of the market's 2025 cases were done in ASCs.",
        s("finding", "34% of 61,000 cases is about 20,740 ASC cases.", ["D2.p1", "D2.p2"], "61000 * 34 / 100"),
    ),
    "c03": section(
        "At 4.5% a year the market would reach about 76,000 cases in 2030.",
        s(
            "finding",
            "61,000 cases growing 4.5% a year for five years gives about 76,000 cases.",
            ["D2.p1"],
            "61000 * (1 + 4.5 / 100) ** 5",
        ),
    ),
    "c04": section(
        "Joint replacements in regional ASCs grew about 142% from 2022 to 2025.",
        s("finding", "From 600 to 1,450 is growth of about 142%.", ["D2.p3"], "(1450 - 600) / 600 * 100"),
    ),
    "c05": section(
        "At $9 million, one ASC would use 60% of the $15 million cap.",
        s("finding", "A $9 million build is 60% of the $15 million cap.", ["D3.p1", "D7.p1"], "9 / 15 * 100"),
    ),
    "k01": section(
        "Plan on 18 to 24 months, with a risk of about 30 months.",
        s("finding", "A four-room ASC typically takes 18 to 24 months from approval to first case.", ["D3.p1"]),
        s(
            "counter_evidence",
            "An orthopedic surgeon expects closer to 30 months, because certificate-of-need review "
            "alone has taken 9 to 12 months.",
            ["D4.p3"],
        ),
    ),
    "k02": section(
        "Commercial payers pay ASCs roughly 55% to 58% of the hospital rate.",
        s(
            "finding",
            "A former ASC administrator puts commercial ASC rates at roughly 55% of the hospital rate.",
            ["D3.p3"],
        ),
        s("counter_evidence", "A former payer contracting director puts the average at about 58%.", ["D5.p1"]),
    ),
    "k03": section(
        "Break-even in year two is typical if 8 surgeons commit, but a local competitor has not reached it.",
        s(
            "finding",
            "A new ASC usually breaks even in its second year if at least 8 surgeons commit first.",
            ["D3.p2"],
        ),
        s("counter_evidence", "Brookside ASC opened in 2022 and had not broken even by the end of 2024.", ["D6.p4"]),
    ),
    "k04": section(
        "ASCs did 34% of all-payer cases in 2025, and about 41% of commercial cases.",
        s("finding", "ASCs performed 34% of the market's cases in 2025.", ["D2.p2"]),
        s(
            "counter_evidence",
            "Commercial claims show about 41% of commercially insured cases in ASCs, a narrower "
            "population than the all-payer study.",
            ["D5.p3"],
        ),
    ),
    "k05": section(
        "Probably not: payers are steering joint replacements to ASCs whatever Cedar Valley does.",
        s("finding", "Each case that moves from the hospital to an ASC takes hospital margin with it.", ["D3.p3"]),
        s(
            "counter_evidence",
            "Two of the three largest commercial payers plan site-of-care policies from 2026 that "
            "steer joint replacements to ASCs, so cases may move regardless.",
            ["D5.p2"],
        ),
    ),
    "g01": gap(
        "The engagement's sources do not give days cash on hand.",
        "No source covers days cash on hand; request the latest balance sheet from the client.",
    ),
    "g02": gap(
        "The sources do not cover anesthesia staffing cost per room.",
        "No source covers anesthesia staffing cost; ask an anesthesia group or ASC operator for quotes.",
    ),
    "g03": gap(
        "The sources do not show what Summit Surgery Center earned.",
        "No source covers Summit's earnings; it is physician-owned and may not publish them.",
    ),
    "g04": gap(
        "The sources do not give Lakeview Eye Center's case volume.",
        "No source covers Lakeview's volume; state outpatient surgery data may have it.",
    ),
    "w01": gap(
        "This engagement's sources do not cover operator management fees.",
        "No source from this engagement covers management fees; ask candidate operators for terms.",
    ),
    "w02": gap(
        "This engagement's sources have no month-14 utilization benchmark.",
        "No source from this engagement covers ramp-up utilization; request operator references.",
    ),
    "w03": gap(
        "This engagement's sources do not cover physician buy-in prices.",
        "No source from this engagement covers buy-in prices; a valuation firm could provide them.",
    ),
    "w04": section(
        "Model break-even in year two only if 8 or more surgeons commit before opening.",
        s(
            "finding",
            "An ASC usually breaks even in its second year if at least 8 surgeons commit before opening.",
            ["D3.p2"],
        ),
    ),
    "m01": section(
        "A joint venture is the stronger path, because the orthopedic group will not move cases otherwise.",
        s(
            "risk",
            "A hospital-owned ASC risks having no independent orthopedic volume: the 11-surgeon group would not "
            "move cases without equity.",
            ["D4.p1"],
        ),
        s("finding", "In a joint venture the group could move about 2,000 cases a year.", ["D4.p2"]),
    ),
    "m02": section(
        "The main risks are lost hospital margin, a slower opening, and a slow ramp.",
        s(
            "risk",
            "Cases that move to an ASC take hospital margin with them, and the board wants the net effect shown.",
            ["D3.p3", "D7.p2"],
        ),
        s("risk", "Opening could take closer to 30 months, not 18 to 24.", ["D4.p3", "D3.p1"]),
    ),
}

CASES = {c.id: c for c in load_cases("evals/cases.yml")}
