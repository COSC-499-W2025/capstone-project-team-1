"""Shared Pydantic models for Artifact Miner API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, EmailStr, ValidationError


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


class UserAnswersRequest(BaseModel):
    """Request payload to submit user configuration answers."""

    email: EmailStr = Field(description="User's email address")
    artifacts_focus: str = Field(min_length=1, description="What artifacts to focus on")
    end_goal: str = Field(min_length=1, description="End goal of the analysis")
    repository_priority: str = Field(min_length=1, description="Repository analysis priority")
    file_patterns: str = Field(min_length=1, description="File patterns to include/exclude")


class UserAnswerResponse(BaseModel):
    """Response shape for user answer objects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_text: str
    answered_at: datetime
