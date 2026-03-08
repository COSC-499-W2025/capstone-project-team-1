"""Transport-layer schemas for local LLM generation workflow.

This module defines the request/response contracts (schemas) for the /local-llm/* route in experimental llama branch.

If your at curious about the schema migrations this file has from the llama branch, here they are: 


experimental llama schemas -> this file schema

PipelineIntakeCreateRequest → migrated as IntakeCreateRequest
PipelineIntakeCreateResponse → migrated as IntakeCreateResponse
PipelineRepoCandidate → migrated as RepositoryCandidate
PipelineContributorsRequest → migrated as ContributorDiscoveryRequest
PipelineContributorIdentity → migrated as ContributorIdentity
PipelineContributorsResponse → migrated as ContributorDiscoveryResponse
PipelineStartRequest → migrated as GenerationStartRequest
PipelineStartResponse → migrated as GenerationStartResponse
PipelineTelemetry → migrated as GenerationTelemetry
PipelineStatusResponse → migrated as GenerationStatusResponse
PipelinePolishRequest → migrated as PolishRequest
PipelinePolishResponse → migrated as PolishResponse
PipelineCancelResponse → migrated as CancellationResponse


"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Job and stage status types
# ---------------------------------------------------------------------------

PipelineJobStatus = Literal[
    "queued",
    "running",
    "draft_ready",
    "polishing",
    "complete",
    "error",
    "cancelled",
    "failed_resource_guard",
]
"""Status of an in-flight generation job.

- queued: Job created, waiting for processing
- running: Actively analyzing and extracting data
- draft_ready: Initial generation complete, awaiting user feedback
- polishing: Refining draft based on user input
- complete: All stages finished, final output ready
- error: Job terminated due to processing error
- cancelled: User/admin cancelled the job
- failed_resource_guard: Job killed due to resource limits
"""

PipelineStage = Literal["ANALYZE", "FACTS", "DRAFT", "POLISH"]
"""Logical processing stage within a generation job.

