# The 8 patterns on one page

Same agents, same tools, same question. Only the wiring changes.
For each: the picture, the idea, the key lines of code, and the trade-off.
Run any of them with `python mas.py run NN`.

---

## 01 · One agent (baseline) — `patterns/p01_single_agent.py`

```
user ──▶ agent ──▶ find_candidates · get_cv · get_free_slots · schedule_interview
```
One agent, every tool. The yardstick: **a multi-agent pattern must beat this** on quality, cost or
safety, or it isn't worth it.
```python
agent = team.make(prompts.AGENT, TOOLS)          # all 5 tools
return await team.ask("agent", question, agent=agent)
```
✅ simplest, fewest model calls · ⚠️ context fills with every CV; any step can book

---

## 02 · Supervisor (agents as tools) — `p02_supervisor.py`

```
user ──▶ lead ──▶ ask_sourcer · ask_screener · ask_coordinator
```
The lead never touches the CVs. Each specialist is **wrapped as a tool**, so delegating looks exactly
like a tool call. The docstring is what the lead reads to decide.
```python
@tool
async def ask_screener(task: str) -> str:
    """Ask the screener to check the evidence in named CVs. Give CV file names and must-haves."""
    return await team.ask("screener", task)       # a whole agent run, inside a tool
```
✅ flexible, one agent in charge, specialists stay small · ⚠️ more model calls (the lead thinks between every step)

---

## 03 · Pipeline — `p03_pipeline.py`

```
sourcer ──▶ screener ──▶ writer
```
**Your code** decides the order. Each answer becomes the next agent's input.
```python
found    = await team.ask("sourcer",  f"Find every candidate for this request: {question}")
evidence = await team.ask("screener", f"Check the evidence in these candidates: {found}")
return     await team.ask("writer",   f"Request: {question}\nEvidence:\n{evidence}")
```
✅ cheap, predictable, easy to test · ⚠️ can't skip or repeat a step; early mistakes flow down

---

## 04 · Router — `p04_router.py`

```
router ──▶ ONE of: sourcer | screener | coordinator
```
One cheap call classifies; one specialist does the work.
```python
choice = await team.ask("router", question)      # "screener"
return await team.ask(choice, question)
```
✅ cheapest when requests are of clear kinds · ⚠️ a wrong route = a wrong answer; needs a fallback

---

## 05 · Parallel fan-out — `p05_parallel.py`

```
sourcer ──▶ screener-1 ┐
        ──▶ screener-2 ├──▶ writer
        ──▶ screener-3 ┘
```
One agent per independent piece, **all at the same time**, then merge.
```python
reports = await asyncio.gather(*[team.ask("screener", f"Check {cv}", label=f"screener-{i}")
                                 for i, cv in enumerate(cvs, 1)])
```
✅ fast; each screener's context holds ONE CV · ⚠️ cost grows with N: cap it

---

## 06 · Handoffs (swarm) — `p06_handoffs.py`

```
sourcer ──transfer──▶ screener ──transfer──▶ coordinator ──▶ answer
```
Each agent has `transfer_to_<next>` tools. It does its part, then **passes control on**: no boss, and
control doesn't come back. The last agent answers.
```python
NEXT = {"sourcer": ["screener"], "screener": ["coordinator"], "coordinator": []}
...
if "next" not in box:          # the agent didn't hand off → it answered the user
    return answer
current = box["next"]          # switch to the agent it chose
```
✅ natural for referral-style work · ⚠️ ping-pong loops: cap the handoffs (MAX_HANDOFFS)

---

## 07 · Writer + critic — `p07_critic.py`

```
writer ──▶ critic ──APPROVED──▶ answer
  ▲          │
  └─REVISE───┘   (max 2 rounds)
```
A second agent, with a different prompt, checks the first one's work.
```python
for round_ in range(1, MAX_ROUNDS + 1):
    review = await team.ask("critic", f"...Draft:\n{draft}")
    if review.startswith("APPROVED"):
        return draft
    draft = await team.ask("writer", f"...{draft}\n{review}")
```
✅ better quality on things sent outside · ⚠️ double the cost; a critic that approves everything is useless

---

## 08 · Supervisor + human approval — `p08_human_approval.py`

```
lead ──▶ sourcer ──▶ screener ──▶ ⏸ a person approves ──▶ coordinator
```
Pattern 02, but the run **pauses** before `ask_coordinator` and waits for a person.
```python
approve = HumanInTheLoopMiddleware(interrupt_on={"ask_coordinator": True})
lead = team.make(prompts.LEAD, [], extra_tools=..., middleware=[approve], checkpointer=InMemorySaver())
result = await lead.ainvoke(...)
while result.get("__interrupt__"):                 # paused
    ok = input("approve? [y/n] ")
    result = await lead.ainvoke(Command(resume={"decisions": [...]}), cfg)
```
✅ required whenever agents write, send, pay or book · ⚠️ the person needs context to decide well

---

## Choosing

```
Is one agent good enough?  ── yes ──▶ 01. Stop here.
        │ no
Are the steps always the same?  ── yes ──▶ 03 pipeline (05 if the pieces are independent)
        │ no
Is it "one of a few kinds" of request?  ── yes ──▶ 04 router
        │ no
Does one agent need to stay in charge?  ── yes ──▶ 02 supervisor
        │ no
                                              ──▶ 06 handoffs
Then add: 07 critic where quality matters, 08 approval wherever an agent can act.
```
