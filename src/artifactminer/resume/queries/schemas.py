"""Structured JSON schemas for the multi-stage resume pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Stage1Fact(BaseModel):
    """Single extracted fact with evidence links."""

    fact_id: str = Field(description="Stable fact id like F1, F2, ...")
    fact: str = Field(description="Short factual technical achievement")
    evidence_keys: list[str] = Field(
        default_factory=list,
        description="Evidence keys from the provided evidence catalog",
    )

    @field_validator("fact_id", mode="before")
    @classmethod
    def _strip_fact_id(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("fact", mode="before")
    @classmethod
    def _strip_fact(cls, value: str) -> str:
        return str(value or "").strip()


class Stage1ExtractionResponse(BaseModel):
    """Stage 1 structured response."""

    project_summary: str = ""
    facts: list[Stage1Fact] = Field(default_factory=list)
    role: str = ""

    @field_validator("project_summary", "role", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return str(value or "").strip()


class SkillsSectionResponse(BaseModel):
    """Structured skills layout used by draft/polish stages."""

    languages: list[str] = Field(default_factory=list)
    frameworks_libraries: list[str] = Field(default_factory=list)
    tools_infrastructure: list[str] = Field(default_factory=list)
    practices: list[str] = Field(default_factory=list)


class StageBullet(BaseModel):
    """Project bullet tied to Stage 1 facts."""

    text: str = ""
    fact_ids: list[str] = Field(default_factory=list)

    @field_validator("text", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return str(value or "").strip()


class StageProjectSection(BaseModel):
    """Project section in draft/polish output."""

    project_name: str = ""
    description: str = ""
    bullets: list[StageBullet] = Field(default_factory=list)
    narrative: str = ""

    @field_validator("project_name", "description", "narrative", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return str(value or "").strip()


class StageDraftResponse(BaseModel):
    """Stage 2/3 structured resume output."""

    professional_summary: str = ""
    skills: SkillsSectionResponse = Field(default_factory=SkillsSectionResponse)
    projects: list[StageProjectSection] = Field(default_factory=list)
    developer_profile: str = ""

    @field_validator("professional_summary", "developer_profile", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return str(value or "").strip()
