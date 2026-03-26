"""Tests for atlas.tools.computer."""

import pytest

from atlas.tools.computer import (
    ALL_TOOLS,
    apply_config,
    run_shell_command,
    get_screen_size,
    take_screenshot,
    _PYAUTOGUI_AVAILABLE,
)


class TestComputerTools:
    def test_all_tools_count(self):
        assert len(ALL_TOOLS) == 10

    def test_all_tools_have_name_and_description(self):
        for tool in ALL_TOOLS:
            assert tool.name, f"Tool missing name: {tool}"
            assert tool.description, f"Tool missing description: {tool.name}"

    def test_apply_config_no_crash(self):
        apply_config(0.0)
        apply_config(1.0)

    def test_run_shell_command_echo(self):
        result = run_shell_command.invoke({"command": "echo atlas"})
        assert "atlas" in result

    def test_run_shell_command_timeout(self):
        result = run_shell_command.invoke({"command": "sleep 10", "timeout": 1})
        assert "timed out" in result.lower()

    def test_run_shell_command_error_output(self):
        result = run_shell_command.invoke({"command": "ls /nonexistent_path_xyz"})
        assert result  # should return stderr

    def test_no_display_returns_message(self):
        if _PYAUTOGUI_AVAILABLE:
            pytest.skip("PyAutoGUI is available – skipping headless-only test")
        result = take_screenshot.invoke({})
        assert "not available" in result.lower() or "display" in result.lower()

    def test_screen_size_no_display(self):
        if _PYAUTOGUI_AVAILABLE:
            pytest.skip("PyAutoGUI is available – skipping headless-only test")
        result = get_screen_size.invoke({})
        assert "not available" in result.lower() or "display" in result.lower()
