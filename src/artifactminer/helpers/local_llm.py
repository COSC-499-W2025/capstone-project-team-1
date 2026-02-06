"""Local LLM helper — thin wrapper around the resume module's llm_client."""

from __future__ import annotations

from artifactminer.resume.llm_client import query_llm_text

DEFAULT_MODEL = "qwen3-1.7b"


def get_local_llm_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Query the local LLM for a text response."""
    return query_llm_text(prompt, model=model, temperature=0.3)
