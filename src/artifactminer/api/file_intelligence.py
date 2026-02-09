import os
from fastapi import APIRouter, Depends, HTTPException
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
    try: 
         uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()
    except Exception as e: 
        raise HTTPException(
                status_code=404,
                detail=f"{e}"
            )
    if uploaded_zip is None:
            raise HTTPException(
                status_code=404,
                detail=f"could not find uploaded zip row with zip id {zip_id}"
            )
    if uploaded_zip.path is None:
        raise HTTPException(
                status_code=404,
                detail=f"path not found for zip id {zip_id}"
            )
    if not os.path.exists(uploaded_zip.path):
        raise HTTPException(
                status_code=404,
                detail=f"path {uploaded_zip.path} does not exist for system"
            )
    #2) get zip path data.
   
    extraction_path = extract_zip_to_persistent_location(uploaded_zip.path, zip_id) #extract the zip file.
    
    directory_walk.CURRENTPATH = extraction_path #set path to crawler
    filedict = directory_walk.crawl_directory() #crawl and get dictionary of file names
    
    file_values = filedict[0].values() #getting file name, path, and extension

    str_response = await get_crawler_pdf_contents(file_values=file_values)

    return str_response
