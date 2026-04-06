"""Minimal async local-generation service built on the shared local runtime."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import math
import subprocess
from pathlib import Path
from typing import Callable

from ...RepositoryIntelligence.repo_intelligence_main import getRepoStats
from ...RepositoryIntelligence.repo_intelligence_user import (
    collect_user_additions,
    get_daily_commit_counts,
    getUserRepoStats,
)
import json as json_lib

from ..client import query_text
from .markdown_parser import parse_resume_markdown
from .prompts import (
    FACTS_SYSTEM,
    POLISH_SYSTEM,
    PROJECT_CONTENT_SYSTEM,
    PROFILE_SYSTEM,
    SUMMARY_SYSTEM,
    build_polish_prompt,
    build_profile_prompt,
    build_project_content_prompt,
    build_project_facts_prompt,
    build_summary_prompt,
)
from .schemas import (
    GenerationFeedback,
    ProjectFacts,
    ResumeOutputModel,
    ResumePortfolioDashboardModel,
    ResumePortfolioModel,
    ResumeProjectModel,
    ResumeProjectPeriod,
)


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


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _format_iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _snapshot_by_project_name(
    snapshots: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    by_project: dict[str, dict[str, object]] = {}
    for snapshot in snapshots:
        name = snapshot.get("project_name")
        if isinstance(name, str) and name.strip():
            by_project[name] = snapshot
    return by_project


def _commit_total_for_depth(
    fact: ProjectFacts, snapshot: dict[str, object] | None
) -> int:
    if snapshot:
        user_total = snapshot.get("user_total_commits")
        if isinstance(user_total, bool):
            return int(user_total)
        if isinstance(user_total, (int, float)):
            return max(0, int(user_total))
    return max(0, sum(fact.commit_breakdown.values()))


def _project_skills(fact: ProjectFacts) -> list[str]:
    skills: list[str] = []
    seen: set[str] = set()
    for raw_skill in fact.technologies:
        normalized = raw_skill.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        skills.append(normalized)
    return skills


def _build_skills_timeline(
    facts: list[ProjectFacts],
    snapshots: list[dict[str, object]],
) -> list[dict[str, object]]:
    snapshots_by_project = _snapshot_by_project_name(snapshots)
    timeline_map: dict[str, dict[str, object]] = {}

    for fact in facts:
        snapshot = snapshots_by_project.get(fact.project_name)
        first_seen = _parse_iso_datetime(fact.first_commit)
        last_seen = _parse_iso_datetime(fact.last_commit)
        depth_score = math.log1p(_commit_total_for_depth(fact, snapshot))
        for skill in _project_skills(fact):
            row = timeline_map.setdefault(
                skill,
                {
                    "skill": skill,
                    "first_seen": None,
                    "last_seen": None,
                    "depth_score": 0.0,
                    "projects": set(),
                },
            )
            row["projects"].add(fact.project_name)
            row["depth_score"] = float(row["depth_score"]) + depth_score
            row_first_seen = row["first_seen"]
            row_last_seen = row["last_seen"]
            if first_seen and (row_first_seen is None or first_seen < row_first_seen):
                row["first_seen"] = first_seen
            if last_seen and (row_last_seen is None or last_seen > row_last_seen):
                row["last_seen"] = last_seen

    timeline_items: list[dict[str, object]] = []
    for row in timeline_map.values():
        projects = row["projects"]
        timeline_items.append(
            {
                "skill": row["skill"],
                "first_seen": _format_iso_datetime(row["first_seen"]),
                "last_seen": _format_iso_datetime(row["last_seen"]),
                "projects_count": len(projects),
                "depth_score": round(float(row["depth_score"]), 4),
            }
        )

    timeline_items.sort(
        key=lambda item: (
            _parse_iso_datetime(
                item["first_seen"] if isinstance(item["first_seen"], str) else None
            )
            or datetime.max,
            -float(item["depth_score"]),
            str(item["skill"]).casefold(),
        )
    )
    return timeline_items


def _build_activity_heatmap(
    snapshots: list[dict[str, object]],
) -> dict[str, object]:
    aggregated: dict[str, int] = defaultdict(int)
    for snapshot in snapshots:
        daily_commits = snapshot.get("daily_commits")
        if not isinstance(daily_commits, dict):
            continue
        for raw_day, raw_count in daily_commits.items():
            if not isinstance(raw_day, str):
                continue
            try:
                datetime.fromisoformat(raw_day)
            except ValueError:
                continue
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                continue
            if count <= 0:
                continue
            aggregated[raw_day] += count

    daily_activity = dict(sorted(aggregated.items()))
    if daily_activity:
        start = next(iter(daily_activity))
        end = next(reversed(daily_activity))
    else:
        start = None
        end = None

    return {
        "daily_activity": daily_activity,
        "total_days_active": len(daily_activity),
        "max_daily_commits": max(daily_activity.values()) if daily_activity else 0,
        "date_range": {"start": start, "end": end},
    }


def _derive_activity_focus(snapshot: dict[str, object]) -> str | None:
    activity_breakdown = snapshot.get("activity_breakdown")
    if not isinstance(activity_breakdown, dict):
        return None

    ranked: list[tuple[str, float, int]] = []
    for activity, payload in activity_breakdown.items():
        if not isinstance(activity, str) or not isinstance(payload, dict):
            continue
        percentage = payload.get("percentage", 0)
        commits = payload.get("commits", 0)
        try:
            pct_value = float(percentage)
        except (TypeError, ValueError):
            pct_value = 0.0
        try:
            commit_value = int(commits)
        except (TypeError, ValueError):
            commit_value = 0
        ranked.append((activity, pct_value, commit_value))

    if not ranked:
        return None

    ranked.sort(key=lambda item: (-item[1], -item[2], item[0].casefold()))
    top = ranked[:2]
    return ", ".join(f"{name} {round(pct)}%" for name, pct, _ in top)


def _derive_evolution_note(first_commit: datetime | None, last_commit: datetime | None) -> str:
    if first_commit and last_commit:
        span = max(0, (last_commit - first_commit).days)
        return f"Evolved over {span} days of commits."
    if first_commit:
        return "Early project activity detected."
    if last_commit:
        return "Recent project activity detected."
    return "Commit history unavailable."


def _build_top_projects(
    facts: list[ProjectFacts],
    snapshots: list[dict[str, object]],
    *,
    now: datetime | None = None,
) -> list[dict[str, object]]:
    snapshots_by_project = _snapshot_by_project_name(snapshots)
    now_dt = now or datetime.now(UTC).replace(tzinfo=None)
    project_rows: list[dict[str, object]] = []

    for fact in facts:
        snapshot = snapshots_by_project.get(fact.project_name, {})
        contribution_pct = fact.contribution_pct
        commit_total = _commit_total_for_depth(fact, snapshot)
        first_commit = _parse_iso_datetime(fact.first_commit)
        last_commit = _parse_iso_datetime(fact.last_commit)
        recency_score = 0.0
        if last_commit:
            days_since_last_commit = max(0, (now_dt - last_commit).days)
            recency_score = max(0.0, 1.0 - (days_since_last_commit / 365.0))

        recent_messages = snapshot.get("recent_commit_messages")
        latest_change = None
        if isinstance(recent_messages, list):
            latest_change = next(
                (
                    message.strip()
                    for message in recent_messages
                    if isinstance(message, str) and message.strip()
                ),
                None,
            )

        project_rows.append(
            {
                "project_name": fact.project_name,
                "project_type": fact.project_type,
                "contribution_pct": contribution_pct,
                "commit_total": commit_total,
                "first_commit": first_commit,
                "last_commit": last_commit,
                "recency_score": recency_score,
                "activity_focus": _derive_activity_focus(snapshot),
                "latest_change": latest_change,
                "evolution_note": _derive_evolution_note(first_commit, last_commit),
            }
        )

    max_contribution = max(
        (
            float(row["contribution_pct"])
            for row in project_rows
            if isinstance(row["contribution_pct"], (int, float))
        ),
        default=0.0,
    )
    max_commit_total = max((int(row["commit_total"]) for row in project_rows), default=0)

    for row in project_rows:
        contribution_raw = row["contribution_pct"]
        contribution_value = (
            float(contribution_raw) if isinstance(contribution_raw, (int, float)) else 0.0
        )
        normalized_contribution = (
            contribution_value / max_contribution if max_contribution > 0 else 0.0
        )
        normalized_commit_total = (
            int(row["commit_total"]) / max_commit_total if max_commit_total > 0 else 0.0
        )
        score = (
            0.45 * normalized_contribution
            + 0.35 * normalized_commit_total
            + 0.20 * float(row["recency_score"])
        )
        row["score"] = score

    project_rows.sort(
        key=lambda row: (
            -float(row["score"]),
            -int(row["commit_total"]),
            -(
                row["last_commit"].timestamp()
                if isinstance(row["last_commit"], datetime)
                else float("-inf")
            ),
            str(row["project_name"]).casefold(),
        )
    )

    top_rows = project_rows[:3]
    top_projects: list[dict[str, object]] = []
    for row in top_rows:
        top_projects.append(
            {
                "project_name": row["project_name"],
                "project_type": row["project_type"],
                "score": round(float(row["score"]), 6),
                "contribution_pct": row["contribution_pct"],
                "commit_total": row["commit_total"],
                "first_commit": _format_iso_datetime(row["first_commit"]),
                "last_commit": _format_iso_datetime(row["last_commit"]),
                "recency_score": round(float(row["recency_score"]), 6),
                "activity_focus": row["activity_focus"],
                "latest_change": row["latest_change"],
                "evolution_note": row["evolution_note"],
            }
        )
    return top_projects


def _build_portfolio_dashboard(
    facts: list[ProjectFacts],
    snapshots: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "skills_timeline": _build_skills_timeline(facts, snapshots),
        "activity_heatmap": _build_activity_heatmap(snapshots),
        "top_projects": _build_top_projects(facts, snapshots),
    }


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
    activity_breakdown: dict[str, object] = {}
    if user_stats and user_stats.commitActivities:
        activities = user_stats.commitActivities
        if isinstance(activities, dict):
            for key, value in activities.items():
                if isinstance(value, dict):
                    activity_breakdown[str(key)] = {
                        "commits": value.get("commits", 0),
                        "lines_added": value.get("lines_added", 0),
                        "percentage": value.get("percentage", 0),
                    }
                elif isinstance(value, (int, float)):
                    commit_breakdown[str(key)] = int(value)

    daily_commits = get_daily_commit_counts(repo_path, user_email)

    return {
        "project_name": repo_stats.project_name,
        "project_path": str(repo_path),
        "primary_language": repo_stats.primary_language,
        "languages": list(repo_stats.Languages),
        "language_percentages": list(repo_stats.language_percentages)
        if hasattr(repo_stats, "language_percentages")
        else [],
        "frameworks": list(repo_stats.frameworks),
        "health_score": repo_stats.health_score,
        "is_collaborative": getattr(repo_stats, "is_collaborative", False),
        "total_commits": repo_stats.total_commits,
        "first_commit": repo_stats.first_commit.isoformat() if repo_stats.first_commit else None,
        "last_commit": repo_stats.last_commit.isoformat() if repo_stats.last_commit else None,
        "user_contribution_pct": (
            round(float(user_stats.userStatspercentages), 1)
            if user_stats and user_stats.userStatspercentages is not None
            else None
        ),
        "user_total_commits": user_stats.total_commits if user_stats else None,
        "commit_frequency": (
            round(float(user_stats.commitFrequency), 2)
            if user_stats and getattr(user_stats, "commitFrequency", None) is not None
            else None
        ),
        "commit_breakdown": commit_breakdown,
        "activity_breakdown": activity_breakdown,
        "daily_commits": daily_commits,
        "readme_excerpt": _read_readme(repo_path),
        "recent_commit_messages": _recent_commit_messages(repo_path, user_email),
        "recent_added_lines": additions[-8:],
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
    snapshots: list[dict[str, object]] | None = None,
    portfolio_dashboard: dict[str, object] | None = None,
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
    if output.portfolio is None:
        output.portfolio = ResumePortfolioModel.model_validate(
            _build_portfolio_summary(facts)
        )
    if output.portfolio_dashboard is None:
        dashboard_payload = portfolio_dashboard or _build_portfolio_dashboard(
            facts, snapshots or []
        )
        output.portfolio_dashboard = ResumePortfolioDashboardModel.model_validate(
            dashboard_payload
        )
    output.metadata.stage = stage
    output.metadata.models_used = list(models_used)
    output.metadata.model_used = models_used[-1] if models_used else None
    output.metadata.generation_time_seconds = generation_time_seconds
    output.metadata.errors = list(errors)
    output.metadata.quality_metrics = output.metadata.quality_metrics or {}
    return output


def _repair_json(text: str) -> str:
    """Fix common small-LLM JSON mistakes."""
    import re
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Fix missing commas between "value" "key" patterns
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)
    # Fix missing commas between ] "key" or } "key"
    text = re.sub(r'(\])\s*\n\s*"', r'],\n"', text)
    text = re.sub(r'(\})\s*\n\s*"', r'},\n"', text)
    # Fix missing commas between value and "key" on same line
    text = re.sub(r'(\d)\s+"', r'\1, "', text)
    return text


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from LLM text that may include reasoning."""
    text = text.strip()
    # Strip code fences
    if "```json" in text:
        text = text.split("```json", 1)[1]
    if "```" in text:
        text = text.split("```", 1)[0]
    # Find the first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    # Try parsing as-is first
    try:
        return json_lib.loads(text)
    except json_lib.JSONDecodeError:
        pass
    # Try repairing common mistakes
    repaired = _repair_json(text)
    return json_lib.loads(repaired)


