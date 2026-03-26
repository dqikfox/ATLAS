"""Computer-control tools powered by PyAutoGUI.

These tools are registered with the ATLAS LangChain agent so the LLM can
interact with the desktop: take screenshots, move the mouse, click, type,
scroll, and run shell commands.

All tools respect the ``pyautogui_pause`` and ``safe_mode`` settings from
:class:`atlas.config.AtlasConfig`.

.. note::
   PyAutoGUI requires a graphical display.  In headless environments the
   module still imports successfully but each tool will return an error
   message indicating that no display is available.
"""

from __future__ import annotations

import base64
import subprocess
from io import BytesIO
from typing import Optional

from langchain_core.tools import tool

try:
    import pyautogui as _pyautogui

    _PYAUTOGUI_AVAILABLE = True
    _pyautogui.FAILSAFE = True  # move mouse to top-left corner to abort
except Exception:
    _pyautogui = None  # type: ignore[assignment]
    _PYAUTOGUI_AVAILABLE = False

_NO_DISPLAY_MSG = (
    "PyAutoGUI is not available in this environment "
    "(no graphical display detected)."
)


def apply_config(pause: float = 0.5) -> None:
    """Set the global PyAutoGUI action pause (seconds)."""
    if _PYAUTOGUI_AVAILABLE:
        _pyautogui.PAUSE = pause


# ── Screenshot ────────────────────────────────────────────────────────────────

@tool
def take_screenshot() -> str:
    """Capture the current screen and return it as a base64-encoded PNG string.

    Use this tool to observe the current state of the desktop before
    deciding which action to take next.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    buf = BytesIO()
    screenshot = _pyautogui.screenshot()
    screenshot.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Mouse ─────────────────────────────────────────────────────────────────────

@tool
def move_mouse(x: int, y: int) -> str:
    """Move the mouse cursor to screen coordinates (*x*, *y*).

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    _pyautogui.moveTo(x, y)
    return f"Mouse moved to ({x}, {y})."


@tool
def click(x: int, y: int, button: str = "left") -> str:
    """Click a mouse button at screen coordinates (*x*, *y*).

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
        button: One of ``"left"``, ``"right"``, or ``"middle"``.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    if button not in ("left", "right", "middle"):
        return f"Invalid button '{button}'. Use 'left', 'right', or 'middle'."
    _pyautogui.click(x, y, button=button)
    return f"Clicked {button} button at ({x}, {y})."


@tool
def double_click(x: int, y: int) -> str:
    """Double-click the left mouse button at screen coordinates (*x*, *y*).

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    _pyautogui.doubleClick(x, y)
    return f"Double-clicked at ({x}, {y})."


@tool
def scroll(x: int, y: int, clicks: int) -> str:
    """Scroll the mouse wheel at (*x*, *y*).

    Args:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
        clicks: Number of scroll steps. Positive scrolls up, negative scrolls down.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    _pyautogui.scroll(clicks, x=x, y=y)
    direction = "up" if clicks > 0 else "down"
    return f"Scrolled {abs(clicks)} clicks {direction} at ({x}, {y})."


# ── Keyboard ──────────────────────────────────────────────────────────────────

@tool
def type_text(text: str) -> str:
    """Type *text* at the current cursor position using the keyboard.

    Args:
        text: The text string to type.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    _pyautogui.typewrite(text, interval=0.03)
    return f"Typed: {text!r}"


@tool
def press_key(key: str) -> str:
    """Press a single keyboard key.

    Args:
        key: A PyAutoGUI key name, e.g. ``"enter"``, ``"escape"``, ``"ctrl"``,
             ``"tab"``, ``"f5"``, ``"backspace"``.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    _pyautogui.press(key)
    return f"Pressed key: {key!r}"


@tool
def hotkey(*keys: str) -> str:
    """Press a keyboard shortcut (multiple keys simultaneously).

    Args:
        keys: Key names in the order they should be held, e.g.
              ``"ctrl", "c"`` for copy.
    """
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    _pyautogui.hotkey(*keys)
    return f"Hotkey pressed: {' + '.join(keys)}"


# ── Shell ─────────────────────────────────────────────────────────────────────

@tool
def run_shell_command(command: str, timeout: Optional[int] = 30) -> str:
    """Run a shell command and return its combined stdout/stderr output.

    Args:
        command: Shell command string to execute.
        timeout: Maximum seconds to wait for the command to finish (default 30).

    Returns:
        Combined stdout and stderr output, or an error message.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds."
    except Exception as exc:
        return f"Error running command: {exc}"


# ── Screen info ───────────────────────────────────────────────────────────────

@tool
def get_screen_size() -> str:
    """Return the current screen resolution as ``width x height``."""
    if not _PYAUTOGUI_AVAILABLE:
        return _NO_DISPLAY_MSG
    size = _pyautogui.size()
    return f"{size.width}x{size.height}"


# ── Convenience export ────────────────────────────────────────────────────────

ALL_TOOLS = [
    take_screenshot,
    move_mouse,
    click,
    double_click,
    scroll,
    type_text,
    press_key,
    hotkey,
    run_shell_command,
    get_screen_size,
]
