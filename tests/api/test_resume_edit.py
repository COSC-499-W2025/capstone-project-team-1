"""Tests for POST /resume/{id}/edit endpoint."""

import pytest
from datetime import datetime, UTC
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
)


@pytest.fixture(scope="function")
def client_with_resume_item():
    """Test client with a single resume item for editing."""
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
        project_name="TestProject",
        project_path="/test",
        first_commit=datetime(2023, 1, 1),
        last_commit=now,
    )
    resume_item = ResumeItem(
        id=1,
        title="Original Title",
        content="Original content",
        category="Backend",
        repo_stat_id=1,
    )
    db.add_all([repo, resume_item])
    db.commit()
    db.close()

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_edit_resume_item_updates_fields(client_with_resume_item):
    """POST /resume/{id}/edit updates title, content, and category."""
    resp = client_with_resume_item.post(
        "/resume/1/edit",
        json={
            "title": "Updated Title",
            "content": "Updated content",
            "category": "Frontend",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == 1
    assert data["title"] == "Updated Title"
    assert data["content"] == "Updated content"
    assert data["category"] == "Frontend"
    assert data["project_name"] == "TestProject"


def test_edit_resume_item_partial_update(client_with_resume_item):
    """POST /resume/{id}/edit allows partial updates (only title)."""
    resp = client_with_resume_item.post(
        "/resume/1/edit",
        json={"title": "Only Title Changed"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["title"] == "Only Title Changed"
    assert data["content"] == "Original content"
    assert data["category"] == "Backend"


def test_edit_resume_item_not_found(client_with_resume_item):
    """POST /resume/{id}/edit returns 404 for nonexistent item."""
    resp = client_with_resume_item.post(
        "/resume/999/edit",
        json={"title": "Doesn't Matter"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Resume item not found"


def test_edit_resume_item_soft_deleted_project():
    """POST /resume/{id}/edit returns 404 when linked RepoStat is soft-deleted."""
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

    deleted_repo = RepoStat(
        id=2,
        project_name="DeletedProject",
        project_path="/deleted",
        first_commit=datetime(2023, 1, 1),
        last_commit=now,
        deleted_at=now,
    )
    resume_item_deleted = ResumeItem(
        id=2,
        title="Item on Deleted Project",
        content="Content",
        category="Backend",
        repo_stat_id=2,
    )
    db.add_all([deleted_repo, resume_item_deleted])
    db.commit()
    db.close()

    client = TestClient(app)
    try:
        resp = client.post(
            "/resume/2/edit",
            json={"title": "Should Fail"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Resume item not found"
    finally:
        app.dependency_overrides.clear()


def test_edit_resume_item_empty_request_rejected(client_with_resume_item):
    """POST /resume/{id}/edit returns 422 when no fields provided."""
    resp = client_with_resume_item.post(
        "/resume/1/edit",
        json={},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any(
        "at least one" in str(err).lower() or "validation error" in str(err).lower()
        for err in (detail if isinstance(detail, list) else [detail])
    )
