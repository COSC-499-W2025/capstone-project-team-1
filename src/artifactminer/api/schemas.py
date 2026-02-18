"""Shared Pydantic models for Artifact Miner API contracts."""

from __future__ import annotations

import datetime as _dt
from datetime import datetime, UTC
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Evidence types
# ---------------------------------------------------------------------------

EvidenceType = Literal["metric", "feedback", "evaluation", "award", "custom"]


class EvidenceCreateRequest(BaseModel):
    """Request payload for creating project evidence."""

    type: EvidenceType
    content: str = Field(min_length=1)
    source: Optional[str] = None
    date: Optional[_dt.date] = None


class EvidenceResponse(BaseModel):
    """Response shape for a single evidence item."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: EvidenceType
    content: str
    source: Optional[str] = None
    date: Optional[_dt.date] = None
    project_id: int


class EvidenceDeleteResponse(BaseModel):
    """Response shape for evidence deletion."""

    success: bool
    deleted_id: int


class HealthStatus(BaseModel):
    """Response shape for service health and readiness checks."""

    status: Literal["ok", "degraded", "unhealthy"] = Field(
        default="ok", description="Overall service health indicator."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="UTC timestamp when the status was generated.",
    )


class QuestionResponse(BaseModel):
    """Response shape for question objects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str | None = None
    question_text: str
    order: int
    required: bool = True
    answer_type: str = "text"


class ConsentResponse(BaseModel):
    """Response shape for consent state."""

    model_config = ConfigDict(from_attributes=True)

    consent_level: Literal["none", "local", "local-llm", "cloud"]
    accepted_at: datetime | None = None


class ConsentUpdateRequest(BaseModel):
    """Request payload to update consent state."""

    consent_level: Literal["none", "local", "local-llm", "cloud"] = Field(
        description="Consent level: 'local' (static only), 'local-llm' (local LLM), 'cloud' (cloud LLM), or 'none'."
    )


class KeyedAnswersRequest(BaseModel):
    """New request payload keyed by question `key`.

    Example:
        {"answers": {"email": "me@example.com", "end_goal": "..."}}
    """

    answers: dict[str, str] = Field(default_factory=dict)


class UserAnswerResponse(BaseModel):
    """Response shape for user answer objects."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_text: str
    answered_at: datetime


class UserAnswerCreate(BaseModel):
    """Response shape for email api request and response"""

    email: str


class ZipUploadResponse(BaseModel):
    """Response shape for ZIP file upload."""

    zip_id: int = Field(description="Unique identifier for the uploaded ZIP file.")
    filename: str = Field(description="Original filename of the uploaded ZIP.")
    portfolio_id: str = Field(
        description="UUID linking this ZIP to a portfolio session."
    )


class PortfolioZipItem(BaseModel):
    """Single ZIP item within a portfolio."""

    model_config = ConfigDict(from_attributes=True)

    zip_id: int = Field(description="Unique identifier for the uploaded ZIP file.")
    filename: str = Field(description="Original filename of the uploaded ZIP.")
    uploaded_at: datetime = Field(description="Timestamp when the ZIP was uploaded.")


class PortfolioResponse(BaseModel):
    """Response shape for portfolio ZIP listing."""

    portfolio_id: str = Field(description="UUID of the portfolio.")
    zips: list[PortfolioZipItem] = Field(
        description="All ZIPs linked to this portfolio."
    )


class DirectoriesResponse(BaseModel):
    """Response shape for directory listing from ZIP file."""

    zip_id: int = Field(description="ID of the uploaded ZIP file.")
    filename: str = Field(description="Original filename of the ZIP.")
    directories: list[str] = Field(
        description="List of top-level directories in the ZIP file."
    )
    cleanedfilespath: list[str] = Field(
        description="Get the file path(s) from a zip direcotry."
    )


class ProjectResponse(BaseModel):
    """Response shape for project listing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_name: str
    project_path: str
    languages: list | None = None
    frameworks: list | None = None
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    is_collaborative: bool
    thumbnail_url: str | None = None


class ProjectSkillItem(BaseModel):
    """Skill item for project detail response."""

    model_config = ConfigDict(from_attributes=True)

    skill_name: str
    category: str | None = None
    proficiency: float | None = None


