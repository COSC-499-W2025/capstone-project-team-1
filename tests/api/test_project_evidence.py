"""Tests for project evidence CRUD endpoints.

Endpoints under test:
  POST   /projects/{id}/evidence              – add evidence
  GET    /projects/{id}/evidence              – list evidence
  DELETE /projects/{id}/evidence/{evidence_id} – remove evidence

Evidence types (flexible enum): metric, feedback, evaluation, award, custom.

These tests are written TDD-style; they will fail until the feature is
implemented per issue #339.
"""

from __future__ import annotations

import pytest


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
# POST /projects/{id}/evidence – Create evidence
# =========================================================================


class TestCreateEvidence:
    """Tests for the evidence creation endpoint."""

    def test_create_evidence_metric(self, client):
        """POST returns 201 with the created evidence for type=metric."""
        pid = _get_project_id(client)
        resp = _post_evidence(client, pid, type="metric", content="10k+ downloads")

        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "metric"
        assert data["content"] == "10k+ downloads"
        assert "id" in data

    def test_create_evidence_feedback(self, client):
        """POST returns 201 for type=feedback."""
        pid = _get_project_id(client)
        resp = _post_evidence(
            client,
            pid,
            type="feedback",
            content="Excellent work on the API redesign",
            source="Manager review Q3",
        )

        assert resp.status_code == 201
        assert resp.json()["type"] == "feedback"

    def test_create_evidence_evaluation(self, client):
        """POST returns 201 for type=evaluation."""
        pid = _get_project_id(client)
        resp = _post_evidence(
            client,
            pid,
            type="evaluation",
            content="Grade: A+",
            source="CS 499 capstone course",
        )

        assert resp.status_code == 201
        assert resp.json()["type"] == "evaluation"

    def test_create_evidence_award(self, client):
        """POST returns 201 for type=award."""
        pid = _get_project_id(client)
        resp = _post_evidence(
            client, pid, type="award", content="Best Hack – HackathonX 2025"
        )

        assert resp.status_code == 201
        assert resp.json()["type"] == "award"

    def test_create_evidence_custom(self, client):
        """POST returns 201 for type=custom (catch-all)."""
        pid = _get_project_id(client)
        resp = _post_evidence(
            client, pid, type="custom", content="Published on Medium"
        )

        assert resp.status_code == 201
        assert resp.json()["type"] == "custom"

    def test_create_evidence_response_shape(self, client):
        """Response includes all expected fields."""
        pid = _get_project_id(client)
        resp = _post_evidence(
            client,
            pid,
            type="metric",
            content="Reduced load time by 40%",
            source="Lighthouse audit",
            date="2025-03-01",
        )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "type" in data
        assert "content" in data
        assert "source" in data
        assert "date" in data
        assert "project_id" in data
        assert data["project_id"] == pid

    def test_create_evidence_optional_source(self, client):
        """Source field is optional; evidence can be created without it."""
        pid = _get_project_id(client)
        payload = {"type": "metric", "content": "500 daily users"}
        resp = client.post(f"/projects/{pid}/evidence", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["source"] is None or "source" in data

    def test_create_evidence_optional_date(self, client):
        """Date field is optional; evidence can be created without it."""
        pid = _get_project_id(client)
        payload = {"type": "feedback", "content": "Great job!", "source": "Peer"}
        resp = client.post(f"/projects/{pid}/evidence", json=payload)

        assert resp.status_code == 201

    # --- Validation errors ---

    def test_create_evidence_missing_type(self, client):
        """POST returns 422 when 'type' is missing."""
        pid = _get_project_id(client)
        resp = client.post(
            f"/projects/{pid}/evidence",
            json={"content": "Some evidence"},
        )

        assert resp.status_code == 422

    def test_create_evidence_missing_content(self, client):
        """POST returns 422 when 'content' is missing."""
        pid = _get_project_id(client)
        resp = client.post(
            f"/projects/{pid}/evidence",
            json={"type": "metric"},
        )

        assert resp.status_code == 422

    def test_create_evidence_invalid_type(self, client):
        """POST returns 422 for an unrecognised evidence type."""
        pid = _get_project_id(client)
        resp = _post_evidence(client, pid, type="invalid_type")

        assert resp.status_code == 422

    def test_create_evidence_empty_content(self, client):
        """POST returns 422 when content is an empty string."""
        pid = _get_project_id(client)
        resp = _post_evidence(client, pid, content="")

        assert resp.status_code == 422

    def test_create_evidence_nonexistent_project(self, client):
        """POST returns 404 for a project that does not exist."""
        resp = _post_evidence(client, 99999)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_create_evidence_soft_deleted_project(self, client):
        """POST returns 404 when trying to add evidence to a soft-deleted project."""
        pid = _get_project_id(client)
        client.delete(f"/projects/{pid}")

        resp = _post_evidence(client, pid)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_create_evidence_invalid_date_format(self, client):
        """POST returns 422 for a malformed date string."""
        pid = _get_project_id(client)
        resp = _post_evidence(client, pid, date="not-a-date")

        assert resp.status_code == 422

    # --- Edge cases ---

    def test_create_multiple_evidence_same_project(self, client):
        """Multiple evidence items can be attached to the same project."""
        pid = _get_project_id(client)
        resp1 = _post_evidence(client, pid, content="Evidence 1")
        resp2 = _post_evidence(client, pid, content="Evidence 2")

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_create_evidence_long_content(self, client):
        """Evidence with a long content string is accepted."""
        pid = _get_project_id(client)
        long_content = "A" * 5000
        resp = _post_evidence(client, pid, content=long_content)

        assert resp.status_code == 201
        assert resp.json()["content"] == long_content

    def test_create_evidence_special_characters(self, client):
        """Content with special characters is preserved."""
        pid = _get_project_id(client)
        special = 'Feedback: "Excellent!" — 100% recommend <script>alert(1)</script>'
        resp = _post_evidence(client, pid, content=special)

        assert resp.status_code == 201
        assert resp.json()["content"] == special

    def test_create_evidence_unicode_content(self, client):
        """Evidence with unicode content is handled correctly."""
        pid = _get_project_id(client)
        unicode_content = "성능 향상 40% 📈 — отличная работа"
        resp = _post_evidence(client, pid, content=unicode_content)

        assert resp.status_code == 201
        assert resp.json()["content"] == unicode_content


# =========================================================================
# GET /projects/{id}/evidence – List evidence
# =========================================================================


class TestListEvidence:
    """Tests for the evidence listing endpoint."""

    def test_list_evidence_empty(self, client):
        """GET returns 200 with empty list when project has no evidence."""
        pid = _get_project_id(client)
        resp = client.get(f"/projects/{pid}/evidence")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_evidence_returns_created_items(self, client):
        """GET returns evidence previously added via POST."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, content="Metric A")
        _post_evidence(client, pid, type="feedback", content="Feedback B")

        resp = client.get(f"/projects/{pid}/evidence")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        contents = {item["content"] for item in data}
        assert "Metric A" in contents
        assert "Feedback B" in contents

    def test_list_evidence_response_fields(self, client):
        """Each item in the list has the expected fields."""
        pid = _get_project_id(client)
        _post_evidence(
            client,
            pid,
            type="evaluation",
            content="Score: 95/100",
            source="Peer review",
            date="2025-01-15",
        )

        resp = client.get(f"/projects/{pid}/evidence")

        assert resp.status_code == 200
        item = resp.json()[0]
        assert "id" in item
        assert "type" in item
        assert "content" in item
        assert "source" in item
        assert "date" in item
        assert "project_id" in item

    def test_list_evidence_scoped_to_project(self, client):
        """Evidence from project A does not appear in project B's list."""
        projects_resp = client.get("/projects")
        projects = projects_resp.json()
        assert len(projects) >= 2

        pid_a = projects[0]["id"]
        pid_b = projects[1]["id"]

        _post_evidence(client, pid_a, content="Only for project A")
        _post_evidence(client, pid_b, content="Only for project B")

        resp_a = client.get(f"/projects/{pid_a}/evidence")
        resp_b = client.get(f"/projects/{pid_b}/evidence")

        assert len(resp_a.json()) == 1
        assert resp_a.json()[0]["content"] == "Only for project A"

        assert len(resp_b.json()) == 1
        assert resp_b.json()[0]["content"] == "Only for project B"

    def test_list_evidence_nonexistent_project(self, client):
        """GET returns 404 for a nonexistent project."""
        resp = client.get("/projects/99999/evidence")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_list_evidence_soft_deleted_project(self, client):
        """GET returns 404 for a soft-deleted project."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, content="Exists before delete")
        client.delete(f"/projects/{pid}")

        resp = client.get(f"/projects/{pid}/evidence")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_list_evidence_filter_by_type(self, client):
        """GET with ?type= filters evidence by type."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, type="metric", content="Metric item")
        _post_evidence(client, pid, type="feedback", content="Feedback item")
        _post_evidence(client, pid, type="award", content="Award item")

        resp = client.get(f"/projects/{pid}/evidence", params={"type": "metric"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["type"] == "metric"

    def test_list_evidence_filter_by_type_no_match(self, client):
        """GET with ?type= returns empty list when no evidence matches."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, type="metric", content="Only metrics here")

        resp = client.get(f"/projects/{pid}/evidence", params={"type": "award"})

        assert resp.status_code == 200
        assert resp.json() == []


# =========================================================================
# DELETE /projects/{id}/evidence/{evidence_id} – Remove evidence
# =========================================================================


class TestDeleteEvidence:
    """Tests for the evidence deletion endpoint."""

    def test_delete_evidence_success(self, client):
        """DELETE returns 200 and confirms deletion."""
        pid = _get_project_id(client)
        create_resp = _post_evidence(client, pid, content="To be deleted")
        evidence_id = create_resp.json()["id"]

        resp = client.delete(f"/projects/{pid}/evidence/{evidence_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["deleted_id"] == evidence_id

    def test_delete_evidence_actually_removes(self, client):
        """Deleted evidence no longer appears in GET listing."""
        pid = _get_project_id(client)
        create_resp = _post_evidence(client, pid, content="Will vanish")
        evidence_id = create_resp.json()["id"]

        client.delete(f"/projects/{pid}/evidence/{evidence_id}")

        resp = client.get(f"/projects/{pid}/evidence")
        assert resp.status_code == 200
        ids_remaining = [item["id"] for item in resp.json()]
        assert evidence_id not in ids_remaining

    def test_delete_evidence_nonexistent_evidence_id(self, client):
        """DELETE returns 404 for evidence ID that does not exist."""
        pid = _get_project_id(client)
        resp = client.delete(f"/projects/{pid}/evidence/99999")

        assert resp.status_code == 404

    def test_delete_evidence_nonexistent_project(self, client):
        """DELETE returns 404 when the project does not exist."""
        resp = client.delete("/projects/99999/evidence/1")

        assert resp.status_code == 404

    def test_delete_evidence_wrong_project(self, client):
        """DELETE returns 404 when evidence belongs to a different project."""
        projects = client.get("/projects").json()
        assert len(projects) >= 2

        pid_a = projects[0]["id"]
        pid_b = projects[1]["id"]

        # Create evidence on project A
        create_resp = _post_evidence(client, pid_a, content="Belongs to A")
        evidence_id = create_resp.json()["id"]

        # Try to delete it via project B
        resp = client.delete(f"/projects/{pid_b}/evidence/{evidence_id}")

        assert resp.status_code == 404

    def test_delete_evidence_soft_deleted_project(self, client):
        """DELETE returns 404 when the parent project is soft-deleted."""
        pid = _get_project_id(client)
        create_resp = _post_evidence(client, pid, content="Orphaned soon")
        evidence_id = create_resp.json()["id"]

        client.delete(f"/projects/{pid}")

        resp = client.delete(f"/projects/{pid}/evidence/{evidence_id}")
        assert resp.status_code == 404

    def test_delete_evidence_idempotent(self, client):
        """Deleting the same evidence twice returns 404 on second attempt."""
        pid = _get_project_id(client)
        create_resp = _post_evidence(client, pid, content="Delete me twice")
        evidence_id = create_resp.json()["id"]

        first = client.delete(f"/projects/{pid}/evidence/{evidence_id}")
        assert first.status_code == 200

        second = client.delete(f"/projects/{pid}/evidence/{evidence_id}")
        assert second.status_code == 404

    def test_delete_one_evidence_preserves_others(self, client):
        """Deleting one evidence item does not affect siblings."""
        pid = _get_project_id(client)
        resp1 = _post_evidence(client, pid, content="Keep me")
        resp2 = _post_evidence(client, pid, content="Delete me")

        keep_id = resp1.json()["id"]
        delete_id = resp2.json()["id"]

        client.delete(f"/projects/{pid}/evidence/{delete_id}")

        listing = client.get(f"/projects/{pid}/evidence").json()
        assert len(listing) == 1
        assert listing[0]["id"] == keep_id
        assert listing[0]["content"] == "Keep me"


# =========================================================================
# Integration – Evidence in project detail / portfolio output
# =========================================================================


class TestEvidenceIntegration:
    """Tests verifying evidence appears in project detail and portfolio endpoints."""

    def test_evidence_included_in_project_detail(self, client):
        """GET /projects/{id} includes evidence in the response."""
        pid = _get_project_id(client)
        _post_evidence(client, pid, type="metric", content="99.9% uptime")
        _post_evidence(client, pid, type="award", content="Best Project 2025")

        resp = client.get(f"/projects/{pid}")

        assert resp.status_code == 200
        data = resp.json()
        assert "evidence" in data
        assert isinstance(data["evidence"], list)
        assert len(data["evidence"]) == 2

    def test_evidence_detail_response_shape(self, client):
        """Evidence items in project detail have the expected shape."""
        pid = _get_project_id(client)
        _post_evidence(
            client,
            pid,
            type="feedback",
            content="Outstanding contribution",
            source="CTO",
            date="2025-09-01",
        )

        resp = client.get(f"/projects/{pid}")
        evidence = resp.json()["evidence"]

        assert len(evidence) == 1
        item = evidence[0]
        assert item["type"] == "feedback"
        assert item["content"] == "Outstanding contribution"
        assert item["source"] == "CTO"

    def test_no_evidence_field_still_present(self, client):
        """Project detail includes empty evidence list when none exist."""
        pid = _get_project_id(client)
        resp = client.get(f"/projects/{pid}")

        assert resp.status_code == 200
        data = resp.json()
        assert "evidence" in data
        assert data["evidence"] == []

    def test_deleted_evidence_excluded_from_detail(self, client):
        """Deleted evidence does not appear in project detail."""
        pid = _get_project_id(client)
        create_resp = _post_evidence(client, pid, content="Temporary")
        evidence_id = create_resp.json()["id"]

        client.delete(f"/projects/{pid}/evidence/{evidence_id}")

        resp = client.get(f"/projects/{pid}")
        assert resp.json()["evidence"] == []

    def test_evidence_types_all_appear_in_detail(self, client):
        """All five evidence types appear correctly in project detail."""
        pid = _get_project_id(client)
        types = ["metric", "feedback", "evaluation", "award", "custom"]
        for t in types:
            _post_evidence(client, pid, type=t, content=f"Content for {t}")

        resp = client.get(f"/projects/{pid}")
        evidence = resp.json()["evidence"]

        returned_types = {item["type"] for item in evidence}
        assert returned_types == set(types)
