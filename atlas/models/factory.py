"""Model factory – returns the correct LangChain chat model based on config."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from atlas.config import AtlasConfig


def get_llm(cfg: AtlasConfig) -> BaseChatModel:
    """Return a LangChain chat model for the provider specified in *cfg*.

    Supported providers
    -------------------
    ``openai``
        Uses :class:`langchain_openai.ChatOpenAI`.  Requires the
        ``OPENAI_API_KEY`` environment variable.
    ``ollama``
        Uses :class:`langchain_ollama.ChatOllama`.  Requires a running
        Ollama server (default ``http://localhost:11434``).
    """
    provider = cfg.model_provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.openai_model,
            temperature=cfg.openai_temperature,
            api_key=cfg.openai_api_key,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=cfg.ollama_model,
            base_url=cfg.ollama_base_url,
        )

    raise ValueError(
        f"Unknown model provider '{provider}'. "
        "Set ATLAS_MODEL_PROVIDER to 'openai' or 'ollama'."
    )
