# Reading a trace

Every run prints a live trace and writes `runs/latest.html`. Both show the same events.

## The terminal

```
➜ code         code → lead: Shortlist Kafka candidates…        your code starts the first agent
▶ lead         Shortlist Kafka candidates…                     the lead starts on its task
· lead         model call                                      the lead's model thinks (≈ cost)
➜ lead         lead → sourcer: Find every candidate with: kafka.   the lead delegates
   ▶ sourcer      Find every candidate with: kafka.           indented = called BY the lead
   🔧 sourcer      find_candidates({'skill': 'kafka'…})        a tool call
   ← sourcer      { "cv": "maya-shapiro.md" … }                   what the tool returned
   ✔ sourcer      Found: maya-shapiro.md, …                       the sourcer's final answer…
✔ lead         …                                               …which goes back to the lead
```

| Icon | Event | Meaning |
|---|---|---|
| ➜ | delegate | one agent (or your code) gives another a task |
| ▶ | start | an agent starts, with the task it was given |
| · | think | one model call (dimmed). Count these: that's your cost |
| 🔧 | tool | a real tool call (MCP or action) |
| ← | result | what the tool returned (shortened) |
| ✔ | answer | an agent's final answer |
| ℹ | note | something the pattern code says: a router fallback, a critic round, a pause |

**Indentation = depth.** An agent called by another agent is indented under it. In the pipeline (03)
nothing is indented: your code calls each agent in turn. In the supervisor (02) everything except the
lead is indented: the lead calls them.

## The HTML timeline

One **column per agent** (the first column, `code`, is your Python orchestration). Time flows down.
Read it top to bottom and ask:

1. **Who started?** The first card in the `code` column.
2. **Who decided the next step?** Look for "delegates" cards. In the column of your code → a fixed
   pattern. In an agent's column → that agent decided.
3. **Where did the time and money go?** Count the "model call" cards per column.
4. **Did anyone do something they shouldn't?** Only the coordinator column should have
   `schedule_interview`.

Buttons: **▶ Replay** animates the run, **Next step →** (or the → key) goes one event at a time:
good for explaining a run to someone.

## What to compare between patterns

| Look at | 01 one agent | 02 supervisor | 03 pipeline | 05 parallel |
|---|---|---|---|---|
| columns | 1 | 4 | 3 | 5 |
| model calls | fewest | most | few | medium |
| who reads the CVs | the one agent | the screener | the screener | 3 screeners, 1 CV each |
| indentation | none | yes | none | none |

## With a real model

The fake model always does the same thing. A real model doesn't: the supervisor might skip the
screener, the sourcer might hand off too early, the critic might approve a bad draft. **That is the
point.** Use the timeline to find *which agent* made the wrong decision, then fix *that agent's prompt*
in `lab/prompts.py` or the tool's docstring.
