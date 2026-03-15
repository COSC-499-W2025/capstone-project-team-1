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
import subprocess
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
from zipfile import ZipFile, is_zipfile

from fastapi import APIRouter, HTTPException

from ..directorycrawler import directory_walk
from .local_llm_schemas import (
    ContributorDiscoveryRequest,
    ContributorDiscoveryResponse,
    ContributorIdentity,
    IntakeCreateRequest,
    IntakeCreateResponse,
    RepositoryCandidate,
)


router = APIRouter(
    prefix="/local-llm",
    tags=["local-llm"],
)


# In-memory storage for active intake contexts
# Maps intake_id -> {zip_path, repos}
_active_intakes: Dict[str, Dict] = {}


class IntakeContext:
    """Represents an active intake session with metadata."""
    
    def __init__(
        self,
        intake_id: str,
        zip_path: str,
        repos: List[RepositoryCandidate],
        extracted_dir: str,
    ):
        self.intake_id = intake_id
        self.zip_path = zip_path
        self.repos = repos
        self.extracted_dir = extracted_dir
        self.repo_id_to_path: Dict[str, Path] = {
            repo.id: Path(extracted_dir) / repo.rel_path
            for repo in repos
        }


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
    temp_extracted_dir = None
    
    try:
        # Extract ZIP to temporary directory
        temp_extracted_dir = tempfile.mkdtemp(prefix="zip_extract_")
        with ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_extracted_dir)
        
        # Set directory_walk's CURRENTPATH to the extracted directory
        directory_walk.CURRENTPATH = Path(temp_extracted_dir)
        
        # Call crawl_directory to scan the extracted files and directories
        _, dirs_list = directory_walk.crawl_directory(refresh_dict=True)
        
        # Find repositories by looking for .git directories in dirs_list
        for dir_path in dirs_list:
            # Check if this is a .git directory
            if dir_path.endswith('.git') or dir_path.endswith('/.git'):
                # Extract the repository path (everything before .git)
                if dir_path.endswith('/.git'):
                    repo_rel_path = dir_path[:-5]  # Remove '/.git'
                else:
                    repo_rel_path = dir_path[:-4]  # Remove '.git'
                
                # Get repo name from the path
                repo_name = os.path.basename(repo_rel_path) if repo_rel_path else os.path.basename(temp_extracted_dir)
                
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


