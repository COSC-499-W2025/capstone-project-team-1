"""Signals related to test coverage metrics."""

from __future__ import annotations

from artifactminer.evidence.models import EvidenceItem


def coverage_dict_to_evidence(coverage_data: dict) -> list[EvidenceItem]:
    """Convert a test-coverage dict to evidence items."""
    percent = coverage_data.get("percent", 100.0)
    if percent < 80:
        return [
            EvidenceItem(
                type="test_coverage",
                content=f"Test coverage below 80%: {percent:.1f}%",
                source="test_coverage_signals",
            )
        ]
    return []
