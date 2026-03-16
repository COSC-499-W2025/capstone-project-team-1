"""Process lifecycle management for a local llama-server instance."""

from __future__ import annotations

import atexit
import shutil
import socket
import subprocess
from pathlib import Path

from ..models import RuntimeStatus
from .config import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODELS_DIR,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    default_gpu_layers,
    resolve_context_window,
)
from .errors import (
    LlamaServerNotFoundError,
    LocalLLMRuntimeError,
    ModelServerCrashedError,
    ModelStartupTimeoutError,
)
from .health import check_health, poll_until_healthy
from .registry import resolve_model_descriptor

_server_process: subprocess.Popen[bytes] | None = None
_server_port: int | None = None
_server_model: str | None = None

_TERMINATE_TIMEOUT_SECONDS = 5
_atexit_registered = False


def _find_llama_server() -> str:
    """Locate the llama-server binary on PATH."""

    path = shutil.which("llama-server")
    if path is None:
        raise LlamaServerNotFoundError()
    return path


def _pick_free_port() -> int:
    """Bind to an ephemeral loopback port and return the OS-assigned number."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _reset_state() -> None:
    """Clear all module-level process state."""

    global _server_process, _server_port, _server_model  # noqa: PLW0603
    _server_process = None
    _server_port = None
    _server_model = None


def _is_process_alive() -> bool:
    """Return True if the managed process exists and has not exited."""

    return _server_process is not None and _server_process.poll() is None


def _detect_crash() -> None:
    """Raise ``ModelServerCrashedError`` if the managed process exited unexpectedly.

    Does nothing when no server has been started or when the process is
    still alive.
    """

    if _server_process is None:
        return
    if _server_process.poll() is not None:
        exit_code = _server_process.returncode
        model = _server_model
        _reset_state()
        raise ModelServerCrashedError(model=model, exit_code=exit_code)


def start_server(
    model: str = DEFAULT_MODEL_NAME,
    *,
    models_dir: Path = DEFAULT_MODELS_DIR,
    timeout: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> None:
    """Start a llama-server subprocess and block until it is healthy.

    Raises ``LocalLLMRuntimeError`` if a server is already running.
    Raises ``ModelStartupTimeoutError`` if the server does not become
    healthy within *timeout* seconds, or ``ModelServerCrashedError`` if
    the process exits before becoming healthy.
    """

    global _server_process, _server_port, _server_model  # noqa: PLW0603

    if _server_process is not None:
        raise LocalLLMRuntimeError(
            "A llama-server process is already running. "
            "Call stop_server() before starting a new one."
        )

    binary = _find_llama_server()
    descriptor = resolve_model_descriptor(model, models_dir)
    port = _pick_free_port()
    ctx = resolve_context_window(descriptor.context_window)
    gpu = default_gpu_layers()

    cmd = [
        binary,
        "--model",
        str(descriptor.path),
        "--ctx-size",
        str(ctx),
        "--n-gpu-layers",
        str(gpu),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-disable",
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _server_process = proc
    _server_port = port
    _server_model = model
    global _atexit_registered  # noqa: PLW0603
    if not _atexit_registered:
        atexit.register(stop_server)
        _atexit_registered = True

    try:
        poll_until_healthy(port, model, timeout=timeout)
    except ModelStartupTimeoutError:
        if proc.poll() is not None:
            _reset_state()
            raise ModelServerCrashedError(model=model, exit_code=proc.returncode)
        stop_server()
        raise


def stop_server() -> None:
    """Terminate the running llama-server process, if any."""

    global _server_process  # noqa: PLW0603

    if _server_process is None:
        return

    _server_process.terminate()
    try:
        _server_process.wait(timeout=_TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _server_process.kill()
        _server_process.wait()

    _reset_state()


def ensure_server(
    model: str = DEFAULT_MODEL_NAME,
    *,
    models_dir: Path = DEFAULT_MODELS_DIR,
    timeout: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> None:
    """Ensure a llama-server is running with the requested model.

    * If the same model is already loaded and the process is alive, returns
      immediately (reuse).
    * If a different model is loaded, the current server is stopped and a
      new one is started (restart).
    * If the previously started server has crashed, raises
      ``ModelServerCrashedError``.
    """

    if _server_process is None:
        start_server(model, models_dir=models_dir, timeout=timeout)
        return

    # Process exited unexpectedly → crash
    _detect_crash()

    # Same model, still alive → reuse
    if _server_model == model:
        return

    # Different model requested → restart
    restart_server(model, models_dir=models_dir, timeout=timeout)


def restart_server(
    model: str = DEFAULT_MODEL_NAME,
    *,
    models_dir: Path = DEFAULT_MODELS_DIR,
    timeout: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> None:
    """Stop the current server (if any) and start a fresh one."""

    stop_server()
    start_server(model, models_dir=models_dir, timeout=timeout)


def get_server_status() -> RuntimeStatus:
    """Return the current runtime state as a ``RuntimeStatus`` snapshot.

    The snapshot is safe to serialize or pass to higher layers without
    exposing subprocess internals.  Performs a single-shot health check
    when the process is alive.
    """

    if _server_process is None:
        return RuntimeStatus(
            loaded_model=None,
            server_pid=None,
            server_port=None,
            is_running=False,
            is_healthy=False,
            models_dir=DEFAULT_MODELS_DIR,
        )

    running = _is_process_alive()
    healthy = False
    if running and _server_port is not None:
        healthy = check_health(_server_port)

    return RuntimeStatus(
        loaded_model=_server_model,
        server_pid=_server_process.pid if running else None,
        server_port=_server_port if running else None,
        is_running=running,
        is_healthy=healthy,
        models_dir=DEFAULT_MODELS_DIR,
    )
