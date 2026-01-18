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
) -> Path:
    """Export resume data to JSON file.
    
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
) -> Path:
    """Export resume data to plain text file.
    
    Returns the path to the created file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_export_{timestamp}.txt"
    path = (directory or Path.cwd()) / filename

    lines: list[str] = [
        "=" * 60,
        "RESUME EXPORT",
        f"Generated: {datetime.now().isoformat()}",
        "=" * 60,
        "",
    ]

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