async def generate_project_facts(
    repo_path: Path,
    *,
    user_email: str,
    model: str,
    progress: ProgressCallback | None = None,
) -> tuple[ProjectFacts, dict[str, object]]:
    """Return (facts, snapshot) so callers can pass snapshot to stage 2."""
    snapshot = _build_snapshot(repo_path, user_email)
    if progress:
        progress(f"Compiling facts for {repo_path.name}")
    max_attempts = 3
    last_error: Exception | None = None
    parsed: dict | None = None
    for attempt in range(max_attempts):
        raw = await query_text(
            build_project_facts_prompt(snapshot),
            model=model,
            system=FACTS_SYSTEM,
        )
        try:
            parsed = _extract_json(raw)
            break
        except (json_lib.JSONDecodeError, ValueError) as exc:
            last_error = exc
            if progress:
                remaining = max_attempts - attempt - 1
                if remaining > 0:
                    progress(f"Retrying facts for {repo_path.name} ({remaining} attempts left)")
                else:
                    progress(f"Facts extraction failed for {repo_path.name}")
    if parsed is None:
        raise last_error  # type: ignore[misc]
    facts = ProjectFacts.model_validate(parsed)
    facts.project_name = str(snapshot["project_name"])
    facts.primary_language = snapshot["primary_language"] or facts.primary_language
    facts.frameworks = list(snapshot["frameworks"]) or facts.frameworks
    facts.contribution_pct = snapshot["user_contribution_pct"] or facts.contribution_pct
    facts.commit_breakdown = dict(snapshot["commit_breakdown"]) or facts.commit_breakdown
    facts.first_commit = snapshot["first_commit"] or facts.first_commit
    facts.last_commit = snapshot["last_commit"] or facts.last_commit
    return facts, snapshot


