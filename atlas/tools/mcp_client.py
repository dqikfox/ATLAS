"""MCP client integration for ATLAS.

Connects to an external MCP server and wraps its tools as LangChain
:class:`~langchain_core.tools.BaseTool` instances so they can be used by
the ATLAS agent alongside the built-in computer-control tools.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPClientTool:
    """A lightweight wrapper that represents a single tool exposed by an MCP server."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        call_fn,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self._call_fn = call_fn

    def __call__(self, **kwargs: Any) -> Any:
        return asyncio.run(self._call_fn(**kwargs))

    def as_langchain_tool(self):
        """Return a :class:`langchain_core.tools.StructuredTool` for this MCP tool."""
        from langchain_core.tools import StructuredTool

        call_fn = self._call_fn
        name = self.name
        description = self.description

        async def _arun(**kwargs: Any) -> str:
            result = await call_fn(**kwargs)
            if isinstance(result, (dict, list)):
                return json.dumps(result)
            return str(result)

        def _run(**kwargs: Any) -> str:
            return asyncio.run(_arun(**kwargs))

        return StructuredTool.from_function(
            func=_run,
            coroutine=_arun,
            name=name,
            description=description,
        )


class MCPClient:
    """Async client that connects to an MCP server and retrieves its tools.

    Parameters
    ----------
    url:
        WebSocket URL of the MCP server, e.g. ``"ws://localhost:8765"``.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._tools: List[MCPClientTool] = []

    async def connect(self) -> None:
        """Connect to the MCP server and discover available tools."""
        try:
            import websockets  # type: ignore

            async with websockets.connect(self.url) as ws:
                await ws.send(json.dumps({"type": "list_tools"}))
                response = json.loads(await ws.recv())
                tools_data = response.get("tools", [])
                self._tools = [
                    self._make_tool(td) for td in tools_data
                ]
                logger.info(
                    "Connected to MCP server at %s – discovered %d tool(s).",
                    self.url,
                    len(self._tools),
                )
        except Exception as exc:
            logger.warning("Could not connect to MCP server at %s: %s", self.url, exc)

    def _make_tool(self, tool_data: Dict[str, Any]) -> MCPClientTool:
        name = tool_data["name"]
        description = tool_data.get("description", "")
        input_schema = tool_data.get("inputSchema", {})
        url = self.url

        async def call_fn(**kwargs: Any) -> Any:
            import websockets  # type: ignore

            async with websockets.connect(url) as ws:
                payload = {"type": "call_tool", "name": name, "arguments": kwargs}
                await ws.send(json.dumps(payload))
                result = json.loads(await ws.recv())
                return result.get("result")

        return MCPClientTool(
            name=name,
            description=description,
            input_schema=input_schema,
            call_fn=call_fn,
        )

    @property
    def tools(self) -> List[MCPClientTool]:
        """Return the list of tools discovered from the MCP server."""
        return list(self._tools)

    def as_langchain_tools(self):
        """Return all MCP tools as LangChain tool objects."""
        return [t.as_langchain_tool() for t in self._tools]


def load_mcp_tools(url: Optional[str]) -> list:
    """Synchronously connect to *url* and return LangChain-compatible tools.

    Returns an empty list if *url* is ``None`` or the server is unreachable.
    """
    if not url:
        return []
    client = MCPClient(url)
    asyncio.run(client.connect())
    return client.as_langchain_tools()
