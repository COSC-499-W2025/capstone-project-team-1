"""Runtime configuration and error primitives for local LLM support."""

# This package-level module is the stable import surface for lightweight runtime
# helpers. Higher layers should import from here instead of reaching into deeper
# modules unless they need implementation-specific behavior.
from .config import (
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODELS_DIR,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    default_gpu_layers,
    get_sampling_defaults,
    resolve_context_window,
)
from .errors import (
    InvalidLLMResponseError,
    LlamaServerNotFoundError,
    LocalLLMRuntimeError,
    ModelNotFoundError,
    ModelServerCrashedError,
    ModelStartupTimeoutError,
)
from .health import poll_until_healthy
from .registry import (
    list_available_models,
    list_supported_models,
    resolve_model_descriptor,
    resolve_model_path,
)

__all__ = [
    "DEFAULT_CONTEXT_WINDOW",
    "DEFAULT_HEALTH_TIMEOUT_SECONDS",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL_NAME",
    "DEFAULT_MODELS_DIR",
    "DEFAULT_STARTUP_TIMEOUT_SECONDS",
    "InvalidLLMResponseError",
    "LlamaServerNotFoundError",
    "LocalLLMRuntimeError",
    "ModelNotFoundError",
    "ModelServerCrashedError",
    "ModelStartupTimeoutError",
    "default_gpu_layers",
    "get_sampling_defaults",
    "list_available_models",
    "list_supported_models",
    "poll_until_healthy",
    "resolve_model_descriptor",
    "resolve_model_path",
    "resolve_context_window",
]
