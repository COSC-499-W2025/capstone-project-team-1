import os
from pathlib import Path
# Part of the Repository Intelligence Module
#Owner: Evan/van-cpu

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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