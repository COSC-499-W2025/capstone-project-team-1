"""
Tests for the master analyze endpoint: POST /analyze/{zip_id}

These tests verify the full orchestration pipeline that:
1. Extracts uploaded ZIP to persistent storage
2. Discovers git repositories
3. Analyzes repos (stats, skills, insights)
4. Ranks projects and generates summaries
"""

import shutil
import zipfile
from pathlib import Path

import pytest

from artifactminer.api import analyze as analyze_module


def _setup_test_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Redirect uploads and extraction dirs to temp location."""
    uploads_dir = tmp_path / "uploads"
    extraction_dir = tmp_path / "extracted"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    extraction_dir.mkdir(parents=True, exist_ok=True)

    # Redirect the extraction base dir
    monkeypatch.setattr(analyze_module, "EXTRACTION_BASE_DIR", extraction_dir)

    return uploads_dir, extraction_dir


def _create_mock_zip_in_db(client, uploads_dir: Path, zip_source: Path) -> int:
    """Copy a zip file to uploads dir and create DB record via upload endpoint."""
    from artifactminer.api import zip as zip_module

    # Read the actual zip file
    with open(zip_source, "rb") as f:
        zip_bytes = f.read()

    files = {"file": ("test_projects.zip", zip_bytes, "application/zip")}
    response = client.post("/zip/upload", files=files)
    assert response.status_code == 200
    return response.json()["zip_id"]


def _seed_user_email(client):
    """Submit user email answer required for analysis."""
    response = client.post(
        "/answers",
        json={
            "answers": {
                "email": "test@example.com",
                "artifacts_focus": "code",
                "end_goal": "testing",
                "repository_priority": "git",
            }
        },
    )
    assert response.status_code == 200


def _set_consent(client, level: str = "none"):
    """Set consent level."""
    response = client.put("/consent", json={"consent_level": level})
    assert response.status_code == 200


class TestAnalyzeEndpoint:
    """Tests for POST /analyze/{zip_id}"""

    def test_analyze_returns_404_for_nonexistent_zip(self, client):
        """Endpoint returns 404 when zip_id doesn't exist."""
        _seed_user_email(client)
        response = client.post("/analyze/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_analyze_returns_400_without_user_email(
        self, client, tmp_path, monkeypatch
    ):
        """Endpoint requires user email to be configured."""
        uploads_dir, _ = _setup_test_dirs(monkeypatch, tmp_path)

        # Create a dummy zip (doesn't need to be valid for this test)
        dummy_zip = uploads_dir / "dummy.zip"
        with zipfile.ZipFile(dummy_zip, "w") as zf:
            zf.writestr("readme.txt", "hello")

        # Manually insert zip record
        from artifactminer.db.models import UploadedZip
        from artifactminer.db import SessionLocal

        # Use the client's test database by going through the upload endpoint
        files = {"file": ("dummy.zip", open(dummy_zip, "rb"), "application/zip")}
        upload_response = client.post("/zip/upload", files=files)
        zip_id = upload_response.json()["zip_id"]

        # Don't seed email - this should fail
        response = client.post(f"/analyze/{zip_id}")
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_analyze_returns_400_for_zip_without_git_repos(
        self, client, tmp_path, monkeypatch
    ):
        """Endpoint returns 400 when ZIP contains no git repositories."""
        uploads_dir, extraction_dir = _setup_test_dirs(monkeypatch, tmp_path)

        # Redirect uploads for the zip module too
        from artifactminer.api import zip as zip_module

        monkeypatch.setattr(zip_module, "UPLOADS_DIR", uploads_dir)

        # Create a zip without any git repos
        no_git_zip = tmp_path / "no_git.zip"
        with zipfile.ZipFile(no_git_zip, "w") as zf:
            zf.writestr("project/readme.txt", "No git here")
            zf.writestr("project/main.py", "print('hello')")

        # Upload it
        files = {"file": ("no_git.zip", open(no_git_zip, "rb"), "application/zip")}
        upload_response = client.post("/zip/upload", files=files)
        zip_id = upload_response.json()["zip_id"]

        _seed_user_email(client)
        _set_consent(client, "none")

        response = client.post(f"/analyze/{zip_id}")
        assert response.status_code == 400
        assert "no git repositories" in response.json()["detail"].lower()


