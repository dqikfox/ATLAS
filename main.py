#!/usr/bin/env python3
"""ATLAS – AI-powered computer-using agent.

Usage
-----
Interactive chat loop (default)::

    python main.py

Single task::

    python main.py --task "Open a terminal and list the home directory"

Start the native MCP server (stdio)::

    python main.py --mcp-server

Switch to Ollama::

    ATLAS_MODEL_PROVIDER=ollama OLLAMA_MODEL=llama3.2 python main.py

Connect to an external MCP server and expose its tools to the agent::

    python main.py --mcp-client ws://localhost:8765
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Optional

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("atlas.main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="atlas",
        description="ATLAS – AI-powered computer-using agent",
    )
    parser.add_argument(
        "--task",
        metavar="TASK",
        help="Run a single task and exit.",
    )
    parser.add_argument(
        "--mcp-server",
        action="store_true",
        help="Start the native ATLAS MCP server (stdio transport) and exit.",
    )
    parser.add_argument(
        "--mcp-client",
        metavar="URL",
        help="Connect to an external MCP server at URL and add its tools to the agent.",
    )
    parser.add_argument(
        "--provider",
        metavar="PROVIDER",
        help="Override the model provider ('openai' or 'ollama').",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        help=(
            "Override the model name "
            "(e.g. 'gpt-4o' for OpenAI or 'llama3.2' for Ollama)."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose LangChain agent output.",
    )
    return parser.parse_args()


def _build_agent(args: argparse.Namespace):
    """Build and return an :class:`~atlas.agent.ATLASAgent`."""
    import os

    from atlas.config import load_config
    from atlas.agent import ATLASAgent
    from atlas.tools.mcp_client import load_mcp_tools

    if args.provider:
        os.environ["ATLAS_MODEL_PROVIDER"] = args.provider
    if args.model:
        provider = os.getenv("ATLAS_MODEL_PROVIDER", "openai").lower()
        if provider == "ollama":
            os.environ["OLLAMA_MODEL"] = args.model
        else:
            os.environ["OPENAI_MODEL"] = args.model

    cfg = load_config()
    extra_tools = load_mcp_tools(args.mcp_client)

    return ATLASAgent(cfg=cfg, extra_tools=extra_tools, verbose=args.verbose)


def run_mcp_server() -> None:
    """Start the native ATLAS MCP server and block until interrupted."""
    from atlas.mcp.server import run_server

    print("Starting ATLAS MCP server (stdio)…  Press Ctrl-C to stop.", flush=True)
    asyncio.run(run_server())


def run_single_task(args: argparse.Namespace) -> None:
    """Run a single task and print the result."""
    agent = _build_agent(args)
    print(f"\n🤖 ATLAS › {args.task}\n", flush=True)
    result = agent.run(args.task)
    print(result)


def run_interactive(args: argparse.Namespace) -> None:
    """Start an interactive REPL loop."""
    agent = _build_agent(args)
    provider = agent.cfg.model_provider
    model = (
        agent.cfg.ollama_model
        if provider == "ollama"
        else agent.cfg.openai_model
    )
    print(
        f"\n🤖 ATLAS interactive shell  [provider={provider}, model={model}]"
        "\nType your task and press Enter.  Type 'exit' or Ctrl-C to quit.\n",
        flush=True,
    )
    while True:
        try:
            task = input("ATLAS › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not task:
            continue
        if task.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break
        try:
            result = agent.run(task)
            print(f"\n{result}\n")
        except Exception as exc:
            logger.exception("Agent error")
            print(f"Error: {exc}\n")


def main() -> None:
    args = parse_args()

    if args.mcp_server:
        run_mcp_server()
        return

    if args.task:
        run_single_task(args)
        return

    run_interactive(args)


if __name__ == "__main__":
    main()
