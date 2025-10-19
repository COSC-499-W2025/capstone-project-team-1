"""Pydantic models for the ingest MVP API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class IngestCreateResponse(BaseModel):
    """Response returned after a zip upload is accepted."""

    ingest_id: str = Field(..., description="Unique identifier for the ingest session.")
    status: Literal["validating_zip"] = Field(
        ..., description="Initial phase after accepting the upload."
    )


class Progress(BaseModel):
    """Represents the current lifecycle status of an ingest session."""

    ingest_id: str = Field(..., description="Identifier of the ingest session.")
    phase: Literal[
        "validating_zip",
        "scanning",
        "listing_candidates",
        "waiting_for_selection",
        "error",
    ] = Field(..., description="Current processing phase.")
    percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Best-effort completion percentage for the current ingest session.",
    )
    message: Optional[str] = Field(
        default=None, description="Optional human readable status message."
    )


class CandidateDir(BaseModel):
    """Represents a top-level directory discovered in the uploaded archive."""

    path: str = Field(..., description="The candidate directory path relative to zip root.")
    approx_files: int = Field(
        ..., ge=0, description="Approximate number of files contained within the directory."
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Heuristic tags that describe the predominant file types.",
    )


class CandidatesResponse(BaseModel):
    """Returned when the candidate listing is ready."""

    ingest_id: str = Field(..., description="Identifier of the ingest session.")
    candidates: list[CandidateDir] = Field(
        default_factory=list, description="Candidate directories discovered in the archive."
    )


class SelectionRequest(BaseModel):
    """Payload sent by the client when the user chooses candidate directories."""

    selected_paths: list[str] = Field(
        default_factory=list,
        description="Paths of the selected candidate directories.",
    )


class SelectionResponse(BaseModel):
    """Response returned after selections are persisted in memory."""

    ingest_id: str = Field(..., description="Identifier of the ingest session.")
    saved: bool = Field(..., description="Indicates the selection has been recorded.")
    selected_paths: list[str] = Field(
        default_factory=list, description="Echo of the stored selection."
    )

