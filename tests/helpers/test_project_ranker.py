import zipfile
from pathlib import Path
import pytest
import unittest.mock
import subprocess
from artifactminer.helpers.project_ranker import rank_projects


@pytest.fixture(scope="module")
def real_projects_data(tmp_path_factory):
    # Locate the zip file
    # tests/helpers/test_project_ranker.py -> tests/helpers/ -> tests/ -> data/mock_projects.zip
    current_dir = Path(__file__).parent
    zip_path = current_dir.parent.parent / "tests" / "data" / "mock_projects.zip"

    if not zip_path.exists():
        pytest.skip("mock_projects.zip not found")

    # Extract to a temporary directory
    temp_dir = tmp_path_factory.mktemp("projects_data")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # The zip contains a 'projects' folder at the root
    projects_root = temp_dir / "projects"
    return projects_root


def test_rank_projects_real_data(real_projects_data):
    projects_dir = real_projects_data

    assert projects_dir.exists(), f"Projects directory not found at {projects_dir}"

    # Run ranker with known user email
    results = rank_projects(str(projects_dir), user_email="shlok10@student.ubc.ca")

    assert len(results) > 0

    # Verify personal-portfolio-site (should be 100%)
    portfolio = next(
        (p for p in results if p["name"] == "personal-portfolio-site"), None
    )
    assert portfolio is not None
    assert portfolio["score"] == 100.0
    assert portfolio["total_commits"] == 21
    assert portfolio["user_commits"] == 21

    # Verify sensor-fleet-backend (should be partial)
    sensor_fleet = next(
        (p for p in results if p["name"] == "sensor-fleet-backend"), None
    )
    assert sensor_fleet is not None
    assert sensor_fleet["score"] > 0
    assert sensor_fleet["score"] < 100.0
    # Based on previous runs, it was 43.48
    assert sensor_fleet["score"] == 43.48

    # Verify sorting
    scores = [p["score"] for p in results]
    assert scores == sorted(scores, reverse=True)


def test_rank_projects_invalid_email(real_projects_data):
    projects_dir = real_projects_data

    results = rank_projects(str(projects_dir), user_email="nonexistent@example.com")

    assert len(results) > 0
    assert all(p["score"] == 0.0 for p in results)


def test_rank_projects_invalid_path():
    """Test that a non-existent path returns an empty list."""
    results = rank_projects("/path/to/nowhere", "user@example.com")
    assert results == []


def test_rank_projects_empty_directory(tmp_path):
    """Test that an empty directory returns an empty list."""
    results = rank_projects(str(tmp_path), "user@example.com")
    assert results == []


def test_rank_projects_skip_non_git(tmp_path):
    """Test that directories without a .git folder are skipped."""
    # Create a project folder without .git
    project_dir = tmp_path / "no-git-project"
    project_dir.mkdir()
    (project_dir / "file.txt").touch()

    results = rank_projects(str(tmp_path), "user@example.com")
    assert results == []


def test_rank_projects_zero_commits(tmp_path):
    """Test that a repository with zero commits is handled gracefully."""
    project_dir = tmp_path / "zero-commit-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()

    # Mock subprocess to return empty string (no commits)
    with unittest.mock.patch("subprocess.check_output", return_value=""):
        results = rank_projects(str(tmp_path), "user@example.com")

    assert len(results) == 1
    assert results[0]["name"] == "zero-commit-project"
    assert results[0]["score"] == 0.0
    assert results[0]["total_commits"] == 0
    assert results[0]["user_commits"] == 0


def test_rank_projects_git_failure(tmp_path):
    """Test that git command failure is handled gracefully."""
    project_dir = tmp_path / "broken-git-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()

    # Mock subprocess to raise CalledProcessError
    with unittest.mock.patch(
        "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git")
    ):
        results = rank_projects(str(tmp_path), "user@example.com")

    assert results == []


def test_rank_projects_malformed_output(tmp_path):
    """Test that malformed git output is ignored."""
    project_dir = tmp_path / "malformed-output-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()

    # Mock output with some valid and some invalid lines
    mock_output = """
       10\tValid User <user@example.com>
       invalid line without tab or email
       5\tAnother User <other@example.com>
    """

    with unittest.mock.patch("subprocess.check_output", return_value=mock_output):
        results = rank_projects(str(tmp_path), "user@example.com")

    assert len(results) == 1
    assert results[0]["score"] == 66.67  # 10 / 15 * 100
    assert results[0]["total_commits"] == 15
    assert results[0]["user_commits"] == 10


def test_rank_projects_case_insensitivity(tmp_path):
    """Test that email matching is case-insensitive."""
    project_dir = tmp_path / "case-test-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()

    mock_output = "   10\tUser Name <USER@EXAMPLE.COM>"

    with unittest.mock.patch("subprocess.check_output", return_value=mock_output):
        # Pass lowercase email to function
        results = rank_projects(str(tmp_path), "user@example.com")

    assert len(results) == 1
    assert results[0]["score"] == 100.0
    assert results[0]["user_commits"] == 10


def test_rank_projects_no_user_commits(tmp_path):
    """Test handling when user has zero commits in a repo with other commits."""
    project_dir = tmp_path / "no-user-commits-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()

    mock_output = "   20\tOther User <other@example.com>"

    with unittest.mock.patch("subprocess.check_output", return_value=mock_output):
        results = rank_projects(str(tmp_path), "user@example.com")

    assert len(results) == 1
    assert results[0]["score"] == 0.0
    assert results[0]["total_commits"] == 20
    assert results[0]["user_commits"] == 0
