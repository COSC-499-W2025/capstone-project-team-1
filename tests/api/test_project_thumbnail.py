"""Tests for project thumbnail upload/url endpoints and response fields."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifactminer.api import projects as projects_module


def _get_project_id(client) -> int:
    response = client.get("/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) > 0
    return projects[0]["id"]


def _redirect_thumbnails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    thumbnails_root = tmp_path / "uploads" / "thumbnails"
    monkeypatch.setattr(projects_module, "THUMBNAILS_DIR", thumbnails_root)
    return thumbnails_root


def test_project_responses_include_thumbnail_url_field(client):
    project_id = _get_project_id(client)

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    assert "thumbnail_url" in list_response.json()[0]

    detail_response = client.get(f"/projects/{project_id}")
    assert detail_response.status_code == 200
    assert "thumbnail_url" in detail_response.json()


def test_upload_thumbnail_png_success(client, tmp_path, monkeypatch):
    project_id = _get_project_id(client)
    thumbnails_root = _redirect_thumbnails(monkeypatch, tmp_path)

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        files={"file": ("thumb.png", b"png-bytes", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["thumbnail_url"].startswith("/uploads/thumbnails/")

    saved_file = thumbnails_root / Path(payload["thumbnail_url"]).name
    assert saved_file.exists()

    detail = client.get(f"/projects/{project_id}").json()
    assert detail["thumbnail_url"] == payload["thumbnail_url"]

    listing = client.get("/projects").json()
    matching = [p for p in listing if p["id"] == project_id]
    assert len(matching) == 1
    assert matching[0]["thumbnail_url"] == payload["thumbnail_url"]


def test_upload_thumbnail_jpg_success(client, tmp_path, monkeypatch):
    project_id = _get_project_id(client)
    _redirect_thumbnails(monkeypatch, tmp_path)

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        files={"file": ("thumb.jpg", b"jpg-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["thumbnail_url"].endswith(".jpg")


@pytest.mark.parametrize(
    "thumbnail_url",
    [
        "http://example.com/thumb.png",
        "https://example.com/thumb.png",
    ],
)
def test_external_thumbnail_url_success(client, thumbnail_url):
    project_id = _get_project_id(client)

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        data={"thumbnail_url": thumbnail_url},
    )

    assert response.status_code == 200
    assert response.json()["thumbnail_url"] == thumbnail_url


def test_thumbnail_rejects_both_file_and_url(client, tmp_path, monkeypatch):
    project_id = _get_project_id(client)
    _redirect_thumbnails(monkeypatch, tmp_path)

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        data={"thumbnail_url": "https://example.com/thumb.png"},
        files={"file": ("thumb.png", b"png-bytes", "image/png")},
    )

    assert response.status_code == 422
    assert "exactly one" in response.json()["detail"]


def test_thumbnail_rejects_missing_file_and_url(client):
    project_id = _get_project_id(client)

    response = client.post(f"/projects/{project_id}/thumbnail")

    assert response.status_code == 422
    assert "exactly one" in response.json()["detail"]


def test_thumbnail_rejects_unsupported_file_type(client, tmp_path, monkeypatch):
    project_id = _get_project_id(client)
    _redirect_thumbnails(monkeypatch, tmp_path)

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        files={"file": ("thumb.gif", b"gif-bytes", "image/gif")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Only PNG and JPG images are allowed."


def test_thumbnail_rejects_invalid_url_scheme(client):
    project_id = _get_project_id(client)

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        data={"thumbnail_url": "ftp://example.com/thumb.png"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "thumbnail_url must be a valid http(s) URL"


def test_thumbnail_rejects_file_over_5mb(client, tmp_path, monkeypatch):
    project_id = _get_project_id(client)
    _redirect_thumbnails(monkeypatch, tmp_path)

    too_large = b"a" * (projects_module.MAX_THUMBNAIL_BYTES + 1)
    response = client.post(
        f"/projects/{project_id}/thumbnail",
        files={"file": ("thumb.png", too_large, "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Thumbnail exceeds 5 MB size limit."


def test_thumbnail_project_not_found_returns_404(client):
    response = client.post(
        "/projects/99999/thumbnail",
        data={"thumbnail_url": "https://example.com/thumb.png"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_thumbnail_soft_deleted_project_returns_404(client):
    project_id = _get_project_id(client)
    delete_response = client.delete(f"/projects/{project_id}")
    assert delete_response.status_code == 200

    response = client.post(
        f"/projects/{project_id}/thumbnail",
        data={"thumbnail_url": "https://example.com/thumb.png"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_thumbnail_replace_deletes_old_uploaded_file(client, tmp_path, monkeypatch):
    project_id = _get_project_id(client)
    thumbnails_root = _redirect_thumbnails(monkeypatch, tmp_path)

    first_response = client.post(
        f"/projects/{project_id}/thumbnail",
        files={"file": ("thumb.png", b"first-image", "image/png")},
    )
    assert first_response.status_code == 200
    first_thumbnail_url = first_response.json()["thumbnail_url"]
    first_saved_path = thumbnails_root / Path(first_thumbnail_url).name
    assert first_saved_path.exists()

    second_response = client.post(
        f"/projects/{project_id}/thumbnail",
        data={"thumbnail_url": "http://example.com/new-thumb.png"},
    )
    assert second_response.status_code == 200
    assert second_response.json()["thumbnail_url"] == "http://example.com/new-thumb.png"
    assert not first_saved_path.exists()