def _discover_contributors_in_repos(
    repo_paths: List[Path],
) -> List[ContributorIdentity]:
    """Discover unique contributors from git history across multiple repositories.
    
    Scans git commit history to extract contributor identities (email/name pairs)
    and aggregate statistics across repositories.
    
    Args:
        repo_paths: List of paths to git repositories
        
    Returns:
        List of unique ContributorIdentity objects sorted by commit count
        
    Raises:
        ValueError: If git operations fail on all repositories
    """
    # Track unique contributors by email
    # email -> {name, repos_set, commit_count}
    contributors_map: Dict[str, Dict] = {}
    repos_with_commits = 0
    
    for repo_path in repo_paths:
        if not repo_path.exists() or not _is_git_repo(repo_path):
            raise ValueError(f"Invalid git repository: {repo_path}")
        
        try:
            # Get all commits with author email and name
            # Format: email|name (separated by pipe for reliable parsing)
            result = subprocess.run(
                ["git", "log", "--format=%ae|%an"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # If git log fails, skip this repo (may not have commits yet)
            if result.returncode != 0:
                continue
            
            # Parse commits
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                
                parts = line.split("|", 1)
                if len(parts) != 2:
                    continue
                
                email = parts[0].strip()
                name = parts[1].strip() if parts[1].strip() else None
                
                if not email:
                    continue
                
                repos_with_commits += 1
                
                # Update or create contributor entry
                if email not in contributors_map:
                    contributors_map[email] = {
                        "name": name,
                        "repos": set(),
                        "commit_count": 0,
                    }
                
                contrib = contributors_map[email]
                contrib["repos"].add(repo_path.name)
                contrib["commit_count"] += 1
                
                # Update name if we get a better one
                if name and (not contrib["name"] or len(name) > len(contrib["name"])):
                    contrib["name"] = name
        
        except subprocess.TimeoutExpired:
            # Timeout is an error - repo may be corrupted or too large
            raise ValueError(f"Git operation timed out for {repo_path}")
        except Exception as e:
            # All other errors should be surfaced - don't silently skip repos
            raise ValueError(f"Failed to analyze git repository {repo_path}: {str(e)}")
    
    # Convert to ContributorIdentity objects
    identities = []
    for email, data in contributors_map.items():
        # Extract potential username from email (part before @)
        candidate_username = email.split("@")[0]
        
        identities.append(
            ContributorIdentity(
                email=email,
                name=data["name"],
                repo_count=len(data["repos"]),
                commit_count=data["commit_count"],
                candidate_username=candidate_username,
            )
        )
    
    # Sort by commit count descending, then by email
    return sorted(identities, key=lambda x: (-x.commit_count, x.email))

@router.post("/context", response_model=IntakeCreateResponse)
async def create_intake(
    request: IntakeCreateRequest,
) -> IntakeCreateResponse:
    """Create a new intake from an uploaded ZIP file.
    
    Scans the provided ZIP file for git repositories and returns a list
    of discovered candidates. This is the first step in the local LLM
    generation workflow.
    
    A unique UUID is generated for each intake request. The intake context
    is stored in memory for subsequent contributor discovery and generation steps.
    
    Args:
        request: IntakeCreateRequest with zip_path
        
    Returns:
        IntakeCreateResponse with intake_id and discovered repositories
        
    Raises:
        HTTPException: 400 if ZIP is invalid, 404 if not found, 500 on internal error
    """
    temp_extracted_dir = None
    
    try:
        # Validate and discover repositories
        repos = _discover_repos_in_zip(request.zip_path)

        if not repos:
            raise ValueError("No git repositories found in ZIP")

        # Generate globally unique intake identifier
        intake_id = str(uuid.uuid4())
        
        # For context storage, we need to keep the extracted directory around
        # In a production system, this would be managed more carefully
        temp_extracted_dir = tempfile.mkdtemp(prefix="intake_")
        
        try:
            with ZipFile(request.zip_path, 'r') as zf:
                zf.extractall(temp_extracted_dir)
        except Exception as e:
            raise ValueError(f"Failed to extract ZIP file: {str(e)}")
        
        # Store intake context for later use
        context = IntakeContext(
            intake_id=intake_id,
            zip_path=request.zip_path,
            repos=repos,
            extracted_dir=temp_extracted_dir,
        )
        _active_intakes[intake_id] = context
        
        return IntakeCreateResponse(
            intake_id=intake_id,
            zip_path=request.zip_path,
            repos=repos,
        )
    
    except ValueError as e:
        # Client error: invalid ZIP or not found
        if temp_extracted_dir and Path(temp_extracted_dir).exists():
            shutil.rmtree(temp_extracted_dir)
        
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Internal server error
        if temp_extracted_dir and Path(temp_extracted_dir).exists():
            shutil.rmtree(temp_extracted_dir)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create intake: {str(e)}",
        )


@router.post("/context/contributors", response_model=ContributorDiscoveryResponse)
async def discover_contributors(
    request: ContributorDiscoveryRequest,
) -> ContributorDiscoveryResponse:
    """Discover contributors across selected repositories.
    
    Requires an active intake context created by POST /local-llm/context.
    Scans git commit history of selected repositories to identify unique
    contributor identities and their contribution statistics.
    
    Args:
        request: ContributorDiscoveryRequest with repo_ids
        
    Returns:
        ContributorDiscoveryResponse with discovered contributors
        
    Raises:
        HTTPException: 404 if no active intake, 400 if invalid repo IDs, 
                      422 if validation fails, 500 on internal error
    """
    try:
        # This would normally come from a session/user context.
        # For now, use the most recent active intake as the current context.
        if not _active_intakes:
            raise ValueError("No active intake context found")
        
        # Get the last (most recent) active intake
        # In production, this would be retrieved from session/user context
        context = next(iter(_active_intakes.values()))
        
        # Validate all repo_ids are valid for this intake
        valid_repo_ids = {repo.id for repo in context.repos}
        requested_repo_ids = set(request.repo_ids)
        
        invalid_ids = requested_repo_ids - valid_repo_ids
        if invalid_ids:
            raise ValueError(
                f"Invalid repository IDs for active intake: {', '.join(sorted(invalid_ids))}"
            )
        
        # Get paths for selected repositories
        repo_paths = [
            context.repo_id_to_path[repo_id]
            for repo_id in request.repo_ids
        ]
        
        # Discover contributors
        contributors = _discover_contributors_in_repos(repo_paths)
        
        return ContributorDiscoveryResponse(contributors=contributors)
    
    except ValueError as e:
        error_msg = str(e)
        if "no active intake" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "invalid repository ids" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    
    except Exception as e:
        # Internal server error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover contributors: {str(e)}",
        )
