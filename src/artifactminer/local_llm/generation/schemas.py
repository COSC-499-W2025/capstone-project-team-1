"""Internal schemas for the minimal local-generation pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectFacts(BaseModel):
    """Grounded per-project facts produced by stage 1."""

    model_config = ConfigDict(extra="ignore")

    project_name: str = Field(min_length=1)
    project_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    contribution_focus: str = Field(default="")
    primary_language: str | None = Field(default=None)
    frameworks: list[str] = Field(default_factory=list)
    contribution_pct: float | None = Field(default=None)
    commit_breakdown: dict[str, int] = Field(default_factory=dict)
    first_commit: str | None = Field(default=None)
    last_commit: str | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _repair_common_llm_shape_errors(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        payload = dict(value)

        def _coerce_list(field_name: str) -> None:
            raw_value = payload.get(field_name)
            if isinstance(raw_value, str):
                lines = [
                    line.strip().lstrip("-* ").strip()
                    for line in raw_value.splitlines()
                    if line.strip()
                ]
                if not lines and raw_value.strip():
                    lines = [part.strip() for part in raw_value.split(",") if part.strip()]
                payload[field_name] = lines

        for alias in ("Summary", "project_summary", "description", "overview"):
            if alias in payload and not payload.get("summary"):
                payload["summary"] = payload[alias]
                break

        for field_name in ("technologies", "highlights", "evidence", "frameworks"):
            _coerce_list(field_name)

        summary = payload.get("summary")
        if isinstance(summary, str):
            payload["summary"] = summary.strip()

        if not payload.get("summary"):
            highlights = payload.get("highlights")
            evidence = payload.get("evidence")
            if isinstance(highlights, list) and highlights:
                payload["summary"] = str(highlights[0]).strip()
            elif isinstance(evidence, list) and evidence:
                payload["summary"] = str(evidence[0]).strip()
            elif payload.get("project_type"):
                payload["summary"] = (
                    f"{str(payload['project_name']).strip() or 'This project'} "
                    f"is a {str(payload['project_type']).strip()}."
                )

        return payload


class ResumeProjectPeriod(BaseModel):
    model_config = ConfigDict(extra="ignore")

    first_commit: str | None = None
    last_commit: str | None = None


class ResumeProjectModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    type: str
    primary_language: str | None = None
    frameworks: list[str] = Field(default_factory=list)
    contribution_pct: float | None = None
    commit_breakdown: dict[str, int] = Field(default_factory=dict)
    period: ResumeProjectPeriod = Field(default_factory=ResumeProjectPeriod)
    description: str | None = None
    bullets: list[str] = Field(default_factory=list)
    bullet_fact_ids: list[list[str]] = Field(default_factory=list)
    narrative: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _repair_common_llm_shape_errors(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        payload = dict(value)
        period = payload.get("period")
        if isinstance(period, ResumeProjectPeriod):
            period = period.model_dump()
        elif not isinstance(period, dict):
            period = {}
        else:
            period = dict(period)

        raw_breakdown = payload.get("commit_breakdown")
        cleaned_breakdown: dict[str, int] = {}
        if isinstance(raw_breakdown, dict):
            for key, raw_value in raw_breakdown.items():
                if key in {"first_commit", "last_commit"}:
                    if raw_value and key not in period:
                        period[key] = str(raw_value)
                    continue

                if isinstance(raw_value, bool):
                    cleaned_breakdown[key] = int(raw_value)
                    continue
                if isinstance(raw_value, int):
                    cleaned_breakdown[key] = raw_value
                    continue
                if isinstance(raw_value, float) and raw_value.is_integer():
                    cleaned_breakdown[key] = int(raw_value)
                    continue
                if isinstance(raw_value, str) and raw_value.strip().isdigit():
                    cleaned_breakdown[key] = int(raw_value.strip())

        for key in ("first_commit", "last_commit"):
            raw_value = payload.pop(key, None)
            if raw_value and key not in period:
                period[key] = str(raw_value)

        payload["commit_breakdown"] = cleaned_breakdown
        payload["period"] = period
        return payload


class ResumeMetadataModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_used: str | None = None
    models_used: list[str] = Field(default_factory=list)
    stage: str = ""
    generation_time_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
    quality_metrics: dict[str, Any] = Field(default_factory=dict)


class ResumePortfolioModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_projects: int = 0
    total_commits: int = 0
    languages_used: list[str] = Field(default_factory=list)
    frameworks_used: list[str] = Field(default_factory=list)
    project_types: dict[str, int] = Field(default_factory=dict)
    top_skills: list[str] = Field(default_factory=list)


class ResumeSkillsTimelineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skill: str
    first_seen: str | None = None
    last_seen: str | None = None
    projects_count: int = 0
    depth_score: float = 0.0


class ResumeActivityHeatmapDateRange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start: str | None = None
    end: str | None = None


class ResumeActivityHeatmapModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    daily_activity: dict[str, int] = Field(default_factory=dict)
    total_days_active: int = 0
    max_daily_commits: int = 0
    date_range: ResumeActivityHeatmapDateRange = Field(
        default_factory=ResumeActivityHeatmapDateRange
    )


class ResumeTopProjectModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_name: str
    project_type: str
    score: float = 0.0
    contribution_pct: float | None = None
    commit_total: int = 0
    first_commit: str | None = None
    last_commit: str | None = None
    recency_score: float = 0.0
    activity_focus: str | None = None
    latest_change: str | None = None
    evolution_note: str | None = None


class ResumePortfolioDashboardModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skills_timeline: list[ResumeSkillsTimelineItem] = Field(default_factory=list)
    activity_heatmap: ResumeActivityHeatmapModel = Field(
        default_factory=ResumeActivityHeatmapModel
    )
    top_projects: list[ResumeTopProjectModel] = Field(default_factory=list)


class ResumeOutputModel(BaseModel):
    """Draft/final output contract consumed by the OpenTUI frontend."""

    model_config = ConfigDict(extra="ignore")

    professional_summary: str = ""
    skills_section: str = ""
    developer_profile: str = ""
    projects: list[ResumeProjectModel] = Field(default_factory=list)
    metadata: ResumeMetadataModel = Field(default_factory=ResumeMetadataModel)
    portfolio: ResumePortfolioModel | None = None
    portfolio_dashboard: ResumePortfolioDashboardModel | None = None


class GenerationFeedback(BaseModel):
    """User feedback captured before the polish stage."""

    model_config = ConfigDict(extra="ignore")

    general_notes: str = ""
    tone: str = ""
    additions: list[str] = Field(default_factory=list)
    removals: list[str] = Field(default_factory=list)
