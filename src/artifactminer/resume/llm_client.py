"""
LLM client using llama-server + OpenAI SDK.

Manages a llama-server subprocess and communicates via the OpenAI-compatible
HTTP API.  No llama-cpp-python build dependency — only needs the llama-server
binary (brew install llama.cpp) and the openai Python package.

Reasoning control: llama-server is launched with --reasoning-budget 0,
which completely disables thinking/reasoning for all models.
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Type, TypeVar, cast

import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

log = logging.getLogger(__name__)

# Models that support /no_think to disable chain-of-thought reasoning.
# Currently unused — reasoning is disabled at the server level via
# --reasoning-budget 0 for all models.
_SUPPORTS_NO_THINK_JSON: set[str] = set()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "qwen2.5-coder-3b-q4"  # Code-specialized model, Q4 for faster loading
MODELS_DIR = Path.home() / ".artifactminer" / "models"

# Task-specific model recommendations
# Use these for optimal performance on different tasks:
# - Code analysis (commits, skills): qwen2.5-coder-3b-q4 (fast, specialized)
# - Reasoning (narratives, complexity, skill evolution): deepseek-r1-qwen-1.5b-q8 (superior logic)
# - Prose generation (bullets, summary): lfm2-2.6b-q8 or qwen3-4b-q4

# Maps friendly name → (HuggingFace repo_id, filename, context_length)
MODEL_REGISTRY: dict[str, tuple[str, str, int]] = {
    # Code-specialized model (best for commit analysis, code understanding)
    "qwen2.5-coder-3b-q4": (
        "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
        "qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        16384,  # 16K context - sufficient for commit analysis, fast loading
    ),
    # Reasoning-specialized model (best for narratives, step-by-step logic)
    "deepseek-r1-qwen-1.5b-q8": (
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        "DeepSeek-R1-Distill-Qwen-1.5B-Q8_0.gguf",
        32768,  # 32K context - excellent for detailed reasoning
    ),
    "qwen3-4b-q4": (
        "unsloth/Qwen3-4B-Instruct-2507-GGUF",
        "Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
        20480,
    ),
    "qwen3-4b-q3": (
        "unsloth/Qwen3-4B-Instruct-2507-GGUF",
        "Qwen3-4B-Instruct-2507-Q3_K_M.gguf",
        20480,
    ),
    "qwen3-1.7b-q8": (
        "unsloth/Qwen3-1.7B-Instruct-GGUF",
        "Qwen3-1.7B-UD-Q8_K_XL.gguf",
        32768,
    ),
    "lfm2-2.6b-q8": (
        "LiquidAI/LFM2-2.6B-GGUF",
        "LFM2-2.6B-Q8_0.gguf",
        20480,
    ),
    "lfm2.5-1.2b-q4": (
        "LiquidAI/LFM2.5-1.2B-Instruct-GGUF",
        "LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
        32768,
    ),
    "lfm2.5-1.2b-bf16": (
        "LiquidAI/LFM2.5-1.2B-Instruct-GGUF",
        "LFM2.5-1.2B-Instruct-BF16.gguf",
        32768,
    ),
    # Prose-generation model (best for resume bullets, summaries, profiles)
    "llama-3.2-3b-q4": (
        "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        16384,
    ),
}

# Per-model sampling defaults — matched to each model family's characteristics.
# Keys use prefix matching: "lfm2.5" matches "lfm2.5-1.2b-q4", etc.
MODEL_SAMPLING_DEFAULTS: dict[str, dict[str, float]] = {
    "lfm2.5": {"temperature": 0.1, "top_p": 0.1, "repetition_penalty": 1.05},
    "qwen2.5-coder": {"temperature": 0.15, "top_p": 0.9},
    "qwen3": {"temperature": 0.2, "top_p": 0.9},
    "llama": {"temperature": 0.4, "top_p": 0.9, "repetition_penalty": 1.1},
    "default": {"temperature": 0.2, "top_p": 0.9},
}


def get_sampling_params(model: str) -> dict[str, float]:
    """Return the sampling parameters for a model, using prefix matching."""
    for prefix, params in MODEL_SAMPLING_DEFAULTS.items():
        if prefix != "default" and model.startswith(prefix):
            return dict(params)
    return dict(MODEL_SAMPLING_DEFAULTS["default"])


# ---------------------------------------------------------------------------
# Model path / GPU helpers (unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# llama-server lifecycle (private)
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
            "Install it with:  brew install llama.cpp\n"
            "Then verify with:  which llama-server"
        )
    return path


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
        raise FileNotFoundError(
            f"Model file not found: {model_path}. "
            f"Manually download the GGUF into {MODELS_DIR} or pass a direct .gguf path via --model."
        )

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
        "--reasoning-budget",
        "0",
        "--log-disable",
    ]

    log.info("[llm] Starting llama-server on port %d for model %s", port, model)
    # Temporarily enable logs for debugging startup issues
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
    log.info("[llm] llama-server healthy on port %d", port)


def _stop_server() -> None:
    """Terminate the running llama-server process."""
    global _server_process, _server_port, _server_model, _openai_client

    if _server_process is None:
        return

    log.info("[llm] Stopping llama-server (pid %d)", _server_process.pid)
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


def _restart_server(model: str) -> None:
    """Stop current server and start a new one with a different model."""
    _stop_server()
    _start_server(model)


def _ensure_server_running(model: str) -> None:
    """Ensure llama-server is running with the requested model."""
    if (
        _server_process is not None
        and _server_process.poll() is None
        and _server_model == model
    ):
        return  # already running with the right model

    if _server_process is not None:
        _restart_server(model)
    else:
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
# Model loading API (adapted for server lifecycle)
# ---------------------------------------------------------------------------


def get_model(model: str = DEFAULT_MODEL) -> OpenAI:
    """
    Ensure the server is running with the given model and return the client.

    Preserves the same call semantics as the old get_model() — callers like
    benchmark.py use it to measure startup time.
    """
    _ensure_server_running(model)
    return _get_client()


def unload_model(model: str | None = None) -> None:
    """Stop the server to free resources. Model arg kept for API compat."""
    _stop_server()


# ---------------------------------------------------------------------------
# Model management (unchanged)
# ---------------------------------------------------------------------------


def ensure_model_available(model: str = DEFAULT_MODEL) -> None:
    """
    Ensure a model GGUF file exists on disk.

    This project intentionally does not auto-download models.
    Download a GGUF manually and place it in ~/.artifactminer/models/ (or pass
    a direct path to a .gguf file).
    """
    try:
        path = _resolve_model_path(model)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Model '{model}' was not found. Provide a direct path to a .gguf file "
            f"or use a known model name: {', '.join(MODEL_REGISTRY)}."
        ) from exc

    if path.exists():
        return

    # Helpful manual download instructions for registry models
    if model in MODEL_REGISTRY:
        repo_id, filename, _ = MODEL_REGISTRY[model]
        raise RuntimeError(
            f"Model '{model}' is not available locally at {path}. "
            f"Manually download '{filename}' from https://huggingface.co/{repo_id} "
            f"and place it in {MODELS_DIR} (or pass --model /path/to/{filename})."
        )

    raise RuntimeError(
        f"Model '{model}' is not available locally at {path}. "
        f"Provide a direct path to a .gguf file."
    )


def check_llm_available(model: str = DEFAULT_MODEL) -> bool:
    """Check if a model's GGUF file exists on disk."""
    try:
        path = _resolve_model_path(model)
        return path.exists()
    except FileNotFoundError:
        return False


