# Part of the Repository Intelligence Module
# Owner: Evan/van-cpu
# Tests for AI-driven user commit summarization

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats
from src.artifactminer.db.database import SessionLocal
from src.artifactminer.db.models import Consent

# test getUserRepoStats with current repo and user email
def test_getUserRepoStats():
    root = Path(__file__).resolve().parents[2]
    # Replace with a valid email present in the commit history of the repo
    test_email = "ecrowl01@student.ubc.ca"
    stats = getUserRepoStats(root, test_email)
    assert stats.project_name == root.name
    assert isinstance(stats.first_commit, (type(None), datetime))
    assert isinstance(stats.last_commit, (type(None), datetime))
    assert isinstance(stats.total_commits, (type(None), int))
    assert isinstance(stats.userStatspercentages, (type(None), float))
    assert isinstance(stats.commitFrequency, (type(None), float))
    print(f"UserRepoStats: {stats}")