class ProjectResumeItem(BaseModel):
    """Resume item for project detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    category: str | None = None


class ProjectDetailResponse(BaseModel):
    """Response shape for single project with related data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_name: str
    project_path: str
    languages: list | None = None
    frameworks: list | None = None
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    is_collaborative: bool
    total_commits: int | None = None
    primary_language: str | None = None
    ranking_score: float | None = None
    health_score: float | None = None
    role: str | None = None
    thumbnail_url: str | None = None
    skills: list[ProjectSkillItem] = []
    resume_items: list[ProjectResumeItem] = []
    evidence: list[EvidenceResponse] = []


class ProjectThumbnailResponse(BaseModel):
    """Response after creating/updating a project's thumbnail."""

    project_id: int
    project_name: str
    thumbnail_url: str


class ProjectRoleUpdateRequest(BaseModel):
    """Payload for setting a user's role on a project."""

    role: str = Field(
        min_length=1,
        max_length=120,
        description="Role of the user in this project (e.g., Lead Developer).",
    )


class ProjectRoleResponse(BaseModel):
    """Response after creating/updating a project role."""

    project_id: int
    project_name: str
    role: str


class ProjectTimelineItem(BaseModel):
    """Aggregated activity window for a project repository."""

    id: int = Field(description="Unique identifier for the project.")
    project_name: str = Field(description="Display name of the project.")
    first_commit: datetime = Field(description="Timestamp of the first commit seen.")
    last_commit: datetime = Field(
        description="Timestamp of the most recent commit seen."
    )
    duration_days: int = Field(
        description="Number of days between first and last commit."
    )
    was_active: bool = Field(
        description="Whether the project was active in the last 6 months."
    )


class OpenAIRequest(BaseModel):
    """Request payload for OpenAI API calls."""

    prompt: str = Field(..., description="The prompt to send to the OpenAI model.")


class OpenAIResponse(BaseModel):
    """Response shape for OpenAI API calls."""

    response: str = Field(..., description="The model's response text.")


class SkillChronologyItem(BaseModel):
    """Chronological skill entry showing when a skill was first demonstrated."""

    model_config = ConfigDict(from_attributes=True)

    date: datetime | None = Field(
        description="Date skill was first used (from project's first commit)."
    )
    skill: str = Field(description="Name of the skill.")
    project: str = Field(description="Project where skill was demonstrated.")
    proficiency: float | None = Field(
        default=None, description="Proficiency level 0.0-1.0."
    )
    category: str | None = Field(
        default=None, description="Skill category (e.g., 'Programming Languages')."
    )


class SkillResponse(BaseModel):
    """Response shape for skill listing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None = None
    project_count: int | None = Field(
        default=None, description="Number of projects using this skill."
    )


class ResumeItemResponse(BaseModel):
    """Response shape for resume/portfolio items."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    category: str | None = None
    project_name: str | None = Field(
        default=None, description="Associated project name."
    )
    role: str | None = Field(
        default=None, description="User role in the associated project."
    )
    created_at: datetime


