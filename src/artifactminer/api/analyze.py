"""
Master analysis endpoint that orchestrates the full artifact mining pipeline.

This module ties together ZIP extraction with repository analysis, providing
a single endpoint that:
1. Extracts uploaded ZIP to persistent storage
2. Discovers git repositories within
3. Analyzes each repo (stats, skills, insights)
4. Ranks projects by user contribution
5. Generates summaries (LLM if consented, template otherwise)

Owner: Nathan (orchestration)
Dependencies:
    - Evan's repo intelligence: getRepoStats, getUserRepoStats, generate_summaries_for_ranked
    - Shlok's skill extraction: DeepRepoAnalyzer, persist_extracted_skills, rank_projects

Milestone Requirements: #2 (Parse zip), #12 (Output all info)
"""

import zipfile
import shutil
from datetime import datetime, UTC
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..db.models import (
    UploadedZip,
    Question,
    UserAnswer,
    Consent,
    RepoStat,
)
from .schemas import (
    RepoAnalysisResult,
    RankingResult,
    SummaryResult,
    AnalyzeRequest,
    AnalyzeResponse,
)
from ..RepositoryIntelligence.repo_intelligence_main import (
    getRepoStats,
    saveRepoStats,
    isGitRepo,
)
from ..RepositoryIntelligence.repo_intelligence_user import (
    getUserRepoStats,
    saveUserRepoStats,
    collect_user_additions,
    generate_summaries_for_ranked,
)
from ..skills.deep_analysis import DeepRepoAnalyzer
from ..skills.persistence import (
    persist_extracted_skills,
    persist_insights_as_resume_items,
)
from ..helpers.project_ranker import rank_projects

router = APIRouter(prefix="/analyze", tags=["analysis"])
EXTRACTION_BASE_DIR = Path("./.extracted")


def get_user_email(db: Session) -> str:
    """
    Retrieve user's email from the answers table.

    Uses the question key 'email' for lookup (safer than hardcoded question_id).

    Raises:
        HTTPException: If email question not found or user hasn't answered.
    """
    # Find the email question by key
    email_question = db.query(Question).filter(Question.key == "email").first()
    if not email_question:
        raise HTTPException(
            status_code=400,
            detail="Email question not configured. Please set up questions first.",
        )

    # Get the user's answer
    email_answer = (
        db.query(UserAnswer)
        .filter(UserAnswer.question_id == email_question.id)
        .order_by(UserAnswer.answered_at.desc())
        .first()
    )
    if not email_answer or not email_answer.answer_text.strip():
        raise HTTPException(
            status_code=400,
            detail="User email not provided. Please complete the configuration first.",
        )

    return email_answer.answer_text.strip().lower()


def get_consent_level(db: Session) -> str:
    """
    Retrieve current consent level from database.

    Returns:
        Consent level string: 'full', 'no_llm', or 'none'
    """
    consent = db.query(Consent).filter(Consent.id == 1).first()
    return consent.consent_level if consent else "none"


def discover_git_repos(base_path: Path) -> List[Path]:
    """
    Recursively find all directories containing a .git folder.

    Args:
        base_path: Root directory to search

    Returns:
        List of paths to git repositories
    """
    git_repos = []
    if base_path.is_dir() and isGitRepo(base_path):
        git_repos.append(base_path)

    # Walk through all directories
    for path in base_path.rglob("*"):
        if path.is_dir() and isGitRepo(path):
            # Avoid adding nested .git directories
            # Only add if no parent is already a git repo
            is_nested = any(
                isGitRepo(parent)
                for parent in path.parents
                if parent != base_path and parent.is_relative_to(base_path)
            )
            if not is_nested:
                git_repos.append(path)

    return git_repos


def discover_git_repos_from_multiple_paths(base_paths: List[Path]) -> List[Path]:
    """
    Discover git repositories across multiple extraction paths.
    
    Used for incremental portfolio uploads where multiple ZIPs contribute
    to the same portfolio. Deduplicates repositories by name to avoid
    analyzing the same project twice.

    Args:
        base_paths: List of extraction directories to search

    Returns:
        List of unique paths to git repositories
    """
    all_repos = []
    seen_repo_names = set()
    
    for base_path in base_paths:
        if not base_path.exists():
            print(f"[analyze] Skipping non-existent path: {base_path}")
            continue
            
        repos = discover_git_repos(base_path)
        for repo in repos:
            if repo.name not in seen_repo_names:
                all_repos.append(repo)
                seen_repo_names.add(repo.name)
            else:
                print(f"[analyze] Skipping duplicate repo: {repo.name}")
    
    return all_repos


