"""
PATTERN 02 · SUPERVISOR (agents as tools)

    user ──▶ lead ──▶ ask_sourcer      ──▶ sourcer     (find_candidates)
                 ├──▶ ask_screener     ──▶ screener    (get_cv)
                 └──▶ ask_coordinator  ──▶ coordinator (schedule_interview)

The idea      A lead agent DELEGATES. Each specialist is wrapped as a tool, so for the lead,
              "ask the screener" looks exactly like any other tool call. The lead decides who to
              ask, in what order, and writes the final answer. Specialists never talk to each other.
Use it when   the steps change from request to request and you want one agent in charge.
Watch for     every delegation is extra model calls; the lead must give each specialist a clear task.
Try           python mas.py run 02 "Shortlist Kafka candidates, check the evidence, and book the best one"
"""
from langchain.tools import tool

from lab import prompts

META = {"name": "Supervisor (agents as tools)", "agents": ["lead", "sourcer", "screener", "coordinator"]}


def delegation_tools(team):
    """Wrap each specialist as a tool the lead can call. The docstring is what the lead reads."""

    @tool
    async def ask_sourcer(task: str) -> str:
        """Ask the sourcer to find EVERY candidate with the given skills. Name the skills."""
        return await team.ask("sourcer", task)

    @tool
    async def ask_screener(task: str) -> str:
        """Ask the screener to check the evidence in named CVs. Give CV file names and must-haves."""
        return await team.ask("screener", task)

    @tool
    async def ask_coordinator(task: str) -> str:
        """Ask the coordinator to book an interview for ONE named candidate (CV file name + job)."""
        return await team.ask("coordinator", task)

    return [ask_sourcer, ask_screener, ask_coordinator]


async def run(question, team, auto=False):
    lead = team.make(prompts.LEAD, [], extra_tools=delegation_tools(team))
    return await team.ask("lead", question, agent=lead)
