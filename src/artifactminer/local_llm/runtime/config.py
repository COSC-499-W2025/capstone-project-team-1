"""Runtime defaults and lightweight helpers for local LLM execution."""

from __future__ import annotations

import platform
from pathlib import Path

from ..models import InferenceOptions

DEFAULT_MODEL_NAME = "qwen2.5-coder-3b-q4"
DEFAULT_MODELS_DIR = Path.home() / ".artifactminer" / "models"
DEFAULT_STARTUP_TIMEOUT_SECONDS = 60.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 60.0
DEFAULT_CONTEXT_WINDOW = 4096
DEFAULT_MAX_TOKENS = 12288

MODEL_FAMILY_SAMPLING_DEFAULTS: dict[str, InferenceOptions] = {
    "lfm2.5": InferenceOptions(
        temperature=0.1,
        top_p=0.1,
        repetition_penalty=1.05,
        max_tokens=DEFAULT_MAX_TOKENS,
    ),
    "qwen2.5-coder": InferenceOptions(
        temperature=0.15,
        top_p=0.9,
        max_tokens=DEFAULT_MAX_TOKENS,
    ),
    "qwen3": InferenceOptions(
        temperature=0.2,
        top_p=0.9,
        max_tokens=DEFAULT_MAX_TOKENS,
    ),
    "fallback": InferenceOptions(
        temperature=0.2,
        top_p=0.9,
        max_tokens=DEFAULT_MAX_TOKENS,
    ),
}

__all__ = [
    "DEFAULT_CONTEXT_WINDOW",
    "DEFAULT_HEALTH_TIMEOUT_SECONDS",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL_NAME",
    "DEFAULT_MODELS_DIR",
    "DEFAULT_STARTUP_TIMEOUT_SECONDS",
    "default_gpu_layers",
    "get_sampling_defaults",
    "resolve_context_window",
]


def default_gpu_layers(
    system_name: str | None = None, machine: str | None = None
) -> int:
    """Return the default GPU offload policy for the current platform."""

    resolved_system = system_name or platform.system()
    resolved_machine = machine or platform.machine()
    if resolved_system == "Darwin" and resolved_machine == "arm64":
        return -1
    return 0


def resolve_context_window(model_context: int | None = None) -> int:
    """Return a usable context window, falling back to the runtime default."""

    if model_context is None:
        return DEFAULT_CONTEXT_WINDOW
    if model_context <= 0:
        raise ValueError("Context window must be a positive integer.")
    return model_context


def get_sampling_defaults(model: str) -> InferenceOptions:
    """Return sampling defaults for a known model family via prefix matching."""

    for prefix, options in MODEL_FAMILY_SAMPLING_DEFAULTS.items():
        if prefix != "fallback" and model.startswith(prefix):
            return options.model_copy(deep=True)
    return MODEL_FAMILY_SAMPLING_DEFAULTS["fallback"].model_copy(deep=True)
