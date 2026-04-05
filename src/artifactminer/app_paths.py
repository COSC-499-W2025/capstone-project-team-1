"""Shared writable-path configuration for Artifact Miner runtime data."""

from __future__ import annotations

import os
from pathlib import Path


def _expand_path(value: str | Path) -> Path:
    return Path(value).expanduser()


APP_HOME = _expand_path(
    os.getenv("ARTIFACTMINER_HOME", Path.home() / ".artifactminer")
)
UPLOADS_DIR = _expand_path(
    os.getenv("ARTIFACTMINER_UPLOADS_DIR", APP_HOME / "uploads")
)
THUMBNAILS_DIR = _expand_path(
    os.getenv("ARTIFACTMINER_THUMBNAILS_DIR", UPLOADS_DIR / "thumbnails")
)
EXTRACTION_BASE_DIR = _expand_path(
    os.getenv("ARTIFACTMINER_EXTRACTION_DIR", APP_HOME / "extracted")
)
MODELS_DIR = _expand_path(
    os.getenv("ARTIFACTMINER_MODELS_DIR", APP_HOME / "models")
)
DATABASE_FILE = _expand_path(
    os.getenv("ARTIFACTMINER_DB_FILE", APP_HOME / "artifactminer.db")
)
DATABASE_URL = os.getenv("ARTIFACTMINER_DB", f"sqlite:///{DATABASE_FILE}")


def ensure_app_directories() -> None:
    """Create the writable directories the app expects to exist."""

    for path in (APP_HOME, UPLOADS_DIR, THUMBNAILS_DIR, EXTRACTION_BASE_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)
