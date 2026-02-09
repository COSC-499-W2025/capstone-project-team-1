"""Data models for heuristic evidence extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, TypeAlias


EvidenceType: TypeAlias = Literal["metric", "feedback", "evaluation", "award", "custom"]
EVIDENCE_TYPE_EVALUATION: EvidenceType = "evaluation"


@dataclass
class EvidenceItem:
    """Structured evidence item ready for ProjectEvidence persistence."""

    type: EvidenceType
    content: str
    source: str | None = None
    date: date | None = None
