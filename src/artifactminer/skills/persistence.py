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
    """Persist extracted skills to Skill/ProjectSkill or UserProjectSkill tables."""
    from sqlalchemy.orm import Session
    from artifactminer.db.models import Skill, ProjectSkill, RepoStat, UserProjectSkill

    if not isinstance(db, Session):
        raise ValueError("db must be a SQLAlchemy Session")

    if not db.query(RepoStat).filter(RepoStat.id == repo_stat_id).first():
        raise ValueError(f"RepoStat {repo_stat_id} does not exist")

    normalized_email = user_email.strip().lower() if user_email else None
    saved = []
    for sk in extracted:
        skill_row = db.query(Skill).filter(Skill.name == sk.skill).first()
        if not skill_row:
            skill_row = Skill(name=sk.skill, category=sk.category)
            db.add(skill_row)
            db.flush()

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
                proj_skill.proficiency = max((proj_skill.proficiency or 0.0), sk.proficiency)
                existing_evidence = set(proj_skill.evidence or [])
                merged = list(existing_evidence.union(sk.evidence))
                proj_skill.evidence = merged
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
            proj_skill = (
                db.query(ProjectSkill)
                .filter(
                    ProjectSkill.repo_stat_id == repo_stat_id,
                    ProjectSkill.skill_id == skill_row.id,
                )
                .first()
            )

            if proj_skill:
                proj_skill.proficiency = max((proj_skill.proficiency or 0.0), sk.proficiency)
                existing_evidence = set(proj_skill.evidence or [])
                merged = list(existing_evidence.union(sk.evidence))
                proj_skill.evidence = merged
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
    for ps in saved:
        db.refresh(ps)
    return saved
