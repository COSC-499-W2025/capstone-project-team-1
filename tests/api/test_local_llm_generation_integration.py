"""Integration tests for local-LLM resume generation API endpoints.

This module tests the full workflow of generating resumes using local LLM models:
1. Uploading a ZIP file containing git repositories
2. Extracting repository context and contributors
3. Starting an asynchronous generation job
4. Polling for job status until completion
5. Verifying proper cleanup of background processes
6. Testing the polish endpoint for final refinement
7. Testing error handling for invalid configurations
8. Testing resource guard functionality

Prerequisites:
    - llama-server binary installed (e.g., via `brew install llama.cpp`)
    - Required models downloaded to ~/.artifactminer/models/
    - mock.zip test fixture present in repository root

The tests verify both successful generation workflows, proper resource cleanup
to prevent zombie processes, and various edge cases like invalid models and
resource guard triggers.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest

import artifactminer.api.resume as resume_api
from artifactminer.resume.llm_client import check_llm_available

# =============================================================================
# CONSTANTS
# =============================================================================

# Model configurations for multi-stage generation pipeline
# Stage 1: Code analysis and initial skill extraction (larger model)
STAGE1_MODEL = "qwen2.5-coder-3b-q4"
# Stage 2 & 3: Resume drafting and refinement (smaller, faster model)
STAGE2_MODEL = "lfm2.5-1.2b-bf16"

# Timeout configurations for polling operations
STATUS_TIMEOUT_SECONDS = 180.0  # Max wait for generation to complete
STATUS_INTERVAL_SECONDS = 1.0  # Polling frequency for status checks
PROCESS_CLEANUP_TIMEOUT_SECONDS = 30.0  # Max wait for process termination


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _llama_server_pids() -> set[int]:
    """Retrieve PIDs of all running llama-server processes.

    Uses pgrep to find processes matching 'llama-server'. This is used to
    track spawned processes and verify they are properly cleaned up.

    Returns:
        Set of process IDs (integers) for running llama-server instances.
        Returns empty set if no processes found.

    Raises:
        AssertionError: If pgrep command fails unexpectedly.
    """
    proc = subprocess.run(
        ["pgrep", "-f", "llama-server"],
        capture_output=True,
        text=True,
        check=False,
        timeout=1.0,
    )
    # Return code 1 means no processes found (this is ok)
    if proc.returncode == 1:
        return set()
    # Any other non-zero return code indicates an error
    if proc.returncode != 0:
        raise AssertionError(
            f"pgrep failed (returncode={proc.returncode}, stderr={proc.stderr!r})"
        )

    # Parse pgrep output to extract PIDs
    pids: set[int] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.add(int(line))
        except ValueError:
            # Skip lines that don't parse as integers
            continue
    return pids


def _job_process_alive(job_id: str) -> bool:
    """Check if a generation worker process is still running.

    Accesses the module-level job registry to check the status of a
    specific background job. Thread-safe via module lock.

    Args:
        job_id: The unique identifier for the generation job.

    Returns:
        True if the job process exists and is alive, False otherwise.
    """
    with resume_api._lock:
        job = resume_api._jobs.get(job_id)
        if job is None or job.process is None:
            return False
        try:
            return job.process.is_alive()
        except Exception:
            # Process object may be in an invalid state
            return False


def _assert_local_llm_prereqs() -> None:
    """Validate that all prerequisites for local LLM tests are met.

    Checks for:
    1. llama-server binary in PATH
    2. Stage 1 model file exists
    3. Stage 2 model file exists

    This function should be called at the start of each test to fail
    fast with helpful error messages if the environment is not set up.

    Raises:
        AssertionError: If any prerequisite is missing.
    """
    assert shutil.which("llama-server"), (
        "llama-server is required. Install with `brew install llama.cpp`."
    )
    assert check_llm_available(STAGE1_MODEL), (
        f"Required model missing: {STAGE1_MODEL}. "
        "Download and place GGUF in ~/.artifactminer/models."
    )
    assert check_llm_available(STAGE2_MODEL), (
        f"Required model missing: {STAGE2_MODEL}. "
        "Download and place GGUF in ~/.artifactminer/models."
    )


def _start_generation_from_mock_zip(
    client,
    *,
    stage1_model: str = STAGE1_MODEL,
    stage2_model: str = STAGE2_MODEL,
    stage3_model: str = STAGE2_MODEL,
) -> str:
    """Orchestrate the full generation workflow starting from mock.zip.

    This helper performs the complete setup sequence:
    1. Creates context from mock.zip file
    2. Discovers contributors from extracted repositories
    3. Starts a generation job with the first repo and contributor

    Args:
        client: HTTP test client for making API requests.
        stage1_model: Model to use for stage 1 (code analysis). Defaults to STAGE1_MODEL.
        stage2_model: Model to use for stage 2 (drafting). Defaults to STAGE2_MODEL.
        stage3_model: Model to use for stage 3 (refinement). Defaults to STAGE2_MODEL.

    Returns:
        job_id: The unique identifier for the started generation job.

    Raises:
        AssertionError: If any API call fails or returns unexpected data.
    """
    # Locate the mock.zip test fixture (2 directories up from this file)
    repo_root = Path(__file__).resolve().parents[2]
    zip_path = repo_root / "mock.zip"
    assert zip_path.exists(), f"Required test artifact missing: {zip_path}"

    # Step 1: Create context from ZIP file
    # POST /local-llm/context extracts repositories and returns metadata
    context_response = client.post(
        "/local-llm/context", json={"zip_path": str(zip_path)}
    )
    assert context_response.status_code == 200
    repos = context_response.json()["repos"]
    assert repos, "No repositories found in mock.zip"
    repo_ids = [repo["id"] for repo in repos]

    # Step 2: Discover contributors from repositories
    # POST /local-llm/context/contributors analyzes git history
    contributors_response = client.post(
        "/local-llm/context/contributors",
        json={"repo_ids": repo_ids},
    )
    assert contributors_response.status_code == 200
    contributors = contributors_response.json()["contributors"]
    assert contributors, "No contributors found in selected repos"

    # Step 3: Start generation job
    # POST /local-llm/generation/start begins async resume generation
    start_response = client.post(
        "/local-llm/generation/start",
        json={
            "repo_ids": [repo_ids[0]],  # Use first repository
            "user_email": contributors[0]["email"],  # Use first contributor
            "stage1_model": stage1_model,
            "stage2_model": stage2_model,
            "stage3_model": stage3_model,
        },
    )
    assert start_response.status_code == 200
    payload = start_response.json()
    assert payload["status"] in {"queued", "running"}
    return payload["job_id"]


def _wait_for_success_status(client) -> dict:
    """Poll generation status until success or failure.

    Continuously queries the status endpoint until:
    - Success: status is 'draft_ready' or 'complete'
    - Failure: status is 'error', 'cancelled', or 'failed_resource_guard'
    - Timeout: exceeds STATUS_TIMEOUT_SECONDS (180 seconds)

    Args:
        client: HTTP test client for making API requests.

    Returns:
        dict: The final status response payload containing job details.

    Raises:
        pytest.fail: If generation fails or times out.
    """
    deadline = time.monotonic() + STATUS_TIMEOUT_SECONDS
    last_payload: dict | None = None

    while time.monotonic() < deadline:
        status_response = client.get("/local-llm/generation/status")
        assert status_response.status_code == 200
        payload = status_response.json()
        last_payload = payload
        status = payload["status"]

        # Success states - generation completed successfully
        if status in {"draft_ready", "complete"}:
            return payload

        # Failure states - generation encountered an error
        if status in {"error", "cancelled", "failed_resource_guard"}:
            pytest.fail(
                "Generation failed before success. "
                f"status={status!r}, error={payload.get('error')!r}, "
                f"messages={payload.get('messages')!r}"
            )

        # Wait before next poll
        time.sleep(STATUS_INTERVAL_SECONDS)

    # Timeout - generation did not complete in time
    pytest.fail(
        f"Timed out waiting for draft_ready/complete. last_payload={last_payload!r}"
    )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clear_local_llm_state():
    """Clean up module-level state before and after each test.

    This fixture ensures test isolation by:
    1. Removing extracted ZIP directories from disk
    2. Clearing in-memory job and intake registries
    3. Resetting active job/intake IDs

    Runs automatically for every test (autouse=True) to prevent state
    leakage between tests.

    Yields:
        None: Control passes to the test function.
    """
    # Setup: Clean up any leftover state before test runs
    for intake in list(resume_api._intakes.values()):
        shutil.rmtree(intake.extract_dir, ignore_errors=True)
    resume_api._intakes.clear()
    resume_api._jobs.clear()
    resume_api._active_intake_id = None
    resume_api._active_job_id = None

    yield  # Test runs here

    # Teardown: Clean up again after test completes
    # This ensures cleanup happens even if test fails
    for intake in list(resume_api._intakes.values()):
        shutil.rmtree(intake.extract_dir, ignore_errors=True)
    resume_api._intakes.clear()
    resume_api._jobs.clear()
    resume_api._active_intake_id = None
    resume_api._active_job_id = None


# =============================================================================
# TESTS
# =============================================================================


def test_generation_start_reaches_draft_or_complete(client) -> None:
    """Test that generation workflow completes successfully.

    Verifies the happy path:
    - Prerequisites are met (llama-server and models available)
    - Generation starts successfully from mock.zip
    - Status polling reaches draft_ready or complete
    - Cleanup occurs via cancel endpoint
    """
    # Verify test environment is properly configured
    _assert_local_llm_prereqs()

    # Start the generation workflow
    _start_generation_from_mock_zip(client)

    # Poll for completion and verify success
    try:
        payload = _wait_for_success_status(client)
        assert payload["status"] in {"draft_ready", "complete"}
    finally:
        # Ensure cleanup happens even if assertions fail
        client.post("/local-llm/generation/cancel")


def test_cancel_cleans_worker_and_llama_server_processes(client) -> None:
    """Test that cancel endpoint properly terminates all subprocesses.

    Verifies resource cleanup:
    - Worker subprocess starts and is tracked
    - llama-server process spawns during generation
    - Cancel endpoint stops both processes cleanly
    - No zombie processes remain after cleanup

    This prevents resource leaks and runaway processes.
    """
    # Verify test environment is properly configured
    _assert_local_llm_prereqs()

    # Capture baseline PIDs to identify test-spawned processes
    baseline_llama_pids = _llama_server_pids()

    # Start generation and get job ID
    job_id = _start_generation_from_mock_zip(client)

    # Phase 1: Wait for worker subprocess to start (up to 30 seconds)
    worker_deadline = time.monotonic() + 30.0
    while time.monotonic() < worker_deadline and not _job_process_alive(job_id):
        time.sleep(0.25)
    assert _job_process_alive(job_id), "Expected worker subprocess to start."

    # Phase 2: Wait for llama-server to spawn (up to 90 seconds)
    spawned_llama_pids: set[int] = set()
    llama_spawn_deadline = time.monotonic() + 90.0
    while time.monotonic() < llama_spawn_deadline:
        # Calculate new PIDs by subtracting baseline from current
        spawned_llama_pids = _llama_server_pids() - baseline_llama_pids
        if spawned_llama_pids:
            break  # llama-server has spawned

        # Check if generation failed before we could test cancel
        status_response = client.get("/local-llm/generation/status")
        assert status_response.status_code == 200
        status = status_response.json()["status"]
        if status in {"error", "cancelled", "failed_resource_guard"}:
            pytest.fail(
                f"Generation entered unexpected status before cancel: {status!r}"
            )
        time.sleep(0.5)

    assert spawned_llama_pids, "Expected llama-server subprocess to spawn."

    # Phase 3: Cancel the generation
    cancel_response = client.post("/local-llm/generation/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] in {"cancelled", "complete"}

    # Phase 4: Verify worker process cleanup (up to 30 seconds)
    worker_cleanup_deadline = time.monotonic() + PROCESS_CLEANUP_TIMEOUT_SECONDS
    while time.monotonic() < worker_cleanup_deadline and _job_process_alive(job_id):
        time.sleep(0.25)
    assert not _job_process_alive(job_id), "Worker subprocess did not terminate."

    # Phase 5: Verify llama-server cleanup (up to 30 seconds)
    # Use set intersection to find spawned processes still running
    llama_cleanup_deadline = time.monotonic() + PROCESS_CLEANUP_TIMEOUT_SECONDS
    remaining = spawned_llama_pids & _llama_server_pids()
    while remaining and time.monotonic() < llama_cleanup_deadline:
        time.sleep(0.5)
        remaining = spawned_llama_pids & _llama_server_pids()
    assert not remaining, (
        f"llama-server subprocesses still running: {sorted(remaining)!r}"
    )


def test_polish_happy_path_reaches_complete(client) -> None:
    """Test the polish endpoint for final resume refinement.

    Verifies the polish workflow:
    - Initial generation completes successfully
    - Polish endpoint accepts refinement instructions
    - Status transitions to 'polishing' state
    - Final output is generated and available
    - Cleanup occurs via cancel endpoint
    """
    # Verify test environment is properly configured
    _assert_local_llm_prereqs()

    # Start the generation workflow
    _start_generation_from_mock_zip(client)

    try:
        # Wait for initial generation to complete
        _wait_for_success_status(client)

        # Call the polish endpoint to refine the generated resume
        # POST /local-llm/generation/polish accepts refinement instructions
        polish_response = client.post(
            "/local-llm/generation/polish",
            json={
                "general_notes": "Keep it concise and technical.",
                "tone": "technical",  # Desired writing style
                "additions": ["Mention impact clearly"],  # Content to add
                "removals": [],  # Content to remove
            },
        )
        assert polish_response.status_code == 200
        assert polish_response.json()["status"] == "polishing"

        # Poll for polish completion
        deadline = time.monotonic() + STATUS_TIMEOUT_SECONDS
        last_payload: dict | None = None
        while time.monotonic() < deadline:
            status_response = client.get("/local-llm/generation/status")
            assert status_response.status_code == 200
            payload = status_response.json()
            last_payload = payload
            status = payload["status"]

            # Success - polish completed and output is available
            if status == "complete":
                assert payload["output"] is not None
                return

            # Failure - polish encountered an error
            if status in {"error", "cancelled", "failed_resource_guard"}:
                pytest.fail(
                    "Polish failed before complete. "
                    f"status={status!r}, error={payload.get('error')!r}, "
                    f"messages={payload.get('messages')!r}"
                )

            # Wait before next poll
            time.sleep(STATUS_INTERVAL_SECONDS)

        # Timeout - polish did not complete in time
        pytest.fail(
            "Timed out waiting for polished complete status. "
            f"last_payload={last_payload!r}"
        )
    finally:
        # Ensure cleanup happens even if test fails
        client.post("/local-llm/generation/cancel")


def test_cancel_is_idempotent(client) -> None:
    """Test that calling cancel twice produces stable, consistent results.

    Verifies idempotency of the cancel endpoint:
    - First cancel call succeeds and returns a status
    - Second cancel call also succeeds with same status
    - No errors or inconsistent behavior on retries

    Idempotency ensures cancel can be safely retried without side effects.
    """
    # Verify test environment is properly configured
    _assert_local_llm_prereqs()

    # Start the generation workflow
    _start_generation_from_mock_zip(client)

    # First cancel call
    first_response = client.post("/local-llm/generation/cancel")
    assert first_response.status_code == 200
    first_status = first_response.json()["status"]
    assert first_status in {"cancelled", "complete"}

    # Second cancel call - should be idempotent
    second_response = client.post("/local-llm/generation/cancel")
    assert second_response.status_code == 200
    second_status = second_response.json()["status"]
    assert second_status in {"cancelled", "complete"}

    # Verify consistency - both calls should return the same status
    assert second_status == first_status


def test_missing_model_configuration_fails_with_error_status(client) -> None:
    """Test that invalid model names produce a clear error status.

    Verifies error handling for configuration issues:
    - Generation starts with invalid model names
    - System detects missing models during job execution
    - Error status is reached with helpful message
    - Error message indicates model problem
    - Cleanup occurs via cancel endpoint
    """
    # Verify test environment is properly configured
    _assert_local_llm_prereqs()

    # Use an intentionally invalid model name
    invalid_model_name = "missing-model-for-test-do-not-create"

    # Start generation with invalid configuration
    _start_generation_from_mock_zip(
        client,
        stage2_model=invalid_model_name,
        stage3_model=invalid_model_name,
    )

    try:
        # Poll for error status
        deadline = time.monotonic() + STATUS_TIMEOUT_SECONDS
        last_payload: dict | None = None
        while time.monotonic() < deadline:
            status_response = client.get("/local-llm/generation/status")
            assert status_response.status_code == 200
            payload = status_response.json()
            last_payload = payload
            status = payload["status"]

            # Success - error status reached with helpful message
            if status == "error":
                error = payload.get("error") or ""
                assert isinstance(error, str)
                lowered = error.lower()
                # Verify error message is helpful (mentions model or not found)
                assert (
                    invalid_model_name in error
                    or "model" in lowered
                    or "not found" in lowered
                )
                return

            # Unexpected success - should have failed with invalid model
            if status in {"draft_ready", "complete", "failed_resource_guard"}:
                pytest.fail(
                    "Expected error status for invalid model configuration, "
                    f"got {status!r}. payload={payload!r}"
                )

            # Wait before next poll
            time.sleep(STATUS_INTERVAL_SECONDS)

        # Timeout - error status not reached in time
        pytest.fail(
            "Timed out waiting for error status after invalid model start. "
            f"last_payload={last_payload!r}"
        )
    finally:
        # Ensure cleanup happens even if test fails
        client.post("/local-llm/generation/cancel")


def test_resource_guard_triggers_failed_resource_guard_status(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that very low RAM limits trigger resource guard failure.

    Verifies the resource guard functionality:
    - Resource guard limit is patched to 1 MB (impossibly low)
    - Generation starts and quickly hits resource constraint
    - Status transitions to failed_resource_guard
    - Error message clearly indicates resource problem
    - Worker process is cleaned up after failure

    Resource guard prevents OOM crashes by proactively failing jobs.
    """
    # Verify test environment is properly configured
    _assert_local_llm_prereqs()

    # Monkeypatch resource guard to use impossibly low RAM limit
    # This ensures the guard will trigger immediately
    monkeypatch.setattr(resume_api, "_RESOURCE_GUARD_MAX_RAM_MB", 1.0)

    # Start generation - should trigger resource guard due to low RAM limit
    job_id = _start_generation_from_mock_zip(client)

    # Poll for resource guard failure status
    deadline = time.monotonic() + 90.0
    last_payload: dict | None = None
    while time.monotonic() < deadline:
        status_response = client.get("/local-llm/generation/status")
        assert status_response.status_code == 200
        payload = status_response.json()
        last_payload = payload
        status = payload["status"]

        # Success - resource guard triggered as expected
        if status == "failed_resource_guard":
            error = payload.get("error") or ""
            assert isinstance(error, str)
            assert "resource guard" in error.lower()
            break

        # Unexpected success - generation should have been blocked
        if status in {"draft_ready", "complete"}:
            pytest.fail(
                "Expected resource guard failure but generation succeeded. "
                f"payload={payload!r}"
            )

        # Wrong failure type - expected resource guard specifically
        if status in {"error", "cancelled"}:
            pytest.fail(
                "Expected failed_resource_guard but got different terminal status. "
                f"payload={payload!r}"
            )

        time.sleep(0.5)
    else:
        # Timeout - resource guard status not reached
        pytest.fail(
            "Timed out waiting for failed_resource_guard status. "
            f"last_payload={last_payload!r}"
        )

    # Verify cleanup occurs even after resource guard failure
    cleanup_deadline = time.monotonic() + PROCESS_CLEANUP_TIMEOUT_SECONDS
    while time.monotonic() < cleanup_deadline and _job_process_alive(job_id):
        time.sleep(0.25)
    assert not _job_process_alive(job_id), (
        "Worker subprocess should be cleaned up after resource-guard failure."
    )
