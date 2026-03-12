"""Tests for the llama-server health-check polling helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from artifactminer.local_llm.runtime.config import DEFAULT_HEALTH_TIMEOUT_SECONDS
from artifactminer.local_llm.runtime.errors import ModelStartupTimeoutError
from artifactminer.local_llm.runtime.health import poll_until_healthy

_HEALTH_MODULE = "artifactminer.local_llm.runtime.health"


def _ok_response() -> httpx.Response:
    return httpx.Response(200)


def _make_monotonic_sequence(*values: float):
    """Return an iterator-based side_effect for ``time.monotonic``."""
    it = iter(values)
    return lambda: next(it)


class TestPollUntilHealthy:
    """Unit tests for ``poll_until_healthy``."""

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.httpx.get", return_value=_ok_response())
    def test_poll_returns_immediately_when_healthy(
        self, mock_get: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """First health check passes — sleep is never called."""

        poll_until_healthy(8080, "qwen3.5-4b-q4", timeout=5.0)
        mock_get.assert_called_once()
        mock_sleep.assert_not_called()

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.time.monotonic")
    @patch(f"{_HEALTH_MODULE}.httpx.get")
    def test_poll_succeeds_after_transient_failures(
        self, mock_get: MagicMock, mock_mono: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Connection errors followed by a 200 — returns cleanly."""

        mock_get.side_effect = [
            httpx.ConnectError("refused"),
            httpx.ConnectError("refused"),
            _ok_response(),
        ]
        # monotonic: start=0, loop checks at 1, 2, and 3 seconds
        mock_mono.side_effect = _make_monotonic_sequence(0.0, 1.0, 2.0, 3.0)

        poll_until_healthy(8080, "qwen3.5-4b-q4", timeout=10.0)
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.time.monotonic")
    @patch(f"{_HEALTH_MODULE}.httpx.get", side_effect=httpx.ConnectError("refused"))
    def test_poll_raises_on_timeout(
        self, mock_get: MagicMock, mock_mono: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Persistent failures until deadline — raises with correct attrs."""

        # monotonic: start=0, first check=5 (past deadline of 3)
        mock_mono.side_effect = _make_monotonic_sequence(0.0, 5.0)

        with pytest.raises(ModelStartupTimeoutError) as exc_info:
            poll_until_healthy(8080, "qwen3.5-4b-q4", timeout=3.0)

        assert exc_info.value.model == "qwen3.5-4b-q4"
        assert exc_info.value.timeout_seconds == 3.0

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.time.monotonic")
    @patch(f"{_HEALTH_MODULE}.httpx.get", side_effect=httpx.ConnectError("refused"))
    def test_poll_does_not_probe_again_after_deadline_passes(
        self, mock_get: MagicMock, mock_mono: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """If sleep carries past the deadline, no extra health probe is made."""

        mock_mono.side_effect = _make_monotonic_sequence(0.0, 0.05, 0.3)

        with pytest.raises(ModelStartupTimeoutError):
            poll_until_healthy(8080, "qwen3.5-4b-q4", timeout=0.1, poll_interval=0.25)

        assert mock_get.call_count == 1
        mock_sleep.assert_called_once_with(0.25)

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.time.monotonic")
    @patch(f"{_HEALTH_MODULE}.httpx.get", side_effect=httpx.ConnectError("refused"))
    def test_poll_uses_default_timeout_from_config(
        self, mock_get: MagicMock, mock_mono: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """When no timeout is given, the config default is used."""

        mock_mono.side_effect = _make_monotonic_sequence(
            0.0, DEFAULT_HEALTH_TIMEOUT_SECONDS + 1.0
        )

        with pytest.raises(ModelStartupTimeoutError) as exc_info:
            poll_until_healthy(8080, "qwen3.5-4b-q4")

        assert exc_info.value.timeout_seconds == DEFAULT_HEALTH_TIMEOUT_SECONDS

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.time.monotonic")
    @patch(f"{_HEALTH_MODULE}.httpx.get")
    def test_poll_respects_custom_poll_interval(
        self, mock_get: MagicMock, mock_mono: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Custom poll_interval is forwarded to sleep."""

        mock_get.side_effect = [
            httpx.ConnectError("refused"),
            _ok_response(),
        ]
        mock_mono.side_effect = _make_monotonic_sequence(0.0, 0.5, 1.0)

        poll_until_healthy(8080, "qwen3.5-4b-q4", timeout=10.0, poll_interval=0.75)
        mock_sleep.assert_called_once_with(0.75)

    @patch(f"{_HEALTH_MODULE}.time.sleep")
    @patch(f"{_HEALTH_MODULE}.time.monotonic")
    @patch(
        f"{_HEALTH_MODULE}.httpx.get",
        side_effect=httpx.RemoteProtocolError("malformed response"),
    )
    def test_poll_treats_other_request_errors_as_unhealthy(
        self, mock_get: MagicMock, mock_mono: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Non-timeout transport failures should still lead to typed timeout."""

        mock_mono.side_effect = _make_monotonic_sequence(0.0, 0.5, 2.0)

        with pytest.raises(ModelStartupTimeoutError) as exc_info:
            poll_until_healthy(8080, "qwen3.5-4b-q4", timeout=1.0)

        assert exc_info.value.timeout_seconds == 1.0
        assert mock_get.call_count == 1
