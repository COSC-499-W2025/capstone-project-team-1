# Part of the Repository Intelligence Module
# Owner: Evan/van-cpu
# Tests for AI-driven user commit summarization

import sys
import os
from pathlib import Path
from datetime import datetime

from artifactminer.RepositoryIntelligence.repo_intelligence_main import calculateRepoHealth
from artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_Repository_Health_user_commit_summary():
    root = Path(__file__).resolve().parents[2]
    # Replace with a valid email present in the commit history of the repo
    repostats1 = getRepoStats(str(root))
    health_score = calculateRepoHealth(str(root), repostats1.last_commit, repostats1.total_commits)
    print(f"Health Score: {health_score}")
    assert 0 <= health_score <= 100
    assert isinstance(health_score, float)

def test_Repository_Health_no_commits():
    root = Path(__file__).resolve().parents[2]
    # Simulate a repo with no commits
    repostats2 = getRepoStats(str(root))
    repostats2.total_commits = 0
    health_score = calculateRepoHealth(str(root), repostats2.last_commit, repostats2.total_commits)
    print(f"Health Score for no commits: {health_score}")
    assert health_score >= 55
