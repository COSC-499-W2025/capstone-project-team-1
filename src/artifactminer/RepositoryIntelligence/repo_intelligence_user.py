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

@dataclass
class UserRepoStats:
    project_name: str 
    first_commit: Optional[datetime] = None 
    last_commit: Optional[datetime] = None 
    total_commits: Optional[int] = None 
