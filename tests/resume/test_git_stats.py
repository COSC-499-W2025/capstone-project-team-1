"""Tests for the Strategy A extractors: git_stats, test_ratio, commit_quality, cross_module."""

from __future__ import annotations

import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from git import Repo

from artifactminer.resume.extractors.git_stats import extract_git_stats
from artifactminer.resume.extractors.test_ratio import extract_test_ratio
from artifactminer.resume.extractors.commit_quality import (
    extract_commit_quality,
    _compute_longest_streak,
)
from artifactminer.resume.extractors.cross_module import extract_cross_module_breadth
from artifactminer.resume.models import CommitGroup


TEST_EMAIL = "dev@example.com"
TEST_NAME = "Test Developer"


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def stats_repo(tmp_path: Path) -> Path:
    """Create a git repo with known commit history for stats testing."""
    repo_dir = tmp_path / "stats-project"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)
    repo.config_writer().set_value("user", "email", TEST_EMAIL).release()
    repo.config_writer().set_value("user", "name", TEST_NAME).release()

    # Create directory structure
    (repo_dir / "src" / "api").mkdir(parents=True)
    (repo_dir / "src" / "models").mkdir(parents=True)
    (repo_dir / "tests").mkdir()
    (repo_dir / "docs").mkdir()

    # Commit 1: add source file
    main_py = repo_dir / "src" / "api" / "main.py"
    main_py.write_text("def hello():\n    return 'hello'\n\ndef goodbye():\n    return 'bye'\n")
    repo.index.add(["src/api/main.py"])
    repo.index.commit("feat: add main module")

    # Commit 2: add model
    model_py = repo_dir / "src" / "models" / "user.py"
    model_py.write_text("class User:\n    pass\n")
    repo.index.add(["src/models/user.py"])
    repo.index.commit("feat: add User model")

    # Commit 3: add test
    test_py = repo_dir / "tests" / "test_main.py"
    test_py.write_text("def test_hello():\n    assert True\n")
    repo.index.add(["tests/test_main.py"])
    repo.index.commit("test: add unit tests")

    # Commit 4: modify source (bug fix)
    main_py.write_text("def hello():\n    return 'hello world'\n\ndef goodbye():\n    return 'bye'\n")
    repo.index.add(["src/api/main.py"])
    repo.index.commit("fix: update hello return value")

    # Commit 5: add docs
    readme = repo_dir / "docs" / "guide.md"
    readme.write_text("# Guide\n\nUsage instructions.\n")
    repo.index.add(["docs/guide.md"])
    repo.index.commit("docs: add usage guide")

    # CI config
    (repo_dir / ".github" / "workflows").mkdir(parents=True)
    ci_yml = repo_dir / ".github" / "workflows" / "ci.yml"
    ci_yml.write_text("name: CI\non: push\n")
    repo.index.add([".github/workflows/ci.yml"])
    repo.index.commit("chore: add CI workflow")

    return repo_dir


# ── GitStats extractor ───────────────────────────────────────────────


class TestExtractGitStats:
    """Tests for the git_stats extractor."""

    def test_counts_lines_added(self, stats_repo: Path) -> None:
        """Should count total lines added by the user."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert stats.lines_added > 0

    def test_counts_lines_deleted(self, stats_repo: Path) -> None:
        """Should count total lines deleted (the fix commit changed a line)."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert stats.lines_deleted >= 0

    def test_net_lines_computed(self, stats_repo: Path) -> None:
        """Net lines should equal added minus deleted."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert stats.net_lines == stats.lines_added - stats.lines_deleted

    def test_files_touched(self, stats_repo: Path) -> None:
        """Should count unique files modified by user."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert stats.files_touched >= 4  # main.py, user.py, test_main.py, guide.md

    def test_file_hotspots_ranked(self, stats_repo: Path) -> None:
        """File hotspots should be ordered by edit frequency."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert len(stats.file_hotspots) > 0
        # main.py was edited twice (commit 1 + 4)
        top_file, top_count = stats.file_hotspots[0]
        assert top_count >= 2

    def test_active_days(self, stats_repo: Path) -> None:
        """Should count distinct commit days (all on same day in fixture)."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert stats.active_days >= 1

    def test_avg_commit_size(self, stats_repo: Path) -> None:
        """Should compute average lines changed per commit."""
        stats = extract_git_stats(str(stats_repo), TEST_EMAIL)
        assert stats.avg_commit_size > 0

    def test_empty_for_unknown_email(self, stats_repo: Path) -> None:
        """Should return empty GitStats for a user with no commits."""
        stats = extract_git_stats(str(stats_repo), "nobody@example.com")
        assert stats.lines_added == 0
        assert stats.files_touched == 0

    def test_empty_for_invalid_repo(self, tmp_path: Path) -> None:
        """Should return empty GitStats for a non-repo path."""
        stats = extract_git_stats(str(tmp_path), TEST_EMAIL)
        assert stats.lines_added == 0


# ── TestRatio extractor ──────────────────────────────────────────────


