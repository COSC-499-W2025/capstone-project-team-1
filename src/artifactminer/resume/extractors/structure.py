"""
Structure extractor — directory overview + user-touched file groupings.

Provides two things:
  1. Top-level directory listing (what does this repo contain?)
  2. User-touched files grouped by module (what areas did this dev work on?)
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from git import Repo


def extract_structure(
    repo_path: str,
    user_email: str,
    *,
    max_commits: int = 500,
) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Extract directory overview and user-touched file groupings.

    Returns:
        (directory_overview, module_groups)
        - directory_overview: sorted list of top-level directory names
        - module_groups: dict mapping top-level dir → list of files touched by user
    """
    root = Path(repo_path)

    # 1. Top-level directory overview
    directory_overview = sorted(
        d.name
        for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    # 2. User-touched files grouped by module
    module_groups: Dict[str, List[str]] = defaultdict(list)

    try:
        repo = Repo(repo_path)
        seen_paths: set[str] = set()

        for commit in repo.iter_commits():
            if len(seen_paths) > 2000:
                break
            if not (commit.author.email and commit.author.email.lower() == user_email.lower()):
                continue

            for path_str in commit.stats.files:
                if path_str in seen_paths:
                    continue
                seen_paths.add(path_str)

                parts = Path(path_str).parts
                if len(parts) >= 2:
                    top_dir = parts[0]
                    # Skip hidden dirs and common noise
                    if not top_dir.startswith("."):
                        module_groups[top_dir].append(path_str)
                else:
                    # Root-level file
                    module_groups["(root)"].append(path_str)
    except Exception:
        pass  # graceful degradation — return empty module_groups

    return directory_overview, dict(module_groups)
