"""Minimal async local-generation service built on the shared local runtime."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from ...RepositoryIntelligence.repo_intelligence_main import getRepoStats
from ...RepositoryIntelligence.repo_intelligence_user import (
    collect_user_additions,
    getUserRepoStats,
)
from ..client import query_json
from .prompts import (
    DRAFT_SYSTEM,
    FACTS_SYSTEM,
    POLISH_SYSTEM,
    build_draft_prompt,
    build_polish_prompt,
    build_project_facts_prompt,
)
from .schemas import GenerationFeedback, ProjectFacts, ResumeOutputModel


ProgressCallback = Callable[[str], None]


def _read_readme(repo_path: Path) -> str:
    candidates = sorted(repo_path.glob("README*"))
    for candidate in candidates:
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8", errors="ignore")[:4000]
            except OSError:
                continue
    return ""


def _recent_commit_messages(repo_path: Path, user_email: str, limit: int = 12) -> list[str]:
    result = subprocess.run(
        [
            "git",
            "log",
            f"--author={user_email}",
            "--format=%s",
            "-n",
            str(limit),
        ],
        cwd=str(repo_path),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _sample_files(repo_path: Path, limit: int = 20) -> list[str]:
    sampled: list[str] = []
    for path in sorted(repo_path.rglob("*")):
        if len(sampled) >= limit:
            break
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(repo_path)
        except ValueError:
            continue
        if ".git" in relative.parts:
            continue
        sampled.append(relative.as_posix())
    return sampled


def _build_snapshot(repo_path: Path, user_email: str) -> dict[str, object]:
    repo_stats = getRepoStats(repo_path)
    try:
        user_stats = getUserRepoStats(repo_path, user_email)
    except ValueError:
        user_stats = None

    try:
        additions = collect_user_additions(
            repo_path=str(repo_path),
            user_email=user_email,
            max_commits=20,
        )
    except Exception:
        additions = []

    commit_breakdown = {}
    if user_stats and user_stats.commitActivities:
        commit_breakdown = {
            str(key): int(value)
            for key, value in user_stats.commitActivities.items()
            if isinstance(value, (int, float))
        }

    return {
        "project_name": repo_stats.project_name,
        "project_path": str(repo_path),
        "primary_language": repo_stats.primary_language,
        "languages": list(repo_stats.Languages),
        "frameworks": list(repo_stats.frameworks),
        "health_score": repo_stats.health_score,
        "total_commits": repo_stats.total_commits,
        "first_commit": repo_stats.first_commit.isoformat() if repo_stats.first_commit else None,
        "last_commit": repo_stats.last_commit.isoformat() if repo_stats.last_commit else None,
        "user_contribution_pct": (
            round(float(user_stats.userStatspercentages), 1)
            if user_stats and user_stats.userStatspercentages is not None
            else None
        ),
        "user_total_commits": user_stats.total_commits if user_stats else None,
        "commit_breakdown": commit_breakdown,
        "readme_excerpt": _read_readme(repo_path),
        "recent_commit_messages": _recent_commit_messages(repo_path, user_email),
        "recent_added_lines": additions[-3:],
        "sample_files": _sample_files(repo_path),
    }


def _build_portfolio_summary(facts: list[ProjectFacts]) -> dict[str, object]:
    languages: list[str] = []
    frameworks: list[str] = []
    project_types: dict[str, int] = {}
    top_skills: list[str] = []
    total_commits = 0

    for fact in facts:
        if fact.primary_language and fact.primary_language not in languages:
            languages.append(fact.primary_language)
        for framework in fact.frameworks:
            if framework not in frameworks:
                frameworks.append(framework)
        project_types[fact.project_type] = project_types.get(fact.project_type, 0) + 1
        total_commits += sum(fact.commit_breakdown.values())
        for technology in fact.technologies:
            if technology not in top_skills:
                top_skills.append(technology)

    return {
        "total_projects": len(facts),
        "total_commits": total_commits,
        "languages_used": languages,
        "frameworks_used": frameworks,
        "project_types": project_types,
        "top_skills": top_skills[:10],
    }


def _normalize_output(
    output: ResumeOutputModel,
    *,
    facts: list[ProjectFacts],
    stage: str,
    models_used: list[str],
    generation_time_seconds: float,
    errors: list[str],
) -> ResumeOutputModel:
    facts_by_name = {fact.project_name: fact for fact in facts}
    normalized_projects = []
    for project in output.projects:
        fact = facts_by_name.get(project.name)
        if fact is None:
            normalized_projects.append(project)
            continue

        if not project.frameworks:
            project.frameworks = list(fact.frameworks)
        if project.primary_language is None:
            project.primary_language = fact.primary_language
        if project.contribution_pct is None:
            project.contribution_pct = fact.contribution_pct
        if not project.commit_breakdown:
            project.commit_breakdown = dict(fact.commit_breakdown)
        if not project.period.first_commit:
            project.period.first_commit = fact.first_commit
        if not project.period.last_commit:
            project.period.last_commit = fact.last_commit
        normalized_projects.append(project)

    output.projects = normalized_projects
    output.portfolio = output.portfolio or _build_portfolio_summary(facts)
    output.metadata.stage = stage
    output.metadata.models_used = list(models_used)
    output.metadata.model_used = models_used[-1] if models_used else None
    output.metadata.generation_time_seconds = generation_time_seconds
    output.metadata.errors = list(errors)
    output.metadata.quality_metrics = output.metadata.quality_metrics or {}
    return output


async def generate_project_facts(
    repo_path: Path,
    *,
    user_email: str,
    model: str,
    progress: ProgressCallback | None = None,
) -> ProjectFacts:
    snapshot = _build_snapshot(repo_path, user_email)
    if progress:
        progress(f"Compiling facts for {repo_path.name}")
    facts = await query_json(
        build_project_facts_prompt(snapshot),
        ProjectFacts,
        model=model,
        system=FACTS_SYSTEM,
    )
    facts.project_name = str(snapshot["project_name"])
    facts.primary_language = snapshot["primary_language"] or facts.primary_language
    facts.frameworks = list(snapshot["frameworks"]) or facts.frameworks
    facts.contribution_pct = snapshot["user_contribution_pct"] or facts.contribution_pct
    facts.commit_breakdown = dict(snapshot["commit_breakdown"]) or facts.commit_breakdown
    facts.first_commit = snapshot["first_commit"] or facts.first_commit
    facts.last_commit = snapshot["last_commit"] or facts.last_commit
    return facts


async def build_draft_output(
    facts: list[ProjectFacts],
    *,
    user_email: str,
    model: str,
) -> ResumeOutputModel:
    portfolio_summary = _build_portfolio_summary(facts)
    output = await query_json(
        build_draft_prompt(
            user_email=user_email,
            project_facts=[fact.model_dump() for fact in facts],
            portfolio_summary=portfolio_summary,
        ),
        ResumeOutputModel,
        model=model,
        system=DRAFT_SYSTEM,
    )
    return output


async def build_polished_output(
    draft_output: ResumeOutputModel,
    feedback: GenerationFeedback,
    *,
    model: str,
) -> ResumeOutputModel:
    output = await query_json(
        build_polish_prompt(
            draft_output=draft_output.model_dump(),
            feedback=feedback.model_dump(),
        ),
        ResumeOutputModel,
        model=model,
        system=POLISH_SYSTEM,
    )
    return output


def finalize_output(
    output: ResumeOutputModel,
    *,
    facts: list[ProjectFacts],
    stage: str,
    models_used: list[str],
    generation_time_seconds: float,
    errors: list[str],
) -> dict[str, object]:
    normalized = _normalize_output(
        output,
        facts=facts,
        stage=stage,
        models_used=models_used,
        generation_time_seconds=generation_time_seconds,
        errors=errors,
    )
    return normalized.model_dump()
