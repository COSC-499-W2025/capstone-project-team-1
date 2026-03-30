"""Stable public client surface for the shared local LLM runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from .models import ModelDescriptor, RuntimeStatus
from .runtime.config import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODELS_DIR,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
)
from .runtime.errors import ModelNotFoundError
from .runtime.inference import query_llm_json as _query_llm_json
from .runtime.inference import query_llm_text as _query_llm_text
from .runtime.process_manager import ensure_server as _ensure_server
from .runtime.process_manager import get_server_status as _get_server_status
from .runtime.process_manager import stop_server as _stop_server
from .runtime.registry import list_available_models as _list_available_models
from .runtime.registry import resolve_model_descriptor as _resolve_model_descriptor

T = TypeVar("T")

__all__ = [
    "check_model_available",
    "ensure_model_available",
    "list_available_models",
    "query_json",
    "query_text",
    "runtime_status",
    "unload_model",
]


def ensure_model_available(
    model: str = DEFAULT_MODEL_NAME,
    *,
    models_dir: Path = DEFAULT_MODELS_DIR,
    timeout: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> None:
    """Ensure the requested model is loaded and ready in the local runtime."""

    _ensure_server(model, models_dir=models_dir, timeout=timeout)


def check_model_available(
    model: str = DEFAULT_MODEL_NAME,
    *,
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> bool:
    """Return whether the requested approved model is installed locally."""

    try:
        _resolve_model_descriptor(model, models_dir=models_dir)
    except ModelNotFoundError:
        return False
    return True


def list_available_models(
    *,
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> list[ModelDescriptor]:
    """Return the approved models that are currently installed locally."""

    return _list_available_models(models_dir=models_dir)


async def query_text(
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
    """Generate plain text through the shared local runtime."""

    return await _query_llm_text(
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        grammar=grammar,
    )


async def query_json(
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
    """Generate structured JSON through the shared local runtime."""

    return await _query_llm_json(
        prompt,
        schema,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
    )


def unload_model() -> None:
    """Stop the managed local runtime process, if one is active."""

    _stop_server()


def runtime_status() -> RuntimeStatus:
    """Return the current local runtime status snapshot."""

    return _get_server_status()
