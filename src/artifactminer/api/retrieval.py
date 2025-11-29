"""Read-only retrieval endpoints for skills, resume items, and summaries.

These endpoints serve data for the final portfolio/resume generation.
All are GET-only with no side effects.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from sqlalchemy import or_

from .schemas import SkillChronologyItem, ResumeItemResponse, SummaryResponse
from ..db import (
    get_db,
    ProjectSkill,
    Skill,
    RepoStat,
    ResumeItem,
    UserAIntelligenceSummary,
)


router = APIRouter(tags=["retrieval"])


@router.get("/skills/chronology", response_model=List[SkillChronologyItem])
async def get_skill_chronology(
    db: Session = Depends(get_db),
) -> list[SkillChronologyItem]:
    """Get chronological list of skills ordered by when they were first demonstrated.

    Joins ProjectSkill -> Skill -> RepoStat to get skill info with project dates.
    Ordered by RepoStat.first_commit ASC (oldest first) to show skill progression.

    Milestone Req #19: Chronological list of skills.
    """
    results = (
        db.query(ProjectSkill, Skill, RepoStat)
        .join(Skill, ProjectSkill.skill_id == Skill.id)
        .join(RepoStat, ProjectSkill.repo_stat_id == RepoStat.id)
        .filter(RepoStat.deleted_at.is_(None))  # Exclude soft-deleted projects
        .order_by(RepoStat.first_commit.asc())
        .all()
    )

    return [
        SkillChronologyItem(
            date=repo_stat.first_commit,
            skill=skill.name,
            project=repo_stat.project_name,
            proficiency=project_skill.proficiency,
            category=skill.category,
        )
        for project_skill, skill, repo_stat in results
    ]


@router.get("/resume", response_model=List[ResumeItemResponse])
async def get_resume_items(
    project_id: int | None = Query(
        default=None,
        description="Filter resume items by project (repo_stat_id). "
        "Use this to show resume section for a specific project.",
    ),
    db: Session = Depends(get_db),
) -> list[ResumeItemResponse]:
    """Retrieve all resume items, sorted by project's last commit (newest first).

    Default sort: RepoStat.last_commit DESC (reverse-chronological for resumes).
    Optional filter: ?project_id=123 to get items for a specific project.

    Milestone Req #14: Retrieve previously generated resume items.
    Milestone Req #12: Output all key information for a project (via project_id filter).
    """
    query = db.query(ResumeItem, RepoStat).outerjoin(
        RepoStat, ResumeItem.repo_stat_id == RepoStat.id
    )

    # Exclude soft-deleted projects (but keep items with no repo_stat)
    query = query.filter(or_(RepoStat.deleted_at.is_(None), RepoStat.id.is_(None)))

    if project_id is not None:
        query = query.filter(ResumeItem.repo_stat_id == project_id)

    # Sort by last_commit DESC; items without repo_stat go last
    query = query.order_by(RepoStat.last_commit.desc().nullslast())

    results = query.all()

    return [
        ResumeItemResponse(
            id=resume_item.id,
            title=resume_item.title,
            content=resume_item.content,
            category=resume_item.category,
            project_name=repo_stat.project_name if repo_stat else None,
            created_at=resume_item.created_at,
        )
        for resume_item, repo_stat in results
    ]


@router.get("/summaries", response_model=List[SummaryResponse])
async def get_summaries(
    user_email: str = Query(
        ...,  # Required parameter
        description="User email to filter summaries. "
        "REQUIRED: Each user only sees their own AI-generated contribution summaries.",
    ),
    db: Session = Depends(get_db),
) -> list[SummaryResponse]:
    """Retrieve AI-generated contribution summaries for a specific user.

    Query param `user_email` is MANDATORY - summaries are user-scoped.
    This ensures users only retrieve their own portfolio data.

    Milestone Req #14: Retrieve portfolio info.
    """
    summaries = (
        db.query(UserAIntelligenceSummary)
        .filter(UserAIntelligenceSummary.user_email == user_email)
        .order_by(UserAIntelligenceSummary.generated_at.desc())
        .all()
    )

    return [
        SummaryResponse(
            id=s.id,
            repo_path=s.repo_path,
            user_email=s.user_email,
            summary_text=s.summary_text,
            generated_at=s.generated_at,
        )
        for s in summaries
    ]
