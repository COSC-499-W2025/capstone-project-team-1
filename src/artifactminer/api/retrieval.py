"""Read-only retrieval endpoints for skills, resume items, and summaries.

These endpoints serve data for the final portfolio/resume generation.
All are GET-only with no side effects.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from sqlalchemy import or_, func
from collections import defaultdict

from .schemas import (
    SkillChronologyItem,
    SkillResponse,
    ResumeItemResponse,
    ResumeItemEditRequest,
    SummaryResponse,
    UserAIIntelligenceSummaryResponse,
)
from ..db import (
    get_db,
    ProjectSkill,
    UserProjectSkill,
    UserRepoStat,
    Skill,
    RepoStat,
    ResumeItem,
    UserAIntelligenceSummary,
)


router = APIRouter(tags=["retrieval"])


@router.get("/skills", response_model=List[SkillResponse])
async def get_skills(
    category: str | None = Query(
        default=None,
        description="Filter skills by category (e.g., 'Programming Languages').",
    ),
    include_project_count: bool = Query(
        default=False,
        description="Include count of projects using each skill.",
    ),
    db: Session = Depends(get_db),
) -> list[SkillResponse]:
    """Get all skills from the Skill table.

    Returns a list of all skills with optional filtering by category.
    Optionally includes an aggregate count of projects using each skill.
    """
    query = db.query(Skill)

    if category:
        query = query.filter(Skill.category == category)

    query = query.order_by(Skill.name.asc())
    skills = query.all()

    # Pre-compute project counts in bulk (2 queries total) to avoid N+1
    project_count_map: dict[int, int] | None = None
    if include_project_count:
        # Collect (skill_id, repo_stat_id) pairs from both tables in two queries
        skill_repo_pairs: dict[int, set[int]] = defaultdict(set)

        for skill_id, repo_stat_id in (
            db.query(ProjectSkill.skill_id, ProjectSkill.repo_stat_id)
            .join(RepoStat, ProjectSkill.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
        ):
            skill_repo_pairs[skill_id].add(repo_stat_id)

        for skill_id, repo_stat_id in (
            db.query(UserProjectSkill.skill_id, UserProjectSkill.repo_stat_id)
            .join(RepoStat, UserProjectSkill.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
        ):
            skill_repo_pairs[skill_id].add(repo_stat_id)

        project_count_map = {
            skill_id: len(repo_ids) for skill_id, repo_ids in skill_repo_pairs.items()
        }

    result = []
    for skill in skills:
        project_count = None
        if project_count_map is not None:
            project_count = project_count_map.get(skill.id, 0)

        result.append(
            SkillResponse(
                id=skill.id,
                name=skill.name,
                category=skill.category,
                project_count=project_count,
            )
        )

    return result


def fetch_skill_chronology(
    db: Session,
    *,
    project_path_prefixes: list[str] | None = None,
) -> list[SkillChronologyItem]:
    """Get chronological list of skills ordered by when they were first demonstrated.

    `project_path_prefixes` filters RepoStat.project_path by SQL LIKE prefix (e.g. extraction root).
    """
    items: list[SkillChronologyItem] = []

    project_query = (
        db.query(ProjectSkill, Skill, RepoStat)
        .join(Skill, ProjectSkill.skill_id == Skill.id)
        .join(RepoStat, ProjectSkill.repo_stat_id == RepoStat.id)
        .filter(RepoStat.deleted_at.is_(None))
    )

    user_query = (
        db.query(UserProjectSkill, Skill, RepoStat)
        .join(Skill, UserProjectSkill.skill_id == Skill.id)
        .join(RepoStat, UserProjectSkill.repo_stat_id == RepoStat.id)
        .filter(RepoStat.deleted_at.is_(None))
    )

    if project_path_prefixes:
        path_filter = or_(
            *[
                RepoStat.project_path.like(f"{prefix}%")
                for prefix in project_path_prefixes
            ]
        )
        project_query = project_query.filter(path_filter)
        user_query = user_query.filter(path_filter)

    project_results = project_query.all()
    user_results = user_query.all()

    for project_skill, skill, repo_stat in project_results:
        items.append(
            SkillChronologyItem(
                date=repo_stat.first_commit,
                skill=skill.name,
                project=repo_stat.project_name,
                proficiency=project_skill.proficiency,
                category=skill.category,
            )
        )

    for user_skill, skill, repo_stat in user_results:
        items.append(
            SkillChronologyItem(
                date=repo_stat.first_commit,
                skill=skill.name,
                project=repo_stat.project_name,
                proficiency=user_skill.proficiency,
                category=skill.category,
            )
        )

    items.sort(key=lambda item: item.date or datetime.max)
    return items


@router.get("/skills/chronology", response_model=List[SkillChronologyItem])
async def get_skill_chronology(
    db: Session = Depends(get_db),
) -> list[SkillChronologyItem]:
    """Get chronological list of skills ordered by when they were first demonstrated.

    Joins ProjectSkill -> Skill -> RepoStat to get skill info with project dates.
    Ordered by RepoStat.first_commit ASC (oldest first) to show skill progression.

    Milestone Req #19: Chronological list of skills.
    """
    return fetch_skill_chronology(db)


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

    role_cache: dict[tuple[str, str], str | None] = {}
    response_items: list[ResumeItemResponse] = []

    for resume_item, repo_stat in results:
        role: str | None = None
        if repo_stat:
            key = (repo_stat.project_name, repo_stat.project_path)
            if key not in role_cache:
                latest_user_stat = (
                    db.query(UserRepoStat)
                    .filter(
                        UserRepoStat.project_name == repo_stat.project_name,
                        UserRepoStat.project_path == repo_stat.project_path,
                    )
                    .order_by(UserRepoStat.id.desc())
                    .first()
                )
                role_cache[key] = (
                    latest_user_stat.user_role if latest_user_stat else None
                )
            role = role_cache[key]

        response_items.append(
            ResumeItemResponse(
                id=resume_item.id,
                title=resume_item.title,
                content=resume_item.content,
                category=resume_item.category,
                project_name=repo_stat.project_name if repo_stat else None,
                role=role,
                created_at=resume_item.created_at,
            )
        )

    return response_items


@router.get("/resume/{resume_id}", response_model=ResumeItemResponse)
async def get_resume_item_by_id(
    resume_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> ResumeItemResponse:
    """Retrieve a single resume item by its ID.

    Returns 404 if the item doesn't exist or its associated project is soft-deleted.
    Orphan items (no associated project) are returned with project_name: null.
    """
    result = (
        db.query(ResumeItem, RepoStat)
        .outerjoin(RepoStat, ResumeItem.repo_stat_id == RepoStat.id)
        .filter(ResumeItem.id == resume_id)
        .first()
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Resume item not found")

    resume_item, repo_stat = result

    if repo_stat is not None and repo_stat.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Resume item not found")

    return ResumeItemResponse(
        id=resume_item.id,
        title=resume_item.title,
        content=resume_item.content,
        category=resume_item.category,
        project_name=repo_stat.project_name if repo_stat else None,
        created_at=resume_item.created_at,
    )


@router.post("/resume/{resume_id}/edit", response_model=ResumeItemResponse)
async def edit_resume_item(
    resume_id: int = Path(..., gt=0),
    request: ResumeItemEditRequest = Body(...),
    db: Session = Depends(get_db),
) -> ResumeItemResponse:
    """Edit a resume item's title, content, and/or category.

    Accepts partial updates - only provided fields are updated.
    Returns 404 if the item doesn't exist or its associated project is soft-deleted.
    """
    result = (
        db.query(ResumeItem, RepoStat)
        .outerjoin(RepoStat, ResumeItem.repo_stat_id == RepoStat.id)
        .filter(ResumeItem.id == resume_id)
        .first()
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Resume item not found")

    resume_item, repo_stat = result

    if repo_stat is not None and repo_stat.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Resume item not found")

    if request.title is not None:
        resume_item.title = request.title
    if request.content is not None:
        resume_item.content = request.content
    if request.category is not None:
        resume_item.category = request.category

    db.commit()
    db.refresh(resume_item)

    return ResumeItemResponse(
        id=resume_item.id,
        title=resume_item.title,
        content=resume_item.content,
        category=resume_item.category,
        project_name=repo_stat.project_name if repo_stat else None,
        created_at=resume_item.created_at,
    )


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


@router.get("/AI_summaries", response_model=List[UserAIIntelligenceSummaryResponse])
async def get_AI_summaries(
    user_email: str,
    repo_path: str,
    db: Session = Depends(get_db),
):
    summaries_query = (
        db.query(UserAIntelligenceSummary)
        .filter(
            UserAIntelligenceSummary.user_email == user_email,
            UserAIntelligenceSummary.repo_path.like(f"{repo_path}%"),
        )
        .all()
    )
    return [
        UserAIIntelligenceSummaryResponse(
            user_email=s.user_email, repo_path=s.repo_path, summary_text=s.summary_text
        )
        for s in summaries_query
    ]
