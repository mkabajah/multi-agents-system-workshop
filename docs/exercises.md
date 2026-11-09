# Exercises

Start with the fake model (`MODEL=fake`), then repeat the starred ones with a real model.
Each has a hint; solutions are left to you.

## Warm-up: read the runs

1. Run `python mas.py compare`. Which pattern makes the fewest model calls? The most? Explain why,
   in one sentence each, using the HTML timelines.
2. Run 02 and 03 on the same question. Both use sourcer → screener. **Who decides** the order in each?
   Where do you see that in the timeline? *(Hint: the column that has the "delegates" cards.)*
3. In pattern 05, open the timeline. Did the three screeners really run at the same time? How can you
   tell? *(Hint: the times on the cards.)*

## Change a pattern

4. **Cap it.** In pattern 05, change the cap from 3 to 2 CVs. Run it. What changes in the table from
   `compare`?
5. **Router fallback.** Run `python mas.py run 04 "hello"`. Which agent handled it, and why? Add a
   fourth choice, `writer`, for general questions. *(Hint: `prompts.ROUTER` and the list in `p04_router.py`.)*
6. **Approval on more tools.** In pattern 08, also require approval before `ask_screener`. Run it
   without `--auto` and reject the screener. What does the lead answer?
7. ⭐ **Stricter critic.** With a real model, make the critic reject any draft that has more than 3
   candidates. Does the writer fix it in one round?

## Build something

8. **Pipeline + parallel.** Write `patterns/p09_hybrid.py`: sourcer (once) → screeners in parallel →
   critic loop on the writer's answer. Add it to the tests.
9. **A new specialist.** Add an `emailer` agent that has `send_email` (from `lab/actions.py`). Put it
   behind human approval. Which pattern did you start from, and why?
10. ⭐ **Break it on purpose.** With a real model, find a question that makes the handoffs pattern
    (06) loop or stop early. Fix it with one sentence in a prompt. Show the before/after timelines.

## Discuss

11. You must build an agent that answers HR questions from 2,000 policy documents and can open tickets.
    Which pattern(s) would you pick? Draw it like the diagrams at the top of each pattern file.
12. When is a multi-agent system **worse** than pattern 01? Give two concrete examples from your runs.
