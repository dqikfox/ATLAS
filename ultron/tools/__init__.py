"""MCP-style tool registry for ATLAS."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional


class Tool:
    """Represents a callable tool available to the model."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: Dict[str, Any],
    ) -> None:
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters  # JSON-schema style

    def call(self, **kwargs: Any) -> Any:
        return self.func(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry that stores and dispatches tool calls."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Optional[Callable[..., Any]] = None,
    ) -> Callable:
        """Register a tool.  Can be used as a decorator or called directly."""

        def decorator(f: Callable) -> Callable:
            self._tools[name] = Tool(name, description, f, parameters)
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")
        return self._tools[tool_name].call(**kwargs)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]

    def get_tools_description(self) -> str:
        lines: List[str] = []
        for tool in self._tools.values():
            lines.append(f"- **{tool.name}**: {tool.description}")
            for param_name, param_info in tool.parameters.get("properties", {}).items():
                param_description = param_info.get("description", "")
                lines.append(f"    `{param_name}`: {param_description}")
        return "\n".join(lines)
