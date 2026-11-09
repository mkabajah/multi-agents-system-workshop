"""
TEAM · the specialists every pattern reuses, and one function to run any agent with tracing.

    Team(tools, rec)          builds the specialists once:
        sourcer      tools: find_candidates, search_cvs        "who has the skills?"
        screener     tools: get_cv, search_cvs                 "is the evidence real?"
        coordinator  tools: get_free_slots, schedule_interview  "book it"
        writer       no tools                                   "write the final answer"
        critic       no tools                                   "is the answer good enough?"
        router       no tools                                   "who should handle this?"
    team.ask(name, task)      run one agent on a fresh conversation, return its final text

Each specialist sees ONLY its own tools and its own conversation. That's the whole point of
splitting work between agents: smaller context, fewer tools to choose from, clearer responsibility.
"""
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware

from lab import actions, prompts
from lab.models import get_model
from lab.trace import Recorder

ROLES = {   # name: (system prompt, the tool names it may use)
    "sourcer": (prompts.SOURCER, ["find_candidates", "search_cvs"]),
    "screener": (prompts.SCREENER, ["get_cv", "search_cvs"]),
    "coordinator": (prompts.COORDINATOR, ["get_free_slots", "schedule_interview"]),
    "writer": (prompts.WRITER, []),
    "critic": (prompts.CRITIC, []),
    "router": (prompts.ROUTER, []),
}


def text_of(message) -> str:
    """The text of a model message (some models return a list of content blocks)."""
    c = message.content
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in c if isinstance(b, dict))


class Team:
    def __init__(self, tools, rec: Recorder):
        self.rec = rec
        self.tools = {t.name: t for t in tools} | {t.name: t for t in actions.ALL}   # MCP tools + write tools
        self.agents = {name: self.make(prompt, names) for name, (prompt, names) in ROLES.items()}

    def make(self, prompt: str, tool_names: list[str], extra_tools=(), middleware=(), **kw):
        """A LangChain agent with a step budget (ModelCallLimitMiddleware), so no agent can loop forever.
        `middleware` adds more, e.g. a human-approval step; **kw goes to create_agent (e.g. checkpointer)."""
        return create_agent(get_model(), [self.tools[n] for n in tool_names] + list(extra_tools),
                            system_prompt=prompt,
                            middleware=[ModelCallLimitMiddleware(run_limit=10), *middleware], **kw)

    async def ask(self, name: str, task: str, agent=None, label: str | None = None) -> str:
        """Run one agent on `task` in a FRESH conversation and return only its final answer.
        `label` names a copy (e.g. "screener-2" when several screeners run in parallel)."""
        agent = agent or self.agents[name]
        async with self.rec.agent(label or name, task):
            out = await agent.ainvoke({"messages": [{"role": "user", "content": task}]},
                                      {"callbacks": [self.rec.callbacks], "recursion_limit": 50})
            answer = text_of(out["messages"][-1])
            self.rec.add("answer", answer)
        return answer
