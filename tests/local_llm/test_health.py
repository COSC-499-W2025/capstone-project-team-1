"""Tests for the llama-server health-check polling helpers."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from artifactminer.local_llm.runtime.config import DEFAULT_HEALTH_TIMEOUT_SECONDS
from artifactminer.local_llm.runtime.errors import ModelStartupTimeoutError
from artifactminer.local_llm.runtime.health import _check_health, poll_until_healthy

_HEALTH_MODULE = "artifactminer.local_llm.runtime.health"
_MODEL = "qwen3.5-4b-q4"


@patch(f"{_HEALTH_MODULE}.httpx.get", return_value=httpx.Response(200))
def test_check_health_returns_true_on_200(mock_get) -> None:
    assert _check_health(8080) is True
    mock_get.assert_called_once_with("http://127.0.0.1:8080/health", timeout=2.0)


@pytest.mark.parametrize("status_code", [404, 500, 503])
@patch(f"{_HEALTH_MODULE}.httpx.get")
def test_check_health_returns_false_on_non_200(mock_get, status_code: int) -> None:
    mock_get.return_value = httpx.Response(status_code)
    assert _check_health(8080) is False


@patch(
    f"{_HEALTH_MODULE}.httpx.get",
    side_effect=httpx.RemoteProtocolError("malformed response"),
)
def test_check_health_returns_false_on_request_error(mock_get) -> None:
    assert _check_health(8080) is False
    assert mock_get.call_count == 1


def test_poll_returns_immediately_when_healthy() -> None:
    with (
        patch(f"{_HEALTH_MODULE}._check_health", return_value=True) as mock_check,
        patch(f"{_HEALTH_MODULE}.time.sleep") as mock_sleep,
    ):
        poll_until_healthy(8080, _MODEL, timeout=5.0)

    mock_check.assert_called_once_with(8080)
    mock_sleep.assert_not_called()


def test_poll_retries_until_healthy() -> None:
    # First monotonic() sets the deadline; later values are loop checks before
    # each health probe. This gives two failed polls, then one success.
    with (
        patch(
            f"{_HEALTH_MODULE}._check_health",
            side_effect=[False, False, True],
        ) as mock_check,
        patch(
            f"{_HEALTH_MODULE}.time.monotonic",
            side_effect=[0.0, 0.0, 0.25, 0.5],
        ),
        patch(f"{_HEALTH_MODULE}.time.sleep") as mock_sleep,
    ):
        poll_until_healthy(8080, _MODEL, timeout=1.0, poll_interval=0.25)

    assert mock_check.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(0.25)


def test_poll_raises_timeout_error_with_default_timeout() -> None:
    # The second loop check lands past the default deadline, so polling should
    # stop with the typed timeout error.
    with (
        patch(f"{_HEALTH_MODULE}._check_health", return_value=False),
        patch(
            f"{_HEALTH_MODULE}.time.monotonic",
            side_effect=[0.0, 0.0, DEFAULT_HEALTH_TIMEOUT_SECONDS + 0.01],
        ),
        patch(f"{_HEALTH_MODULE}.time.sleep"),
    ):
        with pytest.raises(ModelStartupTimeoutError) as exc_info:
            poll_until_healthy(8080, _MODEL)

    assert exc_info.value.model == _MODEL
    assert exc_info.value.timeout_seconds == DEFAULT_HEALTH_TIMEOUT_SECONDS


def test_poll_respects_custom_interval_and_stops_at_deadline() -> None:
    # One failed check is allowed before sleep moves time past the deadline.
    with (
        patch(f"{_HEALTH_MODULE}._check_health", return_value=False) as mock_check,
        patch(
            f"{_HEALTH_MODULE}.time.monotonic",
            side_effect=[0.0, 0.0, 0.3],
        ),
        patch(f"{_HEALTH_MODULE}.time.sleep") as mock_sleep,
    ):
        with pytest.raises(ModelStartupTimeoutError):
            poll_until_healthy(8080, _MODEL, timeout=0.1, poll_interval=0.25)

    assert mock_check.call_count == 1
    mock_sleep.assert_called_once_with(0.25)
