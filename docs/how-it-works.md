# How the lab works (under the hood)

You don't need this to use the lab. Read it when you want to change it.

## One run, end to end

```
python mas.py run 02 "question"
  │
  ├─ rag_tools()          start the CV MCP server (cv_server/server.py) as a child process,
  │                       load its 4 tools as LangChain tools            ← lab/mcp_tools.py
  ├─ Recorder()           an empty list of events                        ← lab/trace.py
  ├─ Team(tools, rec)     build the 6 specialists (prompt + their tools) ← lab/team.py
  ├─ pattern.run(question, team)   the pattern wires the agents          ← patterns/p02_supervisor.py
  │     └─ team.ask("sourcer", task)   run ONE agent in a fresh conversation, return its answer
  └─ viewer.save(rec)     write runs/02-<time>.html and runs/latest.html ← lab/viewer.py
```

## `team.ask()`: the one function every pattern uses

```python
async def ask(self, name, task, agent=None, label=None) -> str:
    agent = agent or self.agents[name]
    async with self.rec.agent(label or name, task):          # 1. "from now on, events belong to <name>"
        out = await agent.ainvoke(
            {"messages": [{"role": "user", "content": task}]}, # 2. a FRESH conversation: only the task
            {"callbacks": [self.rec.callbacks]})              # 3. record every model and tool call
        answer = text_of(out["messages"][-1])                 # 4. keep only the final answer
        self.rec.add("answer", answer)
    return answer
```

Point 2 is the heart of multi-agent: **each agent starts with an empty memory**. The only thing that
flows between agents is the text you pass in `task` and the text they return. If an agent "doesn't know"
something, check what was in its task.

## How the trace knows who did what

`rec.agent(name)` sets a **ContextVar**: a variable that each asyncio task sees its own copy of. The
LangChain callback handler reads it on every model/tool call. That's why, in pattern 05, three screeners
running *at the same time* still get their events in the right column.

## Agents as tools (02, 08)

A tool is just an async function with a docstring. If the function runs another agent, the calling
agent can delegate without knowing it:
```python
@tool
async def ask_screener(task: str) -> str:
    """Ask the screener to check the evidence in named CVs."""   # ← the lead's model reads this
    return await team.ask("screener", task)
```

## Handoffs (06)

The `transfer_to_<agent>` tool doesn't run anything: it writes the target into a box. After the agent
finishes, our loop looks in the box and starts the next agent with the original question plus the notes
so far. (LangGraph also has a prebuilt swarm, `langgraph-swarm`; ours is 40 lines so you can see it.)

## Human approval (08)

`HumanInTheLoopMiddleware(interrupt_on={"ask_coordinator": True})` stops the lead **before** that tool
runs. Because the lead has a **checkpointer**, its conversation is saved under a `thread_id`. We ask the
person, then call `ainvoke(Command(resume=...))` with the same `thread_id` and it continues where it
stopped. Swap `InMemorySaver` for a SQLite or Postgres saver and the pause can last days.

## The fake model

`lab/models.py` → `FakeModel`. It reads `ROLE: <name>` from the system prompt and follows a short plan
per role (e.g. screener: `get_cv` for each CV named in its task, then answer). It's ~100 lines of
plain rules, so it costs nothing and never surprises you. Use it to learn the wiring, then switch to a
real model to see real decisions.

## Add your own pattern

1. Copy `patterns/p03_pipeline.py` to `patterns/p09_mine.py`.
2. Change `META` and `run()`. Use `team.ask(...)`, `team.make(...)` and `team.rec.add("note", ...)`.
3. `python mas.py list` finds it automatically. Add it to `EXPECTED` in `tests/test_patterns.py`.

## Add your own agent

Add a prompt to `lab/prompts.py` (start it with `ROLE: <name>`) and a line to `ROLES` in `lab/team.py`
with the tools it may use. For the fake model, add a rule in `FakeModel._next_call` / `_answer`.
