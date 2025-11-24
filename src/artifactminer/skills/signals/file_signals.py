"""Filesystem-based signals (path matching utilities)."""

from __future__ import annotations

from pathlib import Path
from typing import Set


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
