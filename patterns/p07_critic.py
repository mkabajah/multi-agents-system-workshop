"""
PATTERN 07 · WRITER + CRITIC (a review loop)

    user ──▶ sourcer ──▶ writer ──▶ critic ──APPROVED──▶ answer
                           ▲          │
                           └─REVISE───┘   (at most 2 rounds)

The idea      One agent produces, a second agent with a different prompt checks, and the first one
              fixes what the critic says. Two narrow prompts beat one prompt that tries to do both.
Use it when   quality matters more than speed: reports, emails to candidates, anything sent outside.
Watch for     endless loops (cap the rounds) and a critic that approves everything (test it).
Try           python mas.py run 07 "Write a shortlist of Kafka candidates for the hiring manager"
"""
META = {"name": "Writer + critic loop", "agents": ["sourcer", "writer", "critic"]}
MAX_ROUNDS = 2


async def run(question, team, auto=False):
    evidence = await team.ask("sourcer", f"Find every candidate for this request: {question}")
    draft = await team.ask("writer", f"Request: {question}\nEvidence:\n{evidence}")
    for round_ in range(1, MAX_ROUNDS + 1):
        review = await team.ask("critic", f"Request: {question}\nEvidence:\n{evidence}\nDraft:\n{draft}")
        if review.strip().upper().startswith("APPROVED"):
            return draft
        team.rec.add("note", f"round {round_}: the critic asked for changes")
        draft = await team.ask("writer", f"Request: {question}\nEvidence:\n{evidence}\nYour draft:\n{draft}\n{review}")
    return draft
