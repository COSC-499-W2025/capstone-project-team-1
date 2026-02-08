"""Resume generation endpoints for on-demand resume item creation."""

from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, RepoStat, ResumeItem
from .schemas import ResumeItemResponse
from ..skills.deep_analysis import DeepRepoAnalyzer
from ..skills.persistence import persist_extracted_skills, persist_insights_as_resume_items
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
    Runs DeepRepoAnalyzer on a project and persists insights as resume items.
    
    Args:
        db: Database session
        repo_stat: RepoStat model for the project
        user_email: User's email for contribution tracking
        consent_level: Consent level for LLM usage ('full', 'no_llm', or 'none')
        regenerate: If True, delete existing resume items first
    
    Returns:
        Tuple of (list of created ResumeItem objects, list of error messages)
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
        
        # Persist insights as resume items
        resume_items = persist_insights_as_resume_items(
            db=db,
            repo_stat_id=repo_stat.id,
            insights=deep_result.insights,
            commit=False,
        )
        
        print(
            f"[resume_generate] Generated {len(resume_items)} items for {repo_stat.project_name}"
        )
        
        return resume_items, errors
        
    except Exception as e:
        error_msg = f"Failed to analyze {repo_stat.project_name}: {str(e)}"
        print(f"[resume_generate] Error: {error_msg}")
        errors.append(error_msg)
        return [], errors

