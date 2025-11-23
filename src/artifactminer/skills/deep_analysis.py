"""Higher-order insights built directly from user additions-driven skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.skill_extractor import SkillExtractor


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
            "skills": {"Dataclass Design", "Abstract Interfaces"},
            "why": "Structured modeling and interfaces reflect design thinking beyond scripts.",
        },
        "Robustness and error handling": {
            "skills": {"Exception Design", "Context Management"},
            "why": "Custom exceptions and managed resources reduce brittleness in failure scenarios.",
        },
    }

    def __init__(self, enable_llm: bool = False) -> None:
        self.extractor = SkillExtractor(enable_llm=enable_llm)

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
