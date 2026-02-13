"""Git contribution metrics for user-scoped analysis."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Set

import git

from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo
from artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats


def get_git_stats(
    repo_path: str,
    user_email: str,
    *,
    window_days: int = 90,
    touched_paths: Set[str] | None = None,
    user_stats: Any = None,
) -> Dict[str, Any]:
    """Extract git contribution metrics for a user.

    Delegates to getUserRepoStats for core metrics, adds windowed commit count.

    Returns:
        Dict with keys:
        - commit_count_window: commits in the last window_days
        - commit_frequency: average commits per week
        - contribution_percent: user's share of total repo commits
        - first_commit_date: datetime of first commit
        - last_commit_date: datetime of most recent commit
    """
    if not isGitRepo(repo_path):
        return {}

    if user_stats is None:
        try:
            user_stats = getUserRepoStats(repo_path, user_email)
        except Exception:
            return {}

    if user_stats.total_commits is None or user_stats.total_commits == 0:
        return {
            "commit_count_window": 0,
            "commit_frequency": 0.0,
            "contribution_percent": 0.0,
            "first_commit_date": None,
            "last_commit_date": None,
        }

    commits_in_window = _count_commits_in_window(repo_path, user_email, window_days)

    return {
        "commit_count_window": commits_in_window,
        "commit_frequency": user_stats.commitFrequency or 0.0,
        "contribution_percent": user_stats.userStatspercentages or 0.0,
        "first_commit_date": user_stats.first_commit,
        "last_commit_date": user_stats.last_commit,
    }


def _count_commits_in_window(repo_path: str, user_email: str, window_days: int) -> int:
    """Count user commits within the specified time window."""
    try:
        repo = git.Repo(repo_path)
    except Exception:
        return 0

    user_email = user_email.strip().lower()
    now = datetime.now(UTC)
    window_start = now - timedelta(days=window_days)

    count = 0
    # Filter at git query level to avoid scanning full history on large repos.
    for c in repo.iter_commits(
        author=user_email,
        since=window_start.isoformat(),
    ):
        if (getattr(c.author, "email", "") or "").lower() == user_email:
            count += 1
    return count


def detect_git_patterns(
    repo_path: str, *, touched_paths: Set[str] | None = None
) -> Dict[str, Any]:
    """Detect git workflow patterns from branch names and commit messages."""
    if not isGitRepo(repo_path):
        return {}

    try:
        repo = git.Repo(repo_path)
    except Exception:
        return {}

    patterns: Dict[str, Any] = {
        "has_branches": False,
        "branch_count": 0,
        "has_tags": False,
        "tag_count": 0,
        "merge_commits": 0,
    }

    try:
        branches = list(repo.branches)
        patterns["branch_count"] = len(branches)
        patterns["has_branches"] = len(branches) > 1
    except Exception:
        pass

    try:
        tags = list(repo.tags)
        patterns["tag_count"] = len(tags)
        patterns["has_tags"] = len(tags) > 0
    except Exception:
        pass

    try:
        for commit in repo.iter_commits(max_count=100):
            if len(commit.parents) > 1:
                patterns["merge_commits"] += 1
    except Exception:
        pass

    return patterns
