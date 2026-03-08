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

import os
import shutil
import tempfile
from pathlib import Path
from typing import List
from zipfile import ZipFile, is_zipfile

from fastapi import APIRouter, HTTPException

from ..directorycrawler import directory_walk
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
    
    Extracts the ZIP to a temporary directory and uses directory_walk to crawl
    the directory structure. Identifies repositories by finding .git directories
    in the returned directory list.
    
    Args:
        zip_path: Filesystem path to the ZIP file
        
    Returns:
        List of RepositoryCandidate objects sorted by repository name
        
    Raises:
        ValueError: If ZIP is invalid or cannot be read
    """
    if not Path(zip_path).exists():
        raise ValueError(f"ZIP file not found: {zip_path}")
    
    if not is_zipfile(zip_path):
        raise ValueError(f"Invalid ZIP file: {zip_path}")
    
    candidates = []
    seen_repos = set()
    temp_extracted_dir = None
    
    try:
        # Extract ZIP to temporary directory
        temp_extracted_dir = tempfile.mkdtemp(prefix="zip_extract_")
        with ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_extracted_dir)
        
        # Set directory_walk's CURRENTPATH to the extracted directory
        directory_walk.CURRENTPATH = Path(temp_extracted_dir)
        
        # Call crawl_directory to scan the extracted files
        files_dict, dirs_list = directory_walk.crawl_directory(refresh_dict=True)
        
        # Scan extracted directory for .git directories
        # Using os.walk since .git file contents are not in readable extensions
        for root, dirs, files in os.walk(temp_extracted_dir):
            if '.git' in dirs:
                repo_rel_path = os.path.relpath(root, temp_extracted_dir)
                
                if repo_rel_path not in seen_repos:
                    seen_repos.add(repo_rel_path)
                    repo_name = os.path.basename(root)
                    
                    candidates.append(
                        RepositoryCandidate(
                            id=repo_rel_path,
                            name=repo_name,
                            rel_path=repo_rel_path,
                        )
                    )
    
    except Exception as e:
        raise ValueError(f"Failed to process ZIP file: {str(e)}")
    
    finally:
        # Clean up temporary directory
        if temp_extracted_dir and os.path.exists(temp_extracted_dir):
            shutil.rmtree(temp_extracted_dir)
    
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
