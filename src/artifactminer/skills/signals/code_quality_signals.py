"""Signals related to code quality metrics."""

from __future__ import annotations
from artifactminer.evidence.models import EvidenceItem


class CodeQualitySignals:
    def __init__(self, quality_data: dict):
        self.quality_data = quality_data

    def to_evidence(self) -> list[EvidenceItem]:
        items = []
        if self.quality_data["issues"] > 0:
            items.append(
                EvidenceItem(
                    type="code_quality",
                    content="Code quality issues found: {0} issues".format(
                        self.quality_data["issues"]
                    ),
                    source="code_quality_signals",
                )
            )
        return items
