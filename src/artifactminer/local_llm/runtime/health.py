"""Health-check helpers for llama-server readiness polling."""

from __future__ import annotations

import time

import httpx

from .config import DEFAULT_HEALTH_TIMEOUT_SECONDS
from .errors import ModelStartupTimeoutError

_PER_REQUEST_TIMEOUT = 2.0
# The local runtime only ever talks to a user-managed llama-server on loopback.
_LOOPBACK = "127.0.0.1"
_DEFAULT_POLL_INTERVAL = 0.25


def _check_health(port: int, *, timeout: float = _PER_REQUEST_TIMEOUT) -> bool:
    """Single-shot GET to the llama-server /health endpoint."""

    try:
        resp = httpx.get(
            f"http://{_LOOPBACK}:{port}/health",
            timeout=timeout,
        )
        return resp.status_code == 200
    except httpx.RequestError:
        # Transport failures still mean "not ready yet" here; the public polling
        # helper converts prolonged failure into the typed timeout error.
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
    # Cap both the per-request timeout and sleep to the remaining budget so the
    # total wall-clock time never exceeds the caller's timeout.
    remaining = deadline - time.monotonic()
    while remaining > 0:
        if _check_health(port, timeout=min(_PER_REQUEST_TIMEOUT, remaining)):
            return
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(poll_interval, remaining))
    raise ModelStartupTimeoutError(model, timeout)
