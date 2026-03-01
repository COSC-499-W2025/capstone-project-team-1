"""Smoke tests for local-LLM API route wiring.

These tests aim to be fast and deterministic: they verify that the local-LLM
endpoints are registered and enforce basic request/state validation.

They intentionally do NOT execute any LLM pipeline work (no ZIP extraction, no
multiprocessing workers, no model downloads).
"""


# ---------------------------------------------------------------------------
# Context smoke tests
# ---------------------------------------------------------------------------


def test_local_llm_context_requires_zip_path(client) -> None:
    """POST /local-llm/context rejects requests missing `zip_path`.

    The intake creation endpoint expects a JSON body matching
    `PipelineIntakeCreateRequest` (see `src/artifactminer/api/resume.py`).

    This smoke test only asserts schema enforcement (422) for an empty payload.
    """
    response = client.post("/local-llm/context", json={})
    assert response.status_code == 422


def test_local_llm_context_contributors_requires_active_context(client) -> None:
    """POST /local-llm/context/contributors requires an active intake context.

    Calling this before `POST /local-llm/context` should return 404 with a stable
    message so the client can guide the user through the correct sequence.
    """
    response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": ["r1"]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No active context found. Create context first."


# ---------------------------------------------------------------------------
# Generation smoke tests
# ---------------------------------------------------------------------------


def test_local_llm_generation_start_requires_payload(client) -> None:
    """POST /local-llm/generation/start rejects invalid/missing payload.

    This endpoint expects `PipelineStartRequest` (repo IDs + user identity).
    The smoke test asserts request validation (422) without starting any worker.
    """
    response = client.post("/local-llm/generation/start", json={})
    assert response.status_code == 422


def test_local_llm_generation_status_requires_active_generation(client) -> None:
    """GET /local-llm/generation/status returns 404 when no job is active.

    Without a prior `POST /local-llm/generation/start`, polling should return a
    not-found error (the active job is held in memory).
    """
    response = client.get("/local-llm/generation/status")
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "No active generation found. Start generation first."
    )


def test_local_llm_generation_polish_requires_active_generation(client) -> None:
    """POST /local-llm/generation/polish returns 404 when no job is active.

    Polish is only meaningful after a generation job exists (and typically after
    a draft is produced). This smoke test covers the simplest guardrail: no job.
    """
    response = client.post("/local-llm/generation/polish", json={})
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "No active generation found. Start generation first."
    )


def test_local_llm_generation_cancel_requires_active_generation(client) -> None:
    """POST /local-llm/generation/cancel returns 404 when no job is active.

    Cancel is only meaningful when a generation has been started. This smoke
    test verifies the endpoint is wired and rejects the no-active-job case.
    """
    response = client.post("/local-llm/generation/cancel")
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "No active generation found. Start generation first."
    )
