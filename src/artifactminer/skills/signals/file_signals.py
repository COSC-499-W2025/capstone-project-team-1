"""Filesystem-based signals (presence of key files/directories)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set


def path_in_touched(rel: str, touched_paths: Set[str]) -> bool:
    """Return True if a relative path or its descendants were touched by the user."""
    normalized = rel.rstrip("/")
    for touched in touched_paths:
        touched_norm = touched.rstrip("/")
        if touched_norm == normalized:
            return True
        if touched_norm.startswith(f"{normalized}/"):
            return True
        # Allow matching by basename for common manifests (e.g., requirements.txt in nested paths)
        try:
            if Path(touched_norm).name == normalized:
                return True
        except Exception:
            continue
    return False


def paths_present(
    repo_path: str, paths: Iterable[str], *, touched_paths: Set[str] | None = None
) -> List[str]:
    """Return which of the candidate paths exist, optionally filtered to user-touched paths."""
    root = Path(repo_path)
    matched: List[str] = []
    for rel in paths:
        if touched_paths is not None and not path_in_touched(rel, touched_paths):
            continue
        candidate = root / rel
        if candidate.exists():
            matched.append(rel)
    return matched
