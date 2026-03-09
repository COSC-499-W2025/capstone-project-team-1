"""Tests for transport-layer local LLM schemas.

Validates request/response contracts for /local-llm/* endpoints.
"""

import pytest
from pydantic import ValidationError

from artifactminer.api.local_llm_schemas import (
    IntakeCreateRequest,
    IntakeCreateResponse,
    RepositoryCandidate,
    ContributorDiscoveryRequest,
    ContributorIdentity,
    GenerationStartRequest,
    GenerationStartResponse,
    GenerationStatusResponse,
    GenerationTelemetry,
    PolishRequest,
    PolishResponse,
    CancellationResponse,
)


class TestIntakeCreateRequest:
    """Test intake creation request validation."""

    def test_valid_zip_path(self):
        req = IntakeCreateRequest(zip_path="/path/to/file.zip")
        assert req.zip_path == "/path/to/file.zip"

    def test_rejects_empty_zip_path(self):
        with pytest.raises(ValidationError):
            IntakeCreateRequest(zip_path="")

    def test_requires_zip_path(self):
        with pytest.raises(ValidationError):
            IntakeCreateRequest()


class TestRepositoryCandidate:
    """Test discovered repository model."""

    def test_valid_candidate(self):
        repo = RepositoryCandidate(
            id="repo-1", name="my-project", rel_path="projects/my-project"
        )
        assert repo.id == "repo-1"
        assert repo.name == "my-project"
        assert repo.rel_path == "projects/my-project"

    def test_all_fields_required(self):
        with pytest.raises(ValidationError):
            RepositoryCandidate(id="repo-1")

    def test_serialization(self):
        repo = RepositoryCandidate(id="r1", name="proj", rel_path="p/proj")
        data = repo.model_dump()
        assert data == {"id": "r1", "name": "proj", "rel_path": "p/proj"}


class TestIntakeCreateResponse:
    """Test intake creation response."""

    def test_with_multiple_repos(self):
        repos = [
            RepositoryCandidate(id="1", name="repo1", rel_path="src/repo1"),
            RepositoryCandidate(id="2", name="repo2", rel_path="src/repo2"),
        ]
        resp = IntakeCreateResponse(
            intake_id="intake-123", zip_path="/tmp/upload.zip", repos=repos
        )
        assert resp.intake_id == "intake-123"
        assert len(resp.repos) == 2

    def test_empty_repos(self):
        resp = IntakeCreateResponse(
            intake_id="intake-empty", zip_path="/tmp/empty.zip", repos=[]
        )
        assert resp.repos == []

    def test_deserialization(self):
        data = {
            "intake_id": "test-123",
            "zip_path": "/path",
            "repos": [{"id": "r1", "name": "p", "rel_path": "src/p"}],
        }
        resp = IntakeCreateResponse(**data)
        assert resp.intake_id == "test-123"


class TestContributorDiscoveryRequest:
    """Test contributor discovery request."""

    def test_valid_repo_ids(self):
        req = ContributorDiscoveryRequest(repo_ids=["repo-1", "repo-2"])
        assert req.repo_ids == ["repo-1", "repo-2"]

    def test_single_repo_id(self):
        req = ContributorDiscoveryRequest(repo_ids=["repo-1"])
        assert len(req.repo_ids) == 1

    def test_rejects_empty_list(self):
        with pytest.raises(ValidationError):
            ContributorDiscoveryRequest(repo_ids=[])


class TestContributorIdentity:
    """Test contributor identity model."""

    def test_complete_identity(self):
        contrib = ContributorIdentity(
            email="alice@example.com",
            name="Alice",
            repo_count=3,
            commit_count=42,
            candidate_username="alice_dev",
        )
        assert contrib.email == "alice@example.com"
        assert contrib.repo_count == 3
        assert contrib.commit_count == 42

    def test_optional_name(self):
        contrib = ContributorIdentity(
            email="bob@example.com",
            repo_count=1,
            commit_count=5,
            candidate_username="bob",
        )
        assert contrib.name is None

    def test_zero_counts(self):
        contrib = ContributorIdentity(
            email="user@example.com",
            repo_count=0,
            commit_count=0,
            candidate_username="user",
        )
        assert contrib.repo_count == 0


