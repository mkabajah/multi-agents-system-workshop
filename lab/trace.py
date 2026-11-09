"""
TRACE · records what every agent does, prints it live, and keeps it for the HTML timeline.

A multi-agent run is hard to follow because several agents talk at once. This module gives each
event a clear owner:

    Recorder        the list of events for one run (agent, kind, text, depth, time)
    recorder.agent  `async with rec.agent("screener"):` marks code that runs AS that agent
    rec.callbacks   a LangChain callback handler: every model call and tool call inside an
                    agent is recorded under the agent that is running right now

Event kinds:  start · think (a model call) · tool (a tool call) · result (what came back)
              · delegate (one agent hands work to another) · answer · note
"""
import contextlib
import contextvars
import time
from dataclasses import dataclass, field

from langchain_core.callbacks import AsyncCallbackHandler

# Which agent is running right now? A ContextVar is like a global variable that is safe with async:
# each asyncio task (e.g. two screeners running in parallel) sees its own value.
_current: contextvars.ContextVar[tuple[str, int]] = contextvars.ContextVar("current_agent", default=("code", 0))
# "code" = YOUR Python code (mas.py and the pattern's run function): it starts the first agent, and in
# patterns like the pipeline it is the one that decides who goes next.

COLORS = {"code": "37", "lead": "35", "agent": "35", "router": "33", "sourcer": "34", "screener": "36",
          "coordinator": "31", "writer": "32", "critic": "33"}         # terminal colors per agent
ICONS = {"start": "▶", "think": "·", "tool": "🔧", "result": "←", "delegate": "➜", "answer": "✔", "note": "ℹ"}


@dataclass
class Event:
    t: float            # seconds since the run started
    agent: str          # who did it (screener-2 for the second parallel screener)
    kind: str           # start · think · tool · result · delegate · answer · note
    text: str
    depth: int          # 0 = your code, 1 = an agent it started, 2 = an agent called by that one, …


@dataclass
class Recorder:
    """All events of one run, plus counters for the summary and the compare table."""
    quiet: bool = False
    events: list[Event] = field(default_factory=list)
    t0: float = field(default_factory=time.perf_counter)
    model_calls: int = 0
    tool_calls: int = 0
    tokens: int = 0

    def add(self, kind: str, text: str, agent: str | None = None, depth: int | None = None):
        cur_agent, cur_depth = _current.get()
        e = Event(round(time.perf_counter() - self.t0, 2), agent or cur_agent, kind, " ".join(str(text).split()),
                  cur_depth if depth is None else depth)
        self.events.append(e)
        if not self.quiet:
            base = e.agent.split("-")[0]
            short = e.text if len(e.text) < 160 else e.text[:157] + "…"
            color = "2" if kind == "think" else COLORS.get(base, "37")       # model calls are dimmed
            print(f"{'   ' * max(e.depth - 1, 0)}\033[{color}m{ICONS[kind]} {e.agent:<12}\033[0m {short}")

    @contextlib.asynccontextmanager
    async def agent(self, name: str, task: str = ""):
        """Everything inside this block counts as `name` working on `task`."""
        parent, depth = _current.get()
        last = self.events[-1] if self.events else None
        if not (last and last.kind == "delegate" and f"→ {name}:" in last.text):   # not already announced
            self.add("delegate", f"{parent} → {name}: {task}", agent=parent)
        token = _current.set((name, depth + 1))
        self.add("start", task or "(starts)")
        try:
            yield
        finally:
            _current.reset(token)

    @property
    def callbacks(self):
        """THE LangChain callback handler of this recorder (one per run, so nested agents don't double-count)."""
        if not hasattr(self, "_handler"):
            self._handler = _Handler(self)
        return self._handler

    def agents(self, with_code: bool = False) -> list[str]:
        """The agents that took part, in order of first appearance ("code" too if with_code)."""
        return list(dict.fromkeys(e.agent for e in self.events if with_code or e.agent != "code"))


class _Handler(AsyncCallbackHandler):
    """Turns LangChain's callbacks into Events. LangChain calls these methods for us."""

    def __init__(self, rec: Recorder):
        self.rec, self.seen = rec, set()

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kw):
        if run_id in self.seen:                      # the same callback can arrive twice in nested runs
            return
        self.seen.add(run_id)
        self.rec.model_calls += 1
        self.rec.add("think", "model call")

    async def on_llm_end(self, response, *, run_id, **kw):
        try:                                         # real models report token usage; the fake doesn't
            usage = response.generations[0][0].message.usage_metadata or {}
            self.rec.tokens += usage.get("total_tokens", 0)
        except (AttributeError, IndexError):
            pass

    async def on_tool_start(self, serialized, input_str, *, run_id, **kw):
        if run_id in self.seen:
            return
        self.seen.add(run_id)
        name = serialized.get("name", "tool")
        if name.startswith(("ask_", "transfer_to_")):         # delegations are recorded by rec.agent()
            self.seen.add(("skip", run_id))
            return
        self.rec.tool_calls += 1
        self.rec.add("tool", f"{name}({input_str})")

    async def on_tool_end(self, output, *, run_id, **kw):
        if ("end", run_id) in self.seen or ("skip", run_id) in self.seen:
            return
        self.seen.add(("end", run_id))
        self.rec.add("result", plain(getattr(output, "content", output))[:300])


def plain(content) -> str:
    """Tool results can be a string or a list of content blocks ({'type': 'text', 'text': ...}); give text."""
    if isinstance(content, list):
        return " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)
