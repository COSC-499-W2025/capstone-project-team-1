"""
Local LLM helper using llama-server + OpenAI SDK.

Manages a llama-server subprocess and communicates via the OpenAI-compatible
HTTP API. No llama-cpp-python build dependency — only needs the llama-server
binary and the openai Python package.

Setup:
    1. Install llama.cpp binary:
       - macOS: brew install llama.cpp
       - Linux: sudo apt install llama.cpp  or build from source
       - Windows: download from https://github.com/ggerganov/llama.cpp/releases
    
    2. Download a model GGUF file to ~/.artifactminer/models/
       Example: qwen3-1.7b-instruct-q8.gguf

Usage:
    from artifactminer.helpers.local_llm import get_local_llm_response
    
    response = get_local_llm_response("Explain what FastAPI is")
"""

from __future__ import annotations

import atexit
import logging
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, cast

import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "qwen3-1.7b-q8"
MODELS_DIR = Path.home() / ".artifactminer" / "models"

# Maps friendly name → (HuggingFace repo_id, filename, context_length)
MODEL_REGISTRY: dict[str, tuple[str, str, int]] = {
    "qwen3-1.7b-q8": (
        "unsloth/Qwen3-1.7B-Instruct-GGUF",
        "Qwen3-1.7B-UD-Q8_K_XL.gguf",
        32768,
    ),
    "qwen2.5-coder-3b-q4": (
        "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
        "qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        16384,
    ),
}

# ---------------------------------------------------------------------------
# Server lifecycle (private state)
# ---------------------------------------------------------------------------

_server_process: subprocess.Popen | None = None
_server_port: int | None = None
_server_model: str | None = None
_openai_client: OpenAI | None = None


def _find_llama_server() -> str:
    """Locate the llama-server binary on PATH."""
    path = shutil.which("llama-server")
    if path is None:
        raise FileNotFoundError(
            "llama-server binary not found on PATH.\n"
            "Install it with:\n"
            "  macOS: brew install llama.cpp\n"
            "  Linux: sudo apt install llama.cpp\n"
            "  Windows: download from https://github.com/ggerganov/llama.cpp/releases"
        )
    return path


def _resolve_model_path(model: str) -> Path:
    """Resolve a model name to its GGUF file path on disk."""
    # Direct path — user passed a .gguf file path
    if model.endswith(".gguf"):
        return Path(model)

    # Registry lookup
    if model in MODEL_REGISTRY:
        _, filename, _ = MODEL_REGISTRY[model]
        return MODELS_DIR / filename

    # Check if it's a filename in the models dir
    candidate = MODELS_DIR / model
    if candidate.exists():
        return candidate
    candidate_gguf = MODELS_DIR / f"{model}.gguf"
    if candidate_gguf.exists():
        return candidate_gguf

    raise FileNotFoundError(
        f"Model '{model}' not found. "
        f"Known models: {', '.join(MODEL_REGISTRY)}. "
        f"Or provide a path to a .gguf file."
    )


def _get_n_ctx(model: str) -> int:
    """Get the context length for a model."""
    if model in MODEL_REGISTRY:
        return MODEL_REGISTRY[model][2]
    return 4096


def _get_gpu_layers() -> int:
    """Determine GPU layer offload count based on platform."""
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return -1  # Metal: offload all layers
    return 0  # CPU-only by default on other platforms


def _pick_free_port() -> int:
    """Get an OS-assigned ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 60.0) -> None:
    """Poll llama-server /health until it returns 200 or timeout."""
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                return
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(0.25)
    raise TimeoutError(
        f"llama-server did not become healthy on port {port} within {timeout}s"
    )


def _start_server(model: str) -> None:
    """Spawn a llama-server subprocess for the given model."""
    global _server_process, _server_port, _server_model, _openai_client

    binary = _find_llama_server()
    model_path = _resolve_model_path(model)
    if not model_path.exists():
        # Give helpful download instructions
        if model in MODEL_REGISTRY:
            repo_id, filename, _ = MODEL_REGISTRY[model]
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Download '{filename}' from https://huggingface.co/{repo_id}\n"
                f"and place it in {MODELS_DIR}"
            )
        raise FileNotFoundError(f"Model file not found: {model_path}")

    port = _pick_free_port()
    n_ctx = _get_n_ctx(model)
    gpu = _get_gpu_layers()

    cmd = [
        binary,
        "--model",
        str(model_path),
        "--ctx-size",
        str(n_ctx),
        "--n-gpu-layers",
        str(gpu),
        "--port",
        str(port),
        "--log-disable",
    ]

    log.info(f"[local_llm] Starting llama-server on port {port} for model {model}")
    _server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    _server_port = port
    _server_model = model
    _openai_client = None  # force re-creation

    atexit.register(_stop_server)

    _wait_for_server(port)
    log.info(f"[local_llm] llama-server healthy on port {port}")


def _stop_server() -> None:
    """Terminate the running llama-server process."""
    global _server_process, _server_port, _server_model, _openai_client

    if _server_process is None:
        return

    log.info(f"[local_llm] Stopping llama-server (pid {_server_process.pid})")
    _server_process.terminate()
    try:
        _server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _server_process.kill()
        _server_process.wait()

    _server_process = None
    _server_port = None
    _server_model = None
    _openai_client = None


def _ensure_server_running(model: str) -> None:
    """Ensure llama-server is running with the requested model."""
    if (
        _server_process is not None
        and _server_process.poll() is None
        and _server_model == model
    ):
        return  # already running with the right model

    if _server_process is not None:
        _stop_server()
    
    _start_server(model)


def _get_client() -> OpenAI:
    """Return a lazily-created OpenAI client pointed at the local server."""
    global _openai_client

    if _openai_client is None:
        if _server_port is None:
            raise RuntimeError("llama-server is not running")
        _openai_client = OpenAI(
            base_url=f"http://127.0.0.1:{_server_port}/v1",
            api_key="not-needed",
        )
    return _openai_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_local_llm_response(
    prompt: str,
    model: str = DEFAULT_MODEL,
    *,
    temperature: float = 0.3,
    max_tokens: int = 12288,
) -> str:
    """
    Query the local LLM for a text response.

    Args:
        prompt: The prompt/query to send to the LLM.
        model: Model name to use (defaults to qwen3-1.7b-q8).
        temperature: Sampling temperature (0.0 = deterministic, higher = creative).
        max_tokens: Maximum tokens to generate.

    Returns:
        Plain text response from the LLM.

    Raises:
        FileNotFoundError: If llama-server binary or model file is missing.
        TimeoutError: If llama-server doesn't start within 60 seconds.
        RuntimeError: If the LLM returns an empty response.
    """
    _ensure_server_running(model)
    client = _get_client()

    messages: list[ChatCompletionMessageParam] = [
        cast(ChatCompletionMessageParam, {"role": "user", "content": prompt})
    ]

    response = client.chat.completions.create(
        model="local",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError("LLM returned empty response")
    
    return content


def stop_local_llm() -> None:
    """Stop the llama-server process to free resources."""
    _stop_server()


def is_local_llm_available(model: str = DEFAULT_MODEL) -> bool:
    """Check if llama-server binary and model file are available."""
    try:
        _find_llama_server()
        path = _resolve_model_path(model)
        return path.exists()
    except (FileNotFoundError, RuntimeError):
        return False