class TestGenerationStartRequest:
    """Test generation start request."""

    def test_minimal_request(self):
        req = GenerationStartRequest(
            repo_ids=["repo-1"], user_email="user@example.com"
        )
        assert req.intake_id is None
        assert req.stage1_model == "qwen2.5-coder-3b-q4"
        assert req.stage2_model == "lfm2.5-1.2b-bf16"

    def test_with_intake_id(self):
        req = GenerationStartRequest(
            intake_id="intake-123",
            repo_ids=["repo-1"],
            user_email="user@example.com",
        )
        assert req.intake_id == "intake-123"

    def test_custom_models(self):
        req = GenerationStartRequest(
            repo_ids=["repo-1"],
            user_email="user@example.com",
            stage1_model="custom-1",
            stage2_model="custom-2",
            stage3_model="custom-3",
        )
        assert req.stage1_model == "custom-1"
        assert req.stage2_model == "custom-2"
        assert req.stage3_model == "custom-3"

    def test_rejects_empty_repo_ids(self):
        with pytest.raises(ValidationError):
            GenerationStartRequest(repo_ids=[], user_email="user@example.com")

    def test_rejects_invalid_email_format(self):
        with pytest.raises(ValidationError):
            GenerationStartRequest(repo_ids=["repo-1"], user_email="not-an-email")

    def test_accepts_complex_valid_email(self):
        req = GenerationStartRequest(
            repo_ids=["repo-1"], user_email="user+tag@sub.domain.com"
        )
        assert req.user_email == "user+tag@sub.domain.com"

    def test_rejects_empty_model(self):
        with pytest.raises(ValidationError):
            GenerationStartRequest(
                repo_ids=["repo-1"],
                user_email="user@example.com",
                stage1_model="",
            )


class TestGenerationStartResponse:
    """Test generation start response."""

    def test_valid_response(self):
        resp = GenerationStartResponse(job_id="job-123", status="queued")
        assert resp.job_id == "job-123"
        assert resp.status == "queued"

    def test_all_valid_statuses(self):
        for status in [
            "queued",
            "running",
            "draft_ready",
            "polishing",
            "complete",
            "error",
            "cancelled",
            "failed_resource_guard",
        ]:
            resp = GenerationStartResponse(job_id="job-1", status=status)
            assert resp.status == status

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            GenerationStartResponse(job_id="job-1", status="bad_status")


class TestGenerationTelemetry:
    """Test progress telemetry model."""

    def test_defaults(self):
        tel = GenerationTelemetry()
        assert tel.stage == "ANALYZE"
        assert tel.active_model is None
        assert tel.repos_total == 0
        assert tel.elapsed_seconds == 0.0

    def test_with_progress(self):
        tel = GenerationTelemetry(
            stage="FACTS",
            active_model="qwen",
            repos_total=5,
            repos_done=2,
            facts_total=42,
            elapsed_seconds=120.5,
        )
        assert tel.stage == "FACTS"
        assert tel.repos_done == 2
        assert tel.elapsed_seconds == 120.5

    def test_all_stages(self):
        for stage in ["ANALYZE", "FACTS", "DRAFT", "POLISH"]:
            tel = GenerationTelemetry(stage=stage)
            assert tel.stage == stage

    def test_rejects_invalid_stage(self):
        with pytest.raises(ValidationError):
            GenerationTelemetry(stage="INVALID")


