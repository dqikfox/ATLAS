"""Tests for atlas.models.factory."""

import pytest
from unittest.mock import MagicMock, patch

from atlas.config import AtlasConfig
from atlas.models.factory import get_llm


class TestGetLlm:
    def test_invalid_provider_raises(self):
        cfg = AtlasConfig(model_provider="unknown")
        with pytest.raises(ValueError, match="Unknown model provider"):
            get_llm(cfg)

    def test_openai_provider_creates_chat_openai(self):
        mock_llm = MagicMock()
        cfg = AtlasConfig(
            model_provider="openai",
            openai_api_key="test-key",
            openai_model="gpt-4o",
        )
        with patch("langchain_openai.ChatOpenAI", return_value=mock_llm) as mock_cls:
            result = get_llm(cfg)
        mock_cls.assert_called_once_with(
            model="gpt-4o",
            temperature=cfg.openai_temperature,
            api_key="test-key",
        )
        assert result is mock_llm

    def test_ollama_provider_creates_chat_ollama(self):
        mock_llm = MagicMock()
        cfg = AtlasConfig(
            model_provider="ollama",
            ollama_model="llama3.2",
            ollama_base_url="http://localhost:11434",
        )
        with patch("langchain_ollama.ChatOllama", return_value=mock_llm) as mock_cls:
            result = get_llm(cfg)
        mock_cls.assert_called_once_with(
            model="llama3.2",
            base_url="http://localhost:11434",
        )
        assert result is mock_llm

    def test_bad_provider_error_includes_provider_name(self):
        cfg_bad = AtlasConfig(model_provider="notreal")
        with pytest.raises(ValueError, match="notreal"):
            get_llm(cfg_bad)
