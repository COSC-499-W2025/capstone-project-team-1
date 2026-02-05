"""Project-related API endpoints (timeline, delete, etc.)."""

from datetime import timedelta, date, datetime, UTC
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from fastapi import Query
from .schemas import (
    ProjectTimelineItem,
    ProjectRankingItem,
    DeleteResponse,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectSkillItem,
    ProjectResumeItem,
    ProjectRoleUpdateRequest,
    ProjectRoleResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
    EvidenceDeleteResponse,
    EvidenceType,
)
from ..db import RepoStat, UserRepoStat, ProjectEvidence, get_db
from ..helpers.project_ranker import rank_projects


router = APIRouter(prefix="/projects", tags=["projects"])


def _get_latest_user_repo_stat_for_project(db: Session, repo_stat: RepoStat) -> UserRepoStat | None:
    return (
        db.query(UserRepoStat)
        .filter(
            UserRepoStat.project_name == repo_stat.project_name,
            UserRepoStat.project_path == repo_stat.project_path,
        )
        .order_by(UserRepoStat.id.desc())
        .first()
    )


def _get_active_project(project_id: int, db: Session) -> RepoStat:
    """Return the project or raise 404 if missing / soft-deleted."""
    project = (
        db.query(RepoStat)
        .filter(RepoStat.id == project_id, RepoStat.deleted_at.is_(None))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectResponse])
