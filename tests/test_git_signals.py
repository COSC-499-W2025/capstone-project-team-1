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
    @patch("artifactminer.skills.signals.git_signals.git.Repo")
    def test_returns_empty_dict_on_repo_exception(
        self, mock_repo, mock_is_git, tmp_path
    ):
        mock_is_git.return_value = True
        mock_repo.side_effect = Exception("repo error")
        result = get_git_stats(str(tmp_path), "user@example.com")
        assert result == {}

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.git.Repo")
    def test_returns_zero_stats_for_user_with_no_commits(
        self, mock_repo, mock_is_git, tmp_path
    ):
        mock_is_git.return_value = True
        mock_repo_instance = MagicMock()
        mock_repo_instance.iter_commits.return_value = []
        mock_repo.return_value = mock_repo_instance

        result = get_git_stats(str(tmp_path), "user@example.com")

        assert result["commit_count_window"] == 0
        assert result["commit_frequency"] == 0.0
        assert result["contribution_percent"] == 0.0
        assert result["first_commit_date"] is None
        assert result["last_commit_date"] is None

    @patch("artifactminer.skills.signals.git_signals.isGitRepo")
    @patch("artifactminer.skills.signals.git_signals.git.Repo")
    def test_calculates_commit_metrics_correctly(
        self, mock_repo, mock_is_git, tmp_path
    ):
        mock_is_git.return_value = True
        mock_repo_instance = MagicMock()

        now_ts = datetime.now().timestamp()
        two_weeks_ago_ts = (datetime.now() - timedelta(days=14)).timestamp()

        user_commit1 = MagicMock()
        user_commit1.author.email = "User@Example.com"
        user_commit1.committed_date = now_ts
        user_commit1.parents = []

        user_commit2 = MagicMock()
        user_commit2.author.email = "user@example.com"
        user_commit2.committed_date = two_weeks_ago_ts
        user_commit2.parents = []

        other_commit = MagicMock()
        other_commit.author.email = "other@example.com"
        other_commit.committed_date = now_ts
        other_commit.parents = []

        mock_repo_instance.iter_commits.return_value = [
            user_commit1,
            user_commit2,
            other_commit,
        ]
        mock_repo.return_value = mock_repo_instance

        result = get_git_stats(str(tmp_path), "user@example.com", window_days=30)

        assert result["commit_count_window"] == 2
        assert result["contribution_percent"] == pytest.approx(66.67, rel=0.01)
        assert result["first_commit_date"] is not None
        assert result["last_commit_date"] is not None


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
