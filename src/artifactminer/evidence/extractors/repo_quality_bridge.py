"""Bridge repo quality signals to evidence items."""

from __future__ import annotations

from datetime import date
from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.deep_analysis import RepoQualityResult

_DOCS_FLAGS = [("has_readme", "README"), ("has_changelog", "CHANGELOG"), ("has_docs_dir", "docs/")]
_QUALITY_FLAGS = [("has_lint_config", "lint"), ("has_precommit", "pre-commit"), ("has_type_check", "type checking")]


def repo_quality_to_evidence(
    quality: RepoQualityResult,
    *,
    evidence_date: date | None = None,
) -> List[EvidenceItem]:
    """Convert repository quality signals to evidence items."""
    items: List[EvidenceItem] = []

    if not quality:
        return items

    # Positive: testing
    if quality.has_tests and quality.test_file_count > 0:
        frameworks = ", ".join(quality.test_frameworks) if quality.test_frameworks else "tests"
        items.append(EvidenceItem(
            type="testing",
            content=f"Has {quality.test_file_count} test files ({frameworks})",
            source="repo_quality_signals",
            date=evidence_date,
        ))

    # Positive: documentation
    docs_parts = [label for attr, label in _DOCS_FLAGS if getattr(quality, attr)]
    if docs_parts:
        items.append(EvidenceItem(
            type="documentation",
            content=f"Has documentation: {', '.join(docs_parts)}",
            source="repo_quality_signals",
            date=evidence_date,
        ))

    # Positive: quality tooling
    quality_parts = [label for attr, label in _QUALITY_FLAGS if getattr(quality, attr)]
    if quality_parts:
        content = f"Has quality tooling: {', '.join(quality_parts)}"
        if quality.quality_tools:
            content += f" ({', '.join(quality.quality_tools)})"
        items.append(EvidenceItem(
            type="code_quality", content=content,
            source="repo_quality_signals", date=evidence_date,
        ))

    # Negative signals
    if not quality.has_tests:
        items.append(EvidenceItem(
            type="test_coverage",
            content="Test coverage below 80%: 0.0%",
            source="test_coverage_signals",
            date=evidence_date,
        ))

    if not quality.has_readme and not quality.has_docs_dir:
        items.append(EvidenceItem(
            type="documentation",
            content="Documentation is missing.",
            source="docs_signals",
            date=evidence_date,
        ))

    return items
