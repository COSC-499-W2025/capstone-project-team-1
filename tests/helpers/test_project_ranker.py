import os
import shutil
import zipfile
from pathlib import Path
import pytest
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
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
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
    portfolio = next((p for p in results if p["name"] == "personal-portfolio-site"), None)
    assert portfolio is not None
    assert portfolio["score"] == 100.0
    assert portfolio["total_commits"] == 21
    assert portfolio["user_commits"] == 21
    
    # Verify sensor-fleet-backend (should be partial)
    sensor_fleet = next((p for p in results if p["name"] == "sensor-fleet-backend"), None)
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
