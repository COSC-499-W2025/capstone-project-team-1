#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import git
from artifactminer.db.models import Consent, UserRepoStat, UserAIntelligenceSummary
from artifactminer.db.database import SessionLocal
from src.artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo, Pathish
from email_validator import validate_email
from artifactminer.helpers.openai import get_gpt5_nano_response

@dataclass
class UserRepoStats:
    project_name: str 
    first_commit: Optional[datetime] = None 
    last_commit: Optional[datetime] = None 
    total_commits: Optional[int] = None 
    userStatspercentages:  Optional[int] = None# Percentage of user's contributions compared to total repo activity
    commitFrequency: Optional[float] = None # Average number of commits per week by the user


def getUserRepoStats(repo_path: Pathish, user_email: str) -> UserRepoStats: 
    if not isGitRepo(repo_path): 
        raise ValueError(f"The path {repo_path} is not a git repository.") 
    if not validate_email(user_email):
        raise ValueError(f"The email {user_email} is not valid.")
    repo = git.Repo(repo_path) #initialize the git repo object

    project_name = Path(repo_path).name #Get project name from the folder name

    commits = list(repo.iter_commits(author=user_email)) #Get all commits by the specified user email
    total_repo_commits = list(repo.iter_commits()) #Get all commits in the repo
    if not commits:
        return UserRepoStats(project_name=project_name) #return empty stats if no commits by user

    first_commit = datetime.fromtimestamp(commits[-1].committed_date)
    last_commit = datetime.fromtimestamp(commits[0].committed_date)
    total_commits = len(commits)
    userStatspercentages = (total_commits / len(total_repo_commits)) * 100 if total_repo_commits else 0 #calculate user contribution percentage
    commitFrequency = total_commits / ((last_commit - first_commit).days / 7) if (last_commit - first_commit).days > 0 else total_commits #average commits per week

    return UserRepoStats(
        project_name=project_name,
        first_commit=first_commit,
        last_commit=last_commit,
        total_commits=total_commits
        userStatspercentages=userStatspercentages,
        commitFrequency=commitFrequency,
    )

# Extract added lines from a unified diff
def extract_added_lines(patch_text: str) -> str:
    """
    Keep only added lines from a unified diff, skip headers and binary files.
    """
    added: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("Binary files"):
            continue
        # skip diff headers and file headers
        if line.startswith(("diff --git", "index ", "--- ", "+++ ", "@@")):
            continue
        # keep true additions (avoid '+++' header above)
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return "\n".join(added)

# Collect lines added by a specific user across their commits
def collect_user_additions(
    repo_path: Pathish,
    user_email: str,
    since: Optional[str] = None,   # e.g. "2025-10-01" or "2.weeks" default to None which means from the beginning
    until: str = "HEAD", #default to latest
    max_commits: int = 500, #maximum number of commits to process
    skip_merges: bool = True, #whether to skip merge commits
    max_patch_bytes: int = 200_000,  # cap raw patch text per commit before parsing
) -> List[str]:
    """
    Walk the repo history and return a list where each item is the combined *added lines*
    from a single commit authored by `user_email`. Ordered oldest → newest.
    """
    # validate repo path
    if not isGitRepo(repo_path):
        raise ValueError(f"The path {repo_path} is not a git repository.")
    # validate email format
    if not validate_email(user_email):
        raise ValueError(f"The email {user_email} is not valid.")
    
    repo = git.Repo(repo_path)

    # pull commits authored by this email; filter merges if requested
    commits = list(repo.iter_commits(rev=until, since=since, max_count=max_commits)) #get commits in range from since to until, up to max_commits, ordered newest -> oldest
    if skip_merges: #filter out merge commits, basically any commit with more than 1 parent in order to only get direct commits
        commits = [c for c in commits if len(getattr(c, "parents", [])) <= 1]
    

    
    # filter to the author email (case-insensitive, exact match)
    email_norm = user_email.strip().lower()

    commits = [c for c in commits if (getattr(c.author, "email", "") or "").lower() == email_norm]

    # we’ll return in chronological order (oldest -> newest) for nicer AI summaries
    commits.reverse()

    additions_per_commit: List[str] = []
    for c in commits:
        # unified diff for this commit
        patch = repo.git.show(
            c.hexsha,
            "--patch",
            "--unified=3",
            "--no-color",
            "--no-ext-diff",
        )

        # optional safety cap (before parsing)
        if len(patch) > max_patch_bytes:
            patch = patch[:max_patch_bytes] + "\n... [truncated]"

        added_only = extract_added_lines(patch).strip()
        if added_only:
            additions_per_commit.append(added_only)

    return additions_per_commit


