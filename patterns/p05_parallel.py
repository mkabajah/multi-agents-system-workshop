"""
PATTERN 05 · PARALLEL FAN-OUT (map, then merge)

                         ┌──▶ screener-1 (cand-006.md) ─┐
    user ──▶ sourcer ────┼──▶ screener-2 (cand-007.md) ─┼──▶ writer ──▶ answer
                         └──▶ screener-3 (cand-009.md) ─┘

The idea      Split the work into independent pieces and run one agent per piece AT THE SAME TIME
              (asyncio.gather), then merge. Each screener reads only ONE CV, so its context stays small.
Use it when   the pieces don't depend on each other: one CV, one document, one file each.
Watch for     cost grows with the number of pieces; cap it (here: 3).
Try           python mas.py run 05 "Screen the Kafka candidates for the backend job"
"""
import asyncio

from lab.models import CV_NAME

META = {"name": "Parallel fan-out", "agents": ["sourcer", "screener ×N", "writer"]}


async def run(question, team, auto=False):
    found = await team.ask("sourcer", f"Find every candidate for this request: {question}")
    cvs = list(dict.fromkeys(CV_NAME.findall(found)))[:3]                    # at most 3 in parallel
    reports = await asyncio.gather(*[                                         # all screeners at once
        team.ask("screener", f"Check the evidence in {cv} for: {question}", label=f"screener-{i}")
        for i, cv in enumerate(cvs, 1)])
    merged = "\n".join(f"{cv}: {r}" for cv, r in zip(cvs, reports))
    return await team.ask("writer", f"Request: {question}\nOne report per candidate:\n{merged}")
