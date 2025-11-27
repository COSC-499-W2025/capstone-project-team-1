# Part of the Repository Intelligence Module
# Owner: Evan/van-cpu
# Tests for activity classification of user commits


import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.artifactminer.RepositoryIntelligence.activity_classifier import classify_commit_activities, print_activity_summary
from src.artifactminer.RepositoryIntelligence.repo_intelligence_user import getUserRepoStats, collect_user_additions
from src.artifactminer.db.database import SessionLocal
from src.artifactminer.db.models import UserRepoStat
def test_classify_commit_activities():
    # Setup: Create a temporary git repo with commits
    root = Path(__file__).resolve().parents[2]
    user_email = "ecrowl01@student.ubc.ca"
    # Ensure the repo exists and has commits by the user
    stats = getUserRepoStats(root, user_email)
    print_activity_summary(stats.commitActivities)
    assert isinstance(stats.commitActivities, dict)


