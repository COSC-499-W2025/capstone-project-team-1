"""
Views API module: endpoints for portfolio representation preferences.
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .schemas import RepresentationPreferences
from ..db import RepresentationPrefs, get_db


router = APIRouter(prefix="/views", tags=["views"])


def get_prefs(db: Session, portfolio_id: str) -> RepresentationPreferences:
    """Retrieve preferences for a portfolio; return defaults if not found."""
    row = db.get(RepresentationPrefs, portfolio_id)
    if row is None:
        return RepresentationPreferences()
    try:
        data = json.loads(row.prefs_json)
        return RepresentationPreferences(**data)
    except (json.JSONDecodeError, TypeError):
        return RepresentationPreferences()


def save_prefs(
    db: Session, portfolio_id: str, prefs: RepresentationPreferences
) -> RepresentationPreferences:
    """Upsert preferences for a portfolio."""
    row = db.get(RepresentationPrefs, portfolio_id)
    prefs_json = json.dumps(prefs.model_dump())

    if row is None:
        row = RepresentationPrefs(
            portfolio_id=portfolio_id,
            prefs_json=prefs_json,
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(row)
    else:
        row.prefs_json = prefs_json
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)

    db.commit()
    db.refresh(row)
    return prefs


@router.get("/{portfolio_id}/prefs", response_model=RepresentationPreferences)
async def get_representation_prefs(
    portfolio_id: str, db: Session = Depends(get_db)
) -> RepresentationPreferences:
    """Fetch representation preferences for a portfolio; returns defaults if not set."""
    return get_prefs(db, portfolio_id)


@router.put("/{portfolio_id}/prefs", response_model=RepresentationPreferences)
async def update_representation_prefs(
    portfolio_id: str,
    payload: RepresentationPreferences,
    db: Session = Depends(get_db),
) -> RepresentationPreferences:
    """Update representation preferences for a portfolio."""
    return save_prefs(db, portfolio_id, payload)
