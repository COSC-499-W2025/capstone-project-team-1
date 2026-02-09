"""Tests for project evidence CRUD endpoints.

Endpoints under test:
  POST   /projects/{id}/evidence              – add evidence
  GET    /projects/{id}/evidence              – list evidence
  DELETE /projects/{id}/evidence/{evidence_id} – remove evidence
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_project_id(client) -> int:
    """Return the ID of the first seeded project."""
    response = client.get("/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) > 0
    return projects[0]["id"]


def _post_evidence(client, project_id: int, **overrides) -> dict:
    """POST a valid evidence payload and return the response object."""
    payload = {
        "type": "metric",
        "content": "Reduced API response time by 40%",
        "source": "Internal benchmarks",
        "date": "2025-06-15",
    }
    payload.update(overrides)
    return client.post(f"/projects/{project_id}/evidence", json=payload)


# =========================================================================
# POST /projects/{id}/evidence
# =========================================================================


class TestCreateEvidence:
    """Tests for the evidence creation endpoint."""

    def test_create_returns_201_with_all_fields(self, client):
        """Happy-path: POST returns 201 with correct shape and values."""
        pid = _get_project_id(client)
        resp = _post_evidence(client, pid, type="metric", content="10k+ downloads")

        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "metric"
        assert data["content"] == "10k+ downloads"
        assert data["project_id"] == pid
        assert "id" in data
        assert "source" in data
        assert "date" in data

    def test_invalid_type_returns_422(self, client):
        """POST returns 422 for an unrecognised evidence type."""
        pid = _get_project_id(client)
        resp = _post_evidence(client, pid, type="invalid_type")
        assert resp.status_code == 422

    def test_nonexistent_project_returns_404(self, client):
        """POST returns 404 for a project that does not exist."""
        resp = _post_evidence(client, 99999)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_soft_deleted_project_returns_404(self, client):
        """POST returns 404 for a soft-deleted project."""
        pid = _get_project_id(client)
        client.delete(f"/projects/{pid}")
        resp = _post_evidence(client, pid)
        assert resp.status_code == 404


# =========================================================================
# GET /projects/{id}/evidence
# =========================================================================


class TestListEvidence:
    """Tests for the evidence listing endpoint."""

    def test_returns_created_items(self, client):
        """GET returns evidence previously added via POST."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, content="Metric A")
        _post_evidence(client, pid, type="feedback", content="Feedback B")

        resp = client.get(f"/projects/{pid}/evidence")
        assert resp.status_code == 200
        contents = {item["content"] for item in resp.json()}
        assert contents == {"Metric A", "Feedback B"}

    def test_scoped_to_project(self, client):
        """Evidence from project A does not appear in project B's list."""
        projects = client.get("/projects").json()
        assert len(projects) >= 2
        pid_a, pid_b = projects[0]["id"], projects[1]["id"]

        _post_evidence(client, pid_a, content="Only for A")
        _post_evidence(client, pid_b, content="Only for B")

        assert client.get(f"/projects/{pid_a}/evidence").json()[0]["content"] == "Only for A"
        assert client.get(f"/projects/{pid_b}/evidence").json()[0]["content"] == "Only for B"

    def test_filter_by_type(self, client):
        """GET with ?type= filters evidence by type."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, type="metric", content="Metric item")
        _post_evidence(client, pid, type="feedback", content="Feedback item")

        data = client.get(f"/projects/{pid}/evidence", params={"type": "metric"}).json()
        assert len(data) == 1
        assert data[0]["type"] == "metric"


# =========================================================================
# DELETE /projects/{id}/evidence/{evidence_id}
# =========================================================================


class TestDeleteEvidence:
    """Tests for the evidence deletion endpoint."""

    def test_delete_returns_200(self, client):
        """DELETE returns 200 and confirms deletion."""
        pid = _get_project_id(client)
        eid = _post_evidence(client, pid).json()["id"]

        resp = client.delete(f"/projects/{pid}/evidence/{eid}")
        assert resp.status_code == 200
        assert resp.json() == {"success": True, "deleted_id": eid}

    def test_wrong_project_returns_404(self, client):
        """DELETE returns 404 when evidence belongs to a different project."""
        projects = client.get("/projects").json()
        assert len(projects) >= 2
        pid_a, pid_b = projects[0]["id"], projects[1]["id"]

        eid = _post_evidence(client, pid_a).json()["id"]
        assert client.delete(f"/projects/{pid_b}/evidence/{eid}").status_code == 404

    def test_delete_preserves_siblings(self, client):
        """Deleting one evidence item does not affect others."""
        pid = _get_project_id(client)
        keep_id = _post_evidence(client, pid, content="Keep me").json()["id"]
        del_id = _post_evidence(client, pid, content="Delete me").json()["id"]

        client.delete(f"/projects/{pid}/evidence/{del_id}")

        listing = client.get(f"/projects/{pid}/evidence").json()
        assert len(listing) == 1
        assert listing[0]["id"] == keep_id


# =========================================================================
# Integration – Evidence in project detail
# =========================================================================


class TestEvidenceIntegration:
    """Tests verifying evidence appears in project detail."""

    def test_evidence_in_project_detail(self, client):
        """GET /projects/{id} includes evidence in the response."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, type="metric", content="99.9% uptime")
        _post_evidence(client, pid, type="award", content="Best Project 2025")

        data = client.get(f"/projects/{pid}").json()
        assert isinstance(data["evidence"], list)
        assert len(data["evidence"]) == 2

    def test_empty_evidence_field_present(self, client):
        """Project detail includes empty evidence list when none exist."""
        pid = _get_project_id(client)
        assert client.get(f"/projects/{pid}").json()["evidence"] == []
