"""Signals related to documentation metrics."""

from __future__ import annotations
from artifactminer.evidence.models import EvidenceItem


class DocsSignals:
    def __init__(self, doc_data: dict):
        self.doc_data = doc_data

    def to_evidence(self) -> list[EvidenceItem]:
        items = []
        if not self.doc_data["has_docs"]:
            items.append(
                EvidenceItem(
                    type="documentation",
                    content="Documentation is missing.",
                    source="docs_signals",
                )
            )
        return items
