from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from artifactminer.api.analyze import extract_zip_to_persistent_location
from artifactminer.db.models import UploadedZip
import artifactminer.directorycrawler.directory_walk as directory_walk
from .schemas import (
    CrawlerFiles, FileValues
)
from ..db import get_db
#import artifactminer.directorycrawler.directory_walk as directory_walk
router = APIRouter(tags=["crawler"])

@router.post("/crawler", response_model=CrawlerFiles, tags=["crawler"])
async def get_crawler_contents(zip_id: int, db: Session = Depends(get_db)) -> CrawlerFiles:
    
    #1) get data from user consent (in config)

    #2) get zip path data.
    uploaded_zip = db.query(UploadedZip).filter(UploadedZip.id == zip_id).first()

    extraction_path = extract_zip_to_persistent_location(uploaded_zip.path, zip_id) #extract the zip file.
    
    directory_walk.CURRENTPATH = extraction_path #set path to crawler
    filedict = directory_walk.crawl_directory() #crawl and get dictionary of file names
    

    file_value_list = [
    FileValues(file_path=v[1], file_name=v[0], file_ext=v[2])
    for v in filedict[0].values()
    ]
        
    return CrawlerFiles(zip_id=zip_id, 
                        crawl_path_and_file_name_and_ext=file_value_list
                        )

@router.post("/crawler", response_model=CrawlerFiles, tags=["crawler"])
async def get_pdf_contents(zip_id: int, db: Session = Depends(get_db)) -> CrawlerFiles:
    