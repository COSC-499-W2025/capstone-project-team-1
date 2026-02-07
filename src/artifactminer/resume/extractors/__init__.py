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

__all__ = [
    "extract_readme",
    "extract_and_classify_commits",
    "extract_structure",
    "extract_constructs",
    "infer_project_type",
]
