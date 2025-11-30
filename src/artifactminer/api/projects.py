"""Project-related API endpoints (timeline, etc.)."""

from datetime import datetime, timedelta, date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .schemas import ProjectTimelineItem, ProjectRankingItem
from ..db import RepoStat, get_db
from ..helpers.project_ranker import rank_projects


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/timeline", response_model=List[ProjectTimelineItem])
async def get_project_timeline(
    start_date: date | None = None,
    end_date: date | None = None,
    active_only: bool | None = None,
    db: Session = Depends(get_db),
) -> list[ProjectTimelineItem]:
    """Return stored project activity windows with optional filtering."""

    now = datetime.utcnow()
    six_months_ago = now - timedelta(days=180)

    repo_stats: List[RepoStat] = (
        db.query(RepoStat)
        .filter(RepoStat.first_commit.isnot(None), RepoStat.last_commit.isnot(None))
        .order_by(RepoStat.first_commit.asc())
        .all()
    )

    timeline_items: list[ProjectTimelineItem] = []
    for stat in repo_stats:
        first_commit = stat.first_commit
        last_commit = stat.last_commit
        if not first_commit or not last_commit:
            continue

        if start_date and first_commit.date() < start_date:
            continue
        if end_date and first_commit.date() > end_date:
            continue

        was_active = last_commit >= six_months_ago
        if active_only and not was_active:
            continue

        duration_days = (last_commit - first_commit).days

        timeline_items.append(
            ProjectTimelineItem(
                project_name=stat.project_name,
                first_commit=first_commit,
                last_commit=last_commit,
                duration_days=duration_days,
                was_active=was_active,
            )
        )

    return timeline_items


@router.get("/ranking", response_model=List[ProjectRankingItem])
async def get_project_ranking(
    projects_dir: str,
    user_email: str,
) -> list[ProjectRankingItem]:
    """Rank projects by user contribution percentage."""
    return rank_projects(projects_dir, user_email)
