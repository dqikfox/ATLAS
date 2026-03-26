"""Tests for atlas.config."""

import os
import pytest

from atlas.config import AtlasConfig, load_config


class TestAtlasConfig:
    def test_defaults(self):
        cfg = AtlasConfig()
        assert cfg.model_provider == "openai"
        assert cfg.openai_model == "gpt-4o"
        assert cfg.ollama_model == "llama3.2"
        assert cfg.safe_mode is True
        assert cfg.pyautogui_pause == 0.5

    def test_provider_from_env(self, monkeypatch):
        monkeypatch.setenv("ATLAS_MODEL_PROVIDER", "ollama")
        cfg = AtlasConfig()
        assert cfg.model_provider == "ollama"

    def test_openai_model_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        cfg = AtlasConfig()
        assert cfg.openai_model == "gpt-4-turbo"

    def test_ollama_model_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "mistral")
        cfg = AtlasConfig()
        assert cfg.ollama_model == "mistral"

    def test_safe_mode_false(self, monkeypatch):
        monkeypatch.setenv("ATLAS_SAFE_MODE", "false")
        cfg = AtlasConfig()
        assert cfg.safe_mode is False

    def test_pyautogui_pause_from_env(self, monkeypatch):
        monkeypatch.setenv("PYAUTOGUI_PAUSE", "1.5")
        cfg = AtlasConfig()
        assert cfg.pyautogui_pause == 1.5

    def test_load_config_returns_atlas_config(self):
        cfg = load_config()
        assert isinstance(cfg, AtlasConfig)
