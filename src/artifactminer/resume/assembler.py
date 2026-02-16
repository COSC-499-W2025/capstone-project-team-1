"""
Resume assembler — stitches LLM responses + extracted data into final output.

Produces two formats:
  1. Markdown (human-readable resume)
  2. JSON (structured data for frontend consumption)
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .models import PortfolioDataBundle, ProjectDataBundle, ResumeOutput


# ---------------------------------------------------------------------------
# Markdown assembly
# ---------------------------------------------------------------------------


def assemble_markdown(output: ResumeOutput) -> str:
    """Render the final resume as markdown."""
    lines: list[str] = []
    portfolio = output.portfolio_data

    lines.append("# Technical Resume")
    lines.append("")

    # Professional Summary
    if output.professional_summary:
        lines.append("## Professional Summary")
        lines.append("")
        lines.append(output.professional_summary)
        lines.append("")

    # Technical Skills
    if output.skills_section:
        lines.append("## Technical Skills")
        lines.append("")
        lines.append(output.skills_section)
        lines.append("")

    # Projects
    lines.append("## Projects")
    lines.append("")

    if portfolio:
        for project in portfolio.projects:
            section = output.project_sections.get(project.project_name)
            lines.append(f"### {project.project_name}")

            # Metadata line
            meta_parts: list[str] = []
            if project.frameworks:
                meta_parts.append(f"**Technologies:** {', '.join(project.frameworks)}")
            if project.primary_language:
                meta_parts.append(f"**Language:** {project.primary_language}")
            if project.user_contribution_pct is not None:
                meta_parts.append(
                    f"**Contribution:** {project.user_contribution_pct:.0f}%"
                )
            if meta_parts:
                lines.append(" | ".join(meta_parts))

            if project.first_commit and project.last_commit:
                lines.append(
                    f"**Period:** {project.first_commit[:10]} to {project.last_commit[:10]}"
                )
            lines.append("")

            if section:
                # Description
                if section.description:
                    lines.append(section.description)
                    lines.append("")

                # Bullets
                for bullet in section.bullets:
                    lines.append(f"- {bullet}")
                if section.bullets:
                    lines.append("")

                # Narrative
                if section.narrative:
                    lines.append(f"> {section.narrative}")
                    lines.append("")
            else:
                lines.append(f"*Contributed to {project.project_name}.*")
                lines.append("")

    # Developer Profile
    if output.developer_profile:
        lines.append("## Developer Profile")
        lines.append("")
        lines.append(output.developer_profile)
        lines.append("")

    # Footer
    lines.append("---")
    time_str = f"{output.generation_time_seconds:.0f}s"
    if output.models_used:
        model_str = ", ".join(output.models_used)
        lines.append(
            f"*Generated with multi-stage pipeline ({model_str}) in {time_str}*"
        )
    else:
        model_str = output.model_used or "template"
        lines.append(f"*Generated with {model_str} in {time_str}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON assembly
# ---------------------------------------------------------------------------


def assemble_json(output: ResumeOutput) -> str:
    """Render the final resume as a JSON string."""
    data: Dict[str, Any] = {
        "professional_summary": output.professional_summary,
        "skills_section": output.skills_section,
        "developer_profile": output.developer_profile,
        "projects": [],
        "metadata": {
            "model_used": output.model_used,
            "models_used": output.models_used,
            "stage": output.stage,
            "generation_time_seconds": output.generation_time_seconds,
            "errors": output.errors,
            "quality_metrics": output.quality_metrics,
        },
    }

    portfolio = output.portfolio_data
    if portfolio:
        data["portfolio"] = {
            "total_projects": portfolio.total_projects,
            "total_commits": portfolio.total_commits,
            "languages_used": portfolio.languages_used,
            "frameworks_used": portfolio.frameworks_used,
            "project_types": portfolio.project_types,
            "top_skills": portfolio.top_skills,
        }

        for project in portfolio.projects:
            section = output.project_sections.get(project.project_name)
            proj_data: Dict[str, Any] = {
                "name": project.project_name,
                "type": project.project_type,
                "primary_language": project.primary_language,
                "frameworks": project.frameworks,
                "contribution_pct": project.user_contribution_pct,
                "commit_breakdown": project.commit_count_by_type(),
                "period": {
                    "first_commit": project.first_commit,
                    "last_commit": project.last_commit,
                },
            }
            if section:
                proj_data["description"] = section.description
                proj_data["bullets"] = section.bullets
                proj_data["bullet_fact_ids"] = section.bullet_fact_ids
                proj_data["narrative"] = section.narrative

            data["projects"].append(proj_data)

    return json.dumps(data, indent=2, default=str)
