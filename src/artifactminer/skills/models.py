"""Lightweight data models used across skill extraction."""

from dataclasses import dataclass, field
from typing import Any, Iterable, List


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


@dataclass
class Insight:
    """Aggregated insight with rationale."""

    title: str
    evidence: List[str] = field(default_factory=list)
    why_it_matters: str = ""


@dataclass
class GitStatsResult:
    """Git contribution metrics for a user in a repo."""

    commit_count_window: int = 0
    commit_frequency: float = 0.0
    contribution_percent: float = 0.0
    first_commit_date: Any = None
    last_commit_date: Any = None
    has_branches: bool = False
    branch_count: int = 0
    has_tags: bool = False
    merge_commits: int = 0


@dataclass
class InfraSignalsResult:
    """Infrastructure and DevOps configuration signals."""

    ci_cd_tools: List[str] = field(default_factory=list)
    docker_tools: List[str] = field(default_factory=list)
    env_build_tools: List[str] = field(default_factory=list)
    all_tools: List[str] = field(default_factory=list)


@dataclass
class DeepAnalysisResult:
    """Baseline skills plus higher-order insights."""

    skills: List[ExtractedSkill]
    insights: List[Insight]
    git_stats: GitStatsResult | None = None
    infra_signals: InfraSignalsResult | None = None
    repo_quality: RepoQualityResult | None = None
