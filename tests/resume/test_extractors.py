"""Tests for the v3 resume pipeline extractors."""

from __future__ import annotations

from pathlib import Path

from artifactminer.resume.extractors.readme import extract_readme
from artifactminer.resume.extractors.commits import (
    extract_and_classify_commits,
    _classify_static,
)
from artifactminer.resume.extractors.structure import extract_structure
from artifactminer.resume.extractors.constructs import extract_constructs
from artifactminer.resume.extractors.project_type import infer_project_type
from artifactminer.resume.models import CommitGroup


TEST_EMAIL = "dev@example.com"


# ── README extractor ──────────────────────────────────────────────────


class TestExtractReadme:
    """Tests for the README extractor."""

    def test_extracts_readme_content(self, sample_repo: Path) -> None:
        """Should return the README text."""
        text = extract_readme(str(sample_repo))
        assert "My Web API" in text
        assert "FastAPI" in text

    def test_respects_max_chars(self, sample_repo: Path) -> None:
        """Should truncate to max_chars."""
        text = extract_readme(str(sample_repo), max_chars=30)
        assert len(text) <= 30

    def test_returns_empty_for_missing_readme(self, tmp_path: Path) -> None:
        """Should return empty string when no README exists."""
        text = extract_readme(str(tmp_path))
        assert text == ""


# ── Commit classifier (static regex) ─────────────────────────────────


class TestClassifyStatic:
    """Tests for the regex-based commit classifier."""

    def test_conventional_feat(self) -> None:
        """Should classify 'feat: ...' as feature."""
        assert _classify_static("feat: add login page") == "feature"

    def test_conventional_fix(self) -> None:
        """Should classify 'fix: ...' as bugfix."""
        assert _classify_static("fix: resolve null pointer") == "bugfix"

    def test_conventional_with_scope(self) -> None:
        """Should handle scope in conventional commits."""
        assert _classify_static("feat(auth): add JWT support") == "feature"

    def test_conventional_test(self) -> None:
        """Should classify 'test: ...' as test."""
        assert _classify_static("test: add unit tests for auth") == "test"

    def test_conventional_docs(self) -> None:
        """Should classify 'docs: ...' as docs."""
        assert _classify_static("docs: update README") == "docs"

    def test_conventional_chore(self) -> None:
        """Should classify 'chore: ...' as chore."""
        assert _classify_static("chore: bump version") == "chore"

    def test_keyword_add(self) -> None:
        """Should classify 'Add ...' via keyword heuristic."""
        assert _classify_static("Add user registration flow") == "feature"

    def test_keyword_fix(self) -> None:
        """Should classify 'Fix ...' via keyword heuristic."""
        assert _classify_static("Fix crash on empty input") == "bugfix"

    def test_keyword_refactor(self) -> None:
        """Should classify refactoring commits."""
        assert _classify_static("Refactor database connection pool") == "refactor"

    def test_unclassifiable_returns_none(self) -> None:
        """Should return None for ambiguous messages."""
        assert _classify_static("Update thing") is None


# ── Commit extractor (full pipeline, no LLM) ─────────────────────────


class TestExtractAndClassifyCommits:
    """Tests for the full commit extraction pipeline."""

    def test_extracts_commits_from_repo(self, sample_repo: Path) -> None:
        """Should return CommitGroup objects with messages."""
        groups = extract_and_classify_commits(str(sample_repo), TEST_EMAIL)
        assert len(groups) > 0
        assert all(isinstance(g, CommitGroup) for g in groups)

    def test_groups_have_correct_categories(self, sample_repo: Path) -> None:
        """Should classify commits into known categories."""
        groups = extract_and_classify_commits(str(sample_repo), TEST_EMAIL)
        categories = {g.category for g in groups}
        # Our sample repo has feat, fix, refactor, test, docs, chore commits
        assert "feature" in categories
        assert "bugfix" in categories

    def test_commit_messages_are_populated(self, sample_repo: Path) -> None:
        """Each group should contain actual commit messages."""
        groups = extract_and_classify_commits(str(sample_repo), TEST_EMAIL)
        total_msgs = sum(g.count for g in groups)
        assert total_msgs >= 5  # we made 7 commits in the fixture

    def test_filters_by_user_email(self, sample_repo: Path) -> None:
        """Should return empty for an email with no commits."""
        groups = extract_and_classify_commits(str(sample_repo), "nobody@example.com")
        total = sum(g.count for g in groups)
        assert total == 0


