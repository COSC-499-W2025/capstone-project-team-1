"""Deeper, per-repo insights to meet TA-style analysis expectations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Pattern, Set, Tuple

from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.signals.file_signals import path_in_touched
from artifactminer.skills.skill_extractor import SkillExtractor
from artifactminer.skills.user_profile import build_user_profile


@dataclass
class Insight:
    """Higher-order skill evidence with rationale."""

    title: str
    evidence: List[str] = field(default_factory=list)
    why_it_matters: str = ""


@dataclass
class DeepAnalysisResult:
    """Combined baseline skills plus higher-order insights."""

    skills: List[ExtractedSkill]
    insights: List[Insight]


class DeepRepoAnalyzer:
    """Per-repo analyzer that layers deeper insights on top of SkillExtractor."""

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
        touched_paths: Set[str] | None = None
        if getattr(repo_stat, "is_collaborative", False):
            user_profile = build_user_profile(repo_path, user_email)
            if not user_profile:
                raise ValueError("No commits found for the specified user in this collaborative repo")
            touched_paths = set(user_profile.get("touched_paths") or [])

        skills = self.extractor.extract_skills(
            repo_path=repo_path,
            repo_stat=repo_stat,
            user_email=user_email,
            user_contributions=user_contributions or {},
            consent_level=consent_level,
        )
        repo_root = Path(repo_path)
        insights = [
            self._build_insight(
                "Complexity awareness",
                self._resource_guards(repo_root, touched_paths),
                "Caps, limits, and chunking show attention to cost/complexity under load.",
            ),
            self._build_insight(
                "Data structure choices",
                self._data_structure_signals(repo_root, touched_paths),
                "Intentional use of sets, Counters, and specialized containers indicates performance-minded decisions.",
            ),
            self._build_insight(
                "Abstraction and encapsulation",
                self._abstraction_signals(repo_root, touched_paths),
                "Classes, dataclasses, and interface-style hooks demonstrate structured design beyond scripts.",
            ),
            self._build_insight(
                "Robustness and error handling",
                self._robustness_signals(repo_root, touched_paths),
                "Guarded operations and fallbacks reduce brittleness when inputs or git state misbehave.",
            ),
        ]
        insights = [i for i in insights if i.evidence]
        return DeepAnalysisResult(skills=skills, insights=insights)

    def _build_insight(self, title: str, evidence: List[str], why: str) -> Insight:
        limited = evidence[:5]
        return Insight(title=title, evidence=limited, why_it_matters=why)

    def _resource_guards(self, repo_root: Path, touched_paths: Set[str] | None) -> List[str]:
        patterns = [
            r"\bmax_[a-zA-Z0-9_]+",
            r"\bchunk",
            r"\bbatch",
            r"\blimit",
            r"\btruncate",
            r"\bsample_limit\b",
            r"\btimeout",
        ]
        return self._keyword_hits(repo_root, patterns, touched_paths)

    def _data_structure_signals(self, repo_root: Path, touched_paths: Set[str] | None) -> List[str]:
        patterns = [
            r"\bCounter\b",
            r"\bdefaultdict\b",
            r"\bdeque\b",
            r"\bset\(",
            r"\bdict\(",
            r"\bheapq\b",
            r"\bbisect\b",
            r"\blru_cache\b",
        ]
        return self._keyword_hits(repo_root, patterns, touched_paths)

    def _abstraction_signals(self, repo_root: Path, touched_paths: Set[str] | None) -> List[str]:
        patterns = [
            r"@dataclass",
            r"\bclass\s+[A-Za-z_][A-Za-z0-9_]*\(",
            r"\bABC\b",
            r"\bProtocol\b",
            r"\babstractmethod\b",
        ]
        return self._keyword_hits(repo_root, patterns, touched_paths)

    def _robustness_signals(self, repo_root: Path, touched_paths: Set[str] | None) -> List[str]:
        patterns = [
            r"\btry:",
            r"\bexcept\b",
            r"\bfallback\b",
            r"\bif\s+not\s+.*:\s+return",
        ]
        return self._keyword_hits(repo_root, patterns, touched_paths)

    def _keyword_hits(self, repo_root: Path, regexes: Iterable[str], touched_paths: Set[str] | None) -> List[str]:
        hits: List[str] = []
        compiled: List[Tuple[str, Pattern[str]]] = [(p, re.compile(p)) for p in regexes]
        for path in repo_root.rglob("*.py"):
            if not path.is_file():
                continue
            if touched_paths is not None:
                rel_str = path.relative_to(repo_root).as_posix()
                if not path_in_touched(rel_str, touched_paths):
                    continue
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for lineno, line in enumerate(lines, start=1):
                for label, regex in compiled:
                    if regex.search(line):
                        rel = path.relative_to(repo_root)
                        snippet = line.strip()
                        hits.append(f"{rel}:{lineno}: {snippet}")
                        break
        return hits