class TestGenerationStatusResponse:
    """Test job status response."""

    def test_queued_status(self):
        resp = GenerationStatusResponse(
            status="queued",
            stage="ANALYZE",
            messages=[],
            telemetry=GenerationTelemetry(),
        )
        assert resp.status == "queued"
        assert resp.draft is None
        assert resp.output is None

    def test_with_draft(self):
        draft = {"projects": [{"name": "Project A"}]}
        resp = GenerationStatusResponse(
            status="draft_ready",
            stage="DRAFT",
            messages=[],
            telemetry=GenerationTelemetry(stage="DRAFT"),
            draft=draft,
        )
        assert resp.draft == draft

    def test_with_output(self):
        output = {"projects": [{"name": "Project A", "polished": True}]}
        resp = GenerationStatusResponse(
            status="complete",
            stage="POLISH",
            messages=[],
            telemetry=GenerationTelemetry(stage="POLISH"),
            output=output,
        )
        assert resp.output == output

    def test_with_error(self):
        resp = GenerationStatusResponse(
            status="error",
            stage="ANALYZE",
            messages=[],
            telemetry=GenerationTelemetry(),
            error="Repository extraction failed",
        )
        assert resp.error == "Repository extraction failed"

    def test_with_messages(self):
        resp = GenerationStatusResponse(
            status="running",
            stage="FACTS",
            messages=["Starting", "Processing"],
            telemetry=GenerationTelemetry(stage="FACTS"),
        )
        assert len(resp.messages) == 2


class TestPolishRequest:
    """Test polish/refinement request."""

    def test_defaults(self):
        req = PolishRequest()
        assert req.general_notes == ""
        assert req.tone == ""
        assert req.additions == []
        assert req.removals == []

    def test_with_feedback(self):
        req = PolishRequest(
            general_notes="Add more detail",
            tone="professional",
            additions=["AWS cert"],
            removals=["Old project"],
        )
        assert len(req.additions) == 1
        assert len(req.removals) == 1


class TestPolishResponse:
    """Test polish operation response."""

    def test_success(self):
        resp = PolishResponse(ok=True, status="polishing")
        assert resp.ok is True
        assert resp.status == "polishing"

    def test_all_statuses(self):
        for status in ["polishing", "complete", "error"]:
            resp = PolishResponse(ok=True, status=status)
            assert resp.status == status


class TestCancellationResponse:
    """Test job cancellation response."""

    def test_cancelled(self):
        resp = CancellationResponse(ok=True, status="cancelled")
        assert resp.ok is True
        assert resp.status == "cancelled"

    def test_failed_cancel(self):
        resp = CancellationResponse(ok=False, status="running")
        assert resp.ok is False


class TestWorkflowIntegration:
    """Integration tests for realistic workflows."""

    def test_full_generation_flow(self):
        # Intake
        repos = [RepositoryCandidate(id="r1", name="p1", rel_path="a/p1")]
        intake = IntakeCreateResponse(
            intake_id="intake-1", zip_path="/zip", repos=repos
        )
        assert intake.intake_id == "intake-1"

        # Start generation
        start = GenerationStartRequest(
            intake_id="intake-1", repo_ids=["r1"], user_email="user@test.com"
        )
        assert start.intake_id == "intake-1"

        # Running status
        status = GenerationStatusResponse(
            status="running",
            stage="FACTS",
            messages=["Processing"],
            telemetry=GenerationTelemetry(stage="FACTS", repos_done=1),
        )
        assert status.stage == "FACTS"

        # Polish
        polish = PolishRequest(tone="professional")
        assert polish.tone == "professional"

        # Complete
        final = GenerationStatusResponse(
            status="complete",
            stage="POLISH",
            messages=[],
            telemetry=GenerationTelemetry(stage="POLISH"),
            output={"projects": []},
        )
        assert final.status == "complete"

    def test_cancellation_flow(self):
        # Running job
        status = GenerationStatusResponse(
            status="running",
            stage="FACTS",
            messages=["Processing"],
            telemetry=GenerationTelemetry(),
        )
        assert status.status == "running"

        # Cancel
        cancel = CancellationResponse(ok=True, status="cancelled")
        assert cancel.status == "cancelled"
