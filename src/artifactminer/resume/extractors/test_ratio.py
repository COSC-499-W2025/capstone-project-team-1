"""
Test ratio extractor — compute test-to-source file ratio.

Measures testing discipline by counting test vs source files
touched by the user. Also checks for CI configuration.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from ..models import TestRatio

# Patterns that indicate a test file
_TEST_PATTERNS = [
    re.compile(r"(?:^|/)tests?/", re.I),
    re.compile(r"(?:^|/)test_\w+\.py$", re.I),
    re.compile(r"(?:^|/)\w+_test\.py$", re.I),
    re.compile(r"(?:^|/)\w+\.test\.[jt]sx?$", re.I),
    re.compile(r"(?:^|/)\w+\.spec\.[jt]sx?$", re.I),
    re.compile(r"(?:^|/)__tests__/", re.I),
]

# Source code extensions
_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".kt", ".go", ".rs", ".rb",
    ".cs", ".cpp", ".c", ".php",
}

# CI config indicators
_CI_PATHS = [
    ".github/workflows",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    ".circleci",
    ".travis.yml",
]


def _is_test_file(path: str) -> bool:
    """Check if a file path looks like a test file."""
    return any(p.search(path) for p in _TEST_PATTERNS)


def _is_source_file(path: str) -> bool:
    """Check if a file path is a source code file (not test)."""
    suffix = Path(path).suffix.lower()
    return suffix in _SOURCE_EXTENSIONS and not _is_test_file(path)


def extract_test_ratio(
    repo_path: str,
    module_groups: Dict[str, List[str]],
) -> TestRatio:
    """
    Compute test-to-source file ratio from user-touched files.

    Args:
        repo_path: Path to the git repository root.
        module_groups: Dict mapping module name to list of file paths
                       (from extract_structure).

    Returns:
        TestRatio with counts and ratio.
    """
    all_files: list[str] = []
    for files in module_groups.values():
        all_files.extend(files)

    test_files = sum(1 for f in all_files if _is_test_file(f))
    source_files = sum(1 for f in all_files if _is_source_file(f))
    ratio = test_files / source_files if source_files > 0 else 0.0

    # Check for CI configuration
    root = Path(repo_path)
    has_ci = any(
        (root / ci_path).exists()
        for ci_path in _CI_PATHS
    )

    return TestRatio(
        test_files=test_files,
        source_files=source_files,
        test_ratio=round(ratio, 2),
        has_ci=has_ci,
    )
