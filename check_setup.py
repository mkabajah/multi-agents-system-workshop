"""
python check_setup.py · checks your setup in ~10 seconds and tells you what to fix.

    1. Python version          3.10 to 3.13
    2. packages                langchain, langgraph, the MCP adapters
    3. .env and MODEL          which model the lab will use
    4. the CV MCP server       starts, lists its tools
    5. one pattern, offline    runs pattern 03 with the fake model
"""
import asyncio
import importlib.util
import os
import sys

OK, BAD = "\033[32m✔\033[0m", "\033[31m✘\033[0m"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    v = sys.version_info
    print(f"{OK if (3, 10) <= v[:2] <= (3, 13) else BAD} Python {v.major}.{v.minor}"
          + ("" if (3, 10) <= v[:2] <= (3, 13) else "   → use Python 3.12 (e.g. `python3.12 -m venv .venv`)"))
    missing = [m for m in ("langchain", "langgraph", "langchain_mcp_adapters", "mcp") if not importlib.util.find_spec(m)]
    if missing:
        sys.exit(f"{BAD} missing packages: {', '.join(missing)}   → pip install -r requirements.txt")
    print(f"{OK} packages")

    from lab import config
    print(f"{OK if os.path.exists('.env') else BAD} .env " + ("found" if os.path.exists('.env') else
          "missing   → copy .env.example to .env (MODEL=fake works with no key)"))
    print(f"{OK} MODEL = {config.MODEL}")

    async def server_and_pattern():
        from lab.mcp_tools import rag_tools
        async with rag_tools() as tools:
            print(f"{OK} CV MCP server: {', '.join(t.name for t in tools)}")
        os.environ["MODEL"] = config.MODEL = "fake"
        import mas
        async with rag_tools() as tools:
            answer, rec, _, path = await mas.run_one("03", mas.all_patterns()["03"], "Who knows Kafka?", tools, quiet=True)
        print(f"{OK} pattern 03 ran offline: {len(rec.agents())} agents, {rec.model_calls} model calls → {path}")

    asyncio.run(server_and_pattern())
    print("\nAll good. Next:  python mas.py list")


if __name__ == "__main__":
    main()
