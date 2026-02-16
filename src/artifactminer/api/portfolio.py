"""Portfolio generation endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .analyze import get_consent_level, get_user_email
from .retrieval import fetch_skill_chronology
from .schemas import (
    PortfolioGenerationRequest,
    PortfolioGenerationResponse,
    PortfolioProjectItem,
    RepresentationPreferences,
    ResumeItemResponse,
    SkillChronologyItem,
    SummaryResponse,
)
from .views import get_prefs
from ..db import RepoStat, ResumeItem, UploadedZip, UserAIntelligenceSummary, get_db
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _normalize_tokens(values: list[str]) -> list[str]:
    return [value.strip() for value in values if str(value).strip()]


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
        .filter(or_(*[RepoStat.project_path.like(f"{p}%") for p in extraction_prefixes]))
        .all()
    )

    errors: list[str] = []
    selected_projects = _apply_preferences(projects, prefs, errors)
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
            .filter(or_(*[UserAIntelligenceSummary.repo_path.like(f"{path}%") for path in selected_paths]))
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

    return PortfolioGenerationResponse(
        success=bool(selected_projects),
        portfolio_id=portfolio_id,
        consent_level=consent_level,
        generated_at=datetime.now(UTC).replace(tzinfo=None),
        preferences=prefs,
        projects=[
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
            )
            for project in selected_projects
        ],
        resume_items=resume_items,
        summaries=summaries,
        skills_chronology=skills_chronology,
        errors=errors,
    )
