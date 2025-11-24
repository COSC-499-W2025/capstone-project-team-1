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
def test_single_line_docstring_counts_as_docs():
    additions = ['"""Short summary for this module."""\n']
    summary = classify_commit_activities(additions)
    assert summary["docs"]["lines_added"] > 0
    assert summary["code"]["lines_added"] == 0

def test_multiline_docstring_counts_all_lines_as_docs():
    additions = ['"""\nSummary line\nAnother line\n"""\n']
    summary = classify_commit_activities(additions)
    assert summary["docs"]["lines_added"] == 4  # 4 non-blank lines

def test_mixed_code_and_docs():
    additions = [
        '"""Module docstring."""\n',
        'def my_function():\n',
        '    """Function docstring."""\n',
        '    pass\n'
    ]
    summary = classify_commit_activities(additions)
    assert summary["docs"]["lines_added"] == 2  # 2 docstring lines
    assert summary["code"]["lines_added"] == 2  # def line + pass line

def test_no_docstrings():
    additions = [
        'def my_function(): #inline test\n',
        '    pass\n'
    ]
    summary = classify_commit_activities(additions)
    assert summary["docs"]["lines_added"] == 1
    assert summary["code"]["lines_added"] == 2
def test_config_lines():
    additions = [
        'import os\n',
        'os.environ["DEBUG"] = "1"  # set debug mode\n'
    ]
    summary = classify_commit_activities(additions)
    assert summary["config"]["lines_added"] == 1
    assert summary["code"]["lines_added"] == 2

def test_env_design_config_lines():
    additions = [
        'DATABASE_URL=postgres://user:pass@localhost/dbname\n',
        'os.environ["DEBUG"] = "1"\n'
    ]
    summary = classify_commit_activities(additions)
    assert summary["config"]["lines_added"] == 2

