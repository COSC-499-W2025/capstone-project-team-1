from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import artifactminer.local_llm as local_llm
import artifactminer.local_llm.runtime as runtime
from artifactminer.local_llm import InferenceOptions, ModelDescriptor, RuntimeStatus
from artifactminer.local_llm.runtime.config import (
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODELS_DIR,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    MODEL_FAMILY_SAMPLING_DEFAULTS,
    default_gpu_layers,
    get_sampling_defaults,
    resolve_context_window,
)
from artifactminer.local_llm.runtime.errors import (
    InvalidLLMResponseError,
    LlamaServerNotFoundError,
    LocalLLMRuntimeError,
    ModelNotFoundError,
    ModelServerCrashedError,
    ModelStartupTimeoutError,
)
from artifactminer.local_llm.runtime.registry import (
    list_available_models,
    list_supported_models,
    resolve_model_descriptor,
    resolve_model_path,
)


def test_exports_are_stable() -> None:
    assert local_llm.__all__ == ["InferenceOptions", "ModelDescriptor", "RuntimeStatus"]
    assert local_llm.InferenceOptions is InferenceOptions
    expected_runtime = {
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
        "resolve_context_window",
        "resolve_model_descriptor",
        "resolve_model_path",
    }
    assert set(runtime.__all__) == expected_runtime
    assert runtime.list_supported_models is list_supported_models
    assert runtime.list_available_models is list_available_models
    assert runtime.resolve_model_descriptor is resolve_model_descriptor
    assert runtime.resolve_model_path is resolve_model_path


def test_inference_options_valid_and_frozen() -> None:
    options = InferenceOptions(
        temperature=0.0, top_p=1.0, max_tokens=256, repetition_penalty=1.1
    )
    assert options.temperature == 0.0
    assert options.top_p == 1.0
    with pytest.raises((ValidationError, TypeError)):
        options.temperature = 0.5  # type: ignore[misc]


@pytest.mark.parametrize(
    ("payload", "field_name"),
    [
        ({"temperature": -0.1}, "temperature"),
        ({"unknown": "value"}, "unknown"),
    ],
)
def test_inference_options_rejects_invalid(
    payload: dict[str, object], field_name: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        InferenceOptions(**payload)
    assert field_name in str(exc_info.value)


def test_model_descriptor_valid_and_frozen() -> None:
    # Use a real supported alias so these shared-model fixtures stay aligned with the local-only registry tests elsewhere in the suite.
    descriptor = ModelDescriptor(
        name="qwen3.5-4b-q4",
        filename="Qwen 3.5 4B Q4 K_M.gguf",
        repo_url="https://huggingface.co/example/model",
        context_window=20480,
        path="/tmp/model.gguf",
    )
    assert descriptor.name == "qwen3.5-4b-q4"
    assert descriptor.repo_url == "https://huggingface.co/example/model"
    assert descriptor.path == Path("/tmp/model.gguf")
    with pytest.raises((ValidationError, TypeError)):
        descriptor.name = "other"  # type: ignore[misc]


def test_model_descriptor_rejects_invalid() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModelDescriptor(name="", context_window=4096)
    assert "name" in str(exc_info.value)


def test_runtime_status_defaults_and_frozen() -> None:
    status = RuntimeStatus(models_dir=DEFAULT_MODELS_DIR)
    assert status.loaded_model is None
    assert status.server_pid is None
    assert status.is_running is False
    assert status.models_dir == DEFAULT_MODELS_DIR
    with pytest.raises((ValidationError, TypeError)):
        status.is_running = True  # type: ignore[misc]


def test_runtime_status_rejects_invalid() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RuntimeStatus(models_dir=DEFAULT_MODELS_DIR, server_port=70000)
    assert "server_port" in str(exc_info.value)


def test_config_constants() -> None:
    assert DEFAULT_MODEL_NAME == "qwen2.5-coder-3b-q4"
    assert DEFAULT_MODELS_DIR == Path.home() / ".artifactminer" / "models"
    assert DEFAULT_STARTUP_TIMEOUT_SECONDS == 60.0
    assert DEFAULT_HEALTH_TIMEOUT_SECONDS == 60.0
    assert DEFAULT_CONTEXT_WINDOW == 4096
    assert DEFAULT_MAX_TOKENS == 12288
    assert "fallback" in MODEL_FAMILY_SAMPLING_DEFAULTS


@pytest.mark.parametrize(
    ("system_name", "machine", "expected"),
    [
        ("Darwin", "arm64", -1),
        ("Linux", "x86_64", 0),
    ],
)
def test_default_gpu_layers(system_name: str, machine: str, expected: int) -> None:
    assert default_gpu_layers(system_name, machine) == expected


def test_resolve_context_window() -> None:
    assert resolve_context_window() == DEFAULT_CONTEXT_WINDOW
    assert resolve_context_window(4096) == 4096
    with pytest.raises(ValueError, match="positive integer"):
        resolve_context_window(0)


def test_get_sampling_defaults() -> None:

    qwen3_5 = get_sampling_defaults("qwen3.5-4b-q4")
    qwen_coder = get_sampling_defaults("qwen2.5-coder-3b-q4")
    lfm = get_sampling_defaults("lfm2.5-1.2b-q4")
    fallback = get_sampling_defaults("unknown-model-family")

    assert qwen3_5.temperature == 0.2
    assert qwen_coder.temperature == 0.15
    assert lfm.temperature == 0.1
    assert lfm.repetition_penalty == 1.05
    assert fallback == MODEL_FAMILY_SAMPLING_DEFAULTS["fallback"]
    assert fallback is not MODEL_FAMILY_SAMPLING_DEFAULTS["fallback"]


def test_error_classes() -> None:
    search_path = Path("/tmp/model.gguf")

    not_found = ModelNotFoundError("missing-model", search_path)
    timeout = ModelStartupTimeoutError("qwen3.5-4b-q4", 60.0)
    crashed = ModelServerCrashedError("qwen3.5-4b-q4", 137)
    invalid = InvalidLLMResponseError("bad json", '{"oops":true}')
    missing_binary = LlamaServerNotFoundError()

    for err in (not_found, timeout, crashed, invalid, missing_binary):
        assert isinstance(err, LocalLLMRuntimeError)

    assert str(not_found) == f"Model 'missing-model' was not found at {search_path}."
    assert "60.0s" in str(timeout)
    assert "exit_code=137" in str(crashed)
    assert invalid.raw_response == '{"oops":true}'
    assert str(missing_binary) == "llama-server binary not found on PATH."

    assert str(ModelNotFoundError("x")) == "Model 'x' was not found."
    assert str(ModelNotFoundError("x", search_path, message="custom")) == "custom"
    assert str(ModelServerCrashedError()) == "llama-server exited unexpectedly."
    assert (
        str(ModelServerCrashedError(model="x"))
        == "llama-server exited unexpectedly (model=x)."
    )
    assert InvalidLLMResponseError("empty").raw_response is None
    assert LlamaServerNotFoundError("custom").binary_name == "custom"
