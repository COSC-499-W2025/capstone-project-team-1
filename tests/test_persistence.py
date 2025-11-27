"""Tests for skill and insight persistence helpers."""

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


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def repo_stat(db_session):
    """Create a RepoStat for testing."""
    rs = RepoStat(project_name="test-project", is_collaborative=False)
    db_session.add(rs)
    db_session.commit()
    return rs


# --- persist_extracted_skills tests ---


def test_persist_extracted_skills_rejects_non_session_db():
    """Should raise ValueError when db is not a SQLAlchemy Session."""
    fake_db = {"not": "a session"}
    extracted = [ExtractedSkill(skill="Python", category="Language")]

    with pytest.raises(ValueError, match="db must be a SQLAlchemy Session"):
        persist_extracted_skills(fake_db, repo_stat_id=1, extracted=extracted)


def test_persist_extracted_skills_rejects_missing_repo_stat(db_session):
    """Should raise ValueError when RepoStat does not exist."""
    extracted = [ExtractedSkill(skill="Python", category="Language")]

    with pytest.raises(ValueError, match="RepoStat 999 does not exist"):
        persist_extracted_skills(db_session, repo_stat_id=999, extracted=extracted)


def test_persist_extracted_skills_creates_project_skill(db_session, repo_stat):
    """Basic flow: creates Skill and ProjectSkill when no user_email."""
    extracted = [
        ExtractedSkill(
            skill="Python",
            category="Language",
            evidence=["import os", "def main()"],
            proficiency=0.8,
        )
    ]

    saved = persist_extracted_skills(db_session, repo_stat.id, extracted)

    assert len(saved) == 1
    # Verify Skill was created
    skill = db_session.query(Skill).filter(Skill.name == "Python").first()
    assert skill is not None
    assert skill.category == "Language"

    # Verify ProjectSkill was created
    ps = (
        db_session.query(ProjectSkill)
        .filter(ProjectSkill.repo_stat_id == repo_stat.id)
        .first()
    )
    assert ps is not None
    assert ps.skill_id == skill.id
    assert ps.proficiency == 0.8
    assert set(ps.evidence) == {"import os", "def main()"}


def test_persist_extracted_skills_creates_user_project_skill(db_session, repo_stat):
    """Creates UserProjectSkill when user_email is provided."""
    extracted = [
        ExtractedSkill(
            skill="FastAPI",
            category="Framework",
            evidence=["from fastapi import FastAPI"],
            proficiency=0.7,
        )
    ]

    saved = persist_extracted_skills(
        db_session, repo_stat.id, extracted, user_email="  User@Example.COM  "
    )

    assert len(saved) == 1
    # Verify Skill was created
    skill = db_session.query(Skill).filter(Skill.name == "FastAPI").first()
    assert skill is not None

    # Verify UserProjectSkill with normalized email
    ups = (
        db_session.query(UserProjectSkill)
        .filter(UserProjectSkill.repo_stat_id == repo_stat.id)
        .first()
    )
    assert ups is not None
    assert ups.user_email == "user@example.com"  # normalized
    assert ups.skill_id == skill.id
    assert ups.proficiency == 0.7


def test_persist_extracted_skills_updates_existing_project_skill(db_session, repo_stat):
    """Updates existing ProjectSkill: max proficiency, merged evidence."""
    # First insertion
    extracted1 = [
        ExtractedSkill(
            skill="SQL",
            category="Database",
            evidence=["SELECT * FROM users"],
            proficiency=0.5,
        )
    ]
    persist_extracted_skills(db_session, repo_stat.id, extracted1)

    # Second insertion with higher proficiency and new evidence
    extracted2 = [
        ExtractedSkill(
            skill="SQL",
            category="Database",
            evidence=["INSERT INTO logs", "SELECT * FROM users"],  # one duplicate
            proficiency=0.9,
        )
    ]
    persist_extracted_skills(db_session, repo_stat.id, extracted2)

    # Should only have one ProjectSkill
    skills = (
        db_session.query(ProjectSkill)
        .filter(ProjectSkill.repo_stat_id == repo_stat.id)
        .all()
    )
    assert len(skills) == 1

    ps = skills[0]
    assert ps.proficiency == 0.9  # max of 0.5 and 0.9
    assert set(ps.evidence) == {"SELECT * FROM users", "INSERT INTO logs"}


def test_persist_extracted_skills_updates_existing_user_project_skill(
    db_session, repo_stat
):
    """Updates existing UserProjectSkill: max proficiency, merged evidence."""
    email = "dev@test.com"

    # First insertion
    extracted1 = [
        ExtractedSkill(
            skill="React",
            category="Framework",
            evidence=["import React"],
            proficiency=0.4,
        )
    ]
    persist_extracted_skills(db_session, repo_stat.id, extracted1, user_email=email)

    # Second insertion
    extracted2 = [
        ExtractedSkill(
            skill="React",
            category="Framework",
            evidence=["useState", "import React"],  # one duplicate
            proficiency=0.6,
        )
    ]
    persist_extracted_skills(db_session, repo_stat.id, extracted2, user_email=email)

    # Should only have one UserProjectSkill
    skills = (
        db_session.query(UserProjectSkill)
        .filter(
            UserProjectSkill.repo_stat_id == repo_stat.id,
            UserProjectSkill.user_email == email,
        )
        .all()
    )
    assert len(skills) == 1

    ups = skills[0]
    assert ups.proficiency == 0.6
    assert set(ups.evidence) == {"import React", "useState"}


