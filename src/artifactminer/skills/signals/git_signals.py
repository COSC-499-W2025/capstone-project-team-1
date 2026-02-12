"""Git contribution metrics for user-scoped analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Set

import git

from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo
from artifactminer.skills.signals.file_signals import path_in_touched


def get_git_stats(
    repo_path: str,
    user_email: str,
    *,
    window_days: int = 90,
    touched_paths: Set[str] | None = None,
) -> Dict[str, Any]:
    """Extract git contribution metrics for a user.

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

    try:
        repo = git.Repo(repo_path)
    except Exception:
        return {}

    user_email = user_email.strip().lower()
    now = datetime.now()
    window_start = now - timedelta(days=window_days)

    all_commits = list(repo.iter_commits())
    user_commits = [
        c
        for c in all_commits
        if (getattr(c.author, "email", "") or "").lower() == user_email
    ]

    if not user_commits:
        return {
            "commit_count_window": 0,
            "commit_frequency": 0.0,
            "contribution_percent": 0.0,
            "first_commit_date": None,
            "last_commit_date": None,
        }

    commits_in_window = [
        c
        for c in user_commits
        if datetime.fromtimestamp(c.committed_date) >= window_start
    ]

    first_commit = datetime.fromtimestamp(user_commits[-1].committed_date)
    last_commit = datetime.fromtimestamp(user_commits[0].committed_date)

    delta = last_commit - first_commit
    weeks = delta.total_seconds() / 604800 if delta.total_seconds() > 0 else 1
    commit_frequency = len(user_commits) / weeks

    total_count = len(all_commits) if all_commits else 1
    contribution_percent = (len(user_commits) / total_count) * 100

    return {
        "commit_count_window": len(commits_in_window),
        "commit_frequency": round(commit_frequency, 2),
        "contribution_percent": round(contribution_percent, 2),
        "first_commit_date": first_commit,
        "last_commit_date": last_commit,
    }


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
