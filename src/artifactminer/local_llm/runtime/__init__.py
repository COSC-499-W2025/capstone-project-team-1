"""Runtime configuration and error primitives for local LLM support."""

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
    "resolve_context_window",
]
