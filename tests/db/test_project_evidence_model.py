"""Tests for the ProjectEvidence database model.

Covers creation, relationships, cascade deletion, and NOT NULL constraints.
"""

from __future__ import annotations

from datetime import datetime, date, UTC

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.db import Base
from artifactminer.db.models import RepoStat, ProjectEvidence


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """In-memory SQLite session with FK enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def sample_project(db) -> RepoStat:
    """Create and return a persisted RepoStat row."""
    project = RepoStat(
        project_name="Test Project",
        project_path="/mock/test-project",
        is_collaborative=False,
        primary_language="Python",
        languages=["Python"],
        first_commit=datetime(2024, 1, 1),
        last_commit=datetime(2025, 6, 1),
        total_commits=100,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _make_evidence(project_id: int = 0, **overrides):
    """Build a ProjectEvidence instance with sensible defaults."""
    defaults = {
        "repo_stat_id": project_id,
        "type": "metric",
        "content": "Reduced latency by 35%",
        "source": "APM dashboard",
        "date": date(2025, 6, 15),
    }
    defaults.update(overrides)
    return ProjectEvidence(**defaults)


# =========================================================================
# Creation
# =========================================================================


class TestProjectEvidenceCreation:
    """Basic model instantiation and persistence."""

    def test_create_with_all_fields(self, db, sample_project):
        """Evidence row is created with all fields populated."""
        evidence = _make_evidence(
            sample_project.id,
            content="10k downloads",
            source="App Store",
            date=date(2025, 3, 1),
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.id is not None
        assert evidence.repo_stat_id == sample_project.id
        assert evidence.content == "10k downloads"
        assert evidence.source == "App Store"
        assert evidence.date == date(2025, 3, 1)
        assert isinstance(evidence.created_at, datetime)

    def test_create_with_minimal_fields(self, db, sample_project):
        """Evidence can be created with only required fields."""
        evidence = _make_evidence(sample_project.id, source=None, date=None)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.id is not None
        assert evidence.source is None
        assert evidence.date is None


# =========================================================================
# Relationships
# =========================================================================


class TestProjectEvidenceRelationships:
    """FK and relationship tests."""

    def test_evidence_belongs_to_project(self, db, sample_project):
        """evidence.repo_stat resolves to the parent RepoStat."""
        evidence = _make_evidence(sample_project.id)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.repo_stat.id == sample_project.id

    def test_project_has_evidence_list(self, db, sample_project):
        """RepoStat.evidence returns all related evidence items."""
        db.add(_make_evidence(sample_project.id, content="Evidence 1"))
        db.add(_make_evidence(sample_project.id, content="Evidence 2"))
        db.commit()
        db.refresh(sample_project)

        assert len(sample_project.evidence) == 2

    def test_fk_constraint(self, db):
        """Cannot create evidence for a nonexistent project."""
        evidence = _make_evidence(repo_stat_id=99999)
        db.add(evidence)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()


# =========================================================================
# Cascade deletion
# =========================================================================


class TestProjectEvidenceCascade:
    """Cascade behaviour when the parent project is deleted."""

    def test_cascade_delete_removes_evidence(self, db, sample_project):
        """Deleting a RepoStat cascades to its evidence rows."""
        db.add(_make_evidence(sample_project.id))
        db.commit()

        db.delete(sample_project)
        db.commit()

        assert db.query(ProjectEvidence).count() == 0

    def test_deleting_evidence_preserves_project(self, db, sample_project):
        """Deleting evidence does not remove the parent project."""
        evidence = _make_evidence(sample_project.id)
        db.add(evidence)
        db.commit()

        db.delete(evidence)
        db.commit()

        assert db.get(RepoStat, sample_project.id) is not None


# =========================================================================
# Constraints
# =========================================================================


class TestProjectEvidenceConstraints:
    """NOT NULL constraint tests."""

    def test_content_not_nullable(self, db, sample_project):
        """Content column rejects NULL values."""
        evidence = _make_evidence(sample_project.id, content=None)
        db.add(evidence)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()