def _derive_skills(facts: list[ProjectFacts]) -> str:
    """Build skills section programmatically from facts — no LLM needed."""
    languages: list[str] = []
    frameworks: list[str] = []
    tools: list[str] = []

    for fact in facts:
        if fact.primary_language and fact.primary_language not in languages:
            languages.append(fact.primary_language)
        for fw in fact.frameworks:
            if fw not in frameworks:
                frameworks.append(fw)
        for tech in fact.technologies:
            normalized = tech.strip()
            if normalized and normalized not in languages and normalized not in frameworks and normalized not in tools:
                tools.append(normalized)

    lines: list[str] = []
    if languages:
        lines.append(f"Languages: {', '.join(languages)}")
    if frameworks:
        lines.append(f"Frameworks: {', '.join(frameworks)}")
    if tools:
        lines.append(f"Tools & Technologies: {', '.join(tools[:12])}")
    return "\n".join(lines)


def _parse_project_content(text: str) -> tuple[str | None, list[str]]:
    """Parse LLM output for a single project into (description, bullets)."""
    text = text.strip()
    # Strip code fences if present
    if text.startswith("```"):
        first_nl = text.index("\n") if "\n" in text else len(text)
        text = text[first_nl + 1:]
    if text.endswith("```"):
        text = text[:text.rfind("```")]
    text = text.strip()

    description_lines: list[str] = []
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullets.append(stripped[2:].strip())
        elif stripped.startswith("#"):
            continue  # skip any heading the LLM might add
        elif stripped:
            description_lines.append(stripped)

    description = " ".join(description_lines) if description_lines else None
    return description, bullets


