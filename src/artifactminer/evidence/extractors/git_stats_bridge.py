"""Bridge git stats into evidence items."""

from __future__ import annotations

from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.evidence.utils import coerce_date
from artifactminer.skills.models import GitStatsResult


def git_stats_to_evidence(git_stats: GitStatsResult) -> List[EvidenceItem]:
    """Convert git contribution metrics to evidence items."""
    if not git_stats:
        return []

    evidence_date = coerce_date(git_stats.last_commit_date)
    items: List[EvidenceItem] = []

    _RULES = [
        (git_stats.contribution_percent > 0,
         f"Contributed {git_stats.contribution_percent:.1f}% of repository commits", "git_stats"),
        (git_stats.commit_frequency > 0,
         f"Commit frequency: {git_stats.commit_frequency:.2f} commits/week", "git_stats"),
        (git_stats.commit_count_window > 0,
         f"{git_stats.commit_count_window} commits in last 90 days", "git_stats"),
        (git_stats.has_branches and git_stats.branch_count > 1,
         f"Uses branching workflow ({git_stats.branch_count} branches)", "git_patterns"),
        (git_stats.has_tags,
         "Uses git tags for releases", "git_patterns"),
        (git_stats.merge_commits > 0,
         f"Performed {git_stats.merge_commits} merge commits", "git_patterns"),
    ]

    for condition, content, source in _RULES:
        if condition:
            items.append(EvidenceItem(type="metric", content=content, source=source, date=evidence_date))

    return items
