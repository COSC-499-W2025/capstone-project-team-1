"""Health-check helpers for llama-server readiness polling."""

from __future__ import annotations

import time

import httpx

from .config import DEFAULT_HEALTH_TIMEOUT_SECONDS
from .errors import ModelStartupTimeoutError

_PER_REQUEST_TIMEOUT = 2.0
_LOOPBACK = "127.0.0.1"
_DEFAULT_POLL_INTERVAL = 0.25


def _check_health(port: int) -> bool:
    """Single-shot GET to the llama-server /health endpoint."""

    try:
        resp = httpx.get(
            f"http://{_LOOPBACK}:{port}/health",
            timeout=_PER_REQUEST_TIMEOUT,
        )
        return resp.status_code == 200
    except httpx.RequestError:
        return False


def poll_until_healthy(
    port: int,
    model: str,
    *,
    timeout: float = DEFAULT_HEALTH_TIMEOUT_SECONDS,
    poll_interval: float = _DEFAULT_POLL_INTERVAL,
) -> None:
    """Block until llama-server reports healthy, or raise on timeout.

    Raises ``ModelStartupTimeoutError`` if the server does not return
    HTTP 200 on ``/health`` before *timeout* seconds elapse.
    """

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _check_health(port):
            return
        time.sleep(poll_interval)
    raise ModelStartupTimeoutError(model, timeout)