async def build_draft_output(
    facts: list[ProjectFacts],
    *,
    snapshots: list[dict[str, object]] | None = None,
    user_email: str,
    model: str,
    progress: ProgressCallback | None = None,
) -> ResumeOutputModel:
    """Build a draft resume using focused LLM calls per section."""
    snapshot_list = snapshots or []
    facts_dicts = [fact.model_dump() for fact in facts]

    # ── Per-project content (focused call per project) ──
    projects: list[ResumeProjectModel] = []
    for i, fact in enumerate(facts):
        snapshot = snapshot_list[i] if i < len(snapshot_list) else {}
        if progress:
            progress(f"Running project query for {fact.project_name}")

        raw = await query_text(
            build_project_content_prompt(facts_dicts[i], snapshot),
            model=model,
            system=PROJECT_CONTENT_SYSTEM,
        )
        description, bullets = _parse_project_content(raw)
        projects.append(
            ResumeProjectModel(
                name=fact.project_name,
                type=fact.project_type,
                primary_language=fact.primary_language,
                frameworks=list(fact.frameworks),
                contribution_pct=fact.contribution_pct,
                commit_breakdown=dict(fact.commit_breakdown),
                period=ResumeProjectPeriod(
                    first_commit=fact.first_commit,
                    last_commit=fact.last_commit,
                ),
                description=description,
                bullets=bullets,
                bullet_fact_ids=[],
                narrative=None,
            )
        )

    # ── Professional summary (one call, all facts) ──
    if progress:
        progress("Running portfolio query for summary")
    professional_summary = await query_text(
        build_summary_prompt(facts_dicts, snapshot_list),
        model=model,
        system=SUMMARY_SYSTEM,
    )

    # ── Developer profile (one call, all facts + activity data) ──
    if progress:
        progress("Running portfolio query for developer profile")
    developer_profile = await query_text(
        build_profile_prompt(facts_dicts, snapshot_list),
        model=model,
        system=PROFILE_SYSTEM,
    )

    # ── Skills (programmatic, no LLM) ──
    skills_section = _derive_skills(facts)

    return ResumeOutputModel(
        professional_summary=professional_summary.strip(),
        skills_section=skills_section,
        developer_profile=developer_profile.strip(),
        projects=projects,
    )


