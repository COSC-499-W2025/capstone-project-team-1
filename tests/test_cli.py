"""CLI tests for artifactminer.main"""
import json
import subprocess
import sys
from pathlib import Path
import pytest

@pytest.fixture
def zip_file():
    return Path(__file__).parent / "data" / "mock_projects.zip"

def test_cli_requires_input(tmp_path):
    """CLI fails without --input argument."""
    result = subprocess.run([sys.executable, "-m", "artifactminer.main", "-o", str(tmp_path / "out.txt")], capture_output=True)
    assert result.returncode != 0

def test_cli_text_export(zip_file, tmp_path, monkeypatch):
    """CLI creates text output with project metrics."""
    if not zip_file.exists():
        pytest.skip("mock_projects.zip not found")
    out = tmp_path / "out.txt"
    monkeypatch.setenv("ARTIFACTMINER_DB", f"sqlite:///{tmp_path / 'test.db'}")
    result = subprocess.run([sys.executable, "-m", "artifactminer.main", "-i", str(zip_file), "-o", str(out), "-u", "test@test.com", "-c", "no_llm"], capture_output=True, timeout=120)
    assert result.returncode == 0 and out.exists()
    content = out.read_text()
    assert "PORTFOLIO ANALYSIS EXPORT" in content and "PROJECT ANALYSIS DETAILS" in content

def test_cli_json_export(zip_file, tmp_path, monkeypatch):
    """CLI creates JSON output with all fields."""
    if not zip_file.exists():
        pytest.skip("mock_projects.zip not found")
    out = tmp_path / "out.json"
    monkeypatch.setenv("ARTIFACTMINER_DB", f"sqlite:///{tmp_path / 'test.db'}")
    result = subprocess.run([sys.executable, "-m", "artifactminer.main", "-i", str(zip_file), "-o", str(out), "-u", "test@test.com", "-c", "no_llm"], capture_output=True, timeout=120)
    assert result.returncode == 0 and out.exists()
    data = json.loads(out.read_text())
    assert "project_analyses" in data and len(data["project_analyses"]) > 0

def test_cli_consent_levels(zip_file, tmp_path, monkeypatch):
    """CLI accepts different consent levels."""
    if not zip_file.exists():
        pytest.skip("mock_projects.zip not found")
    out = tmp_path / "out.txt"
    monkeypatch.setenv("ARTIFACTMINER_DB", f"sqlite:///{tmp_path / 'test.db'}")
    result = subprocess.run([sys.executable, "-m", "artifactminer.main", "-i", str(zip_file), "-o", str(out), "-u", "test@test.com", "-c", "none"], capture_output=True, timeout=120)
    assert result.returncode == 0

def test_cli_custom_email(zip_file, tmp_path, monkeypatch):
    """CLI accepts custom user email."""
    if not zip_file.exists():
        pytest.skip("mock_projects.zip not found")
    out = tmp_path / "out.txt"
    email = "custom@example.com"
    monkeypatch.setenv("ARTIFACTMINER_DB", f"sqlite:///{tmp_path / 'test.db'}")
    result = subprocess.run([sys.executable, "-m", "artifactminer.main", "-i", str(zip_file), "-o", str(out), "-u", email, "-c", "none"], capture_output=True, timeout=120)
    assert result.returncode == 0 and email in result.stdout.decode()

def test_cli_format_detection(zip_file, tmp_path, monkeypatch):
    """CLI detects format from file extension."""
    if not zip_file.exists():
        pytest.skip("mock_projects.zip not found")
    out = tmp_path / "out.json"
    monkeypatch.setenv("ARTIFACTMINER_DB", f"sqlite:///{tmp_path / 'test.db'}")
    result = subprocess.run([sys.executable, "-m", "artifactminer.main", "-i", str(zip_file), "-o", str(out), "-u", "test@test.com", "-c", "none"], capture_output=True, timeout=120)
    assert result.returncode == 0
    data = json.loads(out.read_text())
    assert isinstance(data, dict)