def test_persist_extracted_skills_commit_false_defers_commit(db_session, repo_stat):
    """With commit=False, changes are not committed."""
    extracted = [ExtractedSkill(skill="Go", category="Language", proficiency=0.5)]

    persist_extracted_skills(db_session, repo_stat.id, extracted, commit=False)

    # Rollback to see if data was committed
    db_session.rollback()

    # Should not find the skill after rollback
    skill = db_session.query(Skill).filter(Skill.name == "Go").first()
    assert skill is None


def test_persist_extracted_skills_multiple_skills(db_session, repo_stat):
    """Persists multiple skills in one call."""
    extracted = [
        ExtractedSkill(skill="Python", category="Language", proficiency=0.8),
        ExtractedSkill(skill="FastAPI", category="Framework", proficiency=0.7),
        ExtractedSkill(skill="SQL", category="Database", proficiency=0.6),
    ]

    saved = persist_extracted_skills(db_session, repo_stat.id, extracted)

    assert len(saved) == 3
    skill_names = {s.skill.name for s in saved}
    assert skill_names == {"Python", "FastAPI", "SQL"}


def test_persist_extracted_skills_reuses_existing_skill(db_session, repo_stat):
    """Reuses existing Skill row instead of creating duplicate."""
    # Pre-create a skill
    existing_skill = Skill(name="Docker", category="DevOps")
    db_session.add(existing_skill)
    db_session.commit()

    extracted = [ExtractedSkill(skill="Docker", category="DevOps", proficiency=0.9)]
    persist_extracted_skills(db_session, repo_stat.id, extracted)

    # Should still only have one Skill named Docker
    docker_skills = db_session.query(Skill).filter(Skill.name == "Docker").all()
    assert len(docker_skills) == 1
    assert docker_skills[0].id == existing_skill.id


# --- persist_insights_as_resume_items tests ---


def test_persist_insights_empty_list_returns_early(db_session, repo_stat):
    """Empty insights list returns empty immediately without DB queries."""
    result = persist_insights_as_resume_items(db_session, repo_stat.id, [])
    assert result == []


def test_persist_insights_rejects_missing_repo_stat(db_session):
    """Should raise ValueError when RepoStat does not exist."""
    insights = [Insight(title="Test", evidence=["ev1"], why_it_matters="matters")]

    with pytest.raises(ValueError, match="RepoStat 999 does not exist"):
        persist_insights_as_resume_items(
            db_session, repo_stat_id=999, insights=insights
        )


def test_persist_insights_creates_resume_item(db_session, repo_stat):
    """Basic flow: creates ResumeItem from Insight."""
    insights = [
        Insight(
            title="Complexity awareness",
            evidence=["Resource caps", "Chunking logic"],
            why_it_matters="Shows attention to performance",
        )
    ]

    saved = persist_insights_as_resume_items(db_session, repo_stat.id, insights)

    assert len(saved) == 1
    item = (
        db_session.query(ResumeItem)
        .filter(ResumeItem.repo_stat_id == repo_stat.id)
        .first()
    )
    assert item is not None
    assert item.title == "Complexity awareness"
    assert "Resource caps" in item.content
    assert "Chunking logic" in item.content
    assert "Shows attention to performance" in item.content
    assert item.category == "Deep Insight"


def test_persist_insights_updates_existing_by_title(db_session, repo_stat):
    """Updates existing ResumeItem when title matches (dedup)."""
    # First insertion
    insights1 = [
        Insight(
            title="API design",
            evidence=["REST endpoints"],
            why_it_matters="Good API",
        )
    ]
    persist_insights_as_resume_items(db_session, repo_stat.id, insights1)

    # Second insertion with same title but different content
    insights2 = [
        Insight(
            title="API design",
            evidence=["GraphQL schema", "OpenAPI spec"],
            why_it_matters="Modern API patterns",
        )
    ]
    persist_insights_as_resume_items(db_session, repo_stat.id, insights2)

    # Should only have one ResumeItem
    items = (
        db_session.query(ResumeItem)
        .filter(
            ResumeItem.repo_stat_id == repo_stat.id,
            ResumeItem.title == "API design",
        )
        .all()
    )
    assert len(items) == 1

    # Content should be updated
    assert "GraphQL schema" in items[0].content
    assert "Modern API patterns" in items[0].content


def test_persist_insights_multiple_insights(db_session, repo_stat):
    """Persists multiple insights in one call."""
    insights = [
        Insight(title="Insight A", evidence=["ev1"], why_it_matters="why A"),
        Insight(title="Insight B", evidence=["ev2"], why_it_matters="why B"),
        Insight(title="Insight C", evidence=["ev3"], why_it_matters="why C"),
    ]

    saved = persist_insights_as_resume_items(db_session, repo_stat.id, insights)

    assert len(saved) == 3
    titles = {item.title for item in saved}
    assert titles == {"Insight A", "Insight B", "Insight C"}


def test_persist_insights_commit_false_defers_commit(db_session, repo_stat):
    """With commit=False, changes are not committed."""
    insights = [Insight(title="Deferred", evidence=["test"], why_it_matters="test")]

    persist_insights_as_resume_items(db_session, repo_stat.id, insights, commit=False)

    # Rollback to see if data was committed
    db_session.rollback()

    # Should not find the item after rollback
    item = db_session.query(ResumeItem).filter(ResumeItem.title == "Deferred").first()
    assert item is None
