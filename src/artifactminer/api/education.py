"""API routes for Education and Award management."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from artifactminer.db import get_db
from artifactminer.db.models import Award, Education

from . import schemas

router = APIRouter(prefix="/education", tags=["education"])
awards_router = APIRouter(prefix="/awards", tags=["education"])
legacy_awards_router = APIRouter(prefix="/education/awards", tags=["education"])


def _delete_response(resource_name: str, deleted_id: int) -> schemas.DeleteResponse:
    return schemas.DeleteResponse(
        success=True,
        message=f"{resource_name} entry deleted",
        deleted_id=deleted_id,
    )


def _get_award_or_404(
    db: Session,
    award_id: int,
    portfolio_id: str | None = None,
) -> Award:
    query = db.query(Award).filter(Award.id == award_id)
    if portfolio_id is not None:
        query = query.filter(Award.portfolio_id == portfolio_id)
    entry = query.first()
    if not entry:
        raise HTTPException(status_code=404, detail="Award entry not found")
    return entry


# ============================================================================
# EDUCATION CRUD
# ============================================================================


@router.get("/", response_model=list[schemas.EducationResponse])
def list_education(
    portfolio_id: str = Query(..., description="Portfolio ID"),
    db: Session = Depends(get_db),
):
    """List all education entries for a portfolio."""
    return db.query(Education).filter(Education.portfolio_id == portfolio_id).all()


@router.get("/{education_id}", response_model=schemas.EducationResponse)
def get_education(
    education_id: int,
    portfolio_id: str | None = Query(
        None, description="Portfolio ID for ownership verification"
    ),
    db: Session = Depends(get_db),
):
    """Get a specific education entry by ID."""
    query = db.query(Education).filter(Education.id == education_id)
    if portfolio_id:
        query = query.filter(Education.portfolio_id == portfolio_id)
    entry = query.first()
    if not entry:
        raise HTTPException(status_code=404, detail="Education entry not found")
    return entry


@router.post("/", response_model=schemas.EducationResponse)
def create_education(
    request: schemas.EducationCreateRequest,
    portfolio_id: str = Query(..., description="Portfolio ID"),
    db: Session = Depends(get_db),
):
    """Create a new education entry."""
    entry = Education(
        portfolio_id=portfolio_id,
        institution=request.institution,
        degree=request.degree,
        field_of_study=request.field_of_study,
        start_date=request.start_date,
        end_date=request.end_date,
        gpa=request.gpa,
        honors=request.honors,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/{education_id}", response_model=schemas.EducationResponse)
def update_education(
    education_id: int,
    request: schemas.EducationCreateRequest,
    portfolio_id: str = Query(..., description="Portfolio ID for ownership verification"),
    db: Session = Depends(get_db),
):
    """Update an education entry. Verifies portfolio ownership."""
    entry = (
        db.query(Education)
        .filter(Education.id == education_id, Education.portfolio_id == portfolio_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Education entry not found")

    entry.institution = request.institution
    entry.degree = request.degree
    entry.field_of_study = request.field_of_study
    entry.start_date = request.start_date
    entry.end_date = request.end_date
    entry.gpa = request.gpa
    entry.honors = request.honors
    entry.updated_at = datetime.now(UTC).replace(tzinfo=None)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{education_id}", response_model=schemas.DeleteResponse)
def delete_education(
    education_id: int,
    portfolio_id: str = Query(..., description="Portfolio ID for ownership verification"),
    db: Session = Depends(get_db),
) -> schemas.DeleteResponse:
    """Delete an education entry. Verifies portfolio ownership."""
    entry = (
        db.query(Education)
        .filter(Education.id == education_id, Education.portfolio_id == portfolio_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Education entry not found")

    db.delete(entry)
    db.commit()
    return _delete_response("Education", education_id)


# ============================================================================
# AWARD CRUD
# ============================================================================


@awards_router.get("/", response_model=list[schemas.AwardResponse])
@legacy_awards_router.get("", response_model=list[schemas.AwardResponse], include_in_schema=False)
@legacy_awards_router.get("/", response_model=list[schemas.AwardResponse], include_in_schema=False)
def list_awards(
    portfolio_id: str = Query(..., description="Portfolio ID"),
    db: Session = Depends(get_db),
):
    """List all awards for a portfolio."""
    return db.query(Award).filter(Award.portfolio_id == portfolio_id).all()


@awards_router.get("/{award_id}", response_model=schemas.AwardResponse)
@legacy_awards_router.get(
    "/{award_id}",
    response_model=schemas.AwardResponse,
    include_in_schema=False,
)
def get_award(
    award_id: int,
    portfolio_id: str | None = Query(
        None, description="Portfolio ID for ownership verification"
    ),
    db: Session = Depends(get_db),
):
    """Get a specific award entry by ID."""
    return _get_award_or_404(db, award_id, portfolio_id)


@awards_router.post("/", response_model=schemas.AwardResponse)
@legacy_awards_router.post("", response_model=schemas.AwardResponse, include_in_schema=False)
@legacy_awards_router.post("/", response_model=schemas.AwardResponse, include_in_schema=False)
def create_award(
    request: schemas.AwardCreateRequest,
    portfolio_id: str = Query(..., description="Portfolio ID"),
    db: Session = Depends(get_db),
):
    """Create a new award entry."""
    entry = Award(
        portfolio_id=portfolio_id,
        title=request.title,
        issuer=request.issuer,
        date=request.date,
        description=request.description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@awards_router.put("/{award_id}", response_model=schemas.AwardResponse)
@legacy_awards_router.put(
    "/{award_id}",
    response_model=schemas.AwardResponse,
    include_in_schema=False,
)
def update_award(
    award_id: int,
    request: schemas.AwardCreateRequest,
    portfolio_id: str = Query(..., description="Portfolio ID for ownership verification"),
    db: Session = Depends(get_db),
):
    """Update an award entry. Verifies portfolio ownership."""
    entry = _get_award_or_404(db, award_id, portfolio_id)
    entry.title = request.title
    entry.issuer = request.issuer
    entry.date = request.date
    entry.description = request.description
    entry.updated_at = datetime.now(UTC).replace(tzinfo=None)

    db.commit()
    db.refresh(entry)
    return entry


@awards_router.delete("/{award_id}", response_model=schemas.DeleteResponse)
@legacy_awards_router.delete(
    "/{award_id}",
    response_model=schemas.DeleteResponse,
    include_in_schema=False,
)
def delete_award(
    award_id: int,
    portfolio_id: str = Query(..., description="Portfolio ID for ownership verification"),
    db: Session = Depends(get_db),
) -> schemas.DeleteResponse:
    """Delete an award entry. Verifies portfolio ownership."""
    entry = _get_award_or_404(db, award_id, portfolio_id)
    db.delete(entry)
    db.commit()
    return _delete_response("Award", award_id)
