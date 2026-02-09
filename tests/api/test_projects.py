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


# Tests for GET /projects/{id}


def test_get_project_by_id_success(client):
    """GET /projects/{id} returns 200 and project details."""
    # Get a valid project ID
    response = client.get("/projects")
    projects = response.json()
    project_id = projects[0]["id"]

    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == project_id
    assert "project_name" in data
    assert "project_path" in data


def test_get_project_by_id_response_fields(client):
    """Response includes all required fields including relationships."""
    response = client.get("/projects")
    project_id = response.json()[0]["id"]

    response = client.get(f"/projects/{project_id}")
    data = response.json()

    # Core fields
    assert "id" in data
    assert "project_name" in data
    assert "project_path" in data
    assert "languages" in data
    assert "frameworks" in data
    assert "first_commit" in data
    assert "last_commit" in data
    assert "is_collaborative" in data
    assert "total_commits" in data
    assert "primary_language" in data
    assert "ranking_score" in data
    assert "health_score" in data
    assert "role" in data

    # Relationship fields
    assert "skills" in data
    assert isinstance(data["skills"], list)
    assert "resume_items" in data
    assert isinstance(data["resume_items"], list)


def test_get_project_by_id_not_found(client):
    """GET /projects/{id} returns 404 for nonexistent project."""
    response = client.get("/projects/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_get_project_by_id_soft_deleted(client):
    """GET /projects/{id} returns 404 for soft-deleted project."""
    # Get a project and delete it
    response = client.get("/projects")
    project_id = response.json()[0]["id"]
    client.delete(f"/projects/{project_id}")

    # Try to get the deleted project
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_project_role_upsert_and_get_project(client):
    """POST/PUT /projects/{id}/role sets and updates role shown in project detail."""
    project_id = client.get("/projects").json()[0]["id"]

    create_resp = client.post(
        f"/projects/{project_id}/role",
        json={"role": "Backend Engineer"},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["role"] == "Backend Engineer"

    detail_resp = client.get(f"/projects/{project_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["role"] == "Backend Engineer"

    update_resp = client.put(
        f"/projects/{project_id}/role",
        json={"role": "Lead Developer"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["role"] == "Lead Developer"

    detail_resp_after = client.get(f"/projects/{project_id}")
    assert detail_resp_after.status_code == 200
    assert detail_resp_after.json()["role"] == "Lead Developer"


def test_project_role_upsert_rejects_blank_value(client):
    """Role must not be empty/whitespace."""
    project_id = client.get("/projects").json()[0]["id"]

    response = client.post(
        f"/projects/{project_id}/role",
        json={"role": "   "},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Role must not be empty"


def test_project_role_upsert_not_found(client):
    """Role upsert returns 404 for unknown project id."""
    response = client.post(
        "/projects/99999/role",
        json={"role": "Contributor"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
