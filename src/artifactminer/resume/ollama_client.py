from __future__ import annotations

import asyncio
from typing import Type, TypeVar

from ollama import chat, list as ollama_list, AsyncClient
from pydantic import BaseModel

DEFAULT_MODEL = "qwen3:1.7b"

T = TypeVar("T", bound=BaseModel)


def ensure_model_available(model: str = DEFAULT_MODEL) -> None:
    try:
        available = {m.model for m in ollama_list().models}
    except Exception as exc:  # pragma: no cover - depends on local Ollama
        raise RuntimeError(
            "Unable to connect to Ollama. Make sure the Ollama server is running."
        ) from exc

    if model not in available:
        raise RuntimeError(
            f"Ollama model '{model}' is not available. Run 'ollama pull {model}'."
        )


def query_ollama(
    prompt: str,
    schema: Type[T],
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.1,
) -> T:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat(
        model=model,
        messages=messages,
        format=schema.model_json_schema(),
        think=False,
        options={
            "temperature": temperature,
        },
    )

    content = response.message.content or ""
    if not content.strip():
        raise RuntimeError(
            f"Ollama returned empty response. This may indicate the model "
            f"'{model}' doesn't support structured JSON output, or the context "
            f"window was exceeded. Try a different model or reduce input size."
        )

    return schema.model_validate_json(content)


def query_ollama_text(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.3,
    num_ctx: int = 4096,
    num_predict: int = 2048,
) -> str:
    """Query Ollama for text output (no structured format)."""
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat(
        model=model,
        messages=messages,
        think=False,  # Disable thinking mode for faster responses
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    )

    return response.message.content or ""


def check_ollama_available() -> bool:
    """Check if Ollama server is running and accessible."""
    try:
        ollama_list()
        return True
    except Exception:
        return False


def get_available_models() -> list[str]:
    """Get list of models available in Ollama."""
    try:
        return [m.model for m in ollama_list().models]
    except Exception:
        return []


async def query_ollama_async(
    prompt: str,
    schema: Type[T],
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.1,
) -> T:
    """Async version of query_ollama for concurrent execution."""
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    client = AsyncClient()
    response = await client.chat(
        model=model,
        messages=messages,
        format=schema.model_json_schema(),
        think=False,
        options={
            "temperature": temperature,
        },
    )

    content = response.message.content or ""
    if not content.strip():
        raise RuntimeError(
            f"Ollama returned empty response. This may indicate the model "
            f"'{model}' doesn't support structured JSON output, or the context "
            f"window was exceeded. Try a different model or reduce input size."
        )

    return schema.model_validate_json(content)
