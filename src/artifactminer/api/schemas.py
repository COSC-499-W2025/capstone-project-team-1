"""Shared Pydantic models for Artifact Miner API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(BaseModel):
    """Response shape for service health and readiness checks."""

    status: Literal["ok", "degraded", "unhealthy"] = Field(
        default="ok", description="Overall service health indicator."
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the status was generated.",
    )


class QuestionResponse(BaseModel):
    """Response shape for question objects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    order: int


class ConsentResponse(BaseModel):
    """Response shape for consent state."""

    model_config = ConfigDict(from_attributes=True)

    consent_level: Literal["full", "no_llm", "none"]
    accepted_at: datetime | None = None


class ConsentUpdateRequest(BaseModel):
    """Request payload to update consent state."""

    consent_level: Literal["full", "no_llm", "none"] = Field(
        description="Consent level: 'full' (with LLM), 'no_llm' (without LLM), or 'none'."
    )
