"""Bridge repo quality signals to evidence items."""

from __future__ import annotations

from datetime import date
from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.deep_analysis import RepoQualityResult


def repo_quality_to_evidence(
    quality: RepoQualityResult,
    *,
    evidence_date: date | None = None,
) -> List[EvidenceItem]:
    """Convert repository quality signals to evidence items."""
    items: List[EvidenceItem] = []

    if not quality:
        return items

    if quality.has_tests and quality.test_file_count > 0:
        frameworks = (
            ", ".join(quality.test_frameworks) if quality.test_frameworks else "tests"
        )
        items.append(
            EvidenceItem(
                type="testing",
                content=f"Has {quality.test_file_count} test files ({frameworks})",
                source="repo_quality_signals",
                date=evidence_date,
            )
        )

    docs_parts = []
    if quality.has_readme:
        docs_parts.append("README")
    if quality.has_changelog:
        docs_parts.append("CHANGELOG")
    if quality.has_docs_dir:
        docs_parts.append("docs/")
    if docs_parts:
        items.append(
            EvidenceItem(
                type="documentation",
                content=f"Has documentation: {', '.join(docs_parts)}",
                source="repo_quality_signals",
                date=evidence_date,
            )
        )

    quality_parts = []
    if quality.has_lint_config:
        quality_parts.append("lint")
    if quality.has_precommit:
        quality_parts.append("pre-commit")
    if quality.has_type_check:
        quality_parts.append("type checking")
    if quality_parts:
        tools = ", ".join(quality.quality_tools) if quality.quality_tools else ""
        content = f"Has quality tooling: {', '.join(quality_parts)}"
        if tools:
            content += f" ({tools})"
        items.append(
            EvidenceItem(
                type="code_quality",
                content=content,
                source="repo_quality_signals",
                date=evidence_date,
            )
        )

    return items
