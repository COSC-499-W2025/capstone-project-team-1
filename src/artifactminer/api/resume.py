"""Resume generation endpoints for on-demand resume item creation."""

from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, RepoStat, ResumeItem
from .schemas import ResumeItemResponse, ResumeGenerationRequest, ResumeGenerationResponse
from .analyze import get_user_email, get_consent_level
from ..skills.deep_analysis import DeepRepoAnalyzer
from ..skills.persistence import persist_extracted_skills
from ..evidence.orchestrator import persist_insights_as_project_evidence
from ..RepositoryIntelligence.repo_intelligence_user import collect_user_additions

router = APIRouter(
    prefix="/resume",
    tags=["resume"],
)


async def generate_resume_for_project(
    db: Session,
    repo_stat: RepoStat,
    user_email: str,
    consent_level: str,
    regenerate: bool = False,
) -> tuple[list[ResumeItem], list[str]]:
    """Generate resume items for a single project.
    
    Extracts logic from analyze.py to allow on-demand resume generation.
    Runs DeepRepoAnalyzer on a project and persists insights as project evidence.
    
    Args:
        db: Database session
        repo_stat: RepoStat model for the project
        user_email: User's email for contribution tracking
        consent_level: Consent level for LLM usage ('full', 'no_llm', or 'none')
        regenerate: If True, delete existing resume items first
    
    Returns:
        Tuple of (list of generated ResumeItem objects, list of error messages)
    """
    errors = []
    
    # Delete existing resume items if regenerate is requested
    if regenerate:
        deleted_count = db.query(ResumeItem).filter(
            ResumeItem.repo_stat_id == repo_stat.id
        ).delete()
        if deleted_count > 0:
            print(f"[resume_generate] Deleted {deleted_count} existing items for {repo_stat.project_name}")
    
    # Collect user additions for analysis context
    additions_text = ""
    if repo_stat.project_path and Path(repo_stat.project_path).exists():
        try:
            user_additions = collect_user_additions(
                repo_path=str(repo_stat.project_path),
                user_email=user_email,
                max_commits=500,
            )
            additions_text = "\n".join(user_additions)
        except Exception as e:
            error_msg = f"Could not collect additions for {repo_stat.project_name}: {e}"
            print(f"[resume_generate] Warning: {error_msg}")
            errors.append(error_msg)
    
    # Run deep analysis to extract insights
    analyzer = DeepRepoAnalyzer(enable_llm=False)
    
    try:
        deep_result = analyzer.analyze(
            repo_path=str(repo_stat.project_path) if repo_stat.project_path else "",
            repo_stat=repo_stat,
            user_email=user_email,
            user_contributions={"additions": additions_text},
            consent_level=consent_level,
        )
        
        # Persist skills
        persist_extracted_skills(
            db=db,
            repo_stat_id=repo_stat.id,
            extracted=deep_result.skills,
            user_email=user_email,
            commit=False,
        )
        
        persist_insights_as_project_evidence(
            db=db,
            repo_stat_id=repo_stat.id,
            insights=deep_result.insights,
            repo_last_commit=repo_stat.last_commit,
            commit=False,
        )

        # /resume/generate no longer creates Deep Insight ResumeItem rows.
        print(
            f"[resume_generate] Generated 0 resume items for {repo_stat.project_name}; insights saved to evidence"
        )

        return [], errors
        
    except Exception as e:
        error_msg = f"Failed to analyze {repo_stat.project_name}: {type(e).__name__}: {str(e)}"
        print(f"[resume_generate] Error: {error_msg}")
        errors.append(error_msg)
        return [], errors


@router.post("/generate", response_model=ResumeGenerationResponse)
async def generate_resume_items(
    request: ResumeGenerationRequest,
    db: Session = Depends(get_db),
) -> ResumeGenerationResponse:
    """Generate resume items for selected projects.
    
    This endpoint triggers on-demand resume item generation by running
    DeepRepoAnalyzer on specified projects and persisting the extracted insights.
    
    ## How to Get Project IDs
    
    Project IDs are the database primary keys for RepoStat entries. To retrieve them:
    
    1. **List all projects**: `GET /projects` returns all projects with their IDs
    2. **Get specific project**: `GET /projects/{project_id}` returns details for one project
    3. **After analysis**: When you call `POST /analyze/repo` or upload a ZIP via `POST /zip`,
       the response includes the project ID in the `repo_stat_id` field
    
    Example workflow:
    ```
    # Step 1: Analyze a repository
    POST /analyze/repo -> {"id": 1, "project_name": "my-app", ...}
    
    # Step 2: Generate resume items using the project ID
    POST /resume/generate {"project_ids": [1], "regenerate": false}
    ```
    
    ## Generation Process
    
    1. Validates that all project IDs exist and are not soft-deleted
    2. Retrieves user email and consent level
    3. For each project:
       - Optionally deletes existing resume items (if regenerate=True)
       - Collects user contributions from git history
       - Runs DeepRepoAnalyzer to extract skills and insights
       - Persists insights as project evidence
    4. Returns all generated resume items
    
    Args:
        request: ResumeGenerationRequest with project_ids and regenerate flag
        db: Database session (injected)
    
    Returns:
        ResumeGenerationResponse with generated items, metadata, and success status.
        The `success` field is True only if at least one resume item was generated.
    
    Raises:
        HTTPException 400: If user email not configured
        HTTPException 404: If any project_id not found or soft-deleted
        HTTPException 500: If database commit fails
    
    Milestone Requirement: #331 - POST /resume/generate endpoint
    """
    # Get user email and consent level
    user_email = get_user_email(db)
    consent_level = get_consent_level(db)
    
    print(
        f"[resume_generate] Starting generation for {len(request.project_ids)} projects "
        f"(user={user_email}, consent={consent_level}, regenerate={request.regenerate})"
    )
    
    # Validate all project IDs exist and are not soft-deleted
    projects = (
        db.query(RepoStat)
        .filter(
            RepoStat.id.in_(request.project_ids),
            RepoStat.deleted_at.is_(None),
        )
        .all()
    )
    
    if len(projects) != len(request.project_ids):
        found_ids = {p.id for p in projects}
        missing_ids = set(request.project_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Projects not found or deleted: {sorted(missing_ids)}",
        )
    
    # Generate resume items for each project
    all_resume_items = []
    all_errors = []
    
    for project in projects:
        resume_items, errors = await generate_resume_for_project(
            db=db,
            repo_stat=project,
            user_email=user_email,
            consent_level=consent_level,
            regenerate=request.regenerate,
        )
        all_resume_items.extend(resume_items)
        all_errors.extend(errors)
    
    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save resume items: {type(e).__name__}: {str(e)}",
        )
    
    # Convert to response format
    response_items = [
        ResumeItemResponse(
            id=item.id,
            title=item.title,
            content=item.content,
            category=item.category,
            project_name=item.repo_stat.project_name if item.repo_stat else None,
            created_at=item.created_at,
        )
        for item in all_resume_items
    ]
    
    # Determine success: True only if at least one item was generated
    is_success = len(all_resume_items) > 0
    
    print(
        f"[resume_generate] Completed: {len(all_resume_items)} items generated, "
        f"{len(all_errors)} errors, success={is_success}"
    )
    
    return ResumeGenerationResponse(
        success=is_success,
        items_generated=len(all_resume_items),
        resume_items=response_items,
        consent_level=consent_level,
        errors=all_errors,
    )
