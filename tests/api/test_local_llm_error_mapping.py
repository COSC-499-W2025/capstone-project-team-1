"""Focused tests ensuring /local-llm/* endpoints map unexpected errors to 500.

These tests intentionally monkeypatch internal helpers to raise exceptions
and assert the route-layer maps them to HTTP 500 with an appropriate
error detail prefix.
"""

from zipfile import ZipFile
import uuid

import pytest

from artifactminer.api import local_llm


def _make_intake(client, tmp_path):
    zip_path = tmp_path / "error_map.zip"
    with ZipFile(zip_path, 'w') as zf:
        zf.writestr("repo/.git/config", "[core]")
        zf.writestr("repo/.git/HEAD", "ref: refs/heads/main")

    resp = client.post("/local-llm/context", json={"zip_path": str(zip_path)})
    assert resp.status_code == 200
    return resp.json()


def test_discover_contributors_internal_error_maps_to_500(client, tmp_path, monkeypatch):
    intake = _make_intake(client, tmp_path)

    def _raise(exc_paths):
        raise RuntimeError("discovery boom")

    monkeypatch.setattr(local_llm, "_discover_contributors_in_repos", lambda paths: (_ for _ in ()).throw(RuntimeError("discovery boom")))

    resp = client.post("/local-llm/context/contributors", json={"repo_ids": [intake["repos"][0]["id"]]})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "failed to discover contributors" in detail.lower()


def test_generation_start_internal_error_maps_to_500(client, tmp_path, monkeypatch):
    intake = _make_intake(client, tmp_path)

    # Force uuid generation to error to simulate unexpected internal failure
    monkeypatch.setattr(local_llm, "uuid", type("U", (), {"uuid4": staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("uuid boom")))}) )

    resp = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake["intake_id"],
            "repo_ids": [intake["repos"][0]["id"]],
            "user_email": "dev@example.com",
        },
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "failed to start generation" in detail.lower()


def test_get_generation_status_internal_error_maps_to_500(client, tmp_path, monkeypatch):
    intake = _make_intake(client, tmp_path)

    # Start a job normally
    start = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake["intake_id"],
            "repo_ids": [intake["repos"][0]["id"]],
            "user_email": "dev@example.com",
        },
    )
    assert start.status_code == 200
    job_id = start.json()["job_id"]

    # Break telemetry construction to force a 500
    def _bad_telemetry(*args, **kwargs):
        raise RuntimeError("telemetry boom")

    monkeypatch.setattr(local_llm, "GenerationTelemetry", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("telemetry boom")))

    resp = client.get("/local-llm/generation/status")
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "failed to retrieve generation status" in detail.lower()


def test_polish_generation_internal_error_maps_to_500(client, tmp_path, monkeypatch):
    intake = _make_intake(client, tmp_path)

    start = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake["intake_id"],
            "repo_ids": [intake["repos"][0]["id"]],
            "user_email": "dev@example.com",
        },
    )
    assert start.status_code == 200
    job_id = start.json()["job_id"]

    # Replace job entry with object that raises on setitem to simulate runtime failure
    class FaultyJob(dict):
        def __setitem__(self, key, value):
            raise RuntimeError("cannot set status")

    local_llm._generation_jobs[job_id] = FaultyJob({"status": "draft_ready"})
    local_llm._active_generation_id = job_id

    resp = client.post(
        "/local-llm/generation/polish",
        json={
            "general_notes": "Please improve",
            "tone": "professional",
            "additions": [],
            "removals": [],
        },
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "failed to process polish request" in detail.lower()


def test_generation_cancel_internal_error_maps_to_500(client, tmp_path, monkeypatch):
    intake = _make_intake(client, tmp_path)

    start = client.post(
        "/local-llm/generation/start",
        json={
            "intake_id": intake["intake_id"],
            "repo_ids": [intake["repos"][0]["id"]],
            "user_email": "dev@example.com",
        },
    )
    assert start.status_code == 200
    job_id = start.json()["job_id"]

    # Make _stop_job_runtime raise an unexpected exception
    async def _bad_stop(job_id, job):
        raise RuntimeError("stop boom")

    monkeypatch.setattr(local_llm, "_stop_job_runtime", _bad_stop)

    resp = client.post("/local-llm/generation/cancel")
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "failed to cancel generation runtime" in detail.lower()
