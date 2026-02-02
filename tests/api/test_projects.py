"""Tests for GET /projects endpoint."""

from __future__ import annotations


def test_get_projects_returns_list(client):
    """GET /projects returns 200 and a list of projects."""
    response = client.get("/projects")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4  # Seeded data has 4 projects


def test_get_projects_response_fields(client):
    """Response includes all required fields."""
    response = client.get("/projects")
    data = response.json()

    assert len(data) > 0
    project = data[0]

    # Required fields per issue #327
    assert "id" in project
    assert "project_name" in project
    assert "project_path" in project
    assert "languages" in project
    assert "frameworks" in project
    assert "first_commit" in project
    assert "last_commit" in project
    assert "is_collaborative" in project


def test_get_projects_pagination_limit(client):
    """Limit param restricts number of results."""
    response = client.get("/projects", params={"limit": 2})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_projects_pagination_offset(client):
    """Offset param skips results."""
    # Get all projects first
    all_response = client.get("/projects")
    all_projects = all_response.json()

    # Get with offset
    response = client.get("/projects", params={"offset": 1})
    data = response.json()

    assert response.status_code == 200
    assert len(data) == len(all_projects) - 1


def test_get_projects_pagination_limit_and_offset(client):
    """Limit and offset work together."""
    response = client.get("/projects", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_projects_excludes_soft_deleted(client):
    """Soft-deleted projects are not returned."""
    # Get initial count
    response = client.get("/projects")
    initial_count = len(response.json())

    # Get a project ID and delete it
    projects = response.json()
    project_id = projects[0]["id"]
    client.delete(f"/projects/{project_id}")

    # Verify count decreased
    response = client.get("/projects")
    assert len(response.json()) == initial_count - 1
