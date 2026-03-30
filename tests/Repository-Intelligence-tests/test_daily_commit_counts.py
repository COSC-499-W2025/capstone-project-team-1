from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from artifactminer.RepositoryIntelligence.repo_intelligence_user import (
    get_daily_commit_counts,
)


def test_get_daily_commit_counts_counts_per_day(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    completed = CompletedProcess(
        args=["git", "log"],
        returncode=0,
        stdout="2024-01-15\n2024-01-15\n2024-01-16\n",
        stderr="",
    )

    with patch(
        "artifactminer.RepositoryIntelligence.repo_intelligence_user.subprocess.run",
        return_value=completed,
    ) as mock_run:
        result = get_daily_commit_counts(repo_path, "dev@example.com")

    assert result == {"2024-01-15": 2, "2024-01-16": 1}
    mock_run.assert_called_once()


def test_get_daily_commit_counts_returns_empty_for_git_error(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    completed = CompletedProcess(
        args=["git", "log"],
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
    )

    with patch(
        "artifactminer.RepositoryIntelligence.repo_intelligence_user.subprocess.run",
        return_value=completed,
    ):
        result = get_daily_commit_counts(repo_path, "dev@example.com")

    assert result == {}


def test_get_daily_commit_counts_returns_empty_for_timeout(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    with patch(
        "artifactminer.RepositoryIntelligence.repo_intelligence_user.subprocess.run",
        side_effect=TimeoutExpired(cmd=["git", "log"], timeout=30),
    ):
        result = get_daily_commit_counts(repo_path, "dev@example.com")

    assert result == {}


def test_get_daily_commit_counts_returns_empty_for_empty_output(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    completed = CompletedProcess(
        args=["git", "log"],
        returncode=0,
        stdout="",
        stderr="",
    )

    with patch(
        "artifactminer.RepositoryIntelligence.repo_intelligence_user.subprocess.run",
        return_value=completed,
    ):
        result = get_daily_commit_counts(repo_path, "dev@example.com")

    assert result == {}