class TestExtractTestRatio:
    """Tests for the test_ratio extractor."""

    def test_counts_test_files(self, stats_repo: Path) -> None:
        """Should detect test files from module_groups."""
        module_groups = {
            "src": ["src/api/main.py", "src/models/user.py"],
            "tests": ["tests/test_main.py"],
        }
        ratio = extract_test_ratio(str(stats_repo), module_groups)
        assert ratio.test_files == 1

    def test_counts_source_files(self, stats_repo: Path) -> None:
        """Should count non-test source files."""
        module_groups = {
            "src": ["src/api/main.py", "src/models/user.py"],
            "tests": ["tests/test_main.py"],
        }
        ratio = extract_test_ratio(str(stats_repo), module_groups)
        assert ratio.source_files == 2

    def test_computes_ratio(self, stats_repo: Path) -> None:
        """Should compute test_files / source_files ratio."""
        module_groups = {
            "src": ["src/api/main.py", "src/models/user.py"],
            "tests": ["tests/test_main.py"],
        }
        ratio = extract_test_ratio(str(stats_repo), module_groups)
        assert ratio.test_ratio == 0.5

    def test_detects_ci(self, stats_repo: Path) -> None:
        """Should detect CI config presence."""
        ratio = extract_test_ratio(str(stats_repo), {})
        assert ratio.has_ci is True

    def test_no_ci_when_absent(self, tmp_path: Path) -> None:
        """Should return has_ci=False when no CI config exists."""
        ratio = extract_test_ratio(str(tmp_path), {})
        assert ratio.has_ci is False

    def test_zero_ratio_for_no_source(self, tmp_path: Path) -> None:
        """Should return 0 ratio when no source files exist."""
        ratio = extract_test_ratio(str(tmp_path), {"tests": ["tests/test_x.py"]})
        assert ratio.test_ratio == 0.0


# ── CommitQuality extractor ──────────────────────────────────────────


class TestExtractCommitQuality:
    """Tests for the commit_quality extractor."""

    def test_conventional_percentage(self) -> None:
        """Should compute percentage of conventional-format commits."""
        groups = [
            CommitGroup(category="feature", messages=["feat: add login", "feat: add signup"]),
            CommitGroup(category="bugfix", messages=["fixed a bug"]),
        ]
        quality = extract_commit_quality(groups)
        # 2 out of 3 are conventional
        assert quality.conventional_pct == pytest.approx(66.7, abs=0.1)

    def test_avg_message_length(self) -> None:
        """Should compute average message length."""
        groups = [
            CommitGroup(category="feature", messages=["feat: add X", "feat: add Y"]),
        ]
        quality = extract_commit_quality(groups)
        assert quality.avg_message_length > 0

    def test_type_diversity(self) -> None:
        """Should count distinct commit categories."""
        groups = [
            CommitGroup(category="feature", messages=["feat: add X"]),
            CommitGroup(category="bugfix", messages=["fix: Y"]),
            CommitGroup(category="test", messages=["test: Z"]),
        ]
        quality = extract_commit_quality(groups)
        assert quality.type_diversity == 3

    def test_empty_groups(self) -> None:
        """Should handle empty commit groups gracefully."""
        quality = extract_commit_quality([])
        assert quality.conventional_pct == 0.0
        assert quality.type_diversity == 0

    def test_longest_streak_consecutive(self) -> None:
        """Should compute longest consecutive-day streak."""
        now = datetime.now(tz=timezone.utc)
        dates = [
            now,
            now - timedelta(days=1),
            now - timedelta(days=2),
            now - timedelta(days=5),
        ]
        groups = [
            CommitGroup(category="feature", messages=["a", "b", "c", "d"]),
        ]
        quality = extract_commit_quality(groups, commit_dates=dates)
        assert quality.longest_streak == 3

    def test_streak_single_day(self) -> None:
        """Should return 1 for a single commit day."""
        now = datetime.now(tz=timezone.utc)
        assert _compute_longest_streak([now]) == 1


# ── CrossModuleBreadth extractor ─────────────────────────────────────


class TestExtractCrossModuleBreadth:
    """Tests for the cross_module extractor."""

    def test_counts_modules_touched(self) -> None:
        """Should count top-level modules with user changes."""
        module_groups = {
            "src": ["src/main.py"],
            "tests": ["tests/test_main.py"],
            "(root)": ["README.md"],
        }
        directory_overview = ["src", "tests", "docs", "scripts"]
        breadth = extract_cross_module_breadth(module_groups, directory_overview)
        assert breadth.modules_touched == 2  # src, tests (root excluded)

    def test_total_modules(self) -> None:
        """Should count all top-level directories."""
        module_groups = {"src": ["src/main.py"]}
        directory_overview = ["src", "tests", "docs"]
        breadth = extract_cross_module_breadth(module_groups, directory_overview)
        assert breadth.total_modules == 3

    def test_breadth_percentage(self) -> None:
        """Should compute correct breadth percentage."""
        module_groups = {"src": ["src/main.py"], "tests": ["tests/test_x.py"]}
        directory_overview = ["src", "tests", "docs", "scripts"]
        breadth = extract_cross_module_breadth(module_groups, directory_overview)
        assert breadth.breadth_pct == 50.0

    def test_deepest_path(self) -> None:
        """Should find the deepest nested file path."""
        module_groups = {
            "src": ["src/api/v2/routes/users.py", "src/main.py"],
        }
        directory_overview = ["src"]
        breadth = extract_cross_module_breadth(module_groups, directory_overview)
        assert breadth.deepest_path == "src/api/v2/routes/users.py"

    def test_empty_modules(self) -> None:
        """Should handle empty inputs gracefully."""
        breadth = extract_cross_module_breadth({}, [])
        assert breadth.modules_touched == 0
        assert breadth.breadth_pct == 0.0
        assert breadth.deepest_path == ""
