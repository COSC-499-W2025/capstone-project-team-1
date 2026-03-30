from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from artifactminer.local_llm.client import (
    check_model_available,
    ensure_model_available,
    list_available_models,
    query_json,
    query_text,
    runtime_status,
    unload_model,
)
from artifactminer.local_llm.models import ModelDescriptor, RuntimeStatus
from artifactminer.local_llm.runtime.errors import ModelNotFoundError


def test_client_exports_are_stable() -> None:
    import artifactminer.local_llm.client as client

    assert client.__all__ == [
        "check_model_available",
        "ensure_model_available",
        "list_available_models",
        "query_json",
        "query_text",
        "runtime_status",
        "unload_model",
    ]


def test_ensure_model_available_delegates_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    def fake_ensure_server(model: str, *, models_dir: Path, timeout: float) -> None:
        recorded["model"] = model
        recorded["models_dir"] = models_dir
        recorded["timeout"] = timeout

    monkeypatch.setattr(
        "artifactminer.local_llm.client._ensure_server",
        fake_ensure_server,
    )

    ensure_model_available(
        "qwen3.5-4b-q4",
        models_dir=Path("/tmp/models"),
        timeout=12.5,
    )

    assert recorded == {
        "model": "qwen3.5-4b-q4",
        "models_dir": Path("/tmp/models"),
        "timeout": 12.5,
    }


def test_check_model_available_returns_true_when_model_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_resolve_model_descriptor(model: str, *, models_dir: Path) -> ModelDescriptor:
        return ModelDescriptor(
            name=model,
            filename="model.gguf",
            context_window=4096,
            path=models_dir / "model.gguf",
        )

    monkeypatch.setattr(
        "artifactminer.local_llm.client._resolve_model_descriptor",
        fake_resolve_model_descriptor,
    )

    assert (
        check_model_available(
            "qwen2.5-coder-3b-q4",
            models_dir=Path("/tmp/models"),
        )
        is True
    )


def test_check_model_available_returns_false_for_missing_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_resolve_model_descriptor(model: str, *, models_dir: Path) -> ModelDescriptor:
        raise ModelNotFoundError(model, models_dir / "missing.gguf")

    monkeypatch.setattr(
        "artifactminer.local_llm.client._resolve_model_descriptor",
        fake_resolve_model_descriptor,
    )

    assert (
        check_model_available(
            "qwen2.5-coder-3b-q4",
            models_dir=Path("/tmp/models"),
        )
        is False
    )


def test_list_available_models_delegates_to_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = [
        ModelDescriptor(
            name="lfm2.5-1.2b-q4",
            filename="LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
            context_window=32768,
            path=Path("/tmp/models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf"),
        )
    ]

    def fake_list_available_models(*, models_dir: Path) -> list[ModelDescriptor]:
        assert models_dir == Path("/tmp/models")
        return expected

    monkeypatch.setattr(
        "artifactminer.local_llm.client._list_available_models",
        fake_list_available_models,
    )

    assert list_available_models(models_dir=Path("/tmp/models")) == expected


@pytest.mark.asyncio
async def test_query_text_delegates_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    async def fake_query_llm_text(
        prompt: str,
        *,
        model: str,
        system: str | None,
        temperature: float | None,
        max_tokens: int | None,
        top_p: float | None,
        repetition_penalty: float | None,
        grammar: str | None,
    ) -> str:
        recorded.update(
            {
                "prompt": prompt,
                "model": model,
                "system": system,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "grammar": grammar,
            }
        )
        return "generated text"

    monkeypatch.setattr(
        "artifactminer.local_llm.client._query_llm_text",
        fake_query_llm_text,
    )

    result = await query_text(
        "hello",
        model="qwen3.5-4b-q4",
        system="be concise",
        temperature=0.4,
        max_tokens=123,
        top_p=0.8,
        repetition_penalty=1.1,
        grammar='root ::= "ok"',
    )

    assert result == "generated text"
    assert recorded == {
        "prompt": "hello",
        "model": "qwen3.5-4b-q4",
        "system": "be concise",
        "temperature": 0.4,
        "max_tokens": 123,
        "top_p": 0.8,
        "repetition_penalty": 1.1,
        "grammar": 'root ::= "ok"',
    }


class DemoPayload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_query_json_delegates_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    async def fake_query_llm_json(
        prompt: str,
        schema: type[DemoPayload],
        *,
        model: str,
        system: str | None,
        temperature: float | None,
        max_tokens: int | None,
        top_p: float | None,
        repetition_penalty: float | None,
    ) -> DemoPayload:
        recorded.update(
            {
                "prompt": prompt,
                "schema": schema,
                "model": model,
                "system": system,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
            }
        )
        return DemoPayload(name="Ada")

    monkeypatch.setattr(
        "artifactminer.local_llm.client._query_llm_json",
        fake_query_llm_json,
    )

    result = await query_json(
        "return json",
        DemoPayload,
        model="qwen2.5-coder-3b-q4",
        system="json only",
        temperature=0.2,
        max_tokens=55,
        top_p=0.9,
        repetition_penalty=1.02,
    )

    assert result == DemoPayload(name="Ada")
    assert recorded == {
        "prompt": "return json",
        "schema": DemoPayload,
        "model": "qwen2.5-coder-3b-q4",
        "system": "json only",
        "temperature": 0.2,
        "max_tokens": 55,
        "top_p": 0.9,
        "repetition_penalty": 1.02,
    }


def test_unload_model_delegates_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop_state = {"called": False}

    def fake_stop_server() -> None:
        stop_state["called"] = True

    monkeypatch.setattr(
        "artifactminer.local_llm.client._stop_server",
        fake_stop_server,
    )

    unload_model()

    assert stop_state["called"] is True


def test_runtime_status_delegates_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = RuntimeStatus(
        loaded_model="qwen3.5-4b-q4",
        server_pid=4321,
        server_port=11434,
        is_running=True,
        is_healthy=True,
        models_dir=Path("/tmp/models"),
    )

    monkeypatch.setattr(
        "artifactminer.local_llm.client._get_server_status",
        lambda: expected,
    )

    assert runtime_status() == expected
