"""Tests for skill and insight persistence helpers.

Tests cover:
- persist_extracted_skills: saves ExtractedSkill to ProjectSkill or UserProjectSkill
- persist_insights_as_resume_items: saves Insight to ResumeItem
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from artifactminer.db import Base
from artifactminer.db.models import (
    RepoStat,
    Skill,
    ProjectSkill,
    UserProjectSkill,
    ResumeItem,
)
from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.deep_analysis import Insight
from artifactminer.skills.persistence import (
    persist_extracted_skills,
    persist_insights_as_resume_items,
)


# --- Fixtures ---


@pytest.fixture
def db_session():
    """In-memory SQLite session, created fresh per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def repo_stat(db_session):
    """Pre-populated RepoStat for foreign key references."""
    rs = RepoStat(project_name="test-project", is_collaborative=False)
    db_session.add(rs)
    db_session.commit()
    return rs


# --- persist_extracted_skills tests ---


def test_persist_skills_validation_errors(db_session):
    """Rejects invalid db type and missing RepoStat."""
    extracted = [ExtractedSkill(skill="Python", category="Language")]

    # Non-session db
    with pytest.raises(ValueError, match="db must be a SQLAlchemy Session"):
        persist_extracted_skills({"fake": "db"}, repo_stat_id=1, extracted=extracted)

    # Missing RepoStat
    with pytest.raises(ValueError, match="RepoStat 999 does not exist"):
        persist_extracted_skills(db_session, repo_stat_id=999, extracted=extracted)


def test_persist_skills_creates_project_skill(db_session, repo_stat):
    """Creates Skill + ProjectSkill when no user_email provided."""
    extracted = [
        ExtractedSkill(
            skill="Python", category="Language", evidence=["import os"], proficiency=0.8
        )
    ]
    saved = persist_extracted_skills(db_session, repo_stat.id, extracted)

    assert len(saved) == 1
    skill = db_session.query(Skill).filter(Skill.name == "Python").first()
    ps = (
        db_session.query(ProjectSkill)
        .filter(ProjectSkill.repo_stat_id == repo_stat.id)
        .first()
    )

    assert skill and skill.category == "Language"
    assert ps and ps.proficiency == 0.8 and "import os" in ps.evidence


def test_persist_skills_creates_user_project_skill(db_session, repo_stat):
    """Creates UserProjectSkill with normalized email when user_email provided."""
    extracted = [
        ExtractedSkill(
            skill="FastAPI", category="Framework", evidence=["fastapi"], proficiency=0.7
        )
    ]
    persist_extracted_skills(
        db_session, repo_stat.id, extracted, user_email="  User@Test.COM  "
    )

    ups = (
        db_session.query(UserProjectSkill)
        .filter(UserProjectSkill.repo_stat_id == repo_stat.id)
        .first()
    )

    assert ups and ups.user_email == "user@test.com" and ups.proficiency == 0.7


def test_persist_skills_updates_existing(db_session, repo_stat):
    """Updates existing skill: takes max proficiency, merges evidence."""
    # First insert
    persist_extracted_skills(
        db_session,
        repo_stat.id,
        [
            ExtractedSkill(
                skill="SQL", category="DB", evidence=["SELECT"], proficiency=0.5
            )
        ],
    )
    # Second insert with higher proficiency + new evidence
    persist_extracted_skills(
        db_session,
        repo_stat.id,
        [
            ExtractedSkill(
                skill="SQL",
                category="DB",
                evidence=["INSERT", "SELECT"],
                proficiency=0.9,
            )
        ],
    )

    skills = (
        db_session.query(ProjectSkill)
        .filter(ProjectSkill.repo_stat_id == repo_stat.id)
        .all()
    )
    assert len(skills) == 1
    assert skills[0].proficiency == 0.9
    assert set(skills[0].evidence) == {"SELECT", "INSERT"}


def test_persist_skills_reuses_existing_skill_row(db_session, repo_stat):
    """Reuses existing Skill row instead of creating duplicate."""
    existing = Skill(name="Docker", category="DevOps")
    db_session.add(existing)
    db_session.commit()

    persist_extracted_skills(
        db_session,
        repo_stat.id,
        [ExtractedSkill(skill="Docker", category="DevOps", proficiency=0.9)],
    )

    assert db_session.query(Skill).filter(Skill.name == "Docker").count() == 1


def test_persist_skills_commit_false(db_session, repo_stat):
    """commit=False defers commit; rollback discards changes."""
    persist_extracted_skills(
        db_session,
        repo_stat.id,
        [ExtractedSkill(skill="Go", category="Language")],
        commit=False,
    )
    db_session.rollback()

    assert db_session.query(Skill).filter(Skill.name == "Go").first() is None


# --- persist_insights_as_resume_items tests ---


def test_persist_insights_validation(db_session, repo_stat):
    """Empty list returns early; missing RepoStat raises."""
    assert persist_insights_as_resume_items(db_session, repo_stat.id, []) == []

    with pytest.raises(ValueError, match="RepoStat 999 does not exist"):
        persist_insights_as_resume_items(
            db_session, 999, [Insight(title="X", evidence=["e"], why_it_matters="w")]
        )


def test_persist_insights_creates_resume_item(db_session, repo_stat):
    """Creates ResumeItem from Insight with formatted content."""
    insights = [
        Insight(
            title="Complexity",
            evidence=["caps", "chunks"],
            why_it_matters="perf matters",
        )
    ]
    saved = persist_insights_as_resume_items(db_session, repo_stat.id, insights)

    assert len(saved) == 1
    item = (
        db_session.query(ResumeItem)
        .filter(ResumeItem.repo_stat_id == repo_stat.id)
        .first()
    )
    assert item and item.title == "Complexity" and item.category == "Deep Insight"
    assert "caps" in item.content and "perf matters" in item.content


def test_persist_insights_updates_existing_by_title(db_session, repo_stat):
    """Updates existing ResumeItem when title matches (dedup by title)."""
    persist_insights_as_resume_items(
        db_session,
        repo_stat.id,
        [Insight(title="API", evidence=["REST"], why_it_matters="v1")],
    )
    persist_insights_as_resume_items(
        db_session,
        repo_stat.id,
        [Insight(title="API", evidence=["GraphQL"], why_it_matters="v2")],
    )

    items = db_session.query(ResumeItem).filter(ResumeItem.title == "API").all()
    assert len(items) == 1 and "GraphQL" in items[0].content


def test_persist_insights_commit_false(db_session, repo_stat):
    """commit=False defers commit; rollback discards changes."""
    persist_insights_as_resume_items(
        db_session,
        repo_stat.id,
        [Insight(title="Temp", evidence=["x"], why_it_matters="y")],
        commit=False,
    )
    db_session.rollback()

    assert (
        db_session.query(ResumeItem).filter(ResumeItem.title == "Temp").first() is None
    )
