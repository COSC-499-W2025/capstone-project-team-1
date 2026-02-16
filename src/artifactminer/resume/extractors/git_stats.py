"""
Git statistics extractor — quantitative impact signals per user per repo.

Extracts lines added/deleted, files touched, hotspots, active days, etc.
Data source: git log --numstat via GitPython.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import List, Tuple

from git import Repo

from ..models import GitStats

log = logging.getLogger(__name__)


def extract_git_stats(
    repo_path: str,
    user_email: str,
    *,
    max_commits: int = 500,
) -> GitStats:
    """
    Extract quantitative impact signals for a user in a repo.

    Returns a GitStats dataclass with lines added/deleted, files touched,
    file hotspots, active days, active span, and average commit size.
    """
    try:
        repo = Repo(repo_path)
    except Exception:
        log.warning("Could not open repo at %s", repo_path)
        return GitStats()

    lines_added = 0
    lines_deleted = 0
    file_edits: Counter[str] = Counter()
    commit_dates: list[datetime] = []
    commit_sizes: list[int] = []
    count = 0

    for commit in repo.iter_commits():
        if count >= max_commits:
            break
        if not (commit.author.email and commit.author.email.lower() == user_email.lower()):
            continue
        count += 1

        # Track commit date
        commit_dates.append(commit.committed_datetime)

        # Parse numstat from commit.stats
        commit_added = 0
        commit_deleted = 0
        for path, stat in commit.stats.files.items():
            ins = stat.get("insertions", 0)
            dels = stat.get("deletions", 0)
            lines_added += ins
            lines_deleted += dels
            commit_added += ins
            commit_deleted += dels
            file_edits[path] += 1

        commit_sizes.append(commit_added + commit_deleted)

    if not commit_dates:
        return GitStats()

    # File hotspots: top 10 by edit frequency
    hotspots: List[Tuple[str, int]] = file_edits.most_common(10)

    # Active days: distinct calendar dates
    unique_days = {dt.date() for dt in commit_dates}
    active_days = len(unique_days)

    # Active span: first to last commit
    sorted_dates = sorted(commit_dates)
    span = (sorted_dates[-1] - sorted_dates[0]).days

    # Average commit size
    avg_size = sum(commit_sizes) / len(commit_sizes) if commit_sizes else 0.0

    return GitStats(
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        net_lines=lines_added - lines_deleted,
        files_touched=len(file_edits),
        file_hotspots=hotspots,
        active_days=active_days,
        active_span_days=span,
        avg_commit_size=round(avg_size, 1),
    )
