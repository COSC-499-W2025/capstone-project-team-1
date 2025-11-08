#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu
import subprocess, os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional, Union, List
from pathlib import Path
import git
from artifactminer.db.models import RepoStat
from artifactminer.db.database import SessionLocal
from src.artifactminer.RepositoryIntelligence.repo_intelligence_main import isGitRepo, Pathish
from email_validator import validate_email
@dataclass
class UserRepoStats:
    project_name: str 
    first_commit: Optional[datetime] = None 
    last_commit: Optional[datetime] = None 
    total_commits: Optional[int] = None 


def getUserRepoStats(repo_path: Pathish, user_email: str) -> UserRepoStats: 
    if not isGitRepo(repo_path): 
        raise ValueError(f"The path {repo_path} is not a git repository.") 
    if not validate_email(user_email):
        raise ValueError(f"The email {user_email} is not valid.")
    repo = git.Repo(repo_path) #initialize the git repo object

    project_name = Path(repo_path).name #Get project name from the folder name

    commits = list(repo.iter_commits(author=user_email)) #Get all commits by the specified user email

    if not commits:
        return UserRepoStats(project_name=project_name) #return empty stats if no commits by user

    first_commit = datetime.fromtimestamp(commits[-1].committed_date)
    last_commit = datetime.fromtimestamp(commits[0].committed_date)
    total_commits = len(commits)

    return UserRepoStats(
        project_name=project_name,
        first_commit=first_commit,
        last_commit=last_commit,
        total_commits=total_commits
    )

def saveUserRepoStatsToDB(stats: UserRepoStats): #placeholder function to save user repo stats to the database
    db = SessionLocal()
    try:
        repo_stat = RepoStat(
            project_name=stats.project_name,
            first_commit=stats.first_commit,
            last_commit=stats.last_commit,
            total_commits=stats.total_commits
        )
        db.add(repo_stat)
        db.commit()
    finally:
        db.close()