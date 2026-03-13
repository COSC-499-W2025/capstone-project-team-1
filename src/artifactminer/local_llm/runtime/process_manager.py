"""Process lifecycle management for a local llama-server instance."""

from __future__ import annotations

import atexit
import shutil
import socket
import subprocess
from pathlib import Path

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
from .health import poll_until_healthy
from .registry import resolve_model_descriptor

_server_process: subprocess.Popen[bytes] | None = None
_server_port: int | None = None
_server_model: str | None = None

_TERMINATE_TIMEOUT_SECONDS = 5


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
        "--port",
        str(port),
        "--log-disable",
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _server_process = proc
    _server_port = port
    _server_model = model
    atexit.register(stop_server)

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