def resolve_selected_dirs(extraction_path: Path, directories: list[str]) -> list[Path]:
    """Resolve user-selected directories into valid paths under extraction root."""
    extraction_root = extraction_path.resolve()
    base_paths: list[Path] = []
    seen: set[Path] = set()

    for raw in directories:
        if not raw:
            continue
        name = str(raw).strip()
        if not name:
            continue

        raw_path = Path(name)
        candidate = raw_path if raw_path.is_absolute() else (extraction_root / raw_path)
        candidate = candidate.resolve()

        if not candidate.is_relative_to(extraction_root):
            print(f"[analyze] Skipping out-of-root path: {raw}")
            continue

        if candidate.exists() and candidate.is_dir():
            if candidate not in seen:
                base_paths.append(candidate)
                seen.add(candidate)
            continue

        # Fallback: match by directory name anywhere in extraction tree.
        for match in extraction_root.rglob(raw_path.name):
            if not match.is_dir() or ".git" in match.parts:
                continue
            resolved = match.resolve()
            if resolved in seen or not resolved.is_relative_to(extraction_root):
                continue
            base_paths.append(resolved)
            seen.add(resolved)

    return base_paths


def extract_zip_to_persistent_location(zip_path: str, zip_id: int) -> Path:
    """
    Extract ZIP file to a persistent location for later access.

    Creates: ./extracted/{zip_id}/

    Args:
        zip_path: Path to the ZIP file
        zip_id: Database ID of the UploadedZip record

    Returns:
        Path to the extraction directory

    Raises:
        HTTPException: If ZIP is invalid or extraction fails
    """
    extraction_dir = EXTRACTION_BASE_DIR / str(zip_id)

    # Clean up any previous extraction
    if extraction_dir.exists():
        shutil.rmtree(extraction_dir)

    # Create extraction directory
    extraction_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Validate ZIP integrity
            bad_file = zf.testzip()
            if bad_file:
                raise HTTPException(
                    status_code=400,
                    detail=f"Corrupted ZIP file: bad entry '{bad_file}'",
                )

            # Extract all contents
            zf.extractall(extraction_dir)

    except zipfile.BadZipFile:
        # Clean up on failure
        if extraction_dir.exists():
            shutil.rmtree(extraction_dir)
        raise HTTPException(status_code=400, detail="Invalid ZIP file format")

    return extraction_dir

