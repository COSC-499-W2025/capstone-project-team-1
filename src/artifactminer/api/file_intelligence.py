from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from artifactminer.FileIntelligence.file_intelligence_main import get_crawler_pdf_contents
from artifactminer.api.analyze import extract_zip_to_persistent_location
from artifactminer.db.models import UploadedZip
import artifactminer.directorycrawler.directory_walk as directory_walk
from ..db import get_db
#import artifactminer.directorycrawler.directory_walk as directory_walk
router = APIRouter(tags=["intelligence"])

@router.get("/fileintelligence", tags=["intelligence"])
async def get_file_intelligence_contents(zip_id: int, db: Session = Depends(get_db)) -> str:
    
    #1) get data from user consent (in config)

    #2) get zip path data.
    uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()

    extraction_path = extract_zip_to_persistent_location(uploaded_zip.path, zip_id) #extract the zip file.
    
    directory_walk.CURRENTPATH = extraction_path #set path to crawler
    filedict = directory_walk.crawl_directory() #crawl and get dictionary of file names

    file_values = filedict[0].values()

    str_response = await get_crawler_pdf_contents(file_values=file_values)

    return str_response
