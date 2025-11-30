import sys
import os
from pathlib import Path

from sqlalchemy import text

from artifactminer.db.models import RepoStat
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) #goto project directory

from artifactminer.db.database import SessionLocal
from src.artifactminer.directorycrawler.store_file_dict import StoreFileDict #getting class from store file dict
from src.artifactminer.directorycrawler.directory_walk import crawl_directory, update_path #getting function from directory walk
import src.artifactminer.directorycrawler.directory_walk as dw
from src.artifactminer.RepositoryIntelligence.repo_intelligence_main import getRepoStats

import src.artifactminer.directorycrawler.directory_walk as dw

a = StoreFileDict() #single instance


def test_repo_intelligence():
    #TO RUN THIS, PLEASE RESET DATABASE AND RUN uv run api in terminal!!!! 
    dw.MOCKNAME = "mockdirectory-git"
    update_path() #1) I update the path to the folder with the .git folder
    crawl_directory() #2) call crawler, which now has repo data. 
    repoStats = getRepoStats(Path(dw.CURRENTPATH))
    db = SessionLocal()#create a new session (copied from test_repo_intelligence)
    #query = db.query(RepoStat).filter(RepoStat.project_name == repoStats.project_name).first()#select the saved stats
   
    sql ="SELECT * FROM repo_stats;"
    res = db.execute(text(sql)).all()
    objects = [dict(row._mapping) for row in res]
    assert objects[0]["project_name"] == "mockdirectory-git" 
    assert objects[1]["project_name"] == "mock-git_2" 
    '''This proves that our repo can get multiple folders with .git from a root folder (mockdirectory-git) '''


