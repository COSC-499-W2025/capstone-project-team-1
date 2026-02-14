"""Signals related to code quality metrics."""

from __future__ import annotations

from artifactminer.evidence.models import EvidenceItem


def quality_dict_to_evidence(quality_data: dict) -> list[EvidenceItem]:
    """Convert a code-quality dict to evidence items."""
    issues = quality_data.get("issues", 0) or 0
    if issues > 0:
        return [
            EvidenceItem(
                type="code_quality",
                content=f"Code quality issues found: {issues} issues",
                source="code_quality_signals",
            )
        ]
    return []
