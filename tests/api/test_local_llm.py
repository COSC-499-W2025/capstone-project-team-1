"""Tests for local LLM API endpoints."""

import uuid
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
    
    # Verify intake_id is a valid UUID
    parsed_intake_id = uuid.UUID(data["intake_id"])
    assert str(parsed_intake_id) == data["intake_id"]
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
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-one/README.md", "# Repo One")
        
        # Add second repo
        zf.writestr("repo-two/.git/config", "[core]")
        zf.writestr("repo-two/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-two/main.py", "# Repo Two")
        
        # Add nested repo
        zf.writestr("projects/nested-repo/.git/config", "[core]")
        zf.writestr("projects/nested-repo/.git/HEAD", "ref: refs/heads/main")
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
    
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "no git repositories" in detail.lower()


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
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")
    
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
    """Test that repeated intake calls return same repos but unique intake IDs."""
    zip_path = tmp_path / "idempotent.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")
    
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

    data1 = response1.json()
    data2 = response2.json()

    # Validate both IDs are UUIDs and unique per request.
    assert str(uuid.UUID(data1["intake_id"])) == data1["intake_id"]
    assert str(uuid.UUID(data2["intake_id"])) == data2["intake_id"]
    assert data1["intake_id"] != data2["intake_id"]

    # ZIP path and discovered repositories should remain stable.
    assert data1["zip_path"] == data2["zip_path"]
    assert data1["repos"] == data2["repos"]


def test_repository_candidate_fields(client, tmp_path):
    """Test that RepositoryCandidate fields are correctly populated."""
    zip_path = tmp_path / "fields_test.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Create repo with descriptive path
        zf.writestr("workspace/my-awesome-project/.git/config", "[core]")
        zf.writestr("workspace/my-awesome-project/.git/HEAD", "ref: refs/heads/main")
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


# ============================================================================
# Contributor Discovery Tests
# ============================================================================


def test_contributors_endpoint_exists(client):
    """Verify POST /local-llm/context/contributors endpoint is registered."""
    # Send invalid request to check endpoint exists
    response = client.post("/local-llm/context/contributors", json={})
    # 422 means endpoint exists but validation failed; 404 means missing active context
    # Either is valid here (depends on whether we have an active context)
    assert response.status_code in [404, 422]


def test_discover_contributors_valid_selection(client, tmp_path):
    """Test successful contributor discovery with valid repo selection."""
    # Create a test ZIP with a git repo containing commits
    zip_path = tmp_path / "test_repo_with_commits.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Create git repo structure
        zf.writestr("test-repo/.git/config", "[core]\n\trepositoryformatversion = 0")
        zf.writestr("test-repo/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("test-repo/.git/objects/HEAD", "")
        zf.writestr("test-repo/.git/refs/heads/main", "")
        zf.writestr("test-repo/README.md", "# Test Repository")
    
    # Create intake first
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()
    assert len(intake_data["repos"]) > 0
    
    repo_id = intake_data["repos"][0]["id"]
    
    # Discover contributors for selected repo
    contrib_response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": [repo_id]}
    )
    
    assert contrib_response.status_code == 200
    contrib_data = contrib_response.json()
    
    # Verify response structure
    assert "contributors" in contrib_data
    assert isinstance(contrib_data["contributors"], list)


def test_discover_contributors_missing_active_context(client):
    """Test 404 error when requesting contributors with no active intake."""
    # Clear any active intakes
    local_llm._active_intakes.clear()
    
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": ["repo-1"]}
    )
    
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "active intake" in detail.lower()


def test_discover_contributors_invalid_repo_ids(client, tmp_path):
    """Test 422 error with invalid repository IDs."""
    # Create intake with valid repos
    zip_path = tmp_path / "test_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-two/.git/config", "[core]")
        zf.writestr("repo-two/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    
    # Try to select a repo that doesn't exist
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": ["nonexistent-repo"]}
    )
    
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "invalid" in detail.lower() and "repository" in detail.lower()


def test_discover_contributors_mixed_valid_invalid(client, tmp_path):
    """Test 422 error when mixing valid and invalid repo IDs."""
    # Create intake with repos
    zip_path = tmp_path / "test_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-two/.git/config", "[core]")
        zf.writestr("repo-two/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()
    valid_repo_id = intake_data["repos"][0]["id"]
    
    # Mix valid and invalid IDs
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": [valid_repo_id, "fake-repo"]}
    )
    
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "invalid" in detail.lower()


