"""
Consent API module: endpoints and helpers for consent state.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .schemas import ConsentResponse, ConsentUpdateRequest
from ..db import Consent, get_db


# Current required consent version for this app build.
CONSENT_VERSION = "v0"

router = APIRouter(tags=["consent"])


def _get_or_seed_consent(db: Session) -> Consent:
    """Return the single consent row; create a default if missing."""
    consent = db.get(Consent, 1)
    if consent is None:
        consent = Consent(id=1, accepted=False, version=CONSENT_VERSION, accepted_at=None)
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
    """Update consent state. Accept only the current app consent version when accepting.

    - If `accepted` is true, `version` must match the server's CONSENT_VERSION.
    - Sets `accepted_at` when accepting; clears it when revoking.
    """
    consent = _get_or_seed_consent(db)

    if payload.accepted and payload.version != CONSENT_VERSION:
        # Prevent accepting an outdated version of terms; return structured error detail
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONSENT_VERSION_MISMATCH",
                "message": "Consent version mismatch; update required",
                "server_version": CONSENT_VERSION,
            },
        )

    # Apply update
    if payload.accepted:
        consent.accepted = True
        consent.version = CONSENT_VERSION
        consent.accepted_at = datetime.now(UTC)
    else:
        consent.accepted = False
        consent.accepted_at = None

    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent
