/"""ZIP upload endpoints and helpers."""

from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from artifactminer.api.analyze import extract_zip_to_persistent_location
from artifactminer.directorycrawler import directory_walk

from .schemas import (
    ZipUploadResponse,
    DirectoriesResponse,
    PortfolioResponse,
    PortfolioZipItem,
)
from ..db import UploadedZip, get_db


UPLOADS_DIR = Path("./uploads")


router = APIRouter(prefix="/zip", tags=["zip"])


@router.post("/upload", response_model=ZipUploadResponse)
async def upload_zip(
    file: UploadFile = File(...),
    portfolio_id: str | None = Query(
        default=None,
        description="Optional portfolio UUID to link this ZIP to an existing portfolio.",
    ),
    db: Session = Depends(get_db),
) -> ZipUploadResponse:
    """Accept a ZIP file upload and track metadata in the database.

    If portfolio_id is provided, links the ZIP to an existing portfolio.
    If not provided, generates a new portfolio UUID.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=422, detail="Only ZIP files are allowed.")

    upload_dir = UPLOADS_DIR
    upload_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    normalized_name = Path(file.filename).name
    safe_filename = f"{timestamp}_{normalized_name}"
    file_path = upload_dir / safe_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate new portfolio_id if not provided
    if portfolio_id is None:
        portfolio_id = str(uuid.uuid4())

    uploaded_zip = UploadedZip(
        filename=file.filename,
        path=str(file_path),
        portfolio_id=portfolio_id,
    )
    db.add(uploaded_zip)
    db.commit()
    db.refresh(uploaded_zip)

    return ZipUploadResponse(
        zip_id=uploaded_zip.id,
        filename=uploaded_zip.filename,
        portfolio_id=uploaded_zip.portfolio_id,
    )


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio_zips(
    portfolio_id: str,
    db: Session = Depends(get_db),
) -> PortfolioResponse:
    """Return all ZIPs linked to a portfolio."""
    zips = (
        db.query(UploadedZip)
        .filter(UploadedZip.portfolio_id == portfolio_id)
        .all()
    )

    if not zips:
        raise HTTPException(status_code=404, detail="Portfolio not found.")

    return PortfolioResponse(
        portfolio_id=portfolio_id,
        zips=[
            PortfolioZipItem(
                zip_id=z.id,
                filename=z.filename,
                uploaded_at=z.uploaded_at,
            )
            for z in zips
        ],
    )


@router.get("/{zip_id}/directories", response_model=DirectoriesResponse)
async def get_directories(
    zip_id: int, db: Session = Depends(get_db)
) -> DirectoriesResponse:
    """Return mock directory listings for an uploaded ZIP placeholder."""
    uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()
    if not uploaded_zip:
        raise HTTPException(status_code=404, detail="ZIP file not found.")
    extraction_path = extract_zip_to_persistent_location(uploaded_zip.path, zip_id) #extract the zip file.
    directory_walk.CURRENTPATH = extraction_path #set path to crawler
    file_dict, dir_list = directory_walk.crawl_directory() 
    file_value_list = []
    for filePath in file_dict.values():
        path = filePath[1] #get the file path, not name (even though its stored)
        file_value_list.append(path)


    return DirectoriesResponse(
        zip_id=uploaded_zip.id,
        filename=uploaded_zip.filename,
        directories=dir_list,
        cleanedfilespath=file_value_list
    )

