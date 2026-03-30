from pathlib import Path

import pytest

from artifactminer.api import zip as zip_module


def _redirect_uploads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    uploads_root = tmp_path / "uploads"
    monkeypatch.setattr(zip_module, "UPLOADS_DIR", uploads_root)
    return uploads_root


def test_upload_zip_succeeds_and_directories_available(client, tmp_path, monkeypatch):
    uploads_root = _redirect_uploads(monkeypatch, tmp_path)
    expected_directories = [
        "cs320_project/",
        "cs540_ai_project/",
        "hackathon_2024/",
        "personal_website/",
        "senior_design/",
    ]

    extracted_dir = tmp_path / "extracted" / "1"
    extracted_dir.mkdir(parents=True)
    monkeypatch.setattr(
        zip_module,
        "extract_zip_to_persistent_location",
        lambda zip_path, zip_id: extracted_dir,
    )
    monkeypatch.setattr(
        zip_module.directory_walk,
        "crawl_directory",
        lambda: (
            {
                "README.md": ("README.md", str(extracted_dir / "README.md")),
            },
            expected_directories,
        ),
    )

    zip_path = Path(__file__).resolve().parents[1] / "data" / "mock_projects.zip"
    with zip_path.open("rb") as f:
        files = {"file": ("artifact.zip", f.read(), "application/zip")}
    response = client.post("/zip/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "artifact.zip"
    assert payload["zip_id"] > 0

    saved_files = list(uploads_root.glob("*artifact.zip"))
    assert saved_files, "uploaded file should be written to redirected uploads dir"

    directories = client.get(f"/zip/{payload['zip_id']}/directories")
    assert directories.status_code == 200
    dir_payload = directories.json()
    assert dir_payload["zip_id"] == payload["zip_id"]
    assert dir_payload["directories"] == expected_directories


def test_upload_zip_rejects_non_zip(client, tmp_path, monkeypatch):
    _redirect_uploads(monkeypatch, tmp_path)

    files = {"file": ("notes.txt", b"nope", "text/plain")}
    response = client.post("/zip/upload", files=files)

    assert response.status_code == 422
    assert response.json()["detail"] == "Only ZIP files are allowed."


def test_get_directories_missing_zip_returns_404(client):
    response = client.get("/zip/999/directories")
    assert response.status_code == 404
    assert response.json()["detail"] == "ZIP file not found."


def test_extract_local_uses_uploaded_zip_id(client, tmp_path, monkeypatch):
    uploads_root = _redirect_uploads(monkeypatch, tmp_path)

    files = {"file": ("artifact.zip", b"fake-bytes", "application/zip")}
    upload_response = client.post("/zip/upload", files=files)
    zip_id = upload_response.json()["zip_id"]

    extracted_dir = tmp_path / "extracted" / str(zip_id)
    extracted_dir.mkdir(parents=True)

    monkeypatch.setattr(
        zip_module,
        "extract_zip_to_persistent_location",
        lambda zip_path, extracted_zip_id: extracted_dir,
    )

    response = client.post("/zip/extract-local", json={"zip_id": zip_id})

    assert response.status_code == 200
    assert response.json() == {
        "zip_id": zip_id,
        "extraction_path": str(extracted_dir.resolve()),
    }
    assert list(uploads_root.glob("*artifact.zip"))


def test_extract_local_missing_zip_returns_404(client):
    response = client.post("/zip/extract-local", json={"zip_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "ZIP file with id=999 not found"
