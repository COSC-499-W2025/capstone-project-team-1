"""Offline skill extraction heuristics with optional LLM refinement."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import git

from artifactminer.RepositoryIntelligence.framework_detector import detect_frameworks
from artifactminer.RepositoryIntelligence.repo_intelligence_main import (
    getRepoStats,
    isGitRepo,
)
from artifactminer.helpers.openai import get_gpt5_nano_response
from .skill_patterns import (
    CODE_REGEX_PATTERNS,
    DEPENDENCY_SKILLS,
    FILE_PATTERNS,
    GIT_SKILLS,
    LANGUAGE_EXTENSIONS,
    CATEGORIES,
)


@dataclass
class ExtractedSkill:
    """Structured skill result."""

    skill: str
    category: str
    evidence: list[str] = field(default_factory=list)
    proficiency: float = 0.0

    def add_evidence(self, items: Iterable[str]) -> None:
        deduped = set(self.evidence)
        for item in items:
            if item not in deduped:
                self.evidence.append(item)
                deduped.add(item)


class SkillExtractor:
    """Heuristic skill extractor that works offline, with optional LLM refinement."""

    def __init__(self, enable_llm: bool = False) -> None:
        self.enable_llm = enable_llm

    def extract_skills(
        self,
        repo_path: str,
        user_contributions: Dict | None = None,
        consent_level: str = "none",
    ) -> List[ExtractedSkill]:
        repo_path = str(repo_path)
        user_contributions = user_contributions or {}
        skills: Dict[str, ExtractedSkill] = {}

        file_counts = self._count_files_by_ext(repo_path)
        total_files = max(sum(file_counts.values()), 1)

        # Languages from repository contents
        for ext, count in file_counts.items():
            mapping = LANGUAGE_EXTENSIONS.get(ext)
            if mapping:
                name, category = mapping
                evidence = [f"{count} *{ext} files detected"]
                proficiency = self._score(count, total_files)
                self._add_skill(skills, name, category, evidence, proficiency)

        # Language signals from manifests/shebangs/key files
        for lang_signal, evidence in self._language_signals(repo_path, file_counts):
            name, category = lang_signal
            self._add_skill(skills, name, category, [evidence], 0.55)

        # Frameworks and languages via repo stats
        try:
            stats = getRepoStats(repo_path)
            for lang in getattr(stats, "Languages", []) or []:
                mapping = LANGUAGE_EXTENSIONS.get(lang)
                if mapping:
                    name, category = mapping
                    evidence = [f"Detected via repo stats: {lang}"]
                    self._add_skill(skills, name, category, evidence, 0.55)
            for fw in getattr(stats, "frameworks", []) or []:
                self._add_skill(
                    skills,
                    fw,
                    CATEGORIES["frameworks"],
                    [f"Detected framework {fw}"],
                    0.6,
                )
        except Exception:
            # Repo stats are optional; continue with other signals
            pass

        # Framework detection pass (filesystem-based)
        try:
            for fw in detect_frameworks(repo_path):
                self._add_skill(
                    skills,
                    fw,
                    CATEGORIES["frameworks"],
                    [f"Dependency or config indicates {fw}"],
                    0.62,
                )
        except Exception:
            pass

        # Dependency manifests (pyproject/requirements)
        for dep, (skill_name, category) in DEPENDENCY_SKILLS.items():
            dep_hits = self._dependency_hits(repo_path, dep)
            if dep_hits:
                evidence = [f"{dep_hits} occurrence(s) of '{dep}' in manifests"]
                proficiency = min(0.8, 0.45 + 0.1 * dep_hits)
                self._add_skill(skills, skill_name, category, evidence, proficiency)

        # File/dir presence patterns
        for pattern in FILE_PATTERNS:
            matched = self._paths_present(repo_path, pattern.paths)
            if matched:
                prof = pattern.weight
                evidence = [f"{pattern.evidence}: {', '.join(matched)}"]
                self._add_skill(skills, pattern.skill, pattern.category, evidence, prof)

        # Code regex patterns from user additions/changes
        additions_text = self._collect_additions_text(user_contributions)
        for pattern in CODE_REGEX_PATTERNS:
            hits = len(re.findall(pattern.regex, additions_text, flags=re.MULTILINE))
            if hits:
                evidence = [f"{pattern.evidence} ({hits} match{'es' if hits != 1 else ''})"]
                prof = min(0.9, pattern.weight + 0.05 * hits)
                self._add_skill(skills, pattern.skill, pattern.category, evidence, prof)

        # Git patterns (merge commits / branches)
        git_signals = self._git_signals(repo_path, user_contributions)
        for pattern in GIT_SKILLS:
            if git_signals.get(pattern["key"], 0):
                count = git_signals[pattern["key"]]
                evidence = [f"{pattern['evidence']} ({count})"]
                prof = min(0.8, pattern["weight"] + 0.05 * count)
                self._add_skill(skills, pattern["skill"], pattern["category"], evidence, prof)

        # Optional LLM refinement
        if self.enable_llm and consent_level == "full":
            try:
                skills = self._enhance_with_llm(repo_path, skills)
            except Exception:
                # If LLM fails, keep baseline results
                pass

        return list(skills.values())

    # ----------------------- internal helpers ----------------------- #
    def _add_skill(
        self,
        skills: Dict[str, ExtractedSkill],
        skill: str,
        category: str,
        evidence: Iterable[str],
        proficiency: float,
    ) -> None:
        if skill in skills:
            skills[skill].proficiency = max(skills[skill].proficiency, float(proficiency))
            skills[skill].add_evidence(evidence)
        else:
            skills[skill] = ExtractedSkill(
                skill=skill,
                category=category,
                evidence=list(evidence),
                proficiency=float(proficiency),
            )

    def _count_files_by_ext(self, repo_path: str) -> Counter:
        counts: Counter = Counter()
        for path in Path(repo_path).rglob("*"):
            if path.is_file():
                counts[path.suffix.lower()] += 1
        return counts

    def _score(self, count: int, total: int) -> float:
        ratio = count / total if total else 0
        return round(min(1.0, 0.35 + 0.65 * ratio), 2)

    def _paths_present(self, repo_path: str, paths: Iterable[str]) -> List[str]:
        root = Path(repo_path)
        matched: List[str] = []
        for rel in paths:
            candidate = root / rel
            if candidate.exists():
                matched.append(rel)
        return matched

    def _dependency_hits(self, repo_path: str, needle: str) -> int:
        """Count mentions of a dependency across common manifests."""
        total_hits = 0
        manifests = [
            "pyproject.toml",
            "requirements.txt",
            "Pipfile",
            "package.json",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
        ]
        for manifest in manifests:
            target = Path(repo_path) / manifest
            if not target.exists():
                continue
            try:
                content = target.read_text().lower()
                total_hits += content.count(needle.lower())
            except Exception:
                continue
        return total_hits

    def _collect_additions_text(self, user_contributions: Dict) -> str:
        additions = user_contributions.get("additions") or user_contributions.get(
            "user_additions"
        )
        if not additions:
            return ""
        if isinstance(additions, str):
            return additions
        if isinstance(additions, list):
            return "\n".join([str(a) for a in additions])
        return str(additions)

    def _git_signals(self, repo_path: str, user_contributions: Dict) -> Dict[str, int]:
        # Allow callers to provide counts; otherwise infer from git repo
        signals = {
            "merge_commits": int(user_contributions.get("merge_commits", 0) or 0),
            "branches": 0,
        }
        if signals["merge_commits"] and user_contributions.get("branches"):
            signals["branches"] = len(user_contributions["branches"])

        if not isGitRepo(repo_path):
            return signals

        try:
            repo = git.Repo(repo_path)
        except Exception:
            return signals

        if not signals["merge_commits"]:
            try:
                merge_count = sum(1 for c in repo.iter_commits() if len(c.parents) > 1)
                signals["merge_commits"] = merge_count
            except Exception:
                pass

        if not signals["branches"]:
            try:
                branches = repo.git.branch("--list").splitlines()
                signals["branches"] = len([b for b in branches if b.strip()])
            except Exception:
                pass

        return signals

    def _language_signals(
        self, repo_path: str, file_counts: Counter
    ) -> List[Tuple[Tuple[str, str], str]]:
        """Infer languages from manifests, key files, and shebangs to avoid a huge hardcode list."""
        signals: List[Tuple[Tuple[str, str], str]] = []
        root = Path(repo_path)

        key_files = {
            "package.json": ("JavaScript", CATEGORIES["languages"]),
            "tsconfig.json": ("TypeScript", CATEGORIES["languages"]),
            "requirements.txt": ("Python", CATEGORIES["languages"]),
            "pyproject.toml": ("Python", CATEGORIES["languages"]),
            "Pipfile": ("Python", CATEGORIES["languages"]),
            "pom.xml": ("Java", CATEGORIES["languages"]),
            "build.gradle": ("Java", CATEGORIES["languages"]),
            "build.gradle.kts": ("Kotlin", CATEGORIES["languages"]),
            "go.mod": ("Go", CATEGORIES["languages"]),
            "Cargo.toml": ("Rust", CATEGORIES["languages"]),
            ".csproj": ("C#", CATEGORIES["languages"]),
            "Gemfile": ("Ruby", CATEGORIES["languages"]),
            "composer.json": ("PHP", CATEGORIES["languages"]),
            "mix.exs": ("Elixir", CATEGORIES["languages"]),
            "Makefile": ("Shell Scripting", CATEGORIES["languages"]),
        }

        for rel, mapping in key_files.items():
            if rel.startswith("."):
                matches = list(root.glob(f"**/*{rel}"))
            else:
                matches = list(root.glob(rel))
            if matches:
                signals.append((mapping, f"Detected {rel}"))

        # Simple shebang sampling for script-heavy repos
        shebang_map = {
            "python": ("Python", CATEGORIES["languages"]),
            "node": ("JavaScript", CATEGORIES["languages"]),
            "bash": ("Shell Scripting", CATEGORIES["languages"]),
            "sh": ("Shell Scripting", CATEGORIES["languages"]),
            "perl": ("Perl", CATEGORIES["languages"]),
            "ruby": ("Ruby", CATEGORIES["languages"]),
            "php": ("PHP", CATEGORIES["languages"]),
        }
        sample_limit = 50
        sampled = 0
        for path in root.rglob("*"):
            if sampled >= sample_limit:
                break
            if not path.is_file():
                continue
            try:
                first_line = path.open("r", encoding="utf-8", errors="ignore").readline()
            except Exception:
                continue
            if first_line.startswith("#!"):
                sampled += 1
                for key, mapping in shebang_map.items():
                    if key in first_line.lower():
                        signals.append((mapping, f"Shebang indicates {mapping[0]} in {path.name}"))
                        break

        return signals

    def _enhance_with_llm(
        self, repo_path: str, skills: Dict[str, ExtractedSkill]
    ) -> Dict[str, ExtractedSkill]:
        """Refine proficiency and add nuanced skills via LLM."""
        # Prepare a concise payload to stay within prompt limits
        summary = [
            {"skill": s.skill, "category": s.category, "evidence": s.evidence[:3], "proficiency": s.proficiency}
            for s in skills.values()
        ]
        prompt = (
            "You are refining detected technical skills from a repository scan.\n"
            "Given the baseline skills (with evidence snippets), adjust proficiency to a 0-1 scale "
            "where 1 is expert-level, and propose any additional nuanced skills you see.\n"
            "Return JSON with shape: {\"skills\": [{\"skill\": str, \"category\": str, \"proficiency\": float, \"evidence\": [str,...]}]}.\n\n"
            f"Baseline: {json.dumps(summary)}"
        )
        response = get_gpt5_nano_response(prompt)
        try:
            data = json.loads(response)
            for item in data.get("skills", []):
                skill_name = item.get("skill")
                category = item.get("category", CATEGORIES["practices"])
                evidence = item.get("evidence", [])
                prof = float(item.get("proficiency", 0.5))
                self._add_skill(skills, skill_name, category, evidence, prof)
        except Exception:
            # Fall back to existing skills if parsing fails
            return skills
        return skills
