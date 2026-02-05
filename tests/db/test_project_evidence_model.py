"""Tests for the ProjectEvidence database model.

Covers model creation, field constraints, relationships (RepoStat FK),
cascade deletion, and enum/type handling.

Written TDD-style for issue #339 – will fail until the model is implemented.
"""

from __future__ import annotations

from datetime import datetime, date, UTC

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.db import Base
from artifactminer.db.models import RepoStat


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """In-memory SQLite session with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def _make_evidence(project_id: int, **overrides):
    """Import ProjectEvidence inside the function so the import error
    surfaces clearly in the test output when the model doesn't exist yet."""
    from artifactminer.db.models import ProjectEvidence

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
# Model creation
# =========================================================================


class TestProjectEvidenceCreation:
    """Basic model instantiation and persistence."""

    def test_create_evidence_with_all_fields(self, db, sample_project):
        """Evidence row is created with all fields populated."""
        evidence = _make_evidence(
            sample_project.id,
            type="metric",
            content="10k downloads",
            source="App Store",
            date=date(2025, 3, 1),
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.id is not None
        assert evidence.repo_stat_id == sample_project.id
        assert evidence.type == "metric"
        assert evidence.content == "10k downloads"
        assert evidence.source == "App Store"
        assert evidence.date == date(2025, 3, 1)

    def test_create_evidence_minimal_fields(self, db, sample_project):
        """Evidence can be created with only required fields (type + content)."""
        evidence = _make_evidence(
            sample_project.id,
            type="feedback",
            content="Great work!",
            source=None,
            date=None,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.id is not None
        assert evidence.source is None
        assert evidence.date is None

    def test_create_evidence_all_types(self, db, sample_project):
        """All five evidence types can be persisted."""
        types = ["metric", "feedback", "evaluation", "award", "custom"]
        for t in types:
            ev = _make_evidence(sample_project.id, type=t, content=f"Content: {t}")
            db.add(ev)

        db.commit()

        from artifactminer.db.models import ProjectEvidence

        count = db.query(ProjectEvidence).count()
        assert count == 5

    def test_created_at_auto_set(self, db, sample_project):
        """created_at is automatically populated on insert."""
        evidence = _make_evidence(sample_project.id)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.created_at is not None
        assert isinstance(evidence.created_at, datetime)


# =========================================================================
# Relationships
# =========================================================================


class TestProjectEvidenceRelationships:
    """FK and relationship tests between ProjectEvidence and RepoStat."""

    def test_evidence_belongs_to_project(self, db, sample_project):
        """evidence.repo_stat resolves to the parent RepoStat."""
        evidence = _make_evidence(sample_project.id)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.repo_stat is not None
        assert evidence.repo_stat.id == sample_project.id
        assert evidence.repo_stat.project_name == "Test Project"

    def test_project_has_evidence_list(self, db, sample_project):
        """RepoStat.evidence returns all related evidence items."""
        db.add(_make_evidence(sample_project.id, content="Evidence 1"))
        db.add(_make_evidence(sample_project.id, content="Evidence 2"))
        db.commit()
        db.refresh(sample_project)

        assert hasattr(sample_project, "evidence")
        assert len(sample_project.evidence) == 2

    def test_evidence_fk_constraint(self, db):
        """Cannot create evidence for a nonexistent project (FK violation)."""
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
        from artifactminer.db.models import ProjectEvidence

        db.add(_make_evidence(sample_project.id, content="Cascade me"))
        db.commit()
        assert db.query(ProjectEvidence).count() == 1

        db.delete(sample_project)
        db.commit()

        assert db.query(ProjectEvidence).count() == 0

    def test_deleting_evidence_does_not_cascade_to_project(self, db, sample_project):
        """Deleting evidence does not remove the parent project."""
        evidence = _make_evidence(sample_project.id)
        db.add(evidence)
        db.commit()

        db.delete(evidence)
        db.commit()

        project = db.query(RepoStat).get(sample_project.id)
        assert project is not None


# =========================================================================
# Field constraints & edge cases
# =========================================================================


class TestProjectEvidenceConstraints:
    """Field-level validation and edge cases."""

    def test_content_not_nullable(self, db, sample_project):
        """Content column rejects NULL values."""
        evidence = _make_evidence(sample_project.id, content=None)
        db.add(evidence)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

    def test_type_not_nullable(self, db, sample_project):
        """Type column rejects NULL values."""
        evidence = _make_evidence(sample_project.id, type=None)
        db.add(evidence)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

    def test_long_content_accepted(self, db, sample_project):
        """Large content strings are stored correctly."""
        long_text = "X" * 10_000
        evidence = _make_evidence(sample_project.id, content=long_text)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.content == long_text

    def test_unicode_content(self, db, sample_project):
        """Unicode characters in content are preserved."""
        unicode_text = "성능 향상 40% — отличная работа 📈"
        evidence = _make_evidence(sample_project.id, content=unicode_text)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        assert evidence.content == unicode_text

    def test_multiple_evidence_same_type(self, db, sample_project):
        """Multiple evidence items of the same type are allowed."""
        db.add(_make_evidence(sample_project.id, type="metric", content="Metric 1"))
        db.add(_make_evidence(sample_project.id, type="metric", content="Metric 2"))
        db.commit()

        from artifactminer.db.models import ProjectEvidence

        metrics = (
            db.query(ProjectEvidence)
            .filter_by(repo_stat_id=sample_project.id, type="metric")
            .all()
        )
        assert len(metrics) == 2

    def test_evidence_date_stores_correctly(self, db, sample_project):
        """Date field stores and retrieves a date value."""
        target_date = date(2025, 12, 25)
        evidence = _make_evidence(sample_project.id, date=target_date)
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        # Depending on implementation, date may come back as date or datetime
        stored = evidence.date
        if isinstance(stored, datetime):
            assert stored.date() == target_date
        else:
            assert stored == target_date
