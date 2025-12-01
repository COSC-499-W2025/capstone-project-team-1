"""ZIP upload endpoints and helpers."""

from datetime import datetime
from pathlib import Path
import shutil
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .schemas import ZipUploadResponse, DirectoriesResponse
from ..db import UploadedZip, get_db


UPLOADS_DIR = Path("./uploads")


router = APIRouter(prefix="/zip", tags=["zip"])


@router.post("/upload", response_model=ZipUploadResponse)
async def upload_zip(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ZipUploadResponse:
    """Accept a ZIP file upload and track metadata in the database."""
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

    uploaded_zip = UploadedZip(filename=file.filename, path=str(file_path))
    db.add(uploaded_zip)
    db.commit()
    db.refresh(uploaded_zip)

    return ZipUploadResponse(zip_id=uploaded_zip.id, filename=uploaded_zip.filename)


@router.get("/{zip_id}/directories", response_model=DirectoriesResponse)
async def get_directories(
    zip_id: int, db: Session = Depends(get_db)
) -> DirectoriesResponse:
    """Return top-level directory listings for an uploaded ZIP file."""
    uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()
    if not uploaded_zip:
        raise HTTPException(status_code=404, detail="ZIP file not found.")

    zip_path = Path(uploaded_zip.path)
    if not zip_path.exists():
        raise HTTPException(
            status_code=404, detail="ZIP file no longer exists on disk."
        )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            top_level_dirs: set[str] = set()
            for name in zf.namelist():
                # Split path and get first component
                parts = Path(name).parts
                if parts:
                    first_part = parts[0]
                    # Check if this is a directory (ends with /) or has children
                    if name.endswith("/") or len(parts) > 1:
                        top_level_dirs.add(f"{first_part}/")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Invalid or corrupted ZIP file.")

    return DirectoriesResponse(
        zip_id=uploaded_zip.id,
        filename=uploaded_zip.filename,
        directories=sorted(top_level_dirs),
    )
