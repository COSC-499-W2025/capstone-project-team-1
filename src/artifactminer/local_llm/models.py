"""Shared type definitions for the local LLM runtime."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class InferenceOptions(BaseModel):
    """Reusable sampling and response-shaping options for local inference."""

    # Frozen models make runtime defaults safer to share across helpers without
    # accidental mutation leaking between requests.
    model_config = ConfigDict(extra="forbid", frozen=True)

    system: str | None = Field(
        default=None, description="Optional system prompt to prepend."
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        description="Sampling temperature override for generation.",
    )
    top_p: float | None = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Nucleus sampling override for generation.",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum number of output tokens to generate.",
    )
    repetition_penalty: float | None = Field(
        default=None,
        gt=0.0,
        description="Penalty applied to repeated tokens.",
    )
    grammar: str | None = Field(
        default=None,
        description="Optional GBNF grammar for constrained decoding.",
    )


class ModelDescriptor(BaseModel):
    """Metadata for a locally available or registry-backed model."""

    # This model is used both for curated registry entries and for ad-hoc local
    # GGUF files discovered on disk, so most fields are optional except the
    # user-facing name and resolved context window.
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(
        min_length=1,
        description="Approved model name used across the local runtime.",
    )
    filename: str | None = Field(
        default=None, description="Expected GGUF filename for registry-backed models."
    )
    repo_url: str | None = Field(
        default=None,
        description="Optional source URL for manual model downloads.",
    )
    context_window: int = Field(
        gt=0, description="Recommended runtime context window for the model."
    )
    path: Path | None = Field(
        default=None, description="Resolved GGUF path when a concrete file is known."
    )


class RuntimeStatus(BaseModel):
    """Runtime process status exposed to future client layers."""

    # This is intentionally small and transport-friendly so higher layers can
    # report runtime state without knowing subprocess details.
    model_config = ConfigDict(extra="forbid", frozen=True)

    loaded_model: str | None = Field(
        default=None, description="Currently loaded model name, if any."
    )
    server_pid: int | None = Field(
        default=None, ge=1, description="PID of the active llama-server process."
    )
    server_port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description="Bound localhost port for the active llama-server process.",
    )
    is_running: bool = Field(
        default=False, description="Whether a llama-server process is active."
    )
    is_healthy: bool = Field(
        default=False, description="Whether the active server has passed health checks."
    )
    models_dir: Path = Field(
        description="Directory used to locate local GGUF model files."
    )
