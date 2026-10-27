"""Tests for the ATLAS Web UI and associated tool modules."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

# Make sure the repo root is on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ultron.tools import ToolRegistry
from ultron.tools.fs import register_fs_tools
from ultron.tools.shell import register_shell_tools


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def registry(tmp_path):
    r = ToolRegistry()
    register_fs_tools(r, root=tmp_path)
    register_shell_tools(r)
    return r, tmp_path


@pytest.fixture()
def flask_client():
    from web.app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ── ToolRegistry ─────────────────────────────────────────────────────────────


class TestToolRegistry:
    def test_register_and_call(self):
        r = ToolRegistry()

        @r.register(
            name="greet",
            description="Say hello",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        def greet(name="world"):
            return f"Hello, {name}!"

        assert r.call_tool("greet", name="ATLAS") == "Hello, ATLAS!"

    def test_list_tools(self):
        r = ToolRegistry()
        r.register(
            name="noop",
            description="Does nothing",
            parameters={"type": "object"},
            func=lambda: None,
        )
        tools = r.list_tools()
        assert any(t["name"] == "noop" for t in tools)

    def test_unknown_tool_raises(self):
        r = ToolRegistry()
        with pytest.raises(KeyError):
            r.call_tool("does_not_exist")

    def test_tools_description(self):
        r = ToolRegistry()
        r.register(
            name="example",
            description="An example tool",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "string", "description": "value of x"}},
            },
            func=lambda x: x,
        )
        desc = r.get_tools_description()
        assert "example" in desc
        assert "An example tool" in desc


# ── File-system tools ─────────────────────────────────────────────────────────


class TestFsTools:
    def test_fs_list_root(self, registry):
        r, tmp = registry
        (tmp / "a.txt").write_text("hello")
        (tmp / "subdir").mkdir()
        result = r.call_tool("fs_list", path=".")
        names = [e["name"] for e in result["entries"]]
        assert "a.txt" in names
        assert "subdir" in names

    def test_fs_read_write(self, registry):
        r, tmp = registry
        r.call_tool("fs_write", path="hello.txt", content="world")
        content = r.call_tool("fs_read", path="hello.txt")
        assert content == "world"

    def test_fs_delete(self, registry):
        r, tmp = registry
        (tmp / "del.txt").write_text("bye")
        r.call_tool("fs_delete", path="del.txt")
        assert not (tmp / "del.txt").exists()

    def test_fs_mkdir(self, registry):
        r, tmp = registry
        r.call_tool("fs_mkdir", path="new/nested/dir")
        assert (tmp / "new" / "nested" / "dir").is_dir()

    def test_path_traversal_blocked(self, registry):
        r, _ = registry
        with pytest.raises(PermissionError):
            r.call_tool("fs_read", path="../../../etc/passwd")


# ── Shell tools ────────────────────────────────────────────────────────────────


class TestShellTools:
    def test_shell_run_success(self, registry):
        r, _ = registry
        result = r.call_tool("shell_run", command="echo atlas_test")
        assert result["stdout"].strip() == "atlas_test"
        assert result["returncode"] == 0

    def test_shell_run_error(self, registry):
        r, _ = registry
        result = r.call_tool("shell_run", command="exit 42", timeout=5)
        assert result["returncode"] != 0

    def test_python_eval(self, registry):
        r, _ = registry
        result = r.call_tool("python_eval", code="print(2 + 2)")
        assert result["stdout"].strip() == "4"


# ── Flask endpoints ────────────────────────────────────────────────────────────


class TestFlaskApp:
    def test_index(self, flask_client):
        r = flask_client.get("/")
        assert r.status_code == 200
        assert b"ATLAS" in r.data

    def test_api_tools(self, flask_client):
        r = flask_client.get("/api/tools")
        data = r.get_json()
        assert "tools" in data
        tool_names = [t["name"] for t in data["tools"]]
        assert "fs_list" in tool_names
        assert "shell_run" in tool_names
        assert "ocr_extract" in tool_names

    def test_api_chat_no_model(self, flask_client):
        r = flask_client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hello"}], "use_tools": False},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert "content" in data

    def test_api_fs_list(self, flask_client):
        r = flask_client.get("/api/fs/list?path=.")
        assert r.status_code == 200
        data = r.get_json()
        assert "entries" in data

    def test_api_fs_traversal_blocked(self, flask_client):
        r = flask_client.get("/api/fs/read?path=../../../etc/passwd")
        assert r.status_code == 403

    def test_api_tools_call(self, flask_client):
        r = flask_client.post(
            "/api/tools/call",
            json={"tool": "shell_run", "args": {"command": "echo hi"}},
        )
        assert r.status_code == 200
        assert r.get_json()["result"]["stdout"].strip() == "hi"

    def test_api_tools_call_unknown(self, flask_client):
        r = flask_client.post(
            "/api/tools/call",
            json={"tool": "does_not_exist", "args": {}},
        )
        assert r.status_code == 404

    def test_api_ocr_no_file(self, flask_client):
        r = flask_client.post("/api/ocr")
        assert r.status_code == 400

    def test_api_stt_no_file(self, flask_client):
        r = flask_client.post("/api/stt")
        assert r.status_code == 400

    def test_api_chat_stream(self, flask_client):
        msgs = json.dumps([{"role": "user", "content": "hi"}])
        r = flask_client.get(f"/api/chat/stream?messages={msgs}&use_tools=false")
        assert r.status_code == 200
        assert r.content_type.startswith("text/event-stream")
