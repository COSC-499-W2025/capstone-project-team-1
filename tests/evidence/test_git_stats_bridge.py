"""Tests for git_stats_bridge extractor."""

from datetime import datetime

from artifactminer.evidence.extractors.git_stats_bridge import git_stats_to_evidence
from artifactminer.skills.deep_analysis import GitStatsResult


def test_git_stats_to_evidence_returns_empty_for_zero_commits():
    git_stats = GitStatsResult(commit_count_window=0)
    result = git_stats_to_evidence(git_stats)
    assert result == []


def test_git_stats_to_evidence_converts_contribution_percent():
    git_stats = GitStatsResult(
        commit_count_window=10,
        contribution_percent=25.5,
        commit_frequency=2.0,
        last_commit_date=datetime(2024, 6, 1),
    )
    result = git_stats_to_evidence(git_stats)

    assert len(result) >= 1
    contribution_item = next((i for i in result if i.type == "contribution"), None)
    assert contribution_item is not None
    assert "25.5%" in contribution_item.content
    assert contribution_item.source == "git_stats"


def test_git_stats_to_evidence_includes_activity():
    git_stats = GitStatsResult(
        commit_count_window=10,
        contribution_percent=50.0,
        commit_frequency=3.5,
    )
    result = git_stats_to_evidence(git_stats)

    activity_items = [i for i in result if i.type == "activity"]
    assert len(activity_items) >= 2

    freq_item = next((i for i in activity_items if "frequency" in i.content), None)
    assert freq_item is not None
    assert "3.50" in freq_item.content


def test_git_stats_to_evidence_includes_workflow_patterns():
    git_stats = GitStatsResult(
        commit_count_window=5,
        contribution_percent=10.0,
        has_branches=True,
        branch_count=3,
        has_tags=True,
        merge_commits=2,
    )
    result = git_stats_to_evidence(git_stats)

    workflow_items = [i for i in result if i.type == "workflow"]
    assert len(workflow_items) >= 3

    branch_item = next(
        (i for i in workflow_items if "branch" in i.content.lower()), None
    )
    assert branch_item is not None

    tag_item = next((i for i in workflow_items if "tag" in i.content.lower()), None)
    assert tag_item is not None

    merge_item = next((i for i in workflow_items if "merge" in i.content.lower()), None)
    assert merge_item is not None