def test_discover_contributors_missing_repo_ids(client, tmp_path):
    """Test validation failure when repo_ids is missing."""
    # Create intake
    zip_path = tmp_path / "test_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    
    # Request without repo_ids
    response = client.post(
        "/local-llm/context/contributors",
        json={}
    )
    
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("repo_ids" in str(err).lower() for err in detail)


def test_discover_contributors_empty_repo_ids(client, tmp_path):
    """Test validation failure when repo_ids is empty list."""
    # Create intake
    zip_path = tmp_path / "test_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    
    # Request with empty list
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": []}
    )
    
    assert response.status_code == 422
    detail = response.json()["detail"]
    # Pydantic validation error for min_length constraint
    assert any("min_length" in str(err).lower() or "ensure this value has at least" in str(err).lower() 
               for err in detail)


def test_discover_contributors_response_contract(client, tmp_path):
    """Test that contributor response matches ContributorDiscoveryResponse schema."""
    # Create intake with repo
    zip_path = tmp_path / "contract_test.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    repo_id = intake_response.json()["repos"][0]["id"]
    
    # Discover contributors
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": [repo_id]}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify top-level structure
    assert "contributors" in data
    assert isinstance(data["contributors"], list)
    
    # Verify contributor structure if contributors exist
    if data["contributors"]:
        contrib = data["contributors"][0]
        assert "email" in contrib
        assert "name" in contrib or contrib["name"] is None
        assert "repo_count" in contrib
        assert "commit_count" in contrib
        assert "candidate_username" in contrib
        
        # Verify types
        assert isinstance(contrib["email"], str)
        assert contrib["name"] is None or isinstance(contrib["name"], str)
        assert isinstance(contrib["repo_count"], int)
        assert isinstance(contrib["commit_count"], int)
        assert isinstance(contrib["candidate_username"], str)


