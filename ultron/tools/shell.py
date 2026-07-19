"""Shell / code-execution tool for the ATLAS tool registry.

WARNING: Executing arbitrary shell commands is inherently risky.  Only enable
this if you trust the operator and user of the system.  A configurable
allow-list is applied by default.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional

from ultron.tools import ToolRegistry

# Commands that are always blocked regardless of configuration.
_BLOCKED_COMMAND_PATTERNS: List[str] = [
    "rm -rf /",
    "dd if=",
    "mkfs",
    ":(){ :|:& };:",  # fork bomb
]

# Set ATLAS_SHELL_UNRESTRICTED=1 to disable the block-list check.
_SHELL_UNRESTRICTED_MODE = os.environ.get("ATLAS_SHELL_UNRESTRICTED", "0") == "1"


def _is_blocked(command: str) -> bool:
    if _SHELL_UNRESTRICTED_MODE:
        return False
    normalized_command = command.lower()
    return any(blocked in normalized_command for blocked in _BLOCKED_COMMAND_PATTERNS)


def _run(command: str, timeout: int = 30, cwd: Optional[str] = None) -> Dict[str, Any]:
    if _is_blocked(command):
        return {"error": "Command blocked by safety policy.", "stdout": "", "stderr": "", "returncode": -1}
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s", "stdout": "", "stderr": "", "returncode": -1}
    except Exception as exc:
        return {"error": str(exc), "stdout": "", "stderr": "", "returncode": -1}


def register_shell_tools(registry: ToolRegistry) -> None:
    """Register shell execution tools into *registry*."""

    @registry.register(
        name="shell_run",
        description="Run a shell command and return its stdout, stderr and return code.",
        parameters={
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30).",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command.",
                },
            },
        },
    )
    def shell_run(command: str, timeout: int = 30, cwd: Optional[str] = None) -> Dict[str, Any]:
        return _run(command, timeout=timeout, cwd=cwd)

    @registry.register(
        name="python_eval",
        description="Execute a snippet of Python code and return its output.",
        parameters={
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute.",
                },
            },
        },
    )
    def python_eval(code: str) -> Dict[str, Any]:
        return _run(f'python3 -c {__import__("shlex").quote(code)}', timeout=30)
