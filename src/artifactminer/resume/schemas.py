from __future__ import annotations

from pydantic import BaseModel, Field


class RankedFile(BaseModel):
    file_path: str = Field(..., description="Path to the file")
    importance: int = Field(..., description="1=most important, higher=less important")
    reason: str = Field(..., description="Why this file matters for a resume")


class FileRanking(BaseModel):
    ranked_files: list[RankedFile] = Field(..., description="Files ranked by resume importance")


class FileAnalysis(BaseModel):
    file_path: str = Field(..., description="Path to the analyzed file")
    what_was_built: str = Field(..., description="1-2 sentence description of what this code does")
    technical_decisions: list[str] = Field(
        ..., description="Notable technical choices (e.g., 'Used caching with TTL')"
    )
    skills_demonstrated: list[str] = Field(
        ..., description="Technical skills shown (e.g., 'REST API Design')"
    )


class ProjectSummary(BaseModel):
    project_name: str = Field(..., description="Name of the project")
    one_liner: str = Field(..., description="Single sentence project description for resume header")
    bullet_points: list[str] = Field(
        ..., description="3-5 resume bullet points starting with action verbs"
    )
    technologies: list[str] = Field(..., description="Deduplicated list of technologies used")
    impact_metrics: list[str] = Field(
        default_factory=list,
        description="Quantifiable achievements (e.g., '8 API endpoints')",
    )


class ResumeArtifacts(BaseModel):
    projects: list[ProjectSummary]
    portfolio_summary: str = Field(..., description="Free-form markdown portfolio summary")
    model_used: str = Field(..., description="Which Ollama model was used")
    generation_time_seconds: float = Field(..., description="Total pipeline duration")
