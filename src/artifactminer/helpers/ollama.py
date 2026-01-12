"""Utilities for interacting with a local Ollama LLM."""

from typing import Optional
import httpx

__all__ = ["get_ollama_response"]

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"  # or mistral, gemma, etc.


def get_ollama_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Call a local Ollama model and return plain text.

    Args:
        prompt: The string to send to the model.
        model: The Ollama model name to use.

    Returns:
        The model output as a plain string.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        return f"[Ollama error] {exc}"

    data = response.json()
    return data.get("response", "").strip()
