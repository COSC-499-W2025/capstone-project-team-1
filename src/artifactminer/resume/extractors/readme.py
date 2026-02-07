"""
README extractor — reads and trims README content for LLM context.

The README is the single best source for answering "what does this project do?"
We extract it early so the LLM can reference it when writing project descriptions.
"""

from __future__ import annotations

from pathlib import Path


# Common README filenames in priority order
_README_NAMES = [
    "README.md",
    "readme.md",
    "README.rst",
    "README.txt",
    "README",
    "Readme.md",
]

_MAX_CHARS = 2000


def extract_readme(repo_path: str, *, max_chars: int = _MAX_CHARS) -> str:
    """
    Extract README content from a repository.

    Returns the first ``max_chars`` characters of the README, or an empty
    string if no README is found.
    """
    root = Path(repo_path)

    for name in _README_NAMES:
        candidate = root / name
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
                return text[:max_chars].strip()
            except OSError:
                continue

    return ""
