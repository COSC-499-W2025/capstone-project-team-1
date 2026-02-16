"""Bridge git stats into evidence items."""

from __future__ import annotations

from datetime import date, datetime
from typing import List

from artifactminer.evidence.models import EvidenceItem
from artifactminer.skills.deep_analysis import GitStatsResult


def _coerce_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return None


def git_stats_to_evidence(
    git_stats: GitStatsResult,
) -> List[EvidenceItem]:
    """Convert git contribution metrics to evidence items."""
    items: List[EvidenceItem] = []

    if not git_stats:
        return items

    evidence_date = _coerce_date(git_stats.last_commit_date)

    if git_stats.contribution_percent > 0:
        items.append(
            EvidenceItem(
                type="metric",
                content=f"Contributed {git_stats.contribution_percent:.1f}% of repository commits",
                source="git_stats",
                date=evidence_date,
            )
        )

    if git_stats.commit_frequency > 0:
        items.append(
            EvidenceItem(
                type="metric",
                content=f"Commit frequency: {git_stats.commit_frequency:.2f} commits/week",
                source="git_stats",
                date=evidence_date,
            )
        )

    if git_stats.commit_count_window > 0:
        items.append(
            EvidenceItem(
                type="metric",
                content=f"{git_stats.commit_count_window} commits in last 90 days",
                source="git_stats",
                date=evidence_date,
            )
        )

    if git_stats.has_branches and git_stats.branch_count > 1:
        items.append(
            EvidenceItem(
                type="metric",
                content=f"Uses branching workflow ({git_stats.branch_count} branches)",
                source="git_patterns",
                date=evidence_date,
            )
        )

    if git_stats.has_tags:
        items.append(
            EvidenceItem(
                type="metric",
                content="Uses git tags for releases",
                source="git_patterns",
                date=evidence_date,
            )
        )

    if git_stats.merge_commits > 0:
        items.append(
            EvidenceItem(
                type="metric",
                content=f"Performed {git_stats.merge_commits} merge commits",
                source="git_patterns",
                date=evidence_date,
            )
        )

    return items
