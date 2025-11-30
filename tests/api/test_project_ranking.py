import unittest.mock


def test_project_ranking_returns_ranked_list(client, tmp_path):
    """Test that the endpoint returns ranked projects."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()

    mock_output = """   10\tUser One <user@example.com>
   5\tUser Two <other@example.com>"""

    with unittest.mock.patch("subprocess.check_output", return_value=mock_output):
        response = client.get(
            "/projects/ranking",
            params={"projects_dir": str(tmp_path), "user_email": "user@example.com"},
        )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "test-project"
    assert data[0]["score"] == 66.67
    assert data[0]["total_commits"] == 15
    assert data[0]["user_commits"] == 10


def test_project_ranking_empty_directory(client, tmp_path):
    """Test that an empty directory returns an empty list."""
    response = client.get(
        "/projects/ranking",
        params={"projects_dir": str(tmp_path), "user_email": "user@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_project_ranking_invalid_path(client):
    """Test that an invalid path returns an empty list."""
    response = client.get(
        "/projects/ranking",
        params={"projects_dir": "/nonexistent/path", "user_email": "user@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_project_ranking_multiple_projects(client, tmp_path):
    """Test ranking with multiple projects sorted by score."""
    project1 = tmp_path / "project-high"
    project1.mkdir()
    (project1 / ".git").mkdir()

    project2 = tmp_path / "project-low"
    project2.mkdir()
    (project2 / ".git").mkdir()

    def mock_shortlog(cmd, cwd, **kwargs):
        if "project-high" in cwd:
            return "   20\tUser <user@example.com>"
        else:
            return """   5\tUser <user@example.com>
   15\tOther <other@example.com>"""

    with unittest.mock.patch("subprocess.check_output", side_effect=mock_shortlog):
        response = client.get(
            "/projects/ranking",
            params={"projects_dir": str(tmp_path), "user_email": "user@example.com"},
        )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["score"] >= data[1]["score"]
