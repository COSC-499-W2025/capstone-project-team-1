#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import git
from sqlalchemy import inspect
from artifactminer.db.database import SessionLocal
from artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo, Pathish
from artifactminer.RepositoryIntelligence.activity_classifier import classify_commit_activities 
from artifactminer.RepositoryIntelligence.repo_intelligence_AI import user_allows_llm, createSummaryFromUserAdditions, saveUserIntelligenceSummary, group_additions_into_blocks
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session
from artifactminer.db.models import RepoStat, UserRepoStat, UserAnswer

@dataclass
class UserRepoStats:
    project_name: str 
    project_path: str
    first_commit: Optional[datetime] = None 
    last_commit: Optional[datetime] = None 
    total_commits: Optional[int] = None 
    userStatspercentages:  Optional[float] = None# Percentage of user's contributions compared to total repo activity
    commitFrequency: Optional[float] = None # Average number of commits per week by the user
    commitActivities: Optional[dict] = None # New field to store activity breakdown


def getUserRepoStats(repo_path: Pathish, user_email: str) -> UserRepoStats: 
    if not isGitRepo(repo_path): 
        raise ValueError(f"The path {repo_path} is not a git repository.") 
    try:
        user_email = validate_email(user_email, check_deliverability=False).email
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email address: {user_email}") from e
   

    repo = git.Repo(repo_path) #initialize the git repo object

    project_name = Path(repo_path).name #Get project name from the folder name
    project_path = str(repo_path) # Get the full project path
    commits = list(repo.iter_commits(author=user_email)) #Get all commits by the specified user email
    total_repo_commits = list(repo.iter_commits()) #Get all commits in the repo
    if not commits:
        return UserRepoStats(project_name=project_name, project_path=project_path) #return empty stats if no commits by user
    first_commit = datetime.fromtimestamp(commits[-1].committed_date)
    last_commit = datetime.fromtimestamp(commits[0].committed_date)
    total_commits = len(commits) #total number of commits by the user not the repo
    userStatspercentages = (total_commits / len(total_repo_commits)) * 100 if total_repo_commits else 0 #calculate user contribution percentage
    
    delta = last_commit - first_commit
    weeks = delta.total_seconds() / 604800  # seconds in a week, weeks between first and last commit, to calculate commit frequency more accurately then just dividing by total weeks in delta
    if weeks <= 0: #avoid division by zero
        commitFrequency = float(total_commits) #all commits happened within the same week
    else:
        commitFrequency = total_commits / weeks #average commits per week


    commitActivities = classify_commit_activities(collect_user_additions(repo_path, user_email, max_commits=5000)) #get the user's commit activities breakdown

    return UserRepoStats( #return the populated UserRepoStats dataclass
        project_name=project_name,
        project_path=str(repo_path),
        first_commit=first_commit,
        last_commit=last_commit,
        total_commits=total_commits,
        userStatspercentages=userStatspercentages,
        commitFrequency=commitFrequency,
        commitActivities=commitActivities
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

def split_text_into_chunks(text: str, max_chunk_size: int) -> List[str]:
    """Split text into chunks of at most `max_chunk_size` characters."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


def saveUserRepoStats(stats: UserRepoStats, db=None):
    """Save user repository statistics to database.
    
    Args:
        stats: UserRepoStats object to save
        db: Optional SQLAlchemy session. If None, creates a new session.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    
    try:
        user_repo_stat = UserRepoStat(
            project_name=stats.project_name,
            project_path=stats.project_path,
            first_commit=stats.first_commit,
            last_commit=stats.last_commit,
            total_commits=stats.total_commits,
            userStatspercentages=stats.userStatspercentages,
            commitFrequency=stats.commitFrequency,
            activity_breakdown=stats.commitActivities
        )
        db.add(user_repo_stat)
        if own_session:
            db.commit()
            db.refresh(user_repo_stat)
        return user_repo_stat
    except Exception as e:
        if own_session:
            db.rollback()
        raise
    finally:
        if own_session:
            db.close()

def generate_summaries_for_ranked(db: Session, top=3) -> list[dict]:
    """
    Summarize the top-ranked repositories for the current user.

    Expected flow (called by Nathan's orchestrator):
    - Shlok's ranking code has already set RepoStat.ranking_score.
    - We pick the top 3, check consent, and either:
      * use LLM summaries from diffs, or
      * fall back to a simple template.
    - We persist results into UserAIntelligenceSummary.
    """
    # Pick a ranking column: prefer ranking_score, fall back to total_commits

   
    top_repos: list[RepoStat] = (
        db.query(RepoStat)
        .limit(top)
        .all()
    )

    if not top_repos:
        return []

    # Get the user's email from config answers (question_id = 1)
    email_answer = (
        db.query(UserAnswer)
        .filter(UserAnswer.question_id == 1)
        .order_by(UserAnswer.answered_at.desc())
        .first()
    )

    user_email = email_answer.answer_text.strip() if email_answer else None

    results: list[dict] = []

    for repo in top_repos:
        # Default summary uses template
        user_stats = (
            db.query(UserRepoStat)
            .filter(UserRepoStat.project_name == repo.project_name)
            .order_by(UserRepoStat.id.desc())
            .first()
        )
        pct = user_stats.userStatspercentages if user_stats and user_stats.userStatspercentages is not None else 0

        languages = repo.languages or []
        if isinstance(languages, list):
            languages_text = ", ".join(languages) if languages else "unknown languages"
        else:
            languages_text = str(languages)

        summary_text = (
            f"User contributed {pct:.1f}% to {repo.project_name} "
            f"using {languages_text}."
        )

        # If we have consent + a valid email, try the LLM-based summary instead
        if user_allows_llm() and user_email:
            try:
                # Ensure path is absolute for git operations
                repo_path_absolute = str(Path(repo.project_path).resolve())
                additions = collect_user_additions(
                    repo_path=repo_path_absolute,
                    user_email=user_email,
                )
                if additions:
                    grouped = group_additions_into_blocks(additions, max_chars_per_block=1000, max_blocks=1)
                    ai_summary = createSummaryFromUserAdditions(grouped)
                    print("\n AI Summary Generated for", repo.project_name, ":", ai_summary)
                    summary_text += " AI summary: " + ai_summary
            except Exception as e:
                # Log the actual error for debugging
                print(f"ERROR generating AI summary for {repo.project_name}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                # Fail soft: keep the fallback template summary
                pass

        # Persist into UserAIntelligenceSummary
        saveUserIntelligenceSummary(
            repo_path=repo.project_path,
            user_email=user_email or "",
            summary_text=summary_text,
        )

        results.append(
            {
                "project_name": repo.project_name,
                "summary": summary_text,
            }
        )

    return results
