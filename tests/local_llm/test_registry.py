from __future__ import annotations

from pathlib import Path

import pytest

from artifactminer.local_llm.runtime.errors import ModelNotFoundError
from artifactminer.local_llm.runtime.registry import (
    list_available_models,
    list_supported_models,
    resolve_model_descriptor,
    resolve_model_path,
)


def test_list_supported_models_returns_exact_approved_models() -> None:
    supported = list_supported_models()

    assert [descriptor.name for descriptor in supported] == [
        "lfm2.5-1.2b-q4",
        "qwen2.5-coder-3b-q4",
        "qwen3.5-4b-q4",
    ]

    by_name = {descriptor.name: descriptor for descriptor in supported}
    assert by_name["lfm2.5-1.2b-q4"].filename == "LFM2.5-1.2B-Instruct-Q4_K_M.gguf"
    assert by_name["qwen2.5-coder-3b-q4"].filename == (
        "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
    )
    assert by_name["qwen3.5-4b-q4"].filename == "Qwen 3.5 4B Q4 K_M.gguf"


def test_resolve_model_descriptor_returns_installed_supported_model(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
    model_path.write_text("stub")

    descriptor = resolve_model_descriptor("qwen2.5-coder-3b-q4", models_dir=tmp_path)

    assert descriptor.name == "qwen2.5-coder-3b-q4"
    assert descriptor.filename == model_path.name
    assert descriptor.path == model_path
    assert descriptor.context_window == 16384


def test_resolve_model_path_returns_expected_file_for_supported_model(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "LFM2.5-1.2B-Instruct-Q4_K_M.gguf"
    model_path.write_text("stub")

    assert resolve_model_path("lfm2.5-1.2b-q4", models_dir=tmp_path) == model_path


@pytest.mark.parametrize(
    "model_name",
    [
        "unknown-model",
        "custom-model.gguf",
        "/tmp/some-model.gguf",
    ],
)
def test_resolve_model_descriptor_rejects_unsupported_model_names(
    model_name: str, tmp_path: Path
) -> None:
    with pytest.raises(ModelNotFoundError) as exc_info:
        resolve_model_descriptor(model_name, models_dir=tmp_path)

    assert exc_info.value.searched_path is None
    assert "not a supported local model" in str(exc_info.value)
    assert "Supported model names" in str(exc_info.value)


def test_missing_supported_model_raises_actionable_error(tmp_path: Path) -> None:
    with pytest.raises(ModelNotFoundError) as exc_info:
        resolve_model_descriptor("qwen3.5-4b-q4", models_dir=tmp_path)

    assert exc_info.value.searched_path == (tmp_path / "Qwen 3.5 4B Q4 K_M.gguf")
    assert "Install the expected GGUF file into that directory." in str(exc_info.value)


def test_list_available_models_returns_only_installed_supported_models(
    tmp_path: Path,
) -> None:
    qwen = tmp_path / "qwen2.5-coder-3b-instruct-q4_k_m.gguf"
    qwen35 = tmp_path / "Qwen 3.5 4B Q4 K_M.gguf"
    custom = tmp_path / "custom-model.gguf"
    qwen.write_text("stub")
    qwen35.write_text("stub")
    custom.write_text("stub")

    available = list_available_models(models_dir=tmp_path)

    assert [descriptor.name for descriptor in available] == [
        "qwen2.5-coder-3b-q4",
        "qwen3.5-4b-q4",
    ]
    assert [descriptor.path for descriptor in available] == [qwen, qwen35]


def test_list_available_models_returns_empty_for_missing_directory(
    tmp_path: Path,
) -> None:
    assert list_available_models(models_dir=tmp_path / "missing") == []
