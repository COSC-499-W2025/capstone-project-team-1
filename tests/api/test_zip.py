import shutil
from pathlib import Path

import pytest

from artifactminer.api import zip as zip_module

# Path to the real mock ZIP file in the test fixtures
MOCK_ZIP_PATH = (
    Path(__file__).parent.parent
    / "directorycrawler"
    / "mocks"
    / "mockdirectory_zip.zip"
)


def _redirect_uploads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    uploads_root = tmp_path / "uploads"
    monkeypatch.setattr(zip_module, "UPLOADS_DIR", uploads_root)
    return uploads_root


def test_upload_zip_succeeds(client, tmp_path, monkeypatch):
    """Test that ZIP upload saves file and returns correct response."""
    uploads_root = _redirect_uploads(monkeypatch, tmp_path)

    files = {"file": ("artifact.zip", b"PK\x03\x04", "application/zip")}
    response = client.post("/zip/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "artifact.zip"
    assert payload["zip_id"] > 0

    saved_files = list(uploads_root.glob("*artifact.zip"))
    assert saved_files, "uploaded file should be written to redirected uploads dir"


def test_get_directories_with_real_zip(client, tmp_path, monkeypatch):
    """Test directory listing using the real mockdirectory_zip.zip fixture."""
    uploads_root = _redirect_uploads(monkeypatch, tmp_path)

    # Read and upload the real ZIP file
    with open(MOCK_ZIP_PATH, "rb") as f:
        zip_bytes = f.read()

    files = {"file": ("mockdirectory_zip.zip", zip_bytes, "application/zip")}
    response = client.post("/zip/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    zip_id = payload["zip_id"]

    # Now test the directories endpoint
    directories = client.get(f"/zip/{zip_id}/directories")
    assert directories.status_code == 200
    dir_payload = directories.json()
    assert dir_payload["zip_id"] == zip_id
    assert dir_payload["filename"] == "mockdirectory_zip.zip"
    assert dir_payload["directories"] == ["mockdirectory_zip/"]


def test_upload_zip_rejects_non_zip(client, tmp_path, monkeypatch):
    """Test that non-ZIP files are rejected."""
    _redirect_uploads(monkeypatch, tmp_path)

    files = {"file": ("notes.txt", b"nope", "text/plain")}
    response = client.post("/zip/upload", files=files)

    assert response.status_code == 422
    assert response.json()["detail"] == "Only ZIP files are allowed."


def test_get_directories_missing_zip_returns_404(client):
    """Test that requesting directories for non-existent ZIP returns 404."""
    response = client.get("/zip/999/directories")
    assert response.status_code == 404
    assert response.json()["detail"] == "ZIP file not found."


def test_get_directories_deleted_file_returns_404(client, tmp_path, monkeypatch):
    """Test that requesting directories for a ZIP deleted from disk returns 404."""
    uploads_root = _redirect_uploads(monkeypatch, tmp_path)

    # Upload a valid ZIP first
    with open(MOCK_ZIP_PATH, "rb") as f:
        zip_bytes = f.read()

    files = {"file": ("todelete.zip", zip_bytes, "application/zip")}
    response = client.post("/zip/upload", files=files)
    assert response.status_code == 200
    zip_id = response.json()["zip_id"]

    # Delete the file from disk
    for f in uploads_root.glob("*todelete.zip"):
        f.unlink()

    # Now request directories - should 404
    response = client.get(f"/zip/{zip_id}/directories")
    assert response.status_code == 404
    assert response.json()["detail"] == "ZIP file no longer exists on disk."


def test_get_directories_corrupted_zip_returns_422(client, tmp_path, monkeypatch):
    """Test that corrupted ZIP files return 422."""
    uploads_root = _redirect_uploads(monkeypatch, tmp_path)

    # Upload a file with .zip extension but invalid content
    files = {"file": ("corrupt.zip", b"not a real zip file", "application/zip")}
    response = client.post("/zip/upload", files=files)

    assert response.status_code == 200
    zip_id = response.json()["zip_id"]

    # Try to list directories
    directories = client.get(f"/zip/{zip_id}/directories")
    assert directories.status_code == 422
    assert directories.json()["detail"] == "Invalid or corrupted ZIP file."