def test_discover_contributors_multiple_repos(client, tmp_path):
    """Test discovering contributors across multiple selected repositories."""
    # Create intake with multiple repos
    zip_path = tmp_path / "multi_repo.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        # Add multiple repos
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-two/.git/config", "[core]")
        zf.writestr("repo-two/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()
    repo_ids = [repo["id"] for repo in intake_data["repos"]]
    
    # Select multiple repos
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": repo_ids}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "contributors" in data
    assert isinstance(data["contributors"], list)


def test_discover_contributors_subset_selection(client, tmp_path):
    """Test selecting a subset of available repositories."""
    # Create intake with multiple repos
    zip_path = tmp_path / "subset_test.zip"
    
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-two/.git/config", "[core]")
        zf.writestr("repo-two/.git/HEAD", "ref: refs/heads/main")
        zf.writestr("repo-three/.git/config", "[core]")
        zf.writestr("repo-three/.git/HEAD", "ref: refs/heads/main")
    
    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()
    
    # Select only first two repos
    subset_ids = [repo["id"] for repo in intake_data["repos"][:2]]
    
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": subset_ids}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "contributors" in data


def test_contributors_endpoint_in_openapi(client):
    """Verify POST /local-llm/context/contributors is in OpenAPI schema."""
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    paths = response.json()["paths"]
    
    # Check that the endpoint is registered
    assert "/local-llm/context/contributors" in paths
    assert "post" in paths["/local-llm/context/contributors"]


# ============================================================================
# Generation Start Tests
# ============================================================================


def test_generation_start_endpoint_exists(client):
    """Verify POST /local-llm/generation/start endpoint is registered."""
    response = client.post("/local-llm/generation/start", json={})
    assert response.status_code == 422


def test_generation_start_valid_request(client, tmp_path):
    """Test successful generation start with valid intake, repo selection, and identity."""
    zip_path = tmp_path / "generation_start.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()

    response = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake_data["intake_id"],
            "repo_ids": [intake_data["repos"][0]["id"]],
            "user_email": "developer@example.com",
            "stage1_model": "qwen2.5-coder-3b-q4",
            "stage2_model": "lfm2.5-1.2b-q4",
            "stage3_model": "lfm2.5-1.2b-q4",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "job_id" in data
    assert "status" in data
    parsed_job_id = uuid.UUID(data["job_id"])
    assert str(parsed_job_id) == data["job_id"]
    assert data["status"] == "queued"

    # Verify job envelope persisted for subsequent workflow routes.
    assert data["job_id"] in local_llm._generation_jobs


def test_generation_start_invalid_email(client, tmp_path):
    """Test 422 response when user_email is invalid."""
    zip_path = tmp_path / "invalid_email.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    repo_id = intake_response.json()["repos"][0]["id"]

    response = client.post(
        "/local-llm/generation/start",
        json={
            "repo_ids": [repo_id],
            "user_email": "not-an-email",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("user_email" in str(err).lower() for err in detail)


def test_generation_start_missing_identity_input(client, tmp_path):
    """Test 422 response when user identity input is missing."""
    zip_path = tmp_path / "missing_identity.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    repo_id = intake_response.json()["repos"][0]["id"]

    response = client.post(
        "/local-llm/generation/start",
        json={
            "repo_ids": [repo_id],
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("user_email" in str(err).lower() for err in detail)


def test_generation_start_empty_model_selection_rejected(client, tmp_path):
    """Test 422 response when a model-selection field is provided as empty."""
    zip_path = tmp_path / "empty_model.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    repo_id = intake_response.json()["repos"][0]["id"]

    response = client.post(
        "/local-llm/generation/start",
        json={
            "repo_ids": [repo_id],
            "user_email": "developer@example.com",
            "stage1_model": "",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("stage1_model" in str(err).lower() for err in detail)


def test_generation_start_missing_active_context(client):
    """Test 404 response when no active intake context exists."""
    local_llm._active_intakes.clear()

    response = client.post(
        "/local-llm/generation/start",
        json={
            "repo_ids": ["repo-one"],
            "user_email": "developer@example.com",
        },
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "active intake" in detail.lower()


def test_generation_start_invalid_intake_reference(client, tmp_path):
    """Test 404 response when intake_id does not reference an active context."""
    zip_path = tmp_path / "valid_context.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    repo_id = intake_response.json()["repos"][0]["id"]

    response = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": "missing-intake-id",
            "repo_ids": [repo_id],
            "user_email": "developer@example.com",
        },
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "active intake" in detail.lower()


def test_generation_start_invalid_repo_selection(client, tmp_path):
    """Test 422 response when selected repo IDs are not in intake context."""
    zip_path = tmp_path / "invalid_repo_selection.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo-one/.git/config", "[core]")
        zf.writestr("repo-one/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_id = intake_response.json()["intake_id"]

    response = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake_id,
            "repo_ids": ["nonexistent-repo"],
            "user_email": "developer@example.com",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "invalid" in detail.lower() and "repository" in detail.lower()


def test_generation_start_endpoint_in_openapi(client):
    """Verify POST /local-llm/generation/start appears in OpenAPI schema."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/local-llm/generation/start" in paths
    assert "post" in paths["/local-llm/generation/start"]


# ============================================================================
# Generation Cancel Tests
# ============================================================================


def test_generation_cancel_valid_request(client, tmp_path):
    """Test successful cancellation of an active generation job."""
    zip_path = tmp_path / "generation_cancel.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()

    start_response = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake_data["intake_id"],
            "repo_ids": [intake_data["repos"][0]["id"]],
            "user_email": "developer@example.com",
        },
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]
    assert local_llm._active_generation_id == job_id

    response = client.post("/local-llm/generation/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data == {"ok": True, "status": "cancelled"}
    assert local_llm._generation_jobs[job_id]["status"] == "cancelled"
    assert local_llm._active_generation_id is None


def test_generation_cancel_no_active_job(client):
    """Test cancel behavior when no active generation job exists."""
    local_llm._active_generation_id = None

    response = client.post("/local-llm/generation/cancel")

    assert response.status_code == 200
    assert response.json() == {"ok": False, "status": "cancelled"}


def test_generation_cancel_repeat_cancel_behavior(client, tmp_path):
    """Test repeat cancel call behavior after an initial successful cancellation."""
    zip_path = tmp_path / "repeat_cancel.zip"

    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    intake_response = client.post(
        "/local-llm/context",
        json={"zip_path": str(zip_path)}
    )
    assert intake_response.status_code == 200
    intake_data = intake_response.json()

    start_response = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake_data["intake_id"],
            "repo_ids": [intake_data["repos"][0]["id"]],
            "user_email": "developer@example.com",
        },
    )
    assert start_response.status_code == 200

    first_cancel = client.post("/local-llm/generation/cancel")
    second_cancel = client.post("/local-llm/generation/cancel")

    assert first_cancel.status_code == 200
    assert first_cancel.json() == {"ok": True, "status": "cancelled"}
    assert second_cancel.status_code == 200
    assert second_cancel.json() == {"ok": False, "status": "cancelled"}


def test_generation_cancel_endpoint_in_openapi(client):
    """Verify POST /local-llm/generation/cancel appears in OpenAPI schema."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/local-llm/generation/cancel" in paths
    assert "post" in paths["/local-llm/generation/cancel"]

