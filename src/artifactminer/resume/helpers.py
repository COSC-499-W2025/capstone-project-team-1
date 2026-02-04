from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import git
from email_validator import EmailNotValidError, validate_email

from artifactminer.RepositoryIntelligence.repo_intelligence_main import Pathish, isGitRepo


SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "coverage",
}

SKIP_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
}

SKIP_EXTS = {
    ".lock",
    ".min.js",
    ".min.css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".ico",
}


def should_skip_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    parts = {p.lower() for p in Path(normalized).parts}
    if parts & SKIP_DIRS:
        return True

    lower = normalized.lower()
    if Path(lower).name in SKIP_FILES:
        return True
    if any(lower.endswith(ext) for ext in SKIP_EXTS):
        return True
    return False


def collect_user_additions_by_file(
    repo_path: Pathish,
    user_email: str,
    since: Optional[str] = None,
    until: str = "HEAD",
    max_commits: int = 500,
    skip_merges: bool = True,
    max_patch_bytes: int = 200_000,
) -> Dict[str, str]:
    """
    Walk history and return {file_path: added_lines_string} for commits by user_email.
    """
    if not isGitRepo(repo_path):
        raise ValueError(f"The path {repo_path} is not a git repository.")

    try:
        validated = validate_email(user_email, check_deliverability=False)
        email_norm = validated.normalized
    except EmailNotValidError as exc:
        raise ValueError(f"The email {user_email} is not valid.") from exc

    repo = git.Repo(repo_path)

    commits = list(repo.iter_commits(rev=until, since=since, max_count=max_commits))
    if skip_merges:
        commits = [c for c in commits if len(getattr(c, "parents", [])) <= 1]
    commits = [c for c in commits if (getattr(c.author, "email", "") or "").lower() == email_norm]
    commits.reverse()

    additions_by_file: Dict[str, List[str]] = {}

    for commit in commits:
        patch = repo.git.show(
            commit.hexsha,
            "--patch",
            "--unified=3",
            "--no-color",
            "--no-ext-diff",
        )

        if len(patch) > max_patch_bytes:
            patch = patch[:max_patch_bytes] + "\n... [truncated]"

        _merge_diff_additions(additions_by_file, patch)

    return {
        path: "\n".join(lines).strip()
        for path, lines in additions_by_file.items()
        if lines
    }


def _merge_diff_additions(additions_by_file: Dict[str, List[str]], patch: str) -> None:
    current_path: Optional[str] = None

    for line in patch.splitlines():
        if line.startswith("diff --git"):
            current_path = None
            continue
        if line.startswith("Binary files"):
            current_path = None
            continue
        if line.startswith("+++ "):
            raw_path = line[4:].strip()
            if raw_path == "/dev/null":
                current_path = None
                continue
            if raw_path.startswith("b/"):
                raw_path = raw_path[2:]
            current_path = raw_path
            continue
        if line.startswith(("index ", "--- ", "@@")):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if current_path:
                additions_by_file.setdefault(current_path, []).append(line[1:])
