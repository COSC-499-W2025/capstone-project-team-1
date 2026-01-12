"""Shared Pydantic models for Artifact Miner API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..helpers.time import utcnow

class HealthStatus(BaseModel):
    """Response shape for service health and readiness checks."""

    status: Literal["ok", "degraded", "unhealthy"] = Field(
        default="ok", description="Overall service health indicator."
    )
    timestamp: datetime = Field(
        default_factory=utcnow,
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

    consent_level: Literal["full", "no_llm", "none"]
    accepted_at: datetime | None = None


class ConsentUpdateRequest(BaseModel):
    """Request payload to update consent state."""

    consent_level: Literal["full", "no_llm", "none"] = Field(
        description="Consent level: 'full' (with LLM), 'no_llm' (without LLM), or 'none'."
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


class ZipUploadResponse(BaseModel):
    """Response shape for ZIP file upload."""

    zip_id: int = Field(description="Unique identifier for the uploaded ZIP file.")
    filename: str = Field(description="Original filename of the uploaded ZIP.")


class DirectoriesResponse(BaseModel):
    """Response shape for directory listing from ZIP file."""

    zip_id: int = Field(description="ID of the uploaded ZIP file.")
    filename: str = Field(description="Original filename of the ZIP.")
    directories: list[str] = Field(
        description="List of top-level directories in the ZIP file."
    )
    cleanedfilespath : list[str] = Field(
        description="Get the file path(s) from a zip direcotry."
    )


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


class FileValues(BaseModel):
    file_path : str
    file_name : str
    
class CrawlerFiles(BaseModel):
    """gets the according file and path data from the crawler"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    zip_id : int
    crawl_path_and_file_name : list[FileValues]


class RepresentationPreferences(BaseModel):
    """User preferences for portfolio representation."""

    showcase_project_ids: list[str] = Field(
        default_factory=list, description="Project IDs to showcase."
    )
    project_order: list[str] = Field(
        default_factory=list, description="Manual project ordering override."
    )
