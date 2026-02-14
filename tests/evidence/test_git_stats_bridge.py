"""Tests for git_stats_bridge extractor."""

from datetime import datetime

from artifactminer.evidence.extractors.git_stats_bridge import git_stats_to_evidence
from artifactminer.skills.deep_analysis import GitStatsResult


def test_git_stats_to_evidence_returns_empty_for_none():
    result = git_stats_to_evidence(None)
    assert result == []


def test_git_stats_to_evidence_generates_other_evidence_when_commit_window_zero():
    """Verify that when commit_count_window is 0, other evidence is still generated."""
    git_stats = GitStatsResult(
        commit_count_window=0,
        contribution_percent=25.5,
        commit_frequency=2.0,
        last_commit_date=datetime(2024, 6, 1),
    )
    result = git_stats_to_evidence(git_stats)

    # Should generate contribution and frequency evidence
    assert len(result) == 2
    
    contribution_item = next((i for i in result if "Contributed" in i.content), None)
    assert contribution_item is not None
    assert contribution_item.type == "metric"
    assert "25.5%" in contribution_item.content
    
    freq_item = next((i for i in result if "frequency" in i.content), None)
    assert freq_item is not None
    assert freq_item.type == "metric"
    
    # Should NOT generate "commits in last 90 days" evidence
    window_item = next((i for i in result if "commits in last 90 days" in i.content), None)
    assert window_item is None


def test_git_stats_to_evidence_converts_contribution_percent():
    git_stats = GitStatsResult(
        commit_count_window=10,
        contribution_percent=25.5,
        commit_frequency=2.0,
        last_commit_date=datetime(2024, 6, 1),
    )
    result = git_stats_to_evidence(git_stats)

    assert len(result) >= 1
    contribution_item = next((i for i in result if i.type == "metric" and "Contributed" in i.content), None)
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

    activity_items = [i for i in result if i.type == "metric"]
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

    workflow_items = [i for i in result if i.type == "metric" and any(k in i.content for k in ("workflow", "tags", "merge"))]
    assert len(workflow_items) >= 3

    branch_item = next(
        (i for i in workflow_items if "branch" in i.content.lower()), None
    )
    assert branch_item is not None

    tag_item = next((i for i in workflow_items if "tag" in i.content.lower()), None)
    assert tag_item is not None

    merge_item = next((i for i in workflow_items if "merge" in i.content.lower()), None)
    assert merge_item is not None


def test_git_stats_to_evidence_keeps_workflow_when_commit_window_zero():
    git_stats = GitStatsResult(
        commit_count_window=0,
        contribution_percent=0.0,
        commit_frequency=0.0,
        has_branches=True,
        branch_count=4,
        has_tags=True,
        merge_commits=3,
    )
    result = git_stats_to_evidence(git_stats)

    assert not any("commits in last 90 days" in item.content for item in result)
    assert any("branching workflow" in item.content for item in result)
    assert any("git tags" in item.content for item in result)
    assert any("merge commits" in item.content for item in result)
