"""Tests for POST /resume/generate endpoint."""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from artifactminer.api.app import create_app
from artifactminer.db import (
    Base,
    get_db,
    RepoStat,
    ResumeItem,
    Question,
    UserAnswer,
    Consent,
)


@pytest.fixture
def client():
    """Test client with seeded data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # Seed test data
    db = TestingSessionLocal()
    now = datetime.now(UTC).replace(tzinfo=None)

    db.add(Question(id=1, key="email", question_text="Email?", order=1, required=True))
    db.add(UserAnswer(question_id=1, answer_text="test@example.com", answered_at=now))
    db.add(Consent(id=1, consent_level="local", accepted_at=now))
    db.add(
        RepoStat(
            id=1,
            project_name="TestProject",
            project_path="/test/repo",
            languages=["Python"],
            frameworks=["FastAPI"],
            total_commits=10,
            first_commit=now,
            last_commit=now,
        )
    )
    db.add(
        RepoStat(
            id=2,
            project_name="DeletedProject",
            project_path="/test/repo2",
            languages=["Java"],
            frameworks=[],
            total_commits=5,
            first_commit=now,
            last_commit=now,
            deleted_at=now,
        )
    )
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
@patch("artifactminer.api.resume.Path")
def test_generate_single_project(mock_path, mock_collect, mock_analyzer, client):
    """Generates evidence/skills without creating Deep Insight resume items."""
    from artifactminer.skills.deep_analysis import Insight, DeepAnalysisResult

    mock_path.return_value.exists.return_value = True
    mock_collect.return_value = ["commit additions"]

    # Mock insights: these should now persist as ProjectEvidence, not ResumeItem rows.
    mock_insight = Insight(
        title="Test Insight",
        evidence=["test evidence 1", "test evidence 2"],
        why_it_matters="This demonstrates testing skills",
    )
    mock_analyzer.return_value.analyze.return_value = DeepAnalysisResult(
        insights=[mock_insight], skills=[]
    )

    resp = client.post(
        "/resume/generate", json={"project_ids": [1], "regenerate": False}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True  # Success = no errors, not based on item count
    assert data["consent_level"] == "local"
    assert isinstance(data["resume_items"], list)
    assert data["items_generated"] == 1  # Count of evidence items (insights)
    evidence = client.get("/projects/1/evidence")
    assert evidence.status_code == 200
    assert len(evidence.json()) > 0


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
def test_generate_missing_project(mock_collect, mock_analyzer, client):
    """Returns 404 for non-existent project."""
    resp = client.post(
        "/resume/generate", json={"project_ids": [999], "regenerate": False}
    )

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
def test_generate_deleted_project(mock_collect, mock_analyzer, client):
    """Returns 404 for soft-deleted project."""
    resp = client.post(
        "/resume/generate", json={"project_ids": [2], "regenerate": False}
    )

    assert resp.status_code == 404


def test_generate_empty_project_list(client):
    """Returns 422 for empty project_ids list."""
    resp = client.post(
        "/resume/generate", json={"project_ids": [], "regenerate": False}
    )

    assert resp.status_code == 422


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
@patch("artifactminer.api.resume.Path")
def test_generate_with_errors(mock_path, mock_collect, mock_analyzer, client):
    """Handles analyzer errors gracefully and returns success=False when errors occur."""
    mock_path.return_value.exists.return_value = True
    mock_collect.side_effect = Exception("Git error")
    mock_analyzer.return_value.analyze.side_effect = Exception("Analysis failed")

    resp = client.post(
        "/resume/generate", json={"project_ids": [1], "regenerate": False}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False  # Success = False when errors occur
    assert len(data["errors"]) > 0
    assert data["items_generated"] == 0


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
@patch("artifactminer.api.resume.Path")
def test_generate_with_empty_insights(mock_path, mock_collect, mock_analyzer, client):
    """Returns success=True when analysis completes but produces no insights (no errors)."""
    from artifactminer.skills.deep_analysis import DeepAnalysisResult

    mock_path.return_value.exists.return_value = True
    mock_collect.return_value = ["commit additions"]

    # Mock analysis that returns empty insights
    mock_analyzer.return_value.analyze.return_value = DeepAnalysisResult(
        insights=[], skills=[]
    )

    resp = client.post(
        "/resume/generate", json={"project_ids": [1], "regenerate": False}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True  # Success = no errors, even with 0 insights
    assert data["items_generated"] == 0
    assert len(data["errors"]) == 0  # No errors, just no insights


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
@patch("artifactminer.api.resume.Path")
def test_warning_does_not_flip_success_false(
    mock_path, mock_collect, mock_analyzer, client
):
    """Non-critical git collection warnings do not mark the run as failed."""
    from artifactminer.skills.deep_analysis import DeepAnalysisResult

    mock_path.return_value.exists.return_value = True
    mock_collect.side_effect = Exception("Git error")
    mock_analyzer.return_value.analyze.return_value = DeepAnalysisResult(
        insights=[], skills=[]
    )

    resp = client.post("/resume/generate", json={"project_ids": [1], "regenerate": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["errors"] == []
    assert len(data["warnings"]) == 1


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
@patch("artifactminer.api.resume.Path")
def test_items_generated_counts_persisted_rows_not_raw_insights(
    mock_path, mock_collect, mock_analyzer, client
):
    """Counts persisted evidence rows after dedupe, not raw insight list length."""
    from artifactminer.skills.deep_analysis import Insight, DeepAnalysisResult

    mock_path.return_value.exists.return_value = True
    mock_collect.return_value = ["commit additions"]

    duplicate_insight = Insight(
        title="Deduped Insight",
        evidence=["same source"],
        why_it_matters="This should dedupe on second run",
    )
    mock_analyzer.return_value.analyze.return_value = DeepAnalysisResult(
        insights=[duplicate_insight], skills=[]
    )

    first = client.post("/resume/generate", json={"project_ids": [1], "regenerate": False})
    assert first.status_code == 200
    assert first.json()["items_generated"] == 1

    second = client.post("/resume/generate", json={"project_ids": [1], "regenerate": False})
    assert second.status_code == 200
    assert second.json()["items_generated"] == 0


@patch("artifactminer.api.resume.DeepRepoAnalyzer")
@patch("artifactminer.api.resume.collect_user_additions")
@patch("artifactminer.api.resume.Path")
def test_regenerate_replaces_existing_project_evidence(
    mock_path, mock_collect, mock_analyzer, client
):
    """regenerate=True clears prior ProjectEvidence before persisting new results."""
    from artifactminer.skills.deep_analysis import Insight, DeepAnalysisResult

    mock_path.return_value.exists.return_value = True
    mock_collect.return_value = ["commit additions"]

    first_insight = Insight(
        title="Original Insight",
        evidence=["source A"],
        why_it_matters="first version",
    )
    second_insight = Insight(
        title="Regenerated Insight",
        evidence=["source B"],
        why_it_matters="second version",
    )
    mock_analyzer.return_value.analyze.side_effect = [
        DeepAnalysisResult(insights=[first_insight], skills=[]),
        DeepAnalysisResult(insights=[second_insight], skills=[]),
    ]

    first = client.post("/resume/generate", json={"project_ids": [1], "regenerate": False})
    assert first.status_code == 200
    assert first.json()["items_generated"] == 1

    second = client.post("/resume/generate", json={"project_ids": [1], "regenerate": True})
    assert second.status_code == 200
    assert second.json()["items_generated"] == 1

    evidence_resp = client.get("/projects/1/evidence")
    assert evidence_resp.status_code == 200
    evidence = evidence_resp.json()
    assert len(evidence) == 1
    assert evidence[0]["content"].startswith("Regenerated Insight:")
