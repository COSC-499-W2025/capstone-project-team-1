"""Async text inference helpers for the shared local LLM runtime."""

from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI

from .config import DEFAULT_MODEL_NAME, get_sampling_defaults
from .errors import InferenceRequestError, InvalidLLMResponseError
from .process_manager import ensure_server, get_server_status

_LOCAL_MODEL_ID = "local"


def _build_client(port: int) -> AsyncOpenAI:
    """Return an OpenAI-compatible client pointed at the local llama-server."""

    return AsyncOpenAI(
        base_url=f"http://127.0.0.1:{port}/v1",
        api_key="not-needed",
    )


def _extract_text_content(response: Any) -> str:
    """Validate and extract plain text from a chat completion response."""

    choices = getattr(response, "choices", None)
    if not choices:
        raise InvalidLLMResponseError(
            "Local LLM response did not include any choices.",
            raw_response=repr(response),
        )

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None:
        raise InvalidLLMResponseError(
            "Local LLM response was missing a message payload.",
            raw_response=repr(first_choice),
        )

    content = getattr(message, "content", None)
    if not isinstance(content, str):
        raise InvalidLLMResponseError(
            "Local LLM response content was not plain text.",
            raw_response=repr(content),
        )

    if not content.strip():
        raise InvalidLLMResponseError(
            "Local LLM returned an empty text response.",
            raw_response=content,
        )

    return content


async def query_llm_text(prompt: str, model: str = DEFAULT_MODEL_NAME) -> str:
    """Generate plain text from the active local llama-server runtime."""

    await asyncio.to_thread(ensure_server, model)
    status = get_server_status()
    if not status.is_running or not status.is_healthy or status.server_port is None:
        raise InferenceRequestError(
            f"Local LLM runtime is not ready for model '{model}'.",
            model=model,
        )

    defaults = get_sampling_defaults(model)
    client = _build_client(status.server_port)

    request_kwargs: dict[str, Any] = {
        "model": _LOCAL_MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
    }
    if defaults.temperature is not None:
        request_kwargs["temperature"] = defaults.temperature
    if defaults.max_tokens is not None:
        request_kwargs["max_tokens"] = defaults.max_tokens

    extra_body: dict[str, Any] = {}
    if defaults.top_p is not None:
        extra_body["top_p"] = defaults.top_p
    if defaults.repetition_penalty is not None:
        extra_body["repetition_penalty"] = defaults.repetition_penalty
    if extra_body:
        request_kwargs["extra_body"] = extra_body

    try:
        response = await client.chat.completions.create(**request_kwargs)
    except Exception as exc:  # pragma: no cover - concrete exceptions are SDK-dependent
        raise InferenceRequestError(
            f"Local LLM inference request failed for model '{model}': "
            f"{type(exc).__name__}: {exc}",
            model=model,
        ) from exc

    return _extract_text_content(response)
