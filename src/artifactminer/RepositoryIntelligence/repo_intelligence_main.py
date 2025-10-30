#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu
import subprocess, os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Optional, Union, List
from pathlib import Path
import git
from artifactminer.db.models import RepoStat
from artifactminer.db.database import SessionLocal

@dataclass
class RepoStats: #This is the basic Repo class for storing the results of the git files.
    project_name: str #store project name as a string
    is_collaborative: bool #Is collaborative as a boolean to see whether the user is the only one to edit this file or had help.
    Languages: List[str] = field(default_factory=list) #Languages as a string list to store the languages used in the repo
    language_percentages: List[float] = field(default_factory=list)# Language percentages as a float list to store the percentage of each language used in the repo
    primary_language: Optional[str] = None # Optional addition is the primary language used in the repo
    first_commit: Optional[datetime] = None # Optional addition is the users first commit date/time
    last_commit: Optional[datetime] = None # Optional addition is the users last commit date/time
    total_commits: Optional[int] = None # Optional addition is the total number of commits in the repo

def isGitRepo(path :os.PathLike | str) -> bool:#This function checks whether the git directory exists inside of the given path
    p = Path(path)
    return (p / ".git").is_dir()

Pathish = Union[os.PathLike, str]#pathlike will accept anything that looks like a path as a string

def runGit(repo_path: Pathish, args: Iterable[str]) -> str: #This function will take the git repo path and run the given git command in the repo. It will fail if the Repo is not a git repo or git is not working properly
#Example : runGit("/path/to/my/repo/", ["rev-parse", "--is-inside-work-tree"]) would return true if that was a real repo
    result = subprocess.run(# run teh git command
        ["git", *args], #git plus the cmd, we use "rev-parse --is-inside-work-tree" in our example
        cwd=Path(repo_path),#run it in the selected git repo, we use "/path/to/my/repo/" in the example
        check=True, #If a non-zero exit happens a called process error is thrown
        stdout=subprocess.PIPE, #captures output
        stderr=subprocess.PIPE, #captures errors
        text=True, #set text to string and not bytes
    )
    return result.stdout #return gits printed output

def getRepoStats(repo_path: Pathish) -> RepoStats: #This function will get the basic repo stats for a given git repo path
    if not isGitRepo(repo_path): #check if its a git repo
        raise ValueError(f"The path {repo_path} is not a git repository.") #raise error if not

    repo = git.Repo(repo_path) #initialize the git repo object

    # Get project name from the folder name
    project_name = Path(repo_path).name

    # Get primary language by analyzing file extensions
    language_counter = Counter()
    for blob in repo.head.commit.tree.traverse(): #traverse all files in the repo
        if blob.type == 'blob': #if its a file
            ext = Path(blob.path).suffix.lower() #get the file extension
            if ext: #if it has an extension
                language_counter[ext] += 1 #count it
    primary_language = language_counter.most_common(1)[0][0] if language_counter else "Unknown"
    languages = [lang for lang, _ in language_counter.most_common()] #list of languages used in the repo
    language_percentages = [count / sum(language_counter.values()) * 100 for _, count in language_counter.most_common()] #percentage of each language used
    # Check if the repository is collaborative
    is_collaborative = len(repo.remotes) > 0

    # Get first and last commit dates
    commits = list(repo.iter_commits())
    first_commit = datetime.fromtimestamp(commits[-1].committed_date) if commits else None #Formatted as year-month-day hour:minute:second
    last_commit = datetime.fromtimestamp(commits[0].committed_date) if commits else None #Formatted as year-month-day hour:minute:second

    return RepoStats(
        project_name=project_name,
        is_collaborative=is_collaborative,
        primary_language=primary_language,
        Languages=languages,
        language_percentages=language_percentages,
        first_commit=first_commit,
        last_commit=last_commit,
        total_commits=len(commits),
    )

def save_repo_stats(stats):
    db = SessionLocal()
    try:
        repo_stat = RepoStat(
            project_name=stats.project_name,
            is_collaborative=stats.is_collaborative,
            primary_language=stats.primary_language,
            languages=stats.Languages,
            language_percentages=stats.language_percentages,
            first_commit=stats.first_commit,
            last_commit=stats.last_commit,
            total_commits=stats.total_commits,
        )
        db.add(repo_stat)
        db.commit()
        db.refresh(repo_stat)
        print(f"Saved repo stats: {repo_stat.project_name}")
    except Exception as e:
        db.rollback()
        print(f"Error saving repo stats: {e}")
    finally:
        db.close()
