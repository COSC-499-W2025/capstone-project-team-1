"""
Commit quality extractor — score overall commit discipline.

Measures conventional commit adoption, message quality, type diversity,
and longest consecutive-day commit streak.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List

from ..models import CommitGroup, CommitQuality

# Conventional-commit regex: type(scope)?: message
_CONVENTIONAL_RE = re.compile(
    r"^[a-z]+(?:\([^)]*\))?[!]?:\s", re.IGNORECASE
)


def extract_commit_quality(
    commit_groups: List[CommitGroup],
    commit_dates: List[datetime] | None = None,
) -> CommitQuality:
    """
    Score overall commit quality from already-classified commit groups.

    Args:
        commit_groups: List of CommitGroup from extract_and_classify_commits.
        commit_dates: Optional list of commit datetimes for streak calculation.

    Returns:
        CommitQuality with metrics about commit discipline.
    """
    all_messages: list[str] = []
    for g in commit_groups:
        all_messages.extend(g.messages)

    if not all_messages:
        return CommitQuality()

    # Conventional commit percentage
    conventional_count = sum(
        1 for msg in all_messages if _CONVENTIONAL_RE.match(msg)
    )
    conventional_pct = round(conventional_count / len(all_messages) * 100, 1)

    # Average message length
    avg_length = round(
        sum(len(msg) for msg in all_messages) / len(all_messages), 1
    )

    # Type diversity: how many distinct categories used
    type_diversity = len([g for g in commit_groups if g.count > 0])

    # Longest consecutive-day streak
    longest_streak = _compute_longest_streak(commit_dates) if commit_dates else 0

    return CommitQuality(
        conventional_pct=conventional_pct,
        avg_message_length=avg_length,
        type_diversity=type_diversity,
        longest_streak=longest_streak,
    )


def _compute_longest_streak(dates: List[datetime]) -> int:
    """Compute longest consecutive-day commit streak."""
    if not dates:
        return 0

    unique_days = sorted({dt.date() for dt in dates})
    if len(unique_days) == 1:
        return 1

    longest = 1
    current = 1
    for i in range(1, len(unique_days)):
        if unique_days[i] - unique_days[i - 1] == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest
