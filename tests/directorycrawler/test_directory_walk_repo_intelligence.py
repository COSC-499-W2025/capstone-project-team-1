import sys
import os
from pathlib import Path

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
    dw.MOCKNAME = "mockdirectory-git"
    update_path() #1) I update the path to the folder with the .git folder
    crawl_directory() #2) call crawler, which now has repo data. 
    repoStats = getRepoStats(dw.CURRENTPATH)
    db = SessionLocal()#create a new session (copied from test_repo_intelligence)
    query = db.query(RepoStat).filter(RepoStat.project_name == repoStats.project_name).first()#select the saved stats
    assert query.project_name == "mockdirectory-git"
  

