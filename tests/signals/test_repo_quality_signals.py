"""Tests for repo_quality_signals extraction."""

from pathlib import Path

import pytest

from artifactminer.skills.signals.repo_quality_signals import (
    detect_test_signals,
    detect_docs_signals,
    detect_quality_signals,
    get_repo_quality_signals,
)


def _make_repo(tmp_path: Path, files: dict[str, str]) -> str:
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return str(root)


def test_detect_test_signals_finds_test_files(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "tests/test_foo.py": "def test_x(): pass",
            "test_bar.py": "def test_y(): pass",
        }
    )
    result = detect_test_signals(repo)
    assert result["has_tests"] is True
    assert result["test_file_count"] >= 2


def test_detect_test_signals_respects_touched_paths(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "tests/test_foo.py": "def test_x(): pass",
            "other/test_bar.py": "def test_y(): pass",
        }
    )
    touched = {"tests/test_foo.py"}
    result = detect_test_signals(repo, touched_paths=touched)
    assert result["test_file_count"] == 1


def test_detect_docs_signals_finds_readme(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "README.md": "# Project",
            "CHANGELOG.md": "v1.0.0",
            "CONTRIBUTING.md": "Please open a PR",
        }
    )
    result = detect_docs_signals(repo)
    assert result["has_readme"] is True
    assert result["has_changelog"] is True
    assert result["has_contributing"] is True


@pytest.mark.parametrize("readme_name", ["readme.md", "Readme.md"])
def test_detect_docs_signals_handles_readme_casing(tmp_path, readme_name):
    repo = _make_repo(tmp_path, {readme_name: "# Project"})
    result = detect_docs_signals(repo)
    assert result["has_readme"] is True


def test_detect_docs_signals_respects_touched_paths(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "README.md": "# Project",
            "CHANGELOG.md": "v1.0.0",
        }
    )
    touched = {"README.md"}
    result = detect_docs_signals(repo, touched_paths=touched)
    assert result["has_readme"] is True
    assert result["has_changelog"] is False


def test_detect_quality_signals_finds_tools(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "pyproject.toml": "[tool.ruff]\n[tool.mypy]\n",
            ".pre-commit-config.yaml": "repos:\n",
        }
    )
    result = detect_quality_signals(repo)
    assert result["has_precommit"] is True
    assert result["has_lint_config"] is True
    assert result["has_type_check"] is True
    assert "ruff" in result["quality_tools"]
    assert "mypy" in result["quality_tools"]


def test_detect_quality_signals_respects_touched_paths(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "pyproject.toml": "[tool.ruff]\n",
            ".pre-commit-config.yaml": "repos:\n",
        }
    )
    touched = {"pyproject.toml"}
    result = detect_quality_signals(repo, touched_paths=touched)
    assert result["has_lint_config"] is True
    assert result["has_precommit"] is False


def test_detect_quality_signals_detects_mypy_from_dot_mypy_ini(tmp_path):
    repo = _make_repo(tmp_path, {".mypy.ini": "[mypy]\npython_version = 3.11\n"})
    result = detect_quality_signals(repo)
    assert result["has_type_check"] is True
    assert "mypy" in result["quality_tools"]


def test_get_repo_quality_signals_aggregates_all(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "tests/test_x.py": "def test_x(): pass",
            "README.md": "# Project",
            "pyproject.toml": "[tool.ruff]\n",
        }
    )
    result = get_repo_quality_signals(repo)
    assert result.has_tests is True
    assert result.has_readme is True
    assert result.has_lint_config is True


def test_get_repo_quality_signals_propagates_contributing(tmp_path):
    repo = _make_repo(
        tmp_path,
        {
            "CONTRIBUTING.md": "Please follow style guide",
        }
    )
    result = get_repo_quality_signals(repo)
    assert result.has_contributing is True
    assert result.has_readme is False


def test_empty_repo_returns_no_signals(tmp_path):
    repo = _make_repo(tmp_path, {})
    result = get_repo_quality_signals(repo)
    assert result.has_tests is False
    assert result.has_readme is False
    assert result.has_contributing is False
    assert result.has_lint_config is False


@pytest.mark.parametrize(
    ("files", "expected_framework", "unexpected_framework"),
    [
        (
            {
                "__tests__/sum.test.js": "test('sum', () => {})",
                "jest.config.js": "module.exports = {};",
            },
            "jest",
            "pytest",
        ),
        (
            {
                "go.mod": "module example.com/app",
                "internal/service/service_test.go": "package service",
            },
            "go test",
            None,
        ),
        (
            {
                "build.gradle": "plugins { id 'java' }",
                "src/test/java/com/example/AppTest.java": "class AppTest {}",
            },
            "junit",
            None,
        ),
        (
            {
                "src/math.spec.ts": "describe('math', () => {})",
                "jest.config.ts": "export default {};",
            },
            "jest",
            None,
        ),
        (
            {
                "Gemfile": "source 'https://rubygems.org'",
                "spec/models/user_spec.rb": "RSpec.describe User do end",
            },
            "rspec",
            None,
        ),
        (
            {
                "Cargo.toml": "[package]\nname = 'demo'",
                "tests/math_test.rs": "#[test]\nfn adds() {}",
            },
            "cargo test",
            None,
        ),
    ],
)
def test_detect_test_signals_detects_frameworks(
    tmp_path,
    files,
    expected_framework,
    unexpected_framework,
):
    repo = _make_repo(tmp_path, files)
    result = detect_test_signals(repo)
    assert result["has_tests"] is True
    assert result["test_file_count"] >= 1
    assert expected_framework in result["test_frameworks"]
    if unexpected_framework:
        assert unexpected_framework not in result["test_frameworks"]


def test_detect_docs_signals_touched_paths_are_case_insensitive(tmp_path):
    repo = _make_repo(tmp_path, {"readme.md": "# Project"})
    result = detect_docs_signals(repo, touched_paths={"README.md"})
    assert result["has_readme"] is True
