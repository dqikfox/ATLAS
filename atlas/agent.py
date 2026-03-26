"""ATLAS agent – the core AI agent that controls the computer.

The agent is built with LangChain's tool-calling agent pattern.  It receives
a list of computer-control tools and, optionally, additional tools fetched
from an MCP server.  The underlying LLM defaults to OpenAI but can be
switched to Ollama (or any future provider) via the ``ATLAS_MODEL_PROVIDER``
environment variable.

Example
-------
::

    from atlas.agent import ATLASAgent
    from atlas.config import load_config

    cfg = load_config()
    agent = ATLASAgent(cfg)
    result = agent.run("Open a terminal and print the current date.")
    print(result)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from atlas.config import AtlasConfig, load_config
from atlas.models import get_llm
from atlas.tools.computer import ALL_TOOLS, apply_config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are ATLAS, an advanced AI agent designed to control and automate a computer.

You have access to tools that allow you to:
- Capture screenshots to observe the screen
- Move the mouse, click, double-click, and scroll
- Type text and press keyboard shortcuts
- Run shell commands
- Query the screen resolution

Guidelines
----------
1. Always take a screenshot first to understand the current state of the screen.
2. Think step by step before acting.
3. Use the least invasive action that achieves the goal.
4. When you have completed a task, summarise what you did and the outcome.
5. If a task is ambiguous, ask for clarification before acting.
"""


class ATLASAgent:
    """High-level wrapper around the LangChain tool-calling agent.

    Parameters
    ----------
    cfg:
        :class:`~atlas.config.AtlasConfig` instance.  If *None* the default
        config is loaded from environment variables.
    extra_tools:
        Additional LangChain tools to register alongside the built-in
        computer-control tools (e.g. tools loaded from an MCP server).
    verbose:
        Whether to enable verbose LangChain output.
    """

    def __init__(
        self,
        cfg: Optional[AtlasConfig] = None,
        extra_tools: Optional[List[Any]] = None,
        verbose: bool = False,
    ) -> None:
        self.cfg = cfg or load_config()
        apply_config(self.cfg.pyautogui_pause)

        llm = get_llm(self.cfg)
        tools = list(ALL_TOOLS) + (extra_tools or [])

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(llm, tools, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=verbose,
            handle_parsing_errors=True,
            max_iterations=50,
        )
        logger.info(
            "ATLAS agent initialised with provider=%s, tools=%d",
            self.cfg.model_provider,
            len(tools),
        )

    def run(self, task: str) -> str:
        """Execute *task* and return the agent's final response.

        Parameters
        ----------
        task:
            Natural-language description of what the agent should do.
        """
        result: Dict[str, Any] = self._executor.invoke({"input": task})
        return result.get("output", "")

    async def arun(self, task: str) -> str:
        """Asynchronous version of :meth:`run`."""
        result: Dict[str, Any] = await self._executor.ainvoke({"input": task})
        return result.get("output", "")