class TestAnalyzeWithRealRepos:
    """Tests using the mock_projects.zip with real git repos."""

    @pytest.fixture
    def mock_projects_zip(self) -> Path:
        """Path to the mock projects ZIP with real git repos."""
        return Path(__file__).parent.parent / "data" / "mock_projects.zip"

    def test_analyze_discovers_git_repos(
        self, client, tmp_path, monkeypatch, mock_projects_zip
    ):
        """Endpoint discovers git repositories in the ZIP."""
        if not mock_projects_zip.exists():
            pytest.skip("mock_projects.zip not found")

        uploads_dir, extraction_dir = _setup_test_dirs(monkeypatch, tmp_path)

        from artifactminer.api import zip as zip_module

        monkeypatch.setattr(zip_module, "UPLOADS_DIR", uploads_dir)

        # Upload the mock projects zip
        files = {
            "file": (
                "mock_projects.zip",
                open(mock_projects_zip, "rb"),
                "application/zip",
            )
        }
        upload_response = client.post("/zip/upload", files=files)
        assert upload_response.status_code == 200
        zip_id = upload_response.json()["zip_id"]

        _seed_user_email(client)
        _set_consent(client, "none")

        response = client.post(f"/analyze/{zip_id}")

        # Should succeed and find repos
        assert response.status_code == 200
        data = response.json()

        assert data["zip_id"] == zip_id
        assert data["repos_found"] > 0
        assert len(data["repos_analyzed"]) > 0
        assert data["user_email"] == "test@example.com"
        assert data["consent_level"] == "none"

        # Verify extraction path was set
        assert "extracted" in data["extraction_path"]

    def test_analyze_extracts_to_persistent_location(
        self, client, tmp_path, monkeypatch, mock_projects_zip
    ):
        """Endpoint extracts ZIP to persistent ./extracted/{zip_id}/ location."""
        if not mock_projects_zip.exists():
            pytest.skip("mock_projects.zip not found")

        uploads_dir, extraction_dir = _setup_test_dirs(monkeypatch, tmp_path)

        from artifactminer.api import zip as zip_module

        monkeypatch.setattr(zip_module, "UPLOADS_DIR", uploads_dir)

        files = {
            "file": (
                "mock_projects.zip",
                open(mock_projects_zip, "rb"),
                "application/zip",
            )
        }
        upload_response = client.post("/zip/upload", files=files)
        zip_id = upload_response.json()["zip_id"]

        _seed_user_email(client)
        _set_consent(client, "none")

        response = client.post(f"/analyze/{zip_id}")
        assert response.status_code == 200

        # Verify files were extracted to persistent location
        expected_extraction = extraction_dir / str(zip_id)
        assert expected_extraction.exists()

        # Should contain the projects folder
        extracted_contents = list(expected_extraction.rglob("*"))
        assert len(extracted_contents) > 0


class TestAnalyzeHelperFunctions:
    """Tests for helper functions in analyze module."""

    def test_discover_git_repos_finds_repos(self, tmp_path):
        """discover_git_repos finds directories with .git folders."""
        # Create a fake git repo structure
        repo1 = tmp_path / "project1"
        repo1.mkdir()
        (repo1 / ".git").mkdir()
        (repo1 / "main.py").write_text("print('hello')")

        repo2 = tmp_path / "nested" / "project2"
        repo2.mkdir(parents=True)
        (repo2 / ".git").mkdir()

        # Non-git directory
        not_a_repo = tmp_path / "docs"
        not_a_repo.mkdir()
        (not_a_repo / "readme.md").write_text("# Docs")

        repos = analyze_module.discover_git_repos(tmp_path)

        assert len(repos) == 2
        repo_names = {r.name for r in repos}
        assert "project1" in repo_names
        assert "project2" in repo_names
        assert "docs" not in repo_names

    def test_discover_git_repos_skips_nested_git(self, tmp_path):
        """discover_git_repos doesn't double-count nested .git directories."""
        # Create repo with submodule-like structure
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / ".git").mkdir()

        # This shouldn't be counted separately
        nested = parent / "vendor" / "lib"
        nested.mkdir(parents=True)
        (nested / ".git").mkdir()

        repos = analyze_module.discover_git_repos(tmp_path)

        # Should only find the parent, not the nested one
        assert len(repos) == 1
        assert repos[0].name == "parent"

    def test_extract_zip_creates_directory(self, tmp_path):
        """extract_zip_to_persistent_location creates extraction directory."""
        # Temporarily override the extraction base
        original_base = analyze_module.EXTRACTION_BASE_DIR
        analyze_module.EXTRACTION_BASE_DIR = tmp_path / "extracted"

        try:
            # Create a test zip
            test_zip = tmp_path / "test.zip"
            with zipfile.ZipFile(test_zip, "w") as zf:
                zf.writestr("file.txt", "content")

            result = analyze_module.extract_zip_to_persistent_location(
                str(test_zip), zip_id=42
            )

            assert result.exists()
            assert result.name == "42"
            assert (result / "file.txt").exists()
        finally:
            analyze_module.EXTRACTION_BASE_DIR = original_base

    def test_extract_zip_cleans_previous_extraction(self, tmp_path):
        """extract_zip_to_persistent_location removes previous extraction."""
        original_base = analyze_module.EXTRACTION_BASE_DIR
        analyze_module.EXTRACTION_BASE_DIR = tmp_path / "extracted"

        try:
            # Create pre-existing extraction
            old_extraction = tmp_path / "extracted" / "42"
            old_extraction.mkdir(parents=True)
            old_file = old_extraction / "old_file.txt"
            old_file.write_text("old content")

            # Create a new zip
            test_zip = tmp_path / "test.zip"
            with zipfile.ZipFile(test_zip, "w") as zf:
                zf.writestr("new_file.txt", "new content")

            result = analyze_module.extract_zip_to_persistent_location(
                str(test_zip), zip_id=42
            )

            # Old file should be gone
            assert not old_file.exists()
            # New file should exist
            assert (result / "new_file.txt").exists()
        finally:
            analyze_module.EXTRACTION_BASE_DIR = original_base
