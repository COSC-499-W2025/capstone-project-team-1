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
    UserRepoStat,
    Skill,
    ProjectSkill,
    UserProjectSkill,
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

    # UserProjectSkill rows that OVERLAP with ProjectSkill (for deduplication testing)
    # repo 1 + Python already in ProjectSkill above -> tests set-union dedup
    user_project_skills = [
        UserProjectSkill(
            repo_stat_id=1, skill_id=1, user_email="stavan@example.com", proficiency=0.75
        ),
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
    user_repo_stats = [
        UserRepoStat(
            project_name="OldProject",
            project_path="/repo1",
            user_role="Contributor",
        ),
        UserRepoStat(
            project_name="NewProject",
            project_path="/repo2",
            user_role="Lead Developer",
        ),
    ]
    db.add_all(
        repos
        + skills
        + project_skills
        + user_project_skills
        + resume_items
        + summaries
        + user_repo_stats
    )
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

    # 3 ProjectSkill rows + 1 UserProjectSkill row = 4 chronology entries
    assert len(data) == 4
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
    assert data[0]["role"] == "Lead Developer"
    assert data[-1]["role"] == "Contributor"
    # Required fields
    assert all(
        k in data[0]
        for k in ["id", "title", "content", "category", "project_name", "role", "created_at"]
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

    # Only one summary for 'other@example.com' in seeded data
    assert len(data) == 1
    assert data[0]["user_email"] == "other@example.com"


# === /skills ===


def test_skills_empty(client_empty):
    """Returns empty list when no data."""
    resp = client_empty.get("/skills")
    assert resp.status_code == 200
    assert resp.json() == []


def test_skills_returns_all_skills(client_with_data):
    """GET /skills returns all skills from the Skill table."""
    resp = client_with_data.get("/skills")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    # Required fields present
    assert all(k in data[0] for k in ["id", "name", "category"])
    # Should be ordered by name
    assert data[0]["name"] == "FastAPI"
    assert data[1]["name"] == "Python"


def test_skills_returns_correct_fields(client_with_data):
    """Each skill has id, name, and category fields."""
    resp = client_with_data.get("/skills")
    assert resp.status_code == 200
    data = resp.json()

    for skill in data:
        assert "id" in skill
        assert "name" in skill
        assert "category" in skill


def test_skills_filter_by_category(client_with_data):
    """Filters skills by category query param."""
    resp = client_with_data.get("/skills?category=Programming Languages")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 1
    assert data[0]["name"] == "Python"
    assert data[0]["category"] == "Programming Languages"


def test_skills_filter_nonexistent_category(client_with_data):
    """Returns empty list for nonexistent category."""
    resp = client_with_data.get("/skills?category=Nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []


def test_skills_with_project_count(client_with_data):
    """Include project count when include_project_count=true."""
    resp = client_with_data.get("/skills?include_project_count=true")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    # Check project_count is present
    for skill in data:
        assert "project_count" in skill
        assert skill["project_count"] is not None

    # Python is used in 2 projects (OldProject and NewProject)
    python_skill = next(s for s in data if s["name"] == "Python")
    assert python_skill["project_count"] == 2

    # FastAPI is used in 1 project (NewProject)
    fastapi_skill = next(s for s in data if s["name"] == "FastAPI")
    assert fastapi_skill["project_count"] == 1


def test_skills_project_count_no_double_counting(client_with_data):
    """Verify project count doesn't double-count when skill exists in both tables.

    The client_with_data fixture seeds Python in ProjectSkill for repos 1 & 2
    AND in UserProjectSkill for repo 1 (overlap). The count should deduplicate.
    """
    resp = client_with_data.get("/skills?include_project_count=true")
    assert resp.status_code == 200
    data = resp.json()

    python_data = next(s for s in data if s["name"] == "Python")
    # Should be 2 (not 3), because repo 1 appears in both tables but is deduplicated
    assert python_data["project_count"] == 2
