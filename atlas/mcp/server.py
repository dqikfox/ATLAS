"""Native MCP server for ATLAS.

Exposes the ATLAS computer-control tools as an MCP server so that other
agents or IDE extensions (e.g. VS Code with GitHub Copilot MCP support)
can discover and invoke them programmatically.

Usage
-----
Run directly::

    python -m atlas.mcp.server

Or import and start programmatically::

    from atlas.mcp.server import create_mcp_app, run_server
    run_server()
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from atlas.tools.computer import (
    ALL_TOOLS,
    apply_config,
    click,
    double_click,
    get_screen_size,
    hotkey,
    move_mouse,
    press_key,
    run_shell_command,
    scroll,
    take_screenshot,
    type_text,
)

logger = logging.getLogger(__name__)

_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


def _build_mcp_tool_schema(lc_tool) -> Tool:
    """Convert a LangChain tool to an MCP :class:`Tool` schema."""
    return Tool(
        name=lc_tool.name,
        description=lc_tool.description or "",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    )


def create_mcp_app() -> Server:
    """Create and configure the ATLAS MCP :class:`Server` instance."""
    apply_config()
    server = Server("atlas")

    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        return ListToolsResult(
            tools=[_build_mcp_tool_schema(t) for t in ALL_TOOLS]
        )

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
        lc_tool = _TOOL_MAP.get(name)
        if lc_tool is None:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
        try:
            result = lc_tool.invoke(arguments)
            return CallToolResult(
                content=[TextContent(type="text", text=str(result))],
                isError=False,
            )
        except Exception as exc:
            logger.exception("Error invoking tool %s", name)
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {exc}")],
                isError=True,
            )

    return server


async def run_server() -> None:
    """Start the MCP server over stdio (standard MCP transport)."""
    app = create_mcp_app()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server())