# ── Structure extractor ───────────────────────────────────────────────


class TestExtractStructure:
    """Tests for the directory structure extractor."""

    def test_returns_top_level_dirs(self, sample_repo: Path) -> None:
        """Should list top-level directories."""
        dirs, _ = extract_structure(str(sample_repo), TEST_EMAIL)
        assert "src" in dirs
        assert "tests" in dirs

    def test_excludes_hidden_dirs(self, sample_repo: Path) -> None:
        """Should not include .git or other hidden directories."""
        dirs, _ = extract_structure(str(sample_repo), TEST_EMAIL)
        assert ".git" not in dirs

    def test_module_groups_populated(self, sample_repo: Path) -> None:
        """Should group user-touched files by module."""
        _, modules = extract_structure(str(sample_repo), TEST_EMAIL)
        assert len(modules) > 0
        # src/ should have files
        assert "src" in modules
        assert len(modules["src"]) > 0


# ── Constructs extractor ──────────────────────────────────────────────


class TestExtractConstructs:
    """Tests for the code construct extractor."""

    def test_finds_routes(self, sample_repo: Path) -> None:
        """Should detect FastAPI route definitions."""
        constructs = extract_constructs(str(sample_repo))
        assert len(constructs.routes) > 0
        route_strs = " ".join(constructs.routes)
        assert "/api/users" in route_strs

    def test_finds_classes(self, sample_repo: Path) -> None:
        """Should detect class definitions."""
        constructs = extract_constructs(str(sample_repo))
        class_names = constructs.classes
        assert "User" in class_names

    def test_finds_test_functions(self, sample_repo: Path) -> None:
        """Should detect test function names."""
        constructs = extract_constructs(str(sample_repo))
        assert len(constructs.test_functions) > 0
        assert "test_list_users" in constructs.test_functions

    def test_finds_key_functions(self, sample_repo: Path) -> None:
        """Should detect non-test, non-dunder functions."""
        constructs = extract_constructs(str(sample_repo))
        func_names = constructs.key_functions
        assert "authenticate" in func_names

    def test_scoped_to_touched_files(self, sample_repo: Path) -> None:
        """Should only scan provided files when touched_files is set."""
        constructs = extract_constructs(
            str(sample_repo),
            touched_files={"src/api/auth.py"},
        )
        # Should find auth functions but not route decorators
        assert "authenticate" in constructs.key_functions
        assert len(constructs.routes) == 0


# ── Project type inference ────────────────────────────────────────────


class TestInferProjectType:
    """Tests for project type inference."""

    def test_detects_web_api_from_frameworks(self, sample_repo: Path) -> None:
        """Should identify a FastAPI project as Web API."""
        ptype = infer_project_type(
            str(sample_repo),
            frameworks=["FastAPI"],
            readme_text="A REST API built with FastAPI",
        )
        assert ptype == "Web API"

    def test_detects_cli_tool(self, tmp_path: Path) -> None:
        """Should identify CLI tool from frameworks."""
        ptype = infer_project_type(
            str(tmp_path),
            frameworks=["Typer", "Click"],
        )
        assert ptype == "CLI Tool"

    def test_fallback_to_software_project(self, tmp_path: Path) -> None:
        """Should return generic type when no signals match."""
        ptype = infer_project_type(str(tmp_path))
        assert ptype == "Software Project"

    def test_readme_keywords_boost_scores(self, tmp_path: Path) -> None:
        """README keywords should contribute to type scoring."""
        ptype = infer_project_type(
            str(tmp_path),
            readme_text="This is a command-line CLI tool for data processing",
        )
        assert ptype == "CLI Tool"
