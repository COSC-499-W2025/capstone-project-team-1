"""Typed runtime exceptions for shared local LLM infrastructure."""

from __future__ import annotations

from pathlib import Path


class LocalLLMRuntimeError(RuntimeError):
    """Base class for shared local LLM runtime failures."""


class LlamaServerNotFoundError(LocalLLMRuntimeError):
    """Raised when the llama-server executable cannot be located."""

    def __init__(self, binary_name: str = "llama-server") -> None:
        self.binary_name = binary_name
        super().__init__(f"{binary_name} binary not found on PATH.")


class ModelNotFoundError(LocalLLMRuntimeError):
    """Raised when a requested model cannot be resolved locally."""

    def __init__(
        self,
        model: str,
        searched_path: Path | None = None,
        message: str | None = None,
    ) -> None:
        self.model = model
        self.searched_path = searched_path
        # Most callers can rely on the default message, but registry helpers can
        # pass a richer message while keeping the same typed exception.
        if message is None:
            if searched_path is None:
                message = f"Model '{model}' was not found."
            else:
                message = f"Model '{model}' was not found at {searched_path}."
        super().__init__(message)


class ModelStartupTimeoutError(LocalLLMRuntimeError):
    """Raised when llama-server does not become healthy in time."""

    def __init__(self, model: str, timeout_seconds: float) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Model '{model}' did not become ready within {timeout_seconds}s."
        )


class ModelServerCrashedError(LocalLLMRuntimeError):
    """Raised when llama-server exits unexpectedly."""

    def __init__(self, model: str | None = None, exit_code: int | None = None) -> None:
        self.model = model
        self.exit_code = exit_code

        # Build the message from optional details so callers can surface exactly
        # what was known at the time of the crash.
        details: list[str] = []
        if model is not None:
            details.append(f"model={model}")
        if exit_code is not None:
            details.append(f"exit_code={exit_code}")

        suffix = f" ({', '.join(details)})" if details else ""
        super().__init__(f"llama-server exited unexpectedly{suffix}.")


class InvalidLLMResponseError(LocalLLMRuntimeError):
    """Raised when the model response is empty or cannot be interpreted."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        self.raw_response = raw_response
        super().__init__(message)
