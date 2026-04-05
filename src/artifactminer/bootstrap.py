"""Shared startup helpers for preparing the local database state."""

from __future__ import annotations

from pathlib import Path

from artifactminer.app_paths import ensure_app_directories
from artifactminer.db import SessionLocal, seed_questions


def ensure_database_ready() -> None:
    """Create writable directories, apply migrations, and seed baseline rows."""

    ensure_app_directories()

    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig

    repo_root = Path(__file__).resolve().parents[2]
    alembic_cfg = AlembicConfig(str(repo_root / "alembic.ini"))
    alembic_command.upgrade(alembic_cfg, "head")

    db = SessionLocal()
    try:
        seed_questions(db)
    finally:
        db.close()
