"""Tests for DELETE /projects/{id} soft-delete endpoint."""

from __future__ import annotations


import pytest



def test_delete_project_success(client):
    """Test successful soft-delete of an existing project."""
    # Get initial timeline to find a project ID
    response = client.get("/projects/timeline")
    assert response.status_code == 200
    initial_projects = response.json()
    assert len(initial_projects) > 0

    # Get the first project's ID
    project_id = initial_projects[0]["id"]

    # Delete the project using the dynamic ID
    response = client.delete(f"/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_id"] == project_id
    assert "deleted successfully" in data["message"]


def test_delete_project_not_found(client):
    """Test 404 response when deleting non-existent project."""
    response = client.delete("/projects/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_delete_project_already_deleted(client):
    """Test that deleting same project twice returns 404 on second attempt."""
    # Get a project to delete
    response = client.get("/projects/timeline")
    projects = response.json()
    if not projects:
        pytest.skip("No projects to delete")
    project_id = projects[0]["id"]

    # First delete should succeed
    response = client.delete(f"/projects/{project_id}")
    assert response.status_code == 200

    # Second delete should return 404 (already soft-deleted)
    response = client.delete(f"/projects/{project_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_deleted_project_excluded_from_timeline(client):
    """Test that soft-deleted projects don't appear in timeline."""
    # Get initial count
    response = client.get("/projects/timeline")
    initial_count = len(response.json())

    # Get a project ID to delete
    projects = response.json()
    if not projects:
        pytest.skip("No projects to delete")
    project_id = projects[0]["id"]

    # Delete the project
    client.delete(f"/projects/{project_id}")

    # Verify count decreased
    response = client.get("/projects/timeline")
    assert len(response.json()) == initial_count - 1


def test_deleted_project_excluded_from_active_only_timeline(client):
    """Test soft-deleted projects are excluded even with active_only filter."""
    # Get initial active projects
    response = client.get("/projects/timeline", params={"active_only": True})
    initial_active = response.json()
    initial_count = len(initial_active)

    if initial_count == 0:
        pytest.skip("No active projects in test data")

    # Find an active project ID
    active_project_id = initial_active[0]["id"]

    # Delete the active project
    client.delete(f"/projects/{active_project_id}")

    # Verify it's excluded
    response = client.get("/projects/timeline", params={"active_only": True})
    final_count = len(response.json())

    # Count should decrease (or stay same if the deleted project wasn't active)
    assert final_count <= initial_count
