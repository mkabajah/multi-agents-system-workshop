"""
MODELS · get_model() turns MODEL="provider:model" (from .env) into a LangChain chat model.

    anthropic:claude-sonnet-4-6   needs ANTHROPIC_API_KEY
    openai:gpt-4o-mini            needs OPENAI_API_KEY (or any OpenAI-compatible API via OPENAI_BASE_URL)
    ollama:qwen2.5:7b             local and free (pip install langchain-ollama)
    fake                          FakeModel below: no key, no network

The fake model is NOT an LLM. It follows simple, readable rules so every pattern runs offline and you
can watch the MECHANICS of a multi-agent system (who calls whom, in what order) for free.
Each agent's system prompt starts with "ROLE: <name>", and the fake plays that role:

    lead        calls the specialists it has as tools: sourcer → screener → (coordinator if asked to book)
    sourcer     find_candidates for each skill in its task
    screener    get_cv for the CVs named in its task
    coordinator get_free_slots, then schedule_interview for the first CV in its task
    router      answers with ONE word: sourcer, screener or coordinator
    writer      writes a short answer from the evidence it was given
    critic      says REVISE the first time, APPROVED once the draft was revised
    (handoffs)  an agent with transfer_to_X tools passes control on when its own work is done
"""
import json
import re
import uuid

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from lab import config

SKILLS = ["power bi", "spring boot", "kubernetes", "terraform", "pytorch", "fastapi", "tableau", "docker",
          "kafka", "python", "java", "react", "sql", "aws", "rag", "llm", "go", "excel"]
CITIES = ["haifa", "tel aviv", "nazareth", "jerusalem", "beersheba", "ramallah"]
# The CV file names in data/cvs (e.g. maya-shapiro.md), longest first so "tamar-klein-2023.md" wins
# over "tamar-klein.md". The fake model uses this to spot CV names in a task or a tool result.
_CV_FILES = sorted((p.name for p in config.CV_DIR.rglob("*.md")), key=len, reverse=True)
CV_NAME = re.compile("|".join(re.escape(n) for n in _CV_FILES) or r"(?!x)x")
BOOK = ("interview", "schedule", "book")


def get_model(name: str | None = None) -> BaseChatModel:
    """The chat model for MODEL in .env. init_chat_model reads "provider:model" and loads the right package."""
    name = name or config.MODEL
    return FakeModel() if name == "fake" else init_chat_model(name)


class FakeModel(BaseChatModel):
    """A rule-following stand-in for an LLM that can call tools (see the module docstring)."""

    tool_names: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools, **kwargs):
        """LangChain calls this to tell the model which tools exist; we only need their names."""
        return self.model_copy(update={"tool_names": [getattr(t, "name", None) or t.__name__ for t in tools]})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """One model call: read the conversation, decide, reply (a tool call or text)."""
        system = " ".join(str(m.content) for m in messages if isinstance(m, SystemMessage))
        role = (re.search(r"ROLE: (\w+)", system) or [None, "agent"])[1]
        last = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=0)
        task = str(messages[last].content)
        turn = messages[last + 1:]
        done = [tc["name"] for m in turn if isinstance(m, AIMessage) for tc in m.tool_calls]
        seen = " ".join(str(m.content) for m in turn if isinstance(m, ToolMessage))
        call = self._next_call(role, task, done, seen)
        if call:
            name, args = call
            msg = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}])
        else:
            msg = AIMessage(content=self._answer(role, task, seen))
        return ChatResult(generations=[ChatGeneration(message=msg)])

    # ------------------------------------------------------------------ which tool next?
    def _next_call(self, role, task, done, seen):
        """Return (tool, args) for the next tool call, or None to answer."""
        q, have = task.lower(), set(self.tool_names)
        cvs = list(dict.fromkeys(CV_NAME.findall(task + " " + seen)))
        skills = [s for s in SKILLS if re.search(rf"(?<![a-z]){re.escape(s)}(?![a-z])", q)] or ["kafka"]
        plan = []
        if role == "lead":                                     # the supervisor: delegate in a sensible order
            plan.append(("ask_sourcer", {"task": f"Find every candidate with: {', '.join(skills[:3])}."}))
            if cvs:
                plan.append(("ask_screener", {"task": f"Check the evidence for {', '.join(skills[:3])} in {', '.join(cvs[:3])}."}))
            if cvs and any(w in q for w in BOOK):
                plan.append(("ask_coordinator", {"task": f"Book an interview for {cvs[0]} for the backend-engineer job."}))
        if role == "agent":                                    # ONE agent doing everything (pattern 01)
            plan += [("find_candidates", {"skill": s, "city": ""}) for s in skills[:3]]
            plan += [("get_cv", {"file_name": c}) for c in cvs[:3]]
            if cvs and any(w in q for w in BOOK):
                plan += [("get_free_slots", {}), ("schedule_interview", {"cv": cvs[0], "job": "backend-engineer", "slot": "Mon 11:00"})]
        if role == "sourcer":
            plan += [("find_candidates", {"skill": s, "city": ""}) for s in skills[:3]]
        if role == "screener":
            plan += [("get_cv", {"file_name": c}) for c in cvs[:3]]
        if role == "coordinator" and cvs:
            plan += [("get_free_slots", {}), ("schedule_interview", {"cv": cvs[0], "job": "backend-engineer", "slot": "Mon 11:00"})]
        # handoffs (swarm): when my own work is done, pass control on
        if role == "sourcer" and "transfer_to_screener" in have and cvs:
            plan.append(("transfer_to_screener", {"note": f"Please check {', '.join(cvs[:3])}."}))
        if role == "screener" and "transfer_to_coordinator" in have and any(w in q for w in BOOK) and cvs:
            plan.append(("transfer_to_coordinator", {"note": f"{cvs[0]} is the strongest; please book them."}))
        used = {}
        for name, args in plan:                                # the first planned call not made yet
            if name in have:
                used[name] = used.get(name, 0) + 1
                if done.count(name) < used[name]:
                    return name, args
        return None

    # ------------------------------------------------------------------ the final text
    def _answer(self, role, task, seen):
        cvs = list(dict.fromkeys(CV_NAME.findall(task + " " + seen)))
        names = ", ".join(cvs[:3]) or "no matching CVs"
        if role == "router":
            q = task.lower()
            return "coordinator" if any(w in q for w in BOOK) else ("screener" if cvs or "evidence" in q else "sourcer")
        if role == "critic":
            return ("APPROVED: every claim names a CV file." if "REVISED" in task
                    else "REVISE: name the CV file for every claim and drop anything without evidence.")
        if role == "writer":
            head = "REVISED: " if "REVISE:" in task else ""
            return f"{head}(fake) Shortlist: {names}. Each one has the must-haves in their CV."
        if role == "screener":
            return f"(fake) Evidence checked in {names}: the skills appear in their work history."
        if role == "coordinator":
            return f"(fake) Booked {cvs[0] if cvs else 'nobody'} on Mon 11:00." if "Booked" in seen else "(fake) Nothing booked."
        if role in ("lead", "agent"):
            return f"(fake) Result: candidates {names}. A real model would now write the final answer."
        return f"(fake) Found: {names}."


def tools_json(args: dict) -> str:
    """Short, readable text for tool arguments (used by the trace)."""
    return json.dumps(args, ensure_ascii=False)
