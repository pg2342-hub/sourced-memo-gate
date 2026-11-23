"""Cost, latency and gate decision of each recorded prompt version, from recordings/ and docs/ (prints JSON)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNG = {"go": "graduates to First-pass", "partial": "stays at Assisted", "no-go": "not fit for client work"}


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line)["value"] for line in path.read_text().splitlines() if line.strip()]


out = {}
for version, docs in (("v1", ROOT / "docs" / "v1"), ("v2", ROOT / "docs")):
    agent = rows(ROOT / "recordings" / f"agent_{version}.jsonl")
    judge = rows(ROOT / "recordings" / f"judge_{version}.jsonl")
    if not agent:
        continue
    meta = [a["_meta"] for a in agent]
    lat = sorted(m["latency_s"] for m in meta)
    results = json.loads((docs / "results.json").read_text()) if (docs / "results.json").exists() else {}
    decision = results.get("decision")
    out[version] = {
        "model": meta[0]["model"],
        "calls": len(meta),
        "mean_latency_s": sum(lat) / len(lat),
        "p90_latency_s": lat[int(0.9 * (len(lat) - 1))],
        "mean_cost_usd": sum(m["cost_usd"] for m in meta) / len(meta),
        "agent_cost_usd": sum(m["cost_usd"] for m in meta),
        "judge_calls": len(judge),
        "judge_cost_usd": sum(j["cost_usd"] for j in judge),
        "decision": decision,
        "rung": RUNG.get(decision),
    }
print(json.dumps(out, indent=2))
