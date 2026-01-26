"""Tests for retrieval endpoints: /skills/chronology, /resume, /summaries."""

import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from artifactminer.api.app import create_app
from artifactminer.db import (
    Base,
    get_db,
    RepoStat,
    Skill,
    ProjectSkill,
    ResumeItem,
    UserAIntelligenceSummary,
)


@pytest.fixture(scope="function")
def client_with_data():
    """Test client with seeded retrieval data."""
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

    # Projects: Old (2020) -> Middle (2021) -> New (2023)
    repos = [
        RepoStat(
            id=1,
            project_name="OldProject",
            project_path="/repo1",
            first_commit=datetime(2020, 1, 15),
            last_commit=datetime(2020, 6, 20),
        ),
        RepoStat(
            id=2,
            project_name="NewProject",
            project_path="/repo2",
            first_commit=datetime(2023, 3, 1),
            last_commit=now - timedelta(days=5),
        ),
        RepoStat(
            id=3,
            project_name="MiddleProject",
            project_path="/repo3",
            first_commit=datetime(2021, 6, 1),
            last_commit=datetime(2022, 12, 15),
        ),
    ]
    skills = [
        Skill(id=1, name="Python", category="Programming Languages"),
        Skill(id=2, name="FastAPI", category="Frameworks & Libraries"),
    ]
    project_skills = [
        ProjectSkill(
            repo_stat_id=1, skill_id=1, proficiency=0.7
        ),  # OldProject - Python
        ProjectSkill(
            repo_stat_id=2, skill_id=1, proficiency=0.9
        ),  # NewProject - Python
        ProjectSkill(
            repo_stat_id=2, skill_id=2, proficiency=0.8
        ),  # NewProject - FastAPI
    ]
    resume_items = [
        ResumeItem(
            id=1,
            title="Built REST API",
            content="FastAPI backend",
            category="Backend",
            repo_stat_id=2,
        ),
        ResumeItem(
            id=2,
            title="Legacy Work",
            content="Python refactoring",
            category="Backend",
            repo_stat_id=1,
        ),
    ]
    summaries = [
        UserAIntelligenceSummary(
            repo_path="/repo1",
            user_email="stavan@example.com",
            summary_text="Python skills",
            generated_at=now - timedelta(days=10),
        ),
        UserAIntelligenceSummary(
            repo_path="/repo2",
            user_email="stavan@example.com",
            summary_text="FastAPI experience",
            generated_at=now - timedelta(days=5),
        ),
        UserAIntelligenceSummary(
            repo_path="/repo3",
            user_email="other@example.com",
            summary_text="React dev",
            generated_at=now,
        ),
    ]
    db.add_all(repos + skills + project_skills + resume_items + summaries)
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client_empty():
    """Test client with no data."""
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
    yield TestClient(app)
    app.dependency_overrides.clear()


# === /skills/chronology ===


def test_skills_chronology_returns_ordered_list(client_with_data):
    """Returns skills ordered by first_commit ASC with proficiency & category."""
    resp = client_with_data.get("/skills/chronology")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 3
    # Oldest project first
    assert data[0]["project"] == "OldProject"
    assert data[0]["skill"] == "Python"
    assert data[0]["proficiency"] == 0.7
    assert data[0]["category"] == "Programming Languages"
    # Required fields present
    assert all(
        k in data[0] for k in ["date", "skill", "project", "proficiency", "category"]
    )


def test_skills_chronology_empty(client_empty):
    """Returns empty list when no data."""
    resp = client_empty.get("/skills/chronology")
    assert resp.status_code == 200
    assert resp.json() == []


# === /resume ===


def test_resume_returns_sorted_list(client_with_data):
    """Returns resume items sorted by last_commit DESC (newest first)."""
    resp = client_with_data.get("/resume")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    assert data[0]["project_name"] == "NewProject"  # newest
    assert data[-1]["project_name"] == "OldProject"  # oldest
    # Required fields
    assert all(
        k in data[0]
        for k in ["id", "title", "content", "category", "project_name", "created_at"]
    )


def test_resume_filter_by_project_id(client_with_data):
    """Filters by project_id query param."""
    resp = client_with_data.get("/resume?project_id=2")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 1
    assert data[0]["project_name"] == "NewProject"


def test_resume_nonexistent_project(client_with_data):
    """Returns empty for nonexistent project_id."""
    resp = client_with_data.get("/resume?project_id=999")
    assert resp.status_code == 200
    assert resp.json() == []


def test_resume_empty(client_empty):
    """Returns empty list when no data."""
    resp = client_empty.get("/resume")
    assert resp.status_code == 200
    assert resp.json() == []


# === /summaries ===


def test_summaries_requires_user_email(client_with_data):
    """Returns 422 without required user_email param."""
    resp = client_with_data.get("/summaries")
    assert resp.status_code == 422


def test_summaries_filters_by_email(client_with_data):
    """Returns only summaries for specified user, ordered by generated_at DESC."""
    resp = client_with_data.get("/summaries?user_email=stavan@example.com")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    assert all(s["user_email"] == "stavan@example.com" for s in data)
    # Newest first
    assert "FastAPI" in data[0]["summary_text"]
    # Required fields
    assert all(
        k in data[0]
        for k in ["id", "repo_path", "user_email", "summary_text", "generated_at"]
    )


def test_summaries_other_user(client_with_data):
    """Returns correct summaries for different user."""
    resp = client_with_data.get("/summaries?user_email=other@example.com")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 1
    assert data[0]["user_email"] == "other@example.com"


def test_summaries_nonexistent_user(client_with_data):
    """Returns empty for unknown user."""
    resp = client_with_data.get("/summaries?user_email=nobody@example.com")
    assert resp.status_code == 200
    assert resp.json() == []


def test_summaries_empty(client_empty):
    """Returns empty list when no data."""
    resp = client_empty.get("/summaries?user_email=anyone@example.com")
    assert resp.status_code == 200
    assert resp.json() == []

# === /AI_summaries ===

def test_AI_summaries_requires_params(client_with_data):
    """Returns 422 if required query params are missing."""
    # Missing both user_email and repo_path
    resp = client_with_data.get("/AI_summaries")
    assert resp.status_code == 422

    # Missing repo_path
    resp = client_with_data.get("/AI_summaries?user_email=stavan@example.com")
    assert resp.status_code == 422

    # Missing user_email
    resp = client_with_data.get("/AI_summaries?repo_path=/repo")
    assert resp.status_code == 422


def test_AI_summaries_filters_by_email_and_repo(client_with_data):
    """Returns only summaries matching user_email and repo_path prefix."""
    resp = client_with_data.get("/AI_summaries", params={
        "user_email": "stavan@example.com",
        "repo_path": "/repo"
    })
    assert resp.status_code == 200
    data = resp.json()

    # Only summaries for stavan@example.com
    assert all(s["user_email"] == "stavan@example.com" for s in data)

    # Only repos starting with "/repo"
    assert all(s["repo_path"].startswith("/repo") for s in data)

    # Required fields present
    for s in data:
        for field in ["user_email", "repo_path", "summary_text"]:
            assert field in s

    # There should be 2 matching summaries (based on seeded data)
    assert len(data) == 2


def test_AI_summaries_other_user(client_with_data):
    """Returns correct summaries for a different user."""
    resp = client_with_data.get("/AI_summaries", params={
        "user_email": "other@example.com",
        "repo_path": "/repo"
    })
    assert resp.status_code == 200
    data = resp.json()

    # Only one summary for 'other@example.com' in s