@router.post("/{zip_id}", response_model=AnalyzeResponse)
async def analyze_zip(
    zip_id: int,
    request: AnalyzeRequest | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """
    Master orchestration endpoint: analyze all git repos in an uploaded ZIP.

    This endpoint ties together the full artifact mining pipeline:

    **Step 1 - Setup:**
    - Retrieve ZIP path from database
    - Get user email from configuration answers
    - Get consent level for LLM usage

    **Step 2 - Extraction:**
    - Extract ZIP to persistent location (./extracted/{zip_id}/)
    - Discover git repositories within (or within selected directories)

    **Step 3 - Analysis Loop (for each repo):**
    - Call Evan's getRepoStats() → save to RepoStat table
    - Call Evan's getUserRepoStats() → save to UserRepoStat table
    - Call Stavans's DeepRepoAnalyzer.analyze() → extract skills + insights
    - Call Shlok's persist_extracted_skills() → save skills
    - Call Shlok's persist_insights_as_resume_items() → save resume items

    **Step 4 - Post-Processing:**
    - Call Shlok's rank_projects() → update RepoStat.ranking_score
    - Call Evan's generate_summaries_for_ranked() → create summaries
      (Uses LLM if consent='full', otherwise template fallback)

    **Error Handling:**
    - Individual repo failures are logged but don't stop the pipeline
    - Transaction is committed after all repos are processed

    Args:
        zip_id: Database ID of the uploaded ZIP file

    Returns:
        AnalyzeResponse with repos analyzed, rankings, and summaries
    """


    uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()
    if not uploaded_zip:
        raise HTTPException(
            status_code=404, detail=f"ZIP file with id={zip_id} not found"
        )

    if not Path(uploaded_zip.path).exists():
        raise HTTPException(
            status_code=404, detail=f"ZIP file not found on disk: {uploaded_zip.path}"
        )

    user_email = get_user_email(db)
    consent_level = get_consent_level(db)

    print(
        f"[analyze] Starting analysis for zip_id={zip_id}, user={user_email}, consent={consent_level}"
    )
    extraction_path = extract_zip_to_persistent_location(uploaded_zip.path, zip_id)

    # Update the UploadedZip record with extraction path
    uploaded_zip.extraction_path = str(extraction_path)

    # Find all git repositories (optionally scoped by selected directories)
    if request and request.directories is not None:
        if not request.directories:
            raise HTTPException(
                status_code=400, detail="No directories provided for analysis"
            )
        selected_paths = resolve_selected_dirs(extraction_path, request.directories)
        if not selected_paths:
            raise HTTPException(
                status_code=400,
                detail="No selected directories found in extracted ZIP",
            )
        git_repos = discover_git_repos_from_multiple_paths(selected_paths)
    else:
        git_repos = discover_git_repos(extraction_path)

    if not git_repos:
        raise HTTPException(
            status_code=400, detail="No git repositories found in the uploaded ZIP file"
        )

    print(f"[analyze] Found {len(git_repos)} git repositories")


    # Initialize the deep analyzer (Stavans's component)
    # enable_llm=False because we use deterministic extraction only
    analyzer = DeepRepoAnalyzer(enable_llm=False)

    repos_analyzed: List[RepoAnalysisResult] = []

    for repo_path in git_repos:
        print(f"[analyze] Processing: {repo_path.name}")

        try:
            repo_stats = getRepoStats(repo_path)
            repo_stat = saveRepoStats(repo_stats, db=db)

            # repo_stat is now the SQLAlchemy model instance with .id

            user_stats = getUserRepoStats(repo_path, user_email)
            saveUserRepoStats(user_stats, db=db)

            user_contribution_pct = user_stats.userStatspercentages
            try:
                user_additions = collect_user_additions(
                    repo_path=str(repo_path), user_email=user_email, max_commits=500
                )
                additions_text = "\n".join(user_additions)
            except Exception as e:
                print(
                    f"[analyze] Warning: Could not collect additions for {repo_path.name}: {e}"
                )
                additions_text = ""

  
            deep_result = analyzer.analyze(
                repo_path=str(repo_path),
                repo_stat=repo_stat,  # Pass the SQLAlchemy model
                user_email=user_email,
                user_contributions={"additions": additions_text},
                consent_level=consent_level,
            )

            skills_count = len(deep_result.skills)
            insights_count = len(deep_result.insights)


            persist_extracted_skills(
                db=db,
                repo_stat_id=repo_stat.id,
                extracted=deep_result.skills,
                user_email=user_email,
                commit=False,  # Batch commit at end
            )

            persist_insights_as_resume_items(
                db=db,
                repo_stat_id=repo_stat.id,
                insights=deep_result.insights,
                commit=False,  # Batch commit at end
            )

            print(
                f"[analyze] Completed {repo_path.name}: {skills_count} skills, {insights_count} insights"
            )

            repos_analyzed.append(
                RepoAnalysisResult(
                    project_name=repo_stats.project_name,
                    project_path=str(repo_path),
                    frameworks=repo_stats.frameworks,
                    languages=repo_stats.Languages,
                    skills_count=skills_count,
                    insights_count=insights_count,
                    user_contribution_pct=user_contribution_pct,
                    user_total_commits=user_stats.total_commits,
                    user_commit_frequency=user_stats.commitFrequency,
                    user_first_commit=user_stats.first_commit,
                    user_last_commit=user_stats.last_commit,
                )
            )

        except ValueError as e:
            # User has no commits in this repo, or other validation error
            print(f"[analyze] Skipping {repo_path.name}: {e}")
            repos_analyzed.append(
                RepoAnalysisResult(
                    project_name=repo_path.name,
                    project_path=str(repo_path),
                    error=str(e),
                )
            )
            continue

        except Exception as e:
            # Unexpected error - log and continue with other repos
            print(
                f"[analyze] Error processing {repo_path.name}: {type(e).__name__}: {e}"
            )
            repos_analyzed.append(
                RepoAnalysisResult(
                    project_name=repo_path.name,
                    project_path=str(repo_path),
                    error=f"{type(e).__name__}: {str(e)}",
                )
            )
            continue

    print("[analyze] Ranking projects...")

    rankings: List[RankingResult] = []
    try:
        ranking_data = rank_projects(str(extraction_path), user_email)
        for rank_info in ranking_data:
            repo_stat = (
                db.query(RepoStat)
                .filter(RepoStat.project_name == rank_info["name"])
                .order_by(RepoStat.id.desc())
                .first()
            )
            if repo_stat:
                repo_stat.ranking_score = rank_info["score"]
                repo_stat.ranked_at = datetime.now(UTC)

            rankings.append(
                RankingResult(
                    name=rank_info["name"],
                    score=rank_info["score"],
                    total_commits=rank_info["total_commits"],
                    user_commits=rank_info["user_commits"],
                )
            )

    except Exception as e:
        print(f"[analyze] Warning: Ranking failed: {e}")
        # Continue without rankings

    # Commit all changes before summary generation
    db.commit()
    print("[analyze] Generating summaries...")

    summaries: List[SummaryResult] = []
    try:
        # generate_summaries_for_ranked uses project_path from DB to access git repos
        # This is why we persist to ./extracted/ instead of using temp directory
        summary_data = await generate_summaries_for_ranked(
            db, top=3, extraction_path=str(extraction_path)
        )

        for item in summary_data:
            summaries.append(
                SummaryResult(
                    project_name=item["project_name"],
                    summary=item["summary"],
                )
            )

    except Exception as e:
        print(f"[analyze] Warning: Summary generation failed: {e}")
        import traceback

        traceback.print_exc()
        # Continue without summaries

    print(
        f"[analyze] Analysis complete: {len(repos_analyzed)} repos, {len(rankings)} ranked, {len(summaries)} summaries"
    )

    return AnalyzeResponse(
        zip_id=zip_id,
        extraction_path=str(extraction_path),
        repos_found=len(git_repos),
        repos_analyzed=repos_analyzed,
        rankings=rankings,
        summaries=summaries,
        consent_level=consent_level,
        user_email=user_email,
    )
