"""Export helpers for resume data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def export_to_json(
    resume_items: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    directory: Path | None = None,
    project_analyses: list[dict[str, Any]] | None = None,
) -> Path:
    """Export resume data to JSON file.
    
    Args:
        resume_items: List of resume items
        summaries: List of project summaries
        directory: Output directory (defaults to current directory)
        project_analyses: List of detailed project analysis data
    
    Returns the path to the created file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_export_{timestamp}.json"
    path = (directory or Path.cwd()) / filename

    export_data = {
        "exported_at": datetime.now().isoformat(),
        "resume_items": resume_items,
        "summaries": summaries,
    }
    
    # Include detailed project analysis if provided
    if project_analyses:
        export_data["project_analyses"] = project_analyses

    with path.open("w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)

    return path


def group_by_project(resume_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group resume items by project name."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in resume_items:
        project = item.get("project_name") or "Uncategorized"
        if project not in grouped:
            grouped[project] = []
        grouped[project].append(item)
    return grouped


def build_summaries_lookup(summaries: list[dict[str, Any]]) -> dict[str, str]:
    """Build a lookup dict from project name to summary text."""
    lookup: dict[str, str] = {}
    for summary in summaries:
        repo_path = summary.get("repo_path", "")
        project_name = Path(repo_path).name if repo_path else ""
        if project_name:
            lookup[project_name] = summary.get("summary_text", "")
    return lookup


def export_to_text(
    resume_items: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    directory: Path | None = None,
    project_analyses: list[dict[str, Any]] | None = None,
) -> Path:
    """Export resume data to plain text file.
    
    Args:
        resume_items: List of resume items
        summaries: List of project summaries
        directory: Output directory (defaults to current directory)
        project_analyses: List of detailed project analysis data
    
    Returns the path to the created file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_export_{timestamp}.txt"
    path = (directory or Path.cwd()) / filename

    lines: list[str] = [
        "=" * 80,
        "PORTFOLIO ANALYSIS EXPORT",
        f"Generated: {datetime.now().isoformat()}",
        "=" * 80,
        "",
    ]
    
    # Add detailed project analysis section if provided
    if project_analyses:
        lines.extend([
            "\n" + "=" * 80,
            "PROJECT ANALYSIS DETAILS",
            "=" * 80,
            "",
        ])
        
        for idx, analysis in enumerate(project_analyses, 1):
            lines.extend([
                f"\n{'─' * 80}",
                f"[{idx}] {analysis.get('project_name', 'Unknown Project')}",
                f"{'─' * 80}",
                f"  Path: {analysis.get('project_path', 'N/A')}",
            ])
            
            if analysis.get('error'):
                lines.append(f"  ⚠ Error: {analysis['error']}")
                continue
            
            # Languages and Frameworks
            if analysis.get('languages'):
                langs = ', '.join(analysis['languages'])
                lines.append(f"  Languages: {langs}")
            if analysis.get('frameworks'):
                fws = ', '.join(analysis['frameworks'])
                lines.append(f"  Frameworks: {fws}")
            
            # Skills and Insights
            lines.append(f"  Skills extracted: {analysis.get('skills_count', 0)}")
            lines.append(f"  Insights generated: {analysis.get('insights_count', 0)}")
            
            # User Contribution Metrics
            if analysis.get('user_contribution_pct') is not None:
                lines.append(f"  User contribution: {analysis['user_contribution_pct']:.1f}%")
            if analysis.get('user_total_commits') is not None:
                lines.append(f"  User commits: {analysis['user_total_commits']}")
            if analysis.get('user_commit_frequency') is not None:
                lines.append(f"  Commit frequency: {analysis['user_commit_frequency']:.2f} commits/week")
            
            # Timeline
            if analysis.get('user_first_commit') and analysis.get('user_last_commit'):
                first = analysis['user_first_commit']
                last = analysis['user_last_commit']
                # Handle both datetime objects and strings
                if isinstance(first, str):
                    first_str = first.split('T')[0]
                else:
                    first_str = first.strftime("%Y-%m-%d")
                if isinstance(last, str):
                    last_str = last.split('T')[0]
                else:
                    last_str = last.strftime("%Y-%m-%d")
                lines.append(f"  Activity period: {first_str} → {last_str}")
            
            lines.append("")
    
    # Add resume items section
    lines.extend([
        "\n" + "=" * 80,
        "RESUME ITEMS & SUMMARIES",
        "=" * 80,
        "",
    ])

    grouped = group_by_project(resume_items)
    summaries_lookup = build_summaries_lookup(summaries)

    for project_name, items in grouped.items():
        lines.extend([
            f"\n{'─' * 40}",
            f"PROJECT: {project_name or 'Uncategorized'}",
            f"{'─' * 40}\n",
        ])

        for item in items:
            lines.append(f"  • {item.get('title', 'Untitled')}")
            content = item.get("content", "")
            if content:
                lines.append(f"    {content}")
            lines.append("")

        if project_name and project_name in summaries_lookup:
            lines.extend([
                "  [AI Summary]",
                f"  {summaries_lookup[project_name]}",
                "",
            ])

    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path
