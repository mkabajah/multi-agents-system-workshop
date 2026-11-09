"""
PATTERN 08 · SUPERVISOR + HUMAN APPROVAL

    user ──▶ lead ──▶ ask_sourcer ──▶ ask_screener ──▶ ⏸ a person approves ──▶ ask_coordinator

The idea      Pattern 02, but the lead must get a person's OK before it hands work to the coordinator
              (the only agent that changes something in the world). The run PAUSES, waits, and
              resumes from where it stopped, thanks to a checkpointer that saved the conversation.
Use it when   any agent can write, send, pay, delete or book. Always, in real products.
Watch for     approvals with no context: show the person what will happen and why.
Try           python mas.py run 08 "Find Kafka candidates, check them, and book the best one"
"""
import uuid

from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from lab import prompts
from lab.team import text_of
from patterns.p02_supervisor import delegation_tools

META = {"name": "Supervisor + human approval", "agents": ["lead", "sourcer", "screener", "⏸ person", "coordinator"]}


async def run(question, team, auto=False):
    approve = HumanInTheLoopMiddleware(interrupt_on={"ask_coordinator": True})   # pause BEFORE this tool runs
    lead = team.make(prompts.LEAD, [], extra_tools=delegation_tools(team),
                     middleware=[approve], checkpointer=InMemorySaver())        # checkpointer = can pause/resume
    cfg = {"configurable": {"thread_id": f"hire-{uuid.uuid4().hex[:6]}"},     # which saved conversation
           "callbacks": [team.rec.callbacks], "recursion_limit": 50}

    async with team.rec.agent("lead", question):
        result = await lead.ainvoke({"messages": [{"role": "user", "content": question}]}, cfg)
        while result.get("__interrupt__"):                                     # paused: ask a person
            decisions = []
            for req in result["__interrupt__"][0].value["action_requests"]:
                team.rec.add("note", f"⏸ waiting for a person: {req['name']}({req['args']})")
                ok = auto or input("   approve? [y/n] ").strip().lower().startswith("y")
                team.rec.add("note", "a person approved" if ok else "a person rejected it")
                decisions.append({"type": "approve"} if ok else
                                 {"type": "reject", "message": "The hiring manager said no."})
            result = await lead.ainvoke(Command(resume={"decisions": decisions}), cfg)   # continue
        answer = text_of(result["messages"][-1])
        team.rec.add("answer", answer)
    return answer
