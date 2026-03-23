"""Async text inference helpers for the shared local LLM runtime."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import TypeAdapter, ValidationError

from .config import DEFAULT_MODEL_NAME, get_sampling_defaults
from .errors import (
    EmptyLLMResponseError,
    InferenceRequestError,
    InvalidLLMResponseError,
    MalformedJSONResponseError,
    SchemaValidationResponseError,
)
from .process_manager import ensure_server, get_server_status

T = TypeVar("T")
_LOCAL_MODEL_ID = "local"
_SERVER_READY_LOCK = asyncio.Lock()


def _build_client(port: int) -> AsyncOpenAI:
    """Return an OpenAI-compatible client pointed at the local llama-server."""

    return AsyncOpenAI(
        base_url=f"http://127.0.0.1:{port}/v1",
        api_key="not-needed",
    )


def _build_messages(prompt: str, *, system: str | None = None) -> list[dict[str, str]]:
    """Build chat messages with an optional system prompt."""

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _resolve_sampling(
    *,
    model: str,
    temperature: float | None,
    max_tokens: int | None,
    top_p: float | None,
    repetition_penalty: float | None,
) -> dict[str, float | int | None]:
    """Merge model defaults with explicit caller overrides."""

    defaults = get_sampling_defaults(model)
    return {
        "temperature": (
            temperature if temperature is not None else defaults.temperature
        ),
        "max_tokens": max_tokens if max_tokens is not None else defaults.max_tokens,
        "top_p": top_p if top_p is not None else defaults.top_p,
        "repetition_penalty": (
            repetition_penalty
            if repetition_penalty is not None
            else defaults.repetition_penalty
        ),
    }


async def _ensure_runtime_ready(model: str) -> AsyncOpenAI:
    """Ensure the server is running and return a connected inference client."""

    async with _SERVER_READY_LOCK:
        await asyncio.to_thread(ensure_server, model)
        status = get_server_status()
    if not status.is_running or not status.is_healthy or status.server_port is None:
        raise InferenceRequestError(
            f"Local LLM runtime is not ready for model '{model}'.",
            model=model,
        )
    return _build_client(status.server_port)


def _extract_text_content(response: Any) -> str:
    """Validate and extract text content from a chat completion response."""

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
        raise EmptyLLMResponseError(
            "Local LLM returned an empty text response.",
            raw_response=content,
        )

    return content


def _schema_name(schema: Any) -> str:
    """Derive a stable schema name for llama-server response_format metadata."""

    name = getattr(schema, "__name__", None)
    if isinstance(name, str) and name:
        return name
    return "ResponseSchema"


async def query_llm_text(
    prompt: str,
    model: str = DEFAULT_MODEL_NAME,
    *,
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    grammar: str | None = None,
) -> str:
    """Generate plain text from the active local llama-server runtime."""

    client = await _ensure_runtime_ready(model)
    sampling = _resolve_sampling(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
    )

    request_kwargs: dict[str, Any] = {
        "model": _LOCAL_MODEL_ID,
        "messages": _build_messages(prompt, system=system),
    }
    if sampling["temperature"] is not None:
        request_kwargs["temperature"] = sampling["temperature"]
    if sampling["max_tokens"] is not None:
        request_kwargs["max_tokens"] = sampling["max_tokens"]

    extra_body: dict[str, Any] = {}
    if sampling["top_p"] is not None:
        extra_body["top_p"] = sampling["top_p"]
    if sampling["repetition_penalty"] is not None:
        extra_body["repetition_penalty"] = sampling["repetition_penalty"]
    if grammar is not None:
        extra_body["grammar"] = grammar
    if extra_body:
        request_kwargs["extra_body"] = extra_body

    try:
        try:
            response = await client.chat.completions.create(**request_kwargs)
        except Exception as exc:  # pragma: no cover - concrete exceptions are SDK-dependent
            raise InferenceRequestError(
                f"Local LLM inference request failed for model '{model}': "
                f"{type(exc).__name__}: {exc}",
                model=model,
            ) from exc
    finally:
        await client.close()

    return _extract_text_content(response)


async def query_llm_json(
    prompt: str,
    schema: type[T] | Any,
    *,
    model: str = DEFAULT_MODEL_NAME,
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
) -> T:
    """Generate schema-constrained JSON and validate it against a schema/type."""

    client = await _ensure_runtime_ready(model)
    sampling = _resolve_sampling(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
    )
    adapter: TypeAdapter[T] = TypeAdapter(schema)

    request_kwargs: dict[str, Any] = {
        "model": _LOCAL_MODEL_ID,
        "messages": _build_messages(prompt, system=system),
    }
    if sampling["temperature"] is not None:
        request_kwargs["temperature"] = sampling["temperature"]
    if sampling["max_tokens"] is not None:
        request_kwargs["max_tokens"] = sampling["max_tokens"]

    extra_body: dict[str, Any] = {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": _schema_name(schema),
                "schema": adapter.json_schema(),
            },
        }
    }
    if sampling["top_p"] is not None:
        extra_body["top_p"] = sampling["top_p"]
    if sampling["repetition_penalty"] is not None:
        extra_body["repetition_penalty"] = sampling["repetition_penalty"]
    request_kwargs["extra_body"] = extra_body

    try:
        response = await client.chat.completions.create(**request_kwargs)
    except Exception as exc:  # pragma: no cover - concrete exceptions are SDK-dependent
        raise InferenceRequestError(
            f"Local LLM inference request failed for model '{model}': "
            f"{type(exc).__name__}: {exc}",
            model=model,
        ) from exc

    raw_content = _extract_text_content(response)
    try:
        parsed_json = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise MalformedJSONResponseError(
            "Local LLM returned malformed JSON.",
            raw_response=raw_content,
        ) from exc

    try:
        return adapter.validate_python(parsed_json)
    except ValidationError as exc:
        raise SchemaValidationResponseError(
            f"Local LLM JSON response did not match the requested schema: {exc}",
            raw_response=raw_content,
            validation_error=exc,
        ) from exc
