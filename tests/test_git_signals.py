"""Unit tests for git_signals module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from artifactminer.skills.signals.git_signals import get_git_stats, detect_git_patterns


class TestGetGitStats:
    def test_returns_empty_dict_for_non_git_repo(self, tmp_path):
        result = get_git_stats(str(tmp_path), "user@example.com")
        assert result == {}

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.getUserRepoStats")
    def test_returns_empty_dict_on_exception(
        self, mock_get_stats, mock_is_git, tmp_path
    ):
        mock_is_git.return_value = True
        mock_get_stats.side_effect = Exception("repo error")
        result = get_git_stats(str(tmp_path), "user@example.com")
        assert result == {}

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.getUserRepoStats")
    def test_returns_zero_stats_for_user_with_no_commits(
        self, mock_get_stats, mock_is_git, tmp_path
    ):
        mock_is_git.return_value = True
        mock_stats = MagicMock()
        mock_stats.total_commits = None
        mock_get_stats.return_value = mock_stats

        result = get_git_stats(str(tmp_path), "user@example.com")

        assert result["commit_count_window"] == 0
        assert result["commit_frequency"] == 0.0
        assert result["contribution_percent"] == 0.0
        assert result["first_commit_date"] is None
        assert result["last_commit_date"] is None

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.getUserRepoStats")
    @patch("artifactminer.skills.signals.git_signals._count_commits_in_window")
    def test_delegates_to_getUserRepoStats(
        self, mock_count, mock_get_stats, mock_is_git, tmp_path
    ):
        mock_is_git.return_value = True
        mock_stats = MagicMock()
        mock_stats.total_commits = 10
        mock_stats.commitFrequency = 2.5
        mock_stats.userStatspercentages = 33.33
        mock_stats.first_commit = datetime(2024, 1, 1)
        mock_stats.last_commit = datetime(2024, 6, 1)
        mock_get_stats.return_value = mock_stats
        mock_count.return_value = 5

        result = get_git_stats(str(tmp_path), "user@example.com", window_days=30)

        assert result["commit_count_window"] == 5
        assert result["commit_frequency"] == 2.5
        assert result["contribution_percent"] == 33.33
        assert result["first_commit_date"] == datetime(2024, 1, 1)
        assert result["last_commit_date"] == datetime(2024, 6, 1)

    @patch("artifactminer.skills.signals.git_signals.git.Repo")
    def test_count_commits_in_window(self, mock_repo, tmp_path):
        now = datetime.now()
        three_months_ago = now - timedelta(days=90)

        commit_recent = MagicMock()
        commit_recent.author.email = "user@example.com"
        commit_recent.committed_date = now.timestamp()

        commit_old = MagicMock()
        commit_old.author.email = "user@example.com"
        commit_old.committed_date = three_months_ago.timestamp()

        commit_other = MagicMock()
        commit_other.author.email = "other@example.com"
        commit_other.committed_date = now.timestamp()

        mock_repo.return_value.iter_commits.return_value = [
            commit_recent,
            commit_old,
            commit_other,
        ]

        from artifactminer.skills.signals.git_signals import _count_commits_in_window

        count = _count_commits_in_window(str(tmp_path), "user@example.com", 30)

        assert count == 1


class TestDetectGitPatterns:
    def test_returns_empty_dict_for_non_git_repo(self, tmp_path):
        result = detect_git_patterns(str(tmp_path))
        assert result == {}

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.git.Repo")
    def test_detects_branches_and_tags(self, mock_repo, mock_is_git, tmp_path):
        mock_is_git.return_value = True
        mock_repo_instance = MagicMock()

        mock_branch1 = MagicMock()
        mock_branch2 = MagicMock()
        mock_repo_instance.branches = [mock_branch1, mock_branch2]

        mock_tag1 = MagicMock()
        mock_repo_instance.tags = [mock_tag1]

        mock_repo_instance.iter_commits.return_value = []
        mock_repo.return_value = mock_repo_instance

        result = detect_git_patterns(str(tmp_path))

        assert result["has_branches"] is True
        assert result["branch_count"] == 2
        assert result["has_tags"] is True
        assert result["tag_count"] == 1

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.git.Repo")
    def test_counts_merge_commits(self, mock_repo, mock_is_git, tmp_path):
        mock_is_git.return_value = True
        mock_repo_instance = MagicMock()

        regular_commit = MagicMock()
        regular_commit.parents = [MagicMock()]

        merge_commit = MagicMock()
        merge_commit.parents = [MagicMock(), MagicMock()]

        mock_repo_instance.branches = []
        mock_repo_instance.tags = []
        mock_repo_instance.iter_commits.return_value = [
            regular_commit,
            merge_commit,
            merge_commit,
        ]
        mock_repo.return_value = mock_repo_instance

        result = detect_git_patterns(str(tmp_path))

        assert result["merge_commits"] == 2
