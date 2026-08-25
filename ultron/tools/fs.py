"""File-system tools for the ATLAS tool registry."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from ultron.tools import ToolRegistry

# The root that all fs operations are sandboxed to.  Defaults to the user's
# home directory but can be overridden via the FS_ROOT environment variable.
_DEFAULT_ROOT = Path.home()


def _resolve(base: Path, user_path: str) -> Path:
    """Resolve *user_path* relative to *base*, rejecting traversal attacks."""
    resolved = (base / user_path).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise PermissionError(f"Access denied: path is outside sandbox root ({base})")
    return resolved


def register_fs_tools(registry: ToolRegistry, root: Path = _DEFAULT_ROOT) -> None:
    """Register all file-system tools into *registry*."""

    @registry.register(
        name="fs_list",
        description="List files and directories at a given path (relative to the sandbox root).",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to sandbox root. Defaults to '.' (root).",
                },
            },
        },
    )
    def fs_list(path: str = ".") -> Dict[str, Any]:
        target = _resolve(root, path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        entries: List[Dict[str, Any]] = []
        for item in sorted(target.iterdir()):
            item_stat = item.stat()
            entries.append(
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item_stat.st_size if item.is_file() else None,
                    "modified": item_stat.st_mtime,
                }
            )
        return {"path": str(target), "entries": entries}

    @registry.register(
        name="fs_read",
        description="Read the text content of a file.",
        parameters={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to sandbox root.",
                },
            },
        },
    )
    def fs_read(path: str) -> str:
        target = _resolve(root, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_text(errors="replace")

    @registry.register(
        name="fs_write",
        description="Write or overwrite a file with the given text content.",
        parameters={
            "type": "object",
            "required": ["path", "content"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to sandbox root.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write.",
                },
            },
        },
    )
    def fs_write(path: str, content: str) -> str:
        target = _resolve(root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Written {len(content)} bytes to {target}"

    @registry.register(
        name="fs_delete",
        description="Delete a file (not a directory).",
        parameters={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to sandbox root.",
                },
            },
        },
    )
    def fs_delete(path: str) -> str:
        target = _resolve(root, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        target.unlink()
        return f"Deleted {target}"

    @registry.register(
        name="fs_mkdir",
        description="Create a directory (and any missing parents).",
        parameters={
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to sandbox root.",
                },
            },
        },
    )
    def fs_mkdir(path: str) -> str:
        target = _resolve(root, path)
        target.mkdir(parents=True, exist_ok=True)
        return f"Created directory {target}"
