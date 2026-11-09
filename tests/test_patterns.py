"""Every pattern runs offline (MODEL=fake) and the right agents take part, in the right order."""
import os

os.environ["MODEL"] = "fake"

import asyncio

import pytest

import mas
from lab.mcp_tools import rag_tools

QUESTION = "Find Kafka candidates, check the evidence, and book the best one"
EXPECTED = {                     # pattern: the agents we expect to see, in order of first appearance
    "01": ["agent"],
    "02": ["lead", "sourcer", "screener", "coordinator"],
    "03": ["sourcer", "screener", "writer"],
    "04": ["router", "coordinator"],
    "05": ["sourcer", "screener-1", "screener-2", "screener-3", "writer"],
    "06": ["sourcer", "screener", "coordinator"],
    "07": ["sourcer", "writer", "critic"],
    "08": ["lead", "sourcer", "screener", "coordinator"],
}


def run(pid, question=QUESTION):
    async def go():
        async with rag_tools() as tools:
            return await mas.run_one(pid, mas.all_patterns()[pid], question, tools, auto=True, quiet=True)
    return asyncio.run(go())


def test_all_patterns_are_found():
    assert list(mas.all_patterns()) == list(EXPECTED)


@pytest.mark.parametrize("pid", list(EXPECTED))
def test_pattern_runs_with_the_expected_agents(pid):
    answer, rec, _, path = run(pid)
    assert answer
    assert rec.agents() == EXPECTED[pid]
    assert path.endswith(".html")


def test_supervisor_books_through_the_coordinator():
    _, rec, _, _ = run("02")
    tools = [e.text for e in rec.events if e.kind == "tool"]
    assert any(t.startswith("schedule_interview") for t in tools)
    booker = next(e.agent for e in rec.events if e.kind == "tool" and e.text.startswith("schedule_interview"))
    assert booker == "coordinator"                      # only the coordinator can book


def test_parallel_screeners_each_read_one_cv():
    _, rec, _, _ = run("05")
    for i in (1, 2, 3):
        reads = [e for e in rec.events if e.agent == f"screener-{i}" and e.kind == "tool"]
        assert len(reads) == 1 and reads[0].text.startswith("get_cv")


def test_critic_loop_revises_then_approves():
    answer, rec, _, _ = run("07")
    critic = [e.text for e in rec.events if e.agent == "critic" and e.kind == "answer"]
    assert critic[0].startswith("REVISE") and critic[-1].startswith("APPROVED")
    assert answer.startswith("REVISED")


def test_router_picks_the_screener_for_an_evidence_question():
    _, rec, _, _ = run("04", "Check the evidence in maya-shapiro.md")
    assert rec.agents() == ["router", "screener"]


def test_human_rejection_stops_the_booking(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    async def go():
        async with rag_tools() as tools:
            return await mas.run_one("08", mas.all_patterns()["08"], QUESTION, tools, auto=False, quiet=True)
    _, rec, _, _ = asyncio.run(go())
    assert "coordinator" not in rec.agents()
