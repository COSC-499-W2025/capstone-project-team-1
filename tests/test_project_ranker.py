import os
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
from artifactminer.helpers.project_ranker import rank_projects

# Mock data for git shortlog output
SINGLE_AUTHOR_OUTPUT = "    10\tShlok Shah"
MULTI_AUTHOR_OUTPUT = "    10\tShlok Shah\n     5\tOther User"
NO_USER_OUTPUT = "     5\tOther User"
EMPTY_OUTPUT = ""

@pytest.fixture
def mock_projects_dir(tmp_path):
    # Create a mock projects directory structure
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    
    # Project 1: Single author (User)
    p1 = projects_dir / "project1"
    p1.mkdir()
    (p1 / ".git").mkdir()
    
    # Project 2: Multi author (User + Other)
    p2 = projects_dir / "project2"
    p2.mkdir()
    (p2 / ".git").mkdir()
    
    # Project 3: No user commits
    p3 = projects_dir / "project3"
    p3.mkdir()
    (p3 / ".git").mkdir()
    
    # Project 4: Not a git repo
    p4 = projects_dir / "project4"
    p4.mkdir()
    
    return projects_dir

@patch("subprocess.check_output")
def test_rank_projects(mock_check_output, mock_projects_dir):
    def side_effect(cmd, cwd, **kwargs):
        cwd_path = Path(cwd)
        if cwd_path.name == "project1":
            return SINGLE_AUTHOR_OUTPUT
        elif cwd_path.name == "project2":
            return MULTI_AUTHOR_OUTPUT
        elif cwd_path.name == "project3":
            return NO_USER_OUTPUT
        return ""

    mock_check_output.side_effect = side_effect
    
    results = rank_projects(str(mock_projects_dir), user_name="Shlok Shah")
    
    # Expected results:
    # project1: 10/10 = 100%
    # project2: 10/15 = 66.67%
    # project3: 0/5 = 0%
    # project4: skipped
    
    assert len(results) == 3
    
    # Check sorting (descending score)
    assert results[0]["name"] == "project1"
    assert results[0]["score"] == 100.0
    
    assert results[1]["name"] == "project2"
    assert results[1]["score"] == 66.67
    
    assert results[2]["name"] == "project3"
    assert results[2]["score"] == 0.0

@patch("subprocess.check_output")
def test_rank_projects_empty_dir(mock_check_output, tmp_path):
    results = rank_projects(str(tmp_path), user_name="Shlok Shah")
    assert len(results) == 0

@patch("subprocess.check_output")
def test_rank_projects_git_error(mock_check_output, mock_projects_dir):
    # Simulate git error for all projects
    mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")
    
    results = rank_projects(str(mock_projects_dir), user_name="Shlok Shah")
    assert len(results) == 0