# Check if user has allowed LLM usage via consent
def user_allows_llm() -> bool:
    db = SessionLocal() #create a new database session
    try:
        consent = db.get(Consent, 1)
        if consent is None: #no consent row means no consent given
            consent = db.query(Consent).order_by(Consent.id.desc()).first() #get the latest consent row if multiple exist
        return bool(consent and (consent.consent_level or "").lower() == "full")#return True if consent level is "full"
    finally:
        db.close()

# Create a summary of user additions using LLM
def createAIsummaryFromUserAdditions(additions: List[str]) -> str:
    #Each addition in additions is a string of added lines from a single commit
    if not additions:
        return "No additions found for the specified user."
    if not user_allows_llm():
        return "User has not consented to LLM usage."
    
    #A for loop that goes through every addition and asks the AI to summarize it, then combines all summaries into one final summary, and asks the AI to summarize that final summary.
    for addition in additions:
        prompt = (
        "You are evaluating a student's code contribution from a single commit."
        "Analyze the added lines below and produce a focused, evidence-based critique."

        "For this commit, cover:"
        "- Functional intent: what changed and why it likely matters"
        "- CS concepts observed: OOP (abstraction/encapsulation/inheritance/polymorphism), data structures, algorithms"
        "- Complexity/performance notes: any Big-O implications, memory or latency tradeoffs"
        "- Software engineering practices: modularity, testing, error handling, naming, logging, docs"
        "- Risks/edge cases/security: call out anything suspicious or fragile"

        "Constraints:"
        "- Be concise: 4–6 bullets. No fluff, no speculation beyond the diff."
        "- Don’t restate the code—explain what it implies about skill and decisions."

        "ADDED LINES (unified diff subset, additions only):"
        )
        prompt += f"{addition}\n\n"
        intermediate_summary += get_gpt5_nano_response(prompt)
    final_summary = get_gpt5_nano_response(
        "Summarize the following summaries of code additions made by the user in the repository into a single concise summary:\n\n"
        + intermediate_summary)
    return final_summary


# Create a summary of user additions using LLM if consented and without LLM if not
def createSummaryFromUserAdditions(additions: List[str]) -> str:
    summary: str
    if not additions:
        return "No additions found for the specified user."
    if not user_allows_llm():
        #User has not consented to LLM usage we will create a summary without LLM, placeholder for now
        summary = "User has not consented to LLM usage. Summary generation without LLM is not yet implemented."
    else:
        #User has consented to LLM usage we will create a summary with LLM
        summary = createAIsummaryFromUserAdditions(additions)
    return summary

def saveUserRepoStats(stats: UserRepoStats):
    db = SessionLocal()
    try:
        user_repo_stat = UserRepoStat(
            project_name=stats.project_name,
            first_commit=stats.first_commit,
            last_commit=stats.last_commit,
            total_commits=stats.total_commits,
            userStatspercentages=stats.userStatspercentages,
            commitFrequency=stats.commitFrequency,
        )
        db.add(user_repo_stat)
        db.commit()
        db.refresh(user_repo_stat)
    finally:
        db.close()

def saveUserAIntelligenceSummary(repo_path: str, user_email: str, summary_text: str):
    db = SessionLocal()
    try:
        user_summary = UserAIntelligenceSummary(
            repo_path=repo_path,
            user_email=user_email,
            summary_text=summary_text,
        )
        db.add(user_summary)
        db.commit()
        db.refresh(user_summary)
    finally:
        db.close()