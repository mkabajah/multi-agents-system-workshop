"""
PATTERN 06 · HANDOFFS (a swarm: pass the baton)

    user ──▶ sourcer ──transfer──▶ screener ──transfer──▶ coordinator ──▶ answer
             (the agent in charge decides who goes next; nobody is the boss)

The idea      Each agent has transfer_to_<agent> tools. When it has done its part, it hands control
              (and a note) to the next agent, who continues the SAME task. Unlike the supervisor,
              control does not come back: the last agent answers the user.
Use it when   the work flows naturally from one expert to another, like a hospital referral.
Watch for     ping-pong between two agents; cap the number of handoffs (here: 4).
Try           python mas.py run 06 "Find Kafka candidates, check the best one, and book an interview"
"""
from langchain.tools import tool

from lab import prompts

META = {"name": "Handoffs (swarm)", "agents": ["sourcer", "screener", "coordinator"]}
NEXT = {"sourcer": ["screener"], "screener": ["coordinator"], "coordinator": []}   # who may hand to whom
MAX_HANDOFFS = 4


def transfer_tool(target: str, box: dict):
    """A tool that only records 'hand over to <target>'; our loop below does the actual switch."""

    @tool(f"transfer_to_{target}")
    def transfer(note: str) -> str:
        """Hand the task over to the next specialist, with a short note about what you found."""
        box["next"], box["note"] = target, note
        return f"Handed over to {target}."

    transfer.description = f"Hand the task over to the {target}, with a short note about what you found."
    return transfer


async def run(question, team, auto=False):
    from lab.team import ROLES
    current, notes = "sourcer", []
    for _ in range(MAX_HANDOFFS):
        box = {}
        prompt, tool_names = ROLES[current]
        handoff_note = "\nWhen your part is done, hand over with a transfer tool if someone else must continue."
        agent = team.make(prompt + handoff_note, tool_names, extra_tools=[transfer_tool(t, box) for t in NEXT[current]])
        task = question if not notes else f"{question}\nNotes so far: {' '.join(notes)}"
        answer = await team.ask(current, task, agent=agent)
        if "next" not in box:                                  # no handoff: this agent answered the user
            return answer
        team.rec.add("delegate", f"{current} → {box['next']}: {box['note']}", agent=current)
        notes.append(f"{current}: {box['note']}")
        current = box["next"]
    return answer