- ANALYZE: Initial repository discovery and analysis
- FACTS: Extraction and distillation of technical facts
- DRAFT: Initial resume generation
- POLISH: Refinement and customization of output
"""


# ---------------------------------------------------------------------------
# Intake creation
# ---------------------------------------------------------------------------


class IntakeCreateRequest(BaseModel):
    """Request to create an intake from an uploaded ZIP file.

    An intake represents an ephemeral workspace for repository discovery and
    candidate selection before starting generation.
    """

    zip_path: str = Field(min_length=1, description="Filesystem path to uploaded ZIP")


class RepositoryCandidate(BaseModel):
    """A discovered repository available for selection.

    Discovered during intake creation by scanning the ZIP contents.
    """

    id: str = Field(description="Repository identifier within intake")
    name: str = Field(description="Repository name (typically directory name)")
    rel_path: str = Field(description="Relative path within ZIP root")


class IntakeCreateResponse(BaseModel):
    """Response confirming intake creation and discovered repositories."""

    intake_id: str = Field(description="Unique intake identifier")
    zip_path: str = Field(description="Filesystem path to intake ZIP")
    repos: list[RepositoryCandidate] = Field(
        description="All repositories discovered in ZIP"
    )


# ---------------------------------------------------------------------------
# Contributor discovery
# ---------------------------------------------------------------------------


class ContributorDiscoveryRequest(BaseModel):
    """Request to discover contributors across selected repositories.

    Scans git history of selected repos to identify contributors and their
    commit patterns for later matching with user identity.
    """

    repo_ids: list[str] = Field(
        min_length=1, description="Repository IDs to scan for contributors"
    )


class ContributorIdentity(BaseModel):
    """A contributor identity extracted from git history.

    Represents a unique email/name pair appearing in commit history with
    aggregated statistics about contributions.
    """

    email: str = Field(description="Email address from commits")
    name: Optional[str] = Field(default=None, description="Name from commits")
    repo_count: int = Field(description="Number of repos this identity appears in")
    commit_count: int = Field(description="Total commits by this identity")
    candidate_username: str = Field(
        description="Extracted or suggested username identifier"
    )


class ContributorDiscoveryResponse(BaseModel):
    """Response listing discovered contributors."""

    contributors: list[ContributorIdentity] = Field(
        description="All unique contributor identities found"
    )


# ---------------------------------------------------------------------------
# Generation startup
# ---------------------------------------------------------------------------


class GenerationStartRequest(BaseModel):
    """Request to begin the generation pipeline.

    Launches the multi-stage generation process with specified repositories,
    user identity, and optional model selections.
    """

    intake_id: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Intake ID to use (optional; creates new if not provided)",
    )
    repo_ids: list[str] = Field(
        min_length=1, description="Selected repository IDs for processing"
    )
    user_email: str = Field(
        min_length=3, description="User email for attribution and identification"
    )
    stage1_model: str = Field(
        default="qwen2.5-coder-3b-q4",
        min_length=1,
        description="Model for analysis stage",
    )
    stage2_model: str = Field(
        default="lfm2.5-1.2b-bf16",
        min_length=1,
        description="Model for facts extraction stage",
    )
    stage3_model: str = Field(
        default="lfm2.5-1.2b-bf16",
        min_length=1,
        description="Model for polish/refinement stage",
    )


class GenerationStartResponse(BaseModel):
    """Response confirming generation job creation."""

    job_id: str = Field(description="Unique job identifier for polling/control")
    status: PipelineJobStatus = Field(description="Initial job status")


# ---------------------------------------------------------------------------
# Generation status and telemetry
# ---------------------------------------------------------------------------


class GenerationTelemetry(BaseModel):
    """Progress and performance metrics for an in-flight job.

    Updated continuously during processing to provide real-time feedback
    about processing speed, completion rate, and resource usage.
    """

    model_config = ConfigDict(use_attribute_docstrings=True)

    stage: PipelineStage = Field(default="ANALYZE", description="Current stage")
    active_model: Optional[str] = Field(
        default=None, description="Currently loaded model name"
    )
    repos_total: int = Field(
        default=0, description="Total repositories to process"
    )
    repos_done: int = Field(default=0, description="Repositories completed")
    current_repo: Optional[str] = Field(
        default=None, description="Repository currently being processed"
    )
    facts_total: int = Field(default=0, description="Total facts extracted")
    draft_projects: int = Field(
        default=0, description="Projects added to draft output"
    )
    polished_projects: int = Field(
        default=0, description="Projects finalized in output"
    )
    elapsed_seconds: float = Field(
        default=0.0, description="Total elapsed time in seconds"
    )
    model_check_seconds: float = Field(
        default=0.0, description="Time spent loading/checking model availability"
    )
    selected_repos: list[str] = Field(
        default_factory=list, description="Repos being processed"
    )


class GenerationStatusResponse(BaseModel):
    """Response providing current state of a generation job."""

    status: PipelineJobStatus = Field(description="Current job status")
    stage: PipelineStage = Field(description="Current processing stage")
    messages: list[str] = Field(
        default_factory=list, description="Status messages and logs"
    )
    telemetry: GenerationTelemetry = Field(description="Progress metrics")
    draft: Optional[dict[str, Any]] = Field(
        default=None,
        description="Intermediate draft resume (if available for feedback)",
    )
    output: Optional[dict[str, Any]] = Field(
        default=None, description="Final polished output (when complete)"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if job failed"
    )


# ---------------------------------------------------------------------------
# Polish/refinement
# ---------------------------------------------------------------------------


class PolishRequest(BaseModel):
    """Request to refine the draft output with user feedback.

    Used to trigger Stage 3 (polish) after user reviews and provides
    guidance on tone, additions, or removals from the draft.
    """

    general_notes: str = Field(
        default="", description="Free-form user feedback and guidance"
    )
    tone: str = Field(
        default="", description="Requested tone (e.g., 'professional', 'casual')"
    )
    additions: list[str] = Field(
        default_factory=list, description="Content to add to resume"
    )
    removals: list[str] = Field(
        default_factory=list, description="Content or sections to remove"
    )


class PolishResponse(BaseModel):
    """Response confirming polish operation initiated."""

    ok: bool = Field(description="Success indicator")
    status: PipelineJobStatus = Field(description="Updated job status")


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


class CancellationResponse(BaseModel):
    """Response confirming job cancellation."""

    ok: bool = Field(description="Success indicator")
    status: PipelineJobStatus = Field(description="Final job status after cancel")
