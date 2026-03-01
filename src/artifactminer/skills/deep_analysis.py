"""Higher-order insights built directly from user additions-driven skills."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List

from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.skill_extractor import SkillExtractor
from artifactminer.skills.skill_patterns import CODE_REGEX_PATTERNS
from artifactminer.skills.signals.git_signals import get_git_stats, detect_git_patterns
from artifactminer.skills.signals.infra_signals import get_infra_signals
from artifactminer.skills.signals.repo_quality_signals import get_repo_quality_signals


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
class DeepAnalysisResult:
    """Baseline skills plus higher-order insights."""

    skills: List[ExtractedSkill]
    insights: List[Insight]
    git_stats: GitStatsResult | None = None
    infra_signals: InfraSignalsResult | None = None
    repo_quality: RepoQualityResult | None = None


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
        repo_quality = self._extract_repo_quality(repo_path, user_contributions)

        return DeepAnalysisResult(
            skills=skills,
            insights=insights,
            git_stats=git_stats,
            infra_signals=infra_signals,
            repo_quality=repo_quality,
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
        kwargs = {"touched_paths": touched_paths}
        if user_stats is not None:
            kwargs["user_stats"] = user_stats
        stats = get_git_stats(repo_path, user_email, **kwargs)
        patterns = detect_git_patterns(repo_path, touched_paths=touched_paths)

        if not stats and not patterns:
            return None

        merged = {**(stats or {}), **(patterns or {})}
        valid = {f.name for f in fields(GitStatsResult)}
        return GitStatsResult(**{k: merged.get(k) for k in valid if k in merged})

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
        valid = {f.name for f in fields(InfraSignalsResult)}
        return InfraSignalsResult(**{k: summary.get(k) for k in valid if k in summary})

    def _extract_repo_quality(
        self,
        repo_path: str,
        user_contributions: Dict | None,
    ) -> RepoQualityResult | None:
        """Extract repository quality signals."""
        touched_paths = (
            user_contributions.get("touched_paths") if user_contributions else None
        )
        return get_repo_quality_signals(repo_path, touched_paths=touched_paths) or None

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
