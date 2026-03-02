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


@dataclass
class RepoQualityResult:
    """Repository quality signals: testing, documentation, code quality."""

    test_file_count: int = 0
    has_tests: bool = False
    test_frameworks: List[str] = field(default_factory=list)
    has_readme: bool = False
    has_changelog: bool = False
    has_contributing: bool = False
    has_docs_dir: bool = False
    has_lint_config: bool = False
    has_precommit: bool = False
    has_type_check: bool = False
    quality_tools: List[str] = field(default_factory=list)
