"""Signals related to documentation metrics."""

from __future__ import annotations

from artifactminer.evidence.models import EvidenceItem


def docs_dict_to_evidence(doc_data: dict) -> list[EvidenceItem]:
    """Convert a docs-presence dict to evidence items."""
    if not doc_data.get("has_docs", True):
        return [
            EvidenceItem(
                type="documentation",
                content="Documentation is missing.",
                source="docs_signals",
            )
        ]
    return []
