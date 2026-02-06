"""
Embedded LLM client using llama-cpp-python.

Replaces the Ollama-based client with in-process inference via llama.cpp.
No daemon needed — models are GGUF files loaded directly into the Python process.
Auto-downloads from HuggingFace on first use.
"""

from __future__ import annotations

import asyncio
import json
import platform
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "qwen3-1.7b"
MODELS_DIR = Path.home() / ".artifactminer" / "models"

# Maps friendly name → (HuggingFace repo_id, filename, context_length)
MODEL_REGISTRY: dict[str, tuple[str, str, int]] = {
    "qwen3-1.7b": (
        "bartowski/Qwen_Qwen3-1.7B-GGUF",
        "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        4096,
    ),
    "lfm2.5-1.2b": (
        "LiquidAI/LFM2.5-1.2B-Instruct-GGUF",
        "LFM2.5-1.2B-Instruct-Q4_K_M.gguf",
        4096,
    ),
}

# ---------------------------------------------------------------------------
# Model loading (lazy, cached)
# ---------------------------------------------------------------------------

_loaded_models: dict[str, object] = {}


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


def get_model(model: str = DEFAULT_MODEL) -> object:
    """
    Load and cache a Llama model instance.

    On first call for a given model, loads the GGUF file (1-2 seconds).
    Subsequent calls return the cached instance.
    """
    if model in _loaded_models:
        return _loaded_models[model]

    from llama_cpp import Llama

    model_path = _resolve_model_path(model)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found: {model_path}. "
            f"Run 'resume download-model {model}' to download it."
        )

    llm = Llama(
        model_path=str(model_path),
        n_ctx=_get_n_ctx(model),
        n_gpu_layers=_get_gpu_layers(),
        verbose=False,
    )
    _loaded_models[model] = llm
    return llm


def unload_model(model: str | None = None) -> None:
    """Unload a cached model to free memory. If model is None, unload all."""
    if model is None:
        _loaded_models.clear()
    else:
        _loaded_models.pop(model, None)


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------


def ensure_model_available(model: str = DEFAULT_MODEL) -> None:
    """
    Ensure a model is available on disk, downloading if necessary.

    Raises RuntimeError with a helpful message if download fails.
    """
    try:
        path = _resolve_model_path(model)
        if path.exists():
            return
    except FileNotFoundError:
        pass

    # Need to download
    if model not in MODEL_REGISTRY:
        raise RuntimeError(
            f"Model '{model}' is not in the registry and no .gguf file found. "
            f"Known models: {', '.join(MODEL_REGISTRY)}. "
            f"Or provide a direct path to a .gguf file."
        )

    repo_id, filename, _ = MODEL_REGISTRY[model]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / filename

    print(f"[llm] Downloading {model} from {repo_id}...")
    print(f"[llm] Destination: {dest}")

    try:
        from huggingface_hub import hf_hub_download

        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(MODELS_DIR),
            local_dir_use_symlinks=False,
        )
        print(f"[llm] Download complete: {dest}")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download model '{model}' from HuggingFace. "
            f"Check your internet connection, or manually download "
            f"'{filename}' from https://huggingface.co/{repo_id} "
            f"and place it in {MODELS_DIR}"
        ) from exc


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

    Uses llama.cpp's grammar-based constrained decoding to guarantee valid JSON.
    """
    llm = get_model(model)

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = llm.create_chat_completion(
        messages=messages,
        response_format={
            "type": "json_object",
            "schema": schema.model_json_schema(),
        },
        temperature=temperature,
    )

    content = response["choices"][0]["message"]["content"] or ""
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
    max_tokens: int = 2048,
) -> str:
    """Query the LLM for plain text output."""
    llm = get_model(model)

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = llm.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response["choices"][0]["message"]["content"] or ""


# ---------------------------------------------------------------------------
# Async wrappers (llama.cpp is synchronous — run in thread pool)
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
    max_tokens: int = 2048,
) -> str:
    """Async version of query_llm_text. Runs inference in a thread pool."""
    return await asyncio.to_thread(
        query_llm_text,
        prompt,
        model=model,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )
