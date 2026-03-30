"""Parse free-form markdown resume text into ResumeOutputModel."""

from __future__ import annotations

import re

from .schemas import (
    ProjectFacts,
    ResumeOutputModel,
    ResumeProjectModel,
    ResumeProjectPeriod,
)


def _strip_fences(text: str) -> str:
    """Remove optional code fences that small LLMs sometimes add."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    return text.strip()


_HEADING2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_HEADING3 = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown into {header_lower: body} by ## headings."""
    sections: dict[str, str] = {}
    matches = list(_HEADING2.finditer(text))
    for i, match in enumerate(matches):
        header = match.group(1).strip().lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[header] = text[start:end].strip()
    return sections


def _parse_projects_section(
    body: str,
    facts_by_name: dict[str, ProjectFacts],
) -> list[ResumeProjectModel]:
    """Parse ### sub-headings into ResumeProjectModel list."""
    projects: list[ResumeProjectModel] = []
    matches = list(_HEADING3.finditer(body))
    if not matches:
        return projects

    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        block = body[start:end].strip()

        bullets: list[str] = []
        description_lines: list[str] = []
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                bullets.append(stripped[2:].strip())
            elif stripped:
                description_lines.append(stripped)

        description = " ".join(description_lines) if description_lines else None

        # Fill metadata from facts if available
        fact = facts_by_name.get(name)
        projects.append(
            ResumeProjectModel(
                name=name,
                type=fact.project_type if fact else "project",
                primary_language=fact.primary_language if fact else None,
                frameworks=list(fact.frameworks) if fact else [],
                contribution_pct=fact.contribution_pct if fact else None,
                commit_breakdown=dict(fact.commit_breakdown) if fact else {},
                period=ResumeProjectPeriod(
                    first_commit=fact.first_commit if fact else None,
                    last_commit=fact.last_commit if fact else None,
                ),
                description=description,
                bullets=bullets,
                bullet_fact_ids=[],
                narrative=None,
            )
        )

    return projects


def parse_resume_markdown(
    markdown: str,
    facts: list[ProjectFacts],
) -> ResumeOutputModel:
    """Convert LLM markdown output + facts into a ResumeOutputModel.

    Expects markdown with ## headings: Professional Summary, Technical Skills,
    Developer Profile, Projects (with ### sub-headings per project).
    """
    text = _strip_fences(markdown)
    sections = _split_sections(text)

    professional_summary = sections.get("professional summary", "")
    skills_section = sections.get("technical skills", "")
    developer_profile = sections.get("developer profile", "")

    facts_by_name = {fact.project_name: fact for fact in facts}
    projects_body = sections.get("projects", "")
    projects = _parse_projects_section(projects_body, facts_by_name)

    return ResumeOutputModel(
        professional_summary=professional_summary,
        skills_section=skills_section,
        developer_profile=developer_profile,
        projects=projects,
    )
