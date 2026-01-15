#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu
import subprocess
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional, Union, List
from pathlib import Path
import git
from artifactminer.db.models import RepoStat
from artifactminer.db.database import SessionLocal
from artifactminer.RepositoryIntelligence.framework_detector import detect_frameworks

@dataclass
class RepoStats: #This is the basic Repo class for storing the results of the git files.
    project_name: str #store project name as a string
    project_path: str #store project path as a string
    is_collaborative: bool #Is collaborative as a boolean to see whether the user is the only one to edit this file or had help.
    Languages: List[str] = field(default_factory=list) #Languages as a string list to store the languages used in the repo
    language_percentages: List[float] = field(default_factory=list)# Language percentages as a float list to store the percentage of each language used in the repo
    primary_language: Optional[str] = None # Optional addition is the primary language used in the repo
    first_commit: Optional[datetime] = None # Optional addition is the users first commit date/time
    last_commit: Optional[datetime] = None # Optional addition is the users last commit date/time
    total_commits: Optional[int] = None # Optional addition is the total number of commits in the repo
    frameworks: List[str] = field(default_factory=list) # List of detected frameworks in the repo
    health_score: Optional[float] = None # Repository health score (0-100) based on documentation, recency, and best practices

def isGitRepo(path :os.PathLike | str) -> bool:#This function checks whether the git directory exists inside of the given path
    p = Path(path)
    return (p / ".git").is_dir()

Pathish = Union[os.PathLike, str]#pathlike will accept anything that looks like a path as a string

def runGit(repo_path: Pathish, args: Iterable[str]) -> str: #This function will take the git repo path and run the given git command in the repo. It will fail if the Repo is not a git repo or git is not working properly
#Example : runGit("/path/to/my/repo/", ["rev-parse", "--is-inside-work-tree"]) would return true if that was a real repo
    result = subprocess.run(# run the git command
        ["git", *args], #git plus the cmd, we use "rev-parse --is-inside-work-tree" in our example
        cwd=Path(repo_path),#run it in the selected git repo, we use "/path/to/my/repo/" in the example
        check=True, #If a non-zero exit happens a called process error is thrown
        stdout=subprocess.PIPE, #captures output
        stderr=subprocess.PIPE, #captures errors
        text=True, #set text to string and not bytes
    )
    return result.stdout #return gits printed output

def calculateRepoHealth(repo_path: Pathish, last_commit: Optional[datetime], total_commits: int) -> float:
    """Calculate repository health score (0-100) based on documentation, recency, activity, and best practices.
    
    Health indicators:
    - Documentation presence (README, LICENSE, etc.) - 30 points
    - Commit recency (how recently was last commit) - 25 points  
    - Commit activity (total commits as proxy for maturity) - 20 points
    - Test presence (test files/directories) - 15 points
    - Configuration files (.gitignore, etc.) - 10 points
    
    Returns:
        float: Health score from 0.0 to 100.0
    """
    repo_path = Path(repo_path)
    score = 0.0
    
    # Documentation presence (30 points max)
    doc_files = {
        'README.md': 12,
        'README': 8,
        'LICENSE': 8,
        'CONTRIBUTING.md': 5,
        'CHANGELOG.md': 3,
        'docs': 2,  # directory
    }
    for doc, points in doc_files.items():
        doc_path = repo_path / doc
        if doc_path.exists():
            score += points
    
    # Commit recency (25 points max)
    if last_commit:
        days_since_last = (datetime.now() - last_commit).days
        if days_since_last <= 7:
            score += 25  # Active (within a week)
        elif days_since_last <= 30:
            score += 20  # Recent (within a month)
        elif days_since_last <= 90:
            score += 15  # Moderate (within 3 months)
        elif days_since_last <= 180:
            score += 10  # Older (within 6 months)
        elif days_since_last <= 365:
            score += 5   # Old (within a year)
        # else: 0 points for very old repos
    
    # Commit activity (20 points max)
    if total_commits >= 100:
        score += 20  # Mature project
    elif total_commits >= 50:
        score += 15  # Good activity
    elif total_commits >= 20:
        score += 10  # Moderate activity
    elif total_commits >= 10:
        score += 5   # Some activity
    # else: 0 points for minimal commits
    
    # Test presence (15 points max)
    test_indicators = [
        'tests', 'test', '__tests__', 'spec', 'specs',
        'pytest.ini', 'jest.config.js', 'karma.conf.js'
    ]
    test_score = 0
    for indicator in test_indicators:
        test_path = repo_path / indicator
        if test_path.exists():
            test_score = 15
            break
    # Also check for test files in src
    if test_score == 0:
        for pattern in ['test_*.py', '*_test.py', '*.test.js', '*.spec.js']:
            if list(repo_path.rglob(pattern)):
                test_score = 15
                break
    score += test_score
    
    # Configuration files (10 points max)
    config_files = ['.gitignore', '.editorconfig', '.prettierrc', '.eslintrc', 'pyproject.toml']
    config_score = 0
    for config in config_files:
        if (repo_path / config).exists():
            config_score += 2
            if config_score >= 10:
                break
    score += min(config_score, 10)
    
    return round(min(score, 100.0), 2)

