"""Shared type definitions for the local LLM runtime."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class InferenceOptions(BaseModel):
    """Reusable sampling and response-shaping options for local inference."""

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

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, description="Friendly model identifier or alias.")
    filename: str | None = Field(
        default=None, description="Expected GGUF filename for registry-backed models."
    )
    repo_id: str | None = Field(
        default=None,
        description="Optional source repository identifier (Hugging Face Repo Link) for manual downloads.",
    )
    context_window: int = Field(
        gt=0, description="Recommended runtime context window for the model."
    )
    path: Path | None = Field(
        default=None, description="Resolved GGUF path when a concrete file is known."
    )


class RuntimeStatus(BaseModel):
    """Runtime process status exposed to future client layers."""

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
