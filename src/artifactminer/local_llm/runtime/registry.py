"""Curated model registry for the local-only LLM runtime."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from ..models import ModelDescriptor
from .config import DEFAULT_MODELS_DIR
from .errors import ModelNotFoundError


# This is the single source of truth for the team-approved local models.
# The runtime only supports the model names defined here, and each one resolves
# to a single expected GGUF file in ~/.artifactminer/models.
_SUPPORTED_MODELS = MappingProxyType(
    {
        "qwen3.5-4b-q4": ModelDescriptor(
            name="qwen3.5-4b-q4",
            filename="Qwen 3.5 4B Q4 K_M.gguf",
            repo_url="https://huggingface.co/unsloth/Qwen3.5-4B-GGUF?show_file_info=Qwen3.5-4B-Q4_K_M.gguf",
            context_window=20480,
        ),
        "qwen2.5-coder-3b-q4": ModelDescriptor(
            name="qwen2.5-coder-3b-q4",
            filename="qwen2.5-coder-3b-instruct-q4_k_m.gguf",
            repo_url="https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF?show_file_info=qwen2.5-coder-3b-instruct-q4_k_m.gguf",
            context_window=16384,
        ),
        "lfm2.5-1.2b-q4": ModelDescriptor(
            name="lfm2.5-1.2b-q4",
            filename="LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
            repo_url="https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF?show_file_info=LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
            context_window=32768,
        ),
    }
)

__all__ = [
    "list_available_models",
    "list_supported_models",
    "resolve_model_descriptor",
    "resolve_model_path",
]


def list_supported_models() -> list[ModelDescriptor]:
    """Return registry-backed model metadata."""

    # Sorting keeps the output stable for tests, UIs, and future callers.
    return [
        _SUPPORTED_MODELS[name].model_copy(deep=True)
        for name in sorted(_SUPPORTED_MODELS)
    ]


def list_available_models(
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> list[ModelDescriptor]:
    """Return the supported models that are currently installed locally."""

    if not models_dir.exists():
        return []

    available: list[ModelDescriptor] = []
    for model_name in sorted(_SUPPORTED_MODELS):
        descriptor = _SUPPORTED_MODELS[model_name]
        resolved_path = models_dir / _require_filename(model_name, descriptor)
        if resolved_path.exists():
            available.append(descriptor.model_copy(update={"path": resolved_path}))
    return available


def resolve_model_descriptor(
    model: str, models_dir: Path = DEFAULT_MODELS_DIR
) -> ModelDescriptor:
    """Resolve a supported model name into its concrete local descriptor."""

    if model not in _SUPPORTED_MODELS:
        raise _build_unsupported_model_error(model, models_dir)

    descriptor = _SUPPORTED_MODELS[model]
    resolved_path = models_dir / _require_filename(model, descriptor)
    if not resolved_path.exists():
        raise _build_missing_model_error(model, resolved_path, models_dir)
    return descriptor.model_copy(update={"path": resolved_path})


def resolve_model_path(model: str, models_dir: Path = DEFAULT_MODELS_DIR) -> Path:
    """Resolve a model selector into a concrete GGUF path."""

    descriptor = resolve_model_descriptor(model, models_dir=models_dir)
    if descriptor.path is None:
        raise RuntimeError(f"Resolved model '{model}' did not include a path.")
    return descriptor.path


def _require_filename(model_name: str, descriptor: ModelDescriptor) -> str:
    if descriptor.filename is None:
        raise ValueError(
            f"Registry descriptor for '{model_name}' is missing a filename."
        )
    return descriptor.filename


def _build_unsupported_model_error(
    model: str, models_dir: Path
) -> ModelNotFoundError:
    supported_models = ", ".join(sorted(_SUPPORTED_MODELS))
    message = (
        f"Model '{model}' is not a supported local model. "
        f"Supported model names: {supported_models}. "
        f"Approved models must be installed under {models_dir}."
    )
    return ModelNotFoundError(model, message=message)


def _build_missing_model_error(
    model: str, searched_path: Path, models_dir: Path
) -> ModelNotFoundError:
    # The registry raises one typed error with enough context for callers or UIs
    # to explain what was checked and how the user can recover.
    supported_models = ", ".join(sorted(_SUPPORTED_MODELS))
    message = (
        f"Model '{model}' was not found at {searched_path}. "
        f"Checked local models in {models_dir}. "
        f"Supported model names: {supported_models}. "
        "Install the expected GGUF file into that directory."
    )
    return ModelNotFoundError(model, searched_path, message=message)
