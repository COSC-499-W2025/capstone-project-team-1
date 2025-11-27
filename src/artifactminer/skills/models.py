"""Lightweight data models used across skill extraction."""

from dataclasses import dataclass, field
from typing import Iterable, List


@dataclass
class ExtractedSkill:
    """Structured skill result with evidence and proficiency."""

    skill: str
    category: str
    evidence: List[str] = field(default_factory=list)
    proficiency: float = 0.0

    def add_evidence(self, items: Iterable[str]) -> None:
        """Append unique evidence snippets."""
        deduped = set(self.evidence)
        for item in items:
            if item not in deduped:
                self.evidence.append(item)
                deduped.add(item)
