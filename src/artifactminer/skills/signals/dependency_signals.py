"""Dependency manifest signals that map dependencies to skills."""

from __future__ import annotations

from pathlib import Path
from typing import Set

from artifactminer.skills.signals.file_signals import path_in_touched


def dependency_hits(
    repo_path: str, needle: str, *, touched_paths: Set[str] | None = None
) -> int:
    """Count mentions of a dependency across common manifests, optionally scoped to user edits."""
    total_hits = 0
    manifests = [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "package.json",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ]
    for manifest in manifests:
        if touched_paths is not None and not path_in_touched(manifest, touched_paths):
            continue
        target = Path(repo_path) / manifest
        if not target.exists():
            continue
        try:
            content = target.read_text().lower()
            total_hits += content.count(needle.lower())
        except Exception:
            continue
    return total_hits
