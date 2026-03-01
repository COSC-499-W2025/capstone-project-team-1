"""Integration tests for local-LLM resume generation API endpoints.

This module tests the full workflow of generating resumes using local LLM models:
1. Uploading a ZIP file containing git repositories
2. Extracting repository context and contributors
3. Starting an asynchronous generation job
4. Polling for job status until completion
5. Verifying proper cleanup of background processes
6. Testing the polish endpoint for final refinement

Prerequisites:
    - llama-server binary installed (e.g., via `brew install llama.cpp`)
    - Required models downloaded to ~/.artifactminer/models/
    - mock.zip test fixture present in repository root

The tests verify both successful generation workflows and proper resource cleanup
to prevent zombie processes.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

import artifactminer.api.resume as resume_api
from artifactminer.resume.llm_client import check_llm_available

STAGE1_MODEL = "qwen2.5-coder-3b-q4"
STAGE2_MODEL = "lfm2.5-1.2b-bf16"
POLL_TIMEOUT_SECONDS = 180.0
POLL_INTERVAL_SECONDS = 1.0


@pytest.fixture(autouse=True)
def clear_local_llm_state():
    """Isolate module-level in-memory local-LLM state between tests."""
    for intake in list(resume_api._intakes.values()):
        shutil.rmtree(intake.extract_dir, ignore_errors=True)
    resume_api._intakes.clear()
    resume_api._jobs.clear()
    resume_api._active_intake_id = None
    resume_api._active_job_id = None

    yield

    for intake in list(resume_api._intakes.values()):
        shutil.rmtree(intake.extract_dir, ignore_errors=True)
    resume_api._intakes.clear()
    resume_api._jobs.clear()
    resume_api._active_intake_id = None
    resume_api._active_job_id = None
