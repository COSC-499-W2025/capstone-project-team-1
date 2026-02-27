"""Portfolio generation endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .analyze import get_consent_level, get_user_email
from .retrieval import fetch_skill_chronology
from .schemas import (
    PortfolioDisplayResponse,
    PortfolioEvidenceItem,
    PortfolioGenerationRequest,
    PortfolioGenerationResponse,
    PortfolioProjectItem,
    RepresentationPreferences,
    ResumeItemResponse,
    SkillChronologyItem,
    SummaryResponse,
)
from .views import get_prefs
from ..db import (
    ProjectEvidence,
    RepoStat,
    ResumeItem,
    UploadedZip,
    UserAIntelligenceSummary,
    UserRepoStat,
    get_db,
)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _normalize_tokens(values: list[str | int]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _project_tokens(project: RepoStat) -> set[str]:
    return {str(project.id), project.project_name}


def _project_sort_key(project: RepoStat) -> tuple[bool, float, bool, float, int]:
    ts = project.last_commit.timestamp() if project.last_commit else 0.0
    return (
        project.ranking_score is None,
        -(project.ranking_score or 0.0),
        project.last_commit is None,
        -ts,
        project.id,
    )


def _build_path_boundary_filter(column, paths: list[str]):
    return or_(*[or_(column == path, column.like(f"{path}/%")) for path in paths])


def _build_portfolio_project_items(
    projects: list[RepoStat], db: Session
) -> list[PortfolioProjectItem]:
    """Build complete PortfolioProjectItem objects with role, thumbnail, and evidence."""
    project_paths = [project.project_path for project in projects]
    project_ids = [project.id for project in projects]
    
    # Fetch user roles for all projects in one query
    # Note: Multiple UserRepoStat entries can exist per project_path (e.g., multiple files).
    # We use a dict to keep only one role per project (last one seen, which SQLAlchemy returns deterministically).
    user_roles_map = {}
    if project_paths:
        user_roles = (
            db.query(UserRepoStat)
            .filter(UserRepoStat.project_path.in_(project_paths))
            .order_by(UserRepoStat.project_path, UserRepoStat.id)
            .all()
        )
        user_roles_map = {ur.project_path: ur.user_role for ur in user_roles}
    
    # Fetch evidence for all projects in one query
    evidence_map = {}
    if project_ids:
        evidence_items = (
            db.query(ProjectEvidence)
            .filter(ProjectEvidence.repo_stat_id.in_(project_ids))
            .order_by(ProjectEvidence.repo_stat_id, ProjectEvidence.date.desc().nullslast(), ProjectEvidence.id.desc())
            .all()
        )
        for ev in evidence_items:
            if ev.repo_stat_id not in evidence_map:
                evidence_map[ev.repo_stat_id] = []
            evidence_map[ev.repo_stat_id].append(
                PortfolioEvidenceItem(
                    id=ev.id,
                    type=ev.type,
                    content=ev.content,
                    source=ev.source,
                    date=ev.date,
                )
            )
    
    # Build portfolio project items
    return [
        PortfolioProjectItem(
            id=project.id,
            project_name=project.project_name,
            project_path=project.project_path,
            languages=project.languages,
            frameworks=project.frameworks,
            first_commit=project.first_commit,
            last_commit=project.last_commit,
            ranking_score=project.ranking_score,
            health_score=project.health_score,
            thumbnail_url=project.thumbnail_url,
            user_role=user_roles_map.get(project.project_path),
            evidence=evidence_map.get(project.id, []),
        )
        for project in projects
    ]


def _apply_preferences(
    projects: list[RepoStat], prefs: RepresentationPreferences, errors: list[str]
) -> list[RepoStat]:
    ordered = sorted(projects, key=_project_sort_key)
    showcase = set(_normalize_tokens(prefs.showcase_project_ids))
    if showcase:
        matching = [p for p in ordered if _project_tokens(p) & showcase]
        if matching:
            ordered = matching
        else:
            errors.append("No projects matched showcase_project_ids; returning all projects.")

    order_tokens = _normalize_tokens(prefs.project_order)
    if not order_tokens:
        return ordered

    order_index = {token: idx for idx, token in enumerate(order_tokens)}
    matched = {
        token
        for project in ordered
        for token in _project_tokens(project)
        if token in order_index
    }
    missing = [token for token in order_tokens if token not in matched]
    if missing:
        errors.append(f"project_order references unknown projects: {missing}")

    return sorted(
        ordered,
        key=lambda project: (
            min(
                (
                    order_index[token]
                    for token in _project_tokens(project)
                    if token in order_index
                ),
                default=len(order_index) + 1,
            ),
            _project_sort_key(project),
        ),
    )


@router.post("/generate", response_model=PortfolioGenerationResponse)
async def generate_portfolio(
    request: PortfolioGenerationRequest, db: Session = Depends(get_db)
) -> PortfolioGenerationResponse:
    portfolio_id = request.portfolio_id.strip()
    if not portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id cannot be empty.")

    portfolio_exists = (
        db.query(UploadedZip.id)
        .filter(UploadedZip.portfolio_id == portfolio_id)
        .first()
    )
    if not portfolio_exists:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    zips = (
        db.query(UploadedZip)
        .filter(UploadedZip.portfolio_id == portfolio_id)
        .filter(UploadedZip.extraction_path.isnot(None))
        .order_by(UploadedZip.uploaded_at.asc())
        .all()
    )
    if not zips:
        raise HTTPException(
            status_code=400,
            detail="Portfolio has no analyzed ZIPs yet. Run /analyze/{zip_id} for uploaded ZIPs first.",
        )

    extraction_prefixes = sorted(
        {
            z.extraction_path.rstrip("/")
            for z in zips
            if z.extraction_path and z.extraction_path.strip()
        }
    )
    if not extraction_prefixes:
        raise HTTPException(
            status_code=400,
            detail="Portfolio has no analyzed ZIPs yet. Run /analyze/{zip_id} for uploaded ZIPs first.",
        )

    prefs = get_prefs(db, portfolio_id)
    consent_level = get_consent_level(db)
    user_email = get_user_email(db)

    projects = (
        db.query(RepoStat)
        .filter(RepoStat.deleted_at.is_(None))
        .filter(_build_path_boundary_filter(RepoStat.project_path, extraction_prefixes))
        .all()
    )

    errors: list[str] = []
    selected_projects = _apply_preferences(projects, prefs, errors)
    if not selected_projects:
        raise HTTPException(
            status_code=400,
            detail="No projects available after applying preferences. No portfolio to generate.",
        )
    
    selected_project_ids = [project.id for project in selected_projects]
    selected_paths = sorted({project.project_path.rstrip("/") for project in selected_projects})

    resume_items: list[ResumeItemResponse] = []
    if selected_project_ids:
        rows = (
            db.query(ResumeItem, RepoStat)
            .join(RepoStat, ResumeItem.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
            .filter(ResumeItem.repo_stat_id.in_(selected_project_ids))
            .order_by(
                RepoStat.last_commit.desc().nullslast(),
                ResumeItem.created_at.desc(),
                ResumeItem.id.desc(),
            )
            .all()
        )
        resume_items = [
            ResumeItemResponse(
                id=item.id,
                title=item.title,
                content=item.content,
                category=item.category,
                project_name=repo.project_name,
                created_at=item.created_at,
            )
            for item, repo in rows
        ]

    summaries: list[SummaryResponse] = []
    if selected_paths:
        summary_rows = (
            db.query(UserAIntelligenceSummary)
            .filter(UserAIntelligenceSummary.user_email == user_email)
            .filter(
                _build_path_boundary_filter(
                    UserAIntelligenceSummary.repo_path, selected_paths
                )
            )
            .order_by(UserAIntelligenceSummary.generated_at.desc())
            .all()
        )
        summaries = [
            SummaryResponse(
                id=row.id,
                repo_path=row.repo_path,
                user_email=row.user_email,
                summary_text=row.summary_text,
                generated_at=row.generated_at,
            )
            for row in summary_rows
        ]

    skills_chronology: list[SkillChronologyItem] = []
    if selected_paths:
        skills_chronology = fetch_skill_chronology(db, project_path_prefixes=selected_paths)

    project_items = _build_portfolio_project_items(selected_projects, db)

    return PortfolioGenerationResponse(
        success=bool(selected_projects),
        portfolio_id=portfolio_id,
        consent_level=consent_level,
        generated_at=datetime.now(UTC).replace(tzinfo=None),
        preferences=prefs,
        projects=project_items,
        resume_items=resume_items,
        summaries=summaries,
        skills_chronology=skills_chronology,
        errors=errors,
    )


@router.get("/{portfolio_id}", response_model=PortfolioDisplayResponse)
async def get_portfolio(
    portfolio_id: str, db: Session = Depends(get_db)
) -> PortfolioDisplayResponse:
    """Get portfolio display data by ID.
    
    Returns portfolio showcase with projects, summaries, skills, and project details.
    Includes project role, thumbnail, and evidence for each project.
    Respects RepresentationPrefs for ordering and filtering.
    """
    portfolio_id = portfolio_id.strip()
    if not portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id cannot be empty.")

    # Verify portfolio exists
    portfolio_exists = (
        db.query(UploadedZip.id)
        .filter(UploadedZip.portfolio_id == portfolio_id)
        .first()
    )
    if not portfolio_exists:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    # Get analyzed ZIPs for this portfolio
    zips = (
        db.query(UploadedZip)
        .filter(UploadedZip.portfolio_id == portfolio_id)
        .filter(UploadedZip.extraction_path.isnot(None))
        .order_by(UploadedZip.uploaded_at.asc())
        .all()
    )
    if not zips:
        raise HTTPException(
            status_code=400,
            detail="Portfolio has no analyzed ZIPs yet. Run /analyze/{zip_id} for uploaded ZIPs first.",
        )

    extraction_prefixes = sorted(
        {
            z.extraction_path.rstrip("/")
            for z in zips
            if z.extraction_path and z.extraction_path.strip()
        }
    )
    if not extraction_prefixes:
        raise HTTPException(
            status_code=400,
            detail="Portfolio has no analyzed ZIPs yet. Run /analyze/{zip_id} for uploaded ZIPs first.",
        )

    prefs = get_prefs(db, portfolio_id)
    consent_level = get_consent_level(db)
    user_email = get_user_email(db)

    # Fetch all projects for this portfolio
    projects = (
        db.query(RepoStat)
        .filter(RepoStat.deleted_at.is_(None))
        .filter(_build_path_boundary_filter(RepoStat.project_path, extraction_prefixes))
        .all()
    )

    # Apply preferences (ordering and filtering)
    errors: list[str] = []
    selected_projects = _apply_preferences(projects, prefs, errors)
    if not selected_projects:
        raise HTTPException(
            status_code=400,
            detail="No projects available after applying preferences. No portfolio to generate.",
        )
    
    selected_project_ids = [project.id for project in selected_projects]
    selected_paths = sorted({project.project_path.rstrip("/") for project in selected_projects})

    # Fetch resume items
    resume_items: list[ResumeItemResponse] = []
    if selected_project_ids:
        rows = (
            db.query(ResumeItem, RepoStat)
            .join(RepoStat, ResumeItem.repo_stat_id == RepoStat.id)
            .filter(RepoStat.deleted_at.is_(None))
            .filter(ResumeItem.repo_stat_id.in_(selected_project_ids))
            .order_by(
                RepoStat.last_commit.desc().nullslast(),
                ResumeItem.created_at.desc(),
                ResumeItem.id.desc(),
            )
            .all()
        )
        resume_items = [
            ResumeItemResponse(
                id=item.id,
                title=item.title,
                content=item.content,
                category=item.category,
                project_name=repo.project_name,
                created_at=item.created_at,
            )
            for item, repo in rows
        ]

    # Fetch summaries
    summaries: list[SummaryResponse] = []
    if selected_paths:
        summary_rows = (
            db.query(UserAIntelligenceSummary)
            .filter(UserAIntelligenceSummary.user_email == user_email)
            .filter(
                _build_path_boundary_filter(
                    UserAIntelligenceSummary.repo_path, selected_paths
                )
            )
            .order_by(UserAIntelligenceSummary.generated_at.desc())
            .all()
        )
        summaries = [
            SummaryResponse(
                id=row.id,
                repo_path=row.repo_path,
                user_email=row.user_email,
                summary_text=row.summary_text,
                generated_at=row.generated_at,
            )
            for row in summary_rows
        ]

    # Fetch skills chronology
    skills_chronology: list[SkillChronologyItem] = []
    if selected_paths:
        skills_chronology = fetch_skill_chronology(db, project_path_prefixes=selected_paths)

    # Build complete project items with role, thumbnail, and evidence
    project_items = _build_portfolio_project_items(selected_projects, db)

    return PortfolioDisplayResponse(
        success=bool(selected_projects),
        portfolio_id=portfolio_id,
        consent_level=consent_level,
        generated_at=datetime.now(UTC).replace(tzinfo=None),
        preferences=prefs,
        projects=project_items,
        resume_items=resume_items,
        summaries=summaries,
        skills_chronology=skills_chronology,
        errors=errors,
    )
