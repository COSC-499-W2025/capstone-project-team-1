"""
Hybrid commit classifier — regex first, LLM fallback.

Strategy:
  1. Conventional-commit prefixes (feat:, fix:, …) are classified instantly.
  2. Keyword heuristics catch common patterns ("add", "implement" → feature).
  3. Remaining unclassified commits are batched to the LLM in groups of 50.
  4. If no LLM is available, unclassified commits default to "feature".

This cuts LLM calls from ~5 per project to 0-1 for most repos.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from git import Repo
from pydantic import BaseModel

from ..models import CommitGroup

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex classification rules
# ---------------------------------------------------------------------------

# Conventional-commit prefix → category
_PREFIX_MAP: Dict[str, str] = {
    "feat": "feature",
    "feature": "feature",
    "fix": "bugfix",
    "bugfix": "bugfix",
    "refactor": "refactor",
    "test": "test",
    "tests": "test",
    "docs": "docs",
    "doc": "docs",
    "chore": "chore",
    "build": "chore",
    "ci": "chore",
    "style": "chore",
    "perf": "refactor",
}

# Conventional-commit regex: type(scope)?: message  or  type: message
_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\([^)]*\))?[!]?:\s", re.IGNORECASE
)

# Keyword heuristics (checked if conventional prefix doesn't match)
_KEYWORD_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:add|implement|create|introduce|new)\b", re.I), "feature"),
    (re.compile(r"\b(?:fix|resolve|patch|hotfix|bug)\b", re.I), "bugfix"),
    (re.compile(r"\b(?:refactor|restructure|reorganize|simplify|clean\s?up)\b", re.I), "refactor"),
    (re.compile(r"\b(?:test|spec|coverage)\b", re.I), "test"),
    (re.compile(r"\b(?:doc|readme|comment|changelog)\b", re.I), "docs"),
    (re.compile(r"\b(?:bump|release|version|merge|update dep|upgrade)\b", re.I), "chore"),
]


def _classify_static(message: str) -> Optional[str]:
    """Attempt to classify a commit message using regex rules only."""
    # Try conventional-commit prefix
    m = _CONVENTIONAL_RE.match(message)
    if m:
        prefix = m.group("type").lower()
        if prefix in _PREFIX_MAP:
            return _PREFIX_MAP[prefix]

    # Try keyword heuristics
    for pattern, category in _KEYWORD_RULES:
        if pattern.search(message):
            return category

    return None


# ---------------------------------------------------------------------------
# LLM fallback types
# ---------------------------------------------------------------------------


class _SingleClassification(BaseModel):
    index: int
    category: str


class _ClassificationBatch(BaseModel):
    classifications: list[_SingleClassification]


_CLASSIFY_SYSTEM = (
    "You are a commit message classifier. "
    "Classify each commit into exactly one category: "
    "feature, bugfix, refactor, test, docs, or chore. "
    "Return valid JSON only."
)


def _classify_with_llm(
    messages: List[str],
    model: str,
    batch_size: int = 50,
) -> List[str]:
    """Classify unresolved messages via LLM in batches."""
    from ..llm_client import query_llm

    results: List[str] = ["feature"] * len(messages)  # safe default

    for start in range(0, len(messages), batch_size):
        batch = messages[start : start + batch_size]
        numbered = "\n".join(f"{i+1}. {msg}" for i, msg in enumerate(batch))
        prompt = (
            "Classify each commit message into one category "
            "(feature, bugfix, refactor, test, docs, or chore):\n\n"
            + numbered
        )

        try:
            resp = query_llm(
                prompt,
                _ClassificationBatch,
                model=model,
                system=_CLASSIFY_SYSTEM,
                temperature=0.1,
            )
            for c in resp.classifications:
                idx = c.index - 1  # 1-based → 0-based
                if 0 <= idx < len(batch):
                    cat = c.category.lower().strip()
                    # Normalise synonyms
                    if cat in ("fix", "bug"):
                        cat = "bugfix"
                    if cat in ("feat",):
                        cat = "feature"
                    if cat in _PREFIX_MAP.values():
                        results[start + idx] = cat
        except Exception as e:
            log.warning("LLM commit classification failed for batch: %s", e)
            # leave defaults

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_and_classify_commits(
    repo_path: str,
    user_email: str,
    *,
    max_commits: int = 200,
    llm_model: Optional[str] = None,
) -> List[CommitGroup]:
    """
    Extract user commits and classify them into semantic groups.

    Returns a list of CommitGroup objects (one per category that has commits).
    """
    repo = Repo(repo_path)

    # Collect raw messages + static classifications
    classified: Dict[str, List[str]] = {}  # category → messages
    unclassified_msgs: List[str] = []
    unclassified_indices: List[int] = []  # index into flat list for LLM mapping

    count = 0
    for commit in repo.iter_commits():
        if count >= max_commits:
            break
        if not (commit.author.email and commit.author.email.lower() == user_email.lower()):
            continue

        subject = commit.message.strip().split("\n")[0][:200]
        if not subject:
            continue

        category = _classify_static(subject)
        if category:
            classified.setdefault(category, []).append(subject)
        else:
            unclassified_msgs.append(subject)
            unclassified_indices.append(count)

        count += 1

    # LLM fallback for unclassified
    if unclassified_msgs and llm_model:
        log.info(
            "Classifying %d unresolved commits via LLM (%s)",
            len(unclassified_msgs),
            llm_model,
        )
        llm_cats = _classify_with_llm(unclassified_msgs, llm_model)
        for msg, cat in zip(unclassified_msgs, llm_cats):
            classified.setdefault(cat, []).append(msg)
    elif unclassified_msgs:
        # No LLM — default unclassified to "feature"
        classified.setdefault("feature", []).extend(unclassified_msgs)

    # Build CommitGroup list (stable ordering)
    order = ["feature", "bugfix", "refactor", "test", "docs", "chore"]
    groups: List[CommitGroup] = []
    for cat in order:
        msgs = classified.get(cat, [])
        if msgs:
            groups.append(CommitGroup(category=cat, messages=msgs))

    return groups
