"""User-scoped repository profile helpers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

import git

from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo


def extract_added_lines(patch_text: str) -> str:
    """Keep only added lines from a unified diff, skipping headers and binary markers."""
    added: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("Binary files"):
            continue
        if line.startswith(("diff --git", "index ", "--- ", "+++ ", "@@")):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return "\n".join(added)


def build_user_profile(
    repo_path: str,
    user_email: str,
    *,
    max_commits: int = 400,
    max_patch_bytes: int = 200_000,
) -> Dict[str, Any] | None:
    """Summarize a user's edits for collaborative repos (touched paths, file counts, added lines)."""
    if not isGitRepo(repo_path):
        return None

    try:
        repo = git.Repo(repo_path)
    except Exception:
        return None

    commits = list(repo.iter_commits(author=user_email, max_count=max_commits))
    if not commits:
        return None

    file_counts: Counter = Counter()
    touched_paths: Set[str] = set()
    additions_by_commit: List[str] = []

    for commit in commits:
        try:
            file_stats = getattr(commit, "stats", None)
            files = file_stats.files if file_stats else {}
        except Exception:
            files = {}

        for path in files.keys():
            path_str = str(path)
            touched_paths.add(path_str)
            suffix = Path(path_str).suffix.lower()
            if suffix:
                file_counts[suffix] += 1

        try:
            patch = repo.git.show(
                commit.hexsha,
                "--patch",
                "--unified=3",
                "--no-color",
                "--no-ext-diff",
            )
            if len(patch) > max_patch_bytes:
                patch = patch[:max_patch_bytes] + "\n... [truncated]"
            added_only = extract_added_lines(patch).strip()
            if added_only:
                additions_by_commit.append(added_only)
        except Exception:
            continue

    manifests = {
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "package.json",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    }
    manifest_edits = {Path(p).name for p in touched_paths if Path(p).name in manifests}

    return {
        "file_counts": file_counts,
        "touched_paths": touched_paths,
        "additions_text": "\n".join(additions_by_commit),
        "manifest_edits": manifest_edits,
    }
