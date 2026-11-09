# What is a multi-agent system?

## First, one agent

An **agent** is a loop around a language model:

```
while True:
    reply = model(conversation, tools)        # the model reads everything so far
    if reply asks for a tool:                 # "call get_cv('maya-shapiro.md')"
        result = run that tool
        conversation += reply + result        # and loop again
    else:
        return reply                          # a plain answer: done
```

That's all `create_agent(...)` builds for you. One agent, with good tools and a clear prompt, solves a
lot. **Always start with one** (pattern 01).

## Then, several

A **multi-agent system** is several of those loops, each with:

- its **own prompt** (one narrow job: "you check evidence in CVs"),
- its **own tools** (the screener can read CVs but cannot book interviews),
- its **own conversation** (it doesn't see what the others read),

plus **a rule for who works next**. That rule is the *pattern*.

## Why split one agent into several?

| Problem with one big agent | How splitting helps |
|---|---|
| The context fills up: it read 10 CVs and now forgets the question | each screener reads ONE CV in its own conversation |
| 20 tools: it picks the wrong one | each agent sees 2–3 tools |
| One long prompt that tries to do everything | one short prompt per job, easier to test and fix |
| It can do anything, including things it shouldn't | only the coordinator can book; you put approval there |
| It's slow: one step at a time | independent work runs in parallel |

## Why NOT to split

- **Cost.** Every agent is more model calls. Run `python mas.py compare` and look at the "model" column.
- **Lost information.** Agent B only knows what agent A *wrote in its answer*, not what A read.
- **More ways to fail.** A wrong handoff, a ping-pong loop, a supervisor that forgets to ask the screener.
- **Harder to debug.** That's why this lab has a trace and a timeline.

> Rule of thumb: add an agent only when you can name the problem it solves
> (context, tools, permissions, parallelism, quality). "It feels more advanced" isn't one.

## The one question that separates the patterns

**Who decides what happens next?**

| Who decides | Patterns |
|---|---|
| **Your code** (fixed) | 03 pipeline · 05 parallel · 07 critic loop |
| **A model, once** | 04 router |
| **A model, every step** | 01 one agent · 02 supervisor · 08 supervisor + approval |
| **Whoever is in charge right now** | 06 handoffs |

Code-decided patterns are cheaper and predictable. Model-decided patterns are flexible and handle
surprises. Most real systems mix them: a fixed pipeline where one step is a supervisor.

## Words you'll see

| Word | Meaning here |
|---|---|
| **delegate** | one agent gives another a task and waits for its answer (02, 08) |
| **handoff / transfer** | one agent passes control to another and does not get it back (06) |
| **orchestration** | the code or agent that decides the order |
| **fan-out / fan-in** | start many agents at once / merge their answers (05) |
| **checkpointer** | saves a run so it can pause and resume, e.g. waiting for a person (08) |
| **MCP** | the standard way our agents reach the CV tools (a separate server process) |

Next: run `python mas.py run 01` and `python mas.py run 02`, and open `runs/latest.html` after each.
