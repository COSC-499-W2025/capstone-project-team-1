"""Persistence helpers for extracted skills."""

from __future__ import annotations

from typing import List

from artifactminer.skills.models import ExtractedSkill


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
