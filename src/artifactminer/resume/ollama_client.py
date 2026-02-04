from __future__ import annotations

from typing import Type, TypeVar

from ollama import chat, list as ollama_list
from pydantic import BaseModel

DEFAULT_MODEL = "qwen3:4b"

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
    num_ctx: int = 4096,
    num_predict: int = 1024,
) -> T:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat(
        model=model,
        messages=messages,
        format=schema.model_json_schema(),
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    )

    return schema.model_validate_json(response.message.content)


def query_ollama_text(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.3,
    num_ctx: int = 4096,
    num_predict: int = 2048,
) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = chat(
        model=model,
        messages=messages,
        options={
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    )

    return response.message.content
