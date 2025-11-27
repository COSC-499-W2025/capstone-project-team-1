"""Persistence helpers for extracted skills and resume items.

This module provides functions to save skill extraction and deep analysis
results to the database. It handles both repository-level skills (ProjectSkill)
and user-attributed skills (UserProjectSkill) for collaborative repos.
"""

from __future__ import annotations

from typing import List

from artifactminer.skills.models import ExtractedSkill
from artifactminer.skills.deep_analysis import Insight
from artifactminer.db.models import ResumeItem, RepoStat


def persist_extracted_skills(
    db,
    repo_stat_id: int,
    extracted: List[ExtractedSkill],
    *,
    user_email: str | None = None,
    commit: bool = True,
):
    """Persist extracted skills to the database.

    Saves skills to either ProjectSkill (repo-level) or UserProjectSkill
    (user-attributed) based on whether user_email is provided.

    Args:
        db: SQLAlchemy Session instance.
        repo_stat_id: Foreign key to the RepoStat being analyzed.
        extracted: List of ExtractedSkill objects from skill extraction.
        user_email: If provided, skills are attributed to this user via
            UserProjectSkill. Email is normalized (lowercase, stripped).
        commit: If True (default), commits the transaction. Set False to
            batch multiple operations before committing.

    Returns:
        List of created/updated ProjectSkill or UserProjectSkill objects.

    Raises:
        ValueError: If db is not a SQLAlchemy Session or RepoStat doesn't exist.
    """
    from sqlalchemy.orm import Session
    from artifactminer.db.models import Skill, ProjectSkill, RepoStat, UserProjectSkill

    if not isinstance(db, Session):
        raise ValueError("db must be a SQLAlchemy Session")

    if not db.query(RepoStat).filter(RepoStat.id == repo_stat_id).first():
        raise ValueError(f"RepoStat {repo_stat_id} does not exist")

    normalized_email = user_email.strip().lower() if user_email else None
    saved = []

    for sk in extracted:
        # Ensure the master Skill row exists (shared across all projects)
        skill_row = db.query(Skill).filter(Skill.name == sk.skill).first()
        if not skill_row:
            skill_row = Skill(name=sk.skill, category=sk.category)
            db.add(skill_row)
            db.flush()  # Get the ID before creating junction record

        # Route to UserProjectSkill or ProjectSkill based on email
        if normalized_email:
            proj_skill = (
                db.query(UserProjectSkill)
                .filter(
                    UserProjectSkill.repo_stat_id == repo_stat_id,
                    UserProjectSkill.skill_id == skill_row.id,
                    UserProjectSkill.user_email == normalized_email,
                )
                .first()
            )

            if proj_skill:
                # Merge: keep highest proficiency, union evidence
                proj_skill.proficiency = max(
                    (proj_skill.proficiency or 0.0), sk.proficiency
                )
                existing_evidence = set(proj_skill.evidence or [])
                proj_skill.evidence = list(existing_evidence.union(sk.evidence))
            else:
                proj_skill = UserProjectSkill(
                    repo_stat_id=repo_stat_id,
                    skill_id=skill_row.id,
                    user_email=normalized_email,
                    proficiency=sk.proficiency,
                    evidence=list(sk.evidence),
                )
                db.add(proj_skill)
        else:
            # Generic repo-level skill (no user attribution)
            proj_skill = (
                db.query(ProjectSkill)
                .filter(
                    ProjectSkill.repo_stat_id == repo_stat_id,
                    ProjectSkill.skill_id == skill_row.id,
                )
                .first()
            )

            if proj_skill:
                # Merge: keep highest proficiency, union evidence
                proj_skill.proficiency = max(
                    (proj_skill.proficiency or 0.0), sk.proficiency
                )
                existing_evidence = set(proj_skill.evidence or [])
                proj_skill.evidence = list(existing_evidence.union(sk.evidence))
            else:
                proj_skill = ProjectSkill(
                    repo_stat_id=repo_stat_id,
                    skill_id=skill_row.id,
                    proficiency=sk.proficiency,
                    evidence=list(sk.evidence),
                )
                db.add(proj_skill)

        saved.append(proj_skill)

    if commit:
        db.commit()
    return saved


def persist_insights_as_resume_items(
    db,
    repo_stat_id: int,
    insights: List[Insight],
    commit: bool = True,
):
    """Persist deep analysis insights as resume items.

    Converts Insight objects (from DeepRepoAnalyzer) into ResumeItem rows
    that can be used for resume generation.

    Args:
        db: SQLAlchemy Session instance.
        repo_stat_id: Foreign key to the RepoStat being analyzed.
        insights: List of Insight objects from deep analysis.
        commit: If True (default), commits the transaction.

    Returns:
        List of created/updated ResumeItem objects, or empty list if
        insights is empty.

    Raises:
        ValueError: If RepoStat doesn't exist.
    """
    if not insights:
        return []

    if not db.query(RepoStat).filter(RepoStat.id == repo_stat_id).first():
        raise ValueError(f"RepoStat {repo_stat_id} does not exist")

    saved_items = []

    for insight in insights:
        # Format: "Title: evidence1 evidence2. Why it matters"
        content_text = (
            f"{insight.title}: {' '.join(insight.evidence)}. {insight.why_it_matters}"
        )

        # Deduplicate by title within the same repo
        existing = (
            db.query(ResumeItem)
            .filter(
                ResumeItem.repo_stat_id == repo_stat_id,
                ResumeItem.title == insight.title,
            )
            .first()
        )

        if existing:
            existing.content = content_text
            saved_items.append(existing)
        else:
            new_item = ResumeItem(
                repo_stat_id=repo_stat_id,
                title=insight.title,
                content=content_text,
                category="Deep Insight",
            )
            db.add(new_item)
            saved_items.append(new_item)

    if commit:
        db.commit()

    return saved_items
