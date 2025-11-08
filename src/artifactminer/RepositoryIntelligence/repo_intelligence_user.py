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

@dataclass
class UserRepoStats:
    project_name: str 
    first_commit: Optional[datetime] = None 
    last_commit: Optional[datetime] = None 
    total_commits: Optional[int] = None 


def getUserRepoStats(repo_path: Pathish, user_email: str) -> UserRepoStats: 
    if not isGitRepo(repo_path): 
        raise ValueError(f"The path {repo_path} is not a git repository.") 

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

