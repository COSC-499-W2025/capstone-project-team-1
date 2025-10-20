#Part of the Repository Intelligence Module
#Owner: Evan/van-cpu
import subprocess, os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Optional, Union
from pathlib import Path

@dataclass
class RepoStats: #This is the basic Repo class for storing the results of the git files.
    project_name: str #store project name as a string
    primary_language: str #Primary language name as a string
    is_collaborative: bool #Is collaborative as a boolean to see whether the user is the only one to edit this file or had help.
    first_commit: Optional[datetime] = None # Optional addition is the users first commit date/time
    last_commit: Optional[datetime] = None # Optional addition is the users last commit date/time

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

def getAuthorsCommitCounts(repo_path: Pathish, since: Optional[str] = None) -> Dict[str, int]: #Function takes the Repo path, and "since" which is an optional time filter so it will only count commits pass a certain time, and returns a count of commits per email that made a commit/contributed.
#Example : getAuthorCommitCounts("/path/to/my/repo/")
#Example2 : getAuthorCommitCounts("/path/to/my/repo/", "10,19,2025")
    args = ["log", "--all", "--pretty=%ae"]  #args is for the command we are going to run in git, all logs, pretty=%ae makes it return only the authors email
    if since:#if the user specified a since date it will be added to the arguement
        args.insert(1, f'--since={since}')
    out = runGit(repo_path, args)#use the runGit method with our args
    emails = [line.strip().lower() for line in out.splitlines() if line.strip()]#Formats all the emails to be consistent all lowercase in one line in a list and skips blank lines.
    counts = Counter(emails)# Counts each of teh emails
    counts.pop("", None) #remove anything empty
    return dict(counts)