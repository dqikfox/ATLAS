"""Utilities for loading local AI models in offline mode."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from ultron.config import load_config

# Hold references to preloaded models
_preloaded_llm: Any = None
_preloaded_stt: Any = None
_preload_task: Optional[asyncio.Task] = None


def _load_llm(cfg: Dict[str, Any]) -> Any:
    """Load a quantized LLaMA/Mistral model using llama.cpp or transformers."""
    model_type = cfg.get("type", "llama_cpp")
    if model_type == "llama_cpp":
        from llama_cpp import Llama  # type: ignore
        return Llama(model_path=cfg["path"], n_ctx=cfg.get("n_ctx", 2048))
    else:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        model = AutoModelForCausalLM.from_pretrained(cfg["path"])
        tokenizer = AutoTokenizer.from_pretrained(cfg["path"])
        return {"model": model, "tokenizer": tokenizer}


def _load_stt(cfg: Dict[str, Any]) -> Any:
    """Load a local speech-to-text model using Whisper or Vosk."""
    stt_type = cfg.get("type", "whisper")
    if stt_type == "whisper":
        import whisper  # type: ignore
        return whisper.load_model(cfg.get("model", "base"))
    elif stt_type == "vosk":
        from vosk import Model  # type: ignore
        return Model(cfg["model_path"])
    else:
        raise ValueError(f"Unknown STT type: {stt_type}")


async def _preload(cfg: Dict[str, Any]) -> None:
    """Asynchronously load configured models."""
    global _preloaded_llm, _preloaded_stt
    loop = asyncio.get_running_loop()
    tasks = []
    llm_task_index = stt_task_index = None

    models_cfg = cfg.get("models", {})
    if "llm" in models_cfg:
        llm_task_index = len(tasks)
        tasks.append(loop.run_in_executor(None, _load_llm, models_cfg["llm"]))
    if "stt" in models_cfg:
        stt_task_index = len(tasks)
        tasks.append(loop.run_in_executor(None, _load_stt, models_cfg["stt"]))

    results = await asyncio.gather(*tasks)
    if llm_task_index is not None:
        _preloaded_llm = results[llm_task_index]
    if stt_task_index is not None:
        _preloaded_stt = results[stt_task_index]


def preload_async(cfg: Optional[Dict[str, Any]] = None) -> Optional[asyncio.Task]:
    """Start asynchronous preloading of models if offline mode is enabled."""
    global _preload_task
    cfg = cfg or load_config()
    if not cfg.get("offline_mode"):
        return None
    _preload_task = asyncio.create_task(_preload(cfg))
    return _preload_task


def get_llm() -> Any:
    """Return the preloaded language model, if available."""
    return _preloaded_llm


def get_stt_model() -> Any:
    """Return the preloaded speech-to-text model, if available."""
    return _preloaded_stt
