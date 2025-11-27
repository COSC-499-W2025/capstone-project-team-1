"""Persistence helpers for extracted skills and resume items."""

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
        # 1. Ensure the Master Skill exists
        skill_row = db.query(Skill).filter(Skill.name == sk.skill).first()
        if not skill_row:
            skill_row = Skill(name=sk.skill, category=sk.category)
            db.add(skill_row)
            db.flush() # Flush to get the ID

        # 2. Save to UserProjectSkill (if email provided) or ProjectSkill
        if normalized_email:
            # User-Specific Skill
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
                # Update existing
                proj_skill.proficiency = max((proj_skill.proficiency or 0.0), sk.proficiency)
                existing_evidence = set(proj_skill.evidence or [])
                merged = list(existing_evidence.union(sk.evidence))
                proj_skill.evidence = merged
            else:
                # Create new
                proj_skill = UserProjectSkill(
                    repo_stat_id=repo_stat_id,
                    skill_id=skill_row.id,
                    user_email=normalized_email,
                    proficiency=sk.proficiency,
                    evidence=list(sk.evidence),
                )
                db.add(proj_skill)
        else:
            # Generic Repo Skill
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
    return saved


# --- NEW FUNCTION FOR RESUME ITEMS ---

def persist_insights_as_resume_items(
    db,
    repo_stat_id: int,
    insights: List[Insight],
    commit: bool = True
):
    """Persist deep analysis insights to the ResumeItem table."""

    if not insights:
        return []

    # Verify Repo exists
    if not db.query(RepoStat).filter(RepoStat.id == repo_stat_id).first():
        raise ValueError(f"RepoStat {repo_stat_id} does not exist")

    saved_items = []
    
    for insight in insights:
        # Create a formatted string for the content
        # e.g. "Complexity Awareness: Resource caps... (Why: This matters because...)"
        content_text = f"{insight.title}: {' '.join(insight.evidence)}. {insight.why_it_matters}"
        
        # Check for duplicates (simple check based on title + repo)
        existing = db.query(ResumeItem).filter(
            ResumeItem.repo_stat_id == repo_stat_id,
            ResumeItem.title == insight.title
        ).first()

        if existing:
            # Update content if needed, or skip
            existing.content = content_text
            saved_items.append(existing)
        else:
            new_item = ResumeItem(
                repo_stat_id=repo_stat_id,
                title=insight.title,
                content=content_text,
                category="Deep Insight" # Or map from insight rules
            )
            db.add(new_item)
            saved_items.append(new_item)

    if commit:
        db.commit()
    
    return saved_items