def _resume_to_markdown(output: ResumeOutputModel) -> str:
    """Convert a ResumeOutputModel back to markdown for the polish prompt."""
    lines: list[str] = []
    lines.append("## Professional Summary")
    lines.append(output.professional_summary or "(empty)")
    lines.append("")
    lines.append("## Technical Skills")
    lines.append(output.skills_section or "(empty)")
    lines.append("")
    lines.append("## Developer Profile")
    lines.append(output.developer_profile or "(empty)")
    lines.append("")
    lines.append("## Projects")
    for project in output.projects:
        lines.append(f"### {project.name}")
        if project.description:
            lines.append(project.description)
        for bullet in project.bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines)


async def build_polished_output(
    draft_output: ResumeOutputModel,
    feedback: GenerationFeedback,
    *,
    model: str,
    facts: list[ProjectFacts] | None = None,
) -> ResumeOutputModel:
    draft_md = _resume_to_markdown(draft_output)
    markdown = await query_text(
        build_polish_prompt(
            draft_markdown=draft_md,
            feedback=feedback.model_dump(),
        ),
        model=model,
        system=POLISH_SYSTEM,
    )
    return parse_resume_markdown(markdown, facts or [])


def finalize_output(
    output: ResumeOutputModel,
    *,
    facts: list[ProjectFacts],
    snapshots: list[dict[str, object]] | None = None,
    portfolio_dashboard: dict[str, object] | None = None,
    stage: str,
    models_used: list[str],
    generation_time_seconds: float,
    errors: list[str],
) -> dict[str, object]:
    normalized = _normalize_output(
        output,
        facts=facts,
        snapshots=snapshots,
        portfolio_dashboard=portfolio_dashboard,
        stage=stage,
        models_used=models_used,
        generation_time_seconds=generation_time_seconds,
        errors=errors,
    )
    return normalized.model_dump()
