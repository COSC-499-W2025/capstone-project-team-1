"""
Commit Message Semantic Classification.

Extracts commit messages from git history and uses a single batched LLM call
to classify each commit as: feature | bugfix | refactor | test | docs | chore.

This enables resume bullets like:
"Implemented 15 features and resolved 8 critical bugs across the auth subsystem"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from git import Repo
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CommitInfo:
    """Lightweight commit metadata."""
    hash: str
    message: str
    date: str  # ISO format
    files_changed: int


class SingleClassification(BaseModel):
    hash: str
    category: Literal["feature", "bugfix", "refactor", "test", "docs", "chore"]


class CommitClassificationBatch(BaseModel):
    classifications: list[SingleClassification]


# ---------------------------------------------------------------------------
# Static analysis: extract commit messages
# ---------------------------------------------------------------------------

def extract_commit_messages(
    repo_path: str,
    user_email: str,
    max_commits: int = 200,
) -> List[CommitInfo]:
    """
    Extract commit messages for a user from a git repo.

    Args:
        repo_path: Path to the git repository
        user_email: Author email to filter by
        max_commits: Maximum number of commits to extract

    Returns:
        List of CommitInfo objects, newest first
    """
    repo = Repo(repo_path)
    commits = []
    count = 0

    for commit in repo.iter_commits():
        if count >= max_commits:
            break
        if commit.author.email and commit.author.email.lower() == user_email.lower():
            # Get first line of commit message (subject)
            subject = commit.message.strip().split("\n")[0][:200]
            if subject:
                commits.append(CommitInfo(
                    hash=commit.hexsha[:7],
                    message=subject,
                    date=commit.committed_datetime.isoformat(),
                    files_changed=commit.stats.total.get("files", 0),
                ))
                count += 1

    return commits


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM = (
    "You are a commit message classifier. "
    "Classify each commit into exactly one category: "
    "feature, bugfix, refactor, test, docs, or chore. "
    "Return valid JSON only."
)


def classify_commits(
    commits: List[CommitInfo],
    model: str,
    batch_size: int = 50,
) -> Dict[str, int]:
    """
    Classify commit messages using a single batched LLM call.

    Args:
        commits: List of commit info objects
        model: LLM model name
        batch_size: Max commits per LLM call (to fit context window)

    Returns:
        Breakdown dict, e.g., {"feature": 15, "bugfix": 8, ...}
    """
    from ..llm_client import query_llm

    if not commits:
        return {}

    breakdown: Dict[str, int] = {}

    # Process in batches to fit context window
    for i in range(0, len(commits), batch_size):
        batch = commits[i : i + batch_size]

        # Build prompt
        lines = [f"{c.hash}: {c.message}" for c in batch]
        prompt = (
            f"Classify each commit message into one category "
            f"(feature, bugfix, refactor, test, docs, or chore):\n\n"
            + "\n".join(f"{j+1}. {line}" for j, line in enumerate(lines))
        )

        result = query_llm(
            prompt,
            CommitClassificationBatch,
            model=model,
            system=CLASSIFY_SYSTEM,
            temperature=0.1,
        )

        for c in result.classifications:
            cat = c.category
            breakdown[cat] = breakdown.get(cat, 0) + 1

    return breakdown


def format_breakdown_for_resume(breakdown: Dict[str, int]) -> Optional[str]:
    """
    Format commit breakdown into a resume-friendly summary.

    Returns None if the breakdown is empty or trivial.
    """
    if not breakdown:
        return None

    total = sum(breakdown.values())
    if total < 3:
        return None

    parts = []
    for cat, label in [
        ("feature", "features"),
        ("bugfix", "bug fixes"),
        ("refactor", "refactoring efforts"),
        ("test", "test improvements"),
        ("docs", "documentation updates"),
    ]:
        count = breakdown.get(cat, 0)
        if count > 0:
            parts.append(f"{count} {label}")

    if not parts:
        return None

    return f"Contributed {total} commits including " + ", ".join(parts)
