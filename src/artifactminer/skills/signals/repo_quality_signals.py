"""Repository quality signals: testing, documentation, code quality."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

from artifactminer.skills.signals.file_signals import path_in_touched


TEST_FILE_PATTERNS = ["test_*.py", "*_test.py", "tests.py"]
TEST_DIR_PATTERNS = ["tests", "test"]
TEST_CONFIG_FILES = ["pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"]

DOCS_PATTERNS = {
    "README.md": "readme",
    "README.rst": "readme",
    "README.txt": "readme",
    "CHANGELOG.md": "changelog",
    "CHANGELOG.rst": "changelog",
    "CHANGES.md": "changelog",
    "CONTRIBUTING.md": "contributing",
    "docs": "docs_dir",
}

QUALITY_PATTERNS = {
    ".pre-commit-config.yaml": "pre_commit",
    "pyproject.toml": "pyproject",
    "mypy.ini": "mypy",
    ".mypy.ini": "mypy",
    "setup.cfg": "setup_cfg",
    ".editorconfig": "editorconfig",
    "ruff.toml": "ruff",
}


def _has_test_config(root: Path, touched_paths: Set[str] | None) -> list[str]:
    found = []
    for cfg in TEST_CONFIG_FILES:
        if touched_paths and not path_in_touched(cfg, touched_paths):
            continue
        p = root / cfg
        if p.is_file():
            content = p.read_text(errors="ignore").lower()
            if (
                cfg == "pytest.ini"
                or "[pytest]" in content
                or "[tool:pytest]" in content
            ):
                found.append("pytest")
            if "tox" in content:
                found.append("tox")
    return found


def detect_test_signals(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> Dict[str, Any]:
    """Detect test infrastructure in repository."""
    root = Path(repo_path)
    seen_files: Set[str] = set()
    test_dirs = 0
    frameworks = set()

    for pattern in TEST_FILE_PATTERNS:
        for match in root.rglob(pattern):
            rel = str(match.relative_to(root))
            if touched_paths and not path_in_touched(rel, touched_paths):
                continue
            seen_files.add(rel)

    for dir_name in TEST_DIR_PATTERNS:
        candidate = root / dir_name
        if candidate.is_dir():
            test_dirs += 1
            for py in candidate.rglob("*.py"):
                rel = str(py.relative_to(root))
                if touched_paths and not path_in_touched(rel, touched_paths):
                    continue
                seen_files.add(rel)

    frameworks.update(_has_test_config(root, touched_paths))
    if seen_files:
        frameworks.add("pytest")

    return {
        "test_file_count": len(seen_files),
        "test_dir_count": test_dirs,
        "has_tests": len(seen_files) > 0,
        "test_frameworks": sorted(frameworks),
    }


def detect_docs_signals(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> Dict[str, Any]:
    """Detect documentation in repository."""
    root = Path(repo_path)
    found = {}

    for pattern, doc_type in DOCS_PATTERNS.items():
        if touched_paths and not path_in_touched(pattern, touched_paths):
            continue
        candidate = root / pattern
        if candidate.is_file() or candidate.is_dir():
            found[doc_type] = True

    return {
        "has_readme": found.get("readme", False),
        "has_changelog": found.get("changelog", False),
        "has_contributing": found.get("contributing", False),
        "has_docs_dir": found.get("docs_dir", False),
    }


def detect_quality_signals(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
) -> Dict[str, Any]:
    """Detect code quality tooling in repository."""
    root = Path(repo_path)
    tools = set()
    has_lint_config = False
    has_precommit = False
    has_type_check = False

    for pattern, tool_type in QUALITY_PATTERNS.items():
        if touched_paths and not path_in_touched(pattern, touched_paths):
            continue
        candidate = root / pattern
        if not candidate.is_file():
            continue

        if tool_type == "pre_commit":
            has_precommit = True
            tools.add("pre-commit")
        elif tool_type in ("pyproject", "setup_cfg", "ruff"):
            content = candidate.read_text(errors="ignore").lower()
            if "[tool.ruff" in content or tool_type == "ruff":
                has_lint_config = True
                tools.add("ruff")
            if "[tool.black" in content:
                has_lint_config = True
                tools.add("black")
            if "[tool.mypy" in content:
                has_type_check = True
                tools.add("mypy")
            if "[flake8]" in content or "flake8" in content:
                has_lint_config = True
                tools.add("flake8")
        elif tool_type in ("mypy", ".mypy.ini"):
            has_type_check = True
            tools.add("mypy")
        elif tool_type == "editorconfig":
            tools.add("editorconfig")

    return {
        "has_lint_config": has_lint_config,
        "has_precommit": has_precommit,
        "has_type_check": has_type_check,
        "quality_tools": sorted(tools),
    }


def get_repo_quality_signals(
    repo_path: str,
    *,
    touched_paths: Set[str] | None = None,
):
    """Aggregate all repository quality signals into a dataclass."""
    from artifactminer.skills.deep_analysis import RepoQualityResult

    tests = detect_test_signals(repo_path, touched_paths=touched_paths)
    docs = detect_docs_signals(repo_path, touched_paths=touched_paths)
    quality = detect_quality_signals(repo_path, touched_paths=touched_paths)

    return RepoQualityResult(
        test_file_count=tests.get("test_file_count", 0),
        has_tests=tests.get("has_tests", False),
        test_frameworks=tests.get("test_frameworks", []),
        has_readme=docs.get("has_readme", False),
        has_changelog=docs.get("has_changelog", False),
        has_docs_dir=docs.get("has_docs_dir", False),
        has_lint_config=quality.get("has_lint_config", False),
        has_precommit=quality.get("has_precommit", False),
        has_type_check=quality.get("has_type_check", False),
        quality_tools=quality.get("quality_tools", []),
    )
