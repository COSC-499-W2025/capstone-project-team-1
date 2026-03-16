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
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile, is_zipfile
from ..helpers.zip_utils import safe_extract_zip


from fastapi import APIRouter, HTTPException

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


def _discover_repos_in_zip(zip_path: str) -> tuple[List[RepositoryCandidate], str]:
    """Scan a ZIP file for git repositories and return candidates.

    Extracts the ZIP to a temporary directory and discovers git repositories
    using validation logic aligned with experimental-llamacpp-v3:
    - Requires both .git directory and .git/HEAD file
    - Filters out macOS metadata (__MACOSX, ._* files)
    - Skips nested repositories
    
    Args:
        zip_path: Filesystem path to the ZIP file
        
    Returns:
        Tuple of (List of RepositoryCandidate objects sorted by name, path to extracted directory)
        The extracted directory should be cleaned up by the caller.
        
    Raises:
        ValueError: If ZIP is invalid or cannot be read
    """
    if not Path(zip_path).exists():
        raise ValueError(f"ZIP file not found: {zip_path}")
    
    if not is_zipfile(zip_path):
        raise ValueError(f"Invalid ZIP file: {zip_path}")
    
    candidates = []
    seen_repos = set()
    
    # Extract ZIP to temporary directory
    temp_extracted_dir = tempfile.mkdtemp(prefix="zip_extract_")
    
    try:
        try:
            with ZipFile(zip_path, 'r') as zf:
                safe_extract_zip(zf, Path(temp_extracted_dir))
        except Exception as e:
            # Extraction failures are user errors (corrupted ZIP, etc.)
            shutil.rmtree(temp_extracted_dir)
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
    except ValueError:
        # Re-raise ValueError without cleaning up temp_extracted_dir 
        # (it's already cleaned up by the inner exception handler)
        raise
    except Exception as e:
        # Clean up on unexpected errors
        if Path(temp_extracted_dir).exists():
            shutil.rmtree(temp_extracted_dir)
        raise ValueError(f"Failed to discover repositories: {str(e)}")
    
    return sorted(candidates, key=lambda x: x.name), temp_extracted_dir


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
            
            repos_with_commits += 1
            
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
        # Validate and discover repositories (includes extraction)
        repos, temp_extracted_dir = _discover_repos_in_zip(request.zip_path)

        if not repos:
            raise ValueError("No git repositories found in ZIP")

        # Generate globally unique intake identifier
        intake_id = str(uuid.uuid4())
        
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
