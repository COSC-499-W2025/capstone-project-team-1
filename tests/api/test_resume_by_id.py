"""Tests for GET /resume/{id} endpoint."""

import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from artifactminer.api.app import create_app
from artifactminer.db import Base, get_db, RepoStat, ResumeItem


@pytest.fixture(scope="function")
def client_with_data():
    """Test client with seeded resume data including project associations."""
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

    repos = [
        RepoStat(
            id=1,
            project_name="BackendProject",
            project_path="/repos/backend",
            first_commit=datetime(2023, 1, 15),
            last_commit=datetime(2023, 6, 20),
        ),
        RepoStat(
            id=2,
            project_name="FrontendProject",
            project_path="/repos/frontend",
            first_commit=datetime(2023, 3, 1),
            last_commit=now - timedelta(days=5),
        ),
    ]
    resume_items = [
        ResumeItem(
            id=1,
            title="Built REST API",
            content="Developed FastAPI backend with authentication",
            category="Backend",
            repo_stat_id=1,
        ),
        ResumeItem(
            id=2,
            title="React Dashboard",
            content="Created interactive dashboard with charts",
            category="Frontend",
            repo_stat_id=2,
        ),
        ResumeItem(
            id=3,
            title="Database Design",
            content="Designed normalized schema for user data",
            category="Backend",
            repo_stat_id=1,
        ),
    ]
    db.add_all(repos + resume_items)
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


@pytest.fixture(scope="function")
def client_with_orphan_resume():
    """Test client with resume item that has no associated project."""
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

    db = TestingSessionLocal()
    resume_item = ResumeItem(
        id=1,
        title="Standalone Achievement",
        content="Independent project not linked to repo",
        category="Other",
        repo_stat_id=None,  # No associated project
    )
    db.add(resume_item)
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client_with_soft_deleted_project():
    """Test client with resume item whose project is soft-deleted."""
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

    db = TestingSessionLocal()
    now = datetime.now(UTC).replace(tzinfo=None)

    repo = RepoStat(
        id=1,
        project_name="DeletedProject",
        project_path="/repos/deleted",
        first_commit=datetime(2023, 1, 1),
        last_commit=datetime(2023, 6, 1),
        deleted_at=now,  # Soft-deleted
    )
    resume_item = ResumeItem(
        id=1,
        title="Work on Deleted Project",
        content="This project was later deleted",
        category="Backend",
        repo_stat_id=1,
    )
    db.add_all([repo, resume_item])
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


# === GET /resume/{id} Success Tests ===


def test_get_resume_by_id_success(client_with_data):
    """GET /resume/{id} returns 200 and correct resume item for valid ID."""
    response = client_with_data.get("/resume/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Built REST API"


def test_get_resume_by_id_response_fields(client_with_data):
    """Response includes all required fields: id, title, content, category, project_name, created_at."""
    response = client_with_data.get("/resume/1")

    assert response.status_code == 200
    data = response.json()

    # All required fields per ResumeItemResponse schema
    assert "id" in data
    assert "title" in data
    assert "content" in data
    assert "category" in data
    assert "project_name" in data
    assert "created_at" in data


def test_get_resume_by_id_includes_project_info(client_with_data):
    """Returns associated project name when resume has repo_stat_id."""
    response = client_with_data.get("/resume/1")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "BackendProject"


# === GET /resume/{id} Error Tests ===


def test_get_resume_by_id_not_found(client_with_data):
    """Returns 404 with detail 'Resume item not found' for nonexistent ID."""
    response = client_with_data.get("/resume/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume item not found"


def test_get_resume_by_id_invalid_id(client_with_data):
    """Returns 422 for invalid ID format (e.g., string instead of int)."""
    response = client_with_data.get("/resume/not-a-number")

    assert response.status_code == 422


# === GET /resume/{id} Edge Cases ===


def test_get_resume_by_id_soft_deleted_project(client_with_soft_deleted_project):
    """Returns 404 when associated project is soft-deleted."""
    response = client_with_soft_deleted_project.get("/resume/1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume item not found"


def test_get_resume_by_id_null_project(client_with_orphan_resume):
    """Returns resume item with project_name: null when no associated project."""
    response = client_with_orphan_resume.get("/resume/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Standalone Achievement"
    assert data["project_name"] is None


def test_get_resume_by_id_zero_id(client_with_data):
    """Returns 422 for ID=0 due to Path(gt=0) validation."""
    response = client_with_data.get("/resume/0")

    assert response.status_code == 422


def test_get_resume_by_id_negative_id(client_with_data):
    """Returns 422 for negative IDs due to Path(gt=0) validation."""
    response = client_with_data.get("/resume/-1")

    assert response.status_code == 422


# === Data Integrity Tests ===


def test_get_resume_by_id_correct_content(client_with_data):
    """Returned content matches seeded data exactly."""
    response = client_with_data.get("/resume/2")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 2
    assert data["title"] == "React Dashboard"
    assert data["content"] == "Created interactive dashboard with charts"
    assert data["category"] == "Frontend"
    assert data["project_name"] == "FrontendProject"


def test_get_resume_by_id_different_items(client_with_data):
    """Different IDs return different resume items."""
    response1 = client_with_data.get("/resume/1")
    response2 = client_with_data.get("/resume/2")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    assert data1["id"] != data2["id"]
    assert data1["title"] != data2["title"]
    assert data1["project_name"] != data2["project_name"]


# === Empty Database Test ===


def test_get_resume_by_id_empty_database(client_empty):
    """Returns 404 when database is empty."""
    response = client_empty.get("/resume/1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Resume item not found"
