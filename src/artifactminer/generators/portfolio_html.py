"""Portfolio HTML artifact generator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from artifactminer.api.analyze import get_consent_level, get_user_email
from artifactminer.api.portfolio import _apply_preferences, _build_path_boundary_filter
from artifactminer.api.retrieval import fetch_activity_heatmap, fetch_skill_chronology
from artifactminer.api.views import get_prefs
from artifactminer.db import (
    ProjectEvidence,
    RepoStat,
    ResumeItem,
    UploadedZip,
    UserAIntelligenceSummary,
    UserRepoStat,
)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
ACTIVITY_BUCKETS = ("code", "test", "docs", "config", "other")


def _iso(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _json_default(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _output_path() -> Path:
    return Path.home() / ".artifactminer" / "output" / "portfolio.html"


def _warn(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def _normalize_activity_breakdown(raw: Any) -> dict[str, int]:
    normalized = {bucket: 0 for bucket in ACTIVITY_BUCKETS}
    if not isinstance(raw, dict):
        return normalized

    alias_map = {
        "code": "code",
        "src": "code",
        "test": "test",
        "tests": "test",
        "docs": "docs",
        "documentation": "docs",
        "config": "config",
        "configuration": "config",
        "other": "other",
    }
    for key, value in raw.items():
        try:
            amount = (
                int(value.get("percentage", 0))
                if isinstance(value, dict)
                else int(value)
            )
        except (TypeError, ValueError):
            continue
        bucket = alias_map.get(str(key).strip().lower(), "other")
        normalized[bucket] += amount
    return normalized


def _resolve_portfolio_selection(
    db: Session, portfolio_id: str
) -> tuple[str, list[str], list[RepoStat], Any, str, str, list[str]]:
    normalized_portfolio_id = portfolio_id.strip()
    if not normalized_portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id cannot be empty.")

    portfolio_exists = (
        db.query(UploadedZip.id)
        .filter(UploadedZip.portfolio_id == normalized_portfolio_id)
        .first()
    )
    if portfolio_exists is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    uploaded_zips = (
        db.query(UploadedZip)
        .filter(UploadedZip.portfolio_id == normalized_portfolio_id)
        .filter(UploadedZip.extraction_path.isnot(None))
        .order_by(UploadedZip.uploaded_at.asc())
        .all()
    )
    if not uploaded_zips:
        raise HTTPException(
            status_code=400,
            detail=(
                "Portfolio has no analyzed ZIPs yet. "
                "Run /analyze/{zip_id} for uploaded ZIPs first."
            ),
        )

    extraction_roots = sorted(
        {
            uploaded_zip.extraction_path.rstrip("/")
            for uploaded_zip in uploaded_zips
            if uploaded_zip.extraction_path and uploaded_zip.extraction_path.strip()
        }
    )
    if not extraction_roots:
        raise HTTPException(
            status_code=400,
            detail=(
                "Portfolio has no analyzed ZIPs yet. "
                "Run /analyze/{zip_id} for uploaded ZIPs first."
            ),
        )

    projects = (
        db.query(RepoStat)
        .filter(RepoStat.deleted_at.is_(None))
        .filter(_build_path_boundary_filter(RepoStat.project_path, extraction_roots))
        .all()
    )

    prefs = get_prefs(db, normalized_portfolio_id)
    warnings: list[str] = []
    selected_projects = _apply_preferences(projects, prefs, warnings)
    if not selected_projects:
        raise HTTPException(
            status_code=400,
            detail="No projects available after applying preferences. No portfolio to generate.",
        )

    return (
        normalized_portfolio_id,
        extraction_roots,
        selected_projects,
        prefs,
        get_consent_level(db),
        get_user_email(db),
        warnings,
    )


def _latest_user_stats_by_path(
    db: Session, project_paths: list[str]
) -> dict[str, UserRepoStat]:
    stats = (
        db.query(UserRepoStat)
        .filter(UserRepoStat.project_path.in_(project_paths))
        .order_by(UserRepoStat.project_path.asc(), UserRepoStat.id.desc())
        .all()
    )
    latest: dict[str, UserRepoStat] = {}
    for stat in stats:
        latest.setdefault(stat.project_path, stat)
    return latest


def _match_project_path(candidate: str, project_paths: list[str]) -> str | None:
    matches = [
        project_path
        for project_path in project_paths
        if candidate == project_path or candidate.startswith(f"{project_path}/")
    ]
    return max(matches, key=len) if matches else None


def _latest_summaries_by_project_path(
    db: Session, project_paths: list[str], user_email: str
) -> dict[str, UserAIntelligenceSummary]:
    if not project_paths:
        return {}
    rows = (
        db.query(UserAIntelligenceSummary)
        .filter(UserAIntelligenceSummary.user_email == user_email)
        .filter(_build_path_boundary_filter(UserAIntelligenceSummary.repo_path, project_paths))
        .order_by(
            UserAIntelligenceSummary.generated_at.desc(),
            UserAIntelligenceSummary.id.desc(),
        )
        .all()
    )
    summaries: dict[str, UserAIntelligenceSummary] = {}
    for row in rows:
        project_path = _match_project_path(row.repo_path, project_paths)
        if project_path and project_path not in summaries:
            summaries[project_path] = row
    return summaries


def _group_resume_items(
    db: Session, project_ids: list[int]
) -> dict[int, list[dict[str, Any]]]:
    grouped = {project_id: [] for project_id in project_ids}
    rows = (
        db.query(ResumeItem, RepoStat)
        .join(RepoStat, ResumeItem.repo_stat_id == RepoStat.id)
        .filter(RepoStat.deleted_at.is_(None))
        .filter(ResumeItem.repo_stat_id.in_(project_ids))
        .order_by(
            RepoStat.last_commit.desc().nullslast(),
            ResumeItem.created_at.desc(),
            ResumeItem.id.desc(),
        )
        .all()
    )
    for item, _repo in rows:
        bucket = grouped.setdefault(item.repo_stat_id, [])
        if len(bucket) >= 3:
            continue
        bucket.append(
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "created_at": _iso(item.created_at),
            }
        )
    return grouped


def _group_evidence(
    db: Session, project_ids: list[int]
) -> dict[int, list[dict[str, Any]]]:
    grouped = {project_id: [] for project_id in project_ids}
    rows = (
        db.query(ProjectEvidence)
        .filter(ProjectEvidence.repo_stat_id.in_(project_ids))
        .order_by(
            ProjectEvidence.repo_stat_id.asc(),
            ProjectEvidence.date.desc().nullslast(),
            ProjectEvidence.id.desc(),
        )
        .all()
    )
    for row in rows:
        bucket = grouped.setdefault(row.repo_stat_id, [])
        if len(bucket) >= 3:
            continue
        bucket.append(
            {
                "id": row.id,
                "type": row.type,
                "content": row.content,
                "source": row.source,
                "date": _iso(row.date),
            }
        )
    return grouped


def build_portfolio_dashboard_data(db: Session, portfolio_id: str) -> dict[str, Any]:
    """Build the data object embedded into the self-contained HTML artifact."""
    (
        normalized_portfolio_id,
        _extraction_roots,
        selected_projects,
        prefs,
        consent_level,
        user_email,
        warnings,
    ) = _resolve_portfolio_selection(db, portfolio_id)

    selected_project_paths = [project.project_path.rstrip("/") for project in selected_projects]
    selected_project_ids = [project.id for project in selected_projects]

    latest_user_stats = _latest_user_stats_by_path(db, selected_project_paths)
    latest_summaries = _latest_summaries_by_project_path(
        db, selected_project_paths, user_email
    )
    resume_items_by_project = _group_resume_items(db, selected_project_ids)
    evidence_by_project = _group_evidence(db, selected_project_ids)

    chronology_items = fetch_skill_chronology(
        db, project_path_prefixes=selected_project_paths
    )
    skills_timeline = [
        {
            "date": _iso(item.date),
            "skill": item.skill,
            "project": item.project,
            "category": item.category,
            "proficiency": item.proficiency,
            "level": item.level.value,
        }
        for item in chronology_items
    ]
    if any(item["proficiency"] is None for item in skills_timeline):
        _warn(warnings, "Some skills are missing proficiency values.")

    heatmap = fetch_activity_heatmap(db, project_paths=selected_project_paths)
    heatmap_payload = {
        "daily_activity": heatmap.daily_activity,
        "total_days_active": heatmap.total_days_active,
        "max_daily_commits": heatmap.max_daily_commits,
        "date_range": {
            "start_date": _iso(heatmap.date_range.start_date),
            "end_date": _iso(heatmap.date_range.end_date),
        },
    }
    if heatmap.max_daily_commits == 0:
        _warn(warnings, "No activity data is available for the selected projects.")

    projects_payload: list[dict[str, Any]] = []
    for project in selected_projects:
        latest_user_stat = latest_user_stats.get(project.project_path)
        project_resume_items = resume_items_by_project.get(project.id, [])
        project_evidence = evidence_by_project.get(project.id, [])
        summary_row = latest_summaries.get(project.project_path)

        if summary_row is None:
            _warn(warnings, "Some selected projects do not have summaries yet.")
        if not project_resume_items:
            _warn(warnings, "Some selected projects do not have resume items yet.")
        if not project_evidence:
            _warn(warnings, "Some selected projects do not have evidence highlights yet.")

        projects_payload.append(
            {
                "id": project.id,
                "project_name": project.project_name,
                "project_path": project.project_path,
                "languages": project.languages or [],
                "frameworks": project.frameworks or [],
                "first_commit": _iso(project.first_commit),
                "last_commit": _iso(project.last_commit),
                "ranking_score": project.ranking_score,
                "health_score": project.health_score,
                "user_role": latest_user_stat.user_role if latest_user_stat else None,
                "contribution_pct": (
                    latest_user_stat.userStatspercentages if latest_user_stat else None
                ),
                "activity_breakdown": _normalize_activity_breakdown(
                    latest_user_stat.activity_breakdown if latest_user_stat else None
                ),
                "thumbnail_url": project.thumbnail_url,
                "resume_items": project_resume_items,
                "evidence": project_evidence,
                "summary_text": summary_row.summary_text if summary_row else "",
            }
        )

    unique_languages = sorted(
        {
            language
            for project in selected_projects
            for language in (project.languages or [])
            if language
        }
    )
    unique_frameworks = sorted(
        {
            framework
            for project in selected_projects
            for framework in (project.frameworks or [])
            if framework
        }
    )
    unique_skill_names = sorted({item["skill"] for item in skills_timeline if item["skill"]})
    unique_skill_categories = sorted(
        {item["category"] for item in skills_timeline if item["category"]}
    )

    build_portfolio_dashboard_data.last_warnings = warnings
    return {
        "meta": {
            "portfolio_id": normalized_portfolio_id,
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "consent_level": consent_level,
            "user_email": user_email,
            "title": "Developer Portfolio",
        },
        "preferences": prefs.model_dump(mode="json"),
        "stats": {
            "total_projects": len(selected_projects),
            "total_skills": len(unique_skill_names),
            "total_commits": sum(
                (latest_user_stats.get(project.project_path).total_commits or 0)
                if latest_user_stats.get(project.project_path)
                else (project.total_commits or 0)
                for project in selected_projects
            ),
            "active_days": heatmap.total_days_active,
            "languages": len(unique_languages),
            "frameworks": len(unique_frameworks),
        },
        "filters": {
            "languages": unique_languages,
            "skill_categories": unique_skill_categories,
        },
        "skills_timeline": skills_timeline,
        "heatmap": heatmap_payload,
        "projects": projects_payload,
        "top_projects": [dict(project) for project in projects_payload[:3]],
    }


build_portfolio_dashboard_data.last_warnings = []


def write_portfolio_html(data: dict[str, Any]) -> Path:
    """Render the portfolio template and write it to the fixed output path."""
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(("html",)),
    )
    template = environment.get_template("portfolio.html")
    html = template.render(
        title=data["meta"]["title"],
        data=data,
        data_json=json.dumps(data, default=_json_default, separators=(",", ":")),
    )

    output_path = _output_path().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def generate_portfolio_html(db: Session, portfolio_id: str) -> Path:
    """Generate the portfolio HTML artifact and return its absolute output path."""
    data = build_portfolio_dashboard_data(db, portfolio_id)
    generate_portfolio_html.last_warnings = list(
        getattr(build_portfolio_dashboard_data, "last_warnings", [])
    )
    return write_portfolio_html(data)


generate_portfolio_html.last_warnings = []
