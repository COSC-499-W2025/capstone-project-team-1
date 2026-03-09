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

import shutil
import tempfile
import uuid
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


def _is_git_repo(path: Path) -> bool:
    """Check if a path is a valid git repository.
    
    Aligned with experimental-llamacpp-v3 validation logic.
    Requires both .git directory and HEAD file to exist.
    """
    git_dir = path / ".git"
    return git_dir.is_dir() and (git_dir / "HEAD").is_file()


def _is_macos_metadata(path: Path, base_path: Path) -> bool:
    """Check if path is macOS metadata that should be ignored.
    
    Filters __MACOSX directories and resource fork files (._*).
    Aligned with experimental-llamacpp-v3 filtering logic.
    """
    try:
        parts = path.relative_to(base_path).parts
    except ValueError:
        parts = path.parts
    return any(part == "__MACOSX" or part.startswith("._") for part in parts)


def _discover_repos_in_zip(zip_path: str) -> List[RepositoryCandidate]:
    """Scan a ZIP file for git repositories and return candidates.

    Extracts the ZIP to a temporary directory and discovers git repositories
    using validation logic aligned with experimental-llamacpp-v3:
    - Requires both .git directory and .git/HEAD file
    - Filters out macOS metadata (__MACOSX, ._* files)
    - Skips nested repositories
    
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
        
        try:
            with ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_extracted_dir)
        except Exception as e:
            # Extraction failures are user errors (corrupted ZIP, etc.)
            raise ValueError(f"Failed to extract ZIP file: {str(e)}")
        
        extracted_root = Path(temp_extracted_dir)

        # Discovery logic aligned with experimental-llamacpp-v3
        # Check base path first
        if _is_git_repo(extracted_root) and not _is_macos_metadata(extracted_root, extracted_root):
            repo_rel_path = "."
            if repo_rel_path not in seen_repos:
                seen_repos.add(repo_rel_path)
                candidates.append(
                    RepositoryCandidate(
                        id=repo_rel_path,
                        name=extracted_root.name,
                        rel_path=repo_rel_path,
                    )
                )

        # Search subdirectories
        for path in extracted_root.rglob("*"):
            if not path.is_dir() or _is_macos_metadata(path, extracted_root):
                continue

            if _is_git_repo(path):
                # Avoid nested repos
                is_nested = any(
                    _is_git_repo(parent)
                    for parent in path.parents
                    if parent != extracted_root and parent.is_relative_to(extracted_root)
                )
                if not is_nested:
                    repo_rel_path = path.relative_to(extracted_root).as_posix()
                    if repo_rel_path not in seen_repos:
                        seen_repos.add(repo_rel_path)
                        candidates.append(
                            RepositoryCandidate(
                                id=repo_rel_path,
                                name=path.name,
                                rel_path=repo_rel_path,
                            )
                        )
    
    finally:
        # Clean up temporary directory
        if temp_extracted_dir and Path(temp_extracted_dir).exists():
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
    
    A unique UUID is generated for each intake request.
    
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

        if not repos:
            raise ValueError("No git repositories found in ZIP")

        # Generate globally unique intake identifier
        intake_id = str(uuid.uuid4())
        
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
