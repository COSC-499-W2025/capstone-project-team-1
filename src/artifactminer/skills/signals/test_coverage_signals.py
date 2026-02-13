"""Signals related to test coverage metrics."""

from __future__ import annotations
from artifactminer.evidence.models import EvidenceItem


class TestCoverageSignals:
    def __init__(self, coverage_data: dict):
        self.coverage_data = coverage_data

    def to_evidence(self) -> list[EvidenceItem]:
        items = []
        if self.coverage_data["percent"] < 80:
            items.append(
                EvidenceItem(
                    type="test_coverage",
                    content="Test coverage below 80%: {0:.1f}%".format(
                        self.coverage_data["percent"]
                    ),
                    source="test_coverage_signals",
                )
            )
        return items
