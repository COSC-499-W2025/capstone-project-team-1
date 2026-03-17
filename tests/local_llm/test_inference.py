from __future__ import annotations

from types import SimpleNamespace

import pytest

from artifactminer.local_llm.runtime.errors import (
    InferenceRequestError,
    InvalidLLMResponseError,
)
from artifactminer.local_llm.runtime.inference import query_llm_text
from artifactminer.local_llm.models import RuntimeStatus


def _status(port: int = 11434) -> RuntimeStatus:
    return RuntimeStatus(
        loaded_model="qwen2.5-coder-3b-q4",
        server_pid=1234,
        server_port=port,
        is_running=True,
        is_healthy=True,
        models_dir="/tmp/models",
    )


@pytest.mark.asyncio
async def test_query_llm_text_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create(**kwargs):
        assert kwargs["model"] == "local"
        assert kwargs["messages"] == [{"role": "user", "content": "hello"}]
        assert kwargs["temperature"] == 0.15
        assert kwargs["max_tokens"] == 12288
        assert kwargs["extra_body"] == {"top_p": 0.9}
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="generated text"))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.ensure_server",
        lambda model: None,
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.get_server_status",
        lambda: _status(),
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference._build_client",
        lambda port: fake_client,
    )

    result = await query_llm_text("hello", model="qwen2.5-coder-3b-q4")

    assert result == "generated text"


@pytest.mark.asyncio
async def test_query_llm_text_raises_for_runtime_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.ensure_server",
        lambda model: None,
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.get_server_status",
        lambda: RuntimeStatus(
            loaded_model=None,
            server_pid=None,
            server_port=None,
            is_running=False,
            is_healthy=False,
            models_dir="/tmp/models",
        ),
    )

    with pytest.raises(InferenceRequestError, match="not ready"):
        await query_llm_text("hello", model="qwen2.5-coder-3b-q4")


@pytest.mark.asyncio
async def test_query_llm_text_wraps_transport_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create(**kwargs):
        raise RuntimeError("boom")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.ensure_server",
        lambda model: None,
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.get_server_status",
        lambda: _status(),
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference._build_client",
        lambda port: fake_client,
    )

    with pytest.raises(InferenceRequestError, match="RuntimeError: boom"):
        await query_llm_text("hello", model="qwen2.5-coder-3b-q4")


@pytest.mark.asyncio
async def test_query_llm_text_rejects_empty_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="   "))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.ensure_server",
        lambda model: None,
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.get_server_status",
        lambda: _status(port=8080),
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference._build_client",
        lambda port: fake_client,
    )

    with pytest.raises(InvalidLLMResponseError, match="empty text response"):
        await query_llm_text("hello", model="qwen2.5-coder-3b-q4")


@pytest.mark.asyncio
async def test_query_llm_text_rejects_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create(**kwargs):
        return SimpleNamespace(choices=[])

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.ensure_server",
        lambda model: None,
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference.get_server_status",
        lambda: _status(),
    )
    monkeypatch.setattr(
        "artifactminer.local_llm.runtime.inference._build_client",
        lambda port: fake_client,
    )

    with pytest.raises(InvalidLLMResponseError, match="include any choices"):
        await query_llm_text("hello", model="qwen2.5-coder-3b-q4")
