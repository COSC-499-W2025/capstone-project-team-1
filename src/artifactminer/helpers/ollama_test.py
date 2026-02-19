"""Deprecated — use local_llm.py instead."""

from __future__ import annotations

from artifactminer.helpers.local_llm import get_local_llm_response

DEFAULT_MODEL = "qwen3-1.7b"


def get_ollama_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Deprecated: use get_local_llm_response from helpers.local_llm instead."""
    return get_local_llm_response(prompt, model=model)
