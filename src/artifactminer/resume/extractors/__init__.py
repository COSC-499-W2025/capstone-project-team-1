"""
Static data extractors for the v3 resume pipeline.

Each extractor takes a repo path (+ optional user email) and returns
structured data. No LLM calls — pure static analysis.
"""

from __future__ import annotations

from .readme import extract_readme
from .commits import extract_and_classify_commits
from .structure import extract_structure
from .constructs import extract_constructs
from .project_type import infer_project_type
from .git_stats import extract_git_stats
from .test_ratio import extract_test_ratio
from .commit_quality import extract_commit_quality
from .cross_module import extract_cross_module_breadth

__all__ = [
    "extract_readme",
    "extract_and_classify_commits",
    "extract_structure",
    "extract_constructs",
    "infer_project_type",
    "extract_git_stats",
    "extract_test_ratio",
    "extract_commit_quality",
    "extract_cross_module_breadth",
]
