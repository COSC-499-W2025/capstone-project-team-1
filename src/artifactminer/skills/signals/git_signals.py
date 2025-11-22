"""Git-derived signals (merge commits, branches) with optional user filters."""

from __future__ import annotations

from typing import Dict

import git

from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo


def git_signals(repo_path: str, user_contributions: Dict) -> Dict[str, int]:
    """Infer git-related signals, prioritizing user-scoped merge commits when possible."""
    # Let caller override counts (e.g., from GitHub API)
    provided_merge_commits = user_contributions.get("user_merge_commits")
    if provided_merge_commits is None:
        provided_merge_commits = user_contributions.get("merge_commits")

    signals = {
        "merge_commits": int(provided_merge_commits or 0),
        "branches": 0,
    }
    if signals["merge_commits"] and user_contributions.get("branches"):
        signals["branches"] = len(user_contributions["branches"])

    # Normalize optional filters for user-specific merge attribution
    raw_emails = user_contributions.get("user_email") or user_contributions.get("user_emails")
    if isinstance(raw_emails, str):
        user_emails = {raw_emails.strip().lower()}
    elif isinstance(raw_emails, (list, tuple, set)):
        user_emails = {e.strip().lower() for e in raw_emails if isinstance(e, str)}
    else:
        user_emails = set()

    raw_prs = (
        user_contributions.get("user_prs")
        or user_contributions.get("pr_numbers")
        or user_contributions.get("pull_requests")
        or user_contributions.get("prs")
    )
    if isinstance(raw_prs, (list, tuple, set)):
        pr_numbers = {str(p).lstrip("#") for p in raw_prs}
    elif raw_prs is None:
        pr_numbers = set()
    else:
        pr_numbers = {str(raw_prs).lstrip("#")}

    if not isGitRepo(repo_path):
        return signals

    try:
        repo = git.Repo(repo_path)
    except Exception:
        return signals

    if not signals["merge_commits"]:
        try:
            merge_count = 0
            for c in repo.iter_commits():
                if len(c.parents) <= 1:
                    continue

                # If no user filters are provided, count all merges (previous behavior)
                if not user_emails and not pr_numbers:
                    merge_count += 1
                    continue

                author_email = (getattr(c.author, "email", "") or "").lower()
                authored_by_user = author_email in user_emails if user_emails else False

                involves_user_pr = False
                if pr_numbers:
                    msg = c.message.lower()
                    involves_user_pr = any(
                        f"#{pr}" in msg or f"pull request {pr}" in msg for pr in pr_numbers
                    )

                if authored_by_user or involves_user_pr:
                    merge_count += 1

            signals["merge_commits"] = merge_count
        except Exception:
            pass

    if not signals["branches"]:
        try:
            branches = repo.git.branch("--list").splitlines()
            signals["branches"] = len([b for b in branches if b.strip()])
        except Exception:
            pass

    return signals
