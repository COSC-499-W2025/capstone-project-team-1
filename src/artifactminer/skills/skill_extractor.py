"""Offline skill extraction heuristics with optional LLM refinement."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

from artifactminer.mappings import CATEGORIES, DEPENDENCY_SKILLS
from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.signals.code_signals import collect_additions_text, iter_code_pattern_hits
from artifactminer.skills.signals.dependency_signals import dependency_hits
from artifactminer.skills.signals.language_signals import count_files_by_ext
from artifactminer.skills.user_profile import build_user_profile
from .skill_patterns import LANGUAGE_EXTENSIONS


class SkillExtractor:
    """Heuristic skill extractor that relies on deterministic signals only."""

    def __init__(self, enable_llm: bool = False) -> None:
        # enable_llm is accepted for backward compatibility but ignored
        self.enable_llm = False

    def extract_skills(
        self,
        repo_path: str,
        repo_stat: Any,
        user_email: str,
        user_contributions: Dict | None = None,
        consent_level: str = "none",
        frameworks: List[str] | None = None,
        languages: List[str] | None = None,
    ) -> List[ExtractedSkill]:
        repo_path = str(repo_path)
        user_contributions = dict(user_contributions or {})
        skills: Dict[str, ExtractedSkill] = {}

        # Required context: repo_stat tells us if this is collaborative; user_email scopes evidence.
        if not repo_stat:
            raise ValueError("repo_stat is required")
        if not hasattr(repo_stat, "is_collaborative"):
            raise ValueError("repo_stat.is_collaborative is required")
        if not user_email:
            raise ValueError("user_email is required for skill extraction")

        normalized_email = user_email.strip().lower()
        collab_flag = bool(getattr(repo_stat, "is_collaborative"))

        # Build a user-scoped profile when collaboration is enabled; force failure if no commits exist.
        user_profile = build_user_profile(repo_path, normalized_email) if collab_flag else None
        if collab_flag and not user_profile:
            raise ValueError("No commits found for the specified user in this collaborative repo")

        # Seed additions text for regex-based signals when the caller didn't provide any.
        if user_profile and user_profile.get("additions_text"):
            has_additions = user_contributions.get("additions") or user_contributions.get("user_additions")
            if not has_additions:
                user_contributions["additions"] = user_profile["additions_text"]

        user_contributions.setdefault("user_email", normalized_email)

        touched_paths: Set[str] | None = (
            set(user_profile["touched_paths"]) if user_profile and user_profile.get("touched_paths") else None
        )

        # ----------------------- language and framework signals ----------------------- #
        file_counts = user_profile["file_counts"] if user_profile else count_files_by_ext(repo_path)
        total_files = max(sum(file_counts.values()), 1)
        detected_languages = set(lang.lower() for lang in (languages or []))
        scope_label = "user-touched" if user_profile else "repo"

        # Language inference from file extensions
        for ext, count in file_counts.items():
            mapping = LANGUAGE_EXTENSIONS.get(ext)
            if mapping:
                name, category = mapping
                evidence = [f"{count} {scope_label} *{ext} files detected"]
                proficiency = self._score(count, total_files)
                self._add_skill(skills, name, category, evidence, proficiency)
                detected_languages.add(name.lower())

        # Repo-wide languages/frameworks are only used when the repo is not collaborative
        repo_languages = self._normalize_list(getattr(repo_stat, "Languages", None)) or self._normalize_list(
            getattr(repo_stat, "languages", None)
        )
        repo_frameworks = self._normalize_list(getattr(repo_stat, "frameworks", None))
        for lang in repo_languages:
            detected_languages.add(str(lang).lower())
        if not collab_flag:
            for lang in repo_languages:
                mapping = LANGUAGE_EXTENSIONS.get(lang)
                if mapping:
                    name, category = mapping
                    evidence = [f"Detected via repo stats: {lang}"]
                    self._add_skill(skills, name, category, evidence, 0.55)
                    detected_languages.add(name.lower())
            for fw in repo_frameworks:
                self._add_skill(
                    skills,
                    fw,
                    CATEGORIES["frameworks"],
                    [f"Detected framework {fw}"],
                    0.6,
                )
                detected_languages.update(self._ecosystems_from_frameworks([fw]))

        # Frameworks passed in by the caller (e.g., from dependency scanners)
        frameworks = frameworks or []
        if not collab_flag:
            frameworks = list(dict.fromkeys([*frameworks, *repo_frameworks]))
        for fw in frameworks:
            self._add_skill(
                skills,
                fw,
                CATEGORIES["frameworks"],
                [f"Dependency or config indicates {fw}"],
                0.62,
            )
        detected_languages.update(self._ecosystems_from_frameworks(frameworks))

        ecosystems = self._ecosystems(detected_languages)

        # ----------------------- dependency and filesystem signals ----------------------- #
        for eco in ecosystems | {"cross"}:
            for dep, (skill_name, category) in DEPENDENCY_SKILLS.get(eco, {}).items():
                dep_hits = dependency_hits(repo_path, dep, touched_paths=touched_paths)
                if dep_hits:
                    scope_hint = "user-edited manifests" if user_profile else "manifests"
                    evidence = [f"{dep_hits} occurrence(s) of '{dep}' in {scope_hint}"]
                    proficiency = min(0.8, 0.45 + 0.1 * dep_hits)
                    self._add_skill(skills, skill_name, category, evidence, proficiency)

        # ----------------------- code signals ----------------------- #
        additions_text = collect_additions_text(user_contributions)
        if user_profile and user_profile.get("additions_text"):
            if not additions_text:
                additions_text = user_profile["additions_text"]
            elif user_profile["additions_text"] not in additions_text:
                additions_text = additions_text + "\n" + user_profile["additions_text"]

        for pattern, hits in iter_code_pattern_hits(additions_text, ecosystems):
            evidence = [f"{pattern.evidence} ({hits} match{'es' if hits != 1 else ''})"]
            prof = min(0.9, pattern.weight + 0.05 * hits)
            self._add_skill(skills, pattern.skill, pattern.category, evidence, prof)

        return list(skills.values())

    # ----------------------- internal helpers ----------------------- #
    def _add_skill(
        self,
        skills: Dict[str, ExtractedSkill],
        skill: str,
        category: str,
        evidence: List[str],
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

    def _score(self, count: int, total: int) -> float:
        ratio = count / total if total else 0
        return round(min(1.0, 0.35 + 0.65 * ratio), 2)

    def _normalize_list(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    def _ecosystems(self, detected_languages: Set[str]) -> set[str]:
        lang_map = {
            "python": "python",
            "javascript": "javascript",
            "js": "javascript",
            "typescript": "javascript",
            "ts": "javascript",
            "java": "java",
            "kotlin": "java",
            "go": "go",
            "rust": "rust",
            "c#": "csharp",
            "csharp": "csharp",
            "php": "php",
            "ruby": "ruby",
            "swift": "swift",
        }
        ecos = set()
        for lang in detected_languages:
            low = lang.lower()
            mapped = lang_map.get(low)
            if mapped:
                ecos.add(mapped)
        return ecos

    def _ecosystems_from_frameworks(self, frameworks: Iterable[str]) -> set[str]:
        ecos = set()
        fw_map = {
            "python": ["fastapi", "flask", "django", "pydantic", "sqlalchemy"],
            "javascript": ["react", "vue", "angular", "next", "express", "nest", "next.js"],
            "typescript": ["react", "vue", "angular", "next", "express", "nest", "next.js"],
            "java": ["spring", "spring boot", "hibernate", "junit"],
            "go": ["gin", "echo", "fiber", "gorm"],
        }
        for fw in frameworks:
            fw_lower = fw.lower()
            for eco, needles in fw_map.items():
                if any(n in fw_lower for n in needles):
                    ecos.add(eco)
        return ecos
