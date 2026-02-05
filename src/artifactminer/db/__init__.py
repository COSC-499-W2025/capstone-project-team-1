"""Database module exposing models, session management, and utilities."""

from .database import Base, engine, SessionLocal, get_db
from .models import (
    Artifact,
    Question,
    Consent,
    UserAnswer,
    UploadedZip,
    RepoStat,
    UserRepoStat,
    Skill,
    ProjectSkill,
    UserProjectSkill,
    ResumeItem,
    UserAIntelligenceSummary,
    ProjectEvidence,
    RepresentationPrefs,
)
from .seed import seed_questions, seed_repo_stats

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "Artifact",
    "Question",
    "Consent",
    "UserAnswer",
    "UploadedZip",
    "RepoStat",
    "UserRepoStat",
    "Skill",
    "ProjectSkill",
    "UserProjectSkill",
    "ResumeItem",
    "UserAIntelligenceSummary",
    "ProjectEvidence",
    "RepresentationPrefs",
    "seed_questions",
    "seed_repo_stats",
]
