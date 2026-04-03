import json
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

import pytest

from artifactminer.api import local_llm


def make_fake_git_zip() -> str:
    """Create a temporary ZIP containing a minimal fake git repo structure.

    Returns the absolute path to the created zip file. Caller is responsible
    for removing the temp directory created around it.
    """
    temp_dir = tempfile.mkdtemp(prefix="test_local_llm_")
    root = Path(temp_dir)
    repo_dir = root / "proj"
    (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
    # Create a minimal HEAD file to satisfy discovery checks
    (repo_dir / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    zip_path = root / "projects.zip"
    with ZipFile(zip_path, "w") as zf:
        # Add the fake repo structure
        for path in [repo_dir / ".git" / "HEAD"]:
            zf.write(path, arcname=str(path.relative_to(root)))
    return str(zip_path)


def test_openapi_exposes_all_local_llm_routes(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "paths" in spec

    paths = spec["paths"]

    # Expected route family and methods
    expected = {
        "/local-llm/context": {"post"},
        "/local-llm/context/contributors": {"post"},
        "/local-llm/setup": {"get"},
        "/local-llm/generation/start": {"post"},
        "/local-llm/generation/cancel": {"post"},
        "/local-llm/generation/status": {"get"},
        "/local-llm/generation/polish": {"post"},
    }

    for path, methods in expected.items():
        assert path in paths, f"Missing path in OpenAPI: {path}"
        present_methods = {m.lower() for m in paths[path].keys()}
        for m in methods:
            assert (
                m in present_methods
            ), f"Missing method {m} for path {path} in OpenAPI"


def test_openai_route_removed_from_public_api_surface(client):
    """Verify that /openai route is no longer part of the public API surface.
    
    This test ensures the migration from cloud-based /openai endpoint to
    local /local-llm/* routes is complete. The /openai route should not be
    mounted or exposed in the OpenAPI specification.
    
    Acceptance criteria for task 446: Remove /openai from public API surface.
    """
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "paths" in spec

    paths = spec["paths"]

    # Verify /openai is NOT in the API surface
    assert "/openai" not in paths, (
        "POST /openai should be removed from public API surface. "
        "Migration to /local-llm/* routes should be complete."
    )

    # Verify /openai/* sub-paths are also not present
    for path in list(paths.keys()):
        if path.startswith("/openai"):
            raise AssertionError(
                f"Found {path} in API surface. All /openai/* routes should be removed."
            )


def test_intake_start_status_and_cancel_flow_returns_schema_shapes(client):
    # 1) Create intake from a fake git ZIP
    zip_path = make_fake_git_zip()
    try:
        resp = client.post("/local-llm/context", json={"zip_path": zip_path})
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"intake_id", "zip_path", "repos"}
        assert body["zip_path"].endswith("projects.zip")
        assert isinstance(body["repos"], list)

        # Grab the first repo id
        assert body["repos"], "Expected at least one discovered repo"
        repo_id = body["repos"][0]["id"]

        # 2) Contributor discovery should succeed and return list shape
        resp = client.post(
            "/local-llm/context/contributors", json={"repo_ids": [repo_id]}
        )
        assert resp.status_code == 200
        contribs = resp.json()
        assert set(contribs.keys()) == {"contributors"}
        assert isinstance(contribs["contributors"], list)

        # 3) Start generation
        start_req = {
            "intake_id": body["intake_id"],
            "repo_ids": [repo_id],
            "user_email": "user@example.com",
            "stage1_model": "qwen2.5-coder-3b-q4",
            "stage2_model": "lfm2.5-1.2b-q4",
            "stage3_model": "lfm2.5-1.2b-q4",
        }
        resp = client.post("/local-llm/generation/start", json=start_req)
        assert resp.status_code == 200
        start_body = resp.json()
        assert set(start_body.keys()) == {"job_id", "status"}
        assert start_body["status"] == "queued"
        job_id = start_body["job_id"]

        # 4) Status should return telemetry and fields as per schema
        resp = client.get(f"/local-llm/generation/status?job_id={job_id}")
        assert resp.status_code == 200
        status_body = resp.json()
        assert {
            "status",
            "stage",
            "messages",
            "telemetry",
            "draft",
            "output",
            "error",
        }.issubset(status_body.keys())
        assert isinstance(status_body["telemetry"], dict)
        assert "selected_repos" in status_body["telemetry"]

        # 5) Polish should 409 when pipeline not in draft_ready/complete
        resp = client.post(
            "/local-llm/generation/polish",
            json={"general_notes": "", "tone": "", "additions": [], "removals": []},
        )
        assert resp.status_code == 409

        # Move job to draft_ready to validate nominal response model
        assert job_id in local_llm._generation_jobs
        local_llm._generation_jobs[job_id]["status"] = "draft_ready"

        resp = client.post(
            "/local-llm/generation/polish",
            json={"general_notes": "Looks good", "tone": "professional", "additions": [], "removals": []},
        )
        assert resp.status_code == 200
        polish_body = resp.json()
        assert set(polish_body.keys()) == {"ok", "status"}
        assert polish_body["ok"] is True

        # 6) Cancel should return the cancellation response shape
        resp = client.post(f"/local-llm/generation/cancel?job_id={job_id}")
        assert resp.status_code == 200
        cancel_body = resp.json()
        assert set(cancel_body.keys()) == {"ok", "status"}
        assert cancel_body["ok"] is True
        assert cancel_body["status"] == "cancelled"

    finally:
        # Cleanup temp dir created by make_fake_git_zip
        tmp_root = Path(zip_path).parent
        try:
            # Remove the directory tree created for this test
            for p in sorted(tmp_root.rglob("*"), reverse=True):
                try:
                    if p.is_file() or p.is_symlink():
                        p.unlink(missing_ok=True)
                    else:
                        p.rmdir()
                except Exception:
                    pass
            tmp_root.rmdir()
        except Exception:
            pass


def test_context_returns_404_for_missing_zip(client):
    resp = client.post("/local-llm/context", json={"zip_path": "Z:/nope/does-not-exist.zip"})
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body