class SummaryResponse(BaseModel):
    """Response shape for AI-generated user contribution summaries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_path: str
    user_email: str
    summary_text: str
    generated_at: datetime


class DeleteResponse(BaseModel):
    """Response shape for delete operations."""

    success: bool = Field(description="Whether the delete operation succeeded.")
    message: str = Field(description="Human-readable result message.")
    deleted_id: int = Field(description="ID of the deleted resource.")


class ResumeGenerationRequest(BaseModel):
    """Request payload for resume generation."""

    project_ids: list[int] = Field(
        description="List of project IDs (repo_stat IDs) to generate resume items for.",
        min_length=1,
    )
    regenerate: bool = Field(
        default=False,
        description=(
            "If True, delete existing generated ProjectEvidence rows (and any legacy ResumeItem rows) "
            "for these projects before regenerating."
        ),
    )


class ResumeGenerationResponse(BaseModel):
    """Response from resume generation endpoint.

    ## Success Semantics

    The `success` field indicates whether generation completed without critical errors.
    Insights are persisted as `ProjectEvidence` rows, not `ResumeItem` rows.

    - `success=True`: All projects were processed without errors
    - `success=False`: One or more projects encountered errors during processing
    - `warnings`: Non-critical issues (for example git metadata collection failures)
    - `items_generated`: Count of evidence items created (not resume items)
    - `resume_items`: Always empty list (insights stored as ProjectEvidence)
    """

    success: bool = Field(
        description="True if generation completed without critical errors."
    )
    items_generated: int = Field(
        description="Total number of evidence items created (not resume items)."
    )
    resume_items: list[ResumeItemResponse] = Field(
        default_factory=list,
        description="Always empty. Insights are stored as ProjectEvidence, not ResumeItem rows.",
    )
    consent_level: str = Field(
        description="Consent level used for generation ('full', 'no_llm', or 'none')."
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of errors encountered during generation (if any).",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of non-critical warnings encountered during generation.",
    )


class ProjectRankingItem(BaseModel):
    """Ranked project based on user contribution."""

    name: str = Field(description="Project directory name.")
    score: float = Field(description="User's contribution percentage (0-100).")
    total_commits: int = Field(description="Total commits in the project.")
    user_commits: int = Field(description="Commits by the user.")


class RepoAnalysisResult(BaseModel):
    """Result of analyzing a single repository."""

    project_name: str
    project_path: str
    frameworks: list[str] | None = Field(
        default=None, description="Frameworks detected in the repository."
    )
    languages: list[str] | None = Field(
        default=None, description="Languages detected in the repository."
    )
    skills_count: int = 0
    insights_count: int = 0
    user_contribution_pct: float | None = None
    user_total_commits: int | None = Field(
        default=None, description="Number of commits authored by the user."
    )
    user_commit_frequency: float | None = Field(
        default=None, description="Average commits per week by the user."
    )
    user_first_commit: datetime | None = Field(
        default=None, description="Timestamp of the user's first commit in the repo."
    )
    user_last_commit: datetime | None = Field(
        default=None, description="Timestamp of the user's last commit in the repo."
    )
    error: str | None = None


class RankingResult(BaseModel):
    """Project ranking information."""

    name: str
    score: float = Field(description="User contribution percentage (0-100)")
    total_commits: int
    user_commits: int


class SummaryResult(BaseModel):
    """Generated summary for a project."""

    project_name: str
    summary: str


class AnalyzeRequest(BaseModel):
    """Optional request payload for scoped analysis."""

    directories: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of directories to scope analysis. "
            "Paths are relative to the extracted ZIP root."
        ),
    )


class AnalyzeResponse(BaseModel):
    """Response from the master analyze endpoint."""

    zip_id: int
    extraction_path: str
    repos_found: int
    repos_analyzed: list[RepoAnalysisResult]
    rankings: list[RankingResult]
    summaries: list[SummaryResult]
    consent_level: str
    user_email: str


class SummaryListResponse(BaseModel):
    summaries: list[SummaryResult]


class FileValues(BaseModel):
    file_path: str
    file_name: str
    file_ext: str


class CrawlerFiles(BaseModel):
    """gets the according file and path data from the crawler"""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    zip_id: int
    crawl_path_and_file_name_and_ext: list[FileValues]


class RepresentationPreferences(BaseModel):
    """User preferences for portfolio representation."""

    showcase_project_ids: list[str] = Field(
        default_factory=list, description="Project IDs to showcase."
    )
    project_order: list[str] = Field(
        default_factory=list, description="Manual project ordering override."
    )


class PortfolioGenerationRequest(BaseModel):
    """Request payload for on-demand portfolio assembly."""

    portfolio_id: str = Field(
        min_length=1,
        description="Portfolio UUID returned by ZIP uploads.",
    )


class PortfolioProjectItem(BaseModel):
    """Project entry included in portfolio generation output."""

    id: int
    project_name: str
    project_path: str
    languages: list | None = None
    frameworks: list | None = None
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    ranking_score: float | None = None
    health_score: float | None = None


class PortfolioGenerationResponse(BaseModel):
    """Composed portfolio payload for export or UI rendering."""

    success: bool = Field(description="True when at least one project is included.")
    portfolio_id: str
    consent_level: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    preferences: RepresentationPreferences
    projects: list[PortfolioProjectItem]
    resume_items: list[ResumeItemResponse]
    summaries: list[SummaryResponse]
    skills_chronology: list[SkillChronologyItem]
    errors: list[str] = Field(default_factory=list)


class UserAIIntelligenceSummaryResponse(BaseModel):
    repo_path: str
    user_email: str
    summary_text: str