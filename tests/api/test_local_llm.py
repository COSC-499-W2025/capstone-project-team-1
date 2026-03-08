"""Tests for local LLM API endpoints."""

from zipfile import ZipFile

from artifactminer.api import local_llm


def test_local_llm_router_is_registered(client):
    """Verify the local-llm router is mounted with /local-llm/context."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/local-llm/context" in paths
    assert "post" in paths["/local-llm/context"]


def test_context_endpoint_exists(client):
    """Verify POST /local-llm/context endpoint is registered."""
    # Send invalid request to check endpoint exists (should get 422, not 404)
    response = client.post("/local-llm/context", json={})
    # 422 means endpoint exists but validation failed
    # 404 would mean endpoint doesn't exist
    assert response.status_code == 422


def test_create_intake_with_valid_zip(client, tmp_path):
    """Test successful intake creation with a valid ZIP containing a git repo."""
    # Create a test ZIP with a mock git repository
    zip_path = tmp_path / "test_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Add .git directory structure
        zf.writestr("test-repo/.git/config", "[core]\n\trepositoryformatversion = 0")
        zf.writestr("test-repo/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("test-repo/README.md", "# Test Repository")
        zf.writestr("test-repo/src/main.py", "print('hello')")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "intake_id" in data
    assert "zip_path" in data
    assert "repos" in data
    
    # Verify intake_id matches ZIP filename stem
    assert data["intake_id"] == "test_repo"
    assert data["zip_path"] == str(zip_path)
    
    # Verify discovered repositories
    assert len(data["repos"]) == 1
    repo = data["repos"][0]
    assert repo["id"] == "test-repo"
    assert repo["name"] == "test-repo"
    assert repo["rel_path"] == "test-repo"


def test_create_intake_with_multiple_repos(client, tmp_path):
    """Test intake creation with ZIP containing multiple repositories."""
    zip_path = tmp_path / "multi_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Add first repo
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/README.md", "# Repo One")
        
        # Add second repo
        zf.writestr("repo-two/.git/config", "[core]")
        zf.writestr("repo-two/main.py", "# Repo Two")
        
        # Add nested repo
        zf.writestr("projects/nested-repo/.git/config", "[core]")
        zf.writestr("projects/nested-repo/index.js", "// Nested")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should discover all three repos
    assert len(data["repos"]) == 3
    
    # Verify repos are sorted by name
    repo_names = [r["name"] for r in data["repos"]]
    assert repo_names == sorted(repo_names)
    
    # Verify nested repo structure
    nested = next(r for r in data["repos"] if "nested" in r["name"])
    assert nested["rel_path"] == "projects/nested-repo"


def test_create_intake_with_empty_zip(client, tmp_path):
    """Test intake creation with ZIP containing no repositories."""
    zip_path = tmp_path / "empty.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Add files but no .git directories
        zf.writestr("README.md", "# No Repos")
        zf.writestr("src/main.py", "print('test')")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return empty repos list
    assert len(data["repos"]) == 0


def test_create_intake_missing_zip_path(client):
    """Test validation failure when zip_path is missing."""
    response = client.post("/local-llm/context", json={})
    
    assert response.status_code == 422
    detail = response.json()["detail"]
    # Pydantic validation error for missing required field
    assert any("zip_path" in str(err).lower() for err in detail)


def test_create_intake_empty_zip_path(client):
    """Test validation failure when zip_path is empty string."""
    response = client.post(
        "/local-llm/context",
        json={"zip_path": ""}
    )
    
    assert response.status_code == 422


def test_create_intake_nonexistent_file(client):
    """Test 404 error when ZIP file doesn't exist."""
    response = client.post(
        "/local-llm/context",
        json={"zip_path": "/nonexistent/path/file.zip"}
    )
    
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "not found" in detail.lower()


def test_create_intake_invalid_zip(client, tmp_path):
    """Test 400 error when file is not a valid ZIP."""
    # Create a non-ZIP file
    invalid_file = tmp_path / "not_a_zip.txt"
    invalid_file.write_text("This is not a ZIP file")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(invalid_file)}
    )
    
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "invalid" in detail.lower()


def test_create_intake_corrupted_zip(client, tmp_path):
    """Test 400 error when ZIP file is corrupted."""
    # Create a corrupted ZIP
    corrupted_zip = tmp_path / "corrupted.zip"
    corrupted_zip.write_bytes(b"PK\x03\x04" + b"corrupted data")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(corrupted_zip)}
    )
    
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "invalid" in detail.lower() or "failed" in detail.lower()


def test_create_intake_internal_error_maps_to_500(client, monkeypatch):
    """Test 500 mapping when the route encounters an unexpected error."""

    def _raise_runtime_error(_zip_path: str):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(local_llm, "_discover_repos_in_zip", _raise_runtime_error)

    response = client.post(
        "/local-llm/context",
        json={"zip_path": "any.zip"},
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "failed to create intake" in detail.lower()


def test_create_intake_response_contract(client, tmp_path):
    """Test that response matches IntakeCreateResponse schema."""
    zip_path = tmp_path / "contract_test.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "intake_id" in data
    assert "zip_path" in data
    assert "repos" in data
    
    # Verify types
    assert isinstance(data["intake_id"], str)
    assert isinstance(data["zip_path"], str)
    assert isinstance(data["repos"], list)
    
    # Verify repo structure if repos exist
    if data["repos"]:
        repo = data["repos"][0]
        assert "id" in repo
        assert "name" in repo
        assert "rel_path" in repo
        assert isinstance(repo["id"], str)
        assert isinstance(repo["name"], str)
        assert isinstance(repo["rel_path"], str)


def test_create_intake_idempotency(client, tmp_path):
    """Test that calling create_intake twice with same ZIP returns consistent results."""
    zip_path = tmp_path / "idempotent.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
    
    response1 = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    response2 = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Results should be identical
    assert response1.json() == response2.json()


def test_repository_candidate_fields(client, tmp_path):
    """Test that RepositoryCandidate fields are correctly populated."""
    zip_path = tmp_path / "fields_test.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Create repo with descriptive path
        zf.writestr("workspace/my-awesome-project/.git/config", "[core]")
        zf.writestr("workspace/my-awesome-project/README.md", "# Project")
    
    response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    
    assert response.status_code == 200
    repos = response.json()["repos"]
    
    assert len(repos) == 1
    repo = repos[0]
    
    # Verify id is the full relative path
    assert repo["id"] == "workspace/my-awesome-project"
    
    # Verify name is the last path component
    assert repo["name"] == "my-awesome-project"
    
    # Verify rel_path matches the path within ZIP
    assert repo["rel_path"] == "workspace/my-awesome-project"


def test_consent_routes_unchanged(client):
    """Verify that existing consent routes remain functional after adding local-llm router."""
    # Test that consent endpoint still works
    response = client.get("/consent")
    assert response.status_code == 200
    
    # Test that consent can still be updated
    response = client.put("/consent", json={"consent_level": "local-llm"})
    assert response.status_code == 200
    assert response.json()["consent_level"] == "local-llm"
