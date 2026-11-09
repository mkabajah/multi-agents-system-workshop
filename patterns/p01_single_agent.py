"""
PATTERN 01 · ONE AGENT (the baseline)

    user ──▶ agent ──▶ find_candidates · get_cv · get_free_slots · schedule_interview

The idea      One agent with every tool. Start here: it is the simplest thing that works, and the
              yardstick every multi-agent pattern must beat.
Use it when   the task is small, the tools are few (under ~10), and one context window is enough.
Watch for     the context fills up with every CV it reads; with many tools it picks the wrong one.
Try           python mas.py run 01 "Who knows Kafka? Check the evidence."
"""
from lab import prompts

META = {"name": "One agent (baseline)", "agents": ["agent"]}
TOOLS = ["find_candidates", "search_cvs", "get_cv", "get_free_slots", "schedule_interview"]


async def run(question, team, auto=False):
    """One agent, all the tools, one conversation."""
    agent = team.make(prompts.AGENT, TOOLS)
    return await team.ask("agent", question, agent=agent)
