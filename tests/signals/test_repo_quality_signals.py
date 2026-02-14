"""Tests for repo_quality_signals extraction."""

import tempfile
from pathlib import Path

from artifactminer.skills.signals.repo_quality_signals import (
    detect_test_signals,
    detect_docs_signals,
    detect_quality_signals,
    get_repo_quality_signals,
)


def _make_repo(files: dict[str, str]) -> str:
    d = tempfile.mkdtemp()
    root = Path(d)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return str(root)


def test_detect_test_signals_finds_test_files():
    repo = _make_repo(
        {
            "tests/test_foo.py": "def test_x(): pass",
            "test_bar.py": "def test_y(): pass",
        }
    )
    result = detect_test_signals(repo)
    assert result["has_tests"] is True
    assert result["test_file_count"] >= 2


def test_detect_test_signals_respects_touched_paths():
    repo = _make_repo(
        {
            "tests/test_foo.py": "def test_x(): pass",
            "other/test_bar.py": "def test_y(): pass",
        }
    )
    touched = {"tests/test_foo.py"}
    result = detect_test_signals(repo, touched_paths=touched)
    assert result["test_file_count"] == 1


def test_detect_docs_signals_finds_readme():
    repo = _make_repo(
        {
            "README.md": "# Project",
            "CHANGELOG.md": "v1.0.0",
        }
    )
    result = detect_docs_signals(repo)
    assert result["has_readme"] is True
    assert result["has_changelog"] is True


def test_detect_docs_signals_handles_lowercase_readme():
    repo = _make_repo({"readme.md": "# Project"})
    result = detect_docs_signals(repo)
    assert result["has_readme"] is True


def test_detect_docs_signals_handles_titlecase_readme():
    repo = _make_repo({"Readme.md": "# Project"})
    result = detect_docs_signals(repo)
    assert result["has_readme"] is True


def test_detect_docs_signals_respects_touched_paths():
    repo = _make_repo(
        {
            "README.md": "# Project",
            "CHANGELOG.md": "v1.0.0",
        }
    )
    touched = {"README.md"}
    result = detect_docs_signals(repo, touched_paths=touched)
    assert result["has_readme"] is True
    assert result["has_changelog"] is False


def test_detect_quality_signals_finds_tools():
    repo = _make_repo(
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


def test_detect_quality_signals_respects_touched_paths():
    repo = _make_repo(
        {
            "pyproject.toml": "[tool.ruff]\n",
            ".pre-commit-config.yaml": "repos:\n",
        }
    )
    touched = {"pyproject.toml"}
    result = detect_quality_signals(repo, touched_paths=touched)
    assert result["has_lint_config"] is True
    assert result["has_precommit"] is False


def test_detect_quality_signals_detects_mypy_from_dot_mypy_ini():
    repo = _make_repo({".mypy.ini": "[mypy]\npython_version = 3.11\n"})
    result = detect_quality_signals(repo)
    assert result["has_type_check"] is True
    assert "mypy" in result["quality_tools"]


def test_get_repo_quality_signals_aggregates_all():
    repo = _make_repo(
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


def test_empty_repo_returns_no_signals():
    repo = _make_repo({})
    result = get_repo_quality_signals(repo)
    assert result.has_tests is False
    assert result.has_readme is False
    assert result.has_lint_config is False


def test_detect_test_signals_finds_javascript_tests_and_jest_config():
    repo = _make_repo(
        {
            "__tests__/sum.test.js": "test('sum', () => {})",
            "jest.config.js": "module.exports = {};",
        }
    )
    result = detect_test_signals(repo)
    assert result["has_tests"] is True
    assert result["test_file_count"] >= 1
    assert "jest" in result["test_frameworks"]
    assert "pytest" not in result["test_frameworks"]


def test_detect_test_signals_finds_go_tests_and_module_file():
    repo = _make_repo(
        {
            "go.mod": "module example.com/app",
            "internal/service/service_test.go": "package service",
        }
    )
    result = detect_test_signals(repo)
    assert result["has_tests"] is True
    assert result["test_file_count"] >= 1
    assert "go test" in result["test_frameworks"]


def test_detect_test_signals_finds_java_test_file_patterns():
    repo = _make_repo(
        {
            "build.gradle": "plugins { id 'java' }",
            "src/test/java/com/example/AppTest.java": "class AppTest {}",
        }
    )
    result = detect_test_signals(repo)
    assert result["has_tests"] is True
    assert result["test_file_count"] >= 1
    assert "junit" in result["test_frameworks"]