def get_available_models() -> list[str]:
    """List models available locally (GGUF files in the models directory)."""
    models = []
    if MODELS_DIR.exists():
        for f in MODELS_DIR.glob("*.gguf"):
            # Check if it matches a registry entry
            matched = False
            for name, (_, filename, _) in MODEL_REGISTRY.items():
                if f.name == filename:
                    models.append(name)
                    matched = True
                    break
            if not matched:
                models.append(f.stem)
    return sorted(models)


# ---------------------------------------------------------------------------
# Inference: structured JSON output
# ---------------------------------------------------------------------------


def query_llm(
    prompt: str,
    schema: Type[T],
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.1,
) -> T:
    """
    Query the LLM for structured JSON output conforming to a Pydantic schema.

    Uses llama-server's json_schema response format for constrained decoding.
    """
    _ensure_server_running(model)
    client = _get_client()

    # Disable thinking for JSON calls — schema constraints guide output
    effective_prompt = prompt
    if model in _SUPPORTS_NO_THINK_JSON:
        effective_prompt = prompt + " /no_think"

    messages: list[ChatCompletionMessageParam] = []
    if system:
        messages.append(
            cast(ChatCompletionMessageParam, {"role": "system", "content": system})
        )
    messages.append(
        cast(ChatCompletionMessageParam, {"role": "user", "content": effective_prompt})
    )

    response = client.chat.completions.create(
        model="local",
        messages=messages,
        temperature=temperature,
        extra_body={
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            },
        },
    )

    content = response.choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError(
            f"LLM returned empty response. Model '{model}' may not support "
            f"structured JSON output, or the context window was exceeded."
        )

    return schema.model_validate_json(content)


# ---------------------------------------------------------------------------
# Inference: free-form text output
# ---------------------------------------------------------------------------


def query_llm_text(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 12288,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    grammar: str | None = None,
) -> str:
    """
    Query the LLM for plain text output.

    With --reasoning-budget 0, thinking is disabled at the server level.
    Accepts optional top_p and repetition_penalty for per-model tuning.

    If ``grammar`` is provided, llama-server uses GBNF grammar-constrained
    decoding to enforce the output structure.  Cannot be combined with
    ``response_format`` (JSON schema mode).
    """
    _ensure_server_running(model)
    client = _get_client()

    messages: list[ChatCompletionMessageParam] = []
    if system:
        messages.append(
            cast(ChatCompletionMessageParam, {"role": "system", "content": system})
        )
    messages.append(
        cast(ChatCompletionMessageParam, {"role": "user", "content": prompt})
    )

    extra_body: dict[str, Any] = {}
    if top_p is not None:
        extra_body["top_p"] = top_p
    if repetition_penalty is not None:
        extra_body["repetition_penalty"] = repetition_penalty
    if grammar is not None:
        extra_body["grammar"] = grammar

    kwargs: dict[str, Any] = {
        "model": "local",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_body:
        kwargs["extra_body"] = extra_body

    response = client.chat.completions.create(**kwargs)

    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Async wrappers (OpenAI SDK calls are synchronous — run in thread pool)
# ---------------------------------------------------------------------------


async def query_llm_async(
    prompt: str,
    schema: Type[T],
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.1,
) -> T:
    """Async version of query_llm. Runs inference in a thread pool."""
    return await asyncio.to_thread(
        query_llm,
        prompt,
        schema,
        model=model,
        system=system,
        temperature=temperature,
    )


async def query_llm_text_async(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 12288,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    grammar: str | None = None,
) -> str:
    """Async version of query_llm_text. Runs inference in a thread pool."""
    return await asyncio.to_thread(
        query_llm_text,
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        grammar=grammar,
    )
