"""
PATTERN 03 · PIPELINE (a fixed chain, no boss)

    user ──▶ sourcer ──▶ screener ──▶ writer ──▶ answer
             (who?)      (evidence)   (final text)

The idea      YOUR CODE decides the order, not a model. Each agent does one step and its output
              becomes the next agent's input, like an assembly line.
Use it when   the steps are always the same. Cheaper and more predictable than a supervisor.
Watch for     no step can be skipped or repeated; an error early on flows all the way down.
Try           python mas.py run 03 "Shortlist Kafka candidates for the backend job"
"""
META = {"name": "Pipeline (fixed chain)", "agents": ["sourcer", "screener", "writer"]}


async def run(question, team, auto=False):
    found = await team.ask("sourcer", f"Find every candidate for this request: {question}")
    evidence = await team.ask("screener", f"Check the evidence in these candidates: {found}\nRequest: {question}")
    return await team.ask("writer", f"Request: {question}\nEvidence:\n{evidence}")
