"""Project-related API endpoints (timeline, delete, etc.)."""

from datetime import datetime, timedelta, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .schemas import ProjectTimelineItem, DeleteResponse
from ..db import RepoStat, get_db


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
        .filter(
            RepoStat.first_commit.isnot(None),
            RepoStat.last_commit.isnot(None),
            RepoStat.deleted_at.is_(None),  # Exclude soft-deleted projects
        )
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
                id=stat.id,
                project_name=stat.project_name,
                first_commit=first_commit,
                last_commit=last_commit,
                duration_days=duration_days,
                was_active=was_active,
            )
        )

    return timeline_items


@router.delete("/{project_id}", response_model=DeleteResponse)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """Soft-delete a project (RepoStat) record by ID.

    Sets deleted_at timestamp rather than removing the record.
    Related ProjectSkill, UserProjectSkill, and ResumeItem records
    are preserved but filtered out by other endpoints.

    No files on disk are affected - this only modifies the database.
    """
    # Find RepoStat by ID (only non-deleted)
    repo_stat = (
        db.query(RepoStat)
        .filter(RepoStat.id == project_id, RepoStat.deleted_at.is_(None))
        .first()
    )

    # Handle not found (or already deleted)
    if not repo_stat:
        raise HTTPException(status_code=404, detail="Project not found")

    # Soft delete - set timestamp
    project_name = repo_stat.project_name
    repo_stat.deleted_at = datetime.utcnow()
    db.commit()

    return DeleteResponse(
        success=True,
        message=f"Project '{project_name}' deleted successfully",
        deleted_id=project_id,
    )
