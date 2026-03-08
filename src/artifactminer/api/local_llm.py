"""Local LLM API endpoints for resume generation workflow.

This module provides the /local-llm/* route family for orchestrating
resume generation using local LLM models. It exposes endpoints for:
- Context intake (ZIP discovery and repository scanning)
- Contributor discovery (git history analysis)
- Generation start and monitoring
- Draft polishing and customization

These endpoints support the full local generation pipeline as an alternative
to cloud-based generation workflows.
"""

from pathlib import Path
from typing import List
from zipfile import ZipFile, is_zipfile

from fastapi import APIRouter, HTTPException

from .local_llm_schemas import (
    IntakeCreateRequest,
    IntakeCreateResponse,
    RepositoryCandidate,
)


router = APIRouter(
    prefix="/local-llm",
    tags=["local-llm"],
)


def _discover_repos_in_zip(zip_path: str) -> List[RepositoryCandidate]:
    """Scan a ZIP file for git repositories and return candidates.
    
    A repository is identified by the presence of a .git directory.
    Returns a list of discovered repositories with metadata.
    
    Args:
        zip_path: Filesystem path to the ZIP file
        
    Returns:
        List of RepositoryCandidate objects
        
    Raises:
        ValueError: If ZIP is invalid or cannot be read
    """
    if not Path(zip_path).exists():
        raise ValueError(f"ZIP file not found: {zip_path}")
    
    if not is_zipfile(zip_path):
        raise ValueError(f"Invalid ZIP file: {zip_path}")
    
    candidates = []
    seen_repos = set()
    
    try:
        with ZipFile(zip_path, 'r') as zf:
            # Find all .git directories
            for name in zf.namelist():
                if '.git/' in name:
                    # Extract repo path (everything before .git/)
                    repo_rel_path = name.split('.git/')[0].rstrip('/')
                    
                    if repo_rel_path and repo_rel_path not in seen_repos:
                        seen_repos.add(repo_rel_path)
                        
                        # Extract repo name (last path component)
                        repo_name = repo_rel_path.split('/')[-1] if '/' in repo_rel_path else repo_rel_path
                        
                        candidates.append(
                            RepositoryCandidate(
                                id=repo_rel_path,
                                name=repo_name,
                                rel_path=repo_rel_path,
                            )
                        )
    except Exception as e:
        raise ValueError(f"Failed to read ZIP file: {str(e)}")
    
    return sorted(candidates, key=lambda x: x.name)


@router.post("/context", response_model=IntakeCreateResponse)
async def create_intake(
    request: IntakeCreateRequest,
) -> IntakeCreateResponse:
    """Create a new intake from an uploaded ZIP file.
    
    Scans the provided ZIP file for git repositories and returns a list
    of discovered candidates. This is the first step in the local LLM
    generation workflow.
    
    The intake_id is derived from the ZIP filename for simplicity in this
    initial implementation. Future versions may persist intake state to DB.
    
    Args:
        request: IntakeCreateRequest with zip_path
        
    Returns:
        IntakeCreateResponse with intake_id and discovered repositories
        
    Raises:
        HTTPException: 400 if ZIP is invalid, 404 if not found, 500 on internal error
    """
    try:
        # Validate and discover repositories
        repos = _discover_repos_in_zip(request.zip_path)
        
        # Generate intake_id from ZIP filename
        intake_id = Path(request.zip_path).stem
        
        return IntakeCreateResponse(
            intake_id=intake_id,
            zip_path=request.zip_path,
            repos=repos,
        )
    
    except ValueError as e:
        # Client error: invalid ZIP or not found
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Internal server error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create intake: {str(e)}",
        )
