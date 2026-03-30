"""HTML artifact generation routes shared by portfolio and resume exports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from artifactminer.api.analyze import get_consent_level, get_user_email
from artifactminer.api.schemas import GenerateArtifactRequest
from artifactminer.api.views import get_prefs
from artifactminer.db import UploadedZip, get_db

router = APIRouter(prefix="/generate", tags=["generate"])


def _resolve_portfolio_context(db: Session, portfolio_id: str) -> dict[str, object]:
    normalized_portfolio_id = portfolio_id.strip()
    if not normalized_portfolio_id:
        raise HTTPException(status_code=422, detail="portfolio_id cannot be empty.")

    if (
        db.query(UploadedZip.id)
        .filter(UploadedZip.portfolio_id == normalized_portfolio_id)
        .first()
        is None
    ):
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    extraction_roots = sorted(
        {
            uploaded_zip.extraction_path.rstrip("/")
            for uploaded_zip in (
                db.query(UploadedZip)
                .filter(UploadedZip.portfolio_id == normalized_portfolio_id)
                .filter(UploadedZip.extraction_path.isnot(None))
                .order_by(UploadedZip.uploaded_at.asc())
                .all()
            )
            if uploaded_zip.extraction_path and uploaded_zip.extraction_path.strip()
        }
    )
    if not extraction_roots:
        raise HTTPException(
            status_code=400,
            detail="Portfolio has no analyzed ZIPs yet. Run /analyze/{zip_id} for uploaded ZIPs first.",
        )

    return {
        "portfolio_id": normalized_portfolio_id,
        "extraction_roots": extraction_roots,
        "preferences": get_prefs(db, normalized_portfolio_id),
        "consent_level": get_consent_level(db),
        "user_email": get_user_email(db),
    }


@router.post("/resume")
async def generate_resume_artifact(
    request: GenerateArtifactRequest,
    db: Session = Depends(get_db),
):
    _resolve_portfolio_context(db, request.portfolio_id)
    raise HTTPException(
        status_code=501,
        detail="Resume HTML generation is reserved for issue #510.",
    )


@router.post("/portfolio")
async def generate_portfolio_artifact(
    request: GenerateArtifactRequest,
    db: Session = Depends(get_db),
):
    _resolve_portfolio_context(db, request.portfolio_id)
    raise HTTPException(
        status_code=501,
        detail="Portfolio HTML generation is reserved for issue #511.",
    )
