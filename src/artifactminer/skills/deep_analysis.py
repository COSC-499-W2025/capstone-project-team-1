"""Higher-order insights built directly from user additions-driven skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.skill_extractor import SkillExtractor
from artifactminer.skills.skill_patterns import CODE_REGEX_PATTERNS


@dataclass
class Insight:
    """Aggregated insight with rationale."""

    title: str
    evidence: List[str] = field(default_factory=list)
    why_it_matters: str = ""


@dataclass
class DeepAnalysisResult:
    """Baseline skills plus higher-order insights."""

    skills: List[ExtractedSkill]
    insights: List[Insight]


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
            "skills": {"Exception Design", "Context Management", "Error Handling", "Logging"},
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
        return DeepAnalysisResult(skills=skills, insights=insights)

    def _validate_insight_rules(self) -> None:
        """Fail fast if insight rules reference skills that do not exist."""
        available_skills = {pattern.skill for pattern in CODE_REGEX_PATTERNS}
        for title, rule in self._INSIGHT_RULES.items():
            missing = set(rule["skills"]) - available_skills
            if missing:
                raise ValueError(f"Insight '{title}' references unknown skills: {sorted(missing)}")

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
