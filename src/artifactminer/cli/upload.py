import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from artifactminer.api.zip import UPLOADS_DIR
from artifactminer.db import UploadedZip


def upload_zip(db: Session, input_path: Path) -> UploadedZip:
    """Copy ZIP into uploads dir and persist an UploadedZip row."""
    UPLOADS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = UPLOADS_DIR / f"{timestamp}_{input_path.name}"

    shutil.copy2(input_path, dest_path)

    uploaded_zip = UploadedZip(
        filename=input_path.name,
        path=str(dest_path),
        portfolio_id="cli-generated",
    )
    db.add(uploaded_zip)
    db.commit()
    db.refresh(uploaded_zip)
    return uploaded_zip