async def get_projects(
    limit: int | None = Query(default=None, ge=1, description="Max results to return"),
    offset: int | None = Query(default=0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> list[ProjectResponse]:
    """List all projects, excluding soft-deleted."""
    query = (
        db.query(RepoStat)
        .filter(RepoStat.deleted_at.is_(None))
        .order_by(RepoStat.created_at.desc())
    )

    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    return query.all()


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    """Get single project by ID with related skills and resume items."""
    repo_stat = (
        db.query(RepoStat)
        .filter(RepoStat.id == project_id, RepoStat.deleted_at.is_(None))
        .first()
    )
    if not repo_stat:
        raise HTTPException(status_code=404, detail="Project not found")

    latest_user_stat = _get_latest_user_repo_stat_for_project(db, repo_stat)
    role = latest_user_stat.user_role if latest_user_stat else None

    skills = [
        ProjectSkillItem(
            skill_name=ps.skill.name,
            category=ps.skill.category,
            proficiency=ps.proficiency,
        )
        for ps in repo_stat.project_skills
    ]

    resume_items = [
        ProjectResumeItem(
            id=ri.id,
            title=ri.title,
            content=ri.content,
            category=ri.category,
        )
        for ri in repo_stat.resume_items
    ]

    evidence = [
        EvidenceResponse(
            id=ev.id,
            type=ev.type,
            content=ev.content,
            source=ev.source,
            date=ev.date,
            project_id=repo_stat.id,
        )
        for ev in repo_stat.evidence
    ]

    return ProjectDetailResponse(
        id=repo_stat.id,
        project_name=repo_stat.project_name,
        project_path=repo_stat.project_path,
        languages=repo_stat.languages,
        frameworks=repo_stat.frameworks,
        first_commit=repo_stat.first_commit,
        last_commit=repo_stat.last_commit,
        is_collaborative=repo_stat.is_collaborative,
        total_commits=repo_stat.total_commits,
        primary_language=repo_stat.primary_language,
        ranking_score=repo_stat.ranking_score,
        health_score=repo_stat.health_score,
        role=role,
        skills=skills,
        resume_items=resume_items,
        evidence=evidence,
    )


@router.put("/{project_id}/role", response_model=ProjectRoleResponse)
@router.post("/{project_id}/role", response_model=ProjectRoleResponse)
async def upsert_project_role(
    project_id: int,
    payload: ProjectRoleUpdateRequest,
    db: Session = Depends(get_db),
) -> ProjectRoleResponse:
    """Set or update the user's role for a project."""
    repo_stat = (
        db.query(RepoStat)
        .filter(RepoStat.id == project_id, RepoStat.deleted_at.is_(None))
        .first()
    )
    if not repo_stat:
        raise HTTPException(status_code=404, detail="Project not found")

    normalized_role = payload.role.strip()
    if not normalized_role:
        raise HTTPException(status_code=422, detail="Role must not be empty")

    updated_rows = (
        db.query(UserRepoStat)
        .filter(
            UserRepoStat.project_name == repo_stat.project_name,
            UserRepoStat.project_path == repo_stat.project_path,
        )
        .update({UserRepoStat.user_role: normalized_role}, synchronize_session=False)
    )

    if updated_rows == 0:
        db.add(
            UserRepoStat(
                project_name=repo_stat.project_name,
                project_path=repo_stat.project_path,
                user_role=normalized_role,
            )
        )

    db.commit()

    return ProjectRoleResponse(
        project_id=repo_stat.id,
        project_name=repo_stat.project_name,
        role=normalized_role,
    )


@router.post(
    "/{project_id}/evidence",
    response_model=EvidenceResponse,
    status_code=201,
)
async def create_evidence(
    project_id: int,
    body: EvidenceCreateRequest,
    db: Session = Depends(get_db),
) -> EvidenceResponse:
    """Attach evidence of success to a project."""
    project = _get_active_project(project_id, db)

    evidence = ProjectEvidence(
        repo_stat_id=project.id,
        type=body.type,
        content=body.content,
        source=body.source,
        date=body.date,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return EvidenceResponse(
        id=evidence.id,
        type=evidence.type,
        content=evidence.content,
        source=evidence.source,
        date=evidence.date,
        project_id=project.id,
    )


@router.get("/{project_id}/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    project_id: int,
    type: EvidenceType | None = Query(default=None, description="Filter by evidence type"),
    db: Session = Depends(get_db),
) -> list[EvidenceResponse]:
    """List all evidence for a project, with optional type filter."""
    project = _get_active_project(project_id, db)

    query = db.query(ProjectEvidence).filter(
        ProjectEvidence.repo_stat_id == project.id
    )
    if type is not None:
        query = query.filter(ProjectEvidence.type == type)

    rows = query.all()
    return [
        EvidenceResponse(
            id=ev.id,
            type=ev.type,
            content=ev.content,
            source=ev.source,
            date=ev.date,
            project_id=project.id,
        )
        for ev in rows
    ]


@router.delete(
    "/{project_id}/evidence/{evidence_id}",
    response_model=EvidenceDeleteResponse,
)
async def delete_evidence(
    project_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
) -> EvidenceDeleteResponse:
    """Remove a single evidence item from a project."""
    project = _get_active_project(project_id, db)

    evidence = (
        db.query(ProjectEvidence)
        .filter(
            ProjectEvidence.id == evidence_id,
            ProjectEvidence.repo_stat_id == project.id,
        )
        .first()
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    db.delete(evidence)
    db.commit()

    return EvidenceDeleteResponse(success=True, deleted_id=evidence_id)


def fetch_project_timeline(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    active_only: bool | None = None,
    project_path_prefixes: list[str] | None = None,
) -> list[ProjectTimelineItem]:
    """Return stored project activity windows with optional filtering.

    `project_path_prefixes` filters RepoStat.project_path by SQL LIKE prefix (e.g. extraction root).
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    six_months_ago = now - timedelta(days=180)

    query = (
        db.query(RepoStat)
        .filter(
            RepoStat.first_commit.isnot(None),
            RepoStat.last_commit.isnot(None),
            RepoStat.deleted_at.is_(None),  # Exclude soft-deleted projects
        )
        .order_by(RepoStat.first_commit.asc())
    )

    if project_path_prefixes:
        query = query.filter(
            or_(*[RepoStat.project_path.like(f"{prefix}%") for prefix in project_path_prefixes])
        )

    repo_stats: List[RepoStat] = query.all()

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


@router.get("/timeline", response_model=List[ProjectTimelineItem])
async def get_project_timeline(
    start_date: date | None = None,
    end_date: date | None = None,
    active_only: bool | None = None,
    db: Session = Depends(get_db),
) -> list[ProjectTimelineItem]:
    return fetch_project_timeline(
        db,
        start_date=start_date,
        end_date=end_date,
        active_only=active_only,
    )


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
    repo_stat.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()

    return DeleteResponse(
        success=True,
        message=f"Project '{project_name}' deleted successfully",
        deleted_id=project_id,
    )

@router.get("/ranking", response_model=List[ProjectRankingItem])
async def get_project_ranking(
    projects_dir: str,
    user_email: str,
) -> list[ProjectRankingItem]:
    """Rank projects by user contribution percentage."""
    return rank_projects(projects_dir, user_email)
