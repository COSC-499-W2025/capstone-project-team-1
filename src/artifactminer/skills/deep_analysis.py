"""Higher-order insights built directly from user additions-driven skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.skill_extractor import SkillExtractor
from artifactminer.skills.skill_patterns import CODE_REGEX_PATTERNS
from artifactminer.skills.signals.git_signals import get_git_stats, detect_git_patterns
from artifactminer.skills.signals.infra_signals import get_infra_signals


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


class DeepRepoAnalyzer:
    """Per-repo analyzer that relies on user additions for attribution."""

    # Map insight titles to underlying skill names and rationale
    _INSIGHT_RULES: Dict[str, Dict[str, Any]] = {
        "Complexity awareness": {
            "skills": {"Resource Management"},
            "why": "Resource caps and chunking show attention to cost/complexity under load.",
        },
        "Data structure and optimization": {
            "skills": {"Advanced Collections", "Algorithm Optimization"},
            "why": "Specialized collections and optimization tools indicate performance-minded choices.",
        },
        "Abstraction and encapsulation": {
            "skills": {"Dataclass Design", "Abstract Interfaces", "Data Validation"},
            "why": "Structured modeling and interfaces reflect design thinking beyond scripts.",
        },
        "Robustness and error handling": {
            "skills": {
                "Exception Design",
                "Context Management",
                "Error Handling",
                "Logging",
            },
            "why": "Custom exceptions, managed resources, and logging reduce brittleness in failure scenarios.",
        },
        "Async and concurrency": {
            "skills": {"Asynchronous Programming"},
            "why": "Async patterns enable scalable, non-blocking operations.",
        },
        "API design and architecture": {
            "skills": {"REST API Design", "Dependency Injection", "Data Validation"},
            "why": "Clean API design with validation and DI shows architectural maturity.",
        },
    }

    def __init__(self, enable_llm: bool = False) -> None:
        self.extractor = SkillExtractor(enable_llm=enable_llm)
        self._validate_insight_rules()

    def analyze(
        self,
        repo_path: str,
        repo_stat: Any,
        user_email: str,
        user_contributions: Dict | None = None,
        consent_level: str = "none",
        user_stats: Any = None,
    ) -> DeepAnalysisResult:
        """Run baseline skill extraction, then derive insights from user-attributed skills."""
        skills = self.extractor.extract_skills(
            repo_path=repo_path,
            repo_stat=repo_stat,
            user_email=user_email,
            user_contributions=user_contributions or {},
            consent_level=consent_level,
        )
        insights = self._derive_insights(skills)

        git_stats = self._extract_git_stats(
            repo_path, user_email, user_contributions, user_stats
        )
        infra_signals = self._extract_infra_signals(repo_path, user_contributions)

        return DeepAnalysisResult(
            skills=skills,
            insights=insights,
            git_stats=git_stats,
            infra_signals=infra_signals,
        )

    def _extract_git_stats(
        self,
        repo_path: str,
        user_email: str,
        user_contributions: Dict | None,
        user_stats: Any = None,
    ) -> GitStatsResult | None:
        """Extract git contribution metrics for the user."""
        touched_paths = (
            user_contributions.get("touched_paths") if user_contributions else None
        )
        if user_stats is not None:
            stats = get_git_stats(
                repo_path,
                user_email,
                touched_paths=touched_paths,
                user_stats=user_stats,
            )
        else:
            stats = get_git_stats(repo_path, user_email, touched_paths=touched_paths)
        patterns = detect_git_patterns(repo_path, touched_paths=touched_paths)

        if not stats and not patterns:
            return None

        return GitStatsResult(
            commit_count_window=stats.get("commit_count_window", 0),
            commit_frequency=stats.get("commit_frequency", 0.0),
            contribution_percent=stats.get("contribution_percent", 0.0),
            first_commit_date=stats.get("first_commit_date"),
            last_commit_date=stats.get("last_commit_date"),
            has_branches=patterns.get("has_branches", False),
            branch_count=patterns.get("branch_count", 0),
            has_tags=patterns.get("has_tags", False),
            merge_commits=patterns.get("merge_commits", 0),
        )

    def _extract_infra_signals(
        self,
        repo_path: str,
        user_contributions: Dict | None,
    ) -> InfraSignalsResult | None:
        """Extract infrastructure and DevOps configuration signals."""
        touched_paths = (
            user_contributions.get("touched_paths") if user_contributions else None
        )
        signals = get_infra_signals(repo_path, touched_paths=touched_paths)

        if not signals:
            return None

        summary = signals.get("summary", {})
        return InfraSignalsResult(
            ci_cd_tools=summary.get("ci_cd_tools", []),
            docker_tools=summary.get("docker_tools", []),
            env_build_tools=summary.get("env_build_tools", []),
            all_tools=summary.get("all_tools", []),
        )

    def _validate_insight_rules(self) -> None:
        """Fail fast if insight rules reference skills that do not exist."""
        available_skills = {pattern.skill for pattern in CODE_REGEX_PATTERNS}
        for title, rule in self._INSIGHT_RULES.items():
            missing = set(rule["skills"]) - available_skills
            if missing:
                raise ValueError(
                    f"Insight '{title}' references unknown skills: {sorted(missing)}"
                )

    def _derive_insights(self, skills: List[ExtractedSkill]) -> List[Insight]:
        insight_results: List[Insight] = []
        skill_map = {s.skill: s for s in skills}
        for title, rule in self._INSIGHT_RULES.items():
            names = rule["skills"]
            matched = [skill_map[name] for name in names if name in skill_map]
            if not matched:
                continue
            evidence: List[str] = []
            for skill in matched:
                evidence.extend(skill.evidence[:2])
            # Keep evidence concise
            insight_results.append(
                Insight(
                    title=title,
                    evidence=evidence[:5],
                    why_it_matters=rule["why"],
                )
            )
        return insight_results
