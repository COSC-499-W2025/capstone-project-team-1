from __future__ import annotations

from pathlib import Path

from artifactminer.resume.generate import discover_git_repos


def _make_git_dir(repo_path: Path) -> None:
    git_dir = repo_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")


def test_discover_git_repos_skips_macos_metadata_tree(tmp_path: Path) -> None:
    real_repo = tmp_path / "projects" / "real-repo"
    _make_git_dir(real_repo)

    metadata_repo = tmp_path / "__MACOSX" / "projects" / "real-repo"
    _make_git_dir(metadata_repo)

    repos = discover_git_repos(tmp_path)

    assert real_repo in repos
    assert metadata_repo not in repos
    assert len(repos) == 1


def test_discover_git_repos_skips_resource_fork_paths(tmp_path: Path) -> None:
    real_repo = tmp_path / "projects" / "real-repo"
    _make_git_dir(real_repo)

    resource_fork_repo = tmp_path / "projects" / "._real-repo"
    _make_git_dir(resource_fork_repo)

    repos = discover_git_repos(tmp_path)

    assert real_repo in repos
    assert resource_fork_repo not in repos
    assert len(repos) == 1


def test_discover_git_repos_requires_git_head_file(tmp_path: Path) -> None:
    valid_repo = tmp_path / "valid-repo"
    _make_git_dir(valid_repo)

    broken_repo = tmp_path / "broken-repo"
    (broken_repo / ".git").mkdir(parents=True, exist_ok=True)

    repos = discover_git_repos(tmp_path)

    assert valid_repo in repos
    assert broken_repo not in repos
    assert len(repos) == 1
