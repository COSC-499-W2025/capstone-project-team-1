"""Read-only retrieval endpoints for skills, resume items, summaries, and activity."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .analyze import get_user_email
from .schemas import (
    ActivityHeatmapDateRange,
    ActivityHeatmapResponse,
    SkillChronologyItem,
    SkillResponse,
    ResumeItemResponse,
    SummaryResponse,
    UserAIIntelligenceSummaryResponse,
)
from ..generators import aggregate_skill_proficiency, proficiency_to_level
from ..db import (
    get_db,
    ProjectSkill,
    UserProjectSkill,
    UserRepoStat,
    Skill,
    RepoStat,
    ResumeItem,
    UploadedZip,
    UserAIntelligenceSummary,
)


router = APIRouter(tags=["retrieval"])


def _build_path_prefix_filter(column, prefixes: list[str]):
    return or_(*[or_(column == prefix, column.like(f"{prefix}/%")) for prefix in prefixes])


def _empty_heatmap(today_utc: date | None = None) -> ActivityHeatmapResponse:
    today = today_utc or datetime.now(UTC).date()
    return ActivityHeatmapResponse(
        daily_activity={},
        total_days_active=0,
        max_daily_commits=0,
        date_range=ActivityHeatmapDateRange(
            start_date=today - timedelta(days=363),
            end_date=today,
        ),
    )


def _resolve_portfolio_repo_paths(db: Session, portfolio_id: str) -> list[str]:
    portfolio_exists = (
        db.query(UploadedZip.id)
        .filter(UploadedZip.portfolio_id == portfolio_id)
        .first()
    )
    if portfolio_exists is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    extraction_prefixes = sorted(
        {
            uploaded_zip.extraction_path.rstrip("/")
            for uploaded_zip in (
                db.query(UploadedZip)
                .filter(UploadedZip.portfolio_id == portfolio_id)
                .filter(UploadedZip.extraction_path.isnot(None))
                .all()
            )
            if uploaded_zip.extraction_path and uploaded_zip.extraction_path.strip()
        }
    )
    if not extraction_prefixes:
        raise HTTPException(
            status_code=400,
            detail=(
                "Portfolio has no analyzed ZIPs yet. "
                "Run /analyze/{zip_id} for uploaded ZIPs first."
            ),
        )

    return sorted(
        {
            project_path.rstrip("/")
            for (project_path,) in (
                db.query(RepoStat.project_path)
                .filter(RepoStat.deleted_at.is_(None))
                .filter(_build_path_prefix_filter(RepoStat.project_path, extraction_prefixes))
                .all()
            )
            if project_path
        }
    )


def fetch_activity_heatmap(
    db: Session,
    *,
    project_paths: list[str] | None = None,
) -> ActivityHeatmapResponse:
    """Aggregate latest per-project daily commit data into a 364-day heatmap."""
    today_utc = datetime.now(UTC).date()
    if project_paths is not None and not project_paths:
        return _empty_heatmap(today_utc)

    latest_ids_query = db.query(func.max(UserRepoStat.id).label("id")).group_by(
        UserRepoStat.project_path
    )
    if project_paths:
        latest_ids_query = latest_ids_query.filter(
            UserRepoStat.project_path.in_(project_paths)
        )

    latest_ids = latest_ids_query.subquery()
    rows = (
        db.query(UserRepoStat.daily_commits)
        .join(latest_ids, UserRepoStat.id == latest_ids.c.id)
        .all()
    )

    aggregated: dict[date, int] = defaultdict(int)
    max_observed_commit_date: date | None = None

    for (daily_commits,) in rows:
        if not daily_commits:
            continue
        for raw_day, raw_count in daily_commits.items():
            try:
                observed_day = date.fromisoformat(str(raw_day))
                commit_count = int(raw_count)
            except (TypeError, ValueError):
                continue
            if commit_count < 0:
                continue
            aggregated[observed_day] += commit_count
            if max_observed_commit_date is None or observed_day > max_observed_commit_date:
                max_observed_commit_date = observed_day

    end_date = (
        max(today_utc, max_observed_commit_date)
        if max_observed_commit_date is not None
        else today_utc
    )
    start_date = end_date - timedelta(days=363)

    retained_daily_activity = {
        observed_day.isoformat(): count
        for observed_day, count in sorted(aggregated.items())
        if start_date <= observed_day <= end_date
    }

    return ActivityHeatmapResponse(
        daily_activity=retained_daily_activity,
        total_days_active=sum(
            1 for count in retained_daily_activity.values() if count > 0
        ),
        max_daily_commits=max(retained_daily_activity.values(), default=0),
        date_range=ActivityHeatmapDateRange(
            start_date=start_date,
            end_date=end_date,
        ),
    )


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

    skill_proficiencies: dict[int, list[float | None]] = defaultdict(list)

    # Pre-compute project counts and aggregated proficiencies in bulk.
    project_count_map: dict[int, int] | None = None
    if include_project_count:
        skill_repo_pairs: dict[int, set[int]] = defaultdict(set)

        for skill_id, repo_stat_id, proficiency in (
            db.query(
                ProjectSkill.skill_id,
                ProjectSkill.repo_stat_id,
                ProjectSkill.proficiency,
            )
            .join(RepoStat, ProjectSkill.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
        ):
            skill_repo_pairs[skill_id].add(repo_stat_id)
            skill_proficiencies[skill_id].append(proficiency)

        for skill_id, repo_stat_id, proficiency in (
            db.query(
                UserProjectSkill.skill_id,
                UserProjectSkill.repo_stat_id,
                UserProjectSkill.proficiency,
            )
            .join(RepoStat, UserProjectSkill.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
        ):
            skill_repo_pairs[skill_id].add(repo_stat_id)
            skill_proficiencies[skill_id].append(proficiency)

        project_count_map = {
            skill_id: len(repo_ids) for skill_id, repo_ids in skill_repo_pairs.items()
        }
    else:
        for skill_id, proficiency in (
            db.query(ProjectSkill.skill_id, ProjectSkill.proficiency)
            .join(RepoStat, ProjectSkill.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
        ):
            skill_proficiencies[skill_id].append(proficiency)

        for skill_id, proficiency in (
            db.query(UserProjectSkill.skill_id, UserProjectSkill.proficiency)
            .join(RepoStat, UserProjectSkill.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
        ):
            skill_proficiencies[skill_id].append(proficiency)

    result = []
    for skill in skills:
        project_count = None
        if project_count_map is not None:
            project_count = project_count_map.get(skill.id, 0)
        aggregate_proficiency = aggregate_skill_proficiency(
            skill_proficiencies.get(skill.id, [])
        )

        result.append(
            SkillResponse(
                id=skill.id,
                name=skill.name,
                category=skill.category,
                level=proficiency_to_level(aggregate_proficiency),
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
                level=proficiency_to_level(project_skill.proficiency),
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
                level=proficiency_to_level(user_skill.proficiency),
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


@router.get("/activity/heatmap", response_model=ActivityHeatmapResponse)
async def get_activity_heatmap(
    portfolio_id: str | None = Query(
        default=None,
        description="Optional portfolio UUID to scope the aggregated heatmap.",
    ),
    db: Session = Depends(get_db),
) -> ActivityHeatmapResponse:
    """Get aggregated daily commit activity for the configured user."""
    get_user_email(db)

    if portfolio_id is None:
        return fetch_activity_heatmap(db)

    normalized_portfolio_id = portfolio_id.strip()
    if not normalized_portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id cannot be empty.")

    project_paths = _resolve_portfolio_repo_paths(db, normalized_portfolio_id)
    return fetch_activity_heatmap(db, project_paths=project_paths)


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
