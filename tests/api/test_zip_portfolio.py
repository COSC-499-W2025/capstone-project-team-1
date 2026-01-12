"""Tests for portfolio_id functionality in ZIP uploads.

These tests validate the implementation of GitHub Issue #252:
Add portfolio_id to UploadedZip model for linking multiple ZIPs.
"""

from pathlib import Path
from uuid import UUID

import pytest

from artifactminer.api import zip as zip_module


def _redirect_uploads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect uploads to a temporary directory for testing."""
    uploads_root = tmp_path / "uploads"
    monkeypatch.setattr(zip_module, "UPLOADS_DIR", uploads_root)
    return uploads_root


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


class TestPortfolioIdUpload:
    """Tests for portfolio_id functionality in POST /zip/upload endpoint."""

    def test_upload_zip_without_portfolio_id_generates_new_uuid(
        self, client, tmp_path, monkeypatch
    ):
        """When no portfolio_id is provided, a new UUID should be generated."""
        _redirect_uploads(monkeypatch, tmp_path)

        files = {"file": ("artifact.zip", b"fake-bytes", "application/zip")}
        response = client.post("/zip/upload", files=files)

        assert response.status_code == 200
        payload = response.json()

        # Should return a portfolio_id
        assert "portfolio_id" in payload, "Response should include portfolio_id"
        
        # The portfolio_id should be a valid UUID
        assert _is_valid_uuid(payload["portfolio_id"]), (
            f"portfolio_id '{payload['portfolio_id']}' should be a valid UUID"
        )

    def test_upload_zip_with_portfolio_id_links_to_existing_portfolio(
        self, client, tmp_path, monkeypatch
    ):
        """When a portfolio_id is provided, the ZIP should be linked to that portfolio."""
        _redirect_uploads(monkeypatch, tmp_path)

        # First upload - get a portfolio_id
        files = {"file": ("first.zip", b"first-bytes", "application/zip")}
        first_response = client.post("/zip/upload", files=files)
        assert first_response.status_code == 200
        portfolio_id = first_response.json()["portfolio_id"]

        # Second upload - link to existing portfolio
        files = {"file": ("second.zip", b"second-bytes", "application/zip")}
        second_response = client.post(
            f"/zip/upload?portfolio_id={portfolio_id}", files=files
        )

        assert second_response.status_code == 200
        second_payload = second_response.json()

        # Should have the same portfolio_id
        assert second_payload["portfolio_id"] == portfolio_id, (
            "Second upload should be linked to the same portfolio"
        )
        # But different zip_id
        assert second_payload["zip_id"] != first_response.json()["zip_id"], (
            "Each upload should have a unique zip_id"
        )

    def test_upload_multiple_zips_with_same_portfolio_id(
        self, client, tmp_path, monkeypatch
    ):
        """Upload 3 ZIPs to the same portfolio and verify all are linked correctly."""
        _redirect_uploads(monkeypatch, tmp_path)

        zip_ids = []
        portfolio_id = None

        # Upload 3 ZIPs to the same portfolio
        for i in range(3):
            files = {"file": (f"archive_{i}.zip", f"bytes-{i}".encode(), "application/zip")}
            
            if portfolio_id:
                response = client.post(
                    f"/zip/upload?portfolio_id={portfolio_id}", files=files
                )
            else:
                response = client.post("/zip/upload", files=files)
                portfolio_id = response.json()["portfolio_id"]

            assert response.status_code == 200
            payload = response.json()
            zip_ids.append(payload["zip_id"])

            # All should share the same portfolio_id
            assert payload["portfolio_id"] == portfolio_id

        # Verify all zip_ids are unique
        assert len(set(zip_ids)) == 3, "Each ZIP should have a unique zip_id"

        # Verify via GET /zip/portfolios endpoint that all 3 are linked
        portfolios_response = client.get(f"/zip/portfolios/{portfolio_id}")
        assert portfolios_response.status_code == 200
        
        portfolio_data = portfolios_response.json()
        returned_zip_ids = [z["zip_id"] for z in portfolio_data["zips"]]
        
        assert set(returned_zip_ids) == set(zip_ids), (
            "GET /zip/portfolios should return all ZIPs linked to the portfolio"
        )


class TestGetPortfolios:
    """Tests for GET /zip/portfolios/{portfolio_id} endpoint."""

    def test_get_portfolios_returns_all_zips_for_portfolio(
        self, client, tmp_path, monkeypatch
    ):
        """Given a portfolio_id, return all ZIPs linked to it."""
        _redirect_uploads(monkeypatch, tmp_path)

        # Upload first ZIP and get portfolio_id
        files = {"file": ("docs.zip", b"docs-bytes", "application/zip")}
        first_response = client.post("/zip/upload", files=files)
        portfolio_id = first_response.json()["portfolio_id"]
        first_zip_id = first_response.json()["zip_id"]

        # Upload second ZIP to same portfolio
        files = {"file": ("code.zip", b"code-bytes", "application/zip")}
        second_response = client.post(
            f"/zip/upload?portfolio_id={portfolio_id}", files=files
        )
        second_zip_id = second_response.json()["zip_id"]

        # Get all ZIPs for this portfolio
        response = client.get(f"/zip/portfolios/{portfolio_id}")

        assert response.status_code == 200
        payload = response.json()

        assert payload["portfolio_id"] == portfolio_id
        assert len(payload["zips"]) == 2

        # Verify both ZIPs are returned with correct metadata
        zip_ids_returned = {z["zip_id"] for z in payload["zips"]}
        assert zip_ids_returned == {first_zip_id, second_zip_id}

        # Verify filenames are included
        filenames = {z["filename"] for z in payload["zips"]}
        assert filenames == {"docs.zip", "code.zip"}


class TestBackwardsCompatibility:
    """Tests to ensure existing functionality is not broken."""

    def test_single_zip_upload_flow_unchanged(self, client, tmp_path, monkeypatch):
        """The original single ZIP upload workflow should continue to work."""
        _redirect_uploads(monkeypatch, tmp_path)

        # Original upload flow (no portfolio_id param)
        files = {"file": ("artifact.zip", b"fake-bytes", "application/zip")}
        response = client.post("/zip/upload", files=files)

        # Should still work exactly as before
        assert response.status_code == 200
        payload = response.json()

        # Original fields should still be present
        assert "zip_id" in payload
        assert payload["zip_id"] > 0
        assert payload["filename"] == "artifact.zip"

        # File should be saved
        uploads_root = tmp_path / "uploads"
        saved_files = list(uploads_root.glob("*artifact.zip"))
        assert saved_files, "Uploaded file should be written to uploads dir"

        # GET directories should still work
        directories = client.get(f"/zip/{payload['zip_id']}/directories")
        assert directories.status_code == 200
        dir_payload = directories.json()
        assert dir_payload["zip_id"] == payload["zip_id"]
