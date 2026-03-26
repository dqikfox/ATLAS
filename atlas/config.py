"""ATLAS configuration management.

Reads settings from environment variables and an optional ``.env`` file.
The active model provider (``openai`` or ``ollama``) is controlled by the
``ATLAS_MODEL_PROVIDER`` environment variable and defaults to ``openai``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AtlasConfig:
    # ── Model provider ────────────────────────────────────────────────────────
    # "openai" (default) or "ollama"
    model_provider: str = field(
        default_factory=lambda: os.getenv("ATLAS_MODEL_PROVIDER", "openai")
    )

    # ── OpenAI settings ───────────────────────────────────────────────────────
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o")
    )
    openai_temperature: float = field(
        default_factory=lambda: float(os.getenv("OPENAI_TEMPERATURE", "0"))
    )

    # ── Ollama settings ───────────────────────────────────────────────────────
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2")
    )

    # ── MCP settings ─────────────────────────────────────────────────────────
    mcp_server_host: str = field(
        default_factory=lambda: os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    )
    mcp_server_port: int = field(
        default_factory=lambda: int(os.getenv("MCP_SERVER_PORT", "8765"))
    )

    # ── PyAutoGUI safety ─────────────────────────────────────────────────────
    # Number of seconds before each action (set to 0 to disable)
    pyautogui_pause: float = field(
        default_factory=lambda: float(os.getenv("PYAUTOGUI_PAUSE", "0.5"))
    )
    # When True the agent asks for confirmation before destructive actions
    safe_mode: bool = field(
        default_factory=lambda: os.getenv("ATLAS_SAFE_MODE", "true").lower()
        not in ("false", "0", "no")
    )


def load_config() -> AtlasConfig:
    """Return an :class:`AtlasConfig` populated from environment variables."""
    return AtlasConfig()
