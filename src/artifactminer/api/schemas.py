"""Shared Pydantic models for Artifact Miner API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Response shape for service health and readiness checks."""

    status: Literal["ok", "degraded", "unhealthy"] = Field(
        default="ok", description="Overall service health indicator."
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the status was generated.",
    )
