"""Data models for heuristic evidence extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class EvidenceItem:
    """Structured evidence item ready for ProjectEvidence persistence."""

    type: str
    content: str
    source: str | None = None
    date: date | None = None
