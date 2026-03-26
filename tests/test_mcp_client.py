"""Tests for atlas.tools.mcp_client."""

import pytest
from atlas.tools.mcp_client import MCPClient, load_mcp_tools


class TestLoadMCPTools:
    def test_none_url_returns_empty_list(self):
        tools = load_mcp_tools(None)
        assert tools == []

    def test_empty_string_url_returns_empty_list(self):
        tools = load_mcp_tools("")
        assert tools == []


class TestMCPClient:
    def test_init(self):
        client = MCPClient("ws://localhost:8765")
        assert client.url == "ws://localhost:8765"
        assert client.tools == []

    def test_as_langchain_tools_empty(self):
        client = MCPClient("ws://localhost:8765")
        assert client.as_langchain_tools() == []
