"""
PATTERN 04 · ROUTER (pick one specialist)

    user ──▶ router ──┬──▶ sourcer       "who knows Kafka?"
                      ├──▶ screener      "check the evidence in cand-006.md"
                      └──▶ coordinator   "book cand-006.md on Monday"

The idea      One cheap model call classifies the request; then exactly ONE specialist handles it.
              The router never does the work itself.
Use it when   requests are of a few clear kinds (like a support desk), and each kind has an expert.
Watch for     a wrong route = a wrong answer; give the router a fallback and test it with examples.
Try           python mas.py run 04 "Check the evidence in cand-006.md"
"""
META = {"name": "Router (one specialist)", "agents": ["router", "sourcer | screener | coordinator"]}


async def run(question, team, auto=False):
    choice = (await team.ask("router", question)).strip().lower().split()[0].strip(".:,")
    if choice not in ("sourcer", "screener", "coordinator"):
        team.rec.add("note", f"router said '{choice}': falling back to the sourcer")
        choice = "sourcer"
    return await team.ask(choice, question)
