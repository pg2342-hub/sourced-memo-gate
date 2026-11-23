#!/usr/bin/env bash
# Rebuild the GitHub Pages demo in docs/ from the recorded live runs (no API key needed).
#   docs/           prompt v2 (house rules), the run the gate decides on
#   docs/v1/        prompt v1 (day-one prompt), same cases and gate
#   docs/baseline/  the no-model extractive baseline
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf docs && mkdir -p docs
golive run evals/golive.baseline.yml --out docs/baseline >/dev/null || true
if [ -s recordings/agent_v1.jsonl ]; then golive run evals/golive.v1.yml --out docs/v1 >/dev/null || true; fi
if [ -s recordings/agent_v2.jsonl ]; then golive run evals/golive.v2.yml --out docs >/dev/null || true; fi
python scripts/summarize.py > docs/summary.json
find docs -name report.md -delete
python - <<'PY'
import json
from pathlib import Path

s = json.loads(Path("docs/summary.json").read_text())
code = "<a href='https://github.com/pg2342-hub/sourced-memo-gate'>Code on GitHub</a>"
gate = "<a href='https://github.com/pg2342-hub/golive-gate'>golive-gate</a>"
intro = (
    "An AI analyst drafts sections of a consulting synthesis memo from a fictional engagement's source library "
    "(a health system weighing an ambulatory surgery center). One file in the library belongs to a different "
    f"client. 30 requests, 3 runs each, graded with {gate}: rules check citations, figures, client walls, gaps "
    "and conflicts; a Claude judge checks that each claim says only what its sources say. "
    "The gate decides whether the workflow graduates from Assisted (an analyst writes) to First-pass "
    "(the agent drafts, an analyst reviews)."
)


def line(v):
    r = s[v]
    return (
        f"Recorded live run of {r['model']}, prompt {v}: {r['calls']} sections, mean {r['mean_latency_s']:.1f} s "
        f"and ${r['mean_cost_usd']:.4f} per section; judge ${r['judge_cost_usd']:.2f} in total. "
        f"Decision: <b>{r['rung']}</b>."
    )


pages = {}
if "v2" in s:
    links = "<a href='v1/'>Prompt v1 on the same gate</a> · <a href='baseline/'>No-model baseline</a> · " + code
    pages["docs/index.html"] = f"{intro}</p><p>{line('v2')}</p><p>{links}"
if "v1" in s:
    pages["docs/v1/index.html"] = (
        f"{line('v1')} The same model with a day-one prompt and no house rules. "
        f"<a href='../'>Back to prompt v2</a> · {code}"
    )
pages["docs/baseline/index.html"] = (
    "A no-model baseline that copies the two paragraphs sharing the most words with each request. It looks "
    "sourced, but it cites the other client's file, never admits a gap and never flags a conflict, so the gate "
    f"blocks it. <a href='../'>Back</a> · {code}"
)
for path, note in pages.items():
    p = Path(path)
    p.write_text(p.read_text().replace("</h1>", f"</h1>\n<p>{note}</p>", 1))
if not Path("docs/index.html").exists():  # before the first recording, the baseline is the demo
    Path("docs/index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>sourced-memo-gate</title>"
        f"<p>{intro}</p><p>No live run recorded yet. <a href='baseline/'>See the baseline blocked</a>. {code}</p>"
    )
PY
touch docs/.nojekyll
echo "demo written to docs/"
