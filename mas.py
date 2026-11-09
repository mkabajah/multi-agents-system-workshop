"""
mas.py · run any multi-agent pattern and watch it work.

    python mas.py list                              the 8 patterns, one line each
    python mas.py run 02 "your question"            run one pattern (live trace + an HTML timeline)
    python mas.py run 02                            ... with the pattern's example question
    python mas.py compare "your question"           run ALL patterns on one question, print a table
    python mas.py explain 02                        print the pattern's explanation (its docstring)

Options:  --auto   approve human-approval steps automatically (pattern 08)
          --quiet  no live trace, only the answer

Every run writes runs/<pattern>-<time>.html and runs/latest.html: open it in a browser to replay the run.
"""
import argparse
import asyncio
import importlib
import pkgutil
import re
import sys
import time

from lab import config
from lab.mcp_tools import rag_tools
from lab.team import Team
from lab.trace import Recorder
from lab import viewer
import patterns

if hasattr(sys.stdout, "reconfigure"):          # Windows terminals: print emoji and arrows safely
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def all_patterns() -> dict:
    """{'01': module, '02': module, ...} for every patterns/pNN_*.py file."""
    found = {}
    for m in pkgutil.iter_modules(patterns.__path__):
        if re.match(r"p\d\d_", m.name):
            found[m.name[1:3]] = importlib.import_module(f"patterns.{m.name}")
    return dict(sorted(found.items()))


def example_question(module) -> str:
    """The question on the 'Try' line of the pattern's docstring."""
    hit = re.search(r'Try\s+python mas\.py run \d\d "([^"]+)"', module.__doc__ or "")
    return hit.group(1) if hit else "Who knows Kafka?"


def pick(pid: str):
    pats = all_patterns()
    key = pid.zfill(2)
    if key not in pats:
        sys.exit(f"No pattern '{pid}'. Try: python mas.py list")
    return key, pats[key]


async def run_one(pid, module, question, tools, auto=False, quiet=False):
    """Run one pattern on one question; return (answer, recorder, seconds, html path)."""
    rec = Recorder(quiet=quiet)
    team = Team(tools, rec)
    t0 = time.perf_counter()
    answer = await module.run(question, team, auto=auto)
    seconds = time.perf_counter() - t0
    path = viewer.save(rec, pid, module.META, question, answer, seconds)
    return answer, rec, seconds, path


async def main(args):
    config.check()
    pats = all_patterns()
    if args.cmd == "list":
        print(f"\n  model: {config.MODEL}\n")
        for pid, m in pats.items():
            print(f"  {pid}  {m.META['name']:<30} {' → '.join(m.META['agents'])}")
        print('\n  python mas.py run 02            run one (with its example question)')
        print('  python mas.py explain 02        what it is, when to use it\n')
        return
    if args.cmd == "explain":
        _, m = pick(args.pattern)
        print(m.__doc__)
        return

    async with rag_tools() as tools:
        if args.cmd == "run":
            pid, m = pick(args.pattern)
            question = args.question or example_question(m)
            print(f"\n\033[1m{pid} · {m.META['name']}\033[0m   model: {config.MODEL}\n❓ {question}\n")
            answer, rec, secs, path = await run_one(pid, m, question, tools, args.auto, args.quiet)
            print(f"\n\033[1m✔ Answer\033[0m\n{answer}\n")
            print(f"agents: {len(rec.agents())} · model calls: {rec.model_calls} · tool calls: {rec.tool_calls}"
                  f" · {secs:.1f}s" + (f" · tokens: {rec.tokens}" if rec.tokens else ""))
            print(f"timeline: open {path}  (or runs/latest.html)\n")
        elif args.cmd == "compare":
            question = args.question or "Find Kafka candidates, check the evidence, and book the best one"
            print(f"\n❓ {question}   (model: {config.MODEL})\n")
            print(f"  {'pattern':<34}{'agents':>7}{'model':>7}{'tools':>7}{'secs':>7}")
            for pid, m in pats.items():
                _, rec, secs, _ = await run_one(pid, m, question, tools, auto=True, quiet=True)
                print(f"  {pid + ' ' + m.META['name']:<34}{len(rec.agents()):>7}{rec.model_calls:>7}"
                      f"{rec.tool_calls:>7}{secs:>7.1f}")
            print("\n  model = model calls (≈ cost), tools = tool calls. Fewer is cheaper; more agents isn't better by itself.\n")


def cli(argv=None):
    p = argparse.ArgumentParser(description="Run multi-agent patterns and watch them work.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    e = sub.add_parser("explain"); e.add_argument("pattern")
    r = sub.add_parser("run"); r.add_argument("pattern"); r.add_argument("question", nargs="?")
    c = sub.add_parser("compare"); c.add_argument("question", nargs="?")
    for s in (r, c):
        s.add_argument("--auto", action="store_true", help="approve human-approval steps automatically")
        s.add_argument("--quiet", action="store_true", help="no live trace")
    return p.parse_args(argv)


if __name__ == "__main__":
    asyncio.run(main(cli()))