def getRepoStats(repo_path: Pathish) -> RepoStats: #This function will get the basic repo stats for a given git repo path
    if not isGitRepo(repo_path): #check if its a git repo
        raise ValueError(f"The path {repo_path} is not a git repository.") #raise error if not

    repo = git.Repo(repo_path) #initialize the git repo object

    # Get project name from the folder name
    project_name = Path(repo_path).name

    # Get primary language by analyzing file extensions
    language_counter = Counter()
    if repo.head.is_valid():
        commit = repo.head.commit
    else:
        print("Repository has no commits")
        raise ValueError("Repository has not commits.")
    
    for blob in commit.tree.traverse(): #traverse all files in the repo
        if blob.type == 'blob': #if its a file
            ext = Path(blob.path).suffix.lower() #get the file extension
            if ext: #if it has an extension
                language_counter[ext] += 1 #count it
    primary_language = language_counter.most_common(1)[0][0] if language_counter else "Unknown"
    languages = [lang for lang, _ in language_counter.most_common()] #list of languages used in the repo
    language_percentages = [count / sum(language_counter.values()) * 100 for _, count in language_counter.most_common()] #percentage of each language used

    # Detect frameworks
    frameworks = detect_frameworks(repo_path)

    # Check if the repository is collaborative
    is_collaborative = len(repo.remotes) > 0 # if there are remotes, its collaborative
    # Email-based check for multiple contributors
    authors = {commit.author.email for commit in repo.iter_commits()}
    is_collaborative = is_collaborative or len(authors) > 1

    # Get first and last commit dates
    commits = list(repo.iter_commits())#list of all commits in the repo
    first_commit = datetime.fromtimestamp(commits[-1].committed_date) if commits else None #Formatted as year-month-day hour:minute:second
    last_commit = datetime.fromtimestamp(commits[0].committed_date) if commits else None #Formatted as year-month-day hour:minute:second
    
    # Calculate repository health score
    health_score = calculateRepoHealth(repo_path, last_commit, len(commits))

    return RepoStats(
        project_name=project_name,
        project_path=str(repo_path),
        is_collaborative=is_collaborative,
        primary_language=primary_language,
        Languages=languages,
        language_percentages=language_percentages,
        first_commit=first_commit,
        last_commit=last_commit,
        total_commits=len(commits),
        frameworks=frameworks,
        health_score=health_score,
    )

def saveRepoStats(stats, db=None):
    """Save repository statistics to database.
    
    Args:
        stats: RepoStats object to save
        db: Optional SQLAlchemy session. If None, creates a new session.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    
    try:
        repo_stat = RepoStat(
            project_name=stats.project_name,
            project_path=stats.project_path,
            is_collaborative=stats.is_collaborative,
            primary_language=stats.primary_language,
            languages=stats.Languages,
            language_percentages=stats.language_percentages,
            first_commit=stats.first_commit,
            last_commit=stats.last_commit,
            total_commits=stats.total_commits,
            frameworks=stats.frameworks,
            health_score=stats.health_score,
        )
        db.add(repo_stat)
        # Ensure an ID is assigned even when the caller manages the session.
        db.flush()
        if own_session:
            db.commit()
            db.refresh(repo_stat)
        print(f"Saved repo stats: {repo_stat.project_name}")
        return repo_stat
    except Exception as e:
        if own_session:
            db.rollback()
        print(f"Error saving repo stats: {e}")
        raise
    finally:
        if own_session:
            db.close()
