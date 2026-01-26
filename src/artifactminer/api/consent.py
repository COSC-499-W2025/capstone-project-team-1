"""
Consent API module: endpoints and helpers for consent state.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .schemas import ConsentResponse, ConsentUpdateRequest
from ..db import Consent, get_db


router = APIRouter(tags=["consent"])


def _get_or_seed_consent(db: Session) -> Consent:
    """Return the single consent row; create a default if missing."""
    consent = db.get(Consent, 1)
    if consent is None:
        consent = Consent(id=1, consent_level="none", accepted_at=None)
        db.add(consent)
        db.commit()
        db.refresh(consent)
    return consent


@router.get("/consent", response_model=ConsentResponse)
async def get_consent(db: Session = Depends(get_db)) -> ConsentResponse:
    """Fetch current consent state; seed a default row if it doesn't exist."""
    consent = _get_or_seed_consent(db)
    return consent


@router.put("/consent", response_model=ConsentResponse)
async def update_consent(payload: ConsentUpdateRequest, db: Session = Depends(get_db)) -> ConsentResponse:
    """Update consent state with the selected consent level."""
    consent = _get_or_seed_consent(db)

    consent.consent_level = payload.consent_level
    
    if payload.consent_level in ("full", "no_llm"):
        consent.accepted_at = datetime.now(UTC).replace(tzinfo=None)
    else:
        consent.accepted_at = None

    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent
