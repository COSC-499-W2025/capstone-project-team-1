import sys
import os
import copy
from pathlib import Path

from artifactminer.db.seed import seed_questions
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from artifactminer.db.database import SessionLocal
from src.artifactminer.directorycrawler.user_based_directory_walk import get_user_data, delete_all_user_questions, add_user_answer
import src.artifactminer.directorycrawler.user_based_directory_walk as ubdw
from src.artifactminer.directorycrawler.directory_walk import (
    crawl_directory,
    user_keep_file,
    user_exclude_file,
    update_path,
    store_file_dictionary
)
import src.artifactminer.directorycrawler.directory_walk as dw

def test_user_based_directory_walk():
    store_file_dictionary.remove_all_dict()
    dw.userKeepFileName = []
    dw.userExcludeFileName = []

    dw.MOCKNAME = "mockdirectory1"

    db = SessionLocal()
    try:
        seed_questions(db)
    finally:
        db.close()

    add_user_answer(db, 5, "keep.log, *.avi")
    add_user_answer(db, 6, "*.c")
    get_user_data(db)
    delete_all_user_questions(db)
    update_path()
    files_dict, dirs_list = crawl_directory()
    assert len(files_dict) == 2
    